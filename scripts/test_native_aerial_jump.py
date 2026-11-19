#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Qualify the native-jab title's aerial-jump subset using BootHush only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from build_mac_movement import build, P1AIR_USED, P2AIR_USED, JVEL, P2JVEL
from build_mac_probe import be32, move_byte
from build_mac_title import GROUND_CONTROL_SHA
from test_mac_two_player import decode, pixels

ROOT = Path(__file__).resolve().parents[1]
MOVEMENT_SHA = 'a65c5fa382bee316b916cd6c6af52c4a2591496aa762c346e784e7a8bca7d25c'
JAB_SHA = '30e0e1a84928b05fcf387ce00a8dd10881ebc8c6692a104a925f4a1f68153d6a'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def player(memory, index):
    offset = 24 if index == 0 else 50
    result = {'state': memory[offset], 'clock': memory[offset+1],
            'velocity': int.from_bytes(memory[offset+2:offset+4], 'big', signed=True),
            'height': int.from_bytes(memory[offset+4:offset+6], 'big'),
            'button': memory[offset+6], 'jumps': memory[offset+7],
            'used': memory[107+index]}
    if len(memory) == 113:
        result.update(down=memory[109+index], fast=memory[111+index])
    return result


def tick(old, phase):
    """Separate local physics specification; input transitions checked below."""
    new = dict(old)
    if phase == 5:
        return new
    if old['state'] == 1:
        new['clock'] = (old['clock']+1) & 255
        if new['clock'] == 4:
            new['state'], new['velocity'] = 2, 0x480
    elif old['state'] == 2:
        new['clock'] = (old['clock']+1) & 255
        terminal = -1280 if old.get('fast') else -512
        new['velocity'] = max(old['velocity']-0x60, terminal)
        if new['clock'] == 8 and not old['button']:
            new['velocity'] = 0x102
        new['height'] = old['height']+new['velocity']
        if new['height'] <= 0:
            new.update(state=0, velocity=0, height=0, used=0)
            if 'fast' in new:
                new['fast'] = 0
    return new


