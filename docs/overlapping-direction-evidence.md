<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Dean Howell. -->
# Overlapping direction input — 2026-11-14

The existing VBL-paced movement slice stored only the most recently selected direction. Pressing right, then left, then releasing left incorrectly left the character idle even if right was still held. The port now tracks both modeled key states; the most recently pressed distinct direction controls movement, releasing the active direction restores the other held direction, and releasing the inactive direction leaves the active one unchanged. A duplicate make for a held key is ignored. Restoring a direction re-enters its run at the existing initial velocity. This input policy is original to this project; it is not a finding about the source game's input dispatch, Mac keyboard rollover, or physical hardware.

The 24-byte `NST4` diagnostic uses the formerly reserved byte at offset 21 as a bitmask: bit 0 is right and bit 1 left. The existing held byte remains 0=none, 1=right, 2=left. The test ROM SHA-256 is `3e69619032fc71bed6e1afe3cf09c4e7c0436000c6a56bdd664d373481f56abd`, length 65,536, occupied through offset 7,465. BootHush executable SHA-256 is `1f306c427d1a8c42b9d547b2b25a424e4b4e6a389a52ae5861d030e0fe43bc25`; this is an emulator observation, not a hardware result. Full generated state, every sampled framebuffer, and keyboard/display witnesses are in ignored `out/overlap-direction-20261114-v3`.

The suite passed neutral, both directions, repeat, reversal, four overlap/release orders, both bounds and two one-shot keyboard fault scenarios. At each sampled frame it compared all 512x342 pixels with independently reconstructed original placeholder art; between key deliveries the existing reference model checks the fixed-point motion and pacing. Both input orders were tested. For right-down, left-down, left-up, right-up, the guest delivered replies at cycles 697146, 1739066, 2650712, and 3692662. It observed masks 1, 3, 1 and 0, restored right with entry count 3, and reached zero velocity by VBL 41. Releasing right while left was active retained left and entry count 2; the mirrored sequences produced the corresponding inverse results. No keyboard-witness rows were dropped, rejected or pending in these bounded scenarios. The first attempt requested more capture points than BootHush allows and was rejected before execution; the corrected final run uses at most 32.

Reproduce with a new output directory:

```powershell
python -B scripts/test_mac_movement.py --boothush C:/Repos/boothush/out/windows/boothush.exe --keep out/overlap-direction-new
```

The source-derived Sinbad velocity/friction constants and their upstream provenance remain as documented in [movement evidence](movement-evidence.md) and [provenance](provenance.md). These tests do not establish a full input table, source-matched NES behavior, physical rollover, 128K memory budget, attacks, collision or a playable match. The input policy and source-game-derived ROM are not implementation inputs to ClasSICK; the abstract test question can be reviewed separately under its clean-room policy.
