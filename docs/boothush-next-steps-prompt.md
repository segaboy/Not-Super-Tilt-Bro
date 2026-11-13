# Prompt for the BootHush development chat

We are porting **Super Tilt Bro** from NES to a standalone replacement ROM for the **original Macintosh 128K**, with no Apple ROM or System code. The port project lives at:

- `C:\Repos\Not-Super-Tilt-Bro`
- BootHush: `C:\Repos\boothush`
- ClasSICK 0.97: `C:\Repos\ClasSICK-0.97`

Please improve BootHush to make the next stages of this port observable, repeatable, and testable. Read BootHush's current `AGENTS.md`, `docs/project-direction.md`, `README.md`, `docs/nes.md`, `docs/nes-api.md`, and the port project's `docs/boothush-evidence.md` before changing anything. Inspect the current working trees and preserve other work. Do not assume that the commit and capability status below is still current.

## What is already working

As last observed, BootHush source commit `0e2245d` and executable SHA-256 `e4312839fa999e8a6014a7dfea5dc8edb28fe70000ba51853d99055209640dd5` provided:

- Experimental PAL NES timing and mapper 2/submapper 1 support.
- Scheduled independent inputs for both NES controllers in the CLI and library.
- Multiple CPU-memory inspections plus side-effect-free PPU and OAM inspection.
- NES audio and video capture, with known approximations and alignment limits.
- A Mac 128K profile with a 68000, 128 KiB RAM, 64 KiB ROM, reset overlay, framebuffer, and M0110 keyboard model.

The separately obtained author-provided Super Tilt Bro 2.6 beta 5 UNROM ROM is at `C:\Repos\.task-temp\super-tilt-bro-author-unrom.nes`, SHA-256 `5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa`. Its exact source revision is **unknown**. Do not distribute it or claim it is a build of the current upstream source. The port's `scripts/compare_nes_inputs.py` runs neutral, player-one-only, player-two-only, both and repeated combined-input cases. The final frames differed, and the combined run repeated exactly, but inputs are scheduled by instruction count and the runs have different guest-cycle totals. Those differences do not establish which fighter responded or prove gameplay accuracy.

The port also has a generated 64 KiB original Mac ROM probe, built by `scripts/build_mac_probe.py` and tested by `scripts/test_mac_probe.py`. It boots through a ClasSICK-derived reset sequence, draws original geometric art, and moves one figure eight pixels after a scheduled keyboard press. The test checks guest RAM and framebuffer pixels. It is a **startup/display/input probe**, not a port of Super Tilt Bro's logic, and it has not been tested on physical hardware. Its test stops before the scheduled key release; release delivery is not established.

Do not redo working mapper, PAL, or controller support merely because older notes list those as gaps. Verify current capabilities and address only limitations demonstrated by the exact source build or focused tests.

## Priority 1: Frame- and guest-time-based scenarios

The most immediate need is to compare a game action against a neutral run at the same meaningful point in guest time. Instruction-count scheduling is a poor basis for this: different branches execute different numbers of cycles, and game state can differ because of timing rather than the intended input.

Implement a small, well-defined, headless mechanism for NES and Mac scenarios that supports:

1. Scheduling inputs for each NES controller and the Mac keyboard against a specified guest cycle and/or completed video frame or VBL event. Preserve the existing instruction-based NES interface.
2. Stopping and taking multiple observations at defined cycles, frames/VBLs, or a guest readiness condition where the profile can support it.
3. Starting relative input schedules only after an explicit guest condition or other documented readiness event, so that differing boot/menu times do not shift the action.
4. Clear ordering rules when input, readiness, frame capture, and a stop condition coincide. Report requested and actual application/observation points, pending or dropped events, and any boundary rounding.
5. Reproducible frame-indexed or VBL-indexed screenshots and state samples with emulator build, ROM hash, timing region/profile, guest cycles, frame number, and scenario/input identity.

Do not claim cross-platform equivalence merely because two images or timestamps match. Explicitly document how NES PAL frame timing and Mac VBL timing differ; use a declared mapping or tolerance instead of assuming a one-to-one frame rate.

Acceptance: use independent synthetic fixtures for both machine profiles and at least one optional run against the supplied game ROM. Show identical repeated scenarios; verify neutral and each-controller cases are observed at equivalent declared points; test condition-not-reached, invalid schedules, simultaneous events, and bounds. Keep the game-ROM integration optional and hash-pinned. Do not redistribute the ROM.

## Priority 2: Observable keyboard and controller behavior

Extend diagnostics only where the current models lack the needed evidence:

