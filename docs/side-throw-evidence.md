<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Side-tilt knockback

The current 64 KiB Macintosh title ROM throws the defender on a successful
side tilt. In both tested directions, the opponent takes one damage and moves
32.92 pixels away before control returns. In the previous dash build the
same strike applied two damage and left the defender standing in place.

## Try it

From `C:/Repos/Not-Super-Tilt-Bro`, this headless command clicks Start, moves
P2 into range, and makes P1 dash right. It captures the impact on VBL 63.

```powershell
$bh = 'C:/Repos/.task-temp/boothush-pc-visits-20261120-b/a/boothush-active.exe'
& $bh --machine mac128k --rom out/side-throw-title-20261120.rom --cycles 9000000 --timeout-ms 20000 --mouse-button 2000000:1 --mouse-button 2400000:0 --key 3150000:4:1 --key 4800000:4:0 --key 5000000:0:1 --key 5300000:3:1 --key 5600000:3:0 --key 5900000:0:0 --key 6400000:1:1 --capture-series out/side-throw-demo.pbmseq --capture-vbl 63 --capture-memory 0xb00:117
```

The 64-frame clip `out/side-throw-20261120-c/side-throw.gif` shows the captured
arena at three times its original size and displays each VBL for 70 ms.
GIF SHA-256: `7692587833f68deb9581fc501be426094f8ac2fe473c62b09429958cb7ad5e86`.
The ROM SHA-256 is `93001075295c161bdd132832925ece226a503deef2c58f2569dbc1c2d2b5b24c`.

## What the strike does

Sinbad's custom side-tilt hit routine specifies ±800 horizontal speed in the
strike direction and -400 vertical speed in source coordinates. Both force
coefficients are zero, so accumulated damage does not scale this move's
impulse. The Mac ROM's up-positive vertical coordinate converts -400 to +400.
The PAL hitstun calculation yields 13 simulation ticks:
`floor(2 × 1200 / 256) + floor(1200 / 256) = 13`.

The port resolves the two players' hit checks before applying interruptions.
An impact cancels the defender's attack, restores regular gravity and starts
airborne motion. While stunned, the fighter has neutral air friction, ground
friction after touching down, and no voluntary attack, jump or fast fall.
The local prototype uses its existing gravity, paced simulation, bounded
floor and 254-damage saturation rule. Its geometric damage meter represents
two damage per cell. A single side hit contributes one damage in memory.

Sources are from Super Tilt Bro revision
`b132fd25add46f816e04be64c434386743b84b8b`, with its WTFPL v2 notice
retained in `third_party/super-tilt-bro-LICENSE.txt`.

| Source | SHA-256 | Adapted behavior |
| --- | --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` | Side-tilt hit damage and sign-dependent impulse |
| `game/logic/game_states/game/game_logic.asm` | `8ea4d732a54e2f8d476022763698801e3208b3d2638c75f6fea2673dea35f050` | PAL force-vector and hitstun calculation |
| `game/templates/characters/std_thrown.asm` | `40e5f2152cda2dc4c1d913692f3192d152e248d646ed92f4228e0ce5a5a35ccd` | Neutral air friction while stunned |

## BootHush verification

BootHush `066e85d9d93417c9917c1b12a51f85802163b998`, executable SHA-256
`a00fb8b507d79b0f0b88026c2e9cd613a6a7bd78c3aae10858bb5735e4f6db98`, ran the following:

* Eleven combat scenarios covering hits, misses, neutral jabs, interruption
  and recovery for both players, and simultaneous opposing side attacks.
  Full framebuffer checks and keyboard witnesses accompany the captured
  117-byte state. During each strike's 13 simulation ticks of hitstun, an
  independent check computes velocity, capped position and height at each VBL.
* Both mirrored single hits started on VBL 63. Control returned on VBL 78.
  The peak rise was 2.5 pixels; horizontal displacement was ±8,428 raw
  8.8 units. Jump and attack presses during hitstun did not start a move.
  A fresh jump after recovery took off. Neutral jabs retained their existing
  two damage without a side-throw impulse.
* Both hits of a trade registered on VBL 76. Each fighter received one
  damage and 13 ticks of stun, with opposite horizontal velocities and
  equal upward velocities. This also checks that an interruption does not
  prevent the second hit on the same tick.
* The same ROM passed the existing 39 fast-fall/jump scenarios and their
  four defect controls.

The November 20 BootHush executable used in the launch command above
(`543767ae09f39d330803c05bd34311b3b3f485e53f00ec814c54c82d9c8a329f`)
repeated all 11 combat and 39 jump scenarios. Comparing the full outputs
with the preceding RAM-mirroring build gave these results:

| Suite | Emulator runs, including controls | Captured VBL samples |
| --- | ---: | ---: |
| Side-tilt combat, interruption and trades | 17 | 544 |
| Jump and fast fall, including four defect controls | 43 | 1,376 |

Every captured cycle, guest memory snapshot, framebuffer and keyboard
witness matched across the two executables. All 60 runs also matched at their
final program counter, cycle count and VBL. The regenerated gameplay GIF
has the same SHA-256 recorded above. This compares ordinary gameplay with
the new program-counter tracing feature left off; its trace semantics are
tested separately in BootHush. The comparison record is
`out/side-throw-pc-visits-20261120/comparison.json`.

Build and repeat with the [qualified native components](ground-speed-evidence.md):

```powershell
$move = 'out/ground-speed-20261119-b/ground-a/ground.bin'
$jab = 'C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/a/jab.bin'
$air = 'out/air-control-20261117-b/a/air.bin'
python -B scripts/build_mac_title.py --side-throw --side-dash --fast-fall $move $jab $air --output out/new-throw.rom
python -B scripts/test_side_dash.py --side-throw --boothush $bh --rom out/new-throw.rom --stationary-rom out/ground-speed-title-20261119.rom --gif --output out/new-throw-check
python -B scripts/test_native_aerial_jump.py --side-throw --side-dash --fast-fall --boothush $bh --movement $move --jab $jab --air $air --output out/new-throw-jumps
```

Results are in `out/side-throw-20261120-c/report.json` and
`out/side-throw-jump-20261120/report.json`. Source hitstop, thrown animation,
techs, platform edges, ring-outs and complete matches remain open. This
qualifies prototype execution in BootHush. Physical hardware remains untested.
