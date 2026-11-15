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
P2POS, P2HELD, P2MASK, P2FACING, P2CHANGES = [DIAG+x for x in (38,40,41,42,43)]
P2ACLOCK, P2ABUTTON, P1DAMAGE, P2ATTACKS, P2HITS = [DIAG+x for x in (44,45,46,47,48)]
P2JSTATE, P2JCLOCK, P2JVEL, P2HEIGHT, P2JBUTTON, P2JCOUNT = [DIAG+x for x in (50,51,52,54,56,57)]
P2VEL = DIAG + 88  # experimental C movement velocity; separate from title scratch
P1JAB, P2JAB, P1JAB_NEW, P2JAB_NEW, JAB_PREVIOUS = [DIAG+x for x in (90,94,98,99,100)]
# Original geometric training target and attack pose; no upstream artwork.
DUMMY = (0x0ff0,0x1ff8,0x1ff8,0x0ff0,0x03c0,0x0ff0,0x1ff8,0x3ffc,
         0x3ffc,0x3ffc,0x03c0,0x07e0,0x07e0,0x0e70,0x0e70,0x1c38,
         0x1c38,0x381c,0x381c,0x381c,0x700e,0x700e,0,0)
PUNCH = tuple(bits | (0x000f if 7 <= row <= 10 else 0) for row,bits in enumerate(FIGURE))
PUNCH_LEFT = tuple(int(f'{bits:016b}'[::-1],2) for bits in PUNCH)
DUMMY_PUNCH = tuple(bits | (0x000f if 7 <= row <= 10 else 0) for row,bits in enumerate(DUMMY))
DUMMY_PUNCH_LEFT = tuple(int(f'{bits:016b}'[::-1],2) for bits in DUMMY_PUNCH)

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

def sprite_address(e, addr, jumping=False, height_addr=JHEIGHT):
    # A0 = first row + left margin + (position's integer pixel / 8).
    e.word('3039',addr)                 # MOVE.W absolute,D0
    e.put(bytes.fromhex('e048 e648'))  # LSR.W #8,D0; LSR.W #3,D0
    e.put(bytes.fromhex('41f9')+be32(SCREEN+228*64+16))
    e.put(bytes.fromhex('d0c0'))       # ADDA.W D0,A0
    if jumping:
        e.word('3039',height_addr)   # unsigned 8.8 height above floor
        e.put(bytes.fromhex('e048 ed48 90c0')) # >>8; <<6; SUBA.W D0,A0

def wait_shift(e, name, timeout_target='wait_vbl'):
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
    e.jump(timeout_target)
    e.label(name+'_done')
    e.put(bytes.fromhex('103900eff5fe'))

