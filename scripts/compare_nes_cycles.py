#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run cycle-aligned, independently controlled observations of the pinned beta.

Output is local evidence, not a claim of source-version or hardware equivalence.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROM_HASH = "5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa"
# These navigation steps were first observed on this specific beta.
NAV = [(1,1000000,1),(1,1030000,0),(1,1800000,1),(1,1830000,0),
       (1,4000000,8),(1,4050000,0),(1,6500000,1),(1,6550000,0),
       (1,7500000,8),(1,7550000,0),(2,6500000,1),(2,6550000,0),
       (1,10000000,0),(1,11500000,0),(2,10000000,0),(2,11500000,0)]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def invoke(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=40,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return json.loads(p.stdout)

def witness_summary(path):
    lines = path.read_text(encoding="ascii").splitlines()
    if len(lines) < 2 or not lines[0].startswith("BHNESCTRL1 "):
        raise ValueError("unexpected controller witness format")
    stats = {str(p): {"reads":0,"one_bits":0} for p in (1,2)}
    for line in lines[2:]:
        row = line.split()
        if len(row) != 8:
            raise ValueError("malformed controller witness")
        if row[4] == "read" and row[5] in stats:
            item = stats[row[5]]
            item["reads"] += 1
            item["one_bits"] += int(row[6]) & 1
    return stats

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boothush", type=Path, required=True)
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    if sha(a.rom.read_bytes()) != ROM_HASH:
        raise ValueError("unrecognized beta ROM SHA-256")
    common = [str(a.boothush), "--machine","nes","--rom",str(a.rom),
              "--region","auto","--timeout-ms","30000"]
    cmd = common + ["--steps","13000000","--controller-timing","1"]
    for port,step,mask in NAV:
        cmd += ["--controller-event" if port == 1 else "--controller2-event", f"{step}:{mask}"]
    seed = invoke(cmd)
    events = seed["instruction_schedule"]["events"]
    if len(events) != len(NAV) or not all(e["applied"] for e in events):
        raise RuntimeError("navigation timing was incomplete")
    target = seed["cpu_cycles"]
    movement_start = next(e["actual_cycle"] for e in events if e["requested_step"] == 10000000)
    cases = {"neutral":(0,0), "player1":(128,0), "player2":(0,64),
             "both":(128,64), "both_repeat":(128,64)}
    with tempfile.TemporaryDirectory(prefix="nstb-cycle-") as tmp:
        results = {}
        for name,(p1,p2) in cases.items():
            root = Path(tmp)
            frame = root / (name+".ppm")
            witness = root / (name+".ctrl")
            cmd = common + ["--steps","15000000","--until-cycle",str(target),
                            "--observe-cycle",f"{target}:0:256",
                            "--inspect","0:2048","--inspect-ppu","0x2000:2048",
                            "--inspect-oam","0:256","--frame",str(frame),
                            "--controller-witness",str(witness),
                            "--controller-witness-cycles",f"{movement_start}:{movement_start+100000}"]
            for event in events:
                mask = event["mask"]
                if event["requested_step"] == 10000000:
                    mask = p1 if event["port"] == 1 else p2
                cmd += ["--controller-cycle" if event["port"] == 1 else "--controller2-cycle",
                        f"{event['actual_cycle']}:{mask}"]
            r = invoke(cmd)
            if (r["status"] != "condition_met" or r["rom_sha256"] != ROM_HASH
                or r["cartridge"]["region"] != "pal" or r["controller_schedule"]["pending"] != 0
                or r["controller_schedule"]["accepted"] != len(events)
                or not 0 <= r["cpu_cycles"] - target < 1024
                or r["cycle_observations"]["completed"] != 1
                or r["controller_witness"]["dropped"] != 0):
                raise RuntimeError("incomplete scenario: "+name)
            r.pop("controller_witness")
            results[name] = (r, frame.read_bytes(), witness_summary(witness))
        if results["both"] != results["both_repeat"]:
            raise RuntimeError("repeated combined run differed")
        base, base_frame, _ = results["neutral"]
        report_cases = {}
        for name,(r,frame,witness) in results.items():
            report_cases[name] = {
                "actual_cycle":r["cpu_cycles"], "cycle_over_target":r["cpu_cycles"]-target,
                "frame":r["ppu_frames"], "frame_sha256":sha(frame),
                "frame_changed_from_neutral":frame != base_frame,
                "cpu_changed_bytes":sum(x!=y for x,y in zip(bytes.fromhex(base["memory"]["bytes"]),bytes.fromhex(r["memory"]["bytes"]))),
                "oam_changed_bytes":sum(x!=y for x,y in zip(bytes.fromhex(base["oam"]["bytes"]),bytes.fromhex(r["oam"]["bytes"]))),
                "controller_reads_during_window":witness,
                "schedule":r["cycle_schedule"],
            }
        # During the selected witness window the guest must read both ports.
        # With our fixed single-bit holds, only the active port should return
        # a set serial bit; this does not identify the controlled fighter.
        for name, active in (("neutral",()), ("player1",(1,)), ("player2",(2,)), ("both",(1,2))):
            stats = report_cases[name]["controller_reads_during_window"]
            for port in (1,2):
                if stats[str(port)]["reads"] == 0:
                    raise RuntimeError(f"no guest reads on port {port} in {name}")
                ones = stats[str(port)]["one_bits"]
                if (port in active and ones == 0) or (port not in active and ones != 0):
                    raise RuntimeError(f"unexpected guest reads on port {port} in {name}")
        report = {"rom_sha256":ROM_HASH, "boothush_sha256":sha(a.boothush.read_bytes()),
                  "region":"pal","target_cycle":target, "movement_start_cycle":movement_start,
                  "witness_end_cycle":movement_start+100000, "navigation":NAV,
                  "cases":report_cases, "repeat_exact":True,
                  "limitations":["CPU instruction-boundary rounding can differ between scenarios.",
                    "Read serial one bits are not mapped to named fighter state by this report.",
                    "Binary source revision and hardware accuracy remain unverified."]}
    if sha(a.rom.read_bytes()) != ROM_HASH:
        raise RuntimeError("source ROM changed")
    a.report.parent.mkdir(parents=True, exist_ok=True)
    with a.report.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print(json.dumps({"target_cycle":target, "cases":report_cases, "repeat_exact":True},indent=2))

if __name__ == "__main__":
    main()
