# VBL-paced Sinbad movement experiment — 2026-11-14

Coordination regression, later 2026-11-14: checkout `3db162d178f2706c324c19d7e52cd7597a6fe189` reran `scripts/test_mac_movement.py --boothush C:\Repos\boothush\out\windows\boothush.exe --keep out\coordination-movement-20261114`. The suite passed with ROM SHA-256 `bf7a065eb4d9a8141b7199ebe41eeb6d7abfef74f52d1d5e08948f5470294dd9` and BootHush executable SHA-256 `1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`. Full generated observations remain in that ignored output directory. This repeats the existing modeled behavior; it does not establish hardware timing or game completion. The separately tested BootHush x64 firmware-model work at `7b11f985beaacd7151c73ab84dfbd7cfe85ee49a` has no effect on this Mac executable; its scope is documented in `C:\Repos\boothush\docs\x64-efi-memory-evidence-20261114.md`.

This is a native, independently booting Mac ROM with one source-derived
horizontal movement slice and original diagnostic art. It is **not a playable
Super Tilt Bro match**, a source-matched NES comparison, or a physical Mac
result. BootHush is the only emulator used here.

## What was implemented

`scripts/build_mac_movement.py` generates a 65,536-byte 68000 replacement ROM
using the existing ClasSICK-derived reset and vector relocation. Its original
platform and figure are generated in the ROM. Modeled keys 0 and 1 select right
and left. A press enters a run with signed 8.8 velocity `+0x0100` or `-0x0100`;
each movement tick approaches `+0x0200` or `-0x0200` by `0x0040`. Releasing
the active direction approaches zero by `0x0060` per tick without overshooting.
Velocity is integrated into an unsigned 8.8 position, with local diagnostic
bounds `0x1000..0xe000`, and the sprite is drawn at the corresponding pixel.
Input handling, arena bounds, drawing, and tick ordering are this project's
adaptations. They are not a complete translation of game inputs, animation,
collisions, stage geometry, or the original game loop.

The velocity constants and movement-toward-target behavior were reviewed in
Super Tilt Bro commit `b132fd25add46f816e04be64c434386743b84b8b`, especially
`game-mod/characters/sinbad/states.asm`,
`game/templates/characters/std_running.asm`,
`game/templates/characters/std_friction_routines.asm`, and
`game/logic/utils.asm`. The existing source attribution and WTFPL notice are
in [provenance](provenance.md). Local checkout file SHA-256 values for the two
additional files are `bc6fd5308b70439b93f11210bd778b0315d6f3925635395d6f2457ca48ee8107`
(friction template) and
`7bc4f603752f6fa8deeef2bc9a897e4d61c83c2a85bfcc064bbf16c850b7961b`
(`utils.asm`). This isolated implementation is not a claim that all source
physics or source ordering is reproduced.

## Timing and limits

The guest polls the modeled VIA interrupt flag's CA1 bit for VBL, clears the
flag, polls one keyboard reply, and updates on five out of six serviced VBLs.
BootHush `f41ddc5` models a VBL every 130,240 CPU cycles with a 7,833,600 Hz
clock: roughly 60.15 modeled VBLs/second and 50.12 movement ticks/second before
missed/coalesced events. This 5/6 approximation is **not** precise PAL pacing
or a validated original-Mac timing specification. A modeled one-bit VBL flag
does not count multiple events while the guest is busy. The polling loop is
bounded, not an interrupt-driven keyboard driver. Simultaneous holds, physical
keyboard rollover, all game input combinations and real-world frame timing
remain unverified.

The ROM's output has SHA-256
`bf7a065eb4d9a8141b7199ebe41eeb6d7abfef74f52d1d5e08948f5470294dd9`;
it occupies 7,314 bytes through offset 7,313 inclusive and is padded to
65,536 bytes. This is not a complete game-size estimate. The tested model
has 131,072 bytes of RAM, with a 21,888-byte live framebuffer at `0x1a700`.
The initial stack pointer is `0x4000`. A complete stack, memory ownership,
sound, asset and performance budget remains open.

At RAM `0xb00`, the 24-byte `NST4` diagnostic block contains a four-byte
signature and four-byte ready value, then held direction, last reply, 16-bit
entry count, 16-bit tick count, signed 16-bit velocity, unsigned 16-bit
position, 16-bit serviced-VBL count, one-byte pacing phase, one reserved byte,
and 16-bit keyboard timeout count. Words are big-endian. These are local
diagnostics, not Super Tilt Bro memory addresses.

## BootHush observations

