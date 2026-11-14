#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise movement, fixed-point state, images and modeled input in BootHush."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from build_mac_movement import build
from build_mac_run_transition import FIGURE

HEADER=b'P4\n512 342\n'

def sha(data): return hashlib.sha256(data).hexdigest()
def signed(value): return value if value<32768 else value-65536

def decode(sample):
    b=bytes.fromhex(sample['memory']['bytes'])
    assert len(b)==24 and b[:8]==b'NST4\0\0\0\1'
    return {'held':b[8], 'reply':b[9], 'entries':int.from_bytes(b[10:12],'big'),
            'ticks':int.from_bytes(b[12:14],'big'), 'velocity':signed(int.from_bytes(b[14:16],'big')),
            'position':int.from_bytes(b[16:18],'big'), 'vbls':int.from_bytes(b[18:20],'big'), 'phase':b[20],
            'timeouts':int.from_bytes(b[22:24],'big')}

def check_pixels(frame, state):
    assert frame.startswith(HEADER) and len(frame)==len(HEADER)+21888
    pix=frame[len(HEADER):]
    xpos=state['position']>>8
    expected_screen=bytearray(21888)
    for row,bits in enumerate(FIGURE):
        expected=((bits<<8)>>(xpos%8)).to_bytes(3,'big')
        offset=(228+row)*64+16+xpos//8
        expected_screen[offset:offset+3]=expected
    for y in range(252,260): expected_screen[y*64+16:y*64+48]=b'\xff'*32
    assert pix==expected_screen,('unexpected or stale pixels',xpos)

def simulate(state):
    v=state['velocity']
    if state['held']==1: v=min(v+0x40,0x200)
    elif state['held']==2: v=max(v-0x40,-0x200)
    elif v>0: v=max(v-0x60,0)
    elif v<0: v=min(v+0x60,0)
    return v,min(max(state['position']+v,0x1000),0xe000)

def run(exe,rom,root,name,events,points,stop,fault=None):
    image=root/(name+'.pbmseq')
    trace=root/(name+'.keyboard')
    display=root/(name+'.display')
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles',str(stop),
         '--timeout-ms','20000','--capture-series',str(image),'--capture-memory','0xb00:24',
         '--keyboard-witness',str(trace),'--display-witness',str(display)]
    for point in points: cmd += ['--capture-vbl',str(point)]
    for cycle,key,down in events: cmd += ['--key',f'{cycle}:{key}:{down}']
    if fault: cmd += ['--keyboard-fault',fault]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=25,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if proc.returncode: raise RuntimeError(proc.stdout+proc.stderr)
    result=json.loads(proc.stdout)
    series=result['frame_series']
    assert result['status']=='cycle_limit',result
    assert series['rom_sha256']==sha(rom.read_bytes())
    assert series['executable_sha256']==sha(exe.read_bytes())
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(len(points),len(points),0,0,0)
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['keyboard_witness']['pending']==0
    assert result['display_witness']['dropped']==0
    rows=[x.split() for x in trace.read_text(encoding='ascii').splitlines()[2:]]
    deliveries=[(int(r[0]),int(r[3])) for r in rows if r[2]=='key_delivered']
    assert [v for _,v in deliveries]==[(key<<1)|1|(0 if down else 128) for _,key,down in events],(name,deliveries)
    raw=image.read_bytes()
    states=[]; frames=[]
    for sample in series['samples']:
        assert sample['image_available'] and sample['processed']
        state=decode(sample); states.append(state)
        frame=raw[sample['offset']:sample['offset']+sample['length']]
        check_pixels(frame,state); frames.append(frame)
    # For intervals with no key delivery, independently check each 5/6 paced
    # update against the signed fixed-point reference model.
    checked=0
    for a,b,sa,sb in zip(series['samples'],series['samples'][1:],states,states[1:]):
        if fault or b['frame']!=a['frame']+1 or any(a['cycle']<=c<b['cycle'] for c,_ in deliveries): continue
        assert sb['vbls']==sa['vbls']+1,(name,sa,sb)
        should_tick=sa['phase']!=5
        assert sb['ticks']==sa['ticks']+int(should_tick),(name,sa,sb)
        expected=simulate(sa) if should_tick else (sa['velocity'],sa['position'])
        assert (sb['velocity'],sb['position'])==expected,(name,sa,sb,expected)
        checked+=1
    (root/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result,states,frames,deliveries,checked

def test(exe,root):
    image,size=build(); rom=root/'movement.rom'; rom.write_bytes(image)
    points=list(range(5,32))
    scenarios={
      'neutral':([],points,4300000),
      'right':([(600000,0,1),(2600000,0,0)],points,4300000),
      'right_repeat':([(600000,0,1),(2600000,0,0)],points,4300000),
      'left':([(600000,1,1),(2600000,1,0)],points,4300000),
      'reverse':([(600000,0,1),(1600000,1,1),(2600000,1,0)],points,4300000),
      'right_bound':([(600000,0,1)], [100,140,180],24000000),
      'left_bound':([(600000,1,1)], [100,140,180],24000000),
      'stall_recovery':([(600000,0,1),(2600000,0,0)],points,4300000,'20:1:1:0'),
      'reply_recovery':([(600000,0,1),(2600000,0,0)],points,4300000,'20:1:2:0'),
    }
    cases={name:run(exe,rom,root,name,*args) for name,args in scenarios.items()}
    assert cases['right'][:4]==cases['right_repeat'][:4]
    assert all(s['position']==0x8000 and s['velocity']==0 for s in cases['neutral'][1])
    right=cases['right'][1]; left=cases['left'][1]; rev=cases['reverse'][1]
    assert max(s['position'] for s in right)>0x8000 and min(s['position'] for s in left)<0x8000
    assert any(s['velocity']==0x200 for s in right) and any(s['velocity']==-0x200 for s in left)
    assert right[-1]['held']==left[-1]['held']==0 and right[-1]['velocity']==left[-1]['velocity']==0
    assert any(s['held']==2 and s['velocity']<0 for s in rev)
    assert cases['right_bound'][1][-1]['position']==0xe000
    assert cases['left_bound'][1][-1]['position']==0x1000
    for name in ('stall_recovery','reply_recovery'):
        result,states,_,deliveries,_=cases[name]
        assert result['keyboard_fault']['triggered'] and states[-1]['timeouts']>=1,(name,result,states[-1])
        assert states[-1]['ticks']>5 and states[-1]['position']>0x8000 and len(deliveries)==2,(name,states[-1])
    assert all(s['timeouts']==0 for n in ('neutral','right','left','reverse') for s in cases[n][1])
    assert all(cases[n][4]>=20 for n in ('neutral','right','left','reverse'))
    summary={'result':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_bytes':len(image),'rom_used_through':0x104+size,'cases':{}}
    for name,(result,states,frames,deliveries,checked) in cases.items():
        summary['cases'][name]={'events':scenarios[name][0], 'deliveries':deliveries,
            'checks_against_reference':checked,'observations':[{'vbl':s['frame'],'cycle':s['cycle'],**state}
            for s,state in zip(result['frame_series']['samples'],states)]}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--boothush',type=Path,required=True)
    p.add_argument('--keep',type=Path); a=p.parse_args()
    if a.keep:
        a.keep.mkdir(parents=True,exist_ok=False); test(a.boothush,a.keep)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-movement-') as t: test(a.boothush,Path(t))

if __name__=='__main__': main()
