#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture neutral, right, up and A actions from the pinned unmodified NES beta.

Output is deliberately observational. Input names identify controller bits,
not proven game states or behavior in a version-matched source build.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from compare_nes_cycles import ROM_HASH, NAV, witness_summary

PPM_HEADER = b"P6\n256 240\n255\n"
IMAGE_SIZE = len(PPM_HEADER)+256*240*3
KEYS = {"neutral":0,"right":128,"up":16,"a_button":1,"right_repeat":128}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(cmd):
    result = subprocess.run(cmd,capture_output=True,text=True,timeout=40,
                            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    return json.loads(result.stdout)

def pixels(frame):
    if len(frame) != IMAGE_SIZE or not frame.startswith(PPM_HEADER):
        raise ValueError("invalid NES frame")
    return frame[len(PPM_HEADER):]

def diff(a,b):
    left,right=pixels(a),pixels(b)
    changed=[i for i in range(256*240) if left[3*i:3*i+3] != right[3*i:3*i+3]]
    box=None if not changed else [min(i%256 for i in changed),min(i//256 for i in changed),
                                  max(i%256 for i in changed),max(i//256 for i in changed)]
    return {"pixels_changed":len(changed),"bounding_box_inclusive":box}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--boothush",type=Path,required=True)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True,help="new directory; retains series, witnesses and manifests")
    a=p.parse_args()
    if sha(a.rom.read_bytes()) != ROM_HASH:
        raise ValueError("incorrect input ROM")
    exe_hash=sha(a.boothush.read_bytes())
    a.output.mkdir(parents=True,exist_ok=False)
    common=[str(a.boothush),"--machine","nes","--rom",str(a.rom),
            "--region","auto","--timeout-ms","30000"]
    cmd=common+["--steps","13000000","--controller-timing","1"]
    for port,step,mask in NAV:
        cmd += ["--controller-event" if port==1 else "--controller2-event",f"{step}:{mask}"]
    seed=run(cmd)
    events=seed["instruction_schedule"]["events"]
    if len(events)!=len(NAV) or not all(e["applied"] for e in events):
        raise ValueError("incomplete seed navigation")
    start=next(e["actual_cycle"] for e in events if e["requested_step"]==10000000)
    points=[start-100000,start,start+100000,start+300000,start+700000,start+1100000,start+1500000]
    stop=start+1600000
    results={}
    for name,mask in KEYS.items():
        path=a.output/(name+".ppmseq")
        trace=a.output/(name+".controller")
        cmd=common+["--steps","15000000","--until-cycle",str(stop),
                    "--capture-series",str(path),"--capture-memory","0:256",
                    "--capture-oam","0:256","--capture-ppu","0x2000:256",
                    "--controller-witness",str(trace),"--controller-witness-cycles",f"{start}:{start+1200000}"]
        for event in events:
            if event["requested_step"] in (10000000,11500000):
                continue
            cmd += ["--controller-cycle" if event["port"]==1 else "--controller2-cycle",
                    f"{event['actual_cycle']}:{event['mask']}"]
        cmd += ["--controller-cycle",f"{start}:{mask}","--controller-cycle",f"{start+1000000}:0"]
        for point in points:
            cmd += ["--capture-cycle",str(point)]
        result=run(cmd)
        info=result["frame_series"]
        if (result["status"]!="condition_met" or result["rom_sha256"]!=ROM_HASH
            or info["executable_sha256"]!=exe_hash or info["rom_sha256"]!=ROM_HASH
            or info["processed"]!=len(points) or info["pending"] or info["missing_images"]
            or result["controller_witness"]["dropped"] or result["controller_schedule"]["pending"]):
            raise RuntimeError("incomplete capture "+name)
        raw=path.read_bytes()
        frames=[]
        for sample in info["samples"]:
            frame=raw[sample["offset"]:sample["offset"]+sample["length"]]
            pixels(frame)
            frames.append(frame)
        witness=witness_summary(trace)
        if witness["1"]["reads"]==0:
            raise RuntimeError("guest did not read controller 1 in "+name)
        if mask and witness["1"]["one_bits"]==0:
            raise RuntimeError("guest never read an active bit in "+name)
        if not mask and witness["1"]["one_bits"]!=0:
            raise RuntimeError("neutral returned active bits")
        (a.output/(name+".json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        results[name]=(result,frames,witness)
    if results["right"] != results["right_repeat"]:
        raise RuntimeError("identical right scenario did not repeat")
    baseline=results["neutral"][1]
    for name in ("right", "up", "a_button"):
        frames=results[name][1]
        if frames[:2] != baseline[:2]:
            raise RuntimeError("images differed before the input could take effect: "+name)
        if not any(frame != base for frame,base in zip(frames[2:],baseline[2:])):
            raise RuntimeError("no observed image difference after input: "+name)
    summary={"rom_sha256":ROM_HASH,"boothush_sha256":exe_hash,
             "region":"pal","seed_navigation_steps":NAV,"hold_start_cycle":start,
             "release_cycle":start+1000000,"requested_points":points,"requested_stop":stop,
             "cases":{},"right_repeat_exact":True,
             "limitations":["NES frames are the last completed PPU frame, not necessarily simultaneous with captured RAM or OAM.",
                 "Differences are observations in an approximate emulator, not assigned game states or physical measurements.",
                 "The tested beta has an unknown source revision and is not a build of the inspected upstream checkout."]}
    for name,(result,frames,witness) in results.items():
        summary["cases"][name]={
            "controller_witness":witness,
            "captures":[{"requested":s["requested"],"actual_cycle":s["cycle"],
                         "completed_frame":s["frame"],"inputs_accepted_before":s["inputs_accepted_before"],
                         "frame_sha256":sha(frame),"difference_from_neutral":diff(base,frame)}
                        for s,base,frame in zip(result["frame_series"]["samples"],baseline,frames)]}
    (a.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    if sha(a.rom.read_bytes()) != ROM_HASH:
        raise RuntimeError("source ROM changed")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
