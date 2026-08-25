; QIK-VRT Lean-proved finite gate kernel — Motorola 68000
; ABI v1
; IN : D0 bit0 = PASS certificate present
;      D0 bit1 = BLOCK certificate present
; OUT: D0 = 0 CONTINUE, 1 PASS, 2 BLOCK
;
; BLOCK has priority over PASS. This is the finite executable projection of
; QIKVRT.evaluateGate proved in QIKVRTFormalization/M68000Kernel.lean.
;
; This source does not claim physical Motorola 68000 execution.

        btst    #1,d0
        beq.s   .no_block
        moveq   #2,d0
        rts
.no_block:
        btst    #0,d0
        beq.s   .continue
        moveq   #1,d0
        rts
.continue:
        moveq   #0,d0
        rts
