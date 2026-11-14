/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Copyright (C) 2026 Dean Howell. */
#include <stdint.h>
#include <stdio.h>
#include "../guest/sinbad_movement.h"

struct scenario {
    uint16_t position;
    int16_t velocity;
    int8_t direction;
    uint16_t expected_position;
    int16_t expected_velocity;
};

int main(void)
{
    static const struct scenario cases[] = {
        {0x8000, 0, 1, 0x8040, 0x40},
        {0x8000, 0x1c0, 1, 0x8200, 0x200},
        {0x8000, 0x200, 1, 0x8200, 0x200},
        {0x8000, -0x1c0, -1, 0x7e00, -0x200},
        {0x8000, -0x200, -1, 0x7e00, -0x200},
        {0x8000, 0x100, -1, 0x80c0, 0xc0},
        {0x8000, -0x100, 1, 0x7f40, -0xc0},
        {0x8000, 0x50, 0, 0x8000, 0},
        {0x8000, -0x50, 0, 0x8000, 0},
        {0x8000, 0, 0, 0x8000, 0},
        {0xff00, 0x200, 1, 0x0100, 0x200}
    };
    unsigned i;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        uint16_t position = cases[i].position;
        int16_t velocity = cases[i].velocity;
        sinbad_movement_step(&position, &velocity, cases[i].direction);
        if (position != cases[i].expected_position || velocity != cases[i].expected_velocity) {
            fprintf(stderr, "movement case %u failed: %04x/%d\n", i, (unsigned)position, velocity);
            return 1;
        }
    }
    puts("11 movement cases passed");
    return 0;
}