Source commit `f41ddc5` was clean; the CMake/Ninja dry run reported no pending
work. The tested Windows executable SHA-256 was
`1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`.
`scripts/test_mac_movement.py` passed neutral, right and left hold/release,
exact right replay, direct reversal, both movement bounds, and two injected
keyboard fault/recovery cases. At every sampled point it checked all 512x342
framebuffer pixels against independently reconstructed original art. For
intervals without a delivered key, a Python reference model independently
checked VBL pacing and signed fixed-point state; it checked 26 neutral, 24
right, 24 left and 23 reversal intervals. Witnesses reported no dropped or
rejected input and no pending key events. A `cycle_limit` result indicates a
bounded modeled run, not hardware success.

For the right case, the press was scheduled at cycle 600,000 and released at
2,600,000; the modeled guest received replies at cycles 697,146 and
2,650,748. Capture occurs before processing input at a common boundary.

| Modeled VBL | Actual cycle | Held | Velocity (8.8) | Position (8.8) | Ticks |
| ---: | ---: | --- | --- | --- | ---: |
| 5 | 651212 | none | `0000` | `8000` | 2 |
| 6 | 781450 | right | `0140` | `8140` | 3 |
| 8 | 1041926 | right | `01c0` | `8480` | 5 |
| 9 | 1172164 | right | `01c0` | `8480` | 5 |
| 10 | 1302410 | right | `0200` | `8680` | 6 |
| 22 | 2865290 | none | `01a0` | `9a20` | 16 |
| 31 | 4037448 | none | `0000` | `9ce0` | 24 |

VBL 9 demonstrates the selected pacing skip. A long right hold reached the
local `e000` position bound; a long left hold reached `1000`. Velocity remains
at its signed running maximum while held against either boundary. The full
machine-readable observations, original PBM sequences and modeled keyboard
and display traces are retained locally under
`out/movement-evidence-f41ddc5-v2/`; generated outputs are excluded from Git.

## ClasSICK-relevant modeled fault experiment

The guest now bounds each VIA shift-register poll to 4,097 loop iterations,
increments a diagnostic timeout counter, resets the shift mode, and retries
on a later serviced VBL. The limit is an implementation choice, not a measured
keyboard timeout. Using BootHush's injected first-`0x14` command fault:

| Modeled fault | Fault cycle | Other witness event | Queued press delivered | Timeouts at VBL 31 | Ticks at VBL 31 |
| --- | ---: | --- | ---: | ---: | ---: |
| Stalled outgoing command | 490500 | — | 700376 | 1 | 22 |
| Suppressed reply | 490500 | Reply suppressed at 515624 | 725500 | 1 | 22 |
| No injected fault | — | — | 697146 | 0 | 24 |

Both injected-fault runs subsequently delivered the scheduled release and
reached zero velocity. This demonstrates recovery **for these two modeled
one-shot faults in this guest**, with missed movement ticks, not physical
keyboard timing or proof that ClasSICK's existing driver recovers. BootHush's
separate ClasSICK keyboard test documents a latched timeout, so these results
are a candidate independent test scenario, not a change to either ClasSICK
repository. Any transfer requires its clean-room/source-eligibility review.
The reset and VIA sequence already derive from ClasSICK; the fault injector and
witnesses are BootHush model behavior, not independent hardware evidence.

## Media and reproduction

The blog media is generated directly from BootHush, with no Apple or original
NES assets. `scripts/capture_movement_blog.py` retains the original silent Y4M,
four raw PBM snapshots, the capture series, manifests, and keyboard/display
witnesses under `out/blog-movement-f41ddc5/`. It converts the same run to a
silent GIF, H.264 MP4 and lossless PNG stills using BootHush's conversion path.
The Y4M has 102 samples at 30 fps beginning at modeled cycle 500,000. Its
3.4-second length is modeled video time. The samples are live framebuffer
copies, not hardware-latched frames; MP4 is lossy. The stills are VBL-indexed:
6 at cycle 781442, 55 at 7163216, 100 at 13024002, and 165 at 21489610.
Press/release replies were delivered at cycles 827354, 9032512, 11116314,
and 20102886 respectively. These images depict placeholder art, not game assets.
`media-sha256.json` identifies each converted file.

From the project directory, using a local Python and the current BootHush:

```powershell
$py = 'C:\Repos\ClasSICK-0.97\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py scripts\test_mac_movement.py --boothush $bh --keep out\movement-evidence-new
& $py scripts\capture_movement_blog.py --boothush $bh --output out\blog-movement-new
```

Both output paths must be new. Current missing capabilities include Mac sound
and synchronized audio, and a usable native 68000 toolchain. A version-matched
NES build remains unavailable due to missing supported build tools and the
local WSL/MSYS access failures. BootHush's new filtered NES witness is useful
once that build and its own symbols exist; it cannot validate the unknown beta
against the reviewed source. The experimental comparison helper likewise
requires an explicit, justified mapping before a source-to-target claim.
