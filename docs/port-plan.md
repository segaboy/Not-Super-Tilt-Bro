# Port plan and initial source inventory

Research date: 2026-11-13. This is a preliminary source review, not a complete audit or a completed port.

2026-11-18: deterministic title recovery now covers both players in the existing
native-jab and optional air profiles, including six stale action keys, complete
109-byte checkpoints, replay and two mutation controls. All six profile/player
configurations pass (46 bounded BootHush runs), with unchanged ROM bytes. See
[native title recovery](native-title-recovery-evidence.md); this does not qualify
human pointer response or new aerial/combat behavior.

2026-11-17: the native-jab title adds a source-derived aerial jump for each
player, with landing recharge, short-hop handling and simultaneous two-player
qualification. The 20-case aerial suite and existing 34-case combat/title suite
pass on the pinned current BootHush candidate. See [aerial-jump evidence](aerial-jump-evidence.md).
Full physics, collisions, input dispatch and a source-matched NES build remain open.

Later 2026-11-17: a separate opt-in native C component adds source-derived PAL
horizontal aerial influence and friction, momentum-preserving direction
changes and ground movement restoration. Seven earlier profiles stay
byte-identical. The new 14-case gameplay suite, 522-step component probe,
six native-call checks and both existing combat/jump suites pass; see
[aerial-control evidence](aerial-control-evidence.md).

2026-11-14: A second independently controlled figure now moves, jumps and performs a limited jab in the opt-in prototype. Both figures can trade prototype hits or evade while airborne. It is not a complete match; see [two-character evidence](two-character-evidence.md). Following the owner's direction, a further opt-in build adds a mouse-driven title/start and keyboard control during play. Fast modeled motion can be missed; see [mouse-title evidence](mouse-title-evidence.md).

Later 2026-11-14: an opt-in source-informed first-jab experiment adds an original stationary training target, visible active pose and a bounded two-point damage counter. Movement, jump, both attack directions, misses and repeated hits run in BootHush. This is a diagnostic combat slice, not a source-matched collision engine or playable match. [Evidence](jab-training-evidence.md).

Later 2026-11-14: the opt-in movement ROM adds a source-derived four-tick jumpsquat, jump-power magnitude and short-hop timing/magnitude with independently authored vertical integration, landing and placeholder rendering. Full and short jump, running while jumping, airborne retry and a second grounded jump were tested in BootHush. This remains an approximate slice, not a playable match or a source-matched NES comparison. [Evidence](jump-slice-evidence.md).

2026-11-14 update: the VBL-paced movement experiment integrates velocity and now tracks two overlapping modeled direction keys. Its independently chosen last-pressed input policy restores a still-held direction after release; [evidence and limits](overlapping-direction-evidence.md). This remains a source-derived slice with original placeholder art, not a playable match or a physical-keyboard claim. The older transition-only status immediately below describes the earlier checkpoint.

Progress update: the native ROM now contains a tested, source-derived PAL
Sinbad running-entry state/velocity transition. It does not yet integrate
velocity or implement playable movement; see [the slice](sinbad-running-slice.md)
and [the BootHush evidence](boothush-evidence.md). The source-matched NES build
and the complete toolchain and hardware validation described below remain open.

## Source game

