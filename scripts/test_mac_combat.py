#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Exercise an original training target and bounded jab in BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from build_mac_movement import build

# Frozen expected geometric rows; these are original placeholder art, not
# data extracted from the game or the ROM under test.
FIGURE=(0x03c0,0x07e0,0x07e0,0x03c0,0x0180,0x07e0,0x0ff0,0x1db8,
        0x1998,0x1998,0x0180,0x03c0,0x03c0,0x0660,0x0660,0x0c30,
        0x0c30,0x1818,0x1818,0x1818,0x381c,0x381c,0,0)
PUNCH=(0x03c0,0x07e0,0x07e0,0x03c0,0x0180,0x07e0,0x0ff0,0x1dbf,
       0x199f,0x199f,0x018f,0x03c0,0x03c0,0x0660,0x0660,0x0c30,
       0x0c30,0x1818,0x1818,0x1818,0x381c,0x381c,0,0)
PUNCH_LEFT=(0x03c0,0x07e0,0x07e0,0x03c0,0x0180,0x07e0,0x0ff0,0xfdb8,
            0xf998,0xf998,0xf180,0x03c0,0x03c0,0x0660,0x0660,0x0c30,
            0x0c30,0x1818,0x1818,0x1818,0x381c,0x381c,0,0)
DUMMY=(0x0ff0,0x1ff8,0x1ff8,0x0ff0,0x03c0,0x0ff0,0x1ff8,0x3ffc,
       0x3ffc,0x3ffc,0x03c0,0x07e0,0x07e0,0x0e70,0x0e70,0x1c38,
       0x1c38,0x381c,0x381c,0x381c,0x700e,0x700e,0,0)

HEADER=b'P4\n512 342\n'
def sha(data): return hashlib.sha256(data).hexdigest()

def decode(sample):
    b=bytes.fromhex(sample['memory']['bytes'])
    assert len(b)==38 and b[:8]==b'NST4\0\0\0\1'
    return {'x':int.from_bytes(b[16:18],'big'),'vbls':int.from_bytes(b[18:20],'big'),'phase':b[20],
            'height':int.from_bytes(b[28:30],'big'),
            'jump_state':b[24],'attack_clock':b[32],'attack_button':b[33],
            'facing':b[34],'damage':b[35],'attacks':b[36],'hits':b[37]}

def check_pixels(frame,s):
    assert frame.startswith(HEADER) and len(frame)==len(HEADER)+21888
    expected=bytearray(21888)
    for y in range(252,260): expected[y*64+16:y*64+48]=b'\xff'*32
    x=s['x']>>8; y=228-(s['height']>>8)
    assert 0<=y<=228
    figure=(PUNCH_LEFT if s['facing']==2 else PUNCH) if s['attack_clock'] in (7,8) else FIGURE
    for row,bits in enumerate(figure):
        offset=(y+row)*64+16+x//8
        expected[offset:offset+3]=((bits<<8)>>(x%8)).to_bytes(3,'big')
    # The stationary target deliberately draws after the player in this
    # prototype, so it owns the two bytes where placeholder figures overlap.
    for row,bits in enumerate(DUMMY):
        offset=(228+row)*64+37
        expected[offset:offset+2]=bits.to_bytes(2,'big')
    assert frame[len(HEADER):]==expected,('unexpected combat pixels',s)