- For the NES, expose enough bounded, side-effect-free information to show when each controller is strobed/read and which bits the guest actually receives. Preserve both existing ports and distinguish a scheduled event being accepted from the guest consuming it.
- For the Mac, make it possible to correlate scheduled M0110 press/release transitions with the keyboard queue, command/reply delivery, VIA shift-register activity, and any overflow or dropped input.
- Support multi-key presses, holds and releases within the existing modeled protocol. Do not present simultaneous-key behavior or rollover as physical M0110 fact without independent evidence.
- Provide bounded trace filters and report truncation/drop counts, guest cycle, and relevant instruction context. Avoid slowing normal runs when tracing is disabled.

Acceptance: synthetic guest fixtures verify independent NES ports, ordered key press/release delivery, overlapping keys, queue limits and explicit drops; demonstrate how to test the port's key release rather than stopping before it. State any unverified physical keyboard behavior.

## Priority 3: Mac sound and capture

Implement the relevant original Macintosh 128K sound path needed to let an independently written ROM produce music and effects, based on eligible hardware specifications and independently written implementation. Scope the initial slice to what can be substantiated and tested; document exact device/timing gaps rather than claiming full audio fidelity.

Provide bounded headless capture with a documented sample format and guest-time relationship, explicit underrun/overrun and truncation reporting, and enough metadata to align captured audio with screen/VBL events. Do not require an Apple ROM, System disk, or visible window.

Acceptance: independently generated test ROMs exercise silence and known tones or sample patterns, verify enable/disable and timing, and produce deterministic repeated captures within the model's declared limits. Explain whether and how a human has listened; waveform generation alone is not an audio-fidelity test.

## Priority 4: Capture and bounded execution witnesses

- Provide a useful bounded NES instruction/memory/device witness for investigating the selected game state, including mapper bank and interrupt context where available; filtered watches must be opt-in and report overflow.
- Improve Mac-side visibility into VBL, framebuffer writes and faults for performance/animation work without requiring mouse-specific tracing.
- Make per-frame screenshots and optional audio/video capture reproducible and identify guest-time offsets and any sample/capture loss.
- Ensure ranges are side-effect-free when advertised as inspection. Keep input ROMs read-only, protect existing output paths, bound run time and output size, and preserve the user's desktop.

Add focused synthetic tests and document exact observation and timing limitations. Do not log or publish copyrighted game captures or ROM images as fixtures without a rights review.

## Priority 5: A narrow source-to-target comparison workflow

Build a small reusable vertical slice, not a speculative universal framework:

- Use explicit source and target profiles, ROM hashes, event schedules and readiness conditions.
- Allow an adapter to map a logical action to NES-controller input and Mac-keyboard input, and separately map named observations supplied by each project.
- Compare only explicitly defined outcomes with declared units, frame/time mapping and tolerances. Keep raw data and transformations inspectable.
- Report unsupported capabilities, mismatched profile/ROM/build, timeout, guest fault, dropped input, missing readiness and comparison failure distinctly.

A good first demonstration can use independently generated NES and Mac fixtures with a simple movement action. The real game currently lacks a version-matched source/build and named state mapping, and the Mac port has no game logic, so do not fabricate a Super Tilt Bro equivalence result.

## Compatibility and project constraints

- Use BootHush for emulator runs. Keep automated work headless and bounded, and never use another emulator as a silent fallback.
- Preserve the no-Apple-code boundary. Do not use Apple ROM/System executable code, Apple disassemblies, copied Apple assets, or uncertain-origin implementations as project inputs. For ClasSICK-bound research, follow that repository's clean-room and provenance requirements.
- Report existing NES CPU, PPU, APU, PAL, mapper, and Macintosh device approximations and distinguish emulator observations from physical-hardware validation.
- The current upstream Super Tilt Bro source revision has not been built or run here. Validate that exact build when available, but do not claim the beta ROM is revision-matched.
- A usable 68000 cross-toolchain is a **port build-environment issue**, not automatically a BootHush feature gap: WSL previously returned access denied and the installed Windows LLVM lacked the 68000 target. Report if it blocks your own independent fixtures; do not attempt to bypass an environment restriction.
- Keep ROMs and other generated/private artifacts out of Git. Use independently generated fixtures by default and document third-party provenance and licenses.
- Update BootHush's README, profile docs, API docs, and tests whenever behavior changes. Preserve existing CLI/API compatibility where practical and version any necessary changes.
- Work incrementally in priority order. Run appropriate tests and the actual optional integration when its pinned ROM is available. Report what was implemented, commands and results, exact remaining blockers, and what the port project can use next.
- Inspect Git status and history before committing or pushing. Preserve all pre-existing changes and commits; follow the BootHush project's existing instructions and the user's authorization.
