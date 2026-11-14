#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Capture original jump-experiment media from a bounded BootHush run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from build_mac_movement import build
from test_mac_jump import pixels, state


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(args):
    result = subprocess.run(args,capture_output=True,text=True,timeout=40,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return json.loads(result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boothush',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(); root=args.output
    root.mkdir(parents=True,exist_ok=False)
    image,_=build(jumping=True); rom=root/'jump.rom'
    with rom.open('xb') as stream: stream.write(image)
    sequence=root/'jump-stills.pbmseq'; video=root/'jump-original.y4m'
    cmd=[str(args.boothush),'--machine','mac128k','--rom',str(rom),'--cycles','6200000',
         '--timeout-ms','20000','--key','600000:0:1','--key','900000:2:1',
         '--key','1400000:2:0','--key','3400000:0:0',
         '--video',str(video),'--video-fps','30','--video-frames','30','--video-start','500000',
         '--capture-series',str(sequence),'--capture-memory','0xb00:32',
         '--keyboard-witness',str(root/'keyboard.txt'),'--display-witness',str(root/'display.txt')]
    for vbl in (8,12,20,30,43,46): cmd += ['--capture-vbl',str(vbl)]
    result=invoke(cmd)
    assert result['status']=='cycle_limit'
    assert 0 < result['video']['frames'] < 30 and not result['video']['truncated']
    assert result['frame_series']['rom_sha256']==digest(rom)
    assert result['frame_series']['executable_sha256']==digest(args.boothush)
    assert result['keyboard_witness']['accepted']==4 and result['keyboard_witness']['pending']==0
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['display_witness']['dropped']==0
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n',encoding='utf-8')
    raw=sequence.read_bytes()
    for sample in result['frame_series']['samples']:
        assert sample['processed'] and sample['image_available']
        frame=raw[sample['offset']:sample['offset']+sample['length']]
        pixels(frame,state(sample))
        pbm=root/f"jump-vbl-{sample['requested']}.pbm"
        with pbm.open('xb') as stream: stream.write(frame)
        invoke([str(args.boothush),'--convert-capture',str(pbm),'--output',str(pbm.with_suffix('.png'))])
    for extension in ('gif','mp4'):
        invoke([str(args.boothush),'--convert-capture',str(video),'--output',str(root/('jump.'+extension))])
    media={path.name:digest(path) for path in root.iterdir() if path.suffix in ('.png','.gif','.mp4')}
    (root/'media-sha256.json').write_text(json.dumps(media,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':digest(rom),'boothush_sha256':digest(args.boothush),
                      'video':result['video'],'media_sha256':media},indent=2))


if __name__=='__main__': main()
