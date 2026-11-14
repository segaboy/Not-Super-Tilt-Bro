#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Build and execute a small source-informed native C probe, without WSL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from build_mac_probe import ROM_BASE,ENTRY,be32

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'guest/sinbad_native_probe.c'
MOVEMENT=ROOT/'guest/sinbad_movement.c'
HEADER=ROOT/'guest/sinbad_movement.h'
EXPECTED=((0x8140,0x0140),(0x82c0,0x0180),(0x8480,0x01c0),(0x8680,0x0200),
          (0x8820,0x01a0),(0x8960,0x0140),(0x8a40,0x00e0),(0x8ac0,0x0080),
          (0x8ae0,0x0020),(0x8ae0,0))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command,log,env):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,timeout=30,env=env,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    log.write_text(p.stdout+'\n--- stderr ---\n'+p.stderr,encoding='utf-8')
    if p.returncode:raise RuntimeError('command failed; see '+str(log))
    return p.stdout


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tool-bin',required=True,type=Path);p.add_argument('--boothush',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    tools=a.tool_bin.resolve(strict=True);exe=a.boothush.resolve(strict=True);out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('output must be outside the repository')
    prefix='m68k-unknown-elf-';gcc=tools/(prefix+'gcc.exe');nm=tools/(prefix+'nm.exe');objcopy=tools/(prefix+'objcopy.exe')
    for f in (gcc,nm,objcopy):
        if not f.is_file():raise ValueError('missing compiler tool: '+str(f))
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
    source_hashes={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in (SOURCE,MOVEMENT,HEADER)}
    tool_hashes={f.name:sha(f) for f in (gcc,nm,objcopy)}
    out.mkdir(parents=True,exist_ok=False);images=[];commands=[]
    for name in ('a','b'):
        folder=out/name;folder.mkdir();elf=folder/'probe.elf';binary=folder/'probe.bin';objects=[];compile_commands=[]
        for source in (SOURCE,MOVEMENT):
            obj=folder/(source.stem+'.o');objects.append(obj)
            compile_cmd=[gcc,'-mcpu=68000','-Wa,-m68000','-std=c11','-Os','-ffreestanding','-fno-builtin',
                         '-fno-pic','-fno-pie','-fno-stack-protector','-fno-unwind-tables',
                         '-fno-asynchronous-unwind-tables','-Wall','-Wextra','-Werror','-c',source,'-o',obj]
            run(compile_cmd,folder/(source.stem+'.log'),env)
            compile_commands.append([str(x) for x in compile_cmd])
        link_cmd=[gcc,'-mcpu=68000','-nostdlib','-no-pie','-Wl,--build-id=none',
                  '-Wl,-Ttext=0x400200','-Wl,--entry=port_entry','-Wl,-Map,'+str(folder/'probe.map'),*objects,'-o',elf]
        run(link_cmd,folder/'link.log',env)
        undefined=run([nm,'--undefined-only',elf],folder/'undefined.log',env)
        if undefined.strip():raise ValueError('unexpected undefined symbols')
        symbols=run([nm,'--defined-only','--format=posix',elf],folder/'symbols.log',env)
        if not any(line.split()[:3]==['port_entry','T','400200'] for line in symbols.splitlines()):
            raise ValueError('entry address mismatch')
        if not any(line.split()[:2]==['sinbad_movement_step','T'] for line in symbols.splitlines()):
            raise ValueError('missing reusable movement function')
        run([objcopy,'-O','binary',elf,binary],folder/'objcopy.log',env)
        code=binary.read_bytes()
        if not code or len(code)>65536-0x200:raise ValueError('native C payload outside ROM')
        image=bytearray(65536);image[:4]=be32(0x4000);image[4:8]=be32(ROM_BASE+ENTRY)
        for vector in range(2,64):image[vector*4:vector*4+4]=be32(ROM_BASE+0x1fe)
        # Same project-owned vector relocation as the existing probe.
        startup=bytes.fromhex('46fc2700 13fc004800effffe 13fc005800efe7fe 41f900400000 93c9 703f 22d8 51c8fffc 2f3c00000b00 4eb9')+be32(ROM_BASE+0x200)+bytes.fromhex('60fe')
        image[ENTRY:ENTRY+len(startup)]=startup;image[0x1fe:0x200]=bytes.fromhex('60fe')
        image[0x200:0x200+len(code)]=code
        rom=folder/'sinbad-native-probe.rom';rom.write_bytes(image);images.append(rom)
        commands.append({'compile':compile_commands,'link':[str(x) for x in link_cmd]})
    if images[0].read_bytes()!=images[1].read_bytes():raise ValueError('ROM twins differ')
    command=[str(exe),'--machine','mac128k','--rom',str(images[0]),'--cycles','2000000',
             '--timeout-ms','20000','--inspect','0xb00:86']
    data=json.loads(run(command,out/'boothush.log',env))
    if data['status']!='cycle_limit':raise ValueError('guest did not finish bounded run')
    raw=bytes.fromhex(data['memory']['bytes'])
    if len(raw)!=86 or raw[:4]!=bytes.fromhex('4e430001') or raw[-2:]!=bytes.fromhex('a55a'):
        raise ValueError('guest diagnostic not ready')
    observed=tuple((int.from_bytes(raw[4+i*4:6+i*4],'big'),int.from_bytes(raw[6+i*4:8+i*4],'big')) for i in range(10))
    if observed!=EXPECTED:raise ValueError('native movement trace mismatch: '+str(observed))
    opposite=tuple((int.from_bytes(raw[44+i*4:46+i*4],'big'),int.from_bytes(raw[46+i*4:48+i*4],'big')) for i in range(10))
    opposite_expected=tuple(((0x10000-position)&0xffff,(-velocity)&0xffff) for position,velocity in EXPECTED)
    if opposite!=opposite_expected:raise ValueError('opposite movement trace mismatch: '+str(opposite))
    # Negative control changes the compiled immediate acceleration from 64 to
    # 32; the independent expected trace must detect the different result.
    needle=bytes.fromhex('06400040');original=images[0].read_bytes()
    if original.count(needle)!=1 or original.index(needle)<0x200:raise ValueError('mutation site changed')
    mutant=out/'bad-acceleration.rom';mutant.write_bytes(original.replace(needle,bytes.fromhex('06400020'),1))
    mutant_command=[str(exe),'--machine','mac128k','--rom',str(mutant),'--cycles','2000000',
                    '--timeout-ms','20000','--inspect','0xb00:86']
    mutant_data=json.loads(run(mutant_command,out/'bad-acceleration.log',env))
    m=bytes.fromhex(mutant_data['memory']['bytes'])
    if (mutant_data['status']!='cycle_limit' or m[-2:]!=bytes.fromhex('a55a') or
        m[4:8]!=bytes.fromhex('81200120') or m==raw):raise ValueError('acceleration mutation was not detected')
    if sha(images[0])!=hashlib.sha256(original).hexdigest() or {str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in (SOURCE,MOVEMENT,HEADER)}!=source_hashes:
        raise ValueError('source or ROM changed during test')
    if {f.name:sha(f) for f in (gcc,nm,objcopy)}!=tool_hashes:raise ValueError('tool changed during test')
    report={'status':'pass','rom_sha256':sha(images[0]),'source_sha256':source_hashes,
            'script_sha256':sha(Path(__file__)),'tool_sha256':tool_hashes,'boothush_sha256':sha(exe),
            'compile_and_link':commands,'boot_command':command,'guest_result':data,'movement_trace':observed,'opposite_trace':opposite,
            'mutation_control':{'rom_sha256':sha(mutant),'command':mutant_command,'guest_result':mutant_data},
            'limits':'Isolated source-informed movement diagnostic; no keyboard, match, hardware or release claim.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
