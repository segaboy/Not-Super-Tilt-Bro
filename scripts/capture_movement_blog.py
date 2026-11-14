#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture reproducible, silent Mac movement media directly from BootHush."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from build_mac_movement import build

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--boothush',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path,help='new directory')
    a=p.parse_args(); root=a.output; root.mkdir(parents=True,exist_ok=False)
    image,_=build(); rom=root/'movement.rom'; rom.write_bytes(image)
    series=root/'movement-stills.pbmseq'; video=root/'movement-original.y4m'
    cmd=[str(a.boothush),'--machine','mac128k','--rom',str(rom),'--cycles','27000000',
         '--timeout-ms','20000','--key','800000:0:1','--key','9000000:0:0',
         '--key','11000000:1:1','--key','20000000:1:0','--video',str(video),
         '--video-fps','30','--video-frames','110','--video-start','500000',
         '--capture-series',str(series),'--capture-memory','0xb00:24',
         '--capture-vbl','6','--capture-vbl','55','--capture-vbl','100','--capture-vbl','165',
         '--keyboard-witness',str(root/'keyboard.txt'),'--display-witness',str(root/'display.txt')]
    def invoke(args):
        r=subprocess.run(args,capture_output=True,text=True,timeout=40,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if r.returncode: raise RuntimeError(r.stdout+r.stderr)
        return json.loads(r.stdout)
    result=invoke(cmd)
    digest=lambda x: hashlib.sha256(x.read_bytes()).hexdigest()
    assert result['status']=='cycle_limit' and result['video']['frames']==102 and not result['video']['truncated']
    assert result['keyboard_witness']['accepted']==4 and result['keyboard_witness']['pending']==0
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['display_witness']['dropped']==0
    assert result['frame_series']['rom_sha256']==digest(rom)
    assert result['frame_series']['executable_sha256']==digest(a.boothush)
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n',encoding='utf-8')
    raw=series.read_bytes()
    for s in result['frame_series']['samples']:
        assert s['image_available'] and s['processed']
        pbm=root/f"mac-vbl-{s['requested']}.pbm"
        pbm.write_bytes(raw[s['offset']:s['offset']+s['length']])
        invoke([str(a.boothush),'--convert-capture',str(pbm),'--output',str(pbm.with_suffix('.png'))])
    for extension in ('gif','mp4'):
        invoke([str(a.boothush),'--convert-capture',str(video),'--output',str(root/('mac-movement.'+extension))])
    media={f.name:digest(f) for f in root.iterdir() if f.suffix in ('.png','.gif','.mp4')}
    (root/'media-sha256.json').write_text(json.dumps(media,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':digest(rom),'boothush_sha256':digest(a.boothush),
                      'video':result['video'],'media_sha256':media},indent=2))

if __name__=='__main__': main()
