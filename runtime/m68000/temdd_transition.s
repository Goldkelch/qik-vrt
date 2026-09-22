| TEMDD v0.1 fixed-relation transition kernel, Motorola 68000
| D0 = event: 0 unknown, 1 evidence, 2 blocker; other values fail closed to HOLD.
| returns D0 = state: 0 HOLD, 1 CONTINUE, 2 SUCCESSOR_REQUIRED
        .text
        .globl  temdd_transition_m68000
        .globl  temdd_transition_call
temdd_transition_m68000:
        cmpi.b  #2,%d0
        beq.s   .blocker
        cmpi.b  #1,%d0
        beq.s   .evidence
        moveq   #0,%d0
        rts
.evidence:
        moveq   #1,%d0
        rts
.blocker:
        moveq   #2,%d0
        rts

| C ABI adapter used only by the executable differential test.
temdd_transition_call:
        move.l  4(%sp),%d0
        bra.s   temdd_transition_m68000
