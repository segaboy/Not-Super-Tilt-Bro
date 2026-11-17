<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Native aerial horizontal control

2026-11-17. A further opt-in native-jab title now gives both players
source-derived horizontal control in the air. Direction changes accelerate
through the existing momentum instead of replacing it with the grounded
running-entry speed. Released direction keys leave a gentle drift. Aerial
jump preparation retains horizontal momentum; influence resumes at takeoff.
Landing restores the earlier grounded movement component.

The feature is enabled by passing a separately built `native_air` component
to the ROM builder. All seven pre-existing profiles, including the native-jab
aerial-jump title, remain byte-identical to commit `3c75106`. The independent
comparison receipt is
`C:/Repos/Not-Super-Tilt-Bro/out/air-control-legacy-review-20261117.json`.

## Source behavior and adapter boundaries

The reviewed source remains Super Tilt Bro revision
`b132fd25add46f816e04be64c434386743b84b8b`, under the retained WTFPL v2 notice.
The new native C component adapts its PAL horizontal rule:

| Input and existing velocity | Target velocity | Maximum change per tick |
| --- | ---: | ---: |
| Right, below +256 | +256 | 128 |
| Right, at/above +256 | +256 | 7 |
| Left, above -256 | -256 | 128 |
| Left, at/below -256 | -256 | 7 |
| Neutral | 0 | 7 |

Velocity moves toward the target without passing it. Values use the port's
8.8 units. The native component also integrates a scratch position for its
existing caller interface; source position integration is separate, and the
Mac compositor integrates the live position after erasing the prior figure.
The component does not access vertical state.

