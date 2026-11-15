/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* Sinbad PAL jab-state/input adaptation; see docs/jab-chain-evidence.md. */
#include "sinbad_jab_chain.h"

void nstb_jab_begin(nstb_jab_chain *jab)
{
    jab->state=NSTB_JAB_FIRST;
    jab->clock=24;
    jab->previous_input=NSTB_JAB_ONLY;
}

void nstb_jab_tick(nstb_jab_chain *jab, uint8_t input)
{
    uint8_t threshold;
    if (jab->state==NSTB_JAB_DONE) return;
    --jab->clock;
    if (jab->clock==0) {
        jab->state=NSTB_JAB_DONE;
        return; /* idle-state input dispatch is deliberately outside this slice */
    }
    if (input==jab->previous_input) return;
    if (jab->state==NSTB_JAB_THIRD) {
        if (input==NSTB_JAB_NONE) jab->previous_input=input;
        return;
    }
    threshold=(jab->state==NSTB_JAB_FIRST)?14:16;
    if (jab->clock>threshold) {
        if (input==NSTB_JAB_NONE) jab->previous_input=input;
        return;
    }
    if (input==NSTB_JAB_ONLY) {
        ++jab->state;
        /* Upstream initializes both the second and third states from the
         * second animation's PAL duration. */
        jab->clock=26;
    }
    jab->previous_input=input;
}
