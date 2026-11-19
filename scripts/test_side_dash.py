#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Drive Sinbad's grounded side tilt on both controllers, with frame-by-frame checks."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

from test_mac_two_player import decode, pixels


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('boothush','rom','output'):
        parser.add_argument('--'+key, required=True, type=Path)
    parser.add_argument('--gif',action='store_true',help='save the two captured P1-right sequences as a gameplay GIF')
    parser.add_argument('--stationary-rom',type=Path,help='compare identical input against the preceding title build')
    args = parser.parse_args()
    exe,rom = (p.resolve(strict=True) for p in (args.boothush,args.rom))
    out = args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    identities = {'rom_sha256':digest(rom.read_bytes()),'executable_sha256':digest(exe.read_bytes())}

    def capture(name,events,index,vbls,selected=rom):
        frames,witness = out/(name+'.pbmseq'),out/(name+'.keys')
        cmd = [str(exe),'--machine','mac128k','--rom',str(selected),'--cycles','14000000',
               '--timeout-ms','20000','--mouse-button','2000000:1','--mouse-button','2400000:0',
               '--capture-memory','0xb00:113','--capture-series',str(frames),'--keyboard-witness',str(witness)]
        for frame in vbls:cmd += ['--capture-vbl',str(frame)]
        for cycle,key,down in events:cmd += ['--key',f'{cycle}:{key}:{down}']
        run = subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=30,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (out/(name+'.json')).write_text(run.stdout,encoding='utf-8')
        data=json.loads(run.stdout)
        series=data['frame_series']
        assert data['status']=='cycle_limit' and series['rom_sha256']==digest(selected.read_bytes())
        assert series['executable_sha256']==identities['executable_sha256']
        assert series['processed']==len(vbls) and not any(series[k] for k in ('pending','missing_images','dropped'))
        assert not any(data['keyboard_witness'][k] for k in ('pending','rejected','dropped'))
        deliveries = [int(parts[3]) for row in witness.read_text().splitlines()[2:]
                      if (parts:=row.split())[2]=='key_delivered']
        assert deliveries==[(key<<1)|1|(0 if down else 128) for _,key,down in events]
        blob=frames.read_bytes()
        rows=[]
        for sample in series['samples']:
            mem=bytes.fromhex(sample['memory']['bytes'])
            assert len(mem)==113 and mem[73]==2
            state=decode({'memory':{'bytes':mem[:58].hex()}})
            pixels(blob[sample['offset']:sample['offset']+sample['length']],state)
            vel=14 if index==0 else 88
            side=101+2*index
            rows.append(dict(frame=sample['frame'],phase=state['phase'],side=mem[side],
                             clock=mem[side+1],fresh=mem[105+index],speed=int.from_bytes(mem[vel:vel+2],'big',signed=True),
                             x=state['x' if index==0 else 'p2x'],facing=state['facing' if index==0 else 'p2facing'],
                             jump=mem[24 if index==0 else 50],jump_count=mem[31 if index==0 else 57],
                             hits=state['hits' if index==0 else 'p2hits'],damage=state['damage' if index==0 else 'p1damage']))
        return rows

    results={}
    for index,positive,negative,attack in ((0,0,1,3),(1,4,5,6)):
        for sign,forward,reverse in ((1,positive,negative),(-1,negative,positive)):
            # Place the defender in reach of the moving hit frame for two cases.
            toward = (index==0 and sign==1) or (index==1 and sign==-1)
            away = 4 if index==0 else 1
            setup = [(3150000,away,1),(4800000,away,0)] if toward else []
            events = sorted(setup+[(5000000,forward,1),(5300000,attack,1),(5600000,attack,0),
                                   (5900000,forward,0),(6400000,reverse,1)])
            name=f'p{index+1}_'+('right' if sign>0 else 'left')
            rows = capture(name+'-start',events,index,range(37,69))
            rows += capture(name+'-end',events,index,range(69,101))
            active=[s for s in rows if s['side']]
            assert {s['side'] for s in active}=={1,2,3}
            assert active[0]['speed']==sign*256 and active[0]['side']==1
            assert all(s['facing']==(1 if sign>0 else 2) for s in active)
            assert max(sign*s['speed'] for s in active)==682
            windup_x=active[0]['x']
            recovered=next(s for s in active if s['side']==3 and s['speed']==0)
            assert (recovered['x']-windup_x)*sign > 50*256
            checked=0
            for old,new in zip(rows,rows[1:]):
                if not old['side']:continue
                v=old['speed']
                x=old['x']
                if old['phase']!=5:
                    if not old['fresh'] and old['clock']!=1:
                        v=(sign*max(0,sign*v-96) if old['side']==3 else
                           sign*min(682,sign*v+64) if v else 0)
                    x=max(0x1000,min(0xe000,x+v))
                assert (new['speed'],new['x'])==(v,x),(name,old,new)
                checked+=1
            after=[s for s in rows if s['frame']>active[-1]['frame']]
            assert any(s['facing']==(2 if sign>0 else 1) and s['speed']*sign<0 for s in after)
            if toward:assert rows[-1]['hits']==1 and rows[-1]['damage']==2,(name,rows[-1])
            else:assert rows[-1]['hits']==0
            results[name]={'events':events,'checked_intervals':checked,
                           'travel':(recovered['x']-windup_x)*sign,'rows':rows}
            if toward:
                if args.stationary_rom:
                    prior=capture(name+'-stationary',events,index,range(45,77),args.stationary_rom)
                    assert {s['speed'] for s in prior if s['side']}=={0}
                    assert prior[-1]['hits']==0 and prior[-1]['damage']==0
                    results[name]['stationary_sha256']=digest(args.stationary_rom.read_bytes())
                jump=2 if index==0 else 7
                jump_events=events+[(10300000,jump,1)]
                cancel=capture(name+'-jump',jump_events,index,range(69,101))
                entry=next((old,new) for old,new in zip(cancel,cancel[1:]) if old['side']==3 and new['jump']==1)
                assert entry[0]['clock']<14 and entry[1]['side']==0
                assert cancel[-1]['jump_count']==1 and any(s['jump']==2 for s in cancel)
                results[name+'-jump']={'events':jump_events,'rows':cancel}
    if args.gif:
        from PIL import Image, ImageDraw
        rendered=[]
        for suffix in ('start','end'):
            case='p1_right-'+suffix
            samples=json.loads((out/(case+'.json')).read_text(encoding='utf-8'))['frame_series']['samples']
            blob=(out/(case+'.pbmseq')).read_bytes()
            for sample in samples:
                pic=Image.open(io.BytesIO(blob[sample['offset']:sample['offset']+sample['length']]))
                zoom=pic.crop((128,170,384,274)).resize((768,312),Image.Resampling.NEAREST)
                canvas=Image.new('RGB',(768,342),'white')
                canvas.paste(zoom,(0,0))
                state=results['p1_right']['rows'][sample['frame']-37]
                phase=('Run','Windup','Strike','Recovery')[state['side']]
                ImageDraw.Draw(canvas).text((12,320),f"P1 side tilt | {phase} | speed {state['speed']}/256 px per tick | P2 damage {state['damage']} | VBL {state['frame']}",fill='black')
                rendered.append(canvas)
        rendered[0].save(out/'side-dash.gif',save_all=True,append_images=rendered[1:],duration=70,loop=0,disposal=2)
    report=dict(status='pass',**identities,cases=results)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({**identities,'cases':len(results),'status':'pass'}))


if __name__=='__main__':
    main()
