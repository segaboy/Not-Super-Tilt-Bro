/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
/* Sinbad's PAL ground velocity merge, including momentum carried from a jump. */
#include "sinbad_movement.h"

void sinbad_movement_step(uint16_t *position, int16_t *velocity, int8_t direction)
{
    int32_t current = *velocity;
    int32_t target = direction < 0 ? -512 : direction > 0 ? 512 : 0;
    int32_t step = direction ? 64 : 96;
    int32_t difference = target - current;
    if (difference > step)
        difference = step;
    else if (difference < -step)
        difference = -step;
    current += difference;
    *velocity = (int16_t)current;
    *position = (uint16_t)(*position + (uint16_t)current);
}
