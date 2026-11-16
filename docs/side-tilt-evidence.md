<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Grounded side-tilt timing experiment

The opt-in mouse-title prototype now starts a side attack for either player
when exactly one horizontal direction and attack are pressed on the ground.
The source-derived PAL timing has 12 windup, 12 active, and 18 recovery ticks.
Movement is locked locally during the entire attack and resumes afterward.
Local placeholder collision applies two damage at one chosen active tick; the
figures, hit geometry, attack timing within the active phase, and damage rule
are not source-matched. Facing can change during an attack. The model does not
implement the original move's acceleration, animation, air or ledge behavior,
recovery jump cut, knockback, or the complete game. This is not a playable
match or a physical-hardware result.

## Source and eligibility

The timing interpretation is informed by Super Tilt Bro revision
`b132fd25add46f816e04be64c434386743b84b8b` under the root WTFPL v2 notice
in `third_party/super-tilt-bro-LICENSE.txt`. The reviewed files were
`game-mod/characters/sinbad/states.asm` SHA-256
`cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55`,
`game-mod/characters/sinbad/sinbad.json` SHA-256
`868d311f795e084b73c5c4f0de70618be894a8ee222a9f81282f5de19c036704`,
and `game/templates/characters/tpl_grounded_attack_followup.asm` SHA-256
`b81118e4236ba935d1d7fa32be30e0161d842089cd28edbc9774400b2b62d3a1`.
Windup metadata sums to 12 PAL ticks; the hit state explicitly uses 12 even
though its animation totals eight; recovery metadata sums to 18. This is
game-informed port work and is not an eligible ClasSICK implementation input
merely because BootHush runs it. Hardware-specific findings require separate
source and provenance review before transfer.

## Reproduction and observations

Windows-native tools built the opt-in ROM with SHA-256
`b56adf5472ce86300356824374a8760c25bb83772d0518b20df335880e2aff6d`.
The suite uses scheduled BootHush mouse and keyboard input, checks frame pixels
and frame-to-frame state, tests both players' three phases and recovery,
both local hit directions, a distant miss, and mutation controls for the
first two phase lengths. Existing jab and input-combination cases also run.
The previous no-native-jab ROM remained byte-identical and passed its eight
combat cases in `C:/Repos/.task-temp/nstb-side-legacy-20261115-a/report.json`.
Exact commands, tool and ROM identities, scheduled inputs, witnesses, frames,
observed state and control results are retained in
`C:/Repos/.task-temp/nstb-side-tilt-20261115-e/report.json`. BootHush
observations do not establish behavior on an original Macintosh or a human
input test.
