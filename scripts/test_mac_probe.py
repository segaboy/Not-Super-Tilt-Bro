#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Boot the original arena probe and verify neutral and keyboard behavior."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from build_mac_probe import build

HEADER = b"P4\n512 342\n"

def execute(exe, rom, frame, keys=False):
    cmd = [str(exe), "--machine", "mac128k", "--rom", str(rom),
           "--cycles", "3000000" if keys else "1000000", "--timeout-ms", "15000",
           "--inspect", "0xb00:8", "--frame", str(frame)]
    if keys:
        cmd += ["--key", "600000:0:1", "--key", "650000:0:0",
                "--until", "0xb04:4:2"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    result = json.loads(p.stdout)
    assert result["status"] == ("condition_met" if keys else "cycle_limit"), result
    assert result["memory"]["bytes"].lower() == ("4e53544200000002" if keys else "4e53544200000001"), result
    data = frame.read_bytes()
    assert data.startswith(HEADER) and len(data) == len(HEADER) + 21888
    pixels = data[len(HEADER):]
    assert all(pixels[y*64+x] == 0xff for y in range(252,260) for x in range(16,48))
    assert pixels[228*64+37:228*64+39] == bytes.fromhex("03c0")
    assert pixels[100*64+10] == 0
    expected = bytes.fromhex("0003c0" if keys else "03c000")
    assert pixels[228*64+25:228*64+28] == expected
    return result, data

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boothush", required=True, type=Path)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="nstb-mac-") as tmp:
        root = Path(tmp)
        rom = root / "probe.rom"
        rom.write_bytes(build()[0])
        neutral, frame_neutral = execute(args.boothush, rom, root / "neutral.pbm")
        first, frame_first = execute(args.boothush, rom, root / "first.pbm", True)
        second, frame_second = execute(args.boothush, rom, root / "second.pbm", True)
        assert first == second and frame_first == frame_second, "repeated input runs differ"
        assert frame_neutral != frame_first, "key did not change pixels"
        print(json.dumps({"result": "pass", "neutral": neutral, "input": first,
                          "repeat_exact": True}, indent=2))

if __name__ == "__main__":
    main()
