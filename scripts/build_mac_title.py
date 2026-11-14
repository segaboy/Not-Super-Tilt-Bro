#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Experimental mouse-driven title for the opt-in two-character ROM.

The SCC aliases, phase decoding and polarity are engineering hypotheses; see
docs/mouse-title-evidence.md. No hardware or physical input claim is made.
"""
import argparse
import hashlib
from pathlib import Path
from build_mac_probe import DIAG, SCREEN, be16, be32, move_byte

X,Y=DIAG+64,DIAG+66
XP,YP,XN,YN,ARMED,STATE,LOSSES=[DIAG+i for i in (68,69,70,71,72,73,74)]
DISPLAY_X,DISPLAY_Y,DIRTY,IDLE=DIAG+80,DIAG+82,DIAG+84,DIAG+85
PB=0xefe1fe
SCCA,SCCB=0x9ffffa,0x9ffff8
SCCWA,SCCWB=0xbffffb,0xbffff9

# Original 5x7 geometric lettering for the experimental title only.
FONT={
 'A':('01110','10001','10001','11111','10001','10001','10001'),
 'B':('11110','10001','10001','11110','10001','10001','11110'),
 'E':('11111','10000','10000','11110','10000','10000','11111'),
 'N':('10001','11001','10101','10011','10001','10001','10001'),
 'O':('01110','10001','10001','10001','10001','10001','01110'),
 'P':('11110','10001','10001','11110','10000','10000','10000'),
 'R':('11110','10001','10001','11110','10100','10010','10001'),
 'S':('01111','10000','10000','01110','00001','00001','11110'),
 'T':('11111','00100','00100','00100','00100','00100','00100'),
 'U':('10001','10001','10001','10001','10001','10001','01110'),
 'L':('10000','10000','10000','10000','10000','10000','11111'),
 'I':('11111','00100','00100','00100','00100','00100','11111'),
 ' ':('00000',)*7,
}
POINTER=('100000','110000','111000','111100','111110','111000','101100','000110')

def title_pixels():
    image=bytearray(512*342//8)
    def pixel(x,y):image[y*64+x//8]|=0x80>>(x%8)
    def text(value,x,y,scale):
        for i,ch in enumerate(value):
            for row,bits in enumerate(FONT[ch]):
                for col,b in enumerate(bits):
                    if b=='1':
                        for dy in range(scale):
                            for dx in range(scale):pixel(x+i*6*scale+col*scale+dx,y+row*scale+dy)
    text('NOT SUPER TILT BRO',148,100,2)
    for x in range(208,305):pixel(x,196);pixel(x,224)
    for y in range(196,225):pixel(208,y);pixel(304,y)
    text('START',227,203,2)
    return image

def toggle_pointer(e):
    e.put(bytes.fromhex('4eb9')) # JSR absolute-long; emitter resolves label
    e.patches.append((len(e.code),'title_toggle'));e.put(bytes(4))

def emit_pointer_subroutine(e):
    # Pre-shifted XOR bytes restore underlying pixels on the second call.
    e.label('title_toggle')
    e.word('3039',DISPLAY_Y);e.put(bytes.fromhex('ed48 41f9')+be32(SCREEN)+bytes.fromhex('d0c0'))
    e.word('3039',DISPLAY_X);e.put(bytes.fromhex('e648 d0c0'))
    e.word('3039',DISPLAY_X);e.put(bytes.fromhex('02400007'))
    for shift in range(8):
        e.cmpw(shift);e.cond(0x66,'title_pointer_'+str(shift))
    e.put(bytes.fromhex('4e75'))
    for shift in range(8):
        e.label('title_pointer_'+str(shift))
        for row,bits in enumerate(POINTER):
            mask=(int(bits,2)<<10)>>shift
            for byte,value in enumerate((mask>>8,mask&255)):
                if value:e.put(bytes.fromhex('0a28')+be16(value)+be16(row*64+byte))
        e.put(bytes.fromhex('4e75'))

def bit_test(e,address,bit,target):
    e.put(bytes.fromhex('0839')+be16(bit)+be32(address))
    e.cond(0x67,target) # bit set => BNE

def read_phase(e,axis,pbbit,scc,new):
    e.put(move_byte(0,new))
    bit_test(e,PB,pbbit,axis+'_pb_set');e.jump(axis+'_pb_done')
    e.label(axis+'_pb_set');e.put(bytes.fromhex('08f90001')+be32(new))
    e.label(axis+'_pb_done')
    bit_test(e,scc,3,axis+'_dcd_set');e.jump(axis+'_sample_done')
    e.label(axis+'_dcd_set');e.put(bytes.fromhex('08f90000')+be32(new))
    e.label(axis+'_sample_done')

def emit_axis(e,name,previous,current,position,maximum,reverse=False):
    # Gray edges with changed DCD bit: one pixel for two phase transitions.
    transitions=((0,1,1),(1,0,-1),(3,2,1),(2,3,-1))
    for index,(old,new,direction) in enumerate(transitions):
        label=f'{name}_check_{index}';e.if_byte(previous,old,label)
    e.jump(name+'_save')
    for index,(old,new,direction) in enumerate(transitions):
        e.label(f'{name}_check_{index}')
        e.if_byte(current,new,f'{name}_move_{index}')
        e.jump(name+'_save')
        e.label(f'{name}_move_{index}')
        if reverse:direction=-direction
        e.word('3039',position);e.cmpw(maximum if direction>0 else 0)
        e.cond(0x66,name+'_save') # at boundary, retain current position
        e.word('5279' if direction>0 else '5379',position)
        e.put(bytes.fromhex('5239')+be32(DIRTY))
        e.jump(name+'_save')
    e.label(name+'_save')
    e.put(bytes.fromhex('13f9')+be32(current)+be32(previous))

def emit_title(e,wait_shift):
    for offset,value in enumerate(title_pixels()):
        if value:e.put(move_byte(value,SCREEN+offset))
    e.setword(256,X);e.setword(210,Y);e.setword(256,DISPLAY_X);e.setword(210,DISPLAY_Y)
    e.setword(0,DIAG+22) # keyboard transfer timeout count
    for address in (XP,YP,XN,YN,ARMED,LOSSES,DIRTY,IDLE):e.put(move_byte(0,address))
    e.put(move_byte(1,STATE)) # title ready
    # A and B reset external status; repeated while polling to sample live DCD.
    e.put(move_byte(0x10,SCCWA)+move_byte(0x10,SCCWB))
    read_phase(e,'baseline_x',4,SCCA,XN);read_phase(e,'baseline_y',5,SCCB,YN)
    e.put(bytes.fromhex('13f9')+be32(XN)+be32(XP))
    e.put(bytes.fromhex('13f9')+be32(YN)+be32(YP))
    toggle_pointer(e)
    e.label('title_poll')
    e.put(move_byte(0x10,SCCWA)+move_byte(0x10,SCCWB))
    read_phase(e,'title_x',4,SCCA,XN);read_phase(e,'title_y',5,SCCB,YN)
    # Keep sampling during motion; redraw after sixteen pixel steps or after the
    # phase inputs have stayed unchanged for 16 polling passes.
    e.word('1039',XN);e.word('b039',XP);e.cond(0x67,'title_activity')
    e.word('1039',YN);e.word('b039',YP);e.cond(0x67,'title_activity')
    e.if_byte(DIRTY,0,'title_axis')
    e.label('title_idle_dirty');e.put(bytes.fromhex('5239')+be32(IDLE))
    e.if_byte(IDLE,16,'title_redraw');e.jump('title_axis')
    e.label('title_redraw');toggle_pointer(e)
    e.word('3039',X);e.word('33c0',DISPLAY_X)
    e.word('3039',Y);e.word('33c0',DISPLAY_Y)
    toggle_pointer(e);e.put(move_byte(0,DIRTY)+move_byte(0,IDLE))
    e.jump('title_axis')
    e.label('title_activity');e.put(move_byte(0,IDLE))
    e.put(bytes.fromhex('0c390010')+be32(DIRTY));e.cond(0x65,'title_redraw')
    e.label('title_axis')
    emit_axis(e,'title_dx',XP,XN,X,506)
    emit_axis(e,'title_dy',YP,YN,Y,334,reverse=True)
    bit_test(e,PB,3,'title_released')
    e.if_byte(ARMED,1,'title_pressed');e.jump('title_poll')
    e.label('title_released');e.put(move_byte(1,ARMED));e.jump('title_poll')
    e.label('title_pressed');e.put(move_byte(0,ARMED))
    for addr,edge,inverse in ((X,208,0x64),(X,304,0x63),(Y,196,0x64),(Y,224,0x63)):
        e.word('3039',addr);e.cmpw(edge);e.cond(inverse,'title_poll')
    e.put(move_byte(4,STATE)) # accepted press; transition and keyboard flush in progress
    # Discard queued title-time keys before gameplay, bounded to 65 replies.
    # A held key needs a release and a fresh make after Start.
    e.put(bytes.fromhex('343c0040')) # MOVE.W #64,D2
    e.label('title_flush')
    e.put(move_byte(0x1c,0xeff7fe)+move_byte(0x14,0xeff5fe))
    wait_shift(e,'title_flush_send','title_flush_timeout')
    e.put(move_byte(0x0c,0xeff7fe))
    wait_shift(e,'title_flush_receive','title_flush_timeout')
    e.if_d0(0x7b,'title_flush_done')
    here=0x400000+0x104+len(e.code)
    offset=e.labels['title_flush']-(here+2)
    e.put(bytes.fromhex('51ca')+be16(offset & 0xffff))
    e.label('title_flush_timeout')
    e.put(move_byte(3,STATE)) # failed flush: remain at title until a fresh press
    e.jump('title_poll')
    e.label('title_flush_done')
    e.jump('title_done')
    emit_pointer_subroutine(e)
    e.label('title_done')

def main():
    from build_mac_movement import build
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    data,size=build(jumping=True,combat=True,two_player=True,title=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('xb') as stream:stream.write(data)
    print(f'sha256={hashlib.sha256(data).hexdigest()} bytes={len(data)} used_through={0x104+size}')

if __name__=='__main__':main()
