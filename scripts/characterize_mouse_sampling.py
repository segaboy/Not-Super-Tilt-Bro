#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Dean Howell.
"""Compare title polling with modeled mouse phases using BootHush witnesses."""
import argparse
from bisect import bisect_right
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROM_SHA='7121c504159e128d9ec7349213837c5d7b0dbdf8ead594e687334c63e2926ccd'
ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(exe,rom,out,name,spacing,traced):
    frame=out/(name+'.pbm');witness=out/(name+'.witness')
    cmd=[str(exe),'--machine','mac128k','--rom',str(rom),'--cycles','4000000',
         '--timeout-ms','20000','--mouse-dcd-invert','3','--mouse-edge-cycles',str(spacing),
         '--mouse-motion','1000000:32:0','--inspect','0xb00:86','--frame',str(frame)]
    if traced:cmd+=['--mouse-witness',str(witness),'--mouse-witness-detail','1',
                    '--mouse-witness-range','999000:1200000','--mouse-witness-memory','0xb40:4']
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=25,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    data=json.loads(result.stdout)
    assert data['status']=='cycle_limit' and data['mouse']=={'samples':1,'steps':64,'pending':0}
    (out/(name+'.json')).write_text(json.dumps({'command':cmd,'result':data},indent=2)+'\n',encoding='utf-8')
    return data,frame,witness


def trace_summary(witness):
    lines=witness.read_text(encoding='ascii').splitlines();header=lines[0].split()
    assert header[0]=='BHMACMOUSE3' and header[5:8]==['0','1','1']
    names=lines[1].split();rows=[dict(zip(names,line.split())) for line in lines[2:]]
    assert len(rows)==int(header[4])
    phases=[int(r['cycle']) for r in rows if r['kind']=='phase']
    reads=[int(r['cycle']) for r in rows if r['kind']=='scc_read' and int(r['address'])==0x9ffffa]
    assert len(phases)==64 and len(reads)>1
    pairs=[(a,b) for a,b in zip(reads,reads[1:]) if a<phases[-1] and b>phases[0]]
    counts=[bisect_right(phases,b)-bisect_right(phases,a) for a,b in pairs]
    assert pairs
    return {'trace_sha256':digest(witness),'phase_rows':len(phases),'read_intervals':len(pairs),
            'phase_changes_per_read_interval':dict(sorted(Counter(counts).items())),
            'max_read_gap_cycles':max(b-a for a,b in pairs)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boothush',required=True,type=Path);p.add_argument('--rom',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    exe=a.boothush.resolve(strict=True);rom=a.rom.resolve(strict=True);out=a.output.resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('output must be outside the repository')
    if digest(rom)!=ROM_SHA:raise ValueError('this analysis requires the pinned title ROM')
    out.mkdir(parents=True,exist_ok=False);cases=[]
    for spacing in (256,1024):
        data,frame,witness=run(exe,rom,out,'trace-'+str(spacing),spacing,True)
        plain,plain_frame,_=run(exe,rom,out,'plain-'+str(spacing),spacing,False)
        for field in ('status','cycles','pc','memory','mouse'):
            assert data[field]==plain[field],(spacing,field)
        assert frame.read_bytes()==plain_frame.read_bytes()
        state=bytes.fromhex(data['memory']['bytes']);assert state[73]==1
        cases.append({'spacing_cycles':spacing,'final_x':int.from_bytes(state[64:66],'big'),
                      'frame_sha256':digest(frame),'trace_matches_plain':True,**trace_summary(witness)})
    report={'status':'pass','rom_sha256':digest(rom),'boothush_sha256':digest(exe),
            'script_sha256':digest(Path(__file__)),'cases':cases,
            'limits':'Modeled SCC-read intervals and phase events; not a hardware timing or sole-cause proof.'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
