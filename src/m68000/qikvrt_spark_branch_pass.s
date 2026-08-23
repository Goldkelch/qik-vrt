; SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
; Copyright 2026 Ingolf Lohmann.
;
; QIK-VRT virtual Spark branch-work closure kernel — Motorola 68000
;
; Input D0.b flags:
;   bit 0 IMPLEMENTED
;   bit 1 VERIFIED
;   bit 2 PERSISTED
;   bit 3 REOBSERVED
;   bit 4 STALE_EVIDENCE
;   bit 5 AUTHORITY_REQUIRED
;   bit 6 AUTHORITY_PRESENT
;   bit 7 UNCLASSIFIED_REMAINDER
; Input D3.b: stable work-ring witness, preserved exactly.
;
; Output D0 (existing four-state decision ABI):
;   0 NOOP / complete
;   1 HOLD
;   2 REOBSERVE
;   3 REQUEST_AUTHORITY
; Output D1: 1 iff this bounded branch work ring is complete, else 0.
; Output D2: 1 iff machine-owned reobservation remains active, else 0.
; D3 is never written.
;
; One invocation consumes exactly one bounded branch-work capsule. It does not
; perform a Git merge or any external effect.

qikvrt_spark_branch_pass:
        btst    #7,d0
        bne.s   .hold
        btst    #4,d0
        bne.s   .reobserve
        btst    #5,d0
        beq.s   .ready
        btst    #6,d0
        beq.s   .request_authority
.ready:
        btst    #0,d0
        beq.s   .reobserve
        btst    #1,d0
        beq.s   .reobserve
        btst    #2,d0
        beq.s   .reobserve
        btst    #3,d0
        beq.s   .reobserve
        bra.s   .complete
.hold:
        moveq   #1,d0
        moveq   #0,d1
        moveq   #0,d2
        rts
.reobserve:
        moveq   #2,d0
        moveq   #0,d1
        moveq   #1,d2
        rts
.request_authority:
        moveq   #3,d0
        moveq   #0,d1
        moveq   #0,d2
        rts
.complete:
        moveq   #0,d0
        moveq   #1,d1
        moveq   #0,d2
        rts
