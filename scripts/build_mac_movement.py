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
JSTATE, JCLOCK, JVEL, JHEIGHT, JBUTTON, JCOUNT = [DIAG+x for x in (24,25,26,28,30,31)]
ACLOCK, ABUTTON, FACING, DAMAGE, ATTACKS, HITS = [DIAG+x for x in (32,33,34,35,36,37)]
# Original geometric training target and attack pose; no upstream artwork.
DUMMY = (0x0ff0,0x1ff8,0x1ff8,0x0ff0,0x03c0,0x0ff0,0x1ff8,0x3ffc,
         0x3ffc,0x3ffc,0x03c0,0x07e0,0x07e0,0x0e70,0x0e70,0x1c38,
         0x1c38,0x381c,0x381c,0x381c,0x700e,0x700e,0,0)
PUNCH = tuple(bits | (0x000f if 7 <= row <= 10 else 0) for row,bits in enumerate(FIGURE))
PUNCH_LEFT = tuple(int(f'{bits:016b}'[::-1],2) for bits in PUNCH)

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

def sprite_address(e, addr, jumping=False):
    # A0 = first row + left margin + (position's integer pixel / 8).
    e.word('3039',addr)                 # MOVE.W absolute,D0
    e.put(bytes.fromhex('e048 e648'))  # LSR.W #8,D0; LSR.W #3,D0
    e.put(bytes.fromhex('41f9')+be32(SCREEN+228*64+16))
    e.put(bytes.fromhex('d0c0'))       # ADDA.W D0,A0
    if jumping:
        e.word('3039',JHEIGHT)        # unsigned 8.8 height above floor
        e.put(bytes.fromhex('e048 ed48 90c0')) # >>8; <<6; SUBA.W D0,A0

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

