# Mouse title and keyboard-play experiment — 2026-11-14

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
