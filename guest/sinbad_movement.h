/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
#ifndef NSTB_SINBAD_MOVEMENT_H
#define NSTB_SINBAD_MOVEMENT_H

#include <stdint.h>

/* Input direction is -1, 0, or 1. Positions and velocities use signed 8.8
 * offsets; the caller owns movement bounds, input state, and frame pacing. */
void sinbad_movement_step(uint16_t *position, int16_t *velocity, int8_t direction);

#endif
