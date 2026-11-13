# Not Super Tilt Bro

Not Super Tilt Bro is an experimental port of [Super Tilt Bro](https://github.com/sgadrat/super-tilt-bro) to the original Macintosh 128K. The goal is to boot a playable game directly from a replacement ROM without Apple ROM, System software, or other Apple executable code, and ultimately demonstrate it on original hardware. Research developed along the way should be reusable by [ClasSICK 0.97](https://github.com/segaboy/ClasSICK-0.97) and ClasSICK.

**Status: research and feasibility. There is no playable Mac game or game ROM yet.** An existing ClasSICK ROM has reached its ready state in BootHush. An older NES game build reached its title and options screens in a modified-header experiment; the current upstream game has not been run.

## Approach

- Use [BootHush](https://github.com/segaboy/boothush) headlessly for source and target testing. Report missing capabilities instead of silently switching emulators. Emulator observations are not proof of physical hardware behavior.
- Establish version-matched NES behavior, then adapt game rules and state transitions to native 68000, starting with a small playable slice. Adapt the original, independently authored ClasSICK startup and appropriate hardware services, preserving their GPL-3.0-or-later terms and notices.
- Replace NES graphics and input with Macintosh-specific 512 x 342 monochrome rendering and input. Investigate keyboard rollover and a practical two-player control scheme. Sound requires additional BootHush support.
- Measure the linked ROM and memory map. The stock ROM budget is 65,536 bytes. The screen occupies 21,888 of 131,072 RAM bytes, leaving 109,184 before vectors, stack, sound, game state and other allocations. Whether a complete modern game fits remains unproven; no extra ROM or RAM hardware is assumed.
- Preserve the no-Apple-code boundary. Do not use or include Apple ROM or System code, disassembly, copied Apple assets, or derivative implementations. Separate documented facts, emulator observations, hypotheses and physical measurements. Any research transferred to ClasSICK must follow its clean-room, source eligibility, provenance and test processes.

## Initial source review

The reviewed upstream revision is [b132fd25add46f816e04be64c434386743b84b8b](https://github.com/sgadrat/super-tilt-bro/tree/b132fd25add46f816e04be64c434386743b84b8b). Super Tilt Bro is a two-player NES platform fighter. Its source combines 6502 assembly, 6502-targeted C, generated character templates and banked data. Its game state includes player position, velocity, hitboxes, damage and stocks. The default manifest names five characters and three tilesets.

The default build declares a 1 MiB Rainbow cartridge, while the no-network UNROM build declares mapper 2/submapper 1 and 512 KiB PRG. These cartridge sizes are not the measured minimum size of a native Mac port. The upstream repository carries a WTFPL v2 license file; individual assets and third-party components still require review. ClasSICK 0.97 code is GPL-3.0-or-later. No upstream code or game assets have yet been copied here.

## Initial BootHush observations — 2026-11-13

BootHush executable SHA-256: dcb00e0c0ee156f6c07bae26a516a6627688df2b571fedb058563f232dd5f082. Local source commit: 6b66c54.

- A historical [v1 cartridge](https://github.com/retrobrews/nes-games/blob/master/super-tilt-bro.nes), SHA-256 ed0369a686a945c1f19c30aef9b6d02e184ff592876622610675c3474e2b3d8c, was rejected unchanged because its iNES header identifies PAL timing. A separate experimental copy changed header byte 9 to zero, SHA-256 bb6a9a64da28152ba138471f2a42ae4020312573779cb3f1b1995ecff4388eef. BootHush ran it with NTSC timing. The title screen appeared after 3 million instructions; scheduled A-button presses led to an options screen after 5 million instructions. All four input events were accepted. A full match, PAL behavior, audio accuracy and current-version gameplay were not established.
- An existing ClasSICK 0.97 ROM candidate, SHA-256 faf37c6f96f8eb2ee6cf7a1e58a8b1b9538055d2fc89493c7419eeea816f6c8c, reached its documented stage 16 condition in the Mac 128K profile at cycle 56,836,682 with its fault word zero. This is a ClasSICK baseline, not a boot of this game.

## BootHush feature requests

1. Support the exact current upstream no-network mapper 2/submapper 1 512 KiB cartridge, including its actual banking and RAM requirements once the built image is inspected. Mapper 30 and Rainbow are separate targets.
2. Accept and model PAL NES timing and header metadata accurately, rather than ignoring the timing flag. The experiment above is not PAL validation.
3. Add independently scheduled second-controller input to the process and embedding APIs, with latching and repeatability tests.
4. Implement and capture the relevant Macintosh sound path for repeatable audio testing.
5. Develop comparable guest-time input, state and capture workflows across the NES and Mac profiles, with explicit fidelity and timing limits.

The current NES core also has known CPU, graphics and audio approximations. Do not treat a successful bounded run as a complete or accurate playthrough. All hardware claims require separate evidence.

This is an independent fan project and is not affiliated with Apple, Nintendo, or the Super Tilt Bro authors.


### Additional NES arena observation

A longer run of the same modified-header v1 image reached a frame showing an in-game arena with two characters and damage counters after 17,000,000 instructions and 1,749 modeled PPU frames. All 14 scheduled first-controller events were accepted. This demonstrates reaching the arena in the emulator, not a complete match or accurate PAL and two-controller behavior.
