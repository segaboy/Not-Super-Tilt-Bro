#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Exercise opt-in native jab chains after mouse Start in BootHush."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_mac_movement import build,DAMAGE,P1DAMAGE
from build_mac_probe import be32
from test_mac_two_player import decode,pixels

ROOT=Path(__file__).resolve().parents[1]
SOURCES=(ROOT/'guest/sinbad_jab_chain.c',ROOT/'guest/sinbad_jab_chain.h',
         ROOT/'scripts/build_mac_movement.py',ROOT/'scripts/build_mac_probe.py',
         ROOT/'scripts/build_mac_run_transition.py',ROOT/'scripts/build_mac_title.py',
         ROOT/'scripts/test_mac_two_player.py',ROOT/'scripts/test_mac_combat.py',Path(__file__))
COMPONENT_SHA='a65c5fa382bee316b916cd6c6af52c4a2591496aa762c346e784e7a8bca7d25c'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tool-bin',required=True,type=Path);p.add_argument('--boothush',required=True,type=Path)
    p.add_argument('--component',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();tools=a.tool_bin.resolve(strict=True);exe=a.boothush.resolve(strict=True)
    movement=a.component.resolve(strict=True);out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('output must be outside repository')
    if sha(movement)!=COMPONENT_SHA:raise ValueError('unexpected movement component')
    gcc=tools/'m68k-unknown-elf-gcc.exe';nm=tools/'m68k-unknown-elf-nm.exe';objcopy=tools/'m68k-unknown-elf-objcopy.exe'
    inputs=(*SOURCES,gcc,nm,objcopy,exe,movement);before={str(x):sha(x) for x in inputs}
    out.mkdir(parents=True,exist_ok=False);env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
    commands=[]
    def invoke(cmd,log):
        args=[str(x) for x in cmd];commands.append(args)
        result=subprocess.run(args,capture_output=True,text=True,timeout=30,env=env,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        log.write_text(result.stdout+'\n--- stderr ---\n'+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('command failed: '+str(log))
        return result.stdout
    def component(name,mutant=False):
        folder=out/name;folder.mkdir();source=SOURCES[0]
        if mutant:
            text=source.read_text(encoding='utf-8');needle='?14:16;'
            if text.count(needle)!=1:raise ValueError('mutation site changed')
            source=folder/'mutant.c';source.write_text(text.replace(needle,'?13:16;'),encoding='utf-8')
        obj=folder/'jab.o';elf=folder/'jab.elf';binary=folder/'jab.bin'
        invoke([gcc,'-mcpu=68000','-Wa,-m68000','-std=c11','-Os','-ffreestanding','-fno-builtin',
                '-fno-pic','-fno-pie','-fno-stack-protector','-fno-unwind-tables',
                '-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror',
                '-I',ROOT/'guest','-c',source,'-o',obj],folder/'compile.log')
        invoke([gcc,'-mcpu=68000','-nostdlib','-no-pie','-Wl,--build-id=none','-Wl,-Ttext=0x40e200',
                '-Wl,--entry=nstb_jab_begin','-Wl,-Map,'+str(folder/'jab.map'),obj,'-o',elf],folder/'link.log')
        if invoke([nm,'--undefined-only',elf],folder/'undefined.log').strip():raise ValueError('undefined jab symbols')
        symbols=invoke([nm,'--defined-only','--format=posix',elf],folder/'symbols.log')
        found={parts[0]:int(parts[2],16)-0x40e200 for line in symbols.splitlines()
               if len(parts:=line.split())>=3 and parts[0] in ('nstb_jab_begin','nstb_jab_tick')}
        if set(found)!={'nstb_jab_begin','nstb_jab_tick'}:raise ValueError('missing jab entry symbols')
        invoke([objcopy,'-O','binary',elf,binary],folder/'objcopy.log')
        return binary.read_bytes(),found
    code,symbols=component('a');twin,twin_symbols=component('b')
    if code!=twin or symbols!=twin_symbols:raise ValueError('component twins differ')
    image,size=build(jumping=True,combat=True,two_player=True,title=True,native_movement=movement.read_bytes(),
                     native_p2=True,native_jab=(code,symbols['nstb_jab_begin'],symbols['nstb_jab_tick']))
    rom=out/'title-jab.rom';rom.write_bytes(image)
    scenarios={
        'p1_chain':[(3500000,3,1),(3900000,3,0),(4200000,3,1),(5800000,3,0),(6100000,3,1),(8500000,3,0)],
        'p2_chain':[(3500000,6,1),(3900000,6,0),(4200000,6,1),(5800000,6,0),(6100000,6,1),(8500000,6,0)],
        'both_chain':[(3500000,3,1),(3700000,6,1),(3900000,3,0),(4100000,6,0),
                      (4300000,3,1),(4500000,6,1),(5900000,3,0),(6100000,6,0),
                      (6300000,3,1),(6500000,6,1),(8500000,3,0),(8700000,6,0)],
        'early_tap':[(3500000,3,1),(3900000,3,0),(4100000,3,1),(4300000,3,0)],
        'held':[(3500000,3,1)],
    }
    def run(name,events,selected_rom=rom,points=range(32,64),stop=9200000):
        frames=out/(name+'.pbmseq');witness=out/(name+'.keyboard')
        cmd=[exe,'--machine','mac128k','--rom',selected_rom,'--cycles',str(stop),'--timeout-ms','20000',
             '--mouse-button','2000000:1','--mouse-button','2400000:0','--capture-series',frames,
             '--capture-memory','0xb00:101','--keyboard-witness',witness]
        for frame in points:cmd+=['--capture-vbl',str(frame)]
        for cycle,key,down in events:cmd+=['--key',f'{cycle}:{key}:{down}']
        data=json.loads(invoke(cmd,out/(name+'.log')));series=data['frame_series']
        if (data['status']!='cycle_limit' or series['rom_sha256']!=sha(selected_rom) or
            series['executable_sha256']!=sha(exe) or
            (series['requested'],series['processed'],series['pending'],series['missing_images'],series['dropped'])!=(len(points),len(points),0,0,0) or
            any(data['keyboard_witness'][k] for k in ('dropped','rejected','pending'))):
            raise ValueError(name+': incomplete input or frames')
        rows=[x.split() for x in witness.read_text(encoding='ascii').splitlines()[2:]]
        delivered=[(int(r[0]),int(r[3])) for r in rows if r[2]=='key_delivered']
        if [v for _,v in delivered]!=[(key<<1)|1|(0 if down else 128) for _,key,down in events]:
            raise ValueError(name+': keyboard deliveries differ')
        raw=frames.read_bytes();states=[]
        for sample in series['samples']:
            memory=bytes.fromhex(sample['memory']['bytes'])
            if len(memory)!=101 or not sample['processed'] or not sample['image_available']:raise ValueError('missing sample')
            state=decode({'memory':{'bytes':memory[:58].hex()}})
            state.update({'p1button':memory[33],'p1jab':list(memory[90:93]),'p2jab':list(memory[94:97]),
                          'p1new':memory[98],'p2new':memory[99]})
            pixels(raw[sample['offset']:sample['offset']+sample['length']],state)
            states.append(state)
        checks=0
        for left,right,old,new in zip(series['samples'],series['samples'][1:],states,states[1:]):
            if right['frame']!=left['frame']+1 or any(left['cycle']<=c<right['cycle'] for c,_ in delivered):continue
            if new['vbls']!=old['vbls']+1:raise ValueError(name+': unserviced VBL')
            for prefix,button in (('p1','p1button'),('p2','p2button')):
                stage,clock,previous=old[prefix+'jab'];newflag=old[prefix+'new']
                if old['phase']!=5 and stage:
                    if newflag:newflag=0
                    else:
                        clock-=1
                        if clock==0:stage=0
                        elif old[button]!=previous:
                            current=old[button]
                            if stage==3 or clock>(14 if stage==1 else 16):
                                if current==0:previous=0
                            else:
                                if current==1:stage+=1;clock=26
                                previous=current
                if (new[prefix+'jab'],new[prefix+'new'])!=([stage,clock,previous],newflag):
                    raise ValueError(name+': jab state mismatch '+str((prefix,old,new)))
            checks+=1
        if checks<15:raise ValueError(name+': insufficient unchanged-input intervals')
        return {'command':[str(x) for x in cmd],'keyboard_witness_sha256':sha(witness),
                'frames_sha256':sha(frames),'oracle_intervals':checks,
                'observations':[{'vbl':sample['frame'],'cycle':sample['cycle'],**state}
                                for sample,state in zip(series['samples'],states)]}
    cases={name:run(name,events) for name,events in scenarios.items()}
    for name,prefixes in (('p1_chain',('p1',)),('p2_chain',('p2',)),('both_chain',('p1','p2'))):
        for prefix in prefixes:
            if not {1,2,3}.issubset({s[prefix+'jab'][0] for s in cases[name]['observations']}):
                raise ValueError(name+': expected three jab stages')
    for name in ('early_tap','held'):
        if any(s['p1jab'][0] in (2,3) for s in cases[name]['observations']):raise ValueError(name+': unexpected chain')
    attack_events={
        'p1_chain_hits':[(3500000,5,1),(4200000,5,0),(4700000,3,1),(5100000,3,0),
                         (5400000,3,1),(6900000,3,0),(7100000,3,1),(9500000,3,0)],
        'p2_chain_hits':[(3500000,5,1),(4200000,5,0),(4700000,6,1),(5100000,6,0),
                         (5400000,6,1),(6900000,6,0),(7100000,6,1),(9500000,6,0)],
    }
    for name,events in attack_events.items():
        cases[name]=run(name,events,points=range(45,77),stop=12500000)
        last=cases[name]['observations'][-1]
        key=('damage','hits') if name.startswith('p1') else ('p1damage','p2hits')
        if tuple(last[k] for k in key)!=(8,3):raise ValueError(name+': expected three hits and damage 2+1+5')
        history=[(s[key[0]],s[key[1]]) for s in cases[name]['observations']]
        if not all(v in history for v in ((2,1),(3,2),(8,3))):raise ValueError(name+': missing stage damage')
    for initial in (250,254):
        capped,_=build(jumping=True,combat=True,two_player=True,title=True,initial_damage=initial,
                       native_movement=movement.read_bytes(),native_p2=True,
                       native_jab=(code,symbols['nstb_jab_begin'],symbols['nstb_jab_tick']))
        cap_rom=out/('initial-%d.rom'%initial);cap_rom.write_bytes(capped)
        for name,events in attack_events.items():
            label=name+'-initial-%d'%initial
            cases[label]=run(label,events,cap_rom,range(45,77),12500000)
            key=('damage','hits') if name.startswith('p1') else ('p1damage','p2hits')
            history=[(s[key[0]],s[key[1]]) for s in cases[label]['observations']]
            expected=((252,1),(253,2),(254,3)) if initial==250 else ((254,1),(254,2),(254,3))
            if not all(v in history for v in expected):raise ValueError(label+': damage saturation mismatch')
    # Alter stage-specific increments; the final damage must change for both
    # players, proving the outcome check is sensitive to the values.
    damage_controls={}
    for name,address in (('p1_chain_hits',DAMAGE),('p2_chain_hits',P1DAMAGE)):
        for stage,old_amount,new_amount,expected in ((2,1,2,9),(3,5,4,7)):
            needle=bytes.fromhex('0639')+bytes((0,old_amount))+be32(address)
            if image.count(needle)!=1:raise ValueError('damage mutation site changed')
            altered=image.replace(needle,bytes.fromhex('0639')+bytes((0,new_amount))+be32(address),1)
            label=name+'-stage%d-mutant'%stage
            path=out/(label+'.rom');path.write_bytes(altered)
            result=run(label,attack_events[name],path,range(45,77),12500000)
            last=result['observations'][-1]
            key=('damage','hits') if name.startswith('p1') else ('p1damage','p2hits')
            if tuple(last[k] for k in key)!=(expected,3):raise ValueError(label+': damage mutant did not change outcome')
            damage_controls[label]={'rom_sha256':sha(path),'final_damage':expected,'hits':3}
    mutant_code,mutant_symbols=component('mutant',True)
    mutated,_=build(jumping=True,combat=True,two_player=True,title=True,native_movement=movement.read_bytes(),
                    native_p2=True,native_jab=(mutant_code,mutant_symbols['nstb_jab_begin'],mutant_symbols['nstb_jab_tick']))
    mutant_rom=out/'mutant.rom';mutant_rom.write_bytes(mutated)
    # The separate reference calculation must reject the altered first-cut threshold.
    try:run('mutant',scenarios['p1_chain'],mutant_rom)
    except ValueError as exc:
        if 'jab state mismatch' not in str(exc):raise
    else:raise ValueError('jab threshold mutation escaped')
    if before!={str(x):sha(x) for x in inputs}:raise ValueError('source or tool changed')
    report={'status':'pass','rom_sha256':sha(rom),
            'rom_layout':{'emitter_end':0x104+size,'movement_end':0xe000+len(movement.read_bytes()),
                          'jab_component_end':0xe200+len(code),'rom_size':len(image)},
            'jab_component_sha256':hashlib.sha256(code).hexdigest(),'jab_symbols':symbols,
            'input_sha256':before,'commands':commands,'cases':cases,
            'stage_damage_mutations':damage_controls,
            'mutation':{'rom_sha256':sha(mutant_rom),'oracle_rejected':True},
            'limits':'Mouse/keyboard schedules and original placeholder pixels in BootHush; local collision/display adapter, not complete game, physical input or source-matched NES execution.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':sha(rom),'report':str(out/'report.json')}))


if __name__=='__main__':main()
