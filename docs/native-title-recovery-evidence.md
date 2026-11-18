<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Native title recovery and stale input

2026-11-18. The deterministic failed-keyboard-drain qualification now covers
the existing native-jab and optional native-air title ROMs, with a fresh
direction input from either player. The original emitter title still passes
with its original single-key fixture, and now also with player two selected.
No production builder, guest component, graphics or ROM bytes changed.

This closes the native-profile gap identified in the earlier
[emitter recovery receipt](mouse-title-evidence.md#failed-drain-recovery-replay---2026-11-17).
It is a bounded BootHush input/recovery observation, not human mouse response,
physical hardware, a complete match, or paired-release qualification.

## Scenario and checks

`scripts/test_title_recovery.py` keeps its existing command line and defaults.
`--movement` and `--jab` together select the retained native components;
`--air` additionally selects retained aerial control. Component hashes are
checked before building. `--player 1` (default) or `--player 2` selects which
player receives the fresh rightward press after recovery.

Each native-profile fixture queues six makes after the injected timeout:
right, jump and attack for both players, at cycles 3,200,000 through 3,250,000.
The held failed click cannot retry; release at 3,800,000 rearms it, and a fresh
press at 4,000,000 must drain all six keys before gameplay. Releases are
scheduled at 6,000,000 through 6,050,000; the selected player's only fresh
make is at 7,000,000, followed by release at 8,000,000.

In each recording, repeat and replay scenario, all 14 native-profile keyboard
transitions are accepted and delivered in order, with no rejected, dropped or
pending scheduled input. All 13 requested captures
are processed with complete images and exact 109-byte diagnostic blocks.
Final inspection also requires exactly 109 bytes. The original emitter runs
retain 86 bytes and four keyboard transitions.

| Requested native-fixture cycle | Required observation |
| ---: | --- |
| 1,500,000 | Title ready after the modeled 16-pixel move into Start |
| 2,400,000; 2,800,000; 3,500,000 | Failed drain; timeout count one; held click consumed |
| 3,900,000 | Released click rearms while the title remains failed |
| 5,100,000; 5,500,000; 6,500,000 | Gameplay ready; both players stationary with clear direction, jump, attack, jab, side-attack and aerial-use state |
| 7,500,000 | Only the selected player moves, with fresh direction held |
| 8,500,000; 9,500,000 | Fresh direction released; other player remains at its initial position |

The six-key drain takes longer than the earlier one-key fixture. The native
first-ready checkpoint is therefore 5,100,000 instead of the emitter's
4,800,000; the earlier 2,100,000 and 4,200,000 transition captures remain.
The first development run caught this fixture timing difference and is
retained as `out/native-recovery-air-p1-20261118-a/`. It did not expose a
production defect or justify a ROM change.

For the native-air P1 recording, the fault begins at cycle 2,000,894. The six
queued makes are delivered from 4,107,104 through 4,336,784. Their subsequent
releases are delivered from 6,036,984 through 6,688,176, before the fresh make
at 7,078,890. The input adapter polls during gameplay, so release delivery is
not instantaneous. No physical keyboard latency is inferred.

Each profile/player run includes recording, independent repeat, mouse replay,
an observer-free endpoint, no-fresh-click and no-fresh-key controls, and an
intentionally defective held-click ROM. Native profiles add a short-drain
mutant that mistakes the first queued make for the empty-queue reply.

- Recording, independent repeat and replay match every capture cycle, complete
  diagnostic snapshot, captured framebuffer byte, final framebuffer and
  keyboard witness byte.
- The observer-free endpoint matches status, cycles, PC, VBL, modeled mouse
  totals, injected fault, complete diagnostic memory and final pixels.
- Separate pixel expectations check stable title/gameplay frames; transitional
  frames are compared across executions without an atomic-redraw claim.
- No fresh click leaves the title failed. No fresh key leaves both players
  stationary, with native action state and velocities clear.
- The held-click mutant is rejected by failed-title checkpoints. The short-drain
  mutant exposes nonzero jump/attack state at 5,100,000, 5,500,000 and 6,500,000
  and is rejected in all four native-profile runs. This explicit check prevents
  a direction-velocity difference alone from claiming stale-action sensitivity.
- Input ROMs, supplied components and the emulator are checked unchanged after
  execution. All mutation copies and captures remain in ignored output paths.

## Qualification and identities

All six configurations passed: 46 bounded emulator runs and 520 checkpoint
captures. Each run requests 10,000,000 modeled cycles, with a 20-second emulator
timeout and 25-second process timeout. A separate agent reviewed the extension;
its exact-memory-size and stale-action sensitivity suggestions were included
before the final matrix below. `git diff --check` passes.

| Profile | Player | Runs | Final P1/P2 positions (local 8.8 units) | Report under `out/` |
| --- | ---: | ---: | --- | --- |
| Native jab + air | 1 | 8 | 36576 / 43008 | `native-recovery-air-p1-20261118-c/report.json` |
| Native jab + air | 2 | 8 | 32768 / 46816 | `native-recovery-air-p2-20261118-a/report.json` |
| Native jab | 1 | 8 | 36576 / 43008 | `native-recovery-jab-p1-20261118-a/report.json` |
| Native jab | 2 | 8 | 32768 / 46816 | `native-recovery-jab-p2-20261118-a/report.json` |
| Emitter | 1 | 7 | 37088 / 43008 | `native-recovery-emitter-p1-20261118-a/report.json` |
| Emitter | 2 | 7 | 32768 / 44800 | `native-recovery-emitter-p2-20261118-a/report.json` |

Source base: port commit `67b58989bf3ca78206456bcaadd27405ce622940` plus this
test/documentation change. The final test script SHA-256 is
`ebfd26c00186d82edbd5fe9d600421e819ee12f5dff55214c8c67a1327cf5d47`.
Every report contains the hashes of the local Python sources, exact component
paths/hashes, all invocation arguments, emulator results and artifact hashes.

BootHush executable:
`C:/Repos/.task-temp/boothush-floppy-checksum-20261117-a/a/boothush-active.exe`,
SHA-256 `7adb8a74cef009b7c532df24458c3a5db6b77725356fdb31e5ac4966d7ed971a`.
Its previously recorded source identity is
`5d613614dd4f17d605de75ecc3f38c9129079488`; it was reused, not rebuilt here.
Python 3.14.5 executable SHA-256:
`23e0c7f169e3fc760fdedc799cc2673d8d320b6355c97ac2bdce55a28e52dff1`.

| Unchanged 65,536-byte ROM | SHA-256 | Emitter end |
| --- | --- | ---: |
| Emitter title | `c693dcfebf1c9c4b1048abc50503f3462985a926dedc57fe6c5d1da25bfb7d72` | 36502 |
| Native jab | `689d89cebe1947267c1fadacd45d34e3bfe3c958535f42267674dd3e2040f55a` | 38932 |
| Native jab + air | `f28739e256e1426b0849e3ed3c1c6dda01a6c6d39de1b57e9d2e2aaf86a3b00d` | 39452 |

The retained movement, jab and air component hashes are respectively
`a65c5fa382bee316b916cd6c6af52c4a2591496aa762c346e784e7a8bca7d25c`,
`30e0e1a84928b05fcf387ce00a8dd10881ebc8c6692a104a925f4a1f68153d6a`, and
`d7bfcfc9be27610ae74b428589941e462da74f747fa660ad4573964b49b9ad4e`.
These exact components were reused, not recompiled. Their source derivation,
compiler identities and build commands remain in the
[movement](windows-native-c-evidence.md), [jab](jab-chain-evidence.md),
[recovery-jump](recovery-jump-evidence.md), and
[air-control](aerial-control-evidence.md) receipts.

## Reproduction

Run from `C:/Repos/Not-Super-Tilt-Bro`, choosing a new output path each time:

```powershell
$py = 'C:/Repos/ClasSICK-0.97/.tools/llvm-mingw/llvm-mingw-20260908-ucrt-x86_64/python/bin/python.exe'
$bh = 'C:/Repos/.task-temp/boothush-floppy-checksum-20261117-a/a/boothush-active.exe'
$movement = 'C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/a/movement.bin'
$jab = 'C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/a/jab.bin'
$air = 'C:/Repos/Not-Super-Tilt-Bro/out/air-control-20261117-b/a/air.bin'

& $py -B scripts/test_title_recovery.py --boothush $bh --output out/NEW-EMITTER-P1
& $py -B scripts/test_title_recovery.py --boothush $bh --player 2 --output out/NEW-EMITTER-P2
& $py -B scripts/test_title_recovery.py --boothush $bh --movement $movement --jab $jab --output out/NEW-JAB-P1
& $py -B scripts/test_title_recovery.py --boothush $bh --movement $movement --jab $jab --player 2 --output out/NEW-JAB-P2
& $py -B scripts/test_title_recovery.py --boothush $bh --movement $movement --jab $jab --air $air --output out/NEW-AIR-P1
& $py -B scripts/test_title_recovery.py --boothush $bh --movement $movement --jab $jab --air $air --player 2 --output out/NEW-AIR-P2
```

Only BootHush was used, headlessly on native Windows. No Apple ROM/System
disk, private HQ/held research, WSL, other emulator or physical input was used.
This recovery scenario deliberately keeps the aerial component inactive and
does not add aerial/combat behavior qualification; those separate suites were
not rerun for this test-only extension. The useful shared result is the
checkpoint/replay method and exact native-profile recovery result. Game-derived
components, constants, tests and captures remain in this port; no implementation
material was transferred into ClasSICK. Human pointer response remains open.