def validate_jump_case(name, result, index, want):
    states = [s['players'][index] for s in result['observations']]
    if states[-1]['jumps'] != want or states[-1]['state'] != 0 or states[-1]['used']:
        raise ValueError(name+': jump limit or landing reset failed')
    if want == 2:
        prep = [s for s in states if s['jumps'] == 2 and s['state'] == 1]
        if not prep or any(s['velocity'] or not s['height'] or s['used'] != 1 for s in prep):
            raise ValueError(name+': aerial preparation did not preserve altitude/reset velocity')
        if len({s['height'] for s in prep}) != 1:
            raise ValueError(name+': altitude changed during aerial preparation')
        entries = [(old, new) for old, new in zip(states, states[1:])
                   if old['jumps'] == 1 and new['jumps'] == 2]
        if len(entries) != 1 or entries[0][0]['height'] != entries[0][1]['height']:
            raise ValueError(name+': aerial entry changed altitude')
        if not any(s['jumps'] == 2 and s['clock'] == 4 and s['velocity'] == 0x480 for s in states):
            raise ValueError(name+': aerial takeoff missing')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('boothush', 'movement', 'jab', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--air', type=Path, help='also qualify an opt-in aerial-control component')
    parser.add_argument('--fast-fall', action='store_true', help='also exercise Down releases for both players')
    parser.add_argument('--side-dash', action='store_true', help='run the jumps suite on the side-dash title')
    args = parser.parse_args()
    exe, movement, jab = (p.resolve(strict=True) for p in (args.boothush, args.movement, args.jab))
    supported_ground = (MOVEMENT_SHA, GROUND_CONTROL_SHA) if args.fast_fall else (MOVEMENT_SHA,)
    if sha(movement) not in supported_ground or sha(jab) != JAB_SHA:
        raise ValueError('unexpected retained native component')
    inputs = [exe, movement, jab, Path(__file__), *sorted((ROOT/'scripts').glob('build_mac_*.py')),
              ROOT/'scripts/test_mac_two_player.py', ROOT/'scripts/test_mac_combat.py']
    air = args.air.resolve(strict=True) if args.air else None
    if air is not None:inputs.append(air)
    before = {str(p): sha(p) for p in inputs}
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    image, used = build(jumping=True, combat=True, two_player=True, title=True,
                        native_movement=movement.read_bytes(), native_p2=True,
                        native_jab=(jab.read_bytes(), 0, 22), native_air=air.read_bytes() if air else None,
                        fast_fall=args.fast_fall,side_dash=args.side_dash)
    rom = out/'aerial-jump.rom'
    rom.write_bytes(image)

    def run(name, events, selected_rom=rom, points=tuple(range(38, 69))+(106,), stop=14500000):
        frames, witness = out/(name+'.pbmseq'), out/(name+'.keyboard')
        cmd = [str(exe), '--machine', 'mac128k', '--rom', str(selected_rom), '--cycles', str(stop),
               '--timeout-ms', '20000', '--mouse-button', '2000000:1', '--mouse-button', '2400000:0',
               '--capture-series', str(frames), '--capture-memory', f'0xb00:{113 if args.fast_fall else 109}',
               '--keyboard-witness', str(witness)]
        for point in points:
            cmd += ['--capture-vbl', str(point)]
        for cycle, key, down in events:
            cmd += ['--key', f'{cycle}:{key}:{down}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (out/(name+'.log')).write_text(result.stdout+'\n--- stderr ---\n'+result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name+': BootHush failed')
        data = json.loads(result.stdout)
        series = data['frame_series']
        if (data['status'] != 'cycle_limit' or series['rom_sha256'] != sha(selected_rom) or
                series['executable_sha256'] != before[str(exe)] or
                tuple(series[k] for k in ('requested', 'processed', 'pending', 'missing_images', 'dropped')) !=
                (len(points), len(points), 0, 0, 0) or
                any(data['keyboard_witness'][k] for k in ('dropped', 'rejected', 'pending'))):
            raise ValueError(name+': incomplete capture or input')
        rows = [line.split() for line in witness.read_text(encoding='ascii').splitlines()[2:]]
        deliveries = [(int(row[0]), int(row[3])) for row in rows if row[2] == 'key_delivered']
        if [v for _, v in deliveries] != [(key<<1)|1|(0 if down else 128) for _, key, down in events]:
            raise ValueError(name+': input delivery mismatch')
        blob, observations = frames.read_bytes(), []
        for sample in series['samples']:
            memory = bytes.fromhex(sample['memory']['bytes'])
            if len(memory) != (113 if args.fast_fall else 109) or not sample['processed'] or not sample['image_available']:
                raise ValueError(name+': missing state')
            state = decode({'memory': {'bytes': memory[:58].hex()}})
            pixels(blob[sample['offset']:sample['offset']+sample['length']], state)
            observations.append({'vbl': sample['frame'], 'cycle': sample['cycle'], 'phase': memory[20],
                                 'players': [player(memory, i) for i in range(2)]})
        checks = 0
        for old, new in zip(observations, observations[1:]):
            if new['vbl'] != old['vbl']+1 or any(old['cycle'] <= c < new['cycle'] for c, _ in deliveries):
                continue
            for index in range(2):
                if new['players'][index] != tick(old['players'][index], old['phase']):
                    raise ValueError(name+': aerial state mismatch '+str((index, old, new)))
            checks += 1
        if checks < 15:
            raise ValueError(name+': insufficient independent physics intervals')
        return {'command': cmd, 'deliveries': deliveries, 'oracle_intervals': checks,
                'frames_sha256': sha(frames), 'witness_sha256': sha(witness), 'observations': observations}

    cases, events_by_name = {}, {}
    for index, right, left, attack, jump in ((0, 0, 1, 3, 2), (1, 4, 5, 6, 7)):
        base = [(3500000, jump, 1), (4800000, jump, 0)]
        variations = {
            'held': [(3500000, jump, 1)],
            'double': base+[(5600000, jump, 1)],
            'falling': base+[(6800000, jump, 1)],
            'short': base+[(5600000, jump, 1), (6100000, jump, 0)],
            'third_refused': base+[(5600000, jump, 1), (7000000, jump, 0), (7400000, jump, 1)],
            'direction': base+[(5200000, right, 1), (5600000, jump, 1), (6500000, right, 0)],
            'attack_refused': base+[(5200000, attack, 1), (5600000, jump, 1)],
            'opposed_refused': base+[(5000000, right, 1), (5200000, left, 1), (5600000, jump, 1)],
        }
        for kind, events in variations.items():
            name = f'p{index+1}_{kind}'
            events_by_name[name] = events
            result = run(name, events)
            states = [s['players'][index] for s in result['observations']]
            want = 1 if kind in ('held', 'attack_refused', 'opposed_refused') else 2
            validate_jump_case(name, result, index, want)
            if any(s['players'][1-index]['jumps'] or s['players'][1-index]['used'] for s in result['observations']):
                raise ValueError(name+': other player was changed')
            if kind == 'falling':
                if not any(old['velocity'] < 0 and new['jumps'] == 2 and old['jumps'] == 1
                           for old, new in zip(states, states[1:])):
                    raise ValueError(name+': downward-momentum entry was not exercised')
            cases[name] = result
        full = [s['players'][index] for s in cases[f'p{index+1}_double']['observations']]
        short = [s['players'][index] for s in cases[f'p{index+1}_short']['observations']]
        if (not any(s['jumps'] == 2 and s['clock'] == 8 and s['velocity'] == 0x102 for s in short) or
                max(s['height'] for s in short) >= max(s['height'] for s in full)):
            raise ValueError('aerial short hop did not reduce height')
        name = f'p{index+1}_rearmed'
        events = base+[(5600000, jump, 1), (10500000, jump, 0),
                       (14000000, jump, 1), (15300000, jump, 0), (16100000, jump, 1)]
        events_by_name[name] = events
        result = run(name, events, points=tuple(range(120, 151))+(185,), stop=25000000)
        states = [s['players'][index] for s in result['observations']]
        if not any(s['jumps'] == 4 and s['used'] == 1 for s in states) or states[-1]['used'] or states[-1]['jumps'] != 4:
            raise ValueError(name+': landing failed to rearm second aerial jump')
        cases[name] = result

    both = sorted(events_by_name['p1_double']+[(c+200000, k, d) for c, k, d in events_by_name['p2_double']])
    cases['both_double'] = run('both_double', both)
    for index in range(2):
        validate_jump_case('both_double', cases['both_double'], index, 2)
    repeat = run('both_repeat', both)
    if repeat['observations'] != cases['both_double']['observations'] or repeat['frames_sha256'] != cases['both_double']['frames_sha256']:
        raise ValueError('identical schedule was nondeterministic')
    cases['both_repeat'] = repeat

    if args.fast_fall:
        for index, down, jump, right, attack in ((0,8,2,0,3), (1,9,7,4,6)):
            leap = [(3500000,jump,1), (4900000,jump,0)]
            press = (5150000,down,1)
            release = (6000000,down,0)
            scenarios = {
                'release': leap+[press,release],
                'rising': leap+[press,(5500000,down,0)],
                'descending': leap+[press,(6750000,down,0)],
                'held': leap+[press],
                'direction': leap+[press,(5500000,right,1),release],
                'attack': leap+[press,(5500000,attack,1),release],
                'jump_held': [leap[0],press,release],
                'grounded': [press,release],
                'jump_cancel': leap+[press,release,(6300000,jump,1)],
            }
            landings = {}
            for kind,events in scenarios.items():
                name = f'p{index+1}_fall_{kind}'
                result = run(name,events)
                rows = [(s['vbl'],s['players'][index]) for s in result['observations']]
                active = [s for _,s in rows if s['fast']]
                if bool(active) != (kind in ('release','rising','descending','jump_cancel')):
                    raise ValueError(name+': wrong fast-fall activation')
                if kind != 'grounded' and not any(s['state']==2 for _,s in rows):
                    raise ValueError(name+': missing airborne control')
                if active and not all(s['velocity']==-1280 and s['down']==0 and s['state']==2 for s in active):
                    raise ValueError(name+': incorrect descent')
                if kind in ('rising','descending'):
                    previous = next(old for (_,old),(_,new) in zip(rows,rows[1:])
                                    if not old['fast'] and new['fast'])
                    if previous['velocity'] * (1 if kind == 'rising' else -1) <= 0:
                        raise ValueError(name+': wrong vertical direction before release')
                if not any(s['down']==1 for _,s in rows):
                    raise ValueError(name+': down press never observed')
                if any(s['players'][1-index]['fast'] or s['players'][1-index]['down'] for s in result['observations']):
                    raise ValueError(name+': affected opponent')
                if kind in ('release','held'):
                    landings[kind] = next(frame for frame,s in rows if s['jumps']==1 and s['state']==0)
                if kind == 'jump_cancel':
                    validate_jump_case(name,result,index,2)
                    if any(s['fast'] for _,s in rows if s['jumps']==2):
                        raise ValueError(name+': aerial jump failed to reset terminal speed')
                if rows[-1][1]['fast']:
                    raise ValueError(name+': landing failed to reset fast fall')
                cases[name] = result
            if landings['release'] >= landings['held']:
                raise ValueError('fast fall did not land sooner than its held-key control')
        events = [(3500000,2,1),(3700000,7,1),(4900000,2,0),(5100000,7,0),
                  (5350000,8,1),(5550000,9,1),(6100000,8,0)]
        name = 'two_player_fall'
        cases[name] = run(name,events)
        if not any(p1['state']==0 and p1['jumps']==1 and p2['height']>0 and p2['down']==1
                   for p1,p2 in (s['players'] for s in cases[name]['observations'])):
            raise ValueError('two-player release/hold difference missing')

    controls = {}
    for index, address, velocity in ((0, P1AIR_USED, JVEL), (1, P2AIR_USED, P2JVEL)):
        # Omit the usage latch: the next airborne press must wrongly restart.
        needle = move_byte(1, address)
        if image.count(needle) != 1:
            raise ValueError('usage-latch mutation site changed')
        altered = image.replace(needle, b'\x4e\x71'*4, 1)
        path = out/f'p{index+1}-unlimited-mutant.rom'
        path.write_bytes(altered)
        result = run(f'p{index+1}-unlimited-mutant', events_by_name[f'p{index+1}_third_refused'], path)
        if max(s['players'][index]['jumps'] for s in result['observations']) != 3:
            raise ValueError('unlimited mutation was not detected')
        try:
            validate_jump_case(path.name, result, index, 2)
        except ValueError as exc:
            if 'jump limit' not in str(exc):
                raise
        else:
            raise ValueError('jump-limit oracle accepted unlimited jumps')
        controls[path.name] = {'sha256': sha(path), 'observed_jumps': 3, 'oracle_rejected': True}
        # Nonzero momentum during preparation must violate the state oracle.
        needle = move_byte(1, address)+bytes.fromhex('33fc0000')+be32(velocity)
        if image.count(needle) != 1:
            raise ValueError('velocity reset mutation site changed')
        altered = image.replace(needle, move_byte(1, address)+bytes.fromhex('33fc0060')+be32(velocity), 1)
        path = out/f'p{index+1}-momentum-mutant.rom'
        path.write_bytes(altered)
        result = run(f'p{index+1}-momentum-mutant', events_by_name[f'p{index+1}_double'], path)
        if not any(s['players'][index]['jumps'] == 2 and s['players'][index]['state'] == 1 and
                   s['players'][index]['velocity'] == 0x60 for s in result['observations']):
            raise ValueError('momentum reset mutation was not detected')
        try:
            validate_jump_case(path.name, result, index, 2)
        except ValueError as exc:
            if 'reset velocity' not in str(exc):
                raise
        else:
            raise ValueError('aerial preparation oracle accepted nonzero momentum')
        controls[path.name] = {'sha256': sha(path), 'observed_preparation_velocity': 0x60, 'oracle_rejected': True}
    if before != {str(p): sha(p) for p in inputs}:
        raise ValueError('input changed during qualification')
    report = {'status': 'pass', 'rom_sha256': sha(rom), 'emitter_end': 0x104+used,
              'rom_bytes': len(image), 'input_sha256': before, 'cases': cases, 'mutation_controls': controls,
              'limits': 'Source-derived aerial-jump subset, original placeholder graphics and local physics; no complete match, source-matched NES run or physical Mac claim.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'pass', 'cases': len(cases), 'rom_sha256': sha(rom), 'report': str(out/'report.json')}))


if __name__ == '__main__':
    main()
