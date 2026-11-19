<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# A moving side tilt for both fighters

Hold one direction and press attack on the ground. The fighter lunges in the
chosen direction, carries momentum through the strike, and brakes during
recovery. A fresh opposite direction held during the dash takes effect after
recovery. Either player can still cancel late recovery with a jump.

With the same mouse and keyboard input, the previous ROM missed a defender
moving into position. The updated ROM scored a hit for two damage. This held
for P1 striking right and P2 striking left. Both fighters also missed when
they dashed away from the opponent.

## Run the hit

Start in `C:/Repos/Not-Super-Tilt-Bro`. This headless example clicks Start,
moves P2 into position and sends P1's side tilt. At VBL 70 the three bytes
at `0xb23` read `02 01 01` (P2 damage, P1 attacks, P1 hits). The final
screen is written to `out/side-dash-hit.pbm`.

```powershell
$bh = 'C:/Repos/.task-temp/boothush-ram-step-20261119-a/a/boothush-active.exe'
& $bh --machine mac128k --rom out/side-dash-title-20261119-a.rom --cycles 9200000 --timeout-ms 20000 --mouse-button 2000000:1 --mouse-button 2400000:0 --key 3150000:4:1 --key 4800000:4:0 --key 5000000:0:1 --key 5300000:3:1 --key 5600000:3:0 --key 5900000:0:0 --key 6400000:1:1 --inspect 0xb23:3 --frame out/side-dash-hit.pbm
```

To rebuild or generate the GIF from the checked frames, use the components
from the [ground-speed build](ground-speed-evidence.md) and a fresh output
path for each command.

```powershell
$move = 'out/ground-speed-20261119-b/ground-a/ground.bin'
$jab = 'C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/a/jab.bin'
$air = 'out/air-control-20261117-b/a/air.bin'
python -B scripts/build_mac_title.py --side-dash --fast-fall $move $jab $air --output out/new-dash.rom
python -B scripts/test_side_dash.py --boothush $bh --rom out/new-dash.rom --stationary-rom out/ground-speed-title-20261119.rom --gif --output out/new-dash-traces
python -B scripts/test_native_aerial_jump.py --side-dash --fast-fall --boothush $bh --movement $move --jab $jab --air $air --output out/new-dash-jumps
```

## Source and observations

Sinbad's side-tilt windup sets signed horizontal velocity to 256. The windup
and hit ticks then approach (512 × 4) / 3, integer 682, in steps of 64.
The grounded follow-up template retains velocity on the phase-transition tick
and uses ground friction in recovery. In the port a recovery tick reduces
speed by 96 toward zero. Source files from Super Tilt Bro
`b132fd25add46f816e04be64c434386743b84b8b`:

| Source file | SHA-256 |
| --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` |
| `game/templates/characters/tpl_grounded_attack_followup.asm` | `b81118e4236ba935d1d7fa32be30e0161d842089cd28edbc9774400b2b62d3a1` |
| `game/templates/characters/std_friction_routines.asm` | `bc6fd5308b70439b93f11210bd778b0315d6f3925635395d6f2457ca48ee8107` |
| `game/logic/utils.asm` | `7bc4f603752f6fa8deeef2bc9a897e4d61c83c2a85bfcc064bbf16c850b7961b` |

The existing [timing and collision receipt](side-tilt-evidence.md) describes
the 12/12/18 PAL phases, the local damage and range rule and placeholder art.
The Mac adaptation uses the existing stage clamps. It does not implement
the source game's platform-edge reposition, knockback, source sprites or sound.

Four directional cases each matched a signed velocity and position oracle
over 51 consecutive intervals inside the move. P1 traveled 67.35 pixels to
the right before stopping. P2 hit the stage bound in the outward rightward
case and traveled 52.25 pixels. Two additional cases qualified late recovery
jumps. Both toward-facing cases were also run with the previous stationary
ROM to verify the missed hit. The new ROM passed all 39 jump/fast-fall
scenarios and their four mutation controls.

The tested 65,536-byte ROM SHA-256 is
`6e37b36cab60ed8d925a88022423127c4d07469a550f73f210b204ab9993a500`.
The side dash adds no RAM field. The emitter ends at 40,528. BootHush build
`69596d6af629061d1f09fc1430279093b8c2c3fb` executable SHA-256 is
`c709c7f10b5f8e2a908cc2f06a74192269073dda52e8aa4f7d23a80dac89ac28`.
The gameplay samples and all 12 full framebuffer sequences and keyboard
witnesses matched the preceding BootHush build `cc182c2`.

Find the results under `out/side-dash-20261119-ram-step/` and
`out/side-dash-jump-ram-step-20261119/`. The gameplay clip
`out/side-dash-20261119-ram-step/side-dash.gif` crops the actual
arena pixels, enlarges them threefold, and displays each of 64 modeled VBLs
for 70 ms. Its SHA-256 is
`c6ae67e575fed1f5d2723b73fd4574c6078458cdd7696d531a0bac38ca5e918c`.
This is prototype gameplay in BootHush. Physical keyboard rollover, a full
match and source-matched NES timing remain open.
