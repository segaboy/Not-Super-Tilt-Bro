<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Fast fall for both players

2026-11-19. In the standalone 65,536-byte Macintosh 128K title ROM, start
with the mouse and jump using the keyboard. While airborne, release the Down
key with the player's direction, attack and jump keys all up. The fighter
immediately acquires a downward speed of five pixels per gameplay tick.
Holding Down leaves the ordinary jump trajectory intact. An available aerial
jump resets the downward speed and terminal velocity. Landing also restores
normal gravity. BootHush's modeled Down key indices are 8 for P1 and 9 for P2.

## Source and limits

The pinned Super Tilt Bro source is
`b132fd25add46f816e04be64c434386743b84b8b`. Its license notice is retained
in [third_party](../third_party/super-tilt-bro-LICENSE.txt).

| Source | SHA-256 | Behavior used |
| --- | --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` | Sinbad fast-fall speed of $0500 and neutral aerial dispatch |
| `game/templates/characters/std_constant_tables.asm` | `62d81546fd8d8d29d273c92130a86a8e26433d95eefbb41a35f3449791188e80` | PAL character speed table |
| `game/templates/characters/std_aerial_input.asm` | `c26ddb464dc9032f3f18a7bf3c7c2102d1e85a4ff0ee68141c374134be130045` | Previous input equals Down alone, current input neutral, set gravity target and speed |
| `game/templates/characters/std_jumping.asm` | `21c0a0cc0d5e0420d7b17c4cdd4022076cf7b85b10fc6d28f48ebf5965595c7e` | Reset gravity and velocity at aerial-jump entry |

The Macintosh ROM represents upward speed as positive. It writes -1280 in
local 8.8 units and uses the faster downward terminal speed until landing or
an aerial jump. Input is processed one delivered key at a time. The local
short-hop clock, floor, frame pacing, geometric fighters and horizontal
steering remain those of the existing prototype. The Down keys implement the
airborne move only. Ground shielding, full NES input timing, sound and
physical Macintosh behavior remain open.

## Results on BootHush

The feature suite passed 39 scenarios and four existing aerial-jump mutation
controls. It checks complete keyboard delivery, both players' state and
framebuffer pixels. Separate expectations cover transitions between VBLs and
verify that ground contact and aerial jumps clear the fast-fall flag. For
each player, release at the apex, during ascent and during descent succeeds.
Holding Down, releasing it on the floor, and release with a direction,
attack or jump still held leave fast fall inactive.

| Matched single-player scenario | First captured VBL with fast fall | Landing VBL for P1 and P2 |
| --- | ---: | ---: |
| Down released during ascent | 44 | 48 |
| Down released at apex | 47 | 52 |
| Down released during descent | 53 | 57 |
| Down held | — | 64 |

In the two-player comparison, P1 is grounded at VBL 53 while P2 is still
21 pixels above the floor. The recorded sequence covers both players after
mouse Start and includes their actual keyboard transitions. The reusable
BootHush observation is that the two additional key indices can be delivered
independently and correlated with guest state and full frames. This is a
modeled keyboard observation. Game-derived code and captures stay in Tilt.

| Artifact | Identity |
| --- | --- |
| BootHush executable | `3d48d7515d3492ac796d3899ed2c47603d3330e3f0f64352fd29ed6a78284ff4` |
| CLI-built fast-fall ROM | `f551d8a7cd49ceebc65409f11ec77fe6c371a532caad4cdfde5aa2182123a72f`, 65,536 bytes, emitter ends at 39,944 |
| Prior native-air title, rebuilt without fast fall | `f28739e256e1426b0849e3ed3c1c6dda01a6c6d39de1b57e9d2e2aaf86a3b00d`, 20 legacy cases passed |
| Generated GIF | `b923e9a3f2e0f40b4e77fe2361a2163b272770b607d9f53da29ca9ee5d7c9319` |

## Reproduce

From the Tilt checkout, set the following paths to the retained native
components used in the [air-control qualification](aerial-control-evidence.md).
Use fresh output directories for each qualification.

```powershell
$move = 'C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/a/movement.bin'
$jab = 'C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/a/jab.bin'
$air = 'out/air-control-20261117-b/a/air.bin'
$bh = 'C:/Repos/.task-temp/boothush-floppy-writes-20261118-b/a/boothush-active.exe'
python -B scripts/build_mac_title.py --fast-fall $move $jab $air --output out/new-fast-fall.rom
python -B scripts/test_native_aerial_jump.py --boothush $bh --movement $move --jab $jab --air $air --fast-fall --output out/new-fast-fall-check
python -B scripts/capture_aerial_evidence.py --fast-fall --results out/new-fast-fall-check --output out/new-fast-fall-media
```

The local reports are `out/fast-fall-20261119-b/report.json` and
`out/fast-fall-20261119-legacy/report.json`. The playable prototype is
`out/fast-fall-title-20261119.rom`. The GIF and VBL 53 PNG are under
`out/fast-fall-media-20261119/`. Each sampled VBL is shown for 100 ms in the
GIF, about six times slower than the modeled machine. These captures show a
single stage and the tested moves. A full match and a source-matched NES
comparison are future milestones.
