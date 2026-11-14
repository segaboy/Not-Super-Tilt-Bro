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
