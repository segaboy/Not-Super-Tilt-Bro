#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Execute every title Gray-phase pair at coordinate boundaries in BootHush.

The oracle describes the original adapter's existing mathematical contract;
it is not a hardware quadrature or physical timing qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from build_mac_movement import Asm
from build_mac_probe import ROM_BASE, ENTRY, be32, move_byte, move_long
from build_mac_title import emit_axis, XP, XN, X, DIRTY

RESULTS = 0x5000
DONE = 0x4ff0


def fixture():
    e = Asm()
    # Existing original startup; no firmware is supplied to the emulator.
    e.put(bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe '
                        '41f900400000 93c9 703f 22d8 51c8fffc'))
    cases = []
    gray = (0, 1, 3, 2)
    expected = bytearray()
    for reverse, maximum in ((False, 506), (True, 334)):
        for previous in range(4):
            for current in range(4):
                for position in (0, 1, maximum // 2, maximum - 1, maximum):
                    name = 'case_' + str(len(cases))
                    e.put(move_byte(previous, XP) + move_byte(current, XN)
                          + move_byte(0, DIRTY))
                    e.setword(position, X)
                    emit_axis(e, name, XP, XN, X, maximum, reverse)
                    dest = RESULTS + 4 * len(cases)
                    e.word('3039', X); e.word('33c0', dest)
                    e.put(bytes.fromhex('13f9') + be32(DIRTY) + be32(dest + 2))
                    e.put(bytes.fromhex('13f9') + be32(XP) + be32(dest + 3))
                    # Only an adjacent change of DCD (phase bit 0) emits a pixel.
                    step = (gray.index(current) - gray.index(previous)) % 4
                    delta = (1 if step == 1 else -1 if step == 3 else 0)
                    if (previous ^ current) != 1:
                        delta = 0
                    if reverse:
                        delta = -delta
                    after = min(maximum, max(0, position + delta))
                    expected.extend(after.to_bytes(2, 'big')
                                    + bytes((int(after != position), current)))
                    cases.append([previous, current, position, maximum, reverse])
    e.put(move_long(0x41584953, DONE))  # AXIS: only reached after every case
    e.label('done'); e.jump('done')
    e.label('fault'); e.jump('fault')
    code = e.finish()
    if ENTRY + len(code) > 65536:
        raise ValueError('fixture overflow')
    rom = bytearray(65536)
    rom[:4] = be32(0x4000)
    rom[4:8] = be32(ROM_BASE + ENTRY)
    for vector in range(2, 64):
        rom[vector * 4:vector * 4 + 4] = be32(e.labels['fault'])
    rom[ENTRY:ENTRY + len(code)] = code
    # Deliberately corrupt the +1 transition in the first 0->1 test's table.
    mutation = bytearray(rom)
    mutation[e.labels['case_5_table'] - ROM_BASE + 1] = 255
    return bytes(rom), bytes(mutation), bytes(expected), cases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--boothush', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rom, mutation, expected, cases = fixture()
    records = []
    for name, image in (('axis', rom), ('wrong-sign', mutation)):
        path = args.output / (name + '.rom'); path.write_bytes(image)
        cmd = [str(args.boothush), '--machine', 'mac128k', '--rom', str(path),
               '--cycles', '1000000', '--timeout-ms', '20000',
               '--inspect', f'{DONE}:{RESULTS - DONE + len(expected)}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        data = json.loads(result.stdout)
        raw = bytes.fromhex(data['memory']['bytes'])
        assert raw[:4] == b'AXIS', (name, 'fixture did not complete')
        actual = raw[RESULTS - DONE:]
        mismatches = [i for i in range(len(cases))
                      if actual[4*i:4*i+4] != expected[4*i:4*i+4]]
        assert mismatches == ([] if name == 'axis' else [5]), (name, mismatches)
        records.append({'name': name, 'command': cmd, 'result': data,
                        'rom_sha256': hashlib.sha256(image).hexdigest(),
                        'mismatches': mismatches})
    report = {'emulator_sha256': hashlib.sha256(args.boothush.read_bytes()).hexdigest(),
              'cases': cases, 'expected_hex': expected.hex(), 'runs': records}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'{len(cases)} phase/boundary cases passed; wrong-sign mutation detected')


if __name__ == '__main__':
    main()
