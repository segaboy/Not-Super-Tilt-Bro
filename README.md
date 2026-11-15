# Not Super Tilt Bro

Not Super Tilt Bro is an experimental port of [Super Tilt Bro](https://github.com/sgadrat/super-tilt-bro) to the original Macintosh 128K. The goal is to boot a playable game directly from a replacement ROM without Apple ROM, System software, or other Apple executable code, and ultimately demonstrate it on original hardware. Research developed along the way should be reusable by [ClasSICK 0.97](https://github.com/segaboy/ClasSICK-0.97) and ClasSICK.

**Status: research and feasibility. An opt-in native Mac ROM now starts with a mouse-driven title and enters a keyboard-driven two-character slice with movement, jumping, prototype jabs and damage indicators; there is no playable game yet.** Input, timing, collision, gravity and placeholder art remain experimental, and the reviewed upstream game has not been built and run from its identified source revision. Fast modeled mouse motion can be missed. See [mouse-title evidence](docs/mouse-title-evidence.md), [two-character evidence](docs/two-character-evidence.md), [jab evidence](docs/jab-training-evidence.md), [jump evidence](docs/jump-slice-evidence.md) and [movement evidence](docs/movement-evidence.md).

A [Windows-compiled 68000 C movement component](docs/windows-native-c-evidence.md)
also runs in an opt-in title ROM: mouse Start leads to keyboard-driven
movement through that component for both players. The rest of the prototype
still uses the emitter; neither build is a complete game.

A separate [source-derived PAL jab-chain slice](docs/jab-chain-evidence.md)
now runs as native 68000 C in a bounded BootHush diagnostic. It is not yet
connected to the title/game ROM and does not establish a playable match.

## Approach

- Use [BootHush](https://github.com/segaboy/boothush) headlessly for source and target testing. Report missing capabilities instead of silently switching emulators. Emulator observations are not proof of physical hardware behavior.
- Establish version-matched NES behavior, then adapt game rules and state transitions to native 68000, starting with a small playable slice. Adapt the original, independently authored ClasSICK startup and appropriate hardware services, preserving their GPL-3.0-or-later terms and notices.
- Replace NES graphics and input with Macintosh-specific 512 x 342 monochrome rendering and input. Investigate keyboard rollover and a practical two-player control scheme. Sound requires additional BootHush support.
- Measure the linked ROM and memory map. The stock ROM budget is 65,536 bytes. The screen occupies 21,888 of 131,072 RAM bytes, leaving 109,184 before vectors, stack, sound, game state and other allocations. Whether a complete modern game fits remains unproven; no extra ROM or RAM hardware is assumed.
- Preserve the no-Apple-code boundary. Do not use or include Apple ROM or System code, disassembly, copied Apple assets, or derivative implementations. Separate documented facts, emulator observations, hypotheses and physical measurements. Any research transferred to ClasSICK must follow its clean-room, source eligibility, provenance and test processes.

## Initial source review

The reviewed upstream revision is [b132fd25add46f816e04be64c434386743b84b8b](https://github.com/sgadrat/super-tilt-bro/tree/b132fd25add46f816e04be64c434386743b84b8b). Super Tilt Bro is a two-player NES platform fighter. Its source combines 6502 assembly, 6502-targeted C, generated character templates and banked data. Its game state includes player position, velocity, hitboxes, damage and stocks. The default manifest names five characters and three tilesets.

The default build declares a 1 MiB Rainbow cartridge, while the no-network UNROM build declares mapper 2/submapper 1 and 512 KiB PRG. These cartridge sizes are not the measured minimum size of a native Mac port. The upstream repository carries a WTFPL v2 license file; individual assets and third-party components still require review. ClasSICK 0.97 code is GPL-3.0-or-later. The narrow running-entry behavior was translated from the reviewed game source; no upstream game art is included.

## Initial BootHush observations — 2026-11-13

BootHush executable SHA-256: dcb00e0c0ee156f6c07bae26a516a6627688df2b571fedb058563f232dd5f082. Local source commit: 6b66c54.

- A historical [v1 cartridge](https://github.com/retrobrews/nes-games/blob/master/super-tilt-bro.nes), SHA-256 ed0369a686a945c1f19c30aef9b6d02e184ff592876622610675c3474e2b3d8c, was rejected unchanged because its iNES header identifies PAL timing. A separate experimental copy changed header byte 9 to zero, SHA-256 bb6a9a64da28152ba138471f2a42ae4020312573779cb3f1b1995ecff4388eef. BootHush ran it with NTSC timing. The title screen appeared after 3 million instructions; scheduled A-button presses led to an options screen after 5 million instructions. All four input events were accepted. A full match, PAL behavior, audio accuracy and current-version gameplay were not established.
- An existing ClasSICK 0.97 ROM candidate, SHA-256 faf37c6f96f8eb2ee6cf7a1e58a8b1b9538055d2fc89493c7419eeea816f6c8c, reached its documented stage 16 condition in the Mac 128K profile at cycle 56,836,682 with its fault word zero. This is a ClasSICK baseline, not a boot of this game.

## Initial BootHush feature requests (historical)

1. Support the exact current upstream no-network mapper 2/submapper 1 512 KiB cartridge, including its actual banking and RAM requirements once the built image is inspected. Mapper 30 and Rainbow are separate targets.
2. Accept and model PAL NES timing and header metadata accurately, rather than ignoring the timing flag. The experiment above is not PAL validation.
3. Add independently scheduled second-controller input to the process and embedding APIs, with latching and repeatability tests.
4. Implement and capture the relevant Macintosh sound path for repeatable audio testing.
5. Develop comparable guest-time input, state and capture workflows across the NES and Mac profiles, with explicit fidelity and timing limits.

The current NES core also has known CPU, graphics and audio approximations. Do not treat a successful bounded run as a complete or accurate playthrough. All hardware claims require separate evidence.

This is an independent fan project and is not affiliated with Apple, Nintendo, or the Super Tilt Bro authors.


### Additional NES arena observation

A longer run of the same modified-header v1 image reached a frame showing an in-game arena with two characters and damage counters after 17,000,000 instructions and 1,749 modeled PPU frames. All 14 scheduled first-controller events were accepted. This demonstrates reaching the arena in the emulator, not a complete match or accurate PAL and two-controller behavior.

## BootHush update and native probe — 2026-11-13

BootHush commit `0e2245d` adds experimental mapper 2/submapper 1, PAL timing, independent CLI input on both NES ports, multiple CPU inspections, and PPU/OAM inspection. These replace the earlier feature requests for basic support, not the need to validate the actual current source build and hardware accuracy. The separately obtained author-provided 2.6 beta 5 UNROM image has SHA-256 `5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa`; its source revision is unknown.

A new Mac replacement ROM probe boots in BootHush, draws original geometric arena art, polls one M0110 key and moves one figure eight pixels. This is a startup, framebuffer and keyboard experiment, **not** a port of Super Tilt Bro's game logic or a playable fighter. It uses no Apple code, game assets or system software. The ClasSICK-derived reset sequence and license are recorded in [provenance](docs/provenance.md).

Run on this workstation using Python 3.9+ and the current BootHush executable (the listed interpreter is the existing local installation):

```powershell
$py = 'C:\Repos\ClasSICK-0.97\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py scripts\build_mac_probe.py --output out\arena-probe-new.rom
& $py scripts\test_mac_probe.py --boothush $bh
& $py scripts\compare_nes_inputs.py --boothush $bh --rom 'C:\Repos\.task-temp\super-tilt-bro-author-unrom.nes' --report out\nes-report-new.json
```

Use a fresh output path each time. Generated ROMs and reports are local build artifacts. Tests use BootHush only and do not alter the input NES image. The Mac test checks neutral and scheduled-key pixels, readiness markers and identical repeated key runs. The NES comparison runs neutral, first-controller, second-controller, both and a repeated combined-input case; instruction-indexed runs may reach slightly different guest cycles. See [the evidence record](docs/boothush-evidence.md) for limitations. Mac sound and synchronized cross-platform scenarios remain open. At the time of this historical probe, a native Windows 68000 compiler was unavailable, so it used a narrow auditable instruction-byte emitter. A Windows compiler has since been exercised in the separate [native-C probe](docs/windows-native-c-evidence.md); the original title ROM uses the emitter, while an opt-in title build also calls native C; neither requires WSL.

## Cycle-aligned comparison and controls probe

BootHush commit `ecc9287` adds NES guest-cycle schedules, observations and
controller-read witnesses. The project's `scripts/compare_nes_cycles.py` uses
them to compare neutral, each controller, and combined input at a common
requested guest cycle. Results and limitations are recorded in
[BootHush evidence](docs/boothush-evidence.md).

A second original Mac replacement-ROM probe demonstrates discrete left/right
movement, press/release handling, and three-position bounds. It remains a
placeholder graphics and input experiment, not Super Tilt Bro game logic.
The test runs entirely headlessly on BootHush:

```powershell
& $py scripts\build_mac_controls.py --output out\controls-new.rom
& $py scripts\test_mac_controls.py --boothush $bh
& $py scripts\compare_nes_cycles.py --boothush $bh --rom 'C:\Repos\.task-temp\super-tilt-bro-author-unrom.nes' --report out\nes-cycle-new.json
```

The scripts require fresh output paths. The NES input is caller-supplied and
is not distributed. No physical hardware or game-equivalence claim is made.

## Source-derived running-entry slice

The separate `sinbad-run-entry` ROM translates the PAL Sinbad running-entry
state and initial horizontal velocity, with direction-change handling. It does
not apply that velocity to position, implement the complete input table, or
render original character art. The discrete three-position display remains a
diagnostic. Details, attribution, RAM layout and limits are in
[the running slice](docs/sinbad-running-slice.md).

The following commands use the `$py` and `$bh` variables above. Both `--keep`
and `--output` must name new directories; the latter retains captures from the
locally supplied beta, so keep that directory private and out of Git.

```powershell
& $py scripts\build_mac_run_transition.py --output out\sinbad-run-entry-new.rom
& $py scripts\test_mac_run_transition.py --boothush $bh --keep out\run-entry-evidence-new
& $py scripts\capture_nes_actions.py --boothush $bh --rom 'C:\Repos\.task-temp\super-tilt-bro-author-unrom.nes' --output out\nes-actions-new
```

The recorded BootHush build, exact cycles, controller and keyboard witnesses,
image comparisons, and remaining limitations appear in
[the evidence record](docs/boothush-evidence.md). NES observations are from
an unidentified beta revision and are not source-to-target validation.
