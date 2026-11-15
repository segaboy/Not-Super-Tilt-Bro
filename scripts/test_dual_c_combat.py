#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Exercise combat after mouse Start in the two-player native-C prototype."""
import argparse
import hashlib
import json
from pathlib import Path

from build_mac_movement import build,DAMAGE,P1DAMAGE,ACLOCK,VEL
from build_mac_probe import be32
from test_mac_two_player import run

ROOT=Path(__file__).resolve().parents[1]
COMPONENT_SHA='a65c5fa382bee316b916cd6c6af52c4a2591496aa762c346e784e7a8bca7d25c'
ROM_SHA='8fae602e93fc184522cf8f5aae83b632134e1767be80a93c2bef72af830862f6'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boothush',required=True,type=Path)
    p.add_argument('--component',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();exe=a.boothush.resolve(strict=True);component=a.component.resolve(strict=True);out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('output must be outside repository')
    if sha(component)!=COMPONENT_SHA:raise ValueError('unexpected linked movement component')
    inputs=[Path(__file__),*(ROOT/'scripts'/name for name in ('build_mac_movement.py','build_mac_probe.py',
            'build_mac_run_transition.py','build_mac_title.py','test_mac_two_player.py','test_mac_combat.py')),
            ROOT/'guest/sinbad_movement.c',ROOT/'guest/sinbad_movement.h']
    before={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in inputs}
    exe_sha=sha(exe);code=component.read_bytes()
    image,size=build(jumping=True,combat=True,two_player=True,title=True,native_movement=code,native_p2=True)
    twin,_=build(jumping=True,combat=True,two_player=True,title=True,native_movement=code,native_p2=True)
    if image!=twin or hashlib.sha256(image).hexdigest()!=ROM_SHA:raise ValueError('unexpected title ROM identity')
    out.mkdir(parents=True,exist_ok=False);rom=out/'title.rom';rom.write_bytes(image)
    points=list(range(25,57));stop=8000000
    scenarios={
        'far_miss':[(3500000,3,1),(3900000,3,0)],
        'p1_hit':[(3500000,5,1),(4200000,5,0),(4700000,3,1),(5100000,3,0)],
        'p2_hit':[(3500000,5,1),(4200000,5,0),(4700000,6,1),(5100000,6,0)],
        'both_attack':[(3500000,5,1),(4200000,5,0),(4700000,3,1),(4900000,6,1),
                       (5300000,3,0),(5500000,6,0)],
        'p2_attack_lock':[(3500000,5,1),(4200000,6,1),(4600000,6,0),(7000000,5,0)],
        'p1_attack_lock':[(3500000,3,1),(4000000,0,1),(4800000,3,0),(7000000,0,0)],
    }
    cases={name:run(exe,rom,out,name,events,points,stop,native_p2=True,title_start=True)
           for name,events in scenarios.items()}
    last=lambda name:cases[name]['observations'][-1]
    if (last('far_miss')['damage'],last('far_miss')['hits'])!=(0,0):raise ValueError('far attack hit')
    if (last('p1_hit')['damage'],last('p1_hit')['hits'])!=(2,1):raise ValueError('player-one hit not observed')
    if (last('p2_hit')['p1damage'],last('p2_hit')['p2hits'])!=(2,1):raise ValueError('player-two hit not observed')
    if (last('both_attack')['damage'],last('both_attack')['p1damage'])!=(2,2):raise ValueError('two-player trade not observed')
    locked=[s['p2x'] for s in cases['p2_attack_lock']['observations'] if 3<=s['p2attack_clock']<=22]
    if len(locked)<10 or len(set(locked))!=1:raise ValueError('player-two attack lock not sustained')
    locked=[s['x'] for s in cases['p1_attack_lock']['observations'] if 3<=s['attack_clock']<=22]
    if len(locked)<10 or len(set(locked))!=1:raise ValueError('player-one attack lock not sustained')
    held=[(3500000,3,1),(4000000,0,1),(4800000,3,0)]
    cases['p1_resume_held']=run(exe,rom,out,'p1_resume_held',held,list(range(32,64)),9000000,
                                native_p2=True,title_start=True)
    resumed=cases['p1_resume_held']['observations']
    if not any(s['attack_clock']==0 and s['x']>locked[0] for s in resumed):
        raise ValueError('held direction did not resume after player-one attack')
    if any(cases[name]['oracle_intervals']<15 for name in cases):raise ValueError('insufficient state oracle coverage')
    # Remove only the per-tick velocity reset, leaving the initial attack reset
    # intact. The held-direction scenario must reveal movement during the jab.
    marker=bytes.fromhex('0c390000')+be32(ACLOCK)+bytes.fromhex('66064ef9')
    reset=bytes.fromhex('33fc0000')+be32(VEL)
    matches=[i+len(marker)+4 for i in range(len(image)) if image.startswith(marker,i)
             and image.startswith(reset,i+len(marker)+4)]
    if len(matches)!=1:raise ValueError('attack lock mutation site changed')
    mutated=bytearray(image);at=matches[0];mutated[at:at+len(reset)]=bytes.fromhex('4e71')*4
    lock_mutant=out/'p1-lock-mutant.rom';lock_mutant.write_bytes(mutated)
    changed_lock=run(exe,lock_mutant,out,'p1-lock-mutant',scenarios['p1_attack_lock'],points,stop,
                     native_p2=True,title_start=True)
    mutant_positions=[s['x'] for s in changed_lock['observations'] if 3<=s['attack_clock']<=22]
    if len(mutant_positions)<10 or len(set(mutant_positions))<2:raise ValueError('lock mutation escaped control')
    # Deliberately weaken each hit's damage increment to prove that both the
    # explicit outcome check and the separate P2 state oracle detect it.
    p1_needle=bytes.fromhex('5439')+be32(DAMAGE)
    p2_needle=bytes.fromhex('5439')+be32(P1DAMAGE)
    if image.count(p1_needle)!=1 or image.count(p2_needle)!=1:raise ValueError('hit mutation sites changed')
    p1_mutant=out/'p1-damage-mutant.rom'
    p1_mutant.write_bytes(image.replace(p1_needle,bytes.fromhex('5239')+be32(DAMAGE),1))
    changed=run(exe,p1_mutant,out,'p1-damage-mutant',scenarios['p1_hit'],points,stop,native_p2=True,title_start=True)
    if (changed['observations'][-1]['damage'],changed['observations'][-1]['hits'])!=(1,1):
        raise ValueError('player-one damage mutation was not observed')
    p2_mutant=out/'p2-damage-mutant.rom'
    p2_mutant.write_bytes(image.replace(p2_needle,bytes.fromhex('5239')+be32(P1DAMAGE),1))
    try:
        run(exe,p2_mutant,out,'p2-damage-mutant',scenarios['p2_hit'],points,stop,native_p2=True,title_start=True)
    except AssertionError as exc:
        detail=exc.args[0] if exc.args else None
        if (not isinstance(detail,tuple) or len(detail)!=3 or detail[0]!='p2-damage-mutant' or
            detail[1]['p1damage']!=0 or detail[2]['p1damage']!=1 or detail[2]['p2hits']!=1):
            raise ValueError('player-two mutant failed for an unrelated reason') from exc
    else:
        raise ValueError('player-two damage mutation escaped independent state oracle')
    if (sha(exe)!=exe_sha or sha(component)!=COMPONENT_SHA or sha(rom)!=ROM_SHA or
        before!={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in inputs}):
        raise ValueError('source, tool or ROM changed')
    report={'status':'pass','boothush_sha256':exe_sha,'rom_sha256':ROM_SHA,'component_sha256':COMPONENT_SHA,
            'source_sha256':before,'rom_used_through':0x104+size,'cases':cases,
            'mutation_controls':{'p1_sha256':sha(p1_mutant),'p1_final_damage':1,
                                 'p2_sha256':sha(p2_mutant),'p2_oracle_rejected':True,
                                 'p1_lock_sha256':sha(lock_mutant),'p1_lock_positions':mutant_positions},
            'limits':'Mouse and keyboard schedules in BootHush; local combat and placeholder art, not complete game or physical input.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':ROM_SHA,'case_count':len(cases),'report':str(out/'report.json')}))


if __name__=='__main__':main()
