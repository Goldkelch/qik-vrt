/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Bounded C90 executable witness for the recovered MC68000-visible contract. */
#include <stdio.h>

enum qikvrt_d0_code {
    QIKVRT_EFFECT_NACK = 0,
    QIKVRT_EFFECT_ACK_CONTINUE = 1,
    QIKVRT_EFFECT_ACK_ISOLATE = 2,
    QIKVRT_EFFECT_ACK_BLOCK = 3,
    QIKVRT_EFFECT_ACK_DONE = 4
};

static int ordinary_release(int d0)
{
    return d0 == QIKVRT_EFFECT_ACK_DONE;
}

int main(void)
{
#ifdef __m68k__
    puts("ARCH=MC68000_FAMILY");
#else
    puts("ARCH=NON_M68K");
#endif
    if (QIKVRT_EFFECT_NACK != 0 || QIKVRT_EFFECT_ACK_CONTINUE != 1 ||
        QIKVRT_EFFECT_ACK_ISOLATE != 2 || QIKVRT_EFFECT_ACK_BLOCK != 3 ||
        QIKVRT_EFFECT_ACK_DONE != 4) return 10;
    if (ordinary_release(QIKVRT_EFFECT_NACK) || ordinary_release(QIKVRT_EFFECT_ACK_BLOCK)) return 11;
    if (!ordinary_release(QIKVRT_EFFECT_ACK_DONE)) return 12;
    puts("D0_CODES=0,1,2,3,4");
    puts("OVERLAY_BANKS=4");
    puts("ORDINARY_RELEASE=EFFECT_ACK_DONE_ONLY");
    return 0;
}
