<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Windows-native 68000 C movement probe

2026-11-14. Question: can this port compile and execute a small, source-informed
movement calculation as native 68000 C on Windows, with no Apple ROM or System
code? This supports replacing some hand-emitted instructions with maintainable C.
It is a separate diagnostic, not a playable game or the existing title ROM.

`guest/sinbad_native_probe.c` uses the previously documented Sinbad running and
friction constants and local position integration from [movement evidence](movement-evidence.md).
The source game revision, file hashes and WTFPL notice remain in that record and
[provenance](provenance.md); this game-informed work is not an implementation
input to ClasSICK. The startup/vector relocation uses the same previously
attributed GPL-3.0-or-later ClasSICK-derived sequence as `build_mac_probe.py`.
The test harness, deterministic input sequence and diagnostics are original to
the port. No Apple ROM, System code, upstream artwork or game executable is
included. The link map shows only the local probe object, and the build uses
`-nostdlib`; compiler/tool licensing and any future runtime distribution still
need review.

The user supplied the publisher's Windows `m68k-unknown-elf` GCC 16.2.0 bundle,
archive SHA-256 `18d36e1233b54fb2346e134ac849edc436db4e3f1cd50fdea5435aa02c1e5ba2`.
Its complete extracted-file inventory and tool identities are recorded in
`C:/Repos/ClasSICK-0.97/docs/development/windows-m68k-toolchain-20261114.md`.
The first probe source SHA-256 was
`567b014af20d34bb7c4f3fbe020c3cae0b332e31b493287bcbe8742ce8be7a37`.
Two independent first-probe builds produced the same 65,536-byte ROM SHA-256
`97f44775d70f8fa83191018b8fc4faa19e5b6a4d9a18f1e866ffac36b3717110`.

With BootHush executable SHA-256
`5d4f610e98cbb8b03476f28929d6e5c0f64b941aafac3c7d5b6ef12c76c7eeb3`,
the bounded Mac128K run reached diagnostic marker `a55a` and matched ten
expected position/velocity pairs, starting at `8140/0140` and ending at
`8ae0/0000`. An intentionally mutated acceleration changed the first pair to
`8120/0120`, demonstrating that the check detects that error. The first build
attempt was rejected by GCC's fixed-address bounds diagnostic; the corrected
probe passes the address as a normal function argument from the startup code.
Its failed log remains in `C:/Repos/.task-temp/nstb-native-c-probe-20261114-a`.
The successful logs, commands, generated ROMs, mutation and report are in
`C:/Repos/.task-temp/nstb-native-c-probe-20261114-c`.

## Reusable movement component

The subsequent `guest/sinbad_movement.c` and header separate the movement step
from the diagnostic. Two independent state pairs run the same component in
opposite directions, accelerate for four calls, and coast to rest. The caller
owns inputs, direction-entry behavior, pacing, and position bounds; the
component's 16-bit position wraps. This separate probe does not establish
equivalent NES behavior. The source-informed constants and
their earlier attribution remain as above; this is game-informed code, not an
eligible ClasSICK implementation input.

Two Windows-native compiler builds produced identical 65,536-byte ROMs with
SHA-256 `4f60b4f9500318f56a6f8c23331f7bd61062bc67f6e651d24ee596eef7ac429a`.
BootHush matched all ten right and ten left position/velocity pairs. A changed
acceleration immediate failed the expected first rightward pair. Commands,
tool and source hashes, link maps, complete guest data and negative control
are in `C:/Repos/.task-temp/nstb-native-c-component-20261114-a/report.json`.
The local link map contains the two project objects, with `-nostdlib`.

Separately, `tests/sinbad_movement_test.c` checks eleven host cases including
both speed limits, direction reversals, friction crossing zero, and wrap.
Using host compiler SHA-256
`93303edd5791e4b60682f819267a34c349e5f52d052d067e006e76d21cc82ea4`:

```powershell
$cc = 'C:/ClasSICK/bootstrap-clean-source-verified/.tools/llvm-mingw/llvm-mingw-20260908-ucrt-x86_64/bin/clang.exe'
& $cc -std=c11 -Wall -Wextra -Werror guest/sinbad_movement.c tests/sinbad_movement_test.c -o C:/Repos/.task-temp/NEW-MOVEMENT-TEST.exe
& C:/Repos/.task-temp/NEW-MOVEMENT-TEST.exe
```

The run printed `11 movement cases passed`; the executable is retained at
`C:/Repos/.task-temp/nstb-movement-host-20261114-a/movement-test.exe`.
These host checks are software evidence and do not prove target timing or
physical hardware behavior.

After this component work, the existing mouse-title and keyboard handoff
regression was also rerun against the same BootHush executable. Its 22
scenarios and recorded/replayed mouse-to-keyboard handoff passed; the
unchanged title ROM SHA-256 is
`7121c504159e128d9ec7349213837c5d7b0dbdf8ead594e687334c63e2926ccd`.
The per-case outputs are in
`C:/Repos/.task-temp/nstb-title-post-component-20261114-a`; this remains the
hand-emitted prototype, not a live integration of the C component.

