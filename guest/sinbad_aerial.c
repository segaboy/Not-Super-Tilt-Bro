/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* PAL horizontal aerial influence; see docs/aerial-control-evidence.md. */
#include "sinbad_aerial.h"

void sinbad_aerial_step(uint16_t *position, int16_t *velocity, int8_t direction)
{
    int32_t current = *velocity;
    int32_t target = direction < 0 ? -0x0100 : direction > 0 ? 0x0100 : 0;
    int32_t step = 7;
    if ((direction > 0 && current < target) || (direction < 0 && current > target))
        step = 0x80;
    if (current < target) {
        current += step;
        if (current > target) current = target;
    } else if (current > target) {
        current -= step;
        if (current < target) current = target;
    }
    *velocity = (int16_t)current;
    *position = (uint16_t)(*position + (uint16_t)current);
}
