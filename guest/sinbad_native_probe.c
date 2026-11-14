/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* Source-informed movement constants; see docs/movement-evidence.md. */
#include <stdint.h>

/* An isolated deterministic diagnostic, not a game loop or hardware driver. */
void port_entry(volatile uint16_t *out)
{
    uint16_t position=0x8000u;
    int16_t velocity=0x0100;
    unsigned i;
    out[0]=0x4e43u;out[1]=0x0001u;
    for(i=0;i<10u;++i) {
        if(i<4u) {
            if(velocity<0x0200)velocity=(int16_t)(velocity+0x0040);
        } else if(velocity>0) {
            velocity=(int16_t)(velocity-0x0060);
            if(velocity<0)velocity=0;
        }
        position=(uint16_t)(position+(uint16_t)velocity);
        out[2u+2u*i]=position;out[3u+2u*i]=(uint16_t)velocity;
    }
    out[22]=0xa55au;
    for(;;) { }
}
