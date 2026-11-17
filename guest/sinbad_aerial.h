/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
#ifndef NSTB_SINBAD_AERIAL_H
#define NSTB_SINBAD_AERIAL_H
#include <stdint.h>

void sinbad_aerial_step(uint16_t *position, int16_t *velocity, int8_t direction);
#endif
