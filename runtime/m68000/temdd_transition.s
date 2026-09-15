; TEMDD v0.1 fixed-relation transition kernel, Motorola 68000
; D0 = event: 0 unknown, 1 evidence, 2 blocker
; returns D0 = state: 0 HOLD, 1 CONTINUE, 2 SUCCESSOR_REQUIRED
        cmpi.b  #2,d0
        beq.s   .blocker
        cmpi.b  #1,d0
        beq.s   .evidence
        moveq   #0,d0
        rts
.evidence:
        moveq   #1,d0
        rts
.blocker:
        moveq   #2,d0
        rts
