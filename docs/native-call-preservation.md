# Native game-call preservation, 2026-11-16

Question: does the mixed emitter/native-C prototype preserve its calling
convention across the movement and jab calls actually reached after mouse
Start? Pixel checks alone would not detect a damaged saved register before
it affects visible behavior. This is a software test and BootHush observation,
not a physical Macintosh, completed match or historical compatibility result.

`scripts/test_native_call_preservation.py` runs the existing native jab title
ROM, SHA-256
`81a8d80ba392f58a953a14887587b888c11961b8711bd0916463022558cfd4e6`.
The game implementation and original placeholder artwork are unchanged from
port revision `7a87f3e63cbce1439ea9991d42dd59bee3063855`; build identities and
source eligibility remain in [mouse-title evidence](mouse-title-evidence.md)
and [jab-chain evidence](jab-chain-evidence.md). This test does not admit
game-derived code as a ClasSICK implementation input.

BootHush revision `40b4279` adds the stopped-register observation API. Its
tested executable SHA-256 is
`a4c51633e9ee1a2a935eae270f54959d2d72f5ea3f6bd8c5a085264904d0edd7`;
the canonical interface/build receipt is
`C:/Repos/boothush/docs/mac-cpu-state.md`. Runs are headless, bounded at ten
million modeled cycles and 20 seconds, with a 25-second process timeout.

```powershell
python -B scripts/test_native_call_preservation.py --boothush EXE --rom TITLE_JAB_ROM --output NEW_EXTERNAL_DIRECTORY
```

The exact commands, stopped states, full frames, hashes, controls and attempted
scenarios are retained in
`C:/Repos/.task-temp/nstb-native-call-preservation-20261116-a/report.json`.
The script refuses a different ROM identity and existing output directory.
Each boundary run starts from reset with the same inputs: mouse press at
2,000,000 and release at 2,400,000, then scenario keyboard events at 3,500,000
and 3,700,000. No physical input is injected.

Ten call sites pass: six movement calls (neutral, left and right for both
players), two jab-begin and two jab-tick calls. Each checks D2-D7, A2-A6,
active A7, SR control bits and unchanged framebuffer across the call. The
caller-saved registers and condition codes are allowed to change. The measured
call costs are 144/168/164 modeled cycles for right/left/neutral movement,
96 for jab-begin and 188 for jab-tick. These are first-reached paths, not
worst-case costs or a physical timing claim.

All ten after-call runs also match an unobserved control in complete JSON
(apart from the requested CPU object) and frame bytes. Three separate mutant
ROMs replace one callee with an original D7-clobber/return sequence; all three
are detected. The supplied input ROM is never modified. This validates the
check against a concrete bad-callee failure, not every possible corruption.

The new executable also passes the existing functional suites:

- `nstb-cpu-state-title-20261116-a/summary.json`: title cases, frame replay and
  mouse/keyboard handoff.
- `nstb-cpu-state-axis-20261116-a/report.json`: 160 phase/boundary cases and
  detection of the wrong-sign mutant.
- `nstb-cpu-state-jab-20261116-a/report.json`: 22 native scenarios and the
  existing damage, normalization and attack mutation controls.

Those directories are under `C:/Repos/.task-temp/`; commands are the existing
three reproduction commands in mouse-title evidence with this executable.
No generated ROM, trace or frame has entered Git.

## Cross-project use

ClasSICK independently tests its own interrupt wrappers and selected production
interrupt spans with the same BootHush observation interface. Its canonical
receipt is `C:/Repos/ClasSICK-0.97/docs/development/windows-m68k-toolchain-20261114.md`.
The useful shared result is the test method: identify real call boundaries,
check preserved registers and stack, compare unobserved controls, and inject
a known bad callee. Port source or game behavior is not copied into ClasSICK.
Neither result establishes all call paths, physical hardware, human input or
paired-release qualification. A playable game remains unfinished.
