/* Independent MC68000 first-match evaluator and consumer admission.
 * Linux m68k C ABI: three unsigned longs on stack, result in d0.
 * Only caller-saved d0/d1/a0/a1 are used.
 */
    .text
    .globl full_core
full_core:
    move.l 8(%sp),%d0
    cmpi.l #5,%d0
    bcc rejected
    move.l 12(%sp),%d1
    cmpi.l #5,%d1
    bcc rejected
    move.l 4(%sp),%d0
    btst #16,%d0
    bne blocked
    btst #12,%d0
    bne blocked
    btst #1,%d0
    beq nack
    btst #2,%d0
    beq nack
    btst #17,%d0
    bne blocked
    cmpi.l #4,%d1
    beq blocked
    cmpi.l #3,%d1
    beq isolated
    cmpi.l #2,%d1
    bne continued
    tst.l 8(%sp)
    beq continued
    andi.l #61439,%d0
    cmpi.l #61439,%d0
    bne continued
    moveq #2,%d0
    rts
rejected:
    moveq #5,%d0
    rts
blocked:
    moveq #4,%d0
    rts
nack:
    moveq #0,%d0
    rts
isolated:
    moveq #3,%d0
    rts
continued:
    moveq #1,%d0
    rts

    .globl full_admit
full_admit:
    moveq #0,%d0
    cmpi.l #2,4(%sp)
    bne admit_end
    cmpi.l #2,8(%sp)
    bne admit_end
    cmpi.l #511,12(%sp)
    bne admit_end
    moveq #1,%d0
admit_end:
    rts
    .section .note.GNU-stack,"",@progbits
