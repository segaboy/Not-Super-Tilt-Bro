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

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tool-bin', required=True, type=Path)
    p.add_argument('--boothush', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
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
    test(exe, test_dir, binaries[0])
    summary = json.loads((test_dir/'summary.json').read_text(encoding='utf-8'))
    # This mutation must change a keyboard-driven gameplay result, proving that
    # the live title's movement path calls the native component.
    needle = bytes.fromhex('06400040')
    if binaries[0].count(needle) != 1:
        raise ValueError('component mutation site changed')
    mutant_component = binaries[0].replace(needle, bytes.fromhex('06400020'), 1)
    mutant_image, _ = build(jumping=True, combat=True, two_player=True, title=True,
                            native_movement=mutant_component)
    mutant = out/'mutated-title.rom'
    mutant.write_bytes(mutant_image)
    events = [('mouse-button','2000000:1'), ('mouse-button','2400000:0'),
              ('key','3500000:0:1'), ('key','4500000:0:0')]
    changed = run_title(exe, mutant, out, 'mutated-play-keys', events)
    if changed['state'] != 2 or changed['game_x'] == summary['cases']['play_keys']['game_x']:
        raise ValueError('native acceleration mutation did not affect live movement')
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
              'legacy_comparison': {'rom_sha256': sha(legacy), 'movement_checkpoints': observations[0]},
              'limits': 'Experimental source-informed player-one movement, modeled input; not physical or a complete game.'}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
