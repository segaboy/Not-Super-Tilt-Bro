# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Check real native movement/jab call boundaries in the mouse-start prototype.

Game-derived components stay port-only. The transferable result is a bounded
register/stack test method, not game implementation or hardware qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ROM_LAYOUTS = {
    '81a8d80ba392f58a953a14887587b888c11961b8711bd0916463022558cfd4e6': 38404,
    '0210d56550976e60ea3f38e3af9655a4faea34313a5ffe81aaeb7923daf26790': 38728,
}
TARGETS = {'movement': 0x40E000, 'jab_begin': 0x40E200, 'jab_tick': 0x40E216}
SCENARIOS = {'neutral': (), 'right': ((3500000, 0), (3700000, 4)),
             'left': ((3500000, 1), (3700000, 5)),
             'attack': ((3500000, 3), (3700000, 6))}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(before, after):
    fields = []
    if after.get('status') != 'condition_met':
        return ['stop']
    a, b = before['cpu'], after['cpu']
    if a['d'][2:] != b['d'][2:]: fields.append('D2-D7')
    if a['a'][2:7] != b['a'][2:7]: fields.append('A2-A6')
    if a['a'][7] != b['a'][7]: fields.append('A7')
    if (a['sr'] & 0xFF00) != (b['sr'] & 0xFF00): fields.append('SR-control')
    if after['cycles'] <= before['cycles']: fields.append('call-order')
    return fields


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('boothush', 'rom', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); exe = a.boothush.resolve(strict=True); rom = a.rom.resolve(strict=True)
    out = a.output.resolve()
    if out == ROOT or ROOT in out.parents: p.error('output must be outside repository')
    if sha(rom) not in ROM_LAYOUTS: p.error('unreviewed prototype ROM')
    identity = {'rom': sha(rom), 'emulator': sha(exe), 'script': sha(Path(__file__))}
    image = rom.read_bytes(); out.mkdir(parents=True, exist_ok=False)
    attempts = []; cases = []; controls = []

    def run(name, selected_rom, pc, events, registers=True, after_cycle=None):
        frame = out/(name+'.pbm')
        cmd = [str(exe), '--machine', 'mac128k', '--rom', str(selected_rom), '--cycles', '10000000',
               '--timeout-ms', '20000', '--mouse-button', '2000000:1', '--mouse-button', '2400000:0',
               '--until-pc', str(pc), '--inspect', '0xb00:108', '--frame', str(frame)]
        if registers: cmd += ['--mac-cpu-state', '1']
        if after_cycle is not None: cmd += ['--until-pc-after', str(after_cycle)]
        for event in events:
            cycle,key,*state=event
            cmd += ['--key', f'{cycle}:{key}:{state[0] if state else 1}']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (out/(name+'.log')).write_text(r.stdout+r.stderr, encoding='utf-8')
        result = json.loads(r.stdout)
        attempts.append({'name': name, 'command': cmd, 'returncode': r.returncode,
                         'result': result, 'frame_sha256': sha(frame) if frame.exists() else None})
        return result, frame

    for component, target in TARGETS.items():
        pattern = bytes.fromhex('4eb9') + struct.pack('>I', target)
        sites = [offset for offset in range(0x104, ROM_LAYOUTS[sha(rom)], 2) if image[offset:offset+6] == pattern]
        if len(sites) != (6 if component=='movement' else 2):
            raise ValueError('unexpected original call sites: '+component)
        for site in sites:
            label = component+'-'+format(site, 'x'); pc = 0x400000+site
            for scenario, events in SCENARIOS.items():
                name = label+'-'+scenario
                before, first = run(name+'-before', rom, pc, events)
                if before['status'] == 'cycle_limit': continue
                if before['status'] != 'condition_met': raise ValueError(name+': unexpected pre-call stop')
                after, second = run(name+'-after', rom, pc+6, events)
                errors = compare(before, after)
                if errors or first.read_bytes() != second.read_bytes():
                    raise ValueError(name+': preservation failed '+repr(errors))
                plain, plain_frame = run(name+'-plain', rom, pc+6, events, False)
                if plain != {k:v for k,v in after.items() if k != 'cpu'} or plain_frame.read_bytes() != second.read_bytes():
                    raise ValueError(name+': register observation perturbed guest')
                cases.append({'component': component, 'site': pc, 'scenario': scenario,
                              'call_cycles': after['cycles']-before['cycles'], 'stack': after['cpu']['a'][7],
                              'preserved': ['D2-D7', 'A2-A6', 'A7', 'SR-control', 'frame']})
                if not any(c['component'] == component for c in controls):
                    mutant = out/(component+'-bad-callee.rom'); changed = bytearray(image)
                    offset = target-0x400000
                    changed[offset:offset+8] = bytes.fromhex('2e3c5aa55aa54e75')
                    mutant.write_bytes(changed)
                    bad, _ = run(name+'-bad-callee', mutant, pc+6, events)
                    rejected = compare(before, bad)
                    if 'D2-D7' not in rejected: raise ValueError(name+': bad-callee control not detected')
                    controls.append({'component': component, 'rom_sha256': sha(mutant), 'detected': rejected})
                break
            else:
                raise ValueError('no scenario reached call site '+label)
    recovery=[]
    if ROM_LAYOUTS[sha(rom)] == 38728:
        events=((3500000,0,1),(3700000,4,1),(3900000,3,1),(4100000,6,1),
                (4300000,3,0),(4500000,6,0),(4700000,2,1),(4900000,7,1))
        for case in [c for c in cases if c['component']=='movement' and c['scenario']=='right']:
            pc=case['site'];name='recovery-'+format(pc,'x')
            before,first=run(name+'-before',rom,pc,events,after_cycle=9500000)
            if before['status']!='condition_met':raise ValueError('post-recovery call not reached')
            memory=bytes.fromhex(before['memory']['bytes'])
            if (memory[24],memory[50],memory[101],memory[103],memory[31],memory[57]) != (2,2,0,0,1,1):
                raise ValueError('post-recovery calls were not reached during both jumps')
            after,second=run(name+'-after',rom,pc+6,events,after_cycle=before['cycles'])
            errors=compare(before,after)
            if errors or first.read_bytes()!=second.read_bytes():raise ValueError('recovery preservation '+repr(errors))
            plain,frame=run(name+'-plain',rom,pc+6,events,False,after_cycle=before['cycles'])
            if plain!={k:v for k,v in after.items() if k!='cpu'} or frame.read_bytes()!=second.read_bytes():
                raise ValueError('recovery observation perturbed guest')
            recovery.append({'site':pc,'call_cycles':after['cycles']-before['cycles'],
                             'before_cycle':before['cycles'],'after_cycle':after['cycles'],'both_airborne':True})
        if len(recovery)!=2:raise ValueError('missing post-recovery player calls')
    if sha(rom) != identity['rom'] or sha(exe) != identity['emulator']:
        raise ValueError('input changed during native call tests')
    report = {'status': 'pass', 'identities': identity, 'cases': cases, 'controls': controls, 'attempts': attempts,
              'recovery_calls':recovery,
              'limits': 'Selected first and post-recovery calls in bounded synthetic-input scenarios. No arbitrary-call, physical, playable-match or historical compatibility proof; game code remains port-only.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'pass', 'call_sites': len(cases), 'controls': len(controls), 'report': str(out/'report.json')}))


if __name__ == '__main__':
    main()
