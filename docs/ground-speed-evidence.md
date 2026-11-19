<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Ground speed after landing

2026-11-19. The current 64 KiB Mac title ROM includes both fast fall and the
corrected Sinbad ground movement component. Holding a direction while landing
now brings the fighter to exactly two pixels per gameplay tick. In the previous
fast-fall ROM, the same landing left the fighter running slightly faster for as
long as the key stayed down.

| Direction | Last three velocities (signed 8.8) | Previous ROM at steady speed | First VBL at target |
| --- | --- | ---: | ---: |
| P1 right | 387, 451, 512 | 515 | 74 |
| P2 left | -387, -451, -512 | -515 | 74 |

The state comes from actual jumps after mouse Start, under BootHush
`cc182c2311616aff8137ac848c89b1f049acb707`, executable SHA-256
`5fa45b7542409300b7604606a78c81d4ee95e888a57c592a83d0cec43ce1056e`.
The signed target check rejects the previous fast-fall ROM on both schedules.
These subpixel differences are measured in guest memory. All captured
framebuffers also pass the existing per-pixel checks.

## Run or build

From `C:/Repos/Not-Super-Tilt-Bro`, this command clicks Start, runs right,
jumps, lands and reads P1's velocity. The verified output at VBL 94 contains
`"bytes":"0200"` (+512) and the final screen is saved as a PBM.

```powershell
$bh = 'C:/Repos/.task-temp/boothush-drive-selection-20261119-a/a/boothush-active.exe'
& $bh --machine mac128k --rom out/ground-speed-title-20261119.rom --cycles 12300000 --timeout-ms 20000 --mouse-button 2000000:1 --mouse-button 2400000:0 --key 3500000:0:1 --key 4200000:2:1 --inspect 0xb0e:2 --frame out/ground-speed-landed.pbm
```

To rebuild with the qualified Windows cross-compiler and native components,
choose new output paths and run:

```powershell
$tools = 'C:/Repos/.task-temp/m68k-windows-native-20261114-a/x-tools-v3-win/m68k-unknown-elf/bin'
$old = 'C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/a/movement.bin'
$jab = 'C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/a/jab.bin'
python -B scripts/test_native_air_control.py --ground-control --boothush $bh --tool-bin $tools --movement $old --jab $jab --output out/new-ground
python -B scripts/build_mac_title.py --fast-fall out/new-ground/ground-a/ground.bin $jab out/new-ground/a/air.bin --output out/new-current.rom
python -B scripts/test_native_aerial_jump.py --fast-fall --boothush $bh --movement out/new-ground/ground-a/ground.bin --jab $jab --air out/new-ground/a/air.bin --output out/new-ground-fall
```

## Provenance and verification

The pinned upstream revision is `b132fd25add46f816e04be64c434386743b84b8b`.
The signed step toward the directional target follows
`game/templates/characters/std_running.asm`
(`538f349a0365a5adee4e2a798ab311d88e3e9103eef02cd9a5ab0a556be0f790`)
and `game/logic/utils.asm`
(`7bc4f603752f6fa8deeef2bc9a897e4d61c83c2a85bfcc064bbf16c850b7961b`).
Sinbad's PAL run speed ($0200), acceleration ($40) and ground friction ($60)
come from `game-mod/characters/sinbad/states.asm`
(`cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55`).
The [movement receipt](movement-evidence.md) covers source neutral friction,
the keyboard adapter and position representation. The WTFPL v2 source license
is retained in `third_party/super-tilt-bro-LICENSE.txt`.

* Twin native ground-component builds produced 68 identical bytes, SHA-256
  `fa66cc4d59cc4320a5dfca39786e8b436cd460d2dadcb1fd2363fed0a370aa0c`.
  An isolated BootHush probe checked 522 steps for positive, negative and
  neutral input, including signed extremes and fractional speed on either
  side of the target. The old component failed that oracle.
* The combined ROM SHA-256 is
  `2f4f0ec5a13be12473c6502f42f5dc7c8dfdebac4f0ca3dc7b17a3ba1caa46dc`.
  All 14 steering and landing cases passed with the 522-step aerial probe and
  six existing air-call checks. The same ROM passed the 39 jump and fast-fall
  scenarios and their four mutation controls. Rebuilding the older native-air
  profile also passed its 14-case suite with its original ROM identity.
* Local reports are in `out/ground-speed-20261119-b/`,
  `out/ground-speed-fall-20261119/` and `out/ground-speed-20261119-legacy/`.
  The new ROM's fast-fall comparison is in
  `out/ground-speed-media-20261119/fast-fall.gif`. This fixture has no
  horizontal input and reproduces the earlier fast-fall image sequence.

The running rule and fixtures are game-specific. The full-register observations
and image checks exercise the shared BootHush test method. Source-matched NES
execution, a full match and original Macintosh hardware qualification remain open.
