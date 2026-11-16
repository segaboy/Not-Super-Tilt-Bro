<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Source-derived Sinbad PAL jab-chain slice

2026-11-15. A native 68000 C state/input slice is now connected to an opt-in
mouse-title and keyboard-play prototype for both players, as well as the
original isolated diagnostic. It implements part of Sinbad's PAL jab chain,
not a complete match. The displayed figures and collisions are local
placeholders; source-matched animation, sound, idle re-entry and the complete
input combinations remain open. No physical inputs were tested.

## Source and scope

The port may adapt the separately identified open-source Super Tilt Bro
revision `b132fd25add46f816e04be64c434386743b84b8b`. The upstream root carries
the WTFPL v2 notice preserved in `third_party/super-tilt-bro-LICENSE.txt`.
The input was reviewed in the port repository's scope only; no game-derived
implementation is transferred to ClasSICK.

| Upstream file | SHA-256 |
| --- | --- |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` |
| `game-mod/characters/sinbad/sinbad.json` | `868d311f795e084b73c5c4f0de70618be894a8ee222a9f81282f5de19c036704` |
| `game/logic/game_states/game/game_logic.asm` | `8ea4d732a54e2f8d476022763698801e3208b3d2638c75f6fea2673dea35f050` |
| `nine/prg_rom/utils.asm` | `cfb968309acc35e21286d14cb55c77deac67df4b5d3a93f1f3386ab0ffadf5e5` |

For the PAL slice, the first animation metadata totals 24 ticks and the
second totals 26. The source input handlers permit chaining after the first
ten ticks of each of those states, and defer an early nonzero input while
acknowledging a release. Its third state starts with the second state's
26-tick duration even though the third animation metadata totals 29. The
component uses normalized port-local input symbols and models the source's
state-update-before-input ordering and changed-input/dirty behavior within
those jab states. The final transition to idle is represented as DONE; the
subsequent idle input handler is intentionally out of scope. No artwork or
upstream binary is included.

## BootHush observation

Windows-native GCC produced two identical 65,536-byte replacement-ROM test
images, SHA-256
`543006b0808046fbebb5dc206b6514b5e9cedb06e8b748f7a486f83580de040a`;
the emitted content ends at offset 924. BootHush executable SHA-256 was
`ef7b5d9cf89fd0cc0eb1a816b5e489ffc34931349370a178c0579267dcc2ff2a`.
Six scripted input timelines exercised held input, early held re-press, an
early tap released before the cut, a press at the first cut, another button
combination, and third-state input handling. Twenty-five selected boundary
states and 480 checks of a second interleaved state instance passed. A mutant
that delayed the first cut by one tick produced the expected different state
at that boundary. Exact source/tool hashes, build and BootHush commands,
diagnostic bytes and mutant identity are in
`C:/Repos/.task-temp/nstb-jab-chain-20261115-b/report.json`.

The earlier `nstb-jab-chain-20261115-a` run failed because the independent
expectation incorrectly assumed a release on a timeline that kept the button
held. The input schedule was checked, that expected previous-input value was
corrected, and the later run passed; the earlier output remains preserved.
These are emulator and software observations, not a source-matched NES
execution, real keyboard behavior, physical timing, complete attack or game.

```powershell
$py = 'C:/Users/segab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$tools = 'C:/Repos/.task-temp/m68k-windows-native-20261114-a/x-tools-v3-win/m68k-unknown-elf/bin'
$bh = 'C:/Repos/.task-temp/boothush-transient-active-twins-20261115-b/a/boothush-active.exe'
& $py -B scripts/test_sinbad_jab_chain.py --tool-bin $tools --boothush $bh --output C:/Repos/.task-temp/NEW-JAB-CHAIN
```

## Mouse-title and keyboard-play integration

The experiment links the same C component alongside the native movement
component and enters play through a scheduled mouse click. The keyboard
adapter maps each player's local attack button to the slice's normalized jab
input; directional/button combinations and later idle processing are not
fully reproduced. The native state controls the local attack clock and
placeholder hit checks, not source-matched NES sprites or hitboxes. The
default prototype remains byte-identical and retains its single local jab.

ROM SHA-256 `27c1f330ff2eb428e06f5297a28fe46fa1b004cac2ed178777d7ddeec04ac561`
ran on BootHush SHA-256
`ef7b5d9cf89fd0cc0eb1a816b5e489ffc34931349370a178c0579267dcc2ff2a`.
The linked jab component's twin builds matched, SHA-256
`30e0e1a84928b05fcf387ce00a8dd10881ebc8c6692a104a925f4a1f68153d6a`.
Five scheduled scenarios cover each player chaining through all three states,
both players together, an early tap and a held key. All scheduled keyboard
transitions were delivered; 160 captures were available and pixel-checked.
The separate frame-to-frame calculation checked 140 unchanged-input
intervals. It rejected a one-tick first-cut threshold mutation. This checks
the integration under the BootHush model; the calculation was authored with
the implementation and is not an independent external review.

The native-C title and eight-case combat regressions also passed with the
same BootHush executable and preserved ROM SHA-256
`6b302b449e5eab230753cc6604f886628566683d454e5d1b50590f8c061b2db6`.
Exact commands, input and tool hashes, delivery witnesses, frame data,
component layout and limitations are in
`C:/Repos/.task-temp/nstb-title-native-jab-20261115-b/report.json`;
the regression reports are in `C:/Repos/.task-temp/nstb-title-regression-20261115-a`
and `C:/Repos/.task-temp/nstb-dual-c-regression-20261115-a`.

```powershell
& $py -B scripts/test_native_jab_title.py --tool-bin $tools --boothush $bh --component C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/a/movement.bin --output C:/Repos/.task-temp/NEW-TITLE-JAB
```

The same five title/jab scenarios and threshold mutation also passed on the
later BootHush executable SHA-256
`e84e214750c69907f6c5052397243661392810d1f1b14e357d6387a29008885d`.
Its Windows twin build and PC keyboard queue observation work are recorded in
`C:/Repos/boothush/docs/pc286-input-accounting-20261114.md`; the port's exact
commands and hashes are in
`C:/Repos/.task-temp/nstb-jab-pc-queue-regression-20261115-a/report.json`.
This is a Mac-profile regression of the emulator build, not a physical test.

## Stage-specific prototype damage

The reviewed `sinbad.json` identified above specifies damage values 2, 1 and
5 on the enabled direct-hit frames of jab animations one, two and three.
The opt-in title ROM now uses those values when its existing local collision
rule reports a hit in each corresponding jab state. The prototype still
uses its own timing, reach, target geometry, visual pose and maximum damage
of 254; this is not a source-matched implementation of those hitboxes,
knockback, hitstun, animations or the complete game.

Windows-built 68000 component twins and generated ROM SHA-256
`d4ba1b15dad0aedef42f9435dcc517720455e0374b3531a6766bc60edc6ef87b`
ran on BootHush SHA-256
`e84e214750c69907f6c5052397243661392810d1f1b14e357d6387a29008885d`.
For both players, a scheduled mouse Start and keyboard sequence produced
three local hits with damage progression 2, 3, 8. Initial damage 250 and 254
exercised the local saturation cap for both players. Four mutations changing
the second- or third-stage amount produced the expected different totals.
The original five chain, early-tap and held-key cases and the threshold
mutation also passed, with full captured-frame checks. The prior single-jab
ROM remained byte-identical and its eight-case combat regression passed.

Input witnesses, frame captures, tool and source hashes, commands and test
limits are in `C:/Repos/.task-temp/nstb-jab-stage-damage-20261115-d/report.json`;
the legacy regression is `C:/Repos/.task-temp/nstb-legacy-damage-regression-20261115-a/report.json`.
The earlier `-a` run completed its initial scenarios but the first hit case
was rejected before that guest run because it requested more than BootHush's
32 capture points; the output remains preserved. Reproduce using
the title-jab command above with the newer BootHush executable and a fresh
output path. These are software and model observations, not physical input or
hardware validation.

The title/jab suite also passed on BootHush executable SHA-256
`3aec7ffc0062d950f8f62088baf5c17ed95c70a9f1737776157a5a38568aa7f8`,
which adds a PC disk test facility used by ClasSICK. The port's Mac-profile
commands and results are in
`C:/Repos/.task-temp/nstb-ordinal-regression-20261115-a/report.json`; the
facility and limits are documented in
`C:/Repos/boothush/docs/pc286-hard-disk-fault-20261114.md`.

## Direction and jump combinations

The title/game adapter now maps a held direction or jump button to the jab
slice's `OTHER` input, and starts a neutral jab only when neither is held.
During an existing jab, releasing the other input while attack remains held
can make the input neutral-jab again, subject to the source-derived cut
window. This is a local normalization of the source's changed-input
distinction. At the time of this test, pressing attack with a direction held
did not produce a side tilt. The later bounded implementation and its limits
are recorded in [side-tilt evidence](side-tilt-evidence.md). Other button
combinations and idle re-entry remain incomplete.

Both players were tested for direction-plus-attack and jump-plus-attack
through the mouse-started prototype, plus neutral-jab refusal when starting
with a direction held. Four separate mutations removed the direction or jump
normalization for one player; the frame-to-frame state calculation rejected
each. The existing chained hits, damage saturation, threshold mutation and
full-frame checks passed as well. The previous single-jab ROM remained
byte-identical and passed its eight combat scenarios. ROM SHA-256 is
`93e66fd77854844d450b835504fa1689ca55387b355e1ac3842dbf94092b14fe`;
BootHush executable SHA-256 is
`3aec7ffc0062d950f8f62088baf5c17ed95c70a9f1737776157a5a38568aa7f8`.
Exact input schedules, source/tool hashes, commands, witnesses and limitations
are in `C:/Repos/.task-temp/nstb-jab-direction-input-20261115-b/report.json`;
the older ROM regression is in
`C:/Repos/.task-temp/nstb-jab-direction-legacy-20261115-a/report.json`.
These are modeled input tests, not physical key behavior or a playable match.
