#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build the experimental title with native C movement and test it in BootHush."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_mac_movement import build
from test_mac_title import run as run_title, test
from test_mac_two_player import decode, pixels

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_player_two(exe, rom, out):
    frames, witness = out/'p2-trace.pbmseq', out/'p2-trace.keyboard'
    command = [str(exe), '--machine', 'mac128k', '--rom', str(rom), '--cycles', '8500000',
               '--timeout-ms', '20000', '--mouse-button', '2000000:1', '--mouse-button', '2400000:0',
               '--key', '3500000:4:1', '--key', '4500000:4:0',
               '--key', '5000000:5:1', '--key', '6000000:5:0',
               '--capture-series', str(frames), '--capture-memory', '0xb00:90',
               '--keyboard-witness', str(witness)]
    for frame in range(25, 57):
        command += ['--capture-vbl', str(frame)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=25,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    data = json.loads(result.stdout);series = data['frame_series'];key = data['keyboard_witness']
    if (data['status'] != 'cycle_limit' or
        (series['requested'], series['processed'], series['pending'], series['dropped']) != (32, 32, 0, 0) or
        (key['accepted'], key['rejected'], key['pending'], key['dropped']) != (4, 0, 0, 0)):
        raise ValueError('player-two capture or keyboard input incomplete')
    delivered = [(int(row[0]), int(row[3])) for line in witness.read_text(encoding='ascii').splitlines()[2:]
                 if (row := line.split()) and row[2] == 'key_delivered']
    if [value for _,value in delivered] != [9, 137, 11, 139]:
        raise ValueError('player-two keyboard replies differ')
    image = frames.read_bytes();states = []
    for sample in series['samples']:
        raw = bytes.fromhex(sample['memory']['bytes'])
        if len(raw) != 90 or raw[73] != 2:
            raise ValueError('player-two sample outside gameplay')
        state = decode({'memory': {'bytes': raw[:58].hex()}})
        state['p2velocity'] = int.from_bytes(raw[88:90], 'big', signed=True)
        pixels(image[sample['offset']:sample['offset']+sample['length']], state)
        states.append(state)
    checked = 0;right = left = coast = False
    for first, second, old, new in zip(series['samples'], series['samples'][1:], states, states[1:]):
        if any(first['cycle'] <= cycle < second['cycle'] for cycle, _ in delivered):
            continue
        if new['vbls'] != old['vbls'] + 1:
            raise ValueError('player-two VBL was not serviced')
        v, x = old['p2velocity'], old['p2x']
        if old['phase'] != 5 and old['p2attack_clock'] == 0:
            if old['p2held'] == 1:
                if v < 0x200: v += 0x40
                right = True
            elif old['p2held'] == 2:
                if v > -0x200: v -= 0x40
                left = True
            elif v > 0:
                v = max(0, v - 0x60);coast = True
            elif v < 0:
                v = min(0, v + 0x60);coast = True
            x = max(0x1000, min(0xe000, x + v))
        if (new['p2x'], new['p2velocity']) != (x, v):
            raise ValueError('player-two motion mismatch: '+str((old, new, x, v)))
        checked += 1
    if checked < 20 or not (right and left and coast):
        raise ValueError('player-two trace lacks movement coverage')
    record = {'command': command, 'result': data, 'delivered': delivered,
              'checked_intervals': checked, 'right': right, 'left': left, 'coast': coast,
              'frames_sha256': sha(frames), 'witness_sha256': sha(witness)}
    (out/'p2-trace.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record


def check_overlapping_player_two(exe, rom, out):
    frames = out/'p2-overlap.pbmseq'
    command = [str(exe), '--machine', 'mac128k', '--rom', str(rom), '--cycles', '7000000',
               '--timeout-ms', '20000', '--mouse-button', '2000000:1', '--mouse-button', '2400000:0',
               '--key', '3400000:4:1', '--key', '3900000:5:1', '--key', '4400000:5:0',
               '--key', '4900000:4:0', '--capture-series', str(frames), '--capture-memory', '0xb00:90']
    for cycle in (3700000, 4200000, 4700000, 5800000):
        command += ['--capture-cycle', str(cycle)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=25,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    data = json.loads(result.stdout);series = data['frame_series']
    if data['status'] != 'cycle_limit' or (series['processed'], series['pending'], series['dropped']) != (4, 0, 0):
        raise ValueError('overlap capture incomplete')
    observed = []
    for sample in series['samples']:
        raw = bytes.fromhex(sample['memory']['bytes'])
        if len(raw) != 90 or raw[73] != 2:
            raise ValueError('overlap sample outside gameplay')
        state = decode({'memory': {'bytes': raw[:58].hex()}})
        # Cycle captures may interrupt an in-progress redraw; the VBL trace
        # separately verifies complete frames against the pixel oracle.
        observed.append((state['p2held'], state['p2mask'], int.from_bytes(raw[88:90], 'big', signed=True)))
    if ([(held,mask) for held,mask,_ in observed] != [(1,1),(2,3),(1,1),(0,0)] or
        observed[0][2] <= 0 or observed[1][2] >= 0 or observed[2][2] <= 0 or observed[3][2] != 0):
        raise ValueError('overlapping player-two keys or friction failed: '+str(observed))
    record = {'command': command, 'result': data, 'observed': observed, 'frames_sha256': sha(frames)}
    (out/'p2-overlap.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tool-bin', required=True, type=Path)
    p.add_argument('--boothush', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--native-p2', action='store_true', help='also use native movement for player two')
    a = p.parse_args()
    tools = a.tool_bin.resolve(strict=True)
    exe = a.boothush.resolve(strict=True)
    out = a.output.resolve()
    if out == ROOT or ROOT in out.parents:
        raise ValueError('output must be outside the repository')
    gcc, nm, objcopy = (tools / ('m68k-unknown-elf-' + name + '.exe') for name in ('gcc', 'nm', 'objcopy'))
    inputs = [ROOT/'guest/sinbad_movement.c', ROOT/'guest/sinbad_movement.h',
              *(ROOT/'scripts'/name for name in ('build_mac_movement.py', 'build_mac_probe.py',
                 'build_mac_run_transition.py', 'build_mac_title.py', 'test_mac_title.py',
                 'test_mac_two_player.py')), Path(__file__)]
    input_hashes = {str(f.relative_to(ROOT)).replace('\\', '/'): sha(f) for f in inputs}
    tool_hashes = {f.name: sha(f) for f in (gcc, nm, objcopy)}
    emulator_sha = sha(exe)
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['PATH'] = str(tools) + os.pathsep + env.get('PATH', '')
    commands = []

    def run(command, log):
        command = [str(x) for x in command]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, env=env,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        log.write_text(result.stdout + '\n--- stderr ---\n' + result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError('command failed; see ' + str(log))
        commands.append(command)
        return result.stdout

    binaries = []
    for name in ('a', 'b'):
        folder = out/name
        folder.mkdir()
        obj, elf, binary = folder/'movement.o', folder/'movement.elf', folder/'movement.bin'
        run([gcc, '-mcpu=68000', '-Wa,-m68000', '-std=c11', '-Os', '-ffreestanding', '-fno-builtin',
             '-fno-pic', '-fno-pie', '-fno-stack-protector', '-fno-unwind-tables',
             '-fno-asynchronous-unwind-tables', '-Wall', '-Wextra', '-Werror', '-c', inputs[0], '-o', obj], folder/'compile.log')
        run([gcc, '-mcpu=68000', '-nostdlib', '-no-pie', '-Wl,--build-id=none',
             '-Wl,-Ttext=0x40e000', '-Wl,--entry=sinbad_movement_step', '-Wl,-Map,'+str(folder/'movement.map'),
             obj, '-o', elf], folder/'link.log')
        if run([nm, '--undefined-only', elf], folder/'undefined.log').strip():
            raise ValueError('unexpected undefined symbols')
        symbols = run([nm, '--defined-only', '--format=posix', elf], folder/'symbols.log')
        if not any(line.split()[:3] == ['sinbad_movement_step', 'T', '40e000'] for line in symbols.splitlines()):
            raise ValueError('movement entry address mismatch')
        run([objcopy, '-O', 'binary', elf, binary], folder/'objcopy.log')
        binaries.append(binary.read_bytes())
    if binaries[0] != binaries[1]:
        raise ValueError('native movement builds differ')
    test_dir = out/'title-test'
    test_dir.mkdir()
    test(exe, test_dir, binaries[0], a.native_p2)
    summary = json.loads((test_dir/'summary.json').read_text(encoding='utf-8'))
    # This mutation must change a keyboard-driven gameplay result, proving that
    # the live title's movement path calls the native component.
    needle = bytes.fromhex('06400040')
    if binaries[0].count(needle) != 1:
        raise ValueError('component mutation site changed')
    mutant_component = binaries[0].replace(needle, bytes.fromhex('06400020'), 1)
    mutant_image, _ = build(jumping=True, combat=True, two_player=True, title=True,
                            native_movement=mutant_component, native_p2=a.native_p2)
    mutant = out/'mutated-title.rom'
    mutant.write_bytes(mutant_image)
    events = [('mouse-button','2000000:1'), ('mouse-button','2400000:0'),
              ('key','3500000:0:1'), ('key','4500000:0:0')]
    changed = run_title(exe, mutant, out, 'mutated-play-keys', events)
    if changed['state'] != 2 or changed['game_x'] == summary['cases']['play_keys']['game_x']:
        raise ValueError('native acceleration mutation did not affect live movement')
    p2_trace = None
    p2_mutation = None;overlap = None;simultaneous = None
    if a.native_p2:
        p2_trace = check_player_two(exe, test_dir/'title.rom', out)
        overlap = check_overlapping_player_two(exe, test_dir/'title.rom', out)
        p2_events = [('mouse-button','2000000:1'), ('mouse-button','2400000:0'),
                     ('key','3500000:4:1'), ('key','4500000:4:0')]
        expected_p2 = run_title(exe, test_dir/'title.rom', out, 'p2-control', p2_events)
        damaged_p2 = run_title(exe, mutant, out, 'p2-mutant', p2_events)
        if expected_p2['state'] != 2 or damaged_p2['state'] != 2 or expected_p2['p2x'] == damaged_p2['p2x']:
            raise ValueError('native mutation did not affect player-two movement')
        p2_mutation = {'control': expected_p2['p2x'], 'mutated': damaged_p2['p2x']}
        simultaneous = run_title(exe, test_dir/'title.rom', out, 'simultaneous-move',
            [('mouse-button','2000000:1'), ('mouse-button','2400000:0'),
             ('key','3500000:0:1'), ('key','3600000:4:1'),
             ('key','4500000:0:0'), ('key','4600000:4:0')])
        if simultaneous['state'] != 2 or simultaneous['game_x'] <= 0x8000 or simultaneous['p2x'] <= 0xa800:
            raise ValueError('simultaneous two-player movement failed')
    # Compare acceleration, release and reverse against the existing emitter
    # at the same modeled checkpoints, using a separately generated ROM.
    legacy_image, _ = build(jumping=True, combat=True, two_player=True, title=True)
    legacy = out/'legacy-title.rom'
    legacy.write_bytes(legacy_image)
    observations = []
    for name, image in (('legacy', legacy), ('native', test_dir/'title.rom')):
        cmd = [exe, '--machine', 'mac128k', '--rom', image, '--cycles', '8000000', '--timeout-ms', '20000',
               '--mouse-button', '2000000:1', '--mouse-button', '2400000:0',
               '--key', '3500000:0:1', '--key', '4500000:0:0',
               '--key', '5000000:1:1', '--key', '6000000:1:0',
               '--capture-memory', '0xb00:24', '--capture-series', out/(name+'-comparison.pbmseq')]
        for cycle in (3400000, 4000000, 4700000, 5400000, 6200000, 7500000):
            cmd += ['--capture-cycle', str(cycle)]
        result = json.loads(run(cmd, out/(name+'-comparison.log')))
        series = result['frame_series']
        if result['status'] != 'cycle_limit' or (series['processed'], series['pending'], series['dropped']) != (6, 0, 0):
            raise ValueError('comparison capture incomplete')
        observations.append([bytes.fromhex(row['memory']['bytes'])[8:22].hex() for row in series['samples']])
    if observations[0] != observations[1]:
        raise ValueError('native/legacy movement checkpoints differ: '+str(observations))
    if input_hashes != {str(f.relative_to(ROOT)).replace('\\', '/'): sha(f) for f in inputs}:
        raise ValueError('source changed during run')
    if tool_hashes != {f.name: sha(f) for f in (gcc, nm, objcopy)} or sha(exe) != emulator_sha:
        raise ValueError('tool changed during run')
    report = {'status': 'pass', 'source_sha256': input_hashes, 'tool_sha256': tool_hashes,
              'boothush_sha256': emulator_sha, 'build_commands': commands,
              'component_sha256': hashlib.sha256(binaries[0]).hexdigest(), 'component_bytes': len(binaries[0]),
              'title_summary': summary, 'mutation': {'rom_sha256': sha(mutant), 'observed': changed},
              'player_two_trace': p2_trace, 'player_two_mutation': p2_mutation,
              'player_two_overlap': overlap, 'simultaneous_movement': simultaneous,
              'legacy_comparison': {'rom_sha256': sha(legacy), 'movement_checkpoints': observations[0]},
              'native_p2': a.native_p2,
              'limits': 'Experimental source-informed movement, modeled input; not physical or a complete game.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
