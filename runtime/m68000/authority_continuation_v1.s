/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Motorola 68000 projection of QIKVRT authority continuation.
 * ABI: d0=current state, d1=kind, d2=exact_head, d3=approved, d4=review_exact_head.
 * result d0: 0 WAITING_PRODUCTIVELY, 1 STALLED, 2 PROGRESS.
 */
        .text
        .globl qikvrt_authority_continue_m68000
qikvrt_authority_continue_m68000:
        tst.l   %d2
        beq.s   stalled
        cmpi.l  #1,%d1
        bne.s   done
        tst.l   %d3
        beq.s   done
        tst.l   %d4
        beq.s   done
        moveq   #2,%d0
        rts
stalled:
        moveq   #1,%d0
done:
        rts
