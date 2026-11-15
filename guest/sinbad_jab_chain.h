/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
#ifndef NSTB_SINBAD_JAB_CHAIN_H
#define NSTB_SINBAD_JAB_CHAIN_H

#include <stdint.h>

/* Input values are normalized port-local symbols, not Macintosh key codes. */
enum { NSTB_JAB_NONE=0, NSTB_JAB_ONLY=1, NSTB_JAB_OTHER=2 };
enum { NSTB_JAB_DONE=0, NSTB_JAB_FIRST=1, NSTB_JAB_SECOND=2, NSTB_JAB_THIRD=3 };

typedef struct {
    uint8_t state;
    uint8_t clock;
    uint8_t previous_input;
} nstb_jab_chain;

/* Enter the first PAL jab after its initiating input has been consumed. */
void nstb_jab_begin(nstb_jab_chain *jab);
/* Advance one playable PAL tick. Idle re-entry is outside this component. */
void nstb_jab_tick(nstb_jab_chain *jab, uint8_t input);

#endif
