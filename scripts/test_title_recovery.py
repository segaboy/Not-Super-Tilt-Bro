#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Headless failed-drain, fresh-click and fresh-key recovery checks in BootHush.

Uses the existing original title ROM unchanged. All input is scheduled in the
emulator; this is not physical or human input qualification.
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
    if len(b) != 86:
        raise ValueError('incomplete diagnostic memory')
    word = lambda at: int.from_bytes(b[at:at+2], 'big')
    return {'state': b[73], 'armed': b[72], 'timeouts': word(22),
            'p1_x': word(16), 'p2_x': word(38), 'p1_held': b[8],
            'p1_mask': b[21], 'p2_held': b[40], 'p2_mask': b[41]}


def contract_errors(samples):
    """Behavioral checkpoints: failed clicks need rearming; old keys do not play."""
    errors = []
    for at in (2400000, 2800000, 3500000):
        s = samples[at]
        if (s['state'], s['armed'], s['timeouts']) != (3, 0, 1):
            errors.append('held-click-at-' + str(at))
    if (samples[3900000]['state'], samples[3900000]['armed']) != (3, 1):
        errors.append('released-click-before-retry')
    for at in (4800000, 5500000, 6500000):
        s = samples[at]
        if (s['state'], s['p1_x'], s['p1_held'], s['p1_mask'],
                s['p2_x'], s['p2_held'], s['p2_mask'], s['timeouts']) != (
                2, 0x8000, 0, 0, 0xa800, 0, 0, 0):
            errors.append('stale-key-at-' + str(at))
    for at in (7500000, 8500000, 9500000):
        s = samples[at]
        if s['state'] != 2 or s['p1_x'] <= 0x8000 or s['p2_x'] != 0xa800:
            errors.append('fresh-key-at-' + str(at))
        expected_held = 1 if at == 7500000 else 0
        if (s['p1_held'], s['p1_mask'], s['p2_held'], s['p2_mask']) != (
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
    args = parser.parse_args()
    exe = args.boothush.resolve(strict=True)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    image, used = build(jumping=True, combat=True, two_player=True, title=True)
    rom = out / 'title.rom'
    rom.write_bytes(image)
    identities = {'rom_sha256': sha(image), 'boothush_sha256': sha(exe.read_bytes()),
                  'script_sha256': sha(Path(__file__).read_bytes()),
                  'rom_used_through': used + 0x104,
                  'sources': {p.name: sha(p.read_bytes()) for p in
                              Path(__file__).parent.glob('*.py')}}
    trace = out / 'recovery.bhmouse'
    runs = []

    def run(name, events=EVENTS, mode=None, observed=True, selected_rom=rom):
        final = out / (name + '.pbm')
        frames = out / (name + '.pbmseq')
        witness = out / (name + '.keyboard')
        cmd = [str(exe), '--machine', 'mac128k', '--rom', str(selected_rom),
               '--cycles', '10000000', '--timeout-ms', '20000',
               '--keyboard-fault', '0x14:1:1:0', '--inspect', '0xb00:86',
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
            cmd += ['--capture-memory', '0xb00:86', '--capture-series', str(frames),
                    '--keyboard-witness', str(witness)]
            for cycle in CAPTURES:
                cmd += ['--capture-cycle', str(cycle)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (out / (name + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name + ': ' + result.stdout + result.stderr)
        data = json.loads(result.stdout)
        assert data['status'] == 'cycle_limit' and data['mouse']['pending'] == 0
        assert data['keyboard_fault']['triggered']
        snapshots = []
        if observed:
            series = data['frame_series']
            assert (series['requested'], series['processed'], series['pending'],
                    series['missing_images'], series['dropped']) == (len(CAPTURES), len(CAPTURES), 0, 0, 0)
            assert series['rom_sha256'] == sha(selected_rom.read_bytes())
            assert series['executable_sha256'] == identities['boothush_sha256']
            witness_state = data['keyboard_witness']
            count = sum(kind == 'key' for kind, _ in events)
            assert (witness_state['scheduled'], witness_state['accepted'],
                    witness_state['pending'], witness_state['rejected'],
                    witness_state['dropped']) == (count, count, 0, 0, 0)
            assert all(event['accepted'] for event in data['series_inputs']['events'])
            assert tuple(sample['requested'] for sample in series['samples']) == CAPTURES
            assert tuple(sample['target'] for sample in series['samples']) == CAPTURES
            for point, sample in zip(CAPTURES, series['samples']):
                assert point <= sample['cycle'] < point + 100, 'capture missed its boundary'
                assert sample['processed'] and sample['image_available']
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
        assert not contract_errors(samples), contract_errors(samples)
        data = candidate['result']
        raw = (out / (candidate['name'] + '.pbmseq')).read_bytes()
        for sample in data['frame_series']['samples']:
            check_frame(raw[sample['offset']:sample['offset']+sample['length']], sample['memory'])
        rows = [line.split() for line in (out / (candidate['name'] + '.keyboard')).read_text(encoding='ascii').splitlines()[2:]]
        delivered = [(int(row[0]), int(row[3])) for row in rows if row[2] == 'key_delivered']
        assert [value for _, value in delivered] == [1, 129, 1, 129]
        assert 4000000 < delivered[0][0] < 4800000
        assert 6000000 < delivered[1][0] < 6500000
        assert 7000000 < delivered[2][0] < 7500000
        assert 8000000 < delivered[3][0] < 8500000
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

    no_click = run('no-fresh-click', events=tuple(e for e in EVENTS if e != ('mouse-button', '4000000:1')))
    assert all(s['state'] == 3 for s in no_click['checkpoints'] if s['requested'] >= 2400000)
    assert state(no_click['result']['memory'])['timeouts'] == 1
    no_key = run('no-fresh-key', events=tuple(e for e in EVENTS if e not in (
        ('key', '7000000:0:1'), ('key', '8000000:0:0'))))
    for s in no_key['checkpoints']:
        if s['requested'] >= 4800000:
            assert (s['state'], s['p1_x'], s['p1_held'], s['p1_mask'], s['p2_x']) == (2, 0x8000, 0, 0, 0xa800)
    for control in (no_click, no_key):
        check_frame((out / (control['name'] + '.pbm')).read_bytes(), control['result']['memory'])

    # Sensitivity control: leave an accepted click armed, causing a held-button retry.
    # Only the test copy changes. Require the exact, unique original instruction.
    pattern = move_byte(0, ARMED) + bytes.fromhex('3039') + be32(X)
    assert image.count(pattern) == 1, 'ambiguous click-consumption mutation'
    mutant = out / 'held-click-mutant.rom'
    mutant.write_bytes(image.replace(pattern, move_byte(1, ARMED) + pattern[len(move_byte(0, ARMED)):]))
    bad = run('held-click-mutant', selected_rom=mutant)
    rejected = contract_errors({s['requested']: s for s in bad['checkpoints']})
    assert any(e.startswith('held-click-at-') for e in rejected), 'held-click defect escaped oracle'
    assert sha(rom.read_bytes()) == identities['rom_sha256']
    assert sha(exe.read_bytes()) == identities['boothush_sha256']
    report = {'status': 'pass', 'identities': identities, 'runs': runs,
              'replay_trace_sha256': sha(trace.read_bytes()),
              'mutation': {'rom_sha256': sha(mutant.read_bytes()), 'rejected': rejected},
              'limits': 'Bounded synthetic BootHush input on the existing emitter title ROM. No physical/human mouse, native-jab title, complete-game or hardware qualification.'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'pass', 'runs': len(runs), 'checkpoints_per_observed_run': len(CAPTURES),
                      'rom_sha256': identities['rom_sha256'], 'report': str(out / 'report.json')}))


if __name__ == '__main__':
    main()
