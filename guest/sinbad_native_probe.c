/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* Source-informed movement constants; see docs/movement-evidence.md. */
#include <stdint.h>
#include "sinbad_movement.h"

/* An isolated deterministic diagnostic, not a game loop or hardware driver. */
void port_entry(volatile uint16_t *out)
{
    uint16_t position=0x8000u, opposite_position=0x8000u;
    int16_t velocity=0x0100, opposite_velocity=-0x0100;
    unsigned i;
    out[0]=0x4e43u;out[1]=0x0001u;
    for(i=0;i<10u;++i) {
        sinbad_movement_step(&position,&velocity,i<4u ? 1 : 0);
        sinbad_movement_step(&opposite_position,&opposite_velocity,i<4u ? -1 : 0);
        out[2u+2u*i]=position;out[3u+2u*i]=(uint16_t)velocity;
        out[22u+2u*i]=opposite_position;out[23u+2u*i]=(uint16_t)opposite_velocity;
    }
    out[42]=0xa55au;
    for(;;) { }
}
