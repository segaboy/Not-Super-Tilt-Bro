# Jump out of side-attack recovery

2026-11-16. The native-jab title lets either player cut side-tilt recovery
with jump alone or one horizontal direction plus jump. It waits until the
remaining recovery clock is strictly below 14, clears the side-attack state
and attack clock, and starts the existing four-tick jump squat. A held early
jump is retried each playable tick. A released early tap does not jump;
attack-plus-jump and both horizontal directions are outside the implemented
idle-table subset and do not cut recovery. The players retain separate state.

The reviewed source remains Super Tilt Bro revision
`b132fd25add46f816e04be64c434386743b84b8b`, under the retained root WTFPL v2
notice. `game-mod/characters/sinbad/states.asm`, SHA-256
`cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55`,
defines the recovery threshold as PAL animation duration minus four and uses
a strict less-than test before dispatching jump-bearing input through idle.
The 18-tick recovery duration and its metadata source are already identified
in [side-tilt evidence](side-tilt-evidence.md). The local adapter checks held
input before decrementing this tick's clock; source-matched NES event ordering
has not been established. Up-tilt, up-special, full idle dispatch, original
physics/collision/art, and a complete playable match remain unfinished.

Only the opt-in native-jab title emits this new path. Other prototype build
branches retain their existing behavior. No new RAM field is allocated.
The emitter ends at ROM offset 38,728; the existing movement and jab components
end at 57,422 and 57,980. The complete image remains 65,536 bytes. Final ROM:
`0210d56550976e60ea3f38e3af9655a4faea34313a5ffe81aaeb7923daf26790`.

## Executed checks

`scripts/test_native_jab_title.py` builds matching component twins and tests
34 scheduled mouse/keyboard scenarios with complete original pixel checks.
Twelve new cases cover both players' early hold, early released tap, late
press, held attack, opposed directions, and neutral jump. Per-frame checks
verify the 14/13 boundary, attack-to-jump state handoff, one jump only,
takeoff, and unchanged other-player jump state. Four altered-threshold ROMs
(13 and 15 for each player) are rejected. Existing four side-timing controls,
four input-normalization controls, four damage controls and the jab-threshold
control also pass. Test calculations use the specified state rules separately
from the emitted instruction sequence; Codex authored and self-reviewed both.

Reports, exact commands, source/tool hashes, ROMs, witness data and frame
sequences are retained outside Git:

- `C:/Repos/.task-temp/nstb-recovery-jump-20261116-a/report.json`: original
  stopped-register BootHush build.
- `C:/Repos/.task-temp/nstb-recovery-jump-20261116-b/report.json`: new
  BootHush executable SHA-256
  `8860227d991a6c6d252815019c2458a1b0af3cae49306ce43e7fdaff5dd04e3b`.

The second run produces the same ROM. Reproduce with the existing pinned
Windows m68k tools and movement component:

```powershell
python -B scripts/test_native_jab_title.py --tool-bin M68K_BIN --boothush EXE --component MOVEMENT_BIN --output NEW_EXTERNAL_DIRECTORY
```

Four non-jab profiles (jump, combat, two-player title, and two-player native-C
movement title) are byte-identical to the preceding committed builder.
Their hashes and comparisons are in
`C:/Repos/.task-temp/nstb-recovery-legacy-20261116-a.json`.

## Native calls after recovery and cross-project use

BootHush's new `--until-pc-after` lower bound allows observations after the
interaction rather than stopping at the first boot-time visit. The updated
`scripts/test_native_call_preservation.py` retains both reviewed ROM identities
and exact expected call counts. It passes the ten original movement/jab sites,
three bad-callee controls, and two movement calls with both players airborne
after recovery. D2-D7, A2-A6, A7, SR control bits and frame bytes are preserved.
Each return run is anchored to the observed call cycle, and unobserved controls
match. Both later movement calls cost 144 modeled cycles; these are sampled
paths, not worst-case or physical timings.

The complete report is
`C:/Repos/.task-temp/nstb-recovery-call-preservation-20261116-a/report.json`.
Run the existing preservation command with the new title ROM and emulator.
The transfer to ClasSICK is the later-boundary test method and BootHush API;
no game-derived implementation is admitted into ClasSICK. All runs are bounded
and headless, with no WSL or other emulator. Physical input, actual hardware,
full source-game equivalence and release qualification remain unverified.