The reviewed upstream tree is [sgadrat/super-tilt-bro at b132fd25add46f816e04be64c434386743b84b8b](https://github.com/sgadrat/super-tilt-bro/tree/b132fd25add46f816e04be64c434386743b84b8b). It is a NES platform fighter: two characters attempt to knock one another off-screen. The upstream README maps directions to movement, jump and shield, and the two action buttons to attacks and special moves; direction modifies the attacks.

The game mixes 6502 assembly and C compiled for the 6502, with generated assembly, templates, tools, banks and NES-specific hardware interfaces. The reviewed [state constants](https://github.com/sgadrat/super-tilt-bro/blob/b132fd25add46f816e04be64c434386743b84b8b/game/constants.asm) define title, selection, in-game and other screens, local/online/arcade modes, and two players. The [player layout](https://github.com/sgadrat/super-tilt-bro/blob/b132fd25add46f816e04be64c434386743b84b8b/game/mem_labels.asm) includes positions, velocities, state, hitboxes, damage and stocks. Character behavior uses state-machine templates; the [default content manifest](https://github.com/sgadrat/super-tilt-bro/blob/b132fd25add46f816e04be64c434386743b84b8b/game-mod/mod.json) lists five characters and three tilesets. These observations are not a full content, dependencies, or asset-rights inventory.

The upstream [build script](https://github.com/sgadrat/super-tilt-bro/blob/b132fd25add46f816e04be64c434386743b84b8b/build.sh) produces different cartridge variants; the [assembly configuration](https://github.com/sgadrat/super-tilt-bro/blob/b132fd25add46f816e04be64c434386743b84b8b/tilt.asm) declares the default Rainbow mapper 682 with 1024 KiB PRG and a no-network UNROM mapper 2/submapper 1 variant with 512 KiB PRG. Sizes include game-specific layout and do not measure the minimum possible native Mac implementation. The built artifacts, exact RAM needs, complete dependency tree and individual asset licenses remain to be measured.

## Candidate technical approach

1. **Establish behavioral baselines.** Run the exact upstream version and a version-matched build in BootHush once mapper, PAL and input support permit. Capture deterministic per-frame inputs, player state, timing, images and audio where supported. The old v1.0 experiment is useful for orientation only.
2. **Boot an independent native game ROM.** Adapt only reviewed, original GPL-3.0-or-later ClasSICK 0.97 startup and necessary hardware services, preserving notices. Its [reset entry](https://github.com/segaboy/ClasSICK-0.97/blob/5d99706/arch/m68k/mac-reset.S) establishes vectors, removes the reset overlay, initializes data/BSS and calls native code; its [linker script](https://github.com/segaboy/ClasSICK-0.97/blob/5d99706/arch/m68k/mac-rom.ld) constrains its demonstrator to 64 KiB ROM. These are a starting point, not a verified game bootloader or hardware specification.
3. **Translate a narrow playable slice to 68000.** Preserve and test the game rules, movement, hitboxes and state transitions against NES observations. Translate 6502-specific logic or adapt portable pieces after dependency and license review; 6502 machine code cannot simply execute as native 68000. Start with one stage and a small character set, then expand subject to measured budgets. Local two-player input is a goal; the original keyboard's real rollover and practical two-player mappings require investigation. Online networking is a later scope decision.
4. **Replace NES-specific presentation.** Implement a 512×342, 1-bit renderer, converting/reworking NES tiles, sprites and palettes under reviewed asset rights. Prototype dirty regions and sprite composition with measured frame-time and RAM costs. Use appropriate VBL synchronization. Adapt sound to Mac hardware once BootHush can exercise it; first milestones may explicitly be silent.
5. **Prove the budget and compatibility.** The standard screen consumes 21,888 bytes (512×342 bits). Of 131,072 RAM bytes, 109,184 remain before stack, vectors, sound buffers, game state and any other allocations. ROM budget is 65,536 bytes total for startup, code, data and assets. These are arithmetic starting points, not a working memory map. Enforce linker limits and report actual headroom. Validate deterministic input/state/pixels, then qualify actual hardware separately.

A bare replacement ROM is the target, with no dependency on an Apple System disk. Whether the complete modern content fits in the stock ROM and 128K RAM is **unproven**. Do not assume bank-switched or enlarged ROM hardware: any such alternative needs explicit discussion and must not be presented as the original-machine result.

## Research feedback loop

For each Mac finding, record the exact build and hashes, emulator version, inputs, limits and observation, and distinguish hardware documentation, emulator behavior and hypothesis. Before transferring anything to ClasSICK, assess source eligibility and provenance under its existing policies; prepare a reviewed behavioral specification and independent tests. Physical timing, keyboard rollover, sound, and full 128K operation are open. No ClasSICK repository changes have been made by this project.
