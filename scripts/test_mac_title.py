#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Headless mouse-title and keyboard handoff checks in BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from build_mac_movement import build
from build_mac_title import POINTER,title_pixels
from test_mac_two_player import decode,pixels,HEADER

def sha(data):return hashlib.sha256(data).hexdigest()

def run(exe,rom,root,name,events,stop=7000000):
    frame=root/(name+'.pbm');witness=root/(name+'.keyboard')
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles',str(stop),'--timeout-ms','20000',
         '--inspect','0xb00:80','--frame',str(frame),'--keyboard-witness',str(witness)]
    if any(kind=='mouse-motion' for kind,_ in events):cmd+=['--mouse-dcd-invert','3']
    for kind,value in events:cmd+=['--'+kind,value]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(name+': '+result.stdout+result.stderr)
    data=json.loads(result.stdout);assert data['status']=='cycle_limit'
    assert data['keyboard_witness']['rejected']==data['keyboard_witness']['pending']==data['keyboard_witness']['dropped']==0
    if 'mouse' in data:assert data['mouse']['pending']==0
    b=bytes.fromhex(data['memory']['bytes']);state=b[73]
    x=int.from_bytes(b[64:66],'big');y=int.from_bytes(b[66:68],'big')
    image=frame.read_bytes()
    if state in (1,3):
        expected=title_pixels()
        for row,bits in enumerate(POINTER):
            for col,bit in enumerate(bits):
                if bit=='1':expected[(y+row)*64+(x+col)//8]^=0x80>>((x+col)%8)
        assert image==HEADER+expected,(name,x,y)
    elif state==2:
        s=decode({'memory':{'bytes':b[:58].hex()}});pixels(image,s)
    else:raise AssertionError((name,'unexpected title state',state))
    (root/(name+'.json')).write_text(json.dumps({'command':cmd,'result':data,'frame_sha256':sha(image)},indent=2)+'\n',encoding='utf-8')
    return {'x':x,'y':y,'state':state,'game_x':int.from_bytes(b[16:18],'big'),
            'p2x':int.from_bytes(b[38:40],'big'),'frame_sha256':sha(image)}

def test(exe,root):
    image,size=build(jumping=True,combat=True,two_player=True,title=True);rom=root/'title.rom'
    with rom.open('xb') as f:f.write(image)
    scenarios={
      'neutral':([],7000000),
      'right':([('mouse-motion','2000000:16:0')],7000000),
      'left':([('mouse-motion','2000000:-16:0')],7000000),
      'down':([('mouse-motion','2000000:0:16')],7000000),
      'up':([('mouse-motion','2000000:0:-16')],7000000),
      'outside':([('mouse-motion','1500000:80:0'),('mouse-button','3000000:1'),('mouse-button','3400000:0')],7000000),
      'return_and_start':([('mouse-motion','1200000:80:0'),('mouse-motion','3000000:-80:0'),
                           ('mouse-button','5000000:1'),('mouse-button','5400000:0')],9000000),
      'start':([('mouse-button','2000000:1'),('mouse-button','2400000:0')],7000000),
      'title_keys_discarded':([('key','1000000:0:1'),('key','1300000:0:0'),('mouse-button','2000000:1'),('mouse-button','2400000:0')],7000000),
      'play_keys':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:0:1'),('key','4500000:0:0')],7000000),
      'p2_play_keys':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:5:1'),('key','4500000:5:0')],7000000),
      'motion_2048':([('mouse-edge-cycles','2048'),('mouse-motion','1000000:32:0')],4000000),
      'motion_256':([('mouse-edge-cycles','256'),('mouse-motion','1000000:32:0')],4000000),
      'flush_timeout':([('keyboard-fault','0x14:1:1:0'),('mouse-button','2000000:1'),('mouse-button','2400000:0')],7000000),
      'flush_retry':([('keyboard-fault','0x14:1:1:0'),('mouse-button','2000000:1'),('mouse-button','3000000:0'),
                      ('mouse-button','4000000:1'),('mouse-button','4400000:0')],8000000),
    }
    cases={n:run(exe,rom,root,n,*args) for n,args in scenarios.items()}
    assert (cases['neutral']['x'],cases['neutral']['y'],cases['neutral']['state'])==(256,210,1)
    for name,pos in (('right',(272,210)),('left',(240,210)),('down',(256,226)),('up',(256,194))):
        assert (cases[name]['x'],cases[name]['y'],cases[name]['state'])==(*pos,1),(name,cases[name])
    assert (cases['outside']['x'],cases['outside']['state'])==(336,1)
    assert (cases['return_and_start']['x'],cases['return_and_start']['state'])==(256,2)
    assert cases['start']['state']==2 and cases['title_keys_discarded']['game_x']==0x8000
    assert cases['play_keys']['game_x']>0x8000
    assert cases['p2_play_keys']['p2x']<0xa800
    assert cases['motion_2048']['x']==288
    # motion_256 is a characterization, not an assertion that loss must persist.
    assert cases['flush_timeout']['state']==3 and cases['flush_retry']['state']==2
    summary={'status':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_used_through':0x104+size,'cases':cases}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--boothush',required=True,type=Path);p.add_argument('--keep',type=Path);a=p.parse_args()
    if a.keep:a.keep.mkdir(parents=True,exist_ok=False);test(a.boothush,a.keep)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-title-') as d:test(a.boothush,Path(d))

if __name__=='__main__':main()
