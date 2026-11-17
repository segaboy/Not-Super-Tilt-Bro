<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# One aerial jump per player

2026-11-17. The opt-in native-jab title now lets either player jump again
while airborne, once before landing. A fresh jump press, alone or with one
horizontal direction, preserves height, zeros vertical momentum, and restarts
the existing four-tick preparation and short-hop clock. Landing restores the
aerial jump. Holding jump does not consume it automatically; a third jump and
attack-plus-jump or opposed-direction combinations are refused. Both players
can use the feature during the same run.

This is a source-derived gameplay slice with original placeholder graphics
and local physics. It does not establish a complete match, a source-matched
NES result, or physical Mac behavior. The independent keyboard adapter requires
a fresh jump make. The upstream aerial dispatcher can also react to other
button changes, including attack release with jump held. Full controller
dispatch, wall jumps, footstools, hitstun, original gravity/collision/animation,
and source event ordering remain outside this slice.

## Reviewed source

The source is Super Tilt Bro revision
`b132fd25add46f816e04be64c434386743b84b8b`, with its retained WTFPL v2 notice.
The same independently authored GPL-3.0-or-later port startup, input glue and
placeholder art remain in use.

| Source file | SHA-256 | Used behavior |
| --- | --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` | One aerial jump; neutral and single-direction jump inputs; existing PAL jump constants |
| `game/templates/characters/std_jumping.asm` | `21c0a0cc0d5e0420d7b17c4cdd4022076cf7b85b10fc6d28f48ebf5965595c7e` | Usage check/increment, zero vertical velocity, restart shared jumping state and clock |
| `game/templates/characters/std_aerial_input.asm` | `c26ddb464dc9032f3f18a7bf3c7c2102d1e85a4ff0ee68141c374134be130045` | Aerial input dispatch context and its broader behavior |
| `game/logic/game_states/game/game_logic.asm` | `8ea4d732a54e2f8d476022763698801e3208b3d2638c75f6fea2673dea35f050` | Reset aerial-jump usage on ground |

The local positive-up velocity, `0x0060` gravity step, `-0x0200` fall cap,
five-of-six serviced-VBL pacing and bounds remain the earlier prototype's
choices, as described in [jump evidence](jump-slice-evidence.md). No new native
C call site or component is added. Only the native-jab title emits the feature;
six older profiles were independently rebuilt against `cf3c29b` and are
byte-identical. Their complete hashes are in
`C:/Repos/Not-Super-Tilt-Bro/out/aerial-legacy-review-20261117.json`.

## Executed checks

The pinned BootHush active-profile executable is
`C:/Repos/.task-temp/boothush-floppy-state-20261117-a/a/boothush-active.exe`,
SHA-256 `ec4f037699b1e116ca74775f5b257e5deafd3dcfdfc973342ae6bfaa16832730`.
All executions were bounded, headless and on native Windows, using BootHush
only. No Apple ROM, System disk, private HQ, WSL or other emulator was used.

`scripts/test_native_aerial_jump.py` passed 20 scheduled cases: each player's
held ground jump, ascending and descending aerial entry, aerial short hop,
third-jump refusal, directional jump, rejected attack/opposed-direction input,
and another aerial jump after landing, plus simultaneous play and an identical
repeat. The oracle checks unchanged-input physics intervals, retained entry
altitude, zero preparation velocity, takeoff, short-hop reduction, landing
recharge, independent player state and every captured framebuffer byte.
Input witnesses have no rejected, dropped or pending events. Four altered ROMs
omit the aerial-use latch or retain nonzero preparation momentum for each
player; the same outcome validator rejects all four. Implementation and tests
were authored by Codex and reviewed by a separate agent.

The existing 34-case native-jab title qualification also passed, including
its prior mutation controls and twin native-C component builds. Reports:

- `C:/Repos/Not-Super-Tilt-Bro/out/aerial-jump-20261117-c/report.json`
- `C:/Repos/.task-temp/nstb-aerial-jab-regression-20261117-a/report.json`

Both suites produce ROM SHA-256
`689d89cebe1947267c1fadacd45d34e3bfe3c958535f42267674dd3e2040f55a`.
The image is 65,536 bytes. The emitter ends at offset 38,932, a 204-byte
increase; unchanged movement/jab components end at 57,422 and 57,980.
Bytes `DIAG+107` and `DIAG+108` hold separate aerial-use flags; both initialize
to zero and clear on landing. The existing jump-count diagnostics now count
ground and aerial starts. This is not a complete ROM/RAM/stack budget.

In the player-one ascending case, VBL 43 has height 6,048 and velocity 288
in local 8.8 units. VBL 44 starts aerial preparation at the same height with
zero velocity; VBL 47 sets takeoff velocity 1,152. The full aerial jump reaches
sampled height 12,384; early release reaches 9,414 instead. The player lands
with two starts recorded and the aerial-use flag cleared.

Reproduce with the retained components, whose hashes the test enforces:

```powershell
python -B scripts/test_native_aerial_jump.py --boothush EXE --movement MOVEMENT_BIN --jab JAB_BIN --output NEW_DIRECTORY
python -B scripts/capture_aerial_evidence.py --results RESULT_DIRECTORY --output NEW_MEDIA_DIRECTORY
```

The renderer requires Pillow. It uses the passing report and exact captured
bytes, not a new run. The GIF contains VBL 38-68 from a single simultaneous
two-player run at 100 ms per sample, approximately six times slower than
modeled time; the PNG is the unchanged 512x342 VBL 60 framebuffer.
Both were visually inspected. The media receipt, renderer/input/output hashes,
PNG and GIF are retained in
`C:/Repos/Not-Super-Tilt-Bro/out/aerial-jump-media-20261117-a/`.
GIF SHA-256:
`f602f3ef171e190dc40f8e4214e7875f748f8c2efeda0fd2164c1a4b1dc59ffa`.
PNG SHA-256:
`54958c7031f439872608d9a7f5c2df416b43c3ed053a6f376583ff6e2ce93ff9`.

The useful cross-project result is continued validation of the new BootHush
candidate's scheduled input, state and framebuffer observations. No new
hardware claim is made. Game-derived implementation, tests and assets remain
in Not Super Tilt Bro and are not ClasSICK implementation inputs.
