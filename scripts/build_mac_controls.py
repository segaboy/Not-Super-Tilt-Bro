#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Original three-position Mac input probe. Not yet Super Tilt Bro gameplay."""
import argparse
import hashlib
from pathlib import Path
from build_mac_probe import ROM_BASE, ENTRY, SCREEN, SCREEN_BYTES, DIAG, be16, be32, move_byte, move_long

# Original geometric placeholder art; 16 pixels wide by 24 pixels high.
FIGURE = (0x03c0,0x07e0,0x07e0,0x03c0,0x0180,0x07e0,0x0ff0,0x1db8,
          0x1998,0x1998,0x0180,0x03c0,0x03c0,0x0660,0x0660,0x0c30,
          0x0c30,0x1818,0x1818,0x1818,0x381c,0x381c,0,0)

class Emitter:
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.patches = []
    def put(self, data):
        self.code.extend(data)
    def label(self, name):
        if name in self.labels:
            raise ValueError("duplicate label "+name)
        self.labels[name] = ROM_BASE + ENTRY + len(self.code)
    def jump(self, name):
        self.put(bytes.fromhex("4ef9"))
        self.patches.append((len(self.code),name))
        self.put(bytes(4))
    def if_d0(self, value, target):
        # CMPI.B #imm,D0; BNE.S +6; JMP absolute-long.
        self.put(bytes.fromhex("0c00") + be16(value) + bytes.fromhex("6606"))
        self.jump(target)
    def if_pos(self, value, target):
        # CMPI.B #imm,(absolute long); BNE.S +6; JMP absolute-long.
        self.put(bytes.fromhex("0c39") + be16(value) + be32(DIAG+8) + bytes.fromhex("6606"))
        self.jump(target)
    def finish(self):
        for at,name in self.patches:
            if name not in self.labels:
                raise ValueError("missing label "+name)
            self.code[at:at+4] = be32(self.labels[name])
        return self.code

def build():
    e = Emitter()
    # Adapted from ClasSICK 0.97 arch/m68k/mac-reset.S at 5d99706.
    e.put(bytes.fromhex("46fc2700 13fc004800effffe 13fc005800efe7fe "
                        "41f900400000 93c9 703f 22d8 51c8fffc"))
    e.put(bytes.fromhex("41f9")+be32(SCREEN)+bytes.fromhex("303c")+be16(SCREEN_BYTES-1)
          +bytes.fromhex("4218 51c8fffc"))
    for y in range(252,260):
        for x in range(16,48):
            e.put(move_byte(0xff, SCREEN+y*64+x))
    for row,bits in enumerate(FIGURE):
        for byte_x,value in ((25,bits >> 8),(26,bits & 255),
                             (37,bits >> 8),(38,bits & 255)):
            e.put(move_byte(value,SCREEN+(228+row)*64+byte_x))
    e.put(move_long(0x4e535432,DIAG))  # NST2
    e.put(move_byte(1,DIAG+8))          # position 0, 1, or 2
    for offset in (9,10,11):
        e.put(move_byte(0,DIAG+offset))  # last reply, presses, releases
    e.put(move_long(1,DIAG+4))          # ready

    e.label("keyboard")
    e.put(move_byte(0x1c,0xeff7fe)+move_byte(0x14,0xeff5fe))
    e.put(bytes.fromhex("0839000200effbfe 67f6 103900eff5fe"))
    e.put(move_byte(0x0c,0xeff7fe))
    e.put(bytes.fromhex("0839000200effbfe 67f6 103900eff5fe"))
    e.if_d0(1,"right")     # M0110 position 0, press
    e.if_d0(3,"left")      # M0110 position 1, press
    e.if_d0(0x81,"release")
    e.if_d0(0x83,"release")
    e.jump("keyboard")
    for name, replies in (("right",((0,"draw1"),(1,"draw2"),(2,"draw2"))),
                          ("left",((0,"draw0"),(1,"draw0"),(2,"draw1")))):
        e.label(name)
        e.put(bytes.fromhex("13c0")+be32(DIAG+9))    # last recognized reply
        e.put(bytes.fromhex("5239")+be32(DIAG+10))   # addq.b #1, press count
        for value,target in replies:
            e.if_pos(value,target)
        e.jump("fault")  # corrupted position
    e.label("release")
    e.put(bytes.fromhex("13c0")+be32(DIAG+9))
    e.put(bytes.fromhex("5239")+be32(DIAG+11))
    e.jump("keyboard")
    for position in range(3):
        e.label("draw"+str(position))
        for row,bits in enumerate(FIGURE):
            y = 228+row
            for x in range(24,28):
                e.put(move_byte(0,SCREEN+y*64+x))
            e.put(move_byte(bits>>8,SCREEN+y*64+24+position))
            e.put(move_byte(bits&255,SCREEN+y*64+25+position))
        e.put(move_byte(position,DIAG+8))
        e.jump("keyboard")
    e.label("fault")
    e.put(bytes.fromhex("60fe"))
    code = e.finish()
    if ENTRY+len(code) > 65536:
        raise ValueError("ROM overflow")
    rom = bytearray(65536)
    rom[0:4],rom[4:8] = be32(0x4000),be32(ROM_BASE+ENTRY)
    for vector in range(2,64):
        rom[vector*4:vector*4+4] = be32(e.labels["fault"])
    rom[ENTRY:ENTRY+len(code)] = code
    return bytes(rom),len(code)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    a = p.parse_args()
    rom,size = build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb") as f:
        f.write(rom)
    print(f"ROM sha256={hashlib.sha256(rom).hexdigest()} image_bytes={len(rom)} code_bytes={size} used_through={ENTRY+size}")

if __name__ == "__main__":
    main()