def build(jumping=False,combat=False,two_player=False,title=False,initial_damage=0,native_movement=None,native_p2=False,native_jab=None):
    if combat and not jumping:
        raise ValueError('combat experiment requires jumping')
    if two_player and not combat:
        raise ValueError('two-player experiment requires combat')
    if title and not two_player:
        raise ValueError('title experiment requires two-player')
    if initial_damage not in range(0,255,2) or (initial_damage and not two_player):
        raise ValueError('initial damage is a two-player test fixture in 0..254')
    if native_movement is not None and (not isinstance(native_movement,bytes) or not native_movement or len(native_movement)>0x2000):
        raise ValueError('native movement must be nonempty bytes fitting the experimental ROM slot')
    if native_p2 and (native_movement is None or not two_player):
        raise ValueError('native player two requires a native component and two-player profile')
    if native_jab is not None:
        if not (title and native_p2 and isinstance(native_jab,tuple) and len(native_jab)==3):
            raise ValueError('native jab requires the dual-C title profile and component tuple')
        jab_code,jab_begin,jab_tick=native_jab
        if (not isinstance(jab_code,bytes) or not jab_code or len(jab_code)>0x1e00 or
            len(native_movement)>0x200 or any(not isinstance(x,int) or x<0 or x>=len(jab_code) or x%2 for x in (jab_begin,jab_tick))):
            raise ValueError('native jab component outside its ROM slot')
    e=Asm()
    def jab_begin_call(address,new_flag):
        e.put(bytes.fromhex('4879')+be32(address)+bytes.fromhex('4eb9')+be32(ROM_BASE+0xe200+jab_begin)
              +bytes.fromhex('4fef0004')+move_byte(1,new_flag))
    def jab_tick_call(prefix,address,new_flag,button,clock,attacks):
        e.if_byte(address,0,prefix+'_done')
        e.if_byte(new_flag,1,prefix+'_new')
        e.put(bytes.fromhex('13f9')+be32(address)+be32(JAB_PREVIOUS))
        e.put(bytes.fromhex('7000 1039')+be32(button)+bytes.fromhex('2f00 4879')+be32(address))
        e.put(bytes.fromhex('4eb9')+be32(ROM_BASE+0xe200+jab_tick)+bytes.fromhex('4fef0008'))
        e.put(bytes.fromhex('1039')+be32(JAB_PREVIOUS)+bytes.fromhex('b039')+be32(address))
        e.cond(0x67,prefix+'_changed') # BNE: stage transitioned
        e.jump(prefix+'_done')
        e.label(prefix+'_changed')
        e.if_byte(address,0,prefix+'_ended')
        e.put(move_byte(1,clock)+bytes.fromhex('5239')+be32(attacks))
        e.jump(prefix+'_done')
        e.label(prefix+'_ended')
        e.put(move_byte(0,clock))
        e.jump(prefix+'_done')
        e.label(prefix+'_new')
        e.put(move_byte(0,new_flag))
        e.label(prefix+'_done')
    def jab_damage(prefix,jab,damage):
        # Source-derived PAL jab damage values, applied to this prototype's
        # local collision rule. The 254 saturation is a local display policy.
        for stage in (1,2,3):e.if_byte(jab,stage,prefix+'_stage'+str(stage))
        e.jump(prefix+'_done')
        for stage,amount in ((1,2),(2,1),(3,5)):
            e.label(prefix+'_stage'+str(stage))
            e.put(bytes.fromhex('0c39')+be16(254-amount)+be32(damage))
            e.cond(0x65,prefix+'_cap') # unsigned >= threshold
            e.put(bytes.fromhex('0639')+be16(amount)+be32(damage))
            e.jump(prefix+'_done')
        e.label(prefix+'_cap')
        e.put(move_byte(254,damage))
        e.label(prefix+'_done')
    e.put(bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe '
                        '41f900400000 93c9 703f 22d8 51c8fffc'))
    e.put(bytes.fromhex('41f9')+be32(SCREEN)+bytes.fromhex('303c')+be16(SCREEN_BYTES-1)
          +bytes.fromhex('4218 51c8fffc'))
    if title:
        from build_mac_title import emit_title
        emit_title(e,wait_shift)
        # Remove the title before drawing the separate gameplay scene.
        e.put(bytes.fromhex('41f9')+be32(SCREEN)+bytes.fromhex('303c')+be16(SCREEN_BYTES-1)
              +bytes.fromhex('4218 51c8fffc'))
    # Stage is original geometric art. All moving art occupies rows 228..251.
    for y in range(252,260):
        for x in range(16,48):
            e.put(move_byte(0xff,SCREEN+y*64+x))
    for off in range(8,58 if two_player else 38 if combat else 32 if jumping else 24):
        e.put(move_byte(0,DIAG+off))
    if native_jab is not None:
        for off in range(90,101):e.put(move_byte(0,DIAG+off))
    e.setword(0x8000,POS)   # 128 pixels from the left edge of the movement area
    if combat:
        e.put(move_byte(1,FACING))
    if two_player:
        e.setword(0xa800,P2POS)
        if native_p2:e.setword(0,P2VEL)
        e.put(move_byte(2,P2FACING))
        if initial_damage:
            e.put(move_byte(initial_damage,DAMAGE)+move_byte(initial_damage,P1DAMAGE))
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
    if two_player:
        for code,target in ((9,'p2_right'),(11,'p2_left'),(0x89,'p2_right_up'),(0x8b,'p2_left_up'),
                            (13,'p2_attack_down'),(0x8d,'p2_attack_up'),(15,'p2_jump_down'),(0x8f,'p2_jump_up')):
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
        if native_jab is not None:jab_begin_call(P1JAB,P1JAB_NEW)
        e.put(move_byte(1,ACLOCK))
        e.setword(0,VEL)
        e.put(bytes.fromhex('5239')+be32(ATTACKS))
        e.jump('pace')
        e.label('attack_up')
        e.put(move_byte(0,ABUTTON))
        e.jump('pace')
    if two_player:
        e.label('p2_jump_down')
        e.if_byte(P2JBUTTON,1,'pace')
        e.put(move_byte(1,P2JBUTTON))
        e.if_byte(P2ACLOCK,0,'p2_jump_attack_clear')
        e.jump('pace')
        e.label('p2_jump_attack_clear')
        e.if_byte(P2JSTATE,0,'p2_jump_begin')
        e.jump('pace')
        e.label('p2_jump_begin')
        e.put(move_byte(1,P2JSTATE)+move_byte(0,P2JCLOCK))
        e.put(bytes.fromhex('5239')+be32(P2JCOUNT))
        e.jump('pace')
        e.label('p2_jump_up')
        e.put(move_byte(0,P2JBUTTON))
        e.jump('pace')
        e.label('p2_attack_down')
        e.if_byte(P2ABUTTON,1,'pace')
        e.put(move_byte(1,P2ABUTTON))
        e.if_byte(P2JSTATE,0,'p2_attack_grounded')
        e.jump('pace')
        e.label('p2_attack_grounded')
        e.if_byte(P2ACLOCK,0,'p2_attack_begin')
        e.jump('pace')
        e.label('p2_attack_begin')
        if native_jab is not None:jab_begin_call(P2JAB,P2JAB_NEW)
        e.put(move_byte(1,P2ACLOCK))
        e.put(bytes.fromhex('5239')+be32(P2ATTACKS))
        e.jump('pace')
        e.label('p2_attack_up')
        e.put(move_byte(0,P2ABUTTON))
        e.jump('pace')
        for label,direction in (('p2_right',1),('p2_left',2)):
            e.label(label)
            for mask in ((1,3) if direction==1 else (2,3)):
                e.if_byte(P2MASK,mask,'pace')
            e.put(bytes.fromhex('08f9')+be16(direction-1)+be32(P2MASK))
            e.put(move_byte(direction,P2HELD)+move_byte(direction,P2FACING))
            if native_p2:e.setword(0x0100 if direction==1 else 0xff00,P2VEL)
            e.put(bytes.fromhex('5239')+be32(P2CHANGES))
            e.jump('pace')
        for label,direction in (('p2_right_up',1),('p2_left_up',2)):
            e.label(label)
            e.put(bytes.fromhex('08b9')+be16(direction-1)+be32(P2MASK))
            e.if_byte(P2HELD,direction,label+'_active')
            e.jump('pace')
            e.label(label+'_active')
            other=2 if direction==1 else 1
            e.if_byte(P2MASK,other,label+'_restore')
            e.put(move_byte(0,P2HELD))
            e.jump('pace')
            e.label(label+'_restore')
            e.put(move_byte(other,P2HELD)+move_byte(other,P2FACING))
            if native_p2:e.setword(0x0100 if other==1 else 0xff00,P2VEL)
            e.put(bytes.fromhex('5239')+be32(P2CHANGES))
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
        # Direction events can set velocity while a jab is active. Keep the
        # prototype's grounded attack stationary until its clock ends.
        e.setword(0,VEL)
        e.jump('integrate')
        e.label('attack_movement_clear')
    e.if_byte(HELD,1,'native_right' if native_movement is not None else 'speed_right')
    e.if_byte(HELD,2,'native_left' if native_movement is not None else 'speed_left')
    e.jump('native_neutral' if native_movement is not None else 'friction')
    e.label('skip')
    e.put(move_byte(0,PHASE))
    e.jump('wait_vbl')
    if native_movement is not None:
        # Experimental C ABI bridge: the component also integrates a scratch
        # position; the existing compositor integrates the live position after
        # erasing the previous figure. DIAG+86 is dedicated to this scratch.
        for name,direction in (('native_right',1),('native_left',-1),('native_neutral',0)):
            e.label(name)
            e.setword(0,DIAG+86)
            e.put(bytes.fromhex('2f3c')+be32(direction & 0xffffffff))
            e.put(bytes.fromhex('4879')+be32(VEL))
            e.put(bytes.fromhex('4879')+be32(DIAG+86))
            e.put(bytes.fromhex('4eb9')+be32(ROM_BASE+0xe000))
            e.put(bytes.fromhex('4fef000c'))
            e.jump('integrate')
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
    if two_player:
        e.put(bytes.fromhex('43e8')+be16((-18*64)&0xffff)) # A1 = old P1 meter
        for row in range(6):
            for x in range(3):
                e.put(bytes.fromhex('137c0000')+be16(row*64+x))
    for row in range(24):
        for x in range(3):
            e.put(bytes.fromhex('117c0000')+be16(row*64+x))
    if two_player:
        sprite_address(e,P2POS,True,P2HEIGHT)
        for row in range(24):
            for x in range(3):
                e.put(bytes.fromhex('117c0000')+be16(row*64+x))
        e.put(bytes.fromhex('43e8')+be16((-18*64)&0xffff)) # A1 = old meter origin
        for row in range(6):
            for x in range(3):
                e.put(bytes.fromhex('137c0000')+be16(row*64+x))
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
    if two_player:
        e.if_byte(P2ACLOCK,0,'p2_movement_clear')
        if native_p2:e.setword(0,P2VEL)
        e.jump('p2_tick_done')
        e.label('p2_movement_clear')
        if native_p2:
            e.if_byte(P2HELD,1,'p2_native_right')
            e.if_byte(P2HELD,2,'p2_native_left')
            e.jump('p2_native_neutral')
            for label,direction in (('p2_native_right',1),('p2_native_left',-1),('p2_native_neutral',0)):
                e.label(label)
                e.setword(0,DIAG+86)
                e.put(bytes.fromhex('2f3c')+be32(direction & 0xffffffff))
                e.put(bytes.fromhex('4879')+be32(P2VEL))
                e.put(bytes.fromhex('4879')+be32(DIAG+86))
                e.put(bytes.fromhex('4eb9')+be32(ROM_BASE+0xe000))
                e.put(bytes.fromhex('4fef000c'))
                e.jump('p2_native_integrate')
            e.label('p2_native_integrate')
            e.word('3039',P2POS);e.word('d079',P2VEL)
            e.cmpw(0x1000);e.cond(0x64,'p2_clamp_left')
            e.cmpw(0xe000);e.cond(0x63,'p2_clamp_right')
            e.jump('p2_store')
        else:
            e.if_byte(P2HELD,1,'p2_tick_right')
            e.if_byte(P2HELD,2,'p2_tick_left')
            e.jump('p2_tick_done')
        e.label('p2_tick_right')
        e.word('3039',P2POS)
        e.put(bytes.fromhex('06400100'))
        e.cmpw(0xe000)
        e.cond(0x63,'p2_clamp_right')
        e.jump('p2_store')
        e.label('p2_clamp_right')
        e.put(bytes.fromhex('303ce000'))
        e.jump('p2_store')
        e.label('p2_tick_left')
        e.word('3039',P2POS)
        e.put(bytes.fromhex('04400100'))
        e.cmpw(0x1000)
        e.cond(0x64,'p2_clamp_left')
        e.jump('p2_store')
        e.label('p2_clamp_left')
        e.put(bytes.fromhex('303c1000'))
        e.label('p2_store')
        e.word('33c0',P2POS)
        e.label('p2_tick_done')
        e.if_byte(P2JSTATE,1,'p2_jump_squat_tick')
        e.if_byte(P2JSTATE,2,'p2_jump_air_tick')
        e.jump('p2_jump_tick_done')
        e.label('p2_jump_squat_tick')
        e.put(bytes.fromhex('5239')+be32(P2JCLOCK))
        e.if_byte(P2JCLOCK,4,'p2_jump_takeoff')
        e.jump('p2_jump_tick_done')
        e.label('p2_jump_takeoff')
        e.setword(0x0480,P2JVEL)
        e.put(move_byte(2,P2JSTATE))
        e.jump('p2_jump_tick_done')
        e.label('p2_jump_air_tick')
        e.put(bytes.fromhex('5239')+be32(P2JCLOCK))
        e.word('3039',P2JVEL)
        e.put(bytes.fromhex('04400060'))
        e.cmpw(0xfe00)
        e.cond(0x6c,'p2_jump_cap_fall')
        e.jump('p2_jump_save_velocity')
        e.label('p2_jump_cap_fall')
        e.put(bytes.fromhex('303cfe00'))
        e.label('p2_jump_save_velocity')
        e.if_byte(P2JCLOCK,8,'p2_jump_check_short')
        e.jump('p2_jump_store_velocity')
        e.label('p2_jump_check_short')
        e.if_byte(P2JBUTTON,0,'p2_jump_short')
        e.jump('p2_jump_store_velocity')
        e.label('p2_jump_short')
        e.put(bytes.fromhex('303c0102'))
        e.label('p2_jump_store_velocity')
        e.word('33c0',P2JVEL)
        e.word('3039',P2HEIGHT)
        e.word('d079',P2JVEL)
        e.cmpw(0)
        e.cond(0x6e,'p2_jump_land')
        e.word('33c0',P2HEIGHT)
        e.jump('p2_jump_tick_done')
        e.label('p2_jump_land')
        e.setword(0,P2JVEL)
        e.setword(0,P2HEIGHT)
        e.put(move_byte(0,P2JSTATE))
        e.label('p2_jump_tick_done')
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
        if native_jab is not None:jab_tick_call('p1_jab_c',P1JAB,P1JAB_NEW,ABUTTON,ACLOCK,ATTACKS)
        e.if_byte(ACLOCK,0,'draw_body')
        e.put(bytes.fromhex('5239')+be32(ACLOCK))
        e.if_byte(ACLOCK,7,'attack_hit_check')
        if native_jab is None:e.if_byte(ACLOCK,25,'attack_end')
        e.jump('draw_body')
        e.label('attack_hit_check')
        if two_player:
            e.word('3039',P2HEIGHT)
            e.cmpw(0)
            e.cond(0x67,'draw_body')
        e.if_byte(FACING,1,'attack_right')
        e.if_byte(FACING,2,'attack_left')
        e.jump('draw_body')
        e.label('attack_right')
        e.word('3039',P2POS if two_player else POS)
        if two_player: e.word('9079',POS) # target minus player, unsigned 8.8
        e.cmpw(0x1000 if two_player else 0x8800)
        e.cond(0x64,'draw_body') # below the local target interval
        e.cmpw(0x2000 if two_player else 0x9800)
        e.cond(0x63,'draw_body') # above the local target interval
        e.jump('attack_apply')
        e.label('attack_left')
        e.word('3039',POS)
        if two_player: e.word('9079',P2POS) # player minus target
        e.cmpw(0x1000 if two_player else 0xb800)
        e.cond(0x64,'draw_body')
        e.cmpw(0x2000 if two_player else 0xc800)
        e.cond(0x63,'draw_body')
        e.label('attack_apply')
        if native_jab is not None:jab_damage('p1_jab_damage',P1JAB,DAMAGE)
        else:
            e.put(bytes.fromhex('0c3900fe')+be32(DAMAGE))
            e.cond(0x66,'attack_damage_capped') # equal: retain the visible maximum
            e.put(bytes.fromhex('5439')+be32(DAMAGE)) # diagnostic damage += 2
            e.label('attack_damage_capped')
        e.put(bytes.fromhex('5239')+be32(HITS))
        e.jump('draw_body')
        e.label('attack_end')
        e.put(move_byte(0,ACLOCK))
        e.label('draw_body')
        if two_player:
            if native_jab is not None:jab_tick_call('p2_jab_c',P2JAB,P2JAB_NEW,P2ABUTTON,P2ACLOCK,P2ATTACKS)
            e.if_byte(P2ACLOCK,0,'p2_attack_done')
            e.put(bytes.fromhex('5239')+be32(P2ACLOCK))
            e.if_byte(P2ACLOCK,7,'p2_attack_check')
            if native_jab is None:e.if_byte(P2ACLOCK,25,'p2_attack_end')
            e.jump('p2_attack_done')
            e.label('p2_attack_check')
            e.word('3039',JHEIGHT)
            e.cmpw(0)
            e.cond(0x67,'p2_attack_done') # prototype target must be at floor
            e.if_byte(P2FACING,1,'p2_attack_right')
            e.if_byte(P2FACING,2,'p2_attack_left')
            e.jump('p2_attack_done')
            e.label('p2_attack_right')
            e.word('3039',POS)
            e.word('9079',P2POS)
            e.cmpw(0x1000)
            e.cond(0x64,'p2_attack_done')
            e.cmpw(0x2000)
            e.cond(0x63,'p2_attack_done')
            e.jump('p2_attack_apply')
            e.label('p2_attack_left')
            e.word('3039',P2POS)
            e.word('9079',POS)
            e.cmpw(0x1000)
            e.cond(0x64,'p2_attack_done')
            e.cmpw(0x2000)
            e.cond(0x63,'p2_attack_done')
            e.label('p2_attack_apply')
            if native_jab is not None:jab_damage('p2_jab_damage',P2JAB,P1DAMAGE)
            else:
                e.put(bytes.fromhex('0c3900fe')+be32(P1DAMAGE))
                e.cond(0x66,'p2_damage_capped')
                e.put(bytes.fromhex('5439')+be32(P1DAMAGE))
                e.label('p2_damage_capped')
            e.put(bytes.fromhex('5239')+be32(P2HITS))
            e.jump('p2_attack_done')
            e.label('p2_attack_end')
            e.put(move_byte(0,P2ACLOCK))
            e.label('p2_attack_done')
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
        if two_player:
            sprite_address(e,P2POS,True,P2HEIGHT)
            e.word('3039',P2POS)
            e.put(bytes.fromhex('e048 02400007'))
            e.if_byte(P2ACLOCK,7,'p2_attack_render')
            e.if_byte(P2ACLOCK,8,'p2_attack_render')
            for prefix,figure in (('p2_shift',DUMMY),('p2_attack_shift',DUMMY_PUNCH),
                                  ('p2_attack_left_shift',DUMMY_PUNCH_LEFT)):
                if prefix=='p2_attack_shift':
                    e.label('p2_attack_render')
                    e.if_byte(P2FACING,2,'p2_attack_render_left')
                if prefix=='p2_attack_left_shift':e.label('p2_attack_render_left')
                for shift in range(8):
                    e.cmpw(shift)
                    e.cond(0x66,prefix+str(shift))
                e.jump('fault')
                for shift in range(8):
                    e.label(prefix+str(shift))
                    for row,bits in enumerate(figure):
                        pixels=(bits<<8)>>shift
                        for x,value in enumerate(((pixels>>16)&255,(pixels>>8)&255,pixels&255)):
                            e.put(bytes.fromhex('117c')+be16(value)+be16(row*64+x))
                    e.jump('draw_meter')
            e.label('draw_meter')
            sprite_address(e,P2POS,True,P2HEIGHT)
            e.put(bytes.fromhex('43e8')+be16((-18*64)&0xffff))
        else:
            for row,bits in enumerate(DUMMY):
                for x,value in enumerate(((bits>>8)&255,bits&255)):
                    e.put(move_byte(value,SCREEN+(228+row)*64+37+x))
        # Original 8-cell hit indicator over the target: one 3x6 cell per
        # two damage points, capped visually at eight. Damage saturates at 254.
        for row in range(210,216):
            for byte in range(3):
                if two_player:
                    e.put(bytes.fromhex('137c0000')+be16((row-210)*64+byte))
                else:
                    e.put(move_byte(0,SCREEN+row*64+37+byte))
        for cell in range(8):
            mask=7 << (21-cell*3)
            parts=[(byte,(mask>>(16-byte*8))&255) for byte in range(3) if (mask>>(16-byte*8))&255]
            e.put(bytes.fromhex('0c39')+be16(2*(cell+1))+be32(DAMAGE))
            e.put(bytes((0x65,6*len(parts)*(6 if two_player else 8)))) # BCS skips ORI.B stores
            for row in range(210,216):
                for byte,value in parts:
                    if two_player:
                        e.put(bytes.fromhex('0029')+be16(value)+be16((row-210)*64+byte))
                    else:
                        e.put(bytes.fromhex('0039')+be16(value)+be32(SCREEN+row*64+37+byte))
        if two_player:
            # A separate original meter follows player one and reflects P2 hits.
            sprite_address(e,POS,jumping)
            e.put(bytes.fromhex('43e8')+be16((-18*64)&0xffff))
            for row in range(6):
                for byte in range(3):
                    e.put(bytes.fromhex('137c0000')+be16(row*64+byte))
            for cell in range(8):
                mask=7 << (21-cell*3)
                parts=[(byte,(mask>>(16-byte*8))&255) for byte in range(3) if (mask>>(16-byte*8))&255]
                e.put(bytes.fromhex('0c39')+be16(2*(cell+1))+be32(P1DAMAGE))
                e.put(bytes((0x65,6*len(parts)*6)))
                for row in range(6):
                    for byte,value in parts:
                        e.put(bytes.fromhex('0029')+be16(value)+be16(row*64+byte))
        if title:e.put(move_byte(2,DIAG+73)) # first complete arena frame is ready
        e.jump('wait_vbl')
    e.label('fault')
    e.put(bytes.fromhex('60fe'))
    code=e.finish()
    if ENTRY+len(code)>65536:
        raise ValueError('ROM overflow')
    if native_movement is not None and (ENTRY+len(code)>0xe000 or 0xe000+len(native_movement)>65536):
        raise ValueError('native movement overlaps generated code or exceeds ROM')
    rom=bytearray(65536)
    rom[:8]=be32(0x4000)+be32(ROM_BASE+ENTRY)
    for vector in range(2,64):
        rom[vector*4:vector*4+4]=be32(e.labels['fault'])
    rom[ENTRY:ENTRY+len(code)]=code
    if native_movement is not None:rom[0xe000:0xe000+len(native_movement)]=native_movement
    if native_jab is not None:rom[0xe200:0xe200+len(jab_code)]=jab_code
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