def build(jumping=False,combat=False):
    if combat and not jumping:
        raise ValueError('combat experiment requires jumping')
    e=Asm()
    e.put(bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe '
                        '41f900400000 93c9 703f 22d8 51c8fffc'))
    e.put(bytes.fromhex('41f9')+be32(SCREEN)+bytes.fromhex('303c')+be16(SCREEN_BYTES-1)
          +bytes.fromhex('4218 51c8fffc'))
    # Stage is original geometric art. All moving art occupies rows 228..251.
    for y in range(252,260):
        for x in range(16,48):
            e.put(move_byte(0xff,SCREEN+y*64+x))
    for off in range(8,38 if combat else 32 if jumping else 24):
        e.put(move_byte(0,DIAG+off))
    e.setword(0x8000,POS)   # 128 pixels from the left edge of the movement area
    if combat:
        e.put(move_byte(1,FACING))
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
    if jumping:
        e.if_d0(5,'jump_down')
        e.if_d0(0x85,'jump_up')
    if combat:
        e.if_d0(7,'attack_down')
        e.if_d0(0x87,'attack_up')
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
        if combat:
            e.put(move_byte(direction,FACING))
        e.setword(velocity,VEL)
        e.word('5279',ENTRY_COUNT)
        e.jump('pace')
    if jumping:
        e.label('jump_down')
        e.if_byte(JBUTTON,1,'pace')
        e.put(move_byte(1,JBUTTON))
        if combat:
            e.if_byte(ACLOCK,0,'jump_combat_clear')
            e.jump('pace')
            e.label('jump_combat_clear')
        e.if_byte(JSTATE,0,'jump_begin')
        e.jump('pace')
        e.label('jump_begin')
        e.put(move_byte(1,JSTATE)+move_byte(0,JCLOCK))
        e.put(bytes.fromhex('5239')+be32(JCOUNT))
        e.jump('pace')
        e.label('jump_up')
        e.put(move_byte(0,JBUTTON))
        e.jump('pace')
    if combat:
        e.label('attack_down')
        e.if_byte(ABUTTON,1,'pace')
        e.put(move_byte(1,ABUTTON))
        e.if_byte(JSTATE,0,'attack_grounded')
        e.jump('pace')
        e.label('attack_grounded')
        e.if_byte(ACLOCK,0,'attack_begin')
        e.jump('pace')
        e.label('attack_begin')
        e.put(move_byte(1,ACLOCK))
        e.setword(0,VEL)
        e.put(bytes.fromhex('5239')+be32(ATTACKS))
        e.jump('pace')
        e.label('attack_up')
        e.put(move_byte(0,ABUTTON))
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
        if combat:
            e.put(move_byte(other,FACING))
        e.setword(0xff00 if other == 2 else 0x0100,VEL)
        e.word('5279',ENTRY_COUNT)
        e.jump('pace')
    e.label('pace')
    e.put(bytes.fromhex('5239')+be32(PHASE))
    e.if_byte(PHASE,6,'skip')
    e.word('5279',TICKS)
    if combat:
        e.if_byte(ACLOCK,0,'attack_movement_clear')
        e.jump('friction')
        e.label('attack_movement_clear')
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
    sprite_address(e,POS,jumping)
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
    if jumping:
        e.if_byte(JSTATE,1,'jump_squat_tick')
        e.if_byte(JSTATE,2,'jump_air_tick')
        e.jump('draw')
        e.label('jump_squat_tick')
        e.put(bytes.fromhex('5239')+be32(JCLOCK))
        e.if_byte(JCLOCK,4,'jump_takeoff')
        e.jump('draw')
        e.label('jump_takeoff')
        e.setword(0x0480,JVEL)
        e.put(move_byte(2,JSTATE))
        e.jump('draw')
        e.label('jump_air_tick')
        # Approximate local height integration; the source game's complete
        # gravity, collision and tick order remain unimplemented.
        e.put(bytes.fromhex('5239')+be32(JCLOCK))
        e.word('3039',JVEL)
        e.put(bytes.fromhex('04400060'))
        e.cmpw(0xfe00)
        e.cond(0x6c,'jump_cap_fall') # BLT
        e.jump('jump_save_velocity')
        e.label('jump_cap_fall')
        e.put(bytes.fromhex('303cfe00'))
        e.label('jump_save_velocity')
        e.if_byte(JCLOCK,8,'jump_check_short_hop')
        e.jump('jump_store_velocity')
        e.label('jump_check_short_hop')
        e.if_byte(JBUTTON,0,'jump_short_hop')
        e.jump('jump_store_velocity')
        e.label('jump_short_hop')
        e.put(bytes.fromhex('303c0102')) # local positive-up sign convention
        e.label('jump_store_velocity')
        e.word('33c0',JVEL)
        e.word('3039',JHEIGHT)
        e.word('d079',JVEL)
        e.cmpw(0)
        e.cond(0x6e,'jump_land') # BLE
        e.word('33c0',JHEIGHT)
        e.jump('draw')
        e.label('jump_land')
        e.setword(0,JVEL)
        e.setword(0,JHEIGHT)
        e.put(move_byte(0,JSTATE))
    e.label('draw')
    if combat:
        e.if_byte(ACLOCK,0,'draw_body')
        e.put(bytes.fromhex('5239')+be32(ACLOCK))
        e.if_byte(ACLOCK,7,'attack_hit_check')
        e.if_byte(ACLOCK,25,'attack_end')
        e.jump('draw_body')
        e.label('attack_hit_check')
        e.if_byte(FACING,1,'attack_right')
        e.if_byte(FACING,2,'attack_left')
        e.jump('draw_body')
        e.label('attack_right')
        e.word('3039',POS)
        e.cmpw(0x8800)
        e.cond(0x64,'draw_body') # below the local target interval
        e.cmpw(0x9800)
        e.cond(0x63,'draw_body') # above the local target interval
        e.jump('attack_apply')
        e.label('attack_left')
        e.word('3039',POS)
        e.cmpw(0xb800)
        e.cond(0x64,'draw_body')
        e.cmpw(0xc800)
        e.cond(0x63,'draw_body')
        e.label('attack_apply')
        e.put(bytes.fromhex('5439')+be32(DAMAGE)) # diagnostic damage += 2
        e.put(bytes.fromhex('5239')+be32(HITS))
        e.jump('draw_body')
        e.label('attack_end')
        e.put(move_byte(0,ACLOCK))
        e.label('draw_body')
    sprite_address(e,POS,jumping)
    e.word('3039',POS)
    e.put(bytes.fromhex('e048 02400007')) # integer pixel modulo 8
    if combat:
        e.if_byte(ACLOCK,7,'attack_render')
        e.if_byte(ACLOCK,8,'attack_render')
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
        e.jump('draw_dummy' if combat else 'wait_vbl')
    if combat:
        e.label('attack_render')
        e.if_byte(FACING,2,'attack_render_left')
        for prefix,figure in (('attack_shift',PUNCH),('attack_left_shift',PUNCH_LEFT)):
            if prefix=='attack_left_shift': e.label('attack_render_left')
            for shift in range(8):
                e.cmpw(shift)
                e.cond(0x66,prefix+str(shift))
            e.jump('fault')
            for shift in range(8):
                e.label(prefix+str(shift))
                for row,bits in enumerate(figure):
                    pixels=(bits << 8) >> shift
                    for x,value in enumerate(((pixels>>16)&255,(pixels>>8)&255,pixels&255)):
                        e.put(bytes.fromhex('117c')+be16(value)+be16(row*64+x))
                e.jump('draw_dummy')
        e.label('draw_dummy')
        for row,bits in enumerate(DUMMY):
            for x,value in enumerate(((bits>>8)&255,bits&255)):
                e.put(move_byte(value,SCREEN+(228+row)*64+37+x))
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
