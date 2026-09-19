/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Bounded C90 executable witness for the MC68000-visible QIK-VRT boundary. */
#include <stdio.h>

enum qikvrt_boundary_d0 {
    QIKVRT_NOOP = 0,
    QIKVRT_HOLD = 1,
    QIKVRT_REOBSERVE = 2,
    QIKVRT_REQUEST_AUTHORITY = 3
};

enum qikvrt_effect_state {
    QIKVRT_EFFECT_NACK = 0,
    QIKVRT_EFFECT_ACK_CONTINUE = 1,
    QIKVRT_EFFECT_ACK_ISOLATE = 2,
    QIKVRT_EFFECT_ACK_BLOCK = 3,
    QIKVRT_EFFECT_ACK_DONE = 4
};

static int ordinary_release(int effect_state)
{
    return effect_state == QIKVRT_EFFECT_ACK_DONE;
}

static int d0_valid(int value)
{
    return (value & ~3) == 0;
}

int main(void)
{
#ifdef __m68k__
    puts("ARCH=MC68000_FAMILY");
#else
    puts("ARCH=NON_M68K");
#endif
    if (QIKVRT_NOOP != 0 || QIKVRT_HOLD != 1 || QIKVRT_REOBSERVE != 2 ||
        QIKVRT_REQUEST_AUTHORITY != 3) return 10;
    if (!d0_valid(QIKVRT_NOOP) || !d0_valid(QIKVRT_REQUEST_AUTHORITY) || d0_valid(4)) return 11;
    if ((1 + 2) != QIKVRT_REQUEST_AUTHORITY) return 12;
    if (QIKVRT_EFFECT_NACK != 0 || QIKVRT_EFFECT_ACK_CONTINUE != 1 ||
        QIKVRT_EFFECT_ACK_ISOLATE != 2 || QIKVRT_EFFECT_ACK_BLOCK != 3 ||
        QIKVRT_EFFECT_ACK_DONE != 4) return 13;
    if (ordinary_release(QIKVRT_EFFECT_NACK) || ordinary_release(QIKVRT_EFFECT_ACK_BLOCK)) return 14;
    if (!ordinary_release(QIKVRT_EFFECT_ACK_DONE)) return 15;
    puts("D0_BOUNDARY_CODES=0,1,2,3");
    puts("D0_BINARY_WEIGHTS=1,2");
    puts("D0_COMPOSITION_3=1+2");
    puts("NEXT_ORTHOGONAL_WEIGHT=4");
    puts("EFFECT_ACK_CODES=0,1,2,3,4");
    puts("EFFECT_ACK_REGISTER=D4");
    puts("OVERLAY_BANKS=4");
    puts("ORDINARY_RELEASE=EFFECT_ACK_DONE_ONLY");
    return 0;
}
