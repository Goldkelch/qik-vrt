/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann.
 *
 * Canonical TEMDD terminal predicate for MC68000.
 * Input D0 low byte: bits 0..7 = COMPILE,BIND,RESOLVE,EXECUTE,TEST,OBSERVE,
 * READBACK,ACCEPT. Return D0=1 only when all eight bits are set.
 *
 * This is one bounded cycle predicate. The outer qikvrt_main loop remains
 * potentially unbounded and rebinds the accepted successor before the next
 * cycle. EFFECT_ACK_DONE(subject_n) != PROGRAM_DONE.
 */
        .text
        .globl  temdd_effect_ack_done_m68000
temdd_effect_ack_done_m68000:
        andi.l  #255,%d0
        cmpi.l  #255,%d0
        beq.s   .done
        moveq   #0,%d0
        rts
.done:
        moveq   #1,%d0
        rts

/* C ABI adapter: unsigned long temdd_effect_ack_done_call(unsigned long flags). */
        .globl  temdd_effect_ack_done_call
temdd_effect_ack_done_call:
        move.l  4(%sp),%d0
        bra.s   temdd_effect_ack_done_m68000

        .section .note.GNU-stack,"",@progbits
