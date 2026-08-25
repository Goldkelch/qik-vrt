; QIK-VRT Lean v2 D0/D2/D3 step kernel
; D0 = validated decision 0..3 (preserved on valid input)
; D2 = IED phase: 0 INTELLIGENCE, 1 EVIDENCE, 2 DEVELOPMENT
; D3 = stable semantic witness (never written)
; invalid D2 fails closed with D0=1 HOLD

        cmpi.b  #2,d2
        bhi.s   .invalid
        beq.s   .wrap
        addq.b  #1,d2
        rts
.wrap:
        moveq   #0,d2
        rts
.invalid:
        moveq   #1,d0
        rts