## Opt-in title with native player-one movement

The builder now accepts a separately linked native component in an opt-in ROM
slot beginning at offset `0xe000`. The existing emitter still owns title,
keyboard, pacing, bounds, drawing and player two. After mouse Start, the
player-one tick calls the C component for velocity; it writes the component's
integrated position to a scratch word because the existing compositor must
erase the old figure before applying velocity to the actual position. This
bridge uses the Windows compiler's observed 68000 calling convention. It does
not establish a general ABI or change the default title build.

Two Windows builds of the 78-byte component matched, SHA-256
`a65c5fa382bee316b916cd6c6af52c4a2591496aa762c346e784e7a8bca7d25c`.
The resulting 65,536-byte ROM SHA-256 is
`71de2f909f27348e23c28cb8a18ab869c04f79ee190092d43d8887e3093d2974`;
the generated emitter code ends at offset 37,012 and the C slot at 57,422.
In BootHush all 22 existing title scenarios passed, including mouse Start,
keyboard movement, jump, attack, timeout/retry and replay. Six checkpoints
across rightward input, release, leftward input and release matched the legacy
title's movement state. Replacing the C acceleration immediate changed the
final keyboard-driven X from 37,088 to 36,416, confirming this live path calls
the C component. This is a mutation control, not a claim of a physical speed
or NES equivalence. The separate default title regression also passed with
its unchanged `7121c504...` ROM.

Full commands, independently built component binaries, source and tool
fingerprints, ROMs, per-case results, comparison samples and mutant are in
`C:/Repos/.task-temp/nstb-native-c-title-20261114-c/report.json`; the default
control is `C:/Repos/.task-temp/nstb-title-legacy-control-20261114-a`.
The independent BootHush title integration tests passed for this ROM as well.
They and both standalone C fixture checks were rerun successfully with the
later BootHush input-accounting executable SHA-256
`62daf36a8d1e034667fbd73dd09a2a6134a6a0144ea56010d327b41fd110d9da`.
The four-test output and the partial rebuild's object identities are linked
from `C:/Repos/boothush/docs/pc286-input-accounting-20261114.md`. This checks
that the 286 reporting change did not regress these selected Mac fixtures;
it is not new hardware evidence.
Reproduce with:

```powershell
$py = 'C:/Users/segab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$tools = 'C:/Repos/.task-temp/m68k-windows-native-20261114-a/x-tools-v3-win/m68k-unknown-elf/bin'
$bh = 'C:/Repos/.task-temp/boothush-replay-series-20261114-a/boothush.exe'
& $py -B scripts/test_native_c_title.py --tool-bin $tools --boothush $bh --output C:/Repos/.task-temp/NEW-NATIVE-C-TITLE
```

For later progress reporting, the `title-test/neutral.png` and
`title-test/play_keys.png` files in that `-c` receipt directory are lossless
512x342 conversions of its guest-only PBM frames; pixel equality was checked.
Their PNG SHA-256 values are respectively
`aabf25b889449d55e98e98a9ec965479c114c95255a9c08bff57116cb5f5589a` and
`d07639ad8aeffeb5e4c6e99fafe4682b0d33ebae8f2084ea824c8d76f1211e6e`.
They show the original-art modeled title and the post-Start keyboard scenario,
not physical hardware or a completed game. They are generated local evidence,
not committed assets.

This remains an opt-in two-character experiment with placeholder graphics,
experimental hardware mapping and incomplete match mechanics. In this earlier
profile only player one's velocity step uses C; it is not a complete game or a
hardware result.

## Opt-in native movement for both players

The `--native-p2` test build also calls the same source-informed C movement
component for player two. It retains the prototype's keyboard mapping and
last-pressed direction policy. Player two now accelerates and coasts rather
than using the earlier fixed one-pixel step; the local attack lock pauses its
movement and velocity update. This is a port design choice, not proof of
source-game equivalence. Player one and player two have separate velocity
words and use the component sequentially; their display remains original
placeholder art. The older default and player-one-C ROMs remain byte-identical.

Two independently compiled copies of the 78-byte component matched. The
65,536-byte combined ROM SHA-256 is
`b4d75d3839e36cdfb5233b521b0a3474256ebe932525f1aa36a16b418884b126`;
the emitted code ends at offset 37,220 and the component ends at 57,422.
With BootHush SHA-256
`62daf36a8d1e034667fbd73dd09a2a6134a6a0144ea56010d327b41fd110d9da`,
the existing 22 mouse-title and keyboard scenarios passed. A separate 32-frame
VBL series verified the completed-frame pixel oracle and 27 adjacent player-two
movement intervals, including both directions and coasting. Four cycle-based
input-state checkpoints checked overlapping keys and restoration of the held
direction. Simultaneous player-one/player-two input moved both. A mutant
acceleration changed player two's final X from 47,328 to 46,656; the player-one
mutation control also remained effective. The independent BootHush title
integration checks passed with this ROM.

