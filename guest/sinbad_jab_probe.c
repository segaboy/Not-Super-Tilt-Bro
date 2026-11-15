/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
#include "sinbad_jab_chain.h"

/* Six deterministic controller timelines for an isolated PAL jab slice. */
static uint8_t scripted_input(unsigned scenario, unsigned tick)
{
    if (scenario==0) return NSTB_JAB_ONLY;
    if (scenario==1 || scenario==5) {
        if (tick==1 || tick==11 || (scenario==5 && tick==21)) return NSTB_JAB_NONE;
        if (scenario==5 && tick==22) return NSTB_JAB_OTHER;
        return NSTB_JAB_ONLY;
    }
    if (scenario==2) return tick==2 ? NSTB_JAB_ONLY : NSTB_JAB_NONE;
    if (scenario==3) return tick>=10 ? NSTB_JAB_ONLY : NSTB_JAB_NONE;
    if (scenario==4) {
        if (tick==1 || tick==11) return NSTB_JAB_NONE;
        return tick<11 ? NSTB_JAB_OTHER : NSTB_JAB_ONLY;
    }
    return NSTB_JAB_NONE;
}

__attribute__((noreturn)) void port_entry(volatile uint8_t *out)
{
    unsigned scenario,tick;
    *out++='S'; *out++='J'; *out++='B'; *out++=1;
    for (scenario=0;scenario<6;++scenario) {
        nstb_jab_chain a,b;
        nstb_jab_begin(&a);nstb_jab_begin(&b);
        for (tick=1;tick<=80;++tick) {
            nstb_jab_tick(&a,scripted_input(scenario,tick));
            nstb_jab_tick(&b,NSTB_JAB_ONLY);
            *out++=a.state; *out++=a.clock; *out++=a.previous_input;
            *out++=b.state; *out++=b.clock; *out++=b.previous_input;
        }
    }
    *out++=0xa5;*out=0x5a;
    for (;;) { }
}
