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
    if any(kind in ('mouse-motion','window-mouse') for kind,_ in events):cmd+=['--mouse-dcd-invert','3']
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
            'p2x':int.from_bytes(b[38:40],'big'),'p1_jumps':b[31],'p1_attacks':b[36],
            'p2_jumps':b[57],'p2_attacks':b[47],'frame_sha256':sha(image)}

def animation(exe,rom,root):
    frames=root/'in_motion.pbmseq'
    trace=root/'in_motion.bhmouse'
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles','1400000','--timeout-ms','20000',
         '--mouse-dcd-invert','3','--mouse-edge-cycles','1024','--mouse-motion','1000000:32:0',
         '--mouse-record',str(trace),'--capture-series',str(frames),'--capture-memory','0xb00:86']
    for cycle in range(1000000,1110000,5000):cmd+=['--capture-cycle',str(cycle)]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    data=json.loads(result.stdout);series=data['frame_series']
    assert data['status']=='cycle_limit' and data['mouse']['pending']==0
    assert (series['requested'],series['processed'],series['pending'],series['dropped'])==(22,22,0,0)
    displayed=[int.from_bytes(bytes.fromhex(s['memory']['bytes'])[80:82],'big') for s in series['samples']]
    assert any(256<x<288 for x in displayed) and displayed[-1]==288,displayed
    replay_frames=root/'in_motion_replay.pbmseq'
    replay_cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles','1400000','--timeout-ms','20000',
                '--mouse-replay',str(trace),'--capture-series',str(replay_frames),'--capture-memory','0xb00:86']
    for cycle in range(1000000,1110000,5000):replay_cmd+=['--capture-cycle',str(cycle)]
    replay=subprocess.run(replay_cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if replay.returncode:raise RuntimeError('title replay: '+replay.stdout+replay.stderr)
    replay_data=json.loads(replay.stdout);replay_series=replay_data['frame_series']
    assert replay_data['cycles']==data['cycles'] and replay_data['mouse']==data['mouse']
    assert (replay_series['processed'],replay_series['pending'])==(22,0)
    assert replay_frames.read_bytes()==frames.read_bytes()
    assert [(s['cycle'],s['memory']) for s in replay_series['samples']]==[(s['cycle'],s['memory']) for s in series['samples']]
    (root/'in_motion.json').write_text(json.dumps({'command':cmd,'result':data,'displayed_x':displayed},indent=2)+'\n',encoding='utf-8')
    (root/'in_motion_replay.json').write_text(json.dumps({'command':replay_cmd,'result':replay_data,
        'trace_sha256':sha(trace.read_bytes()),'frames_sha256':sha(replay_frames.read_bytes())},indent=2)+'\n',encoding='utf-8')
    return displayed


def handoff_replay(exe,rom,root):
    """Replay mouse title input alongside the same scheduled gameplay key."""
    trace=root/'handoff.bhmouse'
    captures=[1200000,2200000,3000000,4000000,6000000]
    common=['--machine','mac128k','--rom',str(rom),'--cycles','7000000','--timeout-ms','20000',
            '--capture-memory','0xb00:86']
    records=[]
    for name,mouse in (
        ('handoff_record',['--mouse-dcd-invert','3','--mouse-motion','1000000:16:0',
                           '--mouse-button','2000000:1','--mouse-button','2400000:0',
                           '--mouse-record',str(trace)]),
        ('handoff_replay',['--mouse-replay',str(trace)])):
        frames=root/(name+'.pbmseq');witness=root/(name+'.keyboard')
        cmd=[str(exe),*common,*mouse,'--key','3500000:0:1','--key','4500000:0:0',
             '--capture-series',str(frames),'--keyboard-witness',str(witness)]
        for cycle in captures:cmd+=['--capture-cycle',str(cycle)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise RuntimeError(name+': '+result.stdout+result.stderr)
        data=json.loads(result.stdout);series=data['frame_series']
        assert data['status']=='cycle_limit' and data['mouse']['pending']==0
        assert (series['requested'],series['processed'],series['pending'],series['dropped'])==(5,5,0,0)
        assert data['keyboard_witness']['rejected']==data['keyboard_witness']['pending']==data['keyboard_witness']['dropped']==0
        snapshots=[(s['cycle'],s['memory']) for s in series['samples']]
        (root/(name+'.json')).write_text(json.dumps({'command':cmd,'result':data,
            'frames_sha256':sha(frames.read_bytes())},indent=2)+'\n',encoding='utf-8')
        records.append((data,snapshots,frames.read_bytes()))
    first,second=records
    assert first[0]['cycles']==second[0]['cycles'] and first[0]['mouse']==second[0]['mouse']
    assert first[1:]==second[1:]
    final=bytes.fromhex(first[1][-1][1]['bytes'])
    assert final[73]==2 and int.from_bytes(final[16:18],'big')>0x8000
    return {'trace_sha256':sha(trace.read_bytes()),'frames_sha256':sha(first[2]),
            'final_game_x':int.from_bytes(final[16:18],'big')}

def test(exe,root,native_movement=None,native_p2=False):
    image,size=build(jumping=True,combat=True,two_player=True,title=True,native_movement=native_movement,native_p2=native_p2);rom=root/'title.rom'
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
      'window_outside':([('window-mouse','1200000:256:210:0'),('window-mouse','2000000:336:210:0'),
                         ('window-mouse','4000000:336:210:1'),('window-mouse','4400000:336:210:3')],7000000),
      'window_return_and_play':([('window-mouse','1200000:256:210:0'),('window-mouse','2000000:336:210:0'),
                                 ('window-mouse','4000000:336:210:1'),('window-mouse','4400000:336:210:3'),
                                 ('window-mouse','5000000:256:210:0'),('window-mouse','7000000:256:210:1'),
                                 ('window-mouse','7400000:256:210:3'),('key','9000000:0:1'),
                                 ('key','10000000:0:0')],12000000),
      'start':([('mouse-button','2000000:1'),('mouse-button','2400000:0')],7000000),
      'title_keys_discarded':([('key','1000000:0:1'),('key','1300000:0:0'),('mouse-button','2000000:1'),('mouse-button','2400000:0')],7000000),
      'play_keys':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:0:1'),('key','4500000:0:0')],7000000),
      'p2_play_keys':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:5:1'),('key','4500000:5:0')],7000000),
      'p1_jump':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:2:1'),('key','4500000:2:0')],7000000),
      'p2_jump':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:7:1'),('key','4500000:7:0')],7000000),
      'p1_attack':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:3:1'),('key','4500000:3:0')],7000000),
      'p2_attack':([('mouse-button','2000000:1'),('mouse-button','2400000:0'),('key','3500000:6:1'),('key','4500000:6:0')],7000000),
      'motion_2048':([('mouse-edge-cycles','2048'),('mouse-motion','1000000:32:0')],4000000),
      'motion_1024':([('mouse-edge-cycles','1024'),('mouse-motion','1000000:32:0')],4000000),
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
    assert (cases['window_outside']['x'],cases['window_outside']['state'])==(336,1)
    assert (cases['window_return_and_play']['x'],cases['window_return_and_play']['state'])==(256,2)
    assert cases['window_return_and_play']['game_x']>0x8000
    assert cases['start']['state']==2 and cases['title_keys_discarded']['game_x']==0x8000
    assert cases['play_keys']['game_x']>0x8000
    assert cases['p2_play_keys']['p2x']<0xa800
    for name,field in (('p1_jump','p1_jumps'),('p2_jump','p2_jumps'),
                       ('p1_attack','p1_attacks'),('p2_attack','p2_attacks')):
        assert cases[name]['state']==2 and cases[name][field]==1,(name,cases[name])
    assert cases['motion_2048']['x']==288
    assert cases['motion_1024']['x']==288
    # motion_256 is a characterization, not an assertion that loss must persist.
    assert cases['flush_timeout']['state']==3 and cases['flush_retry']['state']==2
    displayed=animation(exe,rom,root)
    handoff=handoff_replay(exe,rom,root)
    summary={'status':'pass','rom_sha256':sha(image),'boothush_sha256':sha(exe.read_bytes()),
             'rom_used_through':0x104+size,'cases':cases,'in_motion_displayed_x':displayed,
             'mouse_keyboard_handoff_replay':handoff,
             'native_p2':native_p2,
             'native_component_sha256':sha(native_movement) if native_movement is not None else None,
             'native_component_end':0xe000+len(native_movement) if native_movement is not None else None}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--boothush',required=True,type=Path);p.add_argument('--keep',type=Path);p.add_argument('--native-component',type=Path);p.add_argument('--native-p2',action='store_true');a=p.parse_args()
    component=a.native_component.read_bytes() if a.native_component else None
    if a.keep:a.keep.mkdir(parents=True,exist_ok=False);test(a.boothush,a.keep,component,a.native_p2)
    else:
        with tempfile.TemporaryDirectory(prefix='nstb-title-') as d:test(a.boothush,Path(d),component,a.native_p2)

if __name__=='__main__':main()
