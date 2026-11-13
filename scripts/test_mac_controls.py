#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify three-position Mac keyboard probe using BootHush and guest pixels."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from build_mac_controls import build

HEADER = b"P4\n512 342\n"
BASIC = [(600000,0,1),(900000,0,0),(1200000,1,1),(1500000,1,0)]
BOUNDS = [(600000,0,1),(800000,0,0),(1000000,0,1),(1200000,0,0),
          (1400000,1,1),(1600000,1,0),(1800000,1,1),(2000000,1,0),
          (2200000,1,1),(2400000,1,0)]

def run(exe,rom,path,cycles,events):
    cmd = [str(exe),"--machine","mac128k","--rom",str(rom),"--cycles",str(cycles),
           "--timeout-ms","15000","--inspect","0xb00:12","--frame",str(path)]
    for cycle,key,state in events:
        if cycle <= cycles:
            cmd += ["--key",f"{cycle}:{key}:{state}"]
    proc = subprocess.run(cmd,capture_output=True,text=True,timeout=20,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if proc.returncode:
        raise RuntimeError(proc.stdout+proc.stderr)
    r = json.loads(proc.stdout)
    if r["status"] != "cycle_limit":
        raise AssertionError(r)
    raw = bytes.fromhex(r["memory"]["bytes"])
    assert raw[:8] == b"NST2"+bytes.fromhex("00000001"), r
    image = path.read_bytes()
    assert image.startswith(HEADER) and len(image) == len(HEADER)+21888
    return r,raw[8:12],image[len(HEADER):]

def verify_pixels(pixels,pos):
    # Only inspect a known, nonzero row; exact state and a separate neutral
    # area also provide checks against a stale or incorrectly captured frame.
    expected = bytearray(4)
    expected[pos:pos+2] = bytes.fromhex("03c0")
    assert pixels[228*64+24:228*64+28] == expected
    assert pixels[228*64+37:228*64+39] == bytes.fromhex("03c0")
    assert all(pixels[y*64+x] == 0xff for y in range(252,260) for x in range(16,48))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boothush",required=True,type=Path)
    a = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="nstb-controls-") as temp:
        root = Path(temp)
        rom = root/"controls.rom"
        rom.write_bytes(build()[0])
        cases = [
          ("neutral", 800000, [], (1,0,0,0)),
          ("right", 800000, BASIC, (2,1,1,0)),
          ("right_release", 1050000, BASIC, (2,0x81,1,1)),
          ("left", 1400000, BASIC, (1,3,2,1)),
          ("left_release", 2000000, BASIC, (1,0x83,2,2)),
          ("max_bound", 1300000, BOUNDS, (2,0x81,2,2)),
          ("min_bound", 2600000, BOUNDS, (0,0x83,5,5)),
          ("repeat", 2000000, BASIC, (1,0x83,2,2)),
        ]
        outputs = {}
        for name,cycles,events,expected in cases:
            result,state,pixels = run(a.boothush,rom,root/(name+".pbm"),cycles,events)
            assert tuple(state) == expected,(name,state.hex(),expected)
            verify_pixels(pixels,expected[0])
            outputs[name] = (result,pixels)
        assert outputs["left_release"] == outputs["repeat"],"replay differed"
        print(json.dumps({"result":"pass","cases":len(cases),
            "states":{name:list(expected) for name,_,_,expected in cases},
            "replay_exact":True,"emulated_keyboard":"M0110 positions 0 and 1"},indent=2))

if __name__ == "__main__":
    main()
