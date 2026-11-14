#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build a VBL-paced, source-derived horizontal movement experiment.

The rendering, input adapter and 5/6 pacing are independently authored;
the run velocity and grounded friction constants come from the Sinbad source.
See docs/movement-evidence.md for scope, provenance and caveats.
"""
import argparse
import hashlib
import struct
from pathlib import Path
from build_mac_probe import ROM_BASE, ENTRY, SCREEN, SCREEN_BYTES, DIAG, be16, be32, move_byte, move_long
from build_mac_run_transition import Emitter, FIGURE

IFR = 0xeffbfe
HELD, REPLY, ENTRY_COUNT, TICKS, VEL, POS, VBLS, PHASE, TIMEOUTS = [DIAG+x for x in (8,9,10,12,14,16,18,20,22)]
HELD_MASK = DIAG + 21  # original experiment's right/left modeled-key bitmap

class Asm(Emitter):
    def cond(self, inverse, target):
        # An inverse short branch skips an absolute JMP when condition is false.
        self.put(bytes((inverse, 6)))
        self.jump(target)
    def word(self, hexop, addr):
        self.put(bytes.fromhex(hexop)+be32(addr))
    def cmpw(self, value):
        self.put(bytes.fromhex('0c40')+be16(value & 0xffff))
    def setword(self, value, addr):
        self.put(bytes.fromhex('33fc')+be16(value & 0xffff)+be32(addr))

def sprite_address(e, addr):
    # A0 = first row + left margin + (position's integer pixel / 8).
    e.word('3039',addr)                 # MOVE.W absolute,D0
    e.put(bytes.fromhex('e048 e648'))  # LSR.W #8,D0; LSR.W #3,D0
    e.put(bytes.fromhex('41f9')+be32(SCREEN+228*64+16))
    e.put(bytes.fromhex('d0c0'))       # ADDA.W D0,A0

def wait_shift(e, name):
    # Bounded polling prevents a missing modeled keyboard reply from hanging
    # the game forever. The threshold is a prototype, not physical timing.
    e.put(bytes.fromhex('323c1000'))  # MOVE.W #4096,D1
    e.label(name+'_poll')
    e.put(bytes.fromhex('08390002')+be32(IFR))
    e.cond(0x67,name+'_done')         # BNE: shift transfer complete
    here=ROM_BASE+ENTRY+len(e.code)
    offset=e.labels[name+'_poll']-(here+2)  # DBRA base is extension word
    e.put(bytes.fromhex('51c9')+struct.pack('>h',offset))
    e.word('5279',TIMEOUTS)
    e.put(move_byte(0,0xeff7fe))      # reset shift mode before a fresh command
    e.jump('wait_vbl')
    e.label(name+'_done')
    e.put(bytes.fromhex('103900eff5fe'))

def build():
    e=Asm()
    e.put(bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe '
                        '41f900400000 93c9 703f 22d8 51c8fffc'))
    e.put(bytes.fromhex('41f9')+be32(SCREEN)+bytes.fromhex('303c')+be16(SCREEN_BYTES-1)
          +bytes.fromhex('4218 51c8fffc'))
    # Stage is original geometric art. All moving art occupies rows 228..251.
    for y in range(252,260):
        for x in range(16,48):
            e.put(move_byte(0xff,SCREEN+y*64+x))
    for off in range(8,24):
        e.put(move_byte(0,DIAG+off))
    e.setword(0x8000,POS)   # 128 pixels from the left edge of the movement area
    e.put(move_long(0x4e535434,DIAG)) # NST4
    e.put(move_long(1,DIAG+4))
    e.jump('draw')

    e.label('wait_vbl')
    e.put(bytes.fromhex('08390001')+be32(IFR)) # BTST #1,IFR
    e.cond(0x67,'vbl')  # BNE vbl
    e.jump('wait_vbl')
    e.label('vbl')
    e.put(move_byte(2,IFR))
    e.word('5279',VBLS) # ADDQ.W #1, absolute
    # Keyboard instant command with a bounded polling timeout. Each modeled
    # reply can consume time; this is not a physical keyboard claim.
    e.put(move_byte(0x1c,0xeff7fe)+move_byte(0x14,0xeff5fe))
    wait_shift(e,'send')
    e.put(move_byte(0x0c,0xeff7fe))
    wait_shift(e,'receive')
    for code,target in ((1,'right'),(3,'left'),(0x81,'right_up'),(0x83,'left_up')):
        e.if_d0(code,target)
    e.jump('pace')
    for label,direction,velocity in (('right',1,0x0100),('left',2,0xff00)):
        e.label(label)
        e.put(bytes.fromhex('13c0')+be32(REPLY))
        # Ignore a duplicate make for a key already down. The most recently
        # pressed distinct direction wins until that key is released.
        for state in ((1,3) if direction == 1 else (2,3)):
            e.if_byte(HELD_MASK,state,'pace')
        e.put(bytes.fromhex('08f9')+be16(direction-1)+be32(HELD_MASK)) # BSET
        e.put(move_byte(direction,HELD))
        e.setword(velocity,VEL)
        e.word('5279',ENTRY_COUNT)
        e.jump('pace')
    for label,direction in (('right_up',1),('left_up',2)):
        e.label(label)
        e.put(bytes.fromhex('13c0')+be32(REPLY))
        e.put(bytes.fromhex('08b9')+be16(direction-1)+be32(HELD_MASK)) # BCLR
        e.if_byte(HELD,direction,label+'_active')
        e.jump('pace')
        e.label(label+'_active')
        # If the other key remains down, re-enter its run. This is this
        # experiment's input policy, not a claim about source-game ordering.
        other = 2 if direction == 1 else 1
        e.if_byte(HELD_MASK,other,label+'_restore')
        e.put(move_byte(0,HELD))
        e.jump('pace')
        e.label(label+'_restore')
        e.put(move_byte(other,HELD))
        e.setword(0xff00 if other == 2 else 0x0100,VEL)
        e.word('5279',ENTRY_COUNT)
        e.jump('pace')
    e.label('pace')
    e.put(bytes.fromhex('5239')+be32(PHASE))
    e.if_byte(PHASE,6,'skip')
    e.word('5279',TICKS)
    e.if_byte(HELD,1,'speed_right')
    e.if_byte(HELD,2,'speed_left')
    e.jump('friction')
    e.label('skip')
    e.put(move_byte(0,PHASE))
    e.jump('wait_vbl')
    e.label('speed_right')
    e.word('3039',VEL)
    e.cmpw(0x0200)
    e.cond(0x6c,'add_right')  # BLT target
    e.jump('integrate')
    e.label('add_right')
    e.put(bytes.fromhex('06400040'))
    e.word('33c0',VEL)
    e.jump('integrate')
    e.label('speed_left')
    e.word('3039',VEL)
    e.cmpw(0xfe00)
    e.cond(0x6f,'add_left') # BGT target
    e.jump('integrate')
    e.label('add_left')
    e.put(bytes.fromhex('04400040'))
    e.word('33c0',VEL)
    e.jump('integrate')
    e.label('friction')
    e.word('3039',VEL)
    e.cmpw(0)
    e.cond(0x6f,'friction_positive') # BGT
    e.cond(0x6c,'friction_negative') # BLT
    e.jump('integrate')
    e.label('friction_positive')
    e.put(bytes.fromhex('04400060'))
    e.cmpw(0)
    e.cond(0x6c,'friction_zero') # BLT
    e.jump('save_friction')
    e.label('friction_negative')
    e.put(bytes.fromhex('06400060'))
    e.cmpw(0)
    e.cond(0x6f,'friction_zero') # BGT
    e.jump('save_friction')
    e.label('friction_zero')
    e.put(bytes.fromhex('7000'))
    e.label('save_friction')
    e.word('33c0',VEL)
    e.label('integrate')
    # Erase previous figure, update signed 8.8 position with bounds, redraw.
    sprite_address(e,POS)
    for row in range(24):
        for x in range(3):
            e.put(bytes.fromhex('117c0000')+be16(row*64+x))
    e.word('3039',POS)
    e.word('d079',VEL) # ADD.W velocity,D0
    e.cmpw(0x1000)
    e.cond(0x64,'clamp_min') # BCS: unsigned position below lower bound
    e.cmpw(0xe000)
    e.cond(0x63,'clamp_max') # BHI (inverse BLS)
    e.jump('store_pos')
    e.label('clamp_min')
    e.put(bytes.fromhex('303c1000'))
    e.jump('store_pos')
    e.label('clamp_max')
    e.put(bytes.fromhex('303ce000'))
    e.label('store_pos')
    e.word('33c0',POS)
    e.label('draw')
    sprite_address(e,POS)
    e.word('3039',POS)
    e.put(bytes.fromhex('e048 02400007')) # integer pixel modulo 8
    for shift in range(8):
        e.cmpw(shift)
        e.cond(0x66,'shift'+str(shift)) # BEQ
    e.jump('fault')
    for shift in range(8):
        e.label('shift'+str(shift))
        for row,bits in enumerate(FIGURE):
            pixels=(bits << 8) >> shift
            for x,value in enumerate(((pixels>>16)&255,(pixels>>8)&255,pixels&255)):
                e.put(bytes.fromhex('117c')+be16(value)+be16(row*64+x))
        e.jump('wait_vbl')
    e.label('fault')
    e.put(bytes.fromhex('60fe'))
    code=e.finish()
    if ENTRY+len(code)>65536:
        raise ValueError('ROM overflow')
    rom=bytearray(65536)
    rom[:8]=be32(0x4000)+be32(ROM_BASE+ENTRY)
    for vector in range(2,64):
        rom[vector*4:vector*4+4]=be32(e.labels['fault'])
    rom[ENTRY:ENTRY+len(code)]=code
    return bytes(rom),len(code)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    image,size=build()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('xb') as f: f.write(image)
    print(f'ROM sha256={hashlib.sha256(image).hexdigest()} image_bytes={len(image)} code_bytes={size} used_through={ENTRY+size}')

if __name__=='__main__': main()
