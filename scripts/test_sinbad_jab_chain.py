#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build and check a source-derived PAL jab-chain slice in BootHush."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_mac_probe import ROM_BASE, ENTRY, be32

ROOT=Path(__file__).resolve().parents[1]
SOURCES=(ROOT/'guest/sinbad_jab_probe.c',ROOT/'guest/sinbad_jab_chain.c',ROOT/'guest/sinbad_jab_chain.h')
LENGTH=4+6*80*6+2


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command,log,env):
    args=[str(x) for x in command]
    result=subprocess.run(args,capture_output=True,text=True,timeout=30,env=env,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    log.write_text(result.stdout+'\n--- stderr ---\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('command failed: '+str(log))
    return result.stdout


def point(raw,scenario,tick,player=0):
    start=4+((scenario*80+tick-1)*6)+player*3
    return tuple(raw[start:start+3])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tool-bin',required=True,type=Path);p.add_argument('--boothush',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    tools=a.tool_bin.resolve(strict=True);exe=a.boothush.resolve(strict=True);out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('output must be outside repository')
    gcc=tools/'m68k-unknown-elf-gcc.exe';nm=tools/'m68k-unknown-elf-nm.exe';objcopy=tools/'m68k-unknown-elf-objcopy.exe'
    for path in (gcc,nm,objcopy):
        if not path.is_file():raise ValueError('missing tool: '+str(path))
    paths=(*SOURCES,Path(__file__),ROOT/'scripts/build_mac_probe.py',gcc,nm,objcopy,exe)
    before={str(x):sha(x) for x in paths};out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
    commands=[]
    def build(name,mutant=False):
        folder=out/name;folder.mkdir();objects=[]
        chain=SOURCES[1]
        if mutant:
            text=chain.read_text(encoding='utf-8');needle='?14:16;'
            if text.count(needle)!=1:raise ValueError('mutation site changed')
            chain=folder/'mutant.c';chain.write_text(text.replace(needle,'?13:16;'),encoding='utf-8')
        for source in (SOURCES[0],chain):
            obj=folder/(source.stem+'.o');objects.append(obj)
            cmd=[gcc,'-mcpu=68000','-Wa,-m68000','-std=c11','-Os','-ffreestanding','-fno-builtin',
                 '-fno-pic','-fno-pie','-fno-stack-protector','-fno-unwind-tables',
                 '-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror',
                 '-I',ROOT/'guest','-c',source,'-o',obj]
            run(cmd,folder/(source.stem+'.log'),env);commands.append([str(x) for x in cmd])
        elf=folder/'probe.elf';binary=folder/'probe.bin'
        cmd=[gcc,'-mcpu=68000','-nostdlib','-no-pie','-Wl,--build-id=none','-Wl,-Ttext=0x400200',
             '-Wl,--entry=port_entry','-Wl,-Map,'+str(folder/'probe.map'),*objects,'-o',elf]
        run(cmd,folder/'link.log',env);commands.append([str(x) for x in cmd])
        if run([nm,'--undefined-only',elf],folder/'undefined.log',env).strip():raise ValueError('undefined guest symbols')
        symbols=run([nm,'--defined-only','--format=posix',elf],folder/'symbols.log',env)
        if not any(line.split()[:3]==['port_entry','T','400200'] for line in symbols.splitlines()):
            raise ValueError('guest entry moved')
        if not any(line.split()[:2]==['nstb_jab_tick','T'] for line in symbols.splitlines()):
            raise ValueError('missing jab function')
        run([objcopy,'-O','binary',elf,binary],folder/'objcopy.log',env)
        code=binary.read_bytes()
        if not code or len(code)>65536-0x200:raise ValueError('payload outside ROM')
        image=bytearray(65536);image[:4]=be32(0x4000);image[4:8]=be32(ROM_BASE+ENTRY)
        for vector in range(2,64):image[vector*4:vector*4+4]=be32(ROM_BASE+0x1fe)
        startup=bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe 41f900400000 93c9 703f 22d8 51c8fffc 2f3c00000b00 4eb9')+be32(ROM_BASE+0x200)+bytes.fromhex('60fe')
        image[ENTRY:ENTRY+len(startup)]=startup;image[0x1fe:0x200]=bytes.fromhex('60fe')
        image[0x200:0x200+len(code)]=code
        rom=folder/'jab-chain.rom';rom.write_bytes(image)
        return rom,len(code)
    first,size=build('a');second,_=build('b')
    if first.read_bytes()!=second.read_bytes():raise ValueError('ROM twins differ')
    def observe(name,rom):
        cmd=[exe,'--machine','mac128k','--rom',rom,'--cycles','4000000','--timeout-ms','20000',
             '--inspect',f'0xb00:{LENGTH}']
        result=json.loads(run(cmd,out/(name+'.log'),env));commands.append([str(x) for x in cmd])
        raw=bytes.fromhex(result['memory']['bytes'])
        if result['status']!='cycle_limit' or len(raw)!=LENGTH or raw[:4]!=b'SJB\x01' or raw[-2:]!=b'\xa5\x5a':
            raise ValueError('guest diagnostic incomplete')
        return result,raw
    result,raw=observe('baseline',first)
    # Independently selected boundary expectations from the source state table.
    expected={
        (0,1):(1,23,1),(0,23):(1,1,1),(0,24):(0,0,1),
        (1,1):(1,23,0),(1,2):(1,22,0),(1,9):(1,15,0),(1,10):(2,26,1),
        (1,11):(2,25,0),(1,19):(2,17,0),(1,20):(3,26,1),(1,46):(0,0,1),
        (2,2):(1,22,0),(2,10):(1,14,0),(2,24):(0,0,0),
        (3,9):(1,15,0),(3,10):(2,26,1),
        (4,9):(1,15,0),(4,10):(1,14,2),(4,11):(1,13,0),(4,12):(2,26,1),
        (5,20):(3,26,1),(5,21):(3,25,0),(5,22):(3,24,0),(5,23):(3,23,0),(5,46):(0,0,0),
    }
    for (scenario,tick),want in expected.items():
        if point(raw,scenario,tick)!=want:raise ValueError(f'boundary mismatch {(scenario,tick,want,point(raw,scenario,tick))}')
    for scenario in range(6):
        for tick in range(1,81):
            want=(1,24-tick,1) if tick<24 else (0,0,1)
            if point(raw,scenario,tick,1)!=want:raise ValueError('interleaved player state changed')
    mutant,_=build('mutant',True);mutant_result,changed=observe('mutant',mutant)
    if point(changed,1,10)!=(1,14,0) or point(changed,1,10)==point(raw,1,10):
        raise ValueError('threshold mutation escaped boundary control')
    if before!={str(x):sha(x) for x in paths}:raise ValueError('source or tool changed')
    report={'status':'pass','rom_sha256':sha(first),'rom_used_through':0x200+size,
            'input_sha256':before,'commands':commands,'guest_result':result,
            'checked_boundary_points':len(expected),'interleaved_player_checks':6*80,
            'mutation':{'rom_sha256':sha(mutant),'guest_result':mutant_result,
                        'baseline_at_1_10':point(raw,1,10),'mutant_at_1_10':point(changed,1,10)},
            'limits':'Isolated source-derived PAL jab state/input slice in BootHush; no keyboard, game match, physical hardware or source-matched NES execution.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','rom_sha256':sha(first),'report':str(out/'report.json')}))


if __name__=='__main__':main()