| Reviewed source | SHA-256 | Contribution |
| --- | --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` | Sinbad air-speed, influence and friction constants |
| `game/templates/characters/std_aerial_input.asm` | `c26ddb464dc9032f3f18a7bf3c7c2102d1e85a4ff0ee68141c374134be130045` | Target and influence/friction selection |
| `game/templates/characters/std_friction_routines.asm` | `bc6fd5308b70439b93f11210bd778b0315d6f3925635395d6f2457ca48ee8107` | Neutral target and unchanged vertical target |
| `game/templates/characters/std_constant_tables.asm` | `62d81546fd8d8d29d273c92130a86a8e26433d95eefbb41a35f3449791188e80` | Character table mapping |
| `game/logic/utils.asm` | `7bc4f603752f6fa8deeef2bc9a897e4d61c83c2a85bfcc064bbf16c850b7961b` | `merge_to_player_velocity` target clamping |
| `game/macros.asm` | `b42c950d41cafa6df076c3884ee25408f2f6dc0eb0f69bad3b7908bd90ce4072` | Unscaled PAL table entries |

The shared jump-preparation behavior is attributed in
[aerial-jump evidence](aerial-jump-evidence.md). Source preparation defers
horizontal influence. This new path does so for aerial preparation; the older
ground-squat movement is deliberately preserved. The source gives left input
priority when both directions are held, while the local keyboard adapter
retains its last-pressed policy. Ground acceleration is still the earlier
approximation: after landing with a velocity not aligned to its 64-unit steps,
it may settle slightly above 512 in magnitude. The rightward landing case
settles at 515; the separate oracle checks that exact existing behavior.

Local gravity, five-of-six VBL pacing, floor/bounds, collision and original
placeholder art remain unchanged. The two figures can pass through one
another. A complete match, full upstream input/state dispatch, source-matched
NES timing and physical Mac behavior are not established.

## Qualification and identity

Only BootHush was used, headlessly on native Windows, with no Apple ROM or
System disk, private HQ, WSL or other emulator. Executable:
`C:/Repos/.task-temp/boothush-floppy-state-20261117-a/a/boothush-active.exe`,
SHA-256 `ec4f037699b1e116ca74775f5b257e5deafd3dcfdfc973342ae6bfaa16832730`.
Native compiler/linker/tool hashes and exact commands are in the reports.

`scripts/test_native_air_control.py` passes:

- Twin native component builds with no unresolved symbols.
- An isolated BootHush component probe with 522 steps across 29 signed
  velocities, three directions and six successive calls. These include target
  boundaries, zero crossings, signed-16 extremes and position wrap. This is a
  numerical diagnostic, not gameplay footage.
- Fourteen live title/gameplay scenarios covering both players' overspeed
  decay, neutral drift, reversal, overlapping directions, aerial preparation,
  landing and simultaneous play with identical repeated states/pixels.
  Full frames, keyboard deliveries, vertical behavior and separate horizontal
  expectations are checked. Airborne direction-event intervals specifically
  reject momentum snapping.
- All six new native call sites preserve D2-D7, A2-A6, A7, SR control bits and
  frame bytes. Register observation on/off produces identical results.
  Selected calls cost 190-244 modeled cycles; these are not worst-case or
  physical timings.
- Two altered native components (influence and friction), a ROM routed to
  ground movement while airborne, and a register-clobbering callee are rejected
  by their respective independent expectations.

The existing 20-case aerial-jump suite and 34-case jab/title suite also pass
with `--air` selecting this component, including their existing mutation
controls. Implementation, source interpretation and tests were reviewed by a
separate agent. Complete reports:

- `C:/Repos/Not-Super-Tilt-Bro/out/air-control-20261117-b/report.json`
- `C:/Repos/Not-Super-Tilt-Bro/out/air-control-jump-regression-20261117-a/report.json`
- `C:/Repos/.task-temp/nstb-air-control-jab-regression-20261117-a/report.json`

After that qualification, the focused air-control suite also passed on the
newer executable
`C:/Repos/.task-temp/boothush-floppy-checksum-20261117-a/a/boothush-active.exe`,
SHA-256 `7adb8a74cef009b7c532df24458c3a5db6b77725356fdb31e5ac4966d7ed971a`
(BootHush commit `5d613614dd4f17d605de75ecc3f38c9129079488`). Its report is
`C:/Repos/Not-Super-Tilt-Bro/out/air-control-new-boothush-20261117-a/report.json`.
The 14 gameplay cases, 522-step probe, mutation controls and six native-call
checks pass again. Every gameplay state, frame hash and native-call result
matches the preceding executable. The 20/34-case broader regressions above
and media below retain their original `ec4f0376...` executable identity; they
were not rerun for this emulator-only update.

All three suites produce ROM SHA-256
`f28739e256e1426b0849e3ed3c1c6dda01a6c6d39de1b57e9d2e2aaf86a3b00d`.
The image remains 65,536 bytes. The emitter ends at 39,452; the unchanged
movement and jab components end at 57,422 and 57,980. The new 120-byte air
component occupies `0xe400..0xe477` and has SHA-256
`d7bfcfc9be27610ae74b428589941e462da74f747fa660ad4573964b49b9ad4e`.
No RAM field is added. These are layout measurements, not a full runtime or
stack budget.

Reproduce with the same retained native movement and jab components:

```powershell
python -B scripts/test_native_air_control.py --boothush EXE --tool-bin M68K_BIN --movement MOVEMENT_BIN --jab JAB_BIN --output NEW_DIRECTORY
python -B scripts/test_native_aerial_jump.py --boothush EXE --movement MOVEMENT_BIN --jab JAB_BIN --air AIR_BIN --output NEW_DIRECTORY
python -B scripts/test_native_jab_title.py --boothush EXE --tool-bin M68K_BIN --component MOVEMENT_BIN --air AIR_BIN --output NEW_EXTERNAL_DIRECTORY
python -B scripts/capture_air_control_evidence.py --results RESULT_DIRECTORY --output NEW_MEDIA_DIRECTORY
```

## Original gameplay media and cross-project use

The passing report's simultaneous reversal run supplies VBL 34-65. The GIF
doubles each captured pixel and displays each sample for 100 ms, approximately
six times slower than modeled time. Its annotations show the corresponding
horizontal velocities. The PNG is the unchanged 512x342 VBL 50 framebuffer.
Both were visually inspected. Renderer/input/output hashes and the media are
in `C:/Repos/Not-Super-Tilt-Bro/out/air-control-media-20261117-a/`.

- GIF SHA-256: `d70ec6df8bad6ee890568a14ac5af9d1d822fcc80d75246f6b89b5f4403f0b5d`
- PNG SHA-256: `f946f33d96165cc4bb118e48bc33181f2e6e41c5ad576ab5ccada0a572b4aae8`

This is actual execution of the local original-art gameplay prototype, not
the isolated numerical probe and not the complete source game. The reusable
finding is that the current BootHush candidate passes another native-component
register/stack/observer check during live keyboard-controlled play. Game-derived
code, tests, constants and captures stay in this project; no such implementation
material was copied into ClasSICK.
