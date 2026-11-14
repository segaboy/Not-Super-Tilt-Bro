#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Capture a bounded original training-target jab in BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from build_mac_movement import build
from test_mac_combat import decode, check_pixels


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def invoke(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=40,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    return json.loads(r.stdout)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boothush',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=False)
    image,_=build(jumping=True,combat=True);rom=root/'combat.rom'
    with rom.open('xb') as f:f.write(image)
    frames=root/'combat-stills.pbmseq';video=root/'combat-original.y4m'
    cmd=[str(a.boothush),'--machine','mac128k','--rom',str(rom),'--cycles','6200000','--timeout-ms','20000',
         '--key','600000:0:1','--key','1900000:0:0','--key','2600000:3:1','--key','3000000:3:0',
         '--video',str(video),'--video-fps','30','--video-frames','30','--video-start','500000',
         '--capture-series',str(frames),'--capture-memory','0xb00:38',
         '--keyboard-witness',str(root/'keyboard.txt'),'--display-witness',str(root/'display.txt')]
    for vbl in (5,16,20,26,28,30,37,46):cmd+=['--capture-vbl',str(vbl)]
    result=invoke(cmd);series=result['frame_series']
    assert result['status']=='cycle_limit' and 0<result['video']['frames']<30 and not result['video']['truncated']
    assert series['rom_sha256']==sha(rom) and series['executable_sha256']==sha(a.boothush)
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(8,8,0,0,0)
    assert result['keyboard_witness']['accepted']==4 and result['keyboard_witness']['pending']==0
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['display_witness']['dropped']==0
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n',encoding='utf-8')
    raw=frames.read_bytes()
    for sample in series['samples']:
        assert sample['processed'] and sample['image_available']
        data=raw[sample['offset']:sample['offset']+sample['length']]
        check_pixels(data,decode(sample))
        pbm=root/f"combat-vbl-{sample['requested']}.pbm"
        with pbm.open('xb') as f:f.write(data)
        invoke([str(a.boothush),'--convert-capture',str(pbm),'--output',str(pbm.with_suffix('.png'))])
    for extension in ('gif','mp4'):
        invoke([str(a.boothush),'--convert-capture',str(video),'--output',str(root/('combat.'+extension))])
    media={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.png','.gif','.mp4')}
    (root/'media-sha256.json').write_text(json.dumps(media,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':sha(rom),'boothush_sha256':sha(a.boothush),
                      'video':result['video'],'media_sha256':media},indent=2))

if __name__=='__main__':main()
