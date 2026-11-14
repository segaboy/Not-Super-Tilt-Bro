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
component's 16-bit position wraps. It is not yet linked into the title ROM and
does not establish equivalent NES behavior. The source-informed constants and
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

Reproduce with a fresh output directory outside the repository:

```powershell
$py = 'C:/Users/segab/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$tools = 'C:/Repos/.task-temp/m68k-windows-native-20261114-a/x-tools-v3-win/m68k-unknown-elf/bin'
$bh = 'C:/Repos/.task-temp/boothush-replay-series-20261114-a/boothush.exe'
& $py -B scripts/test_windows_m68k_probe.py --tool-bin $tools --boothush $bh --output C:/Repos/.task-temp/NEW-NATIVE-C-PROBE
```

The current title/game slice still uses its existing emitter. This probe has no
keyboard, audio, full movement loop, source-matched NES comparison, physical
hardware test, or complete match. BootHush's optional independent fixture test
is documented in `C:/Repos/boothush/docs/mac-keyboard.md`.
