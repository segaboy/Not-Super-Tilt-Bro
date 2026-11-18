#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Headless failed-drain, fresh-click and fresh-key recovery checks in BootHush.

Uses existing title ROM profiles unchanged. Optional retained native movement,
jab and aerial components qualify the current gameplay title's recovery too.
All input is scheduled in the emulator, not physical or human qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from build_mac_movement import build
from build_mac_probe import move_byte, be32
from build_mac_title import ARMED, X, POINTER, title_pixels
from test_mac_two_player import decode, pixels, HEADER
from test_native_aerial_jump import MOVEMENT_SHA, JAB_SHA

AIR_SHA = 'd7bfcfc9be27610ae74b428589941e462da74f747fa660ad4573964b49b9ad4e'

CAPTURES = (1500000, 2100000, 2400000, 2800000, 3500000, 3900000,
            4200000, 4800000, 5500000, 6500000, 7500000, 8500000, 9500000)
EVENTS = (('mouse-motion', '1000000:16:0'),
          ('mouse-button', '2000000:1'),
          ('key', '3200000:0:1'),  # queued after the injected timeout
          ('mouse-button', '3800000:0'),
          ('mouse-button', '4000000:1'),
          ('mouse-button', '4400000:0'),
          ('key', '6000000:0:0'),
          ('key', '7000000:0:1'),
          ('key', '8000000:0:0'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def state(memory):
    b = bytes.fromhex(memory['bytes'])
    if len(b) not in (86, 109):
        raise ValueError('incomplete diagnostic memory')
    word = lambda at: int.from_bytes(b[at:at+2], 'big')
    result = {'state': b[73], 'armed': b[72], 'timeouts': word(22),
            'p1_x': word(16), 'p2_x': word(38), 'p1_held': b[8],
            'p1_mask': b[21], 'p2_held': b[40], 'p2_mask': b[41]}
    if len(b) == 109:
        # Explicitly cover stale jump/attack state as well as the direction latch.
        result['idle_gameplay'] = list(b[24:34] + b[35:38] + b[44:49] + b[50:58] + b[90:109])
        result['p1_velocity'] = word(14)
        result['p2_velocity'] = word(88)
    return result


def contract_errors(samples, player=1):
    """Behavioral checkpoints: failed clicks need rearming; old keys do not play."""
    errors = []
    for at in (2400000, 2800000, 3500000):
        s = samples[at]
        if (s['state'], s['armed'], s['timeouts']) != (3, 0, 1):
            errors.append('held-click-at-' + str(at))
    if (samples[3900000]['state'], samples[3900000]['armed']) != (3, 1):
        errors.append('released-click-before-retry')
    first_ready = 5100000 if 5100000 in samples else 4800000
    for at in (first_ready, 5500000, 6500000):
        s = samples[at]
        if (s['state'], s['p1_x'], s['p1_held'], s['p1_mask'],
                s['p2_x'], s['p2_held'], s['p2_mask'], s['timeouts']) != (
                2, 0x8000, 0, 0, 0xa800, 0, 0, 0):
            errors.append('stale-key-at-' + str(at))
        if 'idle_gameplay' in s and (any(s['idle_gameplay']) or s['p1_velocity'] or s['p2_velocity']):
            errors.append('stale-native-action-at-' + str(at))
    for at in (7500000, 8500000, 9500000):
        s = samples[at]
        active, other = ('p1', 'p2') if player == 1 else ('p2', 'p1')
        start, other_start = (0x8000, 0xa800) if player == 1 else (0xa800, 0x8000)
        if s['state'] != 2 or s[active+'_x'] <= start or s[other+'_x'] != other_start:
            errors.append('fresh-key-at-' + str(at))
        expected_held = 1 if at == 7500000 else 0
        if (s[active+'_held'], s[active+'_mask'], s[other+'_held'], s[other+'_mask']) != (
                expected_held, expected_held, 0, 0):
            errors.append('fresh-key-hold-release-at-' + str(at))
    return errors


def check_frame(frame, memory):
    b = bytes.fromhex(memory['bytes'])
    if b[73] in (1, 3):
        expected = title_pixels()
        x = int.from_bytes(b[80:82], 'big')
        y = int.from_bytes(b[82:84], 'big')
        for row, bits in enumerate(POINTER):
            for col, bit in enumerate(bits):
                if bit == '1':
                    expected[(y+row)*64+(x+col)//8] ^= 0x80 >> ((x+col) % 8)
        assert frame == HEADER + expected, 'unexpected title pixels'
    elif b[73] == 2:
        pixels(frame, decode({'memory': {'bytes': b[:58].hex()}}))
    else:
        # A cycle checkpoint may observe the handoff while the frame is changing.
        assert b[73] == 4, 'unexpected title state'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boothush', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--movement', type=Path, help='retained native movement component; requires --jab')
    parser.add_argument('--jab', type=Path, help='retained native jab component; requires --movement')
    parser.add_argument('--air', type=Path, help='retained optional air component; requires native movement/jab')
    parser.add_argument('--player', type=int, choices=(1, 2), default=1, help='player receiving fresh direction after recovery')
    args = parser.parse_args()
    exe = args.boothush.resolve(strict=True)
    if bool(args.movement) != bool(args.jab) or (args.air and not args.jab):
        parser.error('--movement and --jab must be supplied together; --air also requires them')
    components = {}
    for name, expected in (('movement', MOVEMENT_SHA), ('jab', JAB_SHA), ('air', AIR_SHA)):
        path = getattr(args, name)
        if path:
            path = path.resolve(strict=True)
            if sha(path.read_bytes()) != expected:
                raise ValueError('unexpected retained '+name+' component')
            components[name] = path
    native = bool(components)
    memory_size = 109 if native else 86
    # Six drained makes take longer than the original single-key fixture.
    captures = tuple(5100000 if native and c == 4800000 else c for c in CAPTURES)
    profile = 'native-jab-air' if args.air else 'native-jab' if native else 'emitter'
    kwargs = {}
    if native:
        kwargs.update(native_movement=components['movement'].read_bytes(), native_p2=True,
                      native_jab=(components['jab'].read_bytes(), 0, 22),
                      native_air=components['air'].read_bytes() if args.air else None)
    key = 0 if args.player == 1 else 4
    if native:
        # Queue direction, jump and attack for BOTH players after the failure.
        # Every make must be drained, so stale actions cannot hide behind a
        # movement-only oracle. Releases follow gameplay entry; fresh direction
        # is the sole permitted action in this recovery scenario.
        stale = (0, 2, 3, 4, 6, 7)
        events = tuple(sorted(([(kind, value) for kind, value in EVENTS if kind != 'key'] +
                  [('key', f'{3200000+i*10000}:{k}:1') for i, k in enumerate(stale)] +
                  [('key', f'{6000000+i*10000}:{k}:0') for i, k in enumerate(stale)] +
                  [('key', f'7000000:{key}:1'), ('key', f'8000000:{key}:0')]),
                  key=lambda item: int(item[1].split(':')[0])))
    else:
        events = tuple((kind, value.replace(':0:', f':{key}:')) if kind == 'key' else (kind, value)
                       for kind, value in EVENTS)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    image, used = build(jumping=True, combat=True, two_player=True, title=True, **kwargs)
    rom = out / 'title.rom'
    rom.write_bytes(image)
    identities = {'rom_sha256': sha(image), 'boothush_sha256': sha(exe.read_bytes()),
                  'script_sha256': sha(Path(__file__).read_bytes()),
                  'rom_used_through': used + 0x104,
                  'profile': profile, 'player': args.player, 'diagnostic_bytes': memory_size,
                  'components': {str(p): sha(p.read_bytes()) for p in components.values()},
                  'sources': {p.name: sha(p.read_bytes()) for p in
                              Path(__file__).parent.glob('*.py')}}
    trace = out / 'recovery.bhmouse'
    runs = []

    def run(name, events=events, mode=None, observed=True, selected_rom=rom):
        final = out / (name + '.pbm')
        frames = out / (name + '.pbmseq')
        witness = out / (name + '.keyboard')
        cmd = [str(exe), '--machine', 'mac128k', '--rom', str(selected_rom),
               '--cycles', '10000000', '--timeout-ms', '20000',
               '--keyboard-fault', '0x14:1:1:0', '--inspect', '0xb00:'+str(memory_size),
               '--frame', str(final)]
        if mode == 'replay':
            cmd += ['--mouse-replay', str(trace)]
        else:
            cmd += ['--mouse-dcd-invert', '3']
            if mode == 'record':
                cmd += ['--mouse-record', str(trace)]
        # BootHush requires chronological ordering across all scheduled kinds.
        for kind, value in events:
            if mode != 'replay' or kind == 'key':
                cmd += ['--' + kind, value]
        if observed:
            cmd += ['--capture-memory', '0xb00:'+str(memory_size), '--capture-series', str(frames),
                    '--keyboard-witness', str(witness)]
            for cycle in captures:
                cmd += ['--capture-cycle', str(cycle)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (out / (name + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name + ': ' + result.stdout + result.stderr)
        data = json.loads(result.stdout)
        assert data['status'] == 'cycle_limit' and data['mouse']['pending'] == 0
        assert len(bytes.fromhex(data['memory']['bytes'])) == memory_size, 'incomplete final diagnostic'
        assert data['keyboard_fault']['triggered']
        snapshots = []
        if observed:
            series = data['frame_series']
            assert (series['requested'], series['processed'], series['pending'],
                    series['missing_images'], series['dropped']) == (len(captures), len(captures), 0, 0, 0)
            assert series['rom_sha256'] == sha(selected_rom.read_bytes())
            assert series['executable_sha256'] == identities['boothush_sha256']
            witness_state = data['keyboard_witness']
            count = sum(kind == 'key' for kind, _ in events)
            assert (witness_state['scheduled'], witness_state['accepted'],
                    witness_state['pending'], witness_state['rejected'],
                    witness_state['dropped']) == (count, count, 0, 0, 0)
            assert all(event['accepted'] for event in data['series_inputs']['events'])
            assert tuple(sample['requested'] for sample in series['samples']) == captures
            assert tuple(sample['target'] for sample in series['samples']) == captures
            for point, sample in zip(captures, series['samples']):
                assert point <= sample['cycle'] < point + 100, 'capture missed its boundary'
                assert sample['processed'] and sample['image_available']
                assert len(bytes.fromhex(sample['memory']['bytes'])) == memory_size, 'incomplete checkpoint diagnostic'
                snapshots.append({'requested': point, 'actual': sample['cycle'],
                                  **state(sample['memory'])})
        record = {'name': name, 'command': cmd, 'result': data,
                  'final_sha256': sha(final.read_bytes()), 'checkpoints': snapshots}
        if observed:
            record.update(frames_sha256=sha(frames.read_bytes()),
                          keyboard_sha256=sha(witness.read_bytes()))
        (out / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        runs.append(record)
        return record

    recorded = run('record', mode='record')
    repeated = run('repeat')
    replayed = run('replay', mode='replay')
    for candidate in (recorded, repeated, replayed):
        samples = {s['requested']: s for s in candidate['checkpoints']}
        assert samples[1500000]['state'] == 1
        assert not contract_errors(samples, args.player), contract_errors(samples, args.player)
        data = candidate['result']
        raw = (out / (candidate['name'] + '.pbmseq')).read_bytes()
        for sample in data['frame_series']['samples']:
            check_frame(raw[sample['offset']:sample['offset']+sample['length']], sample['memory'])
        rows = [line.split() for line in (out / (candidate['name'] + '.keyboard')).read_text(encoding='ascii').splitlines()[2:]]
        delivered = [(int(row[0]), int(row[3])) for row in rows if row[2] == 'key_delivered']
        expected_keys = [tuple(map(int, value.split(':'))) for kind, value in events if kind == 'key']
        assert [value for _, value in delivered] == [(k << 1) | 1 | (0 if down else 128)
                                                    for _, k, down in expected_keys]
        for (scheduled, _, _), (actual, _) in zip(expected_keys, delivered):
            low, high = ((4000000, 4800000) if scheduled < 4000000 else
                         (scheduled, 6900000 if native else 6500000) if scheduled < 7000000 else
                         (scheduled, scheduled+500000))
            assert low < actual < high, 'delivery outside recovery checkpoint interval'
        assert sum(row[2] == 'fault_start' for row in rows) == 1
    for other in (repeated, replayed):
        assert recorded['checkpoints'] == other['checkpoints']
        for suffix in ('.pbmseq', '.keyboard', '.pbm'):
            assert (out / ('record' + suffix)).read_bytes() == (out / (other['name'] + suffix)).read_bytes()
        assert [(s['cycle'], s['memory']) for s in recorded['result']['frame_series']['samples']] == [
            (s['cycle'], s['memory']) for s in other['result']['frame_series']['samples']]

    plain = run('plain', observed=False)
    for other in (repeated, replayed, plain):
        for field in ('status', 'cycles', 'pc', 'vbl', 'mouse', 'keyboard_fault', 'memory'):
            assert recorded['result'][field] == other['result'][field], (other['name'], field)
        assert recorded['final_sha256'] == other['final_sha256']

    no_click = run('no-fresh-click', events=tuple(e for e in events if e != ('mouse-button', '4000000:1')))
    assert all(s['state'] == 3 for s in no_click['checkpoints'] if s['requested'] >= 2400000)
    assert state(no_click['result']['memory'])['timeouts'] == 1
    no_key = run('no-fresh-key', events=tuple(e for e in events if e not in (
        ('key', f'7000000:{key}:1'), ('key', f'8000000:{key}:0'))))
    for s in no_key['checkpoints']:
        if s['requested'] >= (5100000 if native else 4800000):
            assert (s['state'], s['p1_x'], s['p1_held'], s['p1_mask'], s['p2_x']) == (2, 0x8000, 0, 0, 0xa800)
            assert (s['p2_held'], s['p2_mask']) == (0, 0)
            if native:
                assert not any(s['idle_gameplay']) and s['p1_velocity'] == s['p2_velocity'] == 0
    for control in (no_click, no_key):
        check_frame((out / (control['name'] + '.pbm')).read_bytes(), control['result']['memory'])

    # Sensitivity control: leave an accepted click armed, causing a held-button retry.
    # Only the test copy changes. Require the exact, unique original instruction.
    pattern = move_byte(0, ARMED) + bytes.fromhex('3039') + be32(X)
    assert image.count(pattern) == 1, 'ambiguous click-consumption mutation'
    mutant = out / 'held-click-mutant.rom'
    mutant.write_bytes(image.replace(pattern, move_byte(1, ARMED) + pattern[len(move_byte(0, ARMED)):]))
    bad = run('held-click-mutant', selected_rom=mutant)
    rejected = contract_errors({s['requested']: s for s in bad['checkpoints']}, args.player)
    assert any(e.startswith('held-click-at-') for e in rejected), 'held-click defect escaped oracle'
    mutations = {'held_click': {'rom_sha256': sha(mutant.read_bytes()), 'rejected': rejected}}
    if native:
        # Accepting the first queued make as the empty-queue reply leaves five
        # title-time keys to leak into gameplay. Mutate only the test ROM.
        pattern = bytes.fromhex('0c00007b66064ef9')
        assert image.count(pattern) == 1, 'ambiguous keyboard-drain mutation'
        mutant = out / 'short-drain-mutant.rom'
        mutant.write_bytes(image.replace(pattern, bytes.fromhex('0c00000166064ef9')))
        bad = run('short-drain-mutant', selected_rom=mutant)
        rejected = contract_errors({s['requested']: s for s in bad['checkpoints']}, args.player)
        assert any(e.startswith('stale-native-action-at-') for e in rejected), 'stale native action escaped oracle'
        stale_actions = [s['requested'] for s in bad['checkpoints']
                         if s['requested'] in (5100000, 5500000, 6500000) and any(s['idle_gameplay'])]
        assert stale_actions, 'short drain did not expose stale jump/attack state'
        mutations['short_drain'] = {'rom_sha256': sha(mutant.read_bytes()), 'rejected': rejected,
                                   'stale_jump_attack_checkpoints': stale_actions}
    assert sha(rom.read_bytes()) == identities['rom_sha256']
    assert sha(exe.read_bytes()) == identities['boothush_sha256']
    assert identities['components'] == {str(p): sha(p.read_bytes()) for p in components.values()}
    report = {'status': 'pass', 'identities': identities, 'runs': runs,
              'replay_trace_sha256': sha(trace.read_bytes()),
              'mutation': mutations['held_click'],  # retain the original report field
              'mutations': mutations,
              'limits': 'Bounded synthetic BootHush recovery and fresh-direction input on the identified unchanged title profile. No new aerial/combat behavior, physical/human mouse, complete-game or hardware qualification.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'pass', 'runs': len(runs), 'checkpoints_per_observed_run': len(captures),
                      'rom_sha256': identities['rom_sha256'], 'report': str(out / 'report.json')}))


if __name__ == '__main__':
    main()
