#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Capture the modeled mouse title and keyboard-play transition."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from build_mac_movement import build
from build_mac_title import POINTER,title_pixels
from test_mac_two_player import HEADER,decode,pixels

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def invoke(cmd):
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return json.loads(result.stdout)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boothush',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=False)
    image,_=build(jumping=True,combat=True,two_player=True,title=True);rom=root/'title.rom'
    with rom.open('xb') as f:f.write(image)
    video=root/'title-original.y4m';frames=root/'title-stills.pbmseq'
    cmd=[str(a.boothush),'--machine','mac128k','--rom',str(rom),'--cycles','10000000','--timeout-ms','20000',
         '--mouse-dcd-invert','3','--mouse-motion','1000000:16:0',
         '--mouse-button','2000000:1','--mouse-button','2400000:0',
         '--key','3000000:5:1','--key','4400000:5:0','--key','5000000:3:1',
         '--key','5200000:6:1','--key','5500000:3:0','--key','5700000:6:0',
         '--video',str(video),'--video-fps','30','--video-frames','42','--video-start','500000',
         '--capture-series',str(frames),'--capture-memory','0xb00:80',
         '--keyboard-witness',str(root/'keyboard.txt'),'--display-witness',str(root/'display.txt')]
    points=(8,12,25,28,32,40,50,60,70)
    for vbl in points:cmd+=['--capture-vbl',str(vbl)]
    result=invoke(cmd);series=result['frame_series']
    assert result['status']=='cycle_limit' and 0<result['video']['frames']<42 and not result['video']['truncated']
    assert series['rom_sha256']==sha(rom) and series['executable_sha256']==sha(a.boothush)
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(len(points),len(points),0,0,0)
    assert result['keyboard_witness']['accepted']==6 and result['keyboard_witness']['pending']==0
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['display_witness']['dropped']==0
    assert result['mouse']['pending']==0
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n',encoding='utf-8')
    raw=frames.read_bytes()
    for sample in series['samples']:
        assert sample['processed'] and sample['image_available']
        frame=raw[sample['offset']:sample['offset']+sample['length']]
        data=bytes.fromhex(sample['memory']['bytes']);state=data[73]
        if state==1:
            x=int.from_bytes(data[64:66],'big');y=int.from_bytes(data[66:68],'big');expected=title_pixels()
            for row,bits in enumerate(POINTER):
                for col,bit in enumerate(bits):
                    if bit=='1':expected[(y+row)*64+(x+col)//8]^=0x80>>((x+col)%8)
            assert frame==HEADER+expected
        elif state==2:pixels(frame,decode({'memory':{'bytes':data[:58].hex()}}))
        else:raise AssertionError(('unexpected title state',state))
        pbm=root/f"title-vbl-{sample['requested']}.pbm"
        with pbm.open('xb') as f:f.write(frame)
        invoke([str(a.boothush),'--convert-capture',str(pbm),'--output',str(pbm.with_suffix('.png'))])
    for ext in ('gif','mp4'):invoke([str(a.boothush),'--convert-capture',str(video),'--output',str(root/('title.'+ext))])
    media={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.png','.gif','.mp4')}
    (root/'media-sha256.json').write_text(json.dumps(media,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':sha(rom),'boothush_sha256':sha(a.boothush),
                      'video':result['video'],'media_sha256':media},indent=2))

if __name__=='__main__':main()