def run(exe,rom,root,name,events,points,stop):
    frames=root/(name+'.pbmseq'); witness=root/(name+'.keyboard')
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles',str(stop),'--timeout-ms','20000',
         '--capture-series',str(frames),'--capture-memory','0xb00:38','--keyboard-witness',str(witness)]
    for p in points: cmd+=['--capture-vbl',str(p)]
    for cycle,key,down in events: cmd+=['--key',f'{cycle}:{key}:{down}']
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    result=json.loads(p.stdout); series=result['frame_series']
    assert result['status']=='cycle_limit' and series['rom_sha256']==sha(rom.read_bytes())
    assert series['executable_sha256']==sha(exe.read_bytes())
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(len(points),len(points),0,0,0)
    assert result['keyboard_witness']['dropped']==result['keyboard_witness']['rejected']==result['keyboard_witness']['pending']==0
    rows=[x.split() for x in witness.read_text(encoding='ascii').splitlines()[2:]]
    deliveries=[(int(r[0]),int(r[3])) for r in rows if r[2]=='key_delivered']
    assert [v for _,v in deliveries]==[(key<<1)|1|(0 if down else 128) for _,key,down in events]
    data=frames.read_bytes(); observed=[]
    for sample in series['samples']:
        assert sample['processed'] and sample['image_available']
        s=decode(sample);observed.append(s)
        check_pixels(data[sample['offset']:sample['offset']+sample['length']],s)
    checked=0; unserviced=0
    for a,b,old,new in zip(series['samples'],series['samples'][1:],observed,observed[1:]):
        if b['frame']!=a['frame']+1 or any(a['cycle']<=cycle<b['cycle'] for cycle,_ in deliveries):
            continue
        if new['vbls'] != old['vbls']+1:
            unserviced+=1
            continue
        clock=old['attack_clock']; damage=old['damage'];hits=old['hits']
        if old['phase']!=5 and clock:
            clock+=1
            if clock==25: clock=0
            right_hit=new['facing']==1 and 0x8800<=new['x']<=0x9800
            left_hit=new['facing']==2 and 0xb800<=new['x']<=0xc800
            if clock==7 and (right_hit or left_hit):
                damage=(damage+2)&255;hits=(hits+1)&255
        assert (new['attack_clock'],new['damage'],new['hits'])==(clock,damage,hits), (name,old,new)
        checked+=1
    assert unserviced==0,(name,'unserviced sampled VBL intervals',unserviced)
    (root/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return {'events':events,'deliveries':deliveries,'oracle_intervals':checked,'unserviced_intervals':unserviced,
            'observations':[{'vbl':p['frame'],'cycle':p['cycle'],**s} for p,s in zip(series['samples'],observed)]}

def test(exe,root):
    image,size=build(jumping=True,combat=True);rom=root/'combat.rom'
    with rom.open('xb') as f:f.write(image)
    points=list(range(5,32))+[34,37,40,43,46]
    approaches=[(600000,0,1),(1900000,0,0)]
    scenarios={
      'miss': ([(600000,3,1),(1000000,3,0)],points,6200000),
      'hit': (approaches+[(2600000,3,1),(3000000,3,0)],points,6200000),
      'wrong_facing': (approaches+[(2200000,1,1),(2350000,1,0),(2800000,3,1),(3100000,3,0)],points,6200000),
      'airborne': ([(600000,2,1),(900000,2,0),(1500000,3,1),(1800000,3,0)],points,6200000),
      'held_attack': ([(600000,3,1)],points,6200000),
      'two_hits': (approaches+[(2600000,3,1),(3000000,3,0),(7300000,3,1),(7700000,3,0)],
                   list(range(20,33))+list(range(56,75)),11000000),
      'left_hit': ([(600000,0,1),(5500000,0,0),(6300000,1,1),(6450000,1,0),(7200000,3,1),(7600000,3,0)],
                   [5]+list(range(56,87)),12000000),
    }
    cases={n:run(exe,rom,root,n,*v) for n,v in scenarios.items()}
    assert cases['miss']['observations'][-1]['attacks']==1 and cases['miss']['observations'][-1]['damage']==0
    assert cases['hit']['observations'][-1]['attacks']==1 and cases['hit']['observations'][-1]['damage']==2
    assert cases['hit']['observations'][-1]['hits']==1
    assert any(s['attack_clock']==7 and s['hits']==1 and 0x8800<=s['x']<=0x9800 for s in cases['hit']['observations'])
    assert cases['wrong_facing']['observations'][-1]['attacks']==1 and cases['wrong_facing']['observations'][-1]['damage']==0
    assert any(s['attack_clock'] in (7,8) and s['facing']==2 for s in cases['wrong_facing']['observations'])
    assert cases['airborne']['observations'][-1]['attacks']==0
    assert cases['held_attack']['observations'][-1]['attacks']==1
    assert cases['two_hits']['observations'][-1]['attacks']==2 and cases['two_hits']['observations'][-1]['damage']==4
    assert cases['two_hits']['observations'][-1]['hits']==2
    assert cases['left_hit']['observations'][-1]['facing']==2 and cases['left_hit']['observations'][-1]['damage']==2
    assert any(s['attack_clock']==7 and s['hits']==1 and 0xb800<=s['x']<=0xc800 for s in cases['left_hit']['observations'])
    assert all(cases[n]['oracle_intervals']>=15 for n in ('miss','hit','wrong_facing','airborne','held_attack'))
    assert all(cases[n]['oracle_intervals']>=20 for n in ('two_hits','left_hit'))
    summary={'result':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_bytes':len(image),'rom_used_through':0x104+size,'cases':cases}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('result','rom_sha256','boothush_sha256','rom_used_through')},indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--boothush',required=True,type=Path);p.add_argument('--keep',type=Path);a=p.parse_args()
    if a.keep:a.keep.mkdir(parents=True,exist_ok=False);test(a.boothush,a.keep)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-combat-') as d:test(a.boothush,Path(d))

if __name__=='__main__':main()
