#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build a tiny, original Mac 128K arena display probe without a cross compiler.

The reset sequence through vector relocation is adapted from ClasSICK 0.97
arch/m68k/mac-reset.S at 5d99706; see docs/provenance.md. This deliberately
small emitter writes only the listed, fixed 68000 encodings. It is not a
general assembler and the result is a display probe, not a playable game.
"""
import argparse
import hashlib
import struct
from pathlib import Path

ROM_BASE = 0x400000
ENTRY = 0x104
SCREEN = 0x1A700
SCREEN_BYTES = 512 * 342 // 8
DIAG = 0xB00

def be16(n):
    return struct.pack(">H", n)

def be32(n):
    return struct.pack(">I", n)

def move_byte(value, address):
    # MOVE.B #imm,(absolute long)
    return bytes.fromhex("13fc") + be16(value) + be32(address)

def move_long(value, address):
    # MOVE.L #imm,(absolute long)
    return bytes.fromhex("23fc") + be32(value) + be32(address)

def build():
    code = bytearray()
    # Adapted from the cited ClasSICK startup: mask interrupts, program VIA,
    # and copy the first 64 exception vectors to low RAM after overlay removal.
    code += bytes.fromhex(
        "46fc2700 13fc004800effffe 13fc005800efe7fe "
        "41f900400000 93c9 703f 22d8 51c8fffc"
    )
    # LEA framebuffer,A0; MOVE.W #21887,D0; CLR.B (A0)+; DBRA D0,-4.
    code += bytes.fromhex("41f9") + be32(SCREEN)
    code += bytes.fromhex("303c") + be16(SCREEN_BYTES - 1)
    code += bytes.fromhex("4218 51c8fffc")
    # Original geometric test art, not copied from the game.
    # A platform and two distinct blocky 16x24 fighter silhouettes.
    for y in range(252, 260):
        for byte_x in range(16, 48):
            code += move_byte(0xff, SCREEN + y * 64 + byte_x)
    fighter = [
        0x03c0,0x07e0,0x07e0,0x03c0,
        0x0180,0x07e0,0x0ff0,0x1db8,0x1998,0x1998,0x0180,0x03c0,
        0x03c0,0x0660,0x0660,0x0c30,0x0c30,0x1818,0x1818,0x1818,
        0x381c,0x381c,0x0000,0x0000,
    ]
    for x_byte, mirrored in ((25, False), (37, True)):
        for row, bits in enumerate(fighter):
            if mirrored:
                bits = int(f"{bits:016b}"[::-1], 2)
            for shift, offset in ((8, 0), (0, 1)):
                code += move_byte((bits >> shift) & 0xff, SCREEN + (228 + row) * 64 + x_byte + offset)
    # Set signature and readiness only after all pixels have been written.
    code += move_long(0x4e535442, DIAG)       # 'NSTB'
    code += move_long(1, DIAG + 4)
    # Poll the keyboard's instant command through the VIA shift register.
    # A scheduled M0110 position 0 press returns 0x01. This is a single-key
    # diagnostic, not a complete keyboard driver or a game input system.
    keyboard_loop = ROM_BASE + ENTRY + len(code)
    code += move_byte(0x1c, 0xEFF7FE)         # external-clock shift out
    code += move_byte(0x14, 0xEFF5FE)         # keyboard instant command
    code += bytes.fromhex("0839000200effbfe 67f6")  # wait for shift flag
    code += bytes.fromhex("103900eff5fe")      # acknowledge shift-out
    code += move_byte(0x0c, 0xEFF7FE)         # external-clock shift in
    code += bytes.fromhex("0839000200effbfe 67f6")
    code += bytes.fromhex("103900eff5fe")      # read reply
    code += bytes.fromhex("0c000001 6706")     # CMPI.B #1,D0; BEQ move
    code += bytes.fromhex("4ef9") + be32(keyboard_loop)
    # On the one tested key, move the first silhouette eight pixels right.
    # Clear three bytes on each row then redraw the original geometry.
    for row, bits in enumerate(fighter):
        for byte_x in (25, 26, 27):
            code += move_byte(0, SCREEN + (228 + row) * 64 + byte_x)
        code += move_byte((bits >> 8) & 0xff, SCREEN + (228 + row) * 64 + 26)
        code += move_byte(bits & 0xff, SCREEN + (228 + row) * 64 + 27)
    code += move_long(2, DIAG + 4)
    fault_offset = ENTRY + len(code)
    code += bytes.fromhex("60fe")             # BRA.S to self
    if ENTRY + len(code) > 65536:
        raise ValueError("ROM overflow")
    image = bytearray(65536)
    image[0:4] = be32(0x4000)
    image[4:8] = be32(ROM_BASE + ENTRY)
    for vector in range(2, 64):
        image[vector * 4:vector * 4 + 4] = be32(ROM_BASE + fault_offset)
    image[ENTRY:ENTRY + len(code)] = code
    return bytes(image), len(code)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path, help="new 65536-byte ROM path")
    args = p.parse_args()
    image, code_size = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as f:
        f.write(image)
    print(f"ROM sha256={hashlib.sha256(image).hexdigest()} image_bytes={len(image)} "
          f"code_bytes={code_size} used_through={ENTRY + code_size}")

if __name__ == "__main__":
    main()
