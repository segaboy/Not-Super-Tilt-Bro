#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Test modeled two-character input, rendering and hit range in BootHush."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from build_mac_movement import build,DAMAGE
from build_mac_probe import be32
from test_mac_combat import FIGURE,PUNCH,PUNCH_LEFT,DUMMY,HEADER

# Frozen original placeholder rows for the second character's active poses.
P2PUNCH=(0x0ff0,0x1ff8,0x1ff8,0x0ff0,0x03c0,0x0ff0,0x1ff8,0x3fff,
         0x3fff,0x3fff,0x03cf,0x07e0,0x07e0,0x0e70,0x0e70,0x1c38,
         0x1c38,0x381c,0x381c,0x381c,0x700e,0x700e,0,0)
P2PUNCH_LEFT=(0x0ff0,0x1ff8,0x1ff8,0x0ff0,0x03c0,0x0ff0,0x1ff8,0xfffc,
              0xfffc,0xfffc,0xf3c0,0x07e0,0x07e0,0x0e70,0x0e70,0x1c38,
              0x1c38,0x381c,0x381c,0x381c,0x700e,0x700e,0,0)

def sha(data):return hashlib.sha256(data).hexdigest()
def decode(sample):
    b=bytes.fromhex(sample['memory']['bytes'])
    assert len(b)==58 and b[:8]==b'NST4\0\0\0\1'
    return {'x':int.from_bytes(b[16:18],'big'),'vbls':int.from_bytes(b[18:20],'big'),'phase':b[20],
            'height':int.from_bytes(b[28:30],'big'),'attack_clock':b[32],'facing':b[34],
            'damage':b[35],'attacks':b[36],'hits':b[37],
            'p2x':int.from_bytes(b[38:40],'big'),'p2held':b[40],'p2mask':b[41],
            'p2facing':b[42],'p2changes':b[43],
            'p2attack_clock':b[44],'p2button':b[45],'p1damage':b[46],'p2attacks':b[47],'p2hits':b[48],
            'p2jump_state':b[50],'p2jump_clock':b[51],'p2jump_vel':int.from_bytes(b[52:54],'big',signed=True),
            'p2height':int.from_bytes(b[54:56],'big'),'p2jump_button':b[56],'p2jump_count':b[57]}

