#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Capture a bounded two-character prototype scenario in BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from build_mac_movement import build
from test_mac_two_player import decode, pixels


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def invoke(cmd):
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=40,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return json.loads(result.stdout)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boothush',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=False)
    image,_=build(jumping=True,combat=True,two_player=True);rom=root/'two-player.rom'
    with rom.open('xb') as f:f.write(image)
    frames=root/'two-player-stills.pbmseq';video=root/'two-player-original.y4m'
    cmd=[str(a.boothush),'--machine','mac128k','--rom',str(rom),'--cycles','9000000','--timeout-ms','20000',
         '--key','600000:5:1','--key','2000000:5:0','--key','2600000:3:1','--key','2800000:6:1',
         '--key','3100000:3:0','--key','3300000:6:0',
         '--video',str(video),'--video-fps','30','--video-frames','40','--video-start','500000',
         '--capture-series',str(frames),'--capture-memory','0xb00:58',
         '--keyboard-witness',str(root/'keyboard.txt'),'--display-witness',str(root/'display.txt')]
    points=(5,12,18,22,28,32,36,40,46,55,62,68)
    for vbl in points:cmd+=['--capture-vbl',str(vbl)]
    result=invoke(cmd);series=result['frame_series']
    assert result['status']=='cycle_limit' and 0<result['video']['frames']<40 and not result['video']['truncated']
    assert series['rom_sha256']==sha(rom) and series['executable_sha256']==sha(a.boothush)
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(len(points),len(points),0,0,0)
    assert result['keyboard_witness']['accepted']==6 and result['keyboard_witness']['pending']==0
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['display_witness']['dropped']==0
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n',encoding='utf-8')
    raw=frames.read_bytes()
    for sample in series['samples']:
        assert sample['processed'] and sample['image_available']
        data=raw[sample['offset']:sample['offset']+sample['length']]
        pixels(data,decode(sample))
        pbm=root/f"two-player-vbl-{sample['requested']}.pbm"
        with pbm.open('xb') as f:f.write(data)
        invoke([str(a.boothush),'--convert-capture',str(pbm),'--output',str(pbm.with_suffix('.png'))])
    for extension in ('gif','mp4'):
        invoke([str(a.boothush),'--convert-capture',str(video),'--output',str(root/('two-player.'+extension))])
    media={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.png','.gif','.mp4')}
    (root/'media-sha256.json').write_text(json.dumps(media,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':sha(rom),'boothush_sha256':sha(a.boothush),
                      'video':result['video'],'media_sha256':media},indent=2))


if __name__=='__main__':main()
