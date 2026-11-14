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
The local probe source SHA-256 is
`567b014af20d34bb7c4f3fbe020c3cae0b332e31b493287bcbe8742ce8be7a37`.
Two independent builds produced the same 65,536-byte ROM SHA-256
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
