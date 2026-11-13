#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the narrowly scoped Sinbad PAL run-entry transition in BootHush."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from build_mac_run_transition import build

HEADER = b"P4\n512 342\n"
BASIC = [(600000,0,1),(900000,0,0),(1200000,1,1),(1500000,1,0)]
HELD = [(600000,0,1),(1500000,0,0)]
REVERSE = [(600000,0,1),(1200000,1,1)]
REPEAT = [(600000,0,1),(1200000,0,1)]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def invoke(exe, rom, folder, name, events):
    series = folder/(name+".pbmseq")
    keyboard = folder/(name+".keyboard")
    display = folder/(name+".display")
    cmd = [str(exe),"--machine","mac128k","--rom",str(rom),
           "--cycles","2000000","--timeout-ms","15000",
           "--capture-series",str(series),"--capture-memory","0xb00:17",
           "--capture-vbl","5","--capture-vbl","8","--capture-vbl","11","--capture-vbl","14",
           "--keyboard-witness",str(keyboard),"--display-witness",str(display),
           "--display-witness-range","550000:1900000",
           "--display-witness-memory","0x1a700:21888","--inspect","0xb00:17"]
    for cycle,key,state in events:
        cmd += ["--key",f"{cycle}:{key}:{state}"]
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=20,
                       creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    result = json.loads(p.stdout)
    info = result["frame_series"]
    assert result["status"] == "cycle_limit",result
    assert info["rom_sha256"] == digest(rom.read_bytes())
    assert info["executable_sha256"] == digest(exe.read_bytes())
    assert (info["requested"],info["processed"],info["pending"],info["missing_images"],info["dropped"]) == (4,4,0,0,0)
    assert [s["requested"] for s in info["samples"]] == [5,8,11,14]
    assert result["keyboard_witness"]["dropped"] == 0
    assert result["keyboard_witness"]["rejected"] == 0
    assert result["keyboard_witness"]["pending"] == 0
    assert result["display_witness"]["dropped"] == 0
    trace = keyboard.read_text(encoding="ascii")
    rows = [line.split() for line in trace.splitlines()[2:]]
    actual_replies = [int(row[3]) for row in rows if row[2] == "key_delivered"]
    expected_replies = [((key<<1)|1|(0 if state else 0x80)) for _,key,state in events]
    assert actual_replies == expected_replies,(name,actual_replies,expected_replies)
    drows = [line.split() for line in display.read_text(encoding="ascii").splitlines()[2:]]
    assert not any(row[3] == "fault" for row in drows)
    if events:
        assert any(row[3] == "write" for row in drows)
    data = series.read_bytes()
    frames = []
    states = []
    for s in info["samples"]:
        assert s["processed"] and s["image_available"]
        raw = bytes.fromhex(s["memory"]["bytes"])
        assert len(raw) == 17 and raw[:8] == b"NST3"+bytes.fromhex("00000001")
        states.append(tuple(raw[8:17]))
        frame = data[s["offset"]:s["offset"]+s["length"]]
        assert frame.startswith(HEADER) and len(frame) == len(HEADER)+21888
        frames.append(frame)
    return result, states, frames, trace, display.read_text(encoding="ascii")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boothush",required=True,type=Path)
    p.add_argument("--keep",type=Path,help="new directory in which to retain generated observations")
    a = p.parse_args()
    if a.keep:
        a.keep.mkdir(parents=True,exist_ok=False)
        test(a.boothush,a.keep)
    else:
        with tempfile.TemporaryDirectory(prefix="nstb-run-entry-") as tmp:
            test(a.boothush,Path(tmp))

def test(exe,root):
    rom = root/"source-run-entry.rom"
    image,code_size = build()
    with rom.open("xb") as f:
        f.write(image)
    cases = {}
    for name,events in (("sequence",BASIC),("sequence_repeat",BASIC),
                        ("hold",HELD),("reverse",REVERSE),("repeat_press",REPEAT),("neutral",[])):
        result,states,frames,kb,display = invoke(exe,rom,root,name,events)
        # state layout: position, last reply, presses, releases,
        # normalized state, direction, velocity hi/lo, run-entry counter.
        cases[name] = (result,states,frames,kb,display)
        (root/(name+".json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    seq=cases["sequence"]
    expected=[
      (2,1,1,0,1,1,1,0,1),       # right press => PAL +0x0100
      (2,0x81,1,1,0,1,1,0,1),   # release => idle; entry keeps velocity
      (1,3,2,1,1,0,0xff,0,2),   # left press => PAL -0x0100
      (1,0x83,2,2,0,0,0xff,0,2)]
    assert seq[1] == expected,seq[1]
    assert seq == cases["sequence_repeat"],"repeat result, frames or witnesses differed"
    assert seq[2][0] == seq[2][1] and seq[2][2] == seq[2][3]
    assert seq[2][0] != seq[2][2]
    hold=cases["hold"][1]
    assert all(x[4:9] == (1,1,1,0,1) for x in hold[:3])
    assert hold[3][4:9] == (0,1,1,0,1)
    rev=cases["reverse"][1]
    assert rev[2][4:9] == (1,0,0xff,0,2)
    same=cases["repeat_press"][1]
    assert same[2][4:9] == (1,1,1,0,1)
    assert all(x[4:9] == (0,0,0,0,0) for x in cases["neutral"][1])
    summary={"status":"pass","rom_sha256":digest(image),"boothush_sha256":digest(exe.read_bytes()),
             "rom_used_through":0x104+code_size,"cases":list(cases),
             "sequence":[{"vbl":s["frame"],"cycle":s["cycle"],"state":list(st)}
                         for s,st in zip(seq[0]["frame_series"]["samples"],seq[1])],
             "scope":"source-derived PAL running entry only; normalized state and placeholder display",
             "keyboard_reply_order":[1,129,3,131],
             "repeat_exact":True,
             "limitations":["No position physics, acceleration, friction, animation or full input table.",
               "Overlapping keys are a synthetic direct-transition test, not verified source input dispatch.",
               "No revision-matched NES execution or physical hardware test."]}
    (root/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
