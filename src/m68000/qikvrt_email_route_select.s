; SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
; Copyright 2026 Ingolf Lohmann.
;
; QIK-VRT email route selection kernel — Motorola 68000
;
; Input D0.b flags:
;   bit 0 ENVELOPE_VALID
;   bit 1 ROUTE_RESOLVED
;   bit 2 TLS_POLICY_SATISFIED
;   bit 3 CONTENT_POLICY_CLEAR
;   bit 4 DOMAIN_AUTH_ALIGNED
;   bit 5 RETRYABLE_DEPENDENCY_FAILURE
;   bit 6 AUTHORITY_REQUIRED
;   bit 7 AUTHORITY_PRESENT
; Input D3.b: stable route-capsule witness, preserved exactly.
;
; Output D0 (QIK-VRT four-state decision ABI):
;   0 NOOP / bounded route capsule complete and admissible
;   1 HOLD
;   2 REOBSERVE / retry
;   3 REQUEST_AUTHORITY
; Output D1: 1 iff the bounded route capsule is complete, else 0.
; Output D2: 1 iff machine-owned reobservation remains active, else 0.
; D3 is never written.
;
; This kernel does not open a socket, mutate DNS, submit SMTP, write a
; mailbox, call a cloud provider, read credentials or claim Effect Ack.

qikvrt_email_route_select:
        btst    #0,d0
        beq.s   .hold
        btst    #5,d0
        bne.s   .reobserve
        btst    #6,d0
        beq.s   .route
        btst    #7,d0
        beq.s   .request_authority
.route:
        btst    #1,d0
        beq.s   .reobserve
        btst    #2,d0
        beq.s   .hold
        btst    #3,d0
        beq.s   .hold
        btst    #4,d0
        beq.s   .hold
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
