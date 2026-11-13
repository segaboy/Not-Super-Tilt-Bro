#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare independent controller inputs in the author-provided NES beta.

The ROM is caller-supplied, is not distributed, and has an unverified source
revision. Instruction-indexed input is deterministic for this emulator build
but does not align events to the same guest frame across divergent runs.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROM_SHA256 = "5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa"
NAV = [
    ("--controller-event", "1000000:1"), ("--controller-event", "1030000:0"),
    ("--controller-event", "1800000:1"), ("--controller-event", "1830000:0"),
    ("--controller-event", "4000000:8"), ("--controller-event", "4050000:0"),
    ("--controller-event", "6500000:1"), ("--controller-event", "6550000:0"),
    ("--controller-event", "7500000:8"), ("--controller-event", "7550000:0"),
    ("--controller2-event", "6500000:1"), ("--controller2-event", "6550000:0"),
]
P1 = [("--controller-event", "10000000:128"), ("--controller-event", "11500000:0")]
P2 = [("--controller2-event", "10000000:64"), ("--controller2-event", "11500000:0")]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def execute(exe, rom, frame, events):
    cmd = [str(exe), "--machine", "nes", "--rom", str(rom), "--region", "auto",
           "--steps", "13000000", "--timeout-ms", "30000"]
    for option, value in NAV + events:
        cmd += [option, value]
    cmd += ["--inspect", "0:2048", "--inspect-ppu", "0x2000:2048",
            "--inspect-oam", "0:256", "--frame", str(frame)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=35,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    r = json.loads(p.stdout)
    assert r["status"] == "step_limit" and r["rom_sha256"] == ROM_SHA256, r
    assert r["cartridge"]["region"] == "pal", r
    assert r["controller_schedule"]["accepted"] == len(NAV) + len(events), r
    assert r["controller_schedule"]["pending"] == 0, r
    return r, frame.read_bytes()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--boothush", required=True, type=Path)
    p.add_argument("--rom", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path, help="new JSON report")
    args = p.parse_args()
    if sha(args.rom.read_bytes()) != ROM_SHA256:
        raise ValueError("unexpected ROM SHA-256")
    inputs = {"neutral": [], "player1": P1, "player2": P2, "both": P1 + P2,
              "both_repeat": P1 + P2}
    with tempfile.TemporaryDirectory(prefix="nstb-nes-") as temp:
        runs = {}
        for name, events in inputs.items():
            r, frame = execute(args.boothush, args.rom, Path(temp)/(name + ".ppm"), events)
            runs[name] = (r, frame)
        assert runs["both"] == runs["both_repeat"], "combined input replay differed"
        base, base_frame = runs["neutral"]
        comparisons = {}
        for name in ("player1", "player2", "both"):
            r, frame = runs[name]
            comparisons[name] = {
                "frame_changed": frame != base_frame,
                "cpu_ram_changed_bytes": sum(a != b for a,b in zip(
                    bytes.fromhex(base["memory"]["bytes"]), bytes.fromhex(r["memory"]["bytes"]))),
                "nametable_changed_bytes": sum(a != b for a,b in zip(
                    bytes.fromhex(base["ppu_memory"]["bytes"]), bytes.fromhex(r["ppu_memory"]["bytes"]))),
                "oam_changed_bytes": sum(a != b for a,b in zip(
                    bytes.fromhex(base["oam"]["bytes"]), bytes.fromhex(r["oam"]["bytes"]))),
                "cycles": r["cpu_cycles"], "ppu_frames": r["ppu_frames"],
                "frame_sha256": sha(frame),
            }
        # Each selected input changes the captured frame relative to this
        # baseline on the pinned ROM. This is an emulator regression check,
        # not proof of physical or version-matched gameplay.
        assert all(v["frame_changed"] for v in comparisons.values()), comparisons
        report = {
            "rom_sha256": ROM_SHA256, "boothush_sha256": sha(args.boothush.read_bytes()),
            "region": base["cartridge"]["region"], "steps": 13000000,
            "nav_events": NAV, "player1_events": P1, "player2_events": P2,
            "neutral_cpu_cycles": base["cpu_cycles"], "neutral_ppu_frames": base["ppu_frames"],
            "repeat_exact": True, "comparisons": comparisons,
            "limitations": [
                "The ROM's source revision is unverified; do not assign RAM labels from another revision.",
                "Inputs are scheduled by instruction number; differences can reflect unequal elapsed guest time.",
                "An accepted input or changed screen does not establish which fighter reacted.",
                "No hardware comparison or gameplay correctness is claimed."
            ]
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))
    if sha(args.rom.read_bytes()) != ROM_SHA256:
        raise RuntimeError("input ROM changed")

if __name__ == "__main__":
    main()
