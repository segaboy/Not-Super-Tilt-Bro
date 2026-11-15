<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Source-derived Sinbad PAL jab-chain slice

2026-11-15. The existing mouse-title prototype provides a single local jab;
it does not implement the source game's jab chain. The new native 68000 C
component is an isolated state/input slice toward that goal. It is not yet
connected to the title/game ROM, renders no character, takes no physical or
modeled keyboard events, and does not implement collisions, animation, sound,
idle re-entry, or a playable match.

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
