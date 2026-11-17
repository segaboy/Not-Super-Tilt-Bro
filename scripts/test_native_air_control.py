#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build and qualify opt-in native PAL aerial horizontal control in BootHush."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_mac_movement import Asm, build
from build_mac_probe import be32, move_long
from test_mac_two_player import decode, pixels
from test_native_aerial_jump import MOVEMENT_SHA, JAB_SHA, player, tick
from test_native_call_preservation import compare

ROOT = Path(__file__).resolve().parents[1]
AIR_BASE = 0x40e400


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def air_velocity(current, direction):
    target = 256*direction
    rate = 128 if direction*current < 256 and direction else 7
    difference = target-current
    return current+(1 if difference > 0 else -1)*min(abs(difference), rate) if difference else current


def ground_velocity(current, direction):
    if direction:
        return current+64*direction if direction*current < 512 else current
    return (1 if current > 0 else -1)*max(0, abs(current)-96)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('boothush', 'tool-bin', 'movement', 'jab', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    exe, tools, movement, jab = (p.resolve(strict=True) for p in
                                (args.boothush, args.tool_bin, args.movement, args.jab))
    if sha(movement) != MOVEMENT_SHA or sha(jab) != JAB_SHA:
        raise ValueError('unexpected retained native component')
    gcc, nm, objcopy = (tools/('m68k-unknown-elf-'+name+'.exe') for name in ('gcc', 'nm', 'objcopy'))
    source = ROOT/'guest/sinbad_aerial.c'
    inputs = [exe, movement, jab, gcc, nm, objcopy, source, ROOT/'guest/sinbad_aerial.h', Path(__file__),
              ROOT/'scripts/test_native_aerial_jump.py', ROOT/'scripts/test_mac_two_player.py',
              ROOT/'scripts/test_native_call_preservation.py',
              ROOT/'scripts/test_mac_combat.py', *sorted((ROOT/'scripts').glob('build_mac_*.py'))]
    identities = {str(p): sha(p) for p in inputs}
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy();env['PATH'] = str(tools)+os.pathsep+env.get('PATH', '')
    commands = []

    def invoke(cmd, name):
        cmd = [str(v) for v in cmd];commands.append(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40, env=env,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (out/(name+'.log')).write_text(result.stdout+'\n--- stderr ---\n'+result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name+': command failed')
        return result.stdout

    def component(name, replacement=None):
        folder = out/name;folder.mkdir();selected = source
        if replacement:
            text = source.read_text(encoding='utf-8')
            if text.count(replacement[0]) != 1:raise ValueError('component mutation site changed')
            selected = folder/'mutant.c';selected.write_text(text.replace(*replacement), encoding='utf-8')
        obj, elf, binary = (folder/('air.'+suffix) for suffix in ('o', 'elf', 'bin'))
        invoke([gcc, '-mcpu=68000', '-Wa,-m68000', '-std=c11', '-Os', '-ffreestanding', '-fno-builtin',
                '-fno-pic', '-fno-pie', '-fno-stack-protector', '-fno-unwind-tables',
                '-fno-asynchronous-unwind-tables', '-Wall', '-Wextra', '-Werror', '-I', ROOT/'guest',
                '-c', selected, '-o', obj], name+'-compile')
        invoke([gcc, '-mcpu=68000', '-nostdlib', '-no-pie', '-Wl,--build-id=none', '-Wl,-Ttext=0x40e400',
                '-Wl,--entry=sinbad_aerial_step', '-Wl,-Map,'+str(folder/'air.map'), obj, '-o', elf], name+'-link')
        if invoke([nm, '--undefined-only', elf], name+'-undefined').strip():
            raise ValueError('unresolved component symbols')
        symbols = invoke([nm, '--defined-only', '--format=posix', elf], name+'-symbols')
        if not any(line.split()[:3] == ['sinbad_aerial_step', 'T', '40e400'] for line in symbols.splitlines()):
            raise ValueError('component entry moved')
        invoke([objcopy, '-O', 'binary', elf, binary], name+'-objcopy')
        return binary.read_bytes()

    code = component('a');twin = component('b')
    if code != twin:raise ValueError('native air component twins differ')
    velocities = (-32768, -512, -264, -263, -257, -256, -255, -129, -128, -127,
                  -8, -7, -6, -1, 0, 1, 6, 7, 8, 127, 128, 129, 255, 256, 257, 263, 264, 512, 32767)
    probe_cases = [(velocity, direction) for velocity in velocities for direction in (-1, 0, 1)]

    def probe(name, component_code):
        e = Asm()
        e.put(bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe 41f900400000 93c9 703f 22d8 51c8fffc'))
        cursor = 0x2000;e.put(move_long(0x41495201, cursor));cursor += 4
        expected = bytearray(b'AIR\x01')
        for velocity, direction in probe_cases:
            position = 0x8000;e.setword(position, 0xb00);e.setword(velocity, 0xb02)
            for _ in range(6):
                e.put(bytes.fromhex('2f3c')+be32(direction & 0xffffffff)+bytes.fromhex('4879')+be32(0xb02)+
                      bytes.fromhex('4879')+be32(0xb00)+bytes.fromhex('4eb9')+be32(AIR_BASE)+bytes.fromhex('4fef000c'))
                for address in (0xb00, 0xb02):
                    e.word('3039', address);e.word('33c0', cursor);cursor += 2
                velocity = air_velocity(velocity, direction);position = (position+velocity) & 65535
                expected += position.to_bytes(2, 'big')+(velocity & 65535).to_bytes(2, 'big')
        e.setword(0xa55a, cursor);expected += b'\xa5\x5a';e.label('done');e.put(bytes.fromhex('60fe'))
        body = e.finish()
        if 0x104+len(body) >= 0xe400:raise ValueError('probe exceeded code slot')
        image = bytearray(65536);image[:8] = be32(0x4000)+be32(0x400104)
        for vector in range(2, 64):image[vector*4:vector*4+4] = be32(e.labels['done'])
        image[0x104:0x104+len(body)] = body;image[0xe400:0xe400+len(component_code)] = component_code
        path = out/(name+'.rom');path.write_bytes(image)
        result = json.loads(invoke([exe, '--machine', 'mac128k', '--rom', path, '--cycles', '4000000',
                                   '--timeout-ms', '20000', '--inspect', f'0x2000:{len(expected)}'], name))
        raw = bytes.fromhex(result['memory']['bytes'])
        if result['status'] != 'cycle_limit' or raw[:4] != b'AIR\x01' or raw[-2:] != b'\xa5\x5a':
            raise ValueError('component probe did not complete')
        return {'rom_sha256': sha(path), 'matches_oracle': raw == expected, 'result': result,
                'steps': len(probe_cases)*6, 'observed_sha256': hashlib.sha256(raw).hexdigest()}

    probes = {'baseline': probe('component-probe', code)}
    if not probes['baseline']['matches_oracle']:raise ValueError('native air boundary probe failed')
    for name, replacement in (('influence', ('step = 0x80;', 'step = 0x40;')),
                               ('friction', ('step = 7;', 'step = 8;'))):
        probes[name] = probe(name+'-probe', component(name+'-mutant', replacement))
        if probes[name]['matches_oracle']:raise ValueError(name+': component mutation escaped')

    kwargs = dict(jumping=True, combat=True, two_player=True, title=True, native_movement=movement.read_bytes(),
                  native_p2=True, native_jab=(jab.read_bytes(), 0, 22))
    image, size = build(**kwargs, native_air=code);rom = out/'air-control.rom';rom.write_bytes(image)

    def run(name, events, selected_rom=rom, points=range(34, 66), stop=11000000):
        frames, witness = out/(name+'.pbmseq'), out/(name+'.keyboard')
        cmd = [exe, '--machine', 'mac128k', '--rom', selected_rom, '--cycles', str(stop), '--timeout-ms', '20000',
               '--mouse-button', '2000000:1', '--mouse-button', '2400000:0', '--capture-series', frames,
               '--capture-memory', '0xb00:109', '--keyboard-witness', witness]
        for point in points:cmd += ['--capture-vbl', str(point)]
        for cycle, key, down in events:cmd += ['--key', f'{cycle}:{key}:{down}']
        data = json.loads(invoke(cmd, name));series = data['frame_series']
        if (data['status'] != 'cycle_limit' or series['rom_sha256'] != sha(selected_rom) or
                series['executable_sha256'] != identities[str(exe)] or
                tuple(series[k] for k in ('requested', 'processed', 'pending', 'missing_images', 'dropped')) !=
                (len(points), len(points), 0, 0, 0) or
                any(data['keyboard_witness'][k] for k in ('dropped', 'rejected', 'pending'))):
            raise ValueError(name+': incomplete run')
        rows = [line.split() for line in witness.read_text(encoding='ascii').splitlines()[2:]]
        deliveries = [(int(row[0]), int(row[3])) for row in rows if row[2] == 'key_delivered']
        if [v for _, v in deliveries] != [(key<<1)|1|(0 if down else 128) for _, key, down in events]:
            raise ValueError('keyboard delivery mismatch')
        blob = frames.read_bytes();states = []
        for sample in series['samples']:
            raw = bytes.fromhex(sample['memory']['bytes'])
            if len(raw) != 109 or raw[73] != 2:raise ValueError(name+': outside gameplay')
            state = decode({'memory': {'bytes': raw[:58].hex()}})
            pixels(blob[sample['offset']:sample['offset']+sample['length']], state)
            players = [player(raw, index) for index in range(2)]
            for index, pos, vel, held in ((0, 16, 14, 8), (1, 38, 88, 40)):
                players[index].update(x=int.from_bytes(raw[pos:pos+2], 'big'),
                                      horizontal=int.from_bytes(raw[vel:vel+2], 'big', signed=True),
                                      direction={0: 0, 1: 1, 2: -1}[raw[held]])
            states.append({'vbl': sample['frame'], 'cycle': sample['cycle'], 'phase': raw[20], 'players': players})
        checks, input_checks, modes = 0, 0, set()
        for old, new in zip(states, states[1:]):
            interval_inputs = [value for cycle, value in deliveries if old['cycle'] <= cycle < new['cycle']]
            for index in range(2):
                a, b = old['players'][index], new['players'][index]
                if interval_inputs:
                    direction_codes = (1, 3, 129, 131) if index == 0 else (9, 11, 137, 139)
                    if any(value not in direction_codes for value in interval_inputs) or a['state'] != 2 or b['state'] != 2:
                        continue
                    # Input may change direction but cannot reset momentum.
                    velocity = a['horizontal'] if old['phase'] == 5 else air_velocity(a['horizontal'], b['direction'])
                    if b['horizontal'] != velocity:raise ValueError(name+': airborne input reset momentum')
                    input_checks += 1
                    continue
                velocity = a['horizontal']
                if old['phase'] != 5:
                    if a['state'] == 2:
                        velocity = air_velocity(velocity, a['direction']);modes.add('air')
                    elif a['used']:
                        modes.add('aerial_preparation')
                    else:
                        velocity = ground_velocity(velocity, a['direction']);modes.add('ground')
                x = a['x'] if old['phase'] == 5 else max(0x1000, min(0xe000, a['x']+velocity))
                if (b['horizontal'], b['x']) != (velocity, x):
                    raise ValueError(name+': horizontal oracle mismatch '+str((index, old, new, velocity, x)))
                vertical = {k: v for k, v in a.items() if k not in ('x', 'horizontal', 'direction')}
                if tick(vertical, old['phase']) != {k: v for k, v in b.items() if k in vertical}:
                    raise ValueError(name+': vertical behavior changed')
                checks += 1
        if checks < 35:raise ValueError(name+': insufficient physics intervals')
        return {'command': [str(v) for v in cmd], 'observations': states, 'oracle_intervals': checks,
                'direction_event_intervals': input_checks, 'modes': sorted(modes),
                'frames_sha256': sha(frames), 'keyboard_sha256': sha(witness)}

    cases, events_by_name = {}, {}
    for index, forward, backward, jump in ((0, 0, 1, 2), (1, 5, 4, 7)):
        base = [(3500000, forward, 1), (4200000, jump, 1)]
        variations = {
            'overspeed': base,
            'neutral': base+[(5300000, forward, 0)],
            'reverse': base+[(5300000, forward, 0), (5800000, backward, 1)],
            'overlap': base+[(5600000, backward, 1), (6700000, backward, 0)],
            'aerial_preparation': base+[(5500000, jump, 0), (6000000, jump, 1), (6200000, backward, 1)],
        }
        for kind, events in variations.items():
            name = f'p{index+1}_{kind}';events_by_name[name] = events
            cases[name] = run(name, events)
            obs = [s['players'][index] for s in cases[name]['observations']]
            if 'air' not in cases[name]['modes']:raise ValueError(name+': no aerial movement')
            if kind in ('reverse', 'overlap') and cases[name]['direction_event_intervals'] < 1:
                raise ValueError(name+': no airborne direction-change check')
            if kind == 'reverse' and not any(s['horizontal']*(1 if index == 0 else -1) < 0 for s in obs):
                raise ValueError(name+': reversal did not complete')
            if kind == 'aerial_preparation' and 'aerial_preparation' not in cases[name]['modes']:
                raise ValueError(name+': missing aerial preparation')
        name = f'p{index+1}_landing'
        cases[name] = run(name, base, points=range(62, 94), stop=13000000)
        obs = [s['players'][index] for s in cases[name]['observations']]
        if not any(s['state'] == 2 for s in obs) or not any(s['state'] == 0 and 512 <= abs(s['horizontal']) < 576 for s in obs):
            raise ValueError(name+': ground speed did not resume after landing')
    both = sorted(events_by_name['p1_reverse']+[(c+200000, k, d) for c, k, d in events_by_name['p2_reverse']])
    cases['both_reverse'] = run('both_reverse', both)
    cases['both_repeat'] = run('both_repeat', both)
    if any(cases['both_reverse'][k] != cases['both_repeat'][k] for k in ('observations', 'frames_sha256')):
        raise ValueError('combined scenario was not repeatable')
    pattern = bytes.fromhex('4eb9')+be32(AIR_BASE)
    if image.count(pattern) != 6:raise ValueError('unexpected aerial call-site count')
    mutant = out/'ground-routing-mutant.rom'
    mutant.write_bytes(image.replace(pattern, bytes.fromhex('4eb9')+be32(0x40e000)))
    try:run('ground-routing-mutant', events_by_name['p1_overspeed'], mutant)
    except ValueError as exc:
        if 'horizontal oracle mismatch' not in str(exc):raise
    else:raise ValueError('ground-routing mutation escaped')

    def call_observation(name, selected, pc, events, lower_bound, registers=True):
        frame = out/(name+'.pbm')
        cmd = [exe, '--machine', 'mac128k', '--rom', selected, '--cycles', '10000000', '--timeout-ms', '20000',
               '--mouse-button', '2000000:1', '--mouse-button', '2400000:0', '--until-pc', str(pc),
               '--until-pc-after', str(lower_bound), '--inspect', '0xb00:109', '--frame', frame]
        if registers:cmd += ['--mac-cpu-state', '1']
        for cycle, key, down in events:cmd += ['--key', f'{cycle}:{key}:{down}']
        result = json.loads(invoke(cmd, name))
        if result['status'] != 'condition_met':raise ValueError(name+': air call was not reached')
        return result, frame.read_bytes()

    call_sites = [offset for offset in range(0x104, 0x104+size, 2) if image[offset:offset+6] == pattern]
    calls = []
    for ordinal, offset in enumerate(call_sites):
        index, direction = ordinal//3, (1, -1, 0)[ordinal%3]
        key = (0 if direction == 1 else 1) if index == 0 else (4 if direction == 1 else 5)
        events = ([(3500000, key, 1)] if direction else [])+[(4200000, 2 if index == 0 else 7, 1)]
        label, pc = 'air-call-'+str(ordinal), 0x400000+offset
        before, first = call_observation(label+'-before', rom, pc, events, 5200000)
        memory = bytes.fromhex(before['memory']['bytes'])
        if memory[24 if index == 0 else 50] != 2:raise ValueError(label+': call outside airborne state')
        after, second = call_observation(label+'-after', rom, pc+6, events, before['cycles'])
        errors = compare(before, after)
        if errors or first != second:raise ValueError(label+': ABI/frame preservation failed '+repr(errors))
        plain, plain_frame = call_observation(label+'-plain', rom, pc+6, events, before['cycles'], False)
        if plain != {k: v for k, v in after.items() if k != 'cpu'} or plain_frame != second:
            raise ValueError(label+': register observer changed execution')
        calls.append({'pc': pc, 'player': index+1, 'direction': direction,
                      'before_cycle': before['cycles'], 'call_cycles': after['cycles']-before['cycles'],
                      'preserved': ['D2-D7', 'A2-A6', 'A7', 'SR-control', 'frame'], 'observer_parity': True})
        if ordinal == 0:
            altered = bytearray(image);altered[0xe400:0xe408] = bytes.fromhex('2e3c5aa55aa54e75')
            bad_rom = out/'bad-air-callee.rom';bad_rom.write_bytes(altered)
            bad, _ = call_observation('bad-air-callee', bad_rom, pc+6, events, before['cycles'])
            if 'D2-D7' not in compare(before, bad):raise ValueError('bad air callee escaped preservation oracle')
            bad_callee = {'rom_sha256': sha(bad_rom), 'oracle_rejected': True}
    if identities != {str(p): sha(p) for p in inputs}:raise ValueError('source or tools changed during test')
    report = {'status': 'pass', 'input_sha256': identities, 'rom_sha256': sha(rom),
              'emitter_end': 0x104+size, 'air_component_bytes': len(code),
              'air_component_sha256': hashlib.sha256(code).hexdigest(), 'air_component_end': 0xe400+len(code),
              'commands': commands, 'component_probes': probes, 'cases': cases,
              'native_calls': calls, 'bad_callee_mutation': bad_callee,
              'routing_mutation': {'rom_sha256': sha(mutant), 'oracle_rejected': True},
              'limits': 'Source-derived PAL horizontal air control, local keyboard/physics/rendering adapter; no complete match, source-matched NES result or hardware claim.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'pass', 'cases': len(cases), 'probe_steps': probes['baseline']['steps'],
                      'rom_sha256': sha(rom), 'report': str(out/'report.json')}))


if __name__ == '__main__':
    main()
