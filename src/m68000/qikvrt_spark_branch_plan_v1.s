; QIK-VRT Spark branch-plan kernel — Motorola 68000
; D0.b input flags:
; b0 malformed, b1 main effect, b2 base current, b3 integrity current,
; b4 gates terminal, b5 gates non-adverse, b6 mergeable, b7 authority.
; D0 output: complete bounded branch-plan id 0..11.
; The plan is executed by a host adapter with reobservation after every effect.

        btst    #0,d0
        beq.s   .check_main
        moveq   #1,d0                  ; HOLD_INVALID
        rts
.check_main:
        btst    #1,d0
        beq.s   .check_base
        moveq   #0,d0                  ; ALREADY_COMPLETE
        rts
.check_base:
        btst    #2,d0
        bne.s   .check_integrity
        btst    #7,d0
        beq.s   .base_noauth
        moveq   #2,d0                  ; REBASE_TO_CLOSE
        rts
.base_noauth:
        moveq   #3,d0                  ; REBASE_TO_AUTHORITY
        rts
.check_integrity:
        btst    #3,d0
        bne.s   .check_terminal
        btst    #7,d0
        beq.s   .integrity_noauth
        moveq   #4,d0                  ; MATERIALIZE_TO_CLOSE
        rts
.integrity_noauth:
        moveq   #5,d0                  ; MATERIALIZE_TO_AUTHORITY
        rts
.check_terminal:
        btst    #4,d0
        bne.s   .check_nonadverse
        btst    #7,d0
        beq.s   .terminal_noauth
        moveq   #6,d0                  ; VERIFY_TO_CLOSE
        rts
.terminal_noauth:
        moveq   #7,d0                  ; VERIFY_TO_AUTHORITY
        rts
.check_nonadverse:
        btst    #5,d0
        bne.s   .check_mergeable
        btst    #7,d0
        beq.s   .nonadverse_noauth
        moveq   #8,d0                  ; REPAIR_TO_CLOSE
        rts
.nonadverse_noauth:
        moveq   #9,d0                  ; REPAIR_TO_AUTHORITY
        rts
.check_mergeable:
        btst    #6,d0
        bne.s   .final_authority
        btst    #7,d0
        beq.s   .mergeable_noauth
        moveq   #8,d0                  ; REPAIR_TO_CLOSE
        rts
.mergeable_noauth:
        moveq   #9,d0                  ; REPAIR_TO_AUTHORITY
        rts
.final_authority:
        btst    #7,d0
        beq.s   .request_authority
        moveq   #10,d0                 ; MERGE_TO_CLOSE
        rts
.request_authority:
        moveq   #11,d0                 ; REQUEST_AUTHORITY
        rts
