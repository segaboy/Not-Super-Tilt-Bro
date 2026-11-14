<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# First jab and training target — 2026-11-14

This opt-in native Mac ROM adds a first attack to the movement and jump experiment. A character can face left or right, initiate a grounded jab with key position 3, and hit a stationary training target for two diagnostic damage points when within a local range. The figure and target are original geometric placeholder art. This is a source-informed experiment, **not a playable match**, a complete Super Tilt Bro attack implementation, a version-matched NES comparison, or a physical Mac result.

## Source and adaptation

The Super Tilt Bro input is revision `b132fd25add46f816e04be64c434386743b84b8b`, distributed under its recorded WTFPL v2 terms. `game-mod/characters/sinbad/states.asm` SHA-256 `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` defines the first jab state, countdown and chaining logic. `game-mod/characters/sinbad/sinbad.json` SHA-256 `868d311f795e084b73c5c4f0de70618be894a8ee222a9f81282f5de19c036704` includes first-jab frame durations totaling 24, with an enabled direct-hit frame and damage value 2. We use those as input to a **local 24-count timeline** and a two-point hit; we do not claim equivalent source animation timing, a source-matched hitbox, collision order, knockback or other source mechanics. No upstream artwork is copied. The existing ClasSICK-derived reset is separately attributed in [provenance](provenance.md).

The port assigns a single stationary target to local x=168, permits a hit once at local attack clock 7 when facing the target at a locally selected 16–32 pixel distance, and shows an original active pose at clocks 7–8. The left pose mirrors the right. The target draws after the player when placeholders overlap; this is a temporary compositing policy. The prototype stops horizontal velocity during an attack, rejects airborne attacks and ignores repeated presses while the attack key stays held. It does not implement the source combo chain, real per-frame hitboxes, opponent motion, stun, knockback, aerial attacks, displayed damage, stocks, death, two-player input, or game menus. Damage and event counts are wrapping diagnostic bytes. Target, local ranges, rendering and input policy are independently authored choices, not hardware or source-game facts. The game-derived material is not a ClasSICK implementation input.

## Build and modeled observations

The opt-in 65,536-byte ROM SHA-256 is `cf03b1834ba60db9c7f9b3151a294b005651c27b58c4c5faf63a067bd0854717`, occupied through offset 16,011 inclusive. The existing movement and jump profiles retain their exact previous ROM hashes `3e69619032fc71bed6e1afe3cf09c4e7c0436000c6a56bdd664d373481f56abd` and `70cabce350ee510b93121c15ff3151509926bdafba918bc1adb859c575fad37b`; their respective 13-case and six-case BootHush suites passed after this change. The ROM size is not a full game, 128K RAM, stack or performance budget.

The original `NST4` diagnostic extends to 38 bytes: offsets 32–37 are the attack clock, held attack key, facing (1 right/2 left), target damage, attack count and hit count. The seven bounded scenarios passed using BootHush executable SHA-256 `1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`: out-of-range miss, right-facing hit, wrong-facing miss, rejected airborne attack, held-key single attack, two separate hits and a left-facing hit. In the right hit, the guest reported attack clock 7, x `37600` (8.8), one hit and damage 2 at VBL 28/cycle 3,646,736. In the left hit, it reported clock 7, x `49184`, one hit and damage 2 at VBL 64/cycle 8,335,378. The two-hit case ended with two hits and damage 4.

Each sampled 512x342 framebuffer was checked against separately frozen original geometric rows, including old-position erasure and target drawing. A separate reference checked at least 20 adjacent-VBL intervals without a delivered key per scenario for attack-clock and hit/damage transitions. No checked interval reported an unserviced VBL; keyboard witnesses reported no dropped, rejected or pending events. This is software behavior under this BootHush model, not proof of physical timing or of unsampled inputs.

## Reproduction and media

```powershell
$py = 'C:\ClasSICK\bootstrap-clean-source-verified\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py -B scripts/build_mac_combat.py --output out/NEW-COMBAT.rom
& $py -B scripts/test_mac_combat.py --boothush $bh --keep out/NEW-COMBAT-TEST
& $py -B scripts/capture_combat_evidence.py --boothush $bh --output out/NEW-COMBAT-MEDIA
```

Paths must be new. Full JSON, original PBM frame series and keyboard witnesses are retained under ignored `out/combat-experiment-20261114-f`; regression results are in `out/combat-jump-regression-20261114` and `out/combat-movement-regression-20261114`. An original silent Y4M, eight verified PBM/PNG stills, GIF, MP4 and manifests are in `out/combat-media-20261114`. The video contains 22 modeled samples at 30 fps and is not a physical timing measurement. GIF SHA-256 `89ac7b121f326811d20ea06e46f5674d12988927e8c2e19d5c98a3c09e52b637`, MP4 SHA-256 `e31284a26c29e30cff211ce997b9500a44bdf8d649e3883cf0b43a02b09e8a2a`. PNGs are lossless guest-frame conversions; MP4 is lossy.

## Visible damage follow-up

Later on 2026-11-14, the optional combat ROM gained an original eight-cell indicator above the training target. One 3x6-pixel cell appears per two diagnostic damage points; the display caps at eight cells, while the existing byte counter continues and eventually wraps. It is not a copy of the source game's damage display. The updated ROM is 65,536 bytes, SHA-256 `a42399675fe172343781a49ef5e12981d14958c3f9b49fea2f819131d4dfc490`, occupied through offset 16,715 inclusive. The earlier ROM and evidence above are preserved as a separate checkpoint. The default movement and jump ROM hashes remained unchanged.

All seven previous combat scenarios passed with complete pixel checks including the new indicator. An eighth bounded run performed nine separate right-facing attacks; observations showed damage 2, 4, 6, 8, 10, 12, 14, 16 and 18 with nine hits, while the pixel oracle verified the indicator's visual cap at eight cells. The input schedule, states, frame series and witnesses are retained in ignored `out/combat-meter-20261114-c`; BootHush executable SHA-256 remained `1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`. This is model-dependent, not a physical timing or full combat claim.

The updated original silent capture and eight stills are under `out/combat-visible-meter-20261114`; it uses the same reproduction commands above with a new output directory. Its 22-frame GIF SHA-256 is `109ebf4c7b4c7e2a6e67d1e954e1aedbe18cb66110c5e9dec7c037b18a83dc5a`, and its MP4 SHA-256 is `86f4c4ef563bed173bf632d3944d4dcf6b7d28954d8d7b107a87e3cf8f0b2a4e`. These depict original placeholder art and the prototype diagnostic indicator, not the original game's assets or HUD.

The original-art VBL 28 PBM was separately compared with a 286 EGA bitmap diagnostic in BootHush; all 175,104 canvas and 48,896 margin pixels matched. The PBM SHA-256 was `69b4dcd44fee1e078665183a5a470437607abb63115e238f8f053cbc41122e0b`, and the generated 286 EGA frame SHA-256 was `2db7cf71fbb02c89b63fe98490f3e9b8b18796974c4dd1e677947c263ce568fb`. Full output remains in ignored `C:/Repos/boothush/out/pc286-combat-image-20261114`; method and limits are in `C:/Repos/boothush/docs/mac-pc286-bitmap-20261114.md`. The 286 did not run combat code, and this model result is not physical behavior or a paired-release pass.