BootHush's later fixed-disk fault-injection build SHA-256
`703da7b4b3883f899cff6b17d221a3afce69bcf4d04e21d07718252ed2b6c0b0`
also passed the two title and two native-C port integration tests against
their pinned fixtures. The test output and partial-build limitations are in
`C:/Repos/boothush/docs/pc286-hard-disk-fault-20261114.md`. This is a
cross-project regression, not a physical test.

The follow-up BootHush write-failure build SHA-256
`370f7a12a31bed9908813686a0cbd6bb197065b5e5d3e443fc48ad843e69f28d`
also passed those four pinned port integration tests. Its saved test log and
partial-build inputs are in
`C:/Repos/.task-temp/boothush-pc-hard-fault-twins-20261114-c`; this adds no
claim about game completeness or original hardware.

Commands, source and compiler identities, images, input witnesses, states,
pixel captures and mutant are in
`C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/report.json`. The first
trace attempt in sibling `-b` requested 37 frames, exceeding BootHush's
32-frame cap, and was rejected before the guest ran. In `-d`, an arbitrary
cycle capture interrupted a framebuffer redraw, so treating it as a completed
frame failed the pixel oracle. The corrected overlap check tests state only at
those arbitrary cycles; the VBL series and settled scenarios separately check
pixels. Neither result establishes tear-free physical presentation.

`C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/simultaneous-move.png`
is a lossless, pixel-verified 512x342 conversion of the modeled simultaneous
movement frame. Its PNG SHA-256 is
`fbc0163e48c58fc608591d3ac8c25881029d3a98f341bcc39fe6b2d45d72830b`;
the source PBM SHA-256 is
`e6acb7be465283cc3ea726ff4109aadb27765239374d8f03f2d6525e13eca5d3`.
It is generated guest-only evidence, not a physical demonstration or a
committed asset. Reproduce the experiment with the previous `$py`, `$tools`
and `$bh` settings and a fresh output directory:

```powershell
& $py -B scripts/test_native_c_title.py --tool-bin $tools --boothush $bh --output C:/Repos/.task-temp/NEW-DUAL-C-TITLE --native-p2
```

This still lacks a complete match, full game mechanics, source-matched NES
comparison, audio, verified physical keyboard behavior and original-hardware
testing. Game-informed code is not automatically a ClasSICK implementation
input.

### Combat after mouse Start

On 2026-11-15, the same dual-C title ROM was exercised beyond movement.
After modeled mouse Start, five keyboard-driven scenarios covered an
out-of-range miss, a player-one hit, a player-two hit, an exchange in which
both land a hit, and player-two movement lock during an attack. In the two-hit
exchange each character's diagnostic damage increased by two. The independent
frame and state oracle checked 25–29 adjacent serviced VBL intervals per
scenario, including the new player-two velocity, the existing local hit
rules and original-art pixels. Keyboard witnesses reported all scheduled
events accepted with none pending, rejected or dropped. Deliberately changing
player one's increment to one produced one point instead of two; the
equivalent player-two mutation was rejected at the expected damage assertion.

The ROM SHA-256 remained
`b4d75d3839e36cdfb5233b521b0a3474256ebe932525f1aa36a16b418884b126`;
BootHush SHA-256 was
`370f7a12a31bed9908813686a0cbd6bb197065b5e5d3e443fc48ad843e69f28d`.
Exact commands, input schedules, per-frame observations, source and component
identities, images, witnesses and mutant identities are in
`C:/Repos/.task-temp/nstb-dual-c-combat-20261115-b/report.json`. The legacy
two-character test also passed after the shared oracle was extended, with ROM
SHA-256 `79ec8cf01b4156c5a34ae83c7e3a308a327802f56b6f187bfc66ec0a85e1a1d2`
and evidence in `C:/Repos/.task-temp/nstb-two-player-regression-20261115-a`.
Reproduce with fresh output:

```powershell
$py = 'C:/Users/segab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$bh = 'C:/Repos/.task-temp/boothush-pc-hard-fault-twins-20261114-c/a/boothush.exe'
$component = 'C:/Repos/.task-temp/nstb-dual-c-title-20261114-e/a/movement.bin'
& $py -B scripts/test_dual_c_combat.py --boothush $bh --component $component --output C:/Repos/.task-temp/NEW-DUAL-C-COMBAT
```

These checks exercise the port's existing local prototype combat, not
source-matched hitboxes, knockback, stocks, a complete game, physical input or
hardware timing. Game-informed implementation remains within the port.

Reproduce with a fresh output directory outside the repository:

```powershell
$py = 'C:/Users/segab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$tools = 'C:/Repos/.task-temp/m68k-windows-native-20261114-a/x-tools-v3-win/m68k-unknown-elf/bin'
$bh = 'C:/Repos/.task-temp/boothush-replay-series-20261114-a/boothush.exe'
& $py -B scripts/test_windows_m68k_probe.py --tool-bin $tools --boothush $bh --output C:/Repos/.task-temp/NEW-NATIVE-C-PROBE
```

The standalone probe has no keyboard; the opt-in title test supplies modeled
keyboard input. Neither has audio, a complete game loop, a source-matched NES
comparison, physical hardware testing, or a complete match. BootHush's optional independent fixture test
is documented in `C:/Repos/boothush/docs/mac-keyboard.md`.
