; QIK-VRT Lean-v2 Authority/Mirror recoveryChoice kernel
; IN D0.b = CutPoint 0..6
; OUT D0 = 0 predecessor, 1 successor, 2 HOLD
; Invalid cutpoint bytes fail closed to HOLD.

        cmpi.b  #6,d0
        bhi.s   .invalid
        cmpi.b  #4,d0
        bcc.s   .successor
        moveq   #0,d0
        rts
.successor:
        moveq   #1,d0
        rts
.invalid:
        moveq   #2,d0
        rts
