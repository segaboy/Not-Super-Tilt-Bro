/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* Source-informed constants; attribution is in docs/movement-evidence.md. */
#include "sinbad_movement.h"

void sinbad_movement_step(uint16_t *position, int16_t *velocity, int8_t direction)
{
    int16_t v = *velocity;
    if (direction > 0) {
        if (v < 0x0200) v = (int16_t)(v + 0x0040);
    } else if (direction < 0) {
        if (v > -0x0200) v = (int16_t)(v - 0x0040);
    } else if (v > 0) {
        v = (int16_t)(v - 0x0060);
        if (v < 0) v = 0;
    } else if (v < 0) {
        v = (int16_t)(v + 0x0060);
        if (v > 0) v = 0;
    }
    *velocity = v;
    *position = (uint16_t)(*position + (uint16_t)v);
}
