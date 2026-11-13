# Sinbad PAL running-entry slice

This is an isolated translation of part of the game state machine, exercised by
a diagnostic ROM. It is not a playable game, a complete movement mechanic, or
a demonstration on physical hardware.

## Source and scope

The reviewed local Super Tilt Bro checkout is commit
`b132fd25add46f816e04be64c434386743b84b8b`. Its `std_running.asm` enters the
running state, records the direction, and initializes horizontal velocity with
the sign selected by that direction. Its running input path avoids restarting
the state for the same direction and restarts it when the direction changes.
`game-mod/characters/sinbad/states.asm` specifies a PAL initial speed of
`0x0100` in signed 8.8 notation; its idle entry does not itself write velocity.
The source's animation and input dispatch are not included in this slice.

The local checkout's SHA-256 file hashes are:

| Source file | SHA-256 |
| --- | --- |
| `game/templates/characters/std_running.asm` | `538f349a0365a5adee4e2a798ab311d88e3e9103eef02cd9a5ab0a556be0f790` |
| `game/templates/characters/std_idle.asm` | `ffb1bb53e9ddf07ef4249654f5a9754cf3ef29340a8f604178794f3638f0fd5e` |
| `game-mod/characters/sinbad/states.asm` | `cc4bf3e2550e5877ab9290e95f75d70b3a4ac1bab9457aff03991ffa6c494c55` |
| `game/macros.asm` | `b42c950d41cafa6df076c3884ee25408f2f6dc0eb0f69bad3b7908bd90ce4072` |

The diagnostic adapter maps a modeled right or left key press to entering or
restarting that narrow transition. Right writes `0x0100`; left writes `0xff00`.
It uses local normalized state values (`0` idle, `1` running), not the original
game's state identifiers. Repeated same-direction input leaves the entry count
unchanged. A release puts the adapter in idle and preserves velocity, which
mirrors the relevant source idle-entry write behavior but is not the complete
original key dispatch. The overlapping-key reversal check directly exercises
the isolated transition; it does not establish source simultaneous-input
behavior or physical M0110 rollover.

The placeholder figure moves by a discrete eight-pixel step on each press,
within three positions. That picture does **not** use the stored velocity and
is not evidence of original game physics. Acceleration, maximum speed, position
integration, friction, animation, per-frame updates, complete input handling,
attacks, collision, and the game's characters and assets remain unimplemented.
The exact source revision of the separately obtained beta ROM is unknown;
its observed pictures cannot validate this translation.

## ROM and diagnostic layout

`scripts/build_mac_run_transition.py` extends the existing independently
authored controls probe and ClasSICK-derived reset path. A Python emitter writes
the 68000 instruction encodings; this is a small auditable bootstrap, not a
general 68000 compiler or a replacement for an assembler/linker toolchain.
The ROM is padded to exactly 65,536 bytes and the builder checks its size. The
tested image has SHA-256
`3c0232abce9c096aef41065bfa9da31f92ca8832b36aaa9afc6d1dca1560edc3`;
its occupied image extends through offset 7,139 inclusive. This is not a full
game ROM budget. The modeled machine has 131,072 bytes RAM; its 21,888-byte
framebuffer is observed at `0x1a700`, but no complete RAM/stack budget has
been established.

At RAM `0x0b00`, the probe stores the four-byte `NST3` marker, four-byte ready
value, then one byte each for position, last recognized reply, press count,
release count, normalized state, direction (`0` left/`1` right), signed 8.8
velocity high byte, velocity low byte, and running-entry count. These bytes
are diagnostic state, not source-game addresses. Tests wait by fixed modeled
time and verify the ready value at each capture rather than using a separate
readiness-triggered capture.

The Super Tilt Bro source is distributed with WTFPL v2; its notice is retained
in `third_party/super-tilt-bro-LICENSE.txt`. Attribution and the separately
applicable ClasSICK GPL terms are in [provenance](provenance.md). No original
game art, Apple executable code or Apple assets are included. Any research
proposed for ClasSICK remains subject to its clean-room and source-eligibility
process; this source-derived game code is not automatically eligible.
