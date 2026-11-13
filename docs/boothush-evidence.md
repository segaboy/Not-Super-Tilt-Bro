# BootHush evidence and feature requests

Date: 2026-11-13. BootHush executable SHA-256: `dcb00e0c0ee156f6c07bae26a516a6627688df2b571fedb058563f232dd5f082`. Local source commit: `6b66c54` (checkout was six commits ahead of its remote). The results below are bounded emulator observations, not hardware evidence.

## NES source investigation

A separately obtained historical [retrobrews cartridge](https://github.com/retrobrews/nes-games/blob/master/super-tilt-bro.nes) has SHA-256 `ed0369a686a945c1f19c30aef9b6d02e184ff592876622610675c3474e2b3d8c`, 40,976 bytes, iNES mapper 0 with 32 KiB PRG and 8 KiB CHR. The distribution labels it v1; its title screen reports version 1.0. Its exact source revision and rights for redistribution are not established. It is not checked into this project.

BootHush rejected this unchanged file with `unsupported or invalid iNES/NES 2.0 NROM cartridge`. Its header byte 9 is 1 (PAL), and the present loader requires zero for iNES bytes 8–15. For exploratory execution only, a separate copy had byte 9 changed to zero; all other bytes were preserved. Modified SHA-256: `bb6a9a64da28152ba138471f2a42ae4020312573779cb3f1b1995ecff4388eef`. BootHush then modeled NTSC timing, not PAL: this is **not** a PAL-compatible run.

- No input, 3,000,000 instructions: `step_limit`, 308 PPU frames, 179 APU writes and a recognizable version 1.0 title screen. Audio was captured but not listened to or validated.
- A-button events at instruction steps 1,000,000 / 1,030,000 and 1,800,000 / 1,830,000 (press/release), 5,000,000 instructions: `step_limit`, 514 frames; all four events accepted. The final captured frame showed the options menu. A match, second controller, game accuracy and the current release were not demonstrated.

Representative invocation, using fresh output paths and the modified experimental copy:

```powershell
& $boothush --machine nes --rom $experimentalRom --steps 5000000 --timeout-ms 20000 `
  --controller-event 1000000:1 --controller-event 1030000:0 `
  --controller-event 1800000:1 --controller-event 1830000:0 `
  --frame $newFrame
```

## Macintosh startup baseline

An existing ClasSICK 0.97 64 KiB original ROM candidate, SHA-256 `faf37c6f96f8eb2ee6cf7a1e58a8b1b9538055d2fc89493c7419eeea816f6c8c`, was run under BootHush's `mac128k` profile. With `--cycles 85000000 --timeout-ms 30000 --until 0xcac:4:16 --inspect 0xca8:28`, it returned `condition_met` at cycle 56,836,682, PC 4,196,648 and 436 reported VBLs. The diagnostic record began `43533039 00000010` (CS09, stage 16) and its fault word was zero. This proves that the identified existing candidate reached its documented ready condition in this emulator configuration; it is not a Not Super Tilt Bro game ROM or a physical boot.

## Earlier requested BootHush capabilities (historical)

1. **Current cartridge support:** load and execute the exact upstream non-network mapper 2/submapper 1 512 KiB image, including its actual banking, RAM, header and timing needs after inspecting the built artifact. Mapper 30 and Rainbow are additional distinct targets, not interchangeable aliases. Add fixture-based tests and clear unsupported errors.
2. **PAL NES timing and headers:** accept and accurately model relevant PAL cartridges, including CPU/PPU/APU timing and region reporting. Do not just ignore or rewrite the timing flag. Separate multi-region handling. The old source run above deliberately bypassed this limitation.
3. **Second NES controller:** independent initial and scheduled input for player two through the process and embedding APIs, with latching and repeatability tests. Both ports are needed for meaningful two-player comparisons.
4. **Mac sound:** model the relevant original Macintosh sound path and capture it headlessly with bounded, reproducible tests so the port's audio can be observed. Define supported timing and fidelity; no sound accuracy claim today.
5. **Cross-target comparison:** useful future capabilities include frame-indexed scripted input, repeatable capture aligned to guest time, bounded guest-state observations and comparison artifacts across NES and Mac. Specify semantics and tolerances before claiming equivalence. Existing NES graphics, audio and CPU timing have known approximations and need validation appropriate to the game.

This file is the project-side notification and issue backlog. These are requests, not claims that BootHush has implemented them. Inspect BootHush's current documentation before opening duplicate issues or depending on new behavior.

## Updated BootHush and project probe — 2026-11-13

BootHush source commit `0e2245d`, executable SHA-256 `e4312839fa999e8a6014a7dfea5dc8edb28fe70000ba51853d99055209640dd5`, adds mapper 2/submapper 1 support, PAL modeling, independently scheduled player-two input, up to eight CPU inspections and PPU/OAM inspection. Mapper support and PAL timing are experimental and not physical-hardware verified. The exact current upstream checkout has not been built; the author-provided 2.6 beta 5 image used here is not revision-matched.

The new original Mac ROM probe, SHA-256 `325376bbbe09c962369f459f1cffd3ab9dfadfc5700fa8a9858e3d7ce823307f`, is exactly 65,536 bytes; the builder reports 3,928 bytes of emitted code and 4,188 bytes through its last instruction, including the reserved vectors and initial offset. This is not a linker map or a full RAM budget. The test boots it in BootHush using an original ClasSICK-derived reset sequence, displays original geometric figures, and polls the M0110 model. With no key, it reaches the ready marker and remains at stage 1 through 1,000,016 guest cycles. With a scheduled position-0 press at cycle 600,000, it moves the first figure eight pixels right and reaches stage 2 at cycle 630,766. Two keyed runs return identical JSON and full framebuffer. The stop occurs before the scheduled release, so release delivery is not established. This is not a playable game or a physical Macintosh test.

The new NES comparison uses the unchanged 2.6 beta 5 image (SHA-256 `5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa`) in PAL mode. At 13 million instructions, neutral, player-one-only, player-two-only and combined runs all completed, and the repeated combined run had identical JSON and framebuffer. Each input run's final frame differed from neutral. The player-one-only run differed in 369 CPU RAM bytes and 56 OAM bytes; player-two-only differed in 351 and 44 respectively. These numbers are observations, not named player states: event times are instruction-based, guest cycles differ, and the binary revision is unverified. The results do not establish which fighter reacted or gameplay accuracy. Generated ROMs, frames, and reports stay out of source control.

Remaining BootHush needs: Mac sound; controlled guest-time/frame-indexed input and observation for comparisons; a way to investigate each controller's guest-observed effect and semantic state; and accuracy validation of the specific current source build and devices it uses. Existing PAL/APU/PPU behavior remains approximate. The Linux 68000 toolchain was not runnable here: WSL reported access denied and the installed Windows LLVM build has no 68000 target. The probe therefore uses a narrowly scoped documented byte emitter pending a usable real cross toolchain. No Apple code or external emulator was used.

## Cycle-aligned NES and Mac controls probe — 2026-11-13

BootHush source commit `ecc9287d75a2b420e3c421ad4841dd9f1e85ad89` adds NES
guest-cycle scheduling, cycle-aligned memory observations, readiness-relative
scheduling, cycle/frame stops, and an opt-in controller-read witness. The
executable SHA-256 for these observations is
`2a38e612da7428f1e7e94b882aa8e981884b97db315318dc1ea50cb4331ac3be`.

### NES observation

`scripts/compare_nes_cycles.py` uses the unchanged author-provided beta ROM
(SHA-256 `5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa`)
and BootHush PAL mode. It first records the cycles of the already documented
menu navigation from a 13-million-instruction neutral run, then replays that
navigation by guest cycle. Five runs request stop cycle 40,103,489: neutral,
player 1 right, player 2 left, both, and a repeat of both. Input hold begins
at cycle 30,817,027; the controller witness covers through 30,917,027.

| Case | Actual stop | P1 reads / set bits | P2 reads / set bits | Frame differs from neutral | Changed CPU bytes | Changed OAM bytes |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Neutral | 40,103,489 | 24 / 0 | 24 / 0 | No | 0 | 0 |
| Player 1 | 40,103,489 | 24 / 3 | 24 / 0 | Yes | 369 | 56 |
| Player 2 | 40,103,490 | 24 / 0 | 24 / 3 | Yes | 351 | 44 |
| Both | 40,103,491 | 24 / 3 | 24 / 3 | Yes | 443 | 96 |

Both combined runs matched exactly including JSON, frame and witness summary.
All scheduled events applied, the selected observation completed, and the
witness reported no dropped events. Each input event is applied at an
instruction boundary; stop-cycle differences above are reported rounding, not
identical machine states. A returned set serial bit establishes a guest read
in the modeled window, but these results do not identify which fighter moved.
The ROM's source revision is unverified; no upstream RAM labels are attributed
to it. The comparison does not establish physical timing or gameplay fidelity.

### Mac controls observation

`scripts/build_mac_controls.py` generates an original 65,536-byte ROM with
ClasSICK-derived reset/vector handling and original placeholder graphics.
The tested image SHA-256 is
`31b2666be66ac7a02d576998cb9b46aec3a91245d16679877d593748fd581fc6`.
Its code is 6,680 bytes, with the last code byte at ROM offset 6,939. These
are emitted-image measurements, not a complete RAM or performance budget.

The probe polls modeled M0110 positions 0 and 1; a press moves one figure by
one eight-pixel step right or left between three positions, and releases are
counted separately. It records an `NST2` signature, readiness, position,
last recognized reply, press count and release count at guest RAM `0xb00`.
It is a discrete input/display experiment, not Super Tilt Bro movement,
continuous held-key movement, a physical-keyboard test, or a playable game.

`scripts/test_mac_controls.py` passed eight BootHush runs: neutral, right
press/release, left press/release, repeated presses at each position limit,
and exact replay. It checks the guest diagnostic bytes and the actual PBM
framebuffer, including the platform and other figure. This establishes the
previously missing emulated release observation for the new probe; it does
not establish the old probe's unobserved release or physical rollover.

### Historical blockers and next steps (before BootHush cf3c177)

- Build a **version-matched** upstream NES ROM and verify exact symbols/assets;
  the author-supplied beta is useful for observation but has unknown source.
- Recover a supported native 68000 cross-toolchain; the probe currently emits
  a limited set of machine encodings and is not an appropriate long-term
  way to implement the game's state machine.
- Measure a source-game movement, jump and attack in guest time, then implement
  one identified, testable behavior in a native game slice. Keep source and
  target actions and timing explicitly mapped; PAL frames and Mac VBL are not
  interchangeable.
- Mac sound, multi-frame images in one NES run, and guest-observed Mac keyboard
  tracing remain open in the inspected BootHush checkout. NES PAL/PPU/APU and
  device timing remain approximate.
- At that time the local folder had no Git metadata; see the later update for
  the repository status and new evidence.

## Source slice and indexed captures - 2026-11-13

BootHush source commit `cf3c1777c8bb7704fc11bf89557dbab684019179` was clean.
The preexisting executable had SHA-256
`fa0917057dec6dbd6a4b378a0290e67cb75c423281c959674967162562bc2b78`;
a build dry run still reported work. It was rebuilt from that checkout, after
which Ninja reported no work and the tested executable SHA-256 was
`7b4c32e24d63432b2103f38c9c1844480a64b1b2bdda4342896e24a19d7c98c7`.
The hash change reflects a local rebuild, not a claim about byte-reproducible
builds. The BootHush `boothush` CTest aggregate passed with the pinned beta
and earlier Mac controls ROM supplied. The earlier controls probe's eight
checks also passed.

### Mac run-entry test

`scripts/test_mac_run_transition.py` builds and tests the 65,536-byte ROM
SHA-256 `3c0232abce9c096aef41065bfa9da31f92ca8832b36aaa9afc6d1dca1560edc3`.
The six modeled cases are neutral, right/left press and release, exact replay,
hold/release, direct right-to-left transition, and repeated same-direction
press. The test captures four live framebuffers and RAM `0x0b00:17` at VBLs
5, 8, 11, and 14, checking the ready marker, input state, images, emulator
hashes, and both witnesses. This is fixed-time capture, not a readiness-gated
run. The primary sequence schedules `(cycle, modeled key, down)` as
`(600000,0,1)`, `(900000,0,0)`, `(1200000,1,1)`, `(1500000,1,0)`; the
keyboard witness reports guest delivery of replies `01 81 03 83` in that
order with no rejected, dropped, or pending transitions.

| Requested modeled VBL | Actual modeled cycle | Diagnostic position | State | Direction | Velocity | Entry count |
| --- | ---: | ---: | --- | --- | --- | ---: |
| 5 | 651210 | 2 | running | right | `0100` | 1 |
| 8 | 1041928 | 2 | idle | right | `0100` | 1 |
| 11 | 1432654 | 1 | running | left | `ff00` | 2 |
| 14 | 1823360 | 1 | idle | left | `ff00` | 2 |

The selected display witness records framebuffer writes and no bus faults in
its configured window. Release image pairs match, the two press images differ,
and the repeated sequence matches its complete recorded result, frames and
witnesses. The other checks exercise held state, direct reversal, repeated
same-direction entry and neutral state. The retained local output is
`out/run-entry-evidence-cf3c177/`; files include original PBM series, manifests,
and keyboard/display traces. The builder, scenario and scope are documented in
[the slice record](sinbad-running-slice.md). Mac images are live framebuffer
copies, not hardware-latched frames. Keyboard timing and rollover are modeled,
not established physical M0110 behavior.

### NES beta action observations

`scripts/capture_nes_actions.py` uses the separately supplied unmodified beta
SHA-256 `5d045246f12d424c2c67ecda883c66d8d346f7b5396ed819ddb326f44dcb5aaa`.
It derives the navigation schedule with a 13-million-instruction seed run,
then replays those events in modeled cycles. This is a fixed-cycle scenario,
not a readiness-gated state identification. Neutral, right (`128`), up (`16`),
A (`1`), and a repeated right run use player one. Each action begins at cycle
30,817,027 and releases at 31,817,027; the stop is requested at 32,417,027.
The controller witness for each case recorded 288 player-one reads in the
window: zero set bits for neutral and 30 for each active case. Input is
observed through modeled controller reads, not inferred from its scheduling.

| Requested cycle | Actual cycle in right run | Last completed PPU frame | Right pixels differing from neutral | Up | A |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 30717027 | 30717028 | 923 | 0 | 0 | 0 |
| 30817027 | 30817027 | 926 | 0 | 0 | 0 |
| 30917027 | 30917030 | 929 | 127 | 93 | 147 |
| 31117027 | 31117027 | 935 | 213 | 226 | 151 |
| 31517027 | 31517027 | 947 | 252 | 252 | 136 |
| 31917027 | 31917030 | 959 | 258 | 184 | 26 |
| 32317027 | 32317028 | 972 | 258 | 26 | 26 |

Captures occur at instruction boundaries, with up to three modeled cycles of
rounding in this run. At the common input/capture boundary the image capture
precedes application of input. Each image is the last completed PPU frame;
the captured CPU RAM, PPU and OAM bytes are sampled at the capture boundary
and may represent a different instant. The exact right scenario replay
matched, including returned result, frame bytes and witness summary. Raw local
series, JSON manifests with offsets and guest state, controller witnesses and
the derived pixel counts are retained in `out/nes-actions-cf3c177/`.
These differences do not identify a character or action, establish gameplay
fidelity, or link this unknown beta to the reviewed source. PAL PPU frames and
Mac VBLs are separate modeled clocks: no one-to-one comparison is claimed.

### Current blockers and status

- A version-matched source ROM is still unavailable: the local source build
  requires its supported 6502 GCC, XA fork and Huffmunch tools, which are not
  installed in the usable local environment. WSL returned `Wsl/E_ACCESSDENIED`
  and the available MSYS shell failed with `NtCreateDirectoryObject` access
  denied. No environment restriction was bypassed. Resolve the supported build
  environment to establish source symbols and an executable baseline.
- A usable native 68000 assembler/compiler and linker are needed beyond the
  limited byte emitter. The available cross-toolchain binaries are Linux-only,
  and WSL was inaccessible. The emitted probe is not a sustainable full-game
  toolchain.
- BootHush can now capture series and observe Mac keyboard/display activity.
  A filtered NES instruction/memory witness accepting project-supplied symbols
  would help connect a **version-matched** build's execution to game state; it
  cannot identify symbols in the unknown beta. A reusable comparison workflow
  needs explicit source/target event and time mappings and tolerances; neither
  machine's frame counter is a shared clock. Mac sound and synchronized audio
  capture remain needed for audio. Each is future work, not a prerequisite for
  the source-derived entry transition already tested here.
- Hardware behavior, input rollover, sound, full game compatibility, and a
  complete ROM/RAM budget remain unverified. Further source semantics and
  tests can proceed without those capabilities.
