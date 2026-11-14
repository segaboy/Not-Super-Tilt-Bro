# Two-character native experiment — 2026-11-14

## Question and scope

Can a 64 KiB native replacement ROM exercise two separate modeled inputs and
display independently moving, jumping and attacking figures without stale
framebuffer regions? This is a port software test in BootHush, not a physical
Mac test, complete game, source-matched NES comparison or ClasSICK release test.
The owner subsequently directed mouse-driven title/start and keyboard play;
this experiment starts directly in the arena and does not yet implement that UI.

The earlier source-derived movement, jump and jab inputs, exact source hashes,
license and independent approximations are recorded in [movement](movement-evidence.md),
[jump](jump-slice-evidence.md), [jab](jab-training-evidence.md) and
[provenance](provenance.md). The second figure and presentation are original
geometric art, not upstream sprites. Neither game source nor this game-informed
implementation is automatically eligible as a ClasSICK implementation input.

## Reproduction

Base port commit before this change: `0fbde21`. BootHush executable SHA-256
`1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`.
Generated 65,536-byte ROM SHA-256
`02f68482e598a90c57f22d8811459d1791f138bc47230ebf6e77f0da16df5a9c`;
emitted code and vectors occupy through byte offset 29,808, not a complete
game size measurement. Commands use new output directories and no live window:

```powershell
$py = 'C:\ClasSICK\bootstrap-clean-source-verified\.tools\llvm-mingw\llvm-mingw-20260908-ucrt-x86_64\python\bin\python.exe'
$bh = 'C:\Repos\boothush\out\windows\boothush.exe'
& $py -B scripts/test_mac_two_player.py --boothush $bh --keep out/NEW-TWO-PLAYER-TEST
& $py -B scripts/capture_two_player_evidence.py --boothush $bh --output out/NEW-TWO-PLAYER-MEDIA
```

The retained local run is `out/two-player-experiment-20261114-e`, with the
per-case commands, state samples, keyboard witnesses and frame series. Media
under ignored `out/two-player-media-20261114` includes 12 guest-only PBMs and
PNGs, 33-frame 30-fps Y4M, GIF and MP4, command and manifest. The GIF SHA-256
is `9ca189ca4184f28ab727775ce49722695d05ef4c53247b024c550b725279225d`.
The inputs are scheduled modeled key transitions; they are not human testing.

## Observations and limits

All 25 bounded scenarios passed. They cover both directions and bounds, two
held directions and restoration, simultaneous movement, crossing/overlap,
both attack directions and misses, attack lock, held attack, two separate
hits, simultaneous trade, each airborne evasion, simultaneous jumps, held
jump, running jump and a second jump. Samples compare every 512x342 pixel to
an independent rendering oracle. Consecutive serviced VBL samples without
input delivery also check P2 movement, attack and jump state against a local
reference; the two sparse bound tests have no adjacent-VBL comparisons.
No witness reported rejected, dropped or pending scheduled keys. The original
movement, jump and combat profiles passed their regression tests and retained
their previously recorded ROM hashes.

Modeled key codes 0/1/2/3 are P1 right/left/jump/attack; 4/5/7/6 are P2
right/left/jump/attack. These are model codes, not a verified physical-keyboard
layout or rollover guarantee. P2 horizontal motion is a local fixed one-pixel
step, unlike P1's source-informed acceleration. Both jumps reuse the prior
source-informed squat/power parameters with local gravity/integration. Jabs
are local 24-count approximations: the active pose appears at clocks 7–8,
with one hit check at 7 over a 16–32-pixel facing interval, only while the
target is at floor height. Each hit adds two to an eight-bit wrapping counter;
the visible meter saturates at eight cells. Both attacks can hit in one exchange.
Composition overwrites byte-aligned regions in P1, P2, P2-meter, P1-meter
order; it is not a general sprite compositor. No knockback, stocks, match end,
menu, sound, physical input qualification or full game exists in this slice.

The original-art VBL 28 PBM was also compared with a separately generated
286 EGA bitmap diagnostic. All canvas and margin pixels matched in BootHush;
the 286 did not execute this ROM or game logic. See BootHush's
`docs/mac-pc286-bitmap-20261114.md` for the canonical cross-project receipt.
Neither this display observation nor the source-derived port is an admitted
ClasSICK implementation specification or release qualification.
