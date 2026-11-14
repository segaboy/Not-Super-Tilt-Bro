<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Sinbad jump and short-hop experiment — 2026-11-14

This opt-in Mac replacement-ROM experiment extends the existing source-derived horizontal movement with jump preparation, upward movement, a shorter jump after an early release, landing, and a subsequent grounded jump. It is a narrow adaptation with original placeholder art, **not a playable match**, a full translation of Super Tilt Bro physics, an independently matched NES result, or a physical Mac observation.

## Sources and boundaries

The game-source input is Super Tilt Bro commit `b132fd25add46f816e04be64c434386743b84b8b` under its documented WTFPL v2 terms, alongside the project's independently authored GPL-3.0-or-later startup and input code. `game-mod/characters/sinbad/states.asm` SHA-256 `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` defines PAL jumpsquat duration 4, jump power magnitude `0x0480`, short-hop power magnitude `0x0102`, and the PAL extra short-hop time of 4. `game/templates/characters/std_jumping.asm` SHA-256 `21c0a0cc0d5e0420d7b17c4cdd4022076cf7b85b10fc6d28f48ebf5965595c7e` describes advancing the clock, starting jump velocity at the squat boundary, and selecting short-hop velocity when the jump input is released at the later decision point. `game/templates/characters/std_constant_tables.asm` SHA-256 `62d81546fd8d8d29d273c92130a86a8e26433d95eefbb41a35f3449791188e80` identifies the signs and PAL timing composition.

The local representation stores **height above the floor**, so its positive upward velocity has the opposite sign to the source's negative vertical velocity. It uses the source magnitudes and clock points, but the local `0x0060` acceleration, `-0x0200` terminal speed, position integration order, floor clamp, input mapping, graphics, and behavior when inputs overlap are prototype choices; no claim is made that they reproduce the complete source game. Source squat cancellation, actual stage collisions, aerial directional influence, aerial jump, complete controller table, animations, attacks, sound and multiplayer are not implemented. The model ignores a new jump while airborne even though the source character has an aerial-jump capability. These choices and the original game source are not ClasSICK implementation inputs.

## Build, behavior, and checks

`scripts/build_mac_jump.py` generates the opt-in 65,536-byte ROM SHA-256 `70cabce350ee510b93121c15ff3151509926bdafba918bc1adb859c575fad37b`, occupied through offset 7,905 inclusive. The existing default horizontal ROM remains byte-identical at SHA-256 `3e69619032fc71bed6e1afe3cf09c4e7c0436000c6a56bdd664d373481f56abd`; its complete existing movement/fault suite was rerun and passed. This ROM size is not a complete 128K runtime, stack or asset budget.

In the optional ROM, the existing `NST4` block extends from 24 to 32 bytes. Byte 24 is jump state (0 grounded, 1 preparation, 2 airborne), byte 25 is the local jump clock, bytes 26–27 are signed 8.8 vertical velocity in the local positive-up convention, bytes 28–29 are unsigned 8.8 height, byte 30 records the modeled jump key and byte 31 is a wrapping diagnostic jump count. Key position 2 controls jump. The existing 5-of-6 serviced-VBL pacing is an approximation, not validated PAL or original Mac timing.

The test executable used BootHush SHA-256 `1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`. Six bounded headless scenarios passed: early-release short hop, held full jump, release after the short-hop decision, ignored airborne retry, simultaneous horizontal movement and jump, and another jump after landing. Each sampled 512x342 frame was checked against independently reconstructed placeholder pixels. For adjacent sampled VBLs without a delivered key, a separately written model checked preparation, short-hop selection, velocity, height, landing and pacing. Keyboard witnesses reported no dropped, rejected or pending events.

In the early-release run, the modeled key press and release were delivered at cycles 697,128 and 1,348,324. At VBL 10 the clock was 4 and the initial upward velocity was 1,152 (`0x0480`); at VBL 14, clock 8, the released key selected velocity 258 (`0x0102`). The maximum sampled height was 3,366 in 8.8 units; holding the key instead reached 6,336 in the same samples. A later release delivered at cycle 2,129,766, after the decision, also reached 6,336. All three subsequently landed. These are exact observations of this ROM and emulator configuration, not source-game measurements. The second-jump test reaches its second airborne state; it does not claim a second complete landing.

## Reproduce and media

```powershell
$py = 'C:\ClasSICK\bootstrap-clean-source-verified\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py -B scripts/test_mac_jump.py --boothush $bh --keep out/NEW-JUMP-TEST
& $py -B scripts/test_mac_movement.py --boothush $bh --keep out/NEW-MOVEMENT-REGRESSION
& $py -B scripts/capture_jump_evidence.py --boothush $bh --output out/NEW-JUMP-MEDIA
```

All output directories must be new. Full states, original PBM sequences and witnesses for the six-case run are retained under ignored `out/jump-shorthop-20261114-b`; the unchanged horizontal regression is in `out/post-shorthop-movement-regression-20261114`. The original silent Y4M, six PBM/PNG stills, GIF, MP4, input command and manifest are in `out/jump-shorthop-media-20261114`. The capture contains 22 sampled frames at 30 fps; its display duration is modeled, not a physical timing measurement. GIF SHA-256 `04c9002d6b593ce4f148e156dd85bbac89f40b351d9ecad6165ba3418062c875`, MP4 SHA-256 `4a3d3b837d0aba7ceb813082b05ba78d25ce08d84921c61876ef727ecf4751bb`. PNGs are lossless conversions of original modeled guest-frame PBMs; MP4 is lossy. No Apple or game artwork is included.

The VBL 20 PBM was also passed to BootHush's separate original 286 bitmap-display diagnostic. Its EGA output matched all 175,104 canvas pixels and 48,896 margins. The PBM SHA-256 was `d3ff1b9af9730d1817f8777bed2dd96ad566e50fe9e6ed3bd73c60abbf479f3d`; the diagnostic results and 286 frame are in `C:/Repos/boothush/out/pc286-jump-image-20261114`, with method and limits in `C:/Repos/boothush/docs/mac-pc286-bitmap-20261114.md`. This is an emulator display comparison; the 286 did not run game logic, and the source-derived game material is not an eligible ClasSICK implementation input without separate review.
