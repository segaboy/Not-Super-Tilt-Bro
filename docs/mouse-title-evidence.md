# Mouse title and keyboard-play experiment — 2026-11-14

Latest input qualification: [failed-drain recovery replay](#failed-drain-recovery-replay---2026-11-17).

## Question, origin and scope

The owner directed a mouse-driven title/start screen followed by keyboard
controls during play. Can the replacement ROM demonstrate that transition in
BootHush without Apple ROM or System software? This is an opt-in port prototype,
not a complete game, qualified mouse driver, physical mouse test or ClasSICK
release evidence. Original geometric lettering, button and pointer are drawn
locally; no upstream game assets or Apple assets are used.

The polling phase interpretation and direction convention were informed by
ClasSICK 0.97's original GPL-3.0-or-later `platform/mac128k/polled-phase.c`
at `9c484940d39c2f6c18e01a4eaba9f2a7fe77e258`, file SHA-256
`537d6d62bf3177e16153c86ba4d42fee90a90192bf17e103fc635f5bf1518766`.
Its `platform/mac128k/window-entry.c`, SHA-256
`64c04e4d13fd0a811e6b38ab504fe2d9460aa53d326f1327d94807c58a8ece9d`,
explicitly describes the SCC aliases as an unverified engineering hypothesis.
The port's limited polling and local button/compositing code are not the full
ClasSICK driver. The source-derived game slice remains subject to the separate
boundaries in [provenance](provenance.md); this experiment and its emulator
observations do not automatically become eligible ClasSICK implementation inputs.

## Build, inputs and observations

Port base commit before title changes: `cba9040`. The tested 65,536-byte title
ROM SHA-256 is `27ec8baf67612424b107426ff0eacc6fc4a6f5d79ffe47e480da4fe218f38568`;
used through byte offset 35,672. BootHush executable SHA-256 is
`1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`.
Use fresh output paths; all emulator runs are headless and cycle/time bounded:

```powershell
$py = 'C:\ClasSICK\bootstrap-clean-source-verified\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py -B scripts/build_mac_title.py --output out/NEW-TITLE.rom
& $py -B scripts/test_mac_title.py --boothush $bh --keep out/NEW-TITLE-TEST
& $py -B scripts/capture_title_evidence.py --boothush $bh --output out/NEW-TITLE-MEDIA
```

The retained test run is `out/title-test-20261114-h`; each case stores the
exact command, process JSON, final guest-only PBM and keyboard witness. Fifteen
scenarios cover neutral title, four directions, an outside click, return and
start, a direct start, pre-start queued keyboard events, each player's
post-start key events, two modeled edge intervals, a forced keyboard-transfer
timeout and a retry. A fast-motion case characterizes a known failure and is
not an acceptance assertion requiring the failure to persist. Final image
checks reconstruct title pixels and cursor from the same original shape data;
they detect unexpected stale pixels but are not an independent artwork oracle.
For the gameplay screen they use the two-character pixel oracle. The earlier
two-character profile passed separately with its previous ROM hash unchanged.

At start, the pointer begins at `(256,210)` inside the inclusive Start bounds
`(208,196)` through `(304,224)`. A released button arms a subsequent press;
clicking outside does not start. On a valid press the ROM drains up to 65
modeled instant-keyboard replies through an empty reply before play. A held
title-time key must be released and pressed again. A timeout or exhausted
drain remains on the title screen and allows a fresh click. No on-screen error
message is implemented. The transition can take time: diagnostic byte
`0xb49` is 1 for title, 4 while starting, 2 after the first complete gameplay
draw, or 3 after a drain failure. Pointer coordinates at `0xb40` and `0xb42`
are big-endian words. Gameplay's key positions and limits are documented in
[two-character evidence](two-character-evidence.md).

With a 32-pixel modeled +X request and 64 transitions, the 2,048-cycle edge
case ended at X=288 as requested. At 256 cycles it ended at X=251, despite
BootHush reporting all transitions delivered and none pending. This is a
modeled observation of missed or misinterpreted sampling by this combined
guest/model setup, not a measured physical speed limit or proof of an emulator
defect. The prototype polls and redraws synchronously; it does not count all
missed phase transitions, and rapid or diagonal motion needs more work. SCC
alias, polarity, electrical behavior and real device timing are not qualified.
Headless scheduled events are not human or physical-device input.

Guest-only captures, witness, exact command and a 37-frame, 30-fps video are
retained under ignored `out/title-media-20261114-d`. Its GIF SHA-256 is
`71e90211ca3d3bcf5ebd144bd675d70b2f03effd9993ec5be146c11a08c20256`;
it shows modeled mouse movement, a click and the subsequent keyboard-driven
figures. It is not a live physical input recording or a playable full match.

## Follow-up: fewer redraws during polling

On the same date a follow-up keeps a logical pointer separate from the last
drawn pointer, refreshing after 16 pixel steps or 16 unchanged polling passes.
The button hit test uses the logical position, so during the brief redraw delay
the visible and selected positions can differ. This reduces redraw work during
motion but is not a lossless mouse driver. The optimized 65,536-byte ROM
SHA-256 is `d84d0ab3a1c981c2cbfb1a8ec039c189f3f83500ae90672f19b16ddb976df54e`,
used through offset 35,822. The previous ROM and its results above remain a
historical comparison, not the current output of the builder.

The same BootHush executable and `scripts/test_mac_title.py` command retained
16 scenarios plus a 22-sample during-motion check in ignored
`out/title-deferred-test-20261114-d`. At 1,024 modeled cycles per edge, the
32-pixel +X case now ends at X=288; the previous ROM ended at X=277 under the
same schedule. Displayed-position samples include an intermediate X between
256 and 288 before settling at 288, so the test does not merely check a
single redraw after the entire movement. At 256 cycles the current result is
still inaccurate; consult `summary.json` rather than assuming a reliable
speed threshold. Both runs report 64 transitions and zero pending. This is a
controlled emulator comparison, not a physical hardware qualification.

The updated capture under ignored `out/title-deferred-media-20261114-b` uses
the same scripted title-to-play scenario. Its GIF SHA-256 is
`e7ae88d5c1f4ceca8ef5b3f626c5adefb3629cc42d6c548bfffb23f00545b43e`.
Because the capture can occur while motion is still queued, the title-frame
oracle uses the last drawn coordinates. An arbitrary VBL can still occur
mid-redraw; no hardware-latched frame guarantee is implied.

BootHush commit `49f2d34` adds an optional integration regression against the
exact optimized ROM hash above. With the fixture supplied, it repeats a
mouse-title-to-keyboard-play sequence and compares guest reports, keyboard
witnesses and captured frames; without the fixture it skips. Its canonical
setup and limits are in `C:/Repos/boothush/docs/mac-keyboard.md`. It exercises
the emulator integration with this experimental port, not physical input or
ClasSICK release qualification.

### Replay checkpoints, 2026-11-14

With port source based on `2d9a137eab9542ba5063e5298cc893c361cc7a59` and
the enhanced `scripts/test_mac_title.py`, a headless run used the same title
ROM `d84d0ab3a1c981c2cbfb1a8ec039c189f3f83500ae90672f19b16ddb976df54e`
and BootHush executable SHA-256
`5d4f610e98cbb8b03476f28929d6e5c0f64b941aafac3c7d5b6ef12c76c7eeb3`.
The 16 title/handoff cases passed again. The 22 during-motion frames and
86-byte state snapshots matched exactly when the recorded mouse samples were
replayed. Trace SHA-256 is
`42da5574c94f0e975d151b2a829790565e0f7571a8fc32cef13b0caeb3dd933a`;
the concatenated replay frames SHA-256 is
`0e41367bb760af9bf7843a3e669a809acf9181eb3b42b4fc9faa6226928ad2b1`.
The ignored local receipts and exact commands are in
`out/title-replay-test-20261114-a`; the test now requires BootHush with replay
frame-series support. These are injected emulator events. The 256-cycle case
still ends at X=250 rather than the intended X=288; physical input, a playable
game and release qualification remain unproved. This reproducible capture
workflow also supports ClasSICK testing without making game source a ClasSICK
implementation input.

### Window-message title controls and polling experiment

The subsequent `out/title-window-events-20261114-a` run retains the same ROM
`d84d0ab3a1c981c2cbfb1a8ec039c189f3f83500ae90672f19b16ddb976df54e`
and BootHush executable
`5d4f610e98cbb8b03476f28929d6e5c0f64b941aafac3c7d5b6ef12c76c7eeb3`.
Eighteen scenarios pass, now including invisible window-message input: moving
outside Start and clicking leaves the title active; returning, clicking Start,
and pressing a gameplay key enters the arena and moves player one. Full frames,
commands and keyboard witnesses are in that local directory. These are
injected messages, not real mouse or human input.

A separate attempted optimization skipped the axis transition table when the
sampled phase was unchanged. It produced ROM SHA-256
`a0f1f10adc4d2925a8c28eeea8eab1db485693c44d69cd8048c0ec6260ed85e9`;
the previously passing 1,024-cycle case ended at X=287 rather than X=288, and
the 256-cycle case ended at X=247. The test stopped on the regression; its
per-scenario captures and commands remain in ignored
`out/title-poll-fast-20261114-a`. The attempted change was removed. These
timing-dependent model observations do not establish a physical speed limit.

The follow-up `out/title-actions-20261114-a` reran the same ROM and BootHush
executable with 22 title/handoff scenarios. In addition to both players'
movement, separate post-Start scheduled keyboard cases now verify one P1 jump,
one P2 jump, one P1 attack and one P2 attack using the guest's event counters
and full-frame check. Mouse Start precedes each action; keyboard witnesses
show no rejected, pending or dropped events. This is modeled input to the
existing game-logic slice, not proof of a complete match, physical key layout,
rollover or playable original hardware.

### Visible control hints

The current title ROM now draws original geometric `MOUSE START` and
`KEYBOARD PLAY` hints below the Start button. This follows the owner's chosen
mouse-title/keyboard-play flow; it does not claim a verified physical key
layout. The image was inspected from a guest-only BootHush PBM converted
losslessly to `out/title-controls-labels-20261114-a/neutral.png` (SHA-256
`aabf25b889449d55e98e98a9ec965479c114c95255a9c08bff57116cb5f5589a`).
No Apple or upstream game artwork was used.

The current 65,536-byte ROM SHA-256 is
`1a367b8eceb9f032e20b679e9224cedf44cde1fc4615720e25710d23f0bd839e`,
used through offset 36,854. The previous `d84d...` ROM remains historical.
All 22 title, mouse, action and replay scenarios pass using BootHush executable
`5d4f610e98cbb8b03476f28929d6e5c0f64b941aafac3c7d5b6ef12c76c7eeb3`;
the exact commands, images, reports and trace are in
`out/title-controls-labels-20261114-a`. BootHush's optional title integration
was updated to accept and independently test both pinned ROM identities.
These are injected emulator tests, not a completed game or physical result.

### Recorded mouse-to-keyboard handoff

With the same `1a367b8e...` ROM and BootHush executable `5d4f610e...`,
`scripts/test_mac_title.py` now records mouse movement and a Start click,
then replays those mouse inputs with the same scheduled keyboard press and
release. All 22 existing scenarios pass, and five cycle-indexed frames and
86-byte guest-state snapshots match between the recording and replay. The
guest enters gameplay and the modeled P1 position advances to 37,088. The
trace SHA-256 is
`7ecce07edd6b715d66ab2ba4c79d6addee16d97cde8c57b9c29c4359a2ca3aa4`;
the frame-series SHA-256 is
`2ef5eb0505d16dfbbfcce45be50bc2873a2112ea5cfc48a12fc5a6445e0d707c`.
Exact commands, input traces, keyboard witnesses, frames, ROM and results are
in `C:/Repos/.task-temp/nstb-handoff-replay-20261114-b`. An earlier attempt
in the sibling `-a` directory failed because scheduled inputs were listed out
of order; it is preserved. This demonstrates injected emulator behavior,
not physical input or a completed playable game. BootHush's independently
maintained optional integration test also covers this handoff.

The subsequent damage-saturation change produces title ROM SHA-256
`7121c504159e128d9ec7349213837c5d7b0dbdf8ead594e687334c63e2926ccd`,
used through offset 36,886. The 22 title scenarios, in-motion replay and the
mouse-to-keyboard replay pass in
`C:/Repos/.task-temp/nstb-damage-cap-title-20261114-a`, using the same
BootHush executable. The earlier ROMs and receipts remain historical. See
[two-character evidence](two-character-evidence.md) for damage behavior and
its test-only boundary fixture. BootHush's optional pinned title integration
also passes with this new ROM.

### Branchless phase sampling experiment

An independently written register-based phase sampler replaced the title's
per-bit branch sequence in an experiment. Its 65,536-byte ROM SHA-256 was
`369b42dbab3ac4ddee10d4bdb8f906feca36002f10655db86159045f6c0b1072`,
used through offset 36,774. With the same BootHush executable
`5d4f610e98cbb8b03476f28929d6e5c0f64b941aafac3c7d5b6ef12c76c7eeb3`,
all 22 title/action cases and both replay checks passed. For a scripted
32-pixel X movement, both the previous and experimental ROM ended at X=288
with 2,048- and 1,024-cycle edges. At 256-cycle edges the previous ROM ended
at X=250 and the experiment at X=248, rather than the intended X=288. The
experiment was removed; the `7121c504...` ROM remains current. Commands,
frames and guest state are retained in
`C:/Repos/.task-temp/nstb-branchless-mouse-20261114-a`, with the baseline in
`C:/Repos/.task-temp/nstb-damage-cap-title-20261114-a`.

These are modeled observations, not a physical speed limit; changed sampling
phase may affect the result. This does not isolate emulator versus guest timing
and does not establish game completion. The independently written sampling
idea and the controlled result may inform future input experiments; no game
source is transferred to ClasSICK.

BootHush independently added repeated 1,024- and 256-cycle edge cases to
its optional pinned title-ROM integration. It verifies 64 modeled steps and
repeatability for all three admitted title ROMs, while characterizing rather
than requiring the current 256-cycle loss. See
`C:/Repos/boothush/docs/mac-keyboard.md` for the tool-side setup and limits.

### Modeled phase changes between guest reads

To investigate why the fast case misses movement, the original guest-ROM and
BootHush mouse witness were run with +32 X pixels at cycle 1,000,000 and
edge spacings of 256 and 1,024 modeled cycles. The analysis counts modeled X
phase transitions between successive guest SCC-A reads at `0x9ffffa` while
the 64 transitions are in progress. These are emulator observations of this
specific ROM and schedule, not physical timing measurements or proof of the
sole cause of loss.

| Edge spacing | Final guest X | Read intervals | Phase changes per interval |
| --- | ---: | ---: | --- |
| 256 cycles | 250 | 20 | 2 in two intervals, 3 in twelve, 4 in six |
| 1,024 cycles | 288 | 85 | 0 in 21 intervals, 1 in 64 |

The respective maximum observed read gaps during movement were 972 and 1,646
modeled cycles; the larger slow-case gap shows that a maximum gap alone does
not determine the result. Witnessed and unwitnessed runs matched guest status,
cycles, PC, memory, mouse totals and full frames for each spacing; neither
witness dropped events. The fast trace SHA-256 is
`b40bf4e5015a439fea44244b27937d72f20ece042aef22f784e8080166a1972c`;
the slow trace SHA-256 is
`2fd89a32c819a445282f58edf85e29fbb72c2558a971226d8c7bf17eb530efa7`.
The ROM and BootHush identities are `7121c504...` and `5d4f610e...`, as
specified in the preceding evidence. Exact commands, frames, traces and report
are in `C:/Repos/.task-temp/nstb-mouse-witness-20261114-b`.

Reproduce with `scripts/characterize_mouse_sampling.py --boothush EXE --rom ROM
--output NEW_DIRECTORY`; the script requires this pinned ROM and a fresh
output directory outside the repository. Multi-edge intervals are consistent
with information loss during polling, but do not distinguish guest design,
model fidelity, sampling alignment or their interaction. The reusable finding
is the event-count method and witness result, not game-derived implementation.
## Finite phase lookup and mask trace - 2026-11-16

Question: can the original title adapter spend less time deciding a phase
transition while retaining the mouse Start / keyboard play behavior? Starting
from port revision `6ee7fc2928fd7d89f49fb384c4e723b5a14a5331`, the four existing
DCD-changing Gray transitions were encoded in a 16-byte table for each axis.
The adapter still retains the prior position at an outward boundary, saves the
sampled phase on every pass, reverses the Y convention, and draws the original
pointer. No game source or third-party implementation informed this change.
The earlier phase-source attribution in this receipt continues to apply.

The title ROM now uses 36,502 bytes through its emitter end, versus 36,886 for
the control (384 fewer bytes). Its SHA-256 is
`c693dcfebf1c9c4b1048abc50503f3462985a926dedc57fe6c5d1da25bfb7d72`.
`scripts/test_title_axis.py` executes all 16 previous/current phase pairs at
five positions on both axes: 160 cases, including both boundaries, unchanged
phases and invalid two-bit jumps. A separately calculated Gray-order oracle
checks position, dirty byte and saved phase. Changing one positive table entry
to negative is rejected in exactly the intended case. Original fixture ROMs,
commands and results: `C:/Repos/.task-temp/nstb-axis-table-20261116-a/report.json`.

With BootHush executable SHA-256
`f84de40301b433264fb3697bb2dcd132cdeb901a974d416e8d4482c81e73495d`,
the existing title suite passes its 16 scenarios, 22 captured-frame replay and
mouse-to-keyboard handoff replay. Its receipt is
`C:/Repos/.task-temp/nstb-title-table-20261116-a/summary.json`.
The native jab/side-tilt suite also passes all 22 scenarios and its mutation
controls, with ROM SHA-256
`81a8d80ba392f58a953a14887587b888c11961b8711bd0916463022558cfd4e6`:
`C:/Repos/.task-temp/nstb-table-native-jab-20261116-a/report.json`.
The latter contains source-derived game work and remains port-only evidence.

The new BootHush `probe_mac_cpu_mask.py` compared this title ROM with the
previous `7121c504...` control at four edge spacings. Each run requests +32 X
pixels at cycle 1,000,000, starts from X=256, uses DCD inversion 3 / guard 4,096,
and stops at cycle 4,000,000. All eight traced/untraced pairs have identical
complete guest JSON and frame bytes, with no trace drops and all 64 modeled
phase transitions delivered. Exact commands, hashes and traces:
`C:/Repos/.task-temp/nstb-baseline-mask-20261116-a/report.json` and
`C:/Repos/.task-temp/nstb-table-mask-20261116-a/report.json`.

| Modeled edge cycles | Control final X | Lookup final X | Control mean SCC-A read interval | Lookup mean interval |
| --- | --- | --- | --- | --- |
| 256 | 250 | 246 | 877.30 | 781.91 |
| 512 | 264 | 268 | 842.85 | 761.00 |
| 768 | 280 | 287 | 867.97 | 793.44 |
| 1,024 | 288 | 288 | 870.94 | 797.89 |

Intervals are modeled cycles between successive SCC-A reads whose interval
overlaps the first-to-last phase event. Their means are 8–11% shorter; faster
polling does **not** imply fewer losses at every spacing, as the 256-cycle
counterexample shows. Expected X is 288. Both ROMs remain at IPL7 throughout
the witness range because the title polls; this is not evidence of an IRQ
delivery defect. The trace format and censoring limits are documented in
`C:/Repos/boothush/docs/mac-mouse-witness.md`.

These are software tests and emulator observations, not a physical mouse
rate, playable match, hardware validation or release qualification. The
reusable finding for ClasSICK is the measurement method and the need to
distinguish polling interval from IRQ exclusion. Game code was not transferred.

Reproduce with fresh output directories and the executable/tool paths recorded
in the reports:

```powershell
python -B scripts/test_title_axis.py --boothush EXE --output NEW_AXIS_OUTPUT
python -B scripts/test_mac_title.py --boothush EXE --keep NEW_TITLE_OUTPUT
python -B scripts/test_native_jab_title.py --tool-bin M68K_BIN --boothush EXE --component MOVEMENT_BIN --output NEW_GAME_OUTPUT
```

The subsequent BootHush instruction-witness build, executable SHA-256
`cd3992737cc78ef5758a376872cac8005e7b959157b4be69349f31141c68fe9b`,
passes the same title/replay, 160-axis-case and 22-native-scenario suites.
ROM identities are unchanged. Final receipts are
`C:/Repos/.task-temp/nstb-table-title-final-20261116-a/summary.json`,
`C:/Repos/.task-temp/nstb-table-axis-final-20261116-a/report.json`, and
`C:/Repos/.task-temp/nstb-table-native-final-20261116-a/report.json`.

ClasSICK used this original polling control and BootHush's new instruction
witness to distinguish polling gaps from interrupt exclusion. Its
[pinned receipt](https://github.com/segaboy/ClasSICK-0.97/blob/86e6d2c/docs/development/windows-m68k-toolchain-20261114.md#interrupt-mask-and-instruction-cost-investigation-2026-11-16)
records shorter measured interrupt spans after its own inbox changes, alongside
the continuing fast-input failure. For this port, the transferable lesson is
to compare full endpoints and untraced controls as well as average sampling
cost: a faster decoder alone does not guarantee correct movement. The receipt
owns the detailed measurements; no game-derived implementation was sent to
ClasSICK, and neither project's result establishes physical behavior.

## Failed-drain recovery replay - 2026-11-17

The new original test, `scripts/test_title_recovery.py`, closes a checkpoint gap
in the earlier timeout/retry endpoint checks. It builds the existing emitter
title unchanged from port base `5487acb132f6c50eb5e6029ff086c3fd251da3a0`.
ROM SHA-256 remains
`c693dcfebf1c9c4b1048abc50503f3462985a926dedc57fe6c5d1da25bfb7d72`
(65,536 bytes, emitter end 36,502). No production ROM code changed.

Seven bounded, headless BootHush runs cover a recording, independent repeat,
mouse replay, endpoint without capture/witness observation, two input controls
and one defective test-only ROM. Each observed run captures 13 requested
cycle boundaries and the complete 86-byte diagnostic block. Input is scheduled
in guest cycles; no visible window, host input injection or human test is used.

| Requested cycle | Required observation in the accepted scenario |
| ---: | --- |
| 1,500,000 | Title ready after a modeled 16-pixel move inside Start |
| 2,400,000; 2,800,000; 3,500,000 | Failed drain, timeout count 1; held click cannot retry |
| 3,900,000 | Released click rearms; title remains failed until fresh press |
| 4,800,000; 5,500,000; 6,500,000 | Gameplay ready; title-held key does not move P1; P2 unchanged |
| 7,500,000 | Fresh P1 key is held and moves P1 |
| 8,500,000; 9,500,000 | Release clears P1 held state; P2 remains unchanged |

The first keyboard transfer stalls once at modeled cycle 2,000,894. The test
queues its title-time key at 3,200,000, after failure, so the failed transfer
cannot consume that key and conceal a missing retry drain. A fresh click at
4,000,000 drains it before gameplay. Successful handoff resets the timeout
counter, so a final counter alone would miss this failure. The key stays held
until 6,000,000; only a fresh make at 7,000,000 moves P1. Final P1 position is
37,088 in the prototype's fixed-point units; P2 stays at 43,008.

Recording, independent repeat and replay have identical capture cycles,
complete diagnostic snapshots, all captured PBM bytes, final PBM bytes and
keyboard witness bytes. All four keys are accepted and delivered in order;
there are no pending, rejected or dropped scheduled keys, missing captures or
pending modeled mouse events. The observer-free endpoint matches status,
cycles, PC, VBL, mouse totals, fault result, memory and final pixels. Original
pixel oracles also check stable title/gameplay samples; transitional state 4
frames are compared across runs without claiming an atomic redraw.

Omitting the fresh mouse press keeps the title failed. Omitting the fresh key
make keeps gameplay stationary. A test-only mutation that leaves the accepted
click armed causes an unintended held-button retry; the checkpoint oracle
rejects it. The production ROM hash is checked again after testing.

BootHush source identity supplied for this executable is `238f7e7`;
executable SHA-256:
`9dc2f28425bafd10114cfde9ab5c439d61234873854cfa1c211cdcfb26bda82d`.
The final report includes exact commands, source hashes and each full guest
result at `out/title-recovery-20261117-b/report.json`.
Recorded mouse trace SHA-256 is
`1c85a29bd2d2b60f66361cfe976f1f6b1e758cbd70a03e13ac96a3a0e847711d`;
its captured frame-series SHA-256 is
`9f8a3171c9790bd338b7b88e955e5db516a89fa060d6b97efa313e09a9fc27f7`.
Earlier development probes and the first passing test receipt remain in
neighboring ignored output directories.

The same executable also passes all 22 existing title scenarios, during-motion
and handoff replay (`out/title-recovery-baseline-20261117-a/summary.json`),
plus all 160 phase/boundary cases and the wrong-sign mutation control
(`out/title-recovery-axis-20261117-a/report.json`). Reproduce from the
repository root with a fresh output directory:

```powershell
python -B scripts/test_title_recovery.py --boothush C:/Repos/boothush/out/pointer-testing-20261117/boothush.exe --output out/NEW-RECOVERY
```

This is modeled recovery evidence for the existing emitter title. It does not
qualify native-jab ROM recovery, physical input, human pointer feel, hardware,
a complete playable game or the paired ClasSICK release. Only the independent
measurement method is reusable across projects; game-derived code stays here.