def pixels(frame,s):
    assert frame.startswith(HEADER) and len(frame)==len(HEADER)+21888
    expected=bytearray(21888)
    for y in range(252,260):expected[y*64+16:y*64+48]=b'\xff'*32
    x=s['x']>>8;y=228-(s['height']>>8)
    figure=(PUNCH_LEFT if s['facing']==2 else PUNCH) if s['attack_clock'] in (7,8) else FIGURE
    for row,bits in enumerate(figure):
        at=(y+row)*64+16+x//8
        expected[at:at+3]=((bits<<8)>>(x%8)).to_bytes(3,'big')
    x2=s['p2x']>>8;y2=228-(s['p2height']>>8)
    target=(P2PUNCH_LEFT if s['p2facing']==2 else P2PUNCH) if s['p2attack_clock'] in (7,8) else DUMMY
    for row,bits in enumerate(target):
        at=(y2+row)*64+16+x2//8
        expected[at:at+3]=((bits<<8)>>(x2%8)).to_bytes(3,'big')
    lit=min(s['damage']//2,8);bar=(((1<<(lit*3))-1)<<(24-lit*3)) if lit else 0
    for row in range(y2-18,y2-12):
        at=row*64+16+x2//8;expected[at:at+3]=bar.to_bytes(3,'big')
    p1lit=min(s['p1damage']//2,8);p1bar=(((1<<(p1lit*3))-1)<<(24-p1lit*3)) if p1lit else 0
    for row in range(y-18,y-12):
        at=row*64+16+x//8;expected[at:at+3]=p1bar.to_bytes(3,'big')
    assert frame[len(HEADER):]==expected,('unexpected pixel or stale area',s)

def run(exe,rom,root,name,events,points,stop,native_p2=False,title_start=False):
    frames=root/(name+'.pbmseq');witness=root/(name+'.keyboard')
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles',str(stop),'--timeout-ms','20000',
         '--capture-series',str(frames),'--capture-memory','0xb00:90' if native_p2 else '0xb00:58','--keyboard-witness',str(witness)]
    if title_start:cmd+=['--mouse-button','2000000:1','--mouse-button','2400000:0']
    for p in points:cmd+=['--capture-vbl',str(p)]
    for cycle,key,down in events:cmd+=['--key',f'{cycle}:{key}:{down}']
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    data=json.loads(result.stdout);series=data['frame_series']
    assert data['status']=='cycle_limit' and series['rom_sha256']==sha(rom.read_bytes())
    assert series['executable_sha256']==sha(exe.read_bytes())
    assert (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])==(len(points),len(points),0,0,0)
    assert data['keyboard_witness']['dropped']==data['keyboard_witness']['rejected']==data['keyboard_witness']['pending']==0
    rows=[x.split() for x in witness.read_text(encoding='ascii').splitlines()[2:]]
    delivered=[(int(r[0]),int(r[3])) for r in rows if r[2]=='key_delivered']
    assert [v for _,v in delivered]==[(key<<1)|1|(0 if down else 128) for _,key,down in events]
    raw=frames.read_bytes();states=[]
    for sample in series['samples']:
        assert sample['processed'] and sample['image_available']
        memory=bytes.fromhex(sample['memory']['bytes'])
        if native_p2:
            assert len(memory)==90
            s=decode({'memory':{'bytes':memory[:58].hex()}})
            s['p2velocity']=int.from_bytes(memory[88:90],'big',signed=True)
        else:s=decode(sample)
        states.append(s);pixels(raw[sample['offset']:sample['offset']+sample['length']],s)
    checked=0;unserviced=0
    for a,b,old,new in zip(series['samples'],series['samples'][1:],states,states[1:]):
        if b['frame']!=a['frame']+1 or any(a['cycle']<=cycle<b['cycle'] for cycle,_ in delivered):continue
        if new['vbls']!=old['vbls']+1:unserviced+=1;continue
        x=old['p2x'];velocity=old.get('p2velocity',0)
        if old['phase']!=5 and old['p2attack_clock']==0:
            if native_p2:
                if old['p2held']==1 and velocity<0x200:velocity+=0x40
                elif old['p2held']==2 and velocity>-0x200:velocity-=0x40
                elif old['p2held']==0 and velocity>0:velocity=max(0,velocity-0x60)
                elif old['p2held']==0 and velocity<0:velocity=min(0,velocity+0x60)
                x=max(0x1000,min(0xe000,x+velocity))
            else:
                if old['p2held']==1:x=min(x+0x100,0xe000)
                if old['p2held']==2:x=max(x-0x100,0x1000)
        assert new['p2x']==x,(name,old,new)
        if native_p2:assert new['p2velocity']==velocity,(name,old,new)
        clock=old['p2attack_clock'];damage=old['p1damage'];hits=old['p2hits']
        if old['phase']!=5 and clock:
            clock+=1
            if clock==25:clock=0
            right_hit=new['p2facing']==1 and 0x1000<=new['x']-new['p2x']<=0x2000
            left_hit=new['p2facing']==2 and 0x1000<=new['p2x']-new['x']<=0x2000
            if clock==7 and new['height']==0 and (right_hit or left_hit):
                damage=min(damage+2,254);hits=(hits+1)&255
        assert (new['p2attack_clock'],new['p1damage'],new['p2hits'])==(clock,damage,hits),(name,old,new)
        state=old['p2jump_state'];jclock=old['p2jump_clock'];vel=old['p2jump_vel'];height=old['p2height']
        if old['phase']!=5:
            if state==1:
                jclock+=1
                if jclock==4:state=2;vel=0x480
            elif state==2:
                jclock+=1;vel=max(vel-0x60,-0x200)
                if jclock==8 and not old['p2jump_button']:vel=0x102
                height+=vel
                if height<=0:height=0;vel=0;state=0
        assert (new['p2jump_state'],new['p2jump_clock'],new['p2jump_vel'],new['p2height'])==(state,jclock,vel,height),(name,old,new)
        checked+=1
    assert unserviced==0,(name,unserviced)
    (root/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return {'command':cmd,'frame_series_sha256':sha(frames.read_bytes()),'keyboard_witness_sha256':sha(witness.read_bytes()),
            'events':events,'deliveries':delivered,'oracle_intervals':checked,'unserviced_intervals':unserviced,
            'observations':[{'vbl':p['frame'],'cycle':p['cycle'],**s} for p,s in zip(series['samples'],states)]}

def test(exe,root):
    image,size=build(jumping=True,combat=True,two_player=True);rom=root/'two-player.rom'
    with rom.open('xb') as f:f.write(image)
    points=list(range(5,32))+[34,37,40,43,46]
    scenarios={
      'neutral':([],points,6200000),
      'p2_right':([(600000,4,1),(2000000,4,0)],points,6200000),
      'p2_left':([(600000,5,1),(2000000,5,0)],points,6200000),
      'both':([(600000,0,1),(800000,5,1),(2000000,0,0),(2200000,5,0)],points,6200000),
      'p2_overlap':([(600000,4,1),(1600000,5,1),(2600000,5,0),(3600000,4,0)],points,6200000),
      'moving_target_hit':([(600000,5,1),(2000000,5,0),(2600000,3,1),(3000000,3,0)],points,6200000),
      'moving_target_miss':([(600000,4,1),(2000000,4,0),(2600000,3,1),(3000000,3,0)],points,6200000),
      'p2_hit':([(600000,5,1),(2000000,5,0),(2600000,6,1),(3000000,6,0)],points,6200000),
      'p2_miss':([(600000,6,1),(1000000,6,0)],points,6200000),
      'p2_wrong_facing':([(600000,5,1),(2000000,5,0),(2200000,4,1),(2350000,4,0),(2800000,6,1),(3100000,6,0)],points,6200000),
      'both_trade':([(600000,5,1),(2000000,5,0),(2600000,3,1),(2800000,6,1),(3100000,3,0),(3300000,6,0)],points,6200000),
      'p2_held_attack':([(600000,6,1)],points,6200000),
      'jump_evade':([(600000,5,1),(2000000,5,0),(2100000,2,1),(2300000,2,0),(2500000,6,1),(2800000,6,0)],points,6200000),
      'p2_jump':([(600000,7,1),(1200000,7,0)],points,6200000),
      'both_jump':([(600000,2,1),(800000,7,1),(1200000,2,0),(1400000,7,0)],points,6200000),
      'p2_jump_evade':([(600000,5,1),(2000000,5,0),(2100000,7,1),(2300000,7,0),(2500000,3,1),(2800000,3,0)],points,6200000),
      'p2_air_attack':([(600000,7,1),(900000,7,0),(1500000,6,1),(1800000,6,0)],points,6200000),
      'p2_jump_hold':([(600000,7,1)],points,6200000),
      'p2_running_jump':([(600000,5,1),(900000,7,1),(1400000,7,0),(3400000,5,0)],points,6200000),
      'p2_second_jump':([(600000,7,1),(900000,7,0),(6000000,7,1),(6300000,7,0)],list(range(5,21))+list(range(45,61)),8100000),
      'p2_two_hits':([(600000,5,1),(2000000,5,0),(2600000,6,1),(3000000,6,0),(7300000,6,1),(7700000,6,0)],
                     list(range(20,33))+list(range(56,75)),11000000),
      'p2_attack_lock':([(600000,5,1),(2000000,6,1),(2300000,6,0),(5500000,5,0)],points,6200000),
      'p2_right_bound':([(600000,4,1)],[100,140,180],24000000),
      'p2_left_bound':([(600000,5,1)],[200,240,280],37000000),
      'crossing':([(600000,5,1),(7000000,5,0)],list(range(35,67)),9000000),
    }
    cases={n:run(exe,rom,root,n,*args) for n,args in scenarios.items()}
    assert all(s['p2x']==0xa800 for s in cases['neutral']['observations'])
    assert cases['p2_right']['observations'][-1]['p2x']>0xa800
    assert cases['p2_left']['observations'][-1]['p2x']<0xa800
    assert cases['both']['observations'][-1]['x']>0x8000 and cases['both']['observations'][-1]['p2x']<0xa800
    overlap=cases['p2_overlap']['observations']
    assert any(s['p2held']==2 and s['p2mask']==3 for s in overlap)
    assert any(s['p2held']==1 and s['p2mask']==1 and s['p2changes']==3 for s in overlap)
    assert overlap[-1]['p2held']==overlap[-1]['p2mask']==0
    assert cases['moving_target_hit']['observations'][-1]['damage']==2 and cases['moving_target_hit']['observations'][-1]['hits']==1
    assert cases['moving_target_miss']['observations'][-1]['damage']==0
    assert cases['p2_hit']['observations'][-1]['p1damage']==2 and cases['p2_hit']['observations'][-1]['p2hits']==1
    assert cases['p2_miss']['observations'][-1]['p2attacks']==1 and cases['p2_miss']['observations'][-1]['p1damage']==0
    assert cases['p2_wrong_facing']['observations'][-1]['p2attacks']==1 and cases['p2_wrong_facing']['observations'][-1]['p1damage']==0
    assert cases['both_trade']['observations'][-1]['p1damage']==cases['both_trade']['observations'][-1]['damage']==2
    assert cases['p2_held_attack']['observations'][-1]['p2attacks']==1
    assert cases['jump_evade']['observations'][-1]['p2attacks']==1 and cases['jump_evade']['observations'][-1]['p1damage']==0
    assert max(s['p2height'] for s in cases['p2_jump']['observations'])>0
    assert any(s['height'] and s['p2height'] for s in cases['both_jump']['observations'])
    assert cases['p2_jump_evade']['observations'][-1]['attacks']==1 and cases['p2_jump_evade']['observations'][-1]['damage']==0
    assert cases['p2_air_attack']['observations'][-1]['p2attacks']==0
    assert cases['p2_jump_hold']['observations'][-1]['p2jump_count']==1 and cases['p2_jump_hold']['observations'][-1]['p2jump_button']==1
    assert any(s['p2height'] and s['p2x']<0xa800 for s in cases['p2_running_jump']['observations'])
    assert cases['p2_second_jump']['observations'][-1]['p2jump_count']==2
    assert cases['p2_two_hits']['observations'][-1]['p2hits']==2 and cases['p2_two_hits']['observations'][-1]['p1damage']==4
    locked=[s['p2x'] for s in cases['p2_attack_lock']['observations'] if 3<=s['p2attack_clock']<=22]
    assert len(locked)>=10 and len(set(locked))==1
    assert cases['p2_right_bound']['observations'][-1]['p2x']==0xe000
    assert cases['p2_left_bound']['observations'][-1]['p2x']==0x1000
    assert any(abs(s['p2x']-s['x'])<0x1000 for s in cases['crossing']['observations'])
    assert all(cases[n]['oracle_intervals']>=15 for n in scenarios if n not in ('p2_right_bound','p2_left_bound'))
    saturated,size_saturated=build(jumping=True,combat=True,two_player=True,initial_damage=254)
    saturated_rom=root/'damage-cap-fixture.rom'
    with saturated_rom.open('xb') as f:f.write(saturated)
    for name,events in (('p1_damage_cap',scenarios['moving_target_hit'][0]),
                        ('p2_damage_cap',scenarios['p2_hit'][0])):
        cases[name]=run(exe,saturated_rom,root,name,events,points,6200000)
    assert cases['p1_damage_cap']['observations'][-1]['damage']==254
    assert cases['p1_damage_cap']['observations'][-1]['hits']==1
    assert cases['p2_damage_cap']['observations'][-1]['p1damage']==254
    assert cases['p2_damage_cap']['observations'][-1]['p2hits']==1
    near_cap,_=build(jumping=True,combat=True,two_player=True,initial_damage=252)
    near_rom=root/'damage-near-cap-fixture.rom'
    with near_rom.open('xb') as f:f.write(near_cap)
    for name,events in (('p1_near_cap',scenarios['moving_target_hit'][0]),
                        ('p2_near_cap',scenarios['p2_hit'][0])):
        cases[name]=run(exe,near_rom,root,name,events,points,6200000)
    assert cases['p1_near_cap']['observations'][-1]['damage']==254
    assert cases['p1_near_cap']['observations'][-1]['hits']==1
    assert cases['p2_near_cap']['observations'][-1]['p1damage']==254
    assert cases['p2_near_cap']['observations'][-1]['p2hits']==1
    # Negative control: change the P1 hit's cap comparison so 254 wraps.
    needle=bytes.fromhex('0c3900fe')+be32(DAMAGE)
    assert saturated.count(needle)==1
    mutant=saturated.replace(needle,bytes.fromhex('0c3900fc')+be32(DAMAGE),1)
    mutant_rom=root/'damage-wrap-control.rom'
    with mutant_rom.open('xb') as f:f.write(mutant)
    control=run(exe,mutant_rom,root,'damage_wrap_control',scenarios['moving_target_hit'][0],points,6200000)
    assert control['observations'][-1]['damage']==0 and control['observations'][-1]['hits']==1
    summary={'result':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_bytes':len(image),'rom_used_through':0x104+size,'cases':cases,
             'damage_cap_fixture_sha256':sha(saturated),'damage_cap_fixture_used_through':0x104+size_saturated,
             'damage_near_cap_fixture_sha256':sha(near_cap),
             'damage_wrap_control_sha256':sha(mutant)}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('result','rom_sha256','boothush_sha256','rom_used_through')},indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--boothush',required=True,type=Path);p.add_argument('--keep',type=Path);a=p.parse_args()
    if a.keep:a.keep.mkdir(parents=True,exist_ok=False);test(a.boothush,a.keep)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-two-') as d:test(a.boothush,Path(d))

if __name__=='__main__':main()
