; QIK-VRT event-terminal ABI — Motorola 68000
; D0: 0 NOOP, 1 HOLD, 2 REOBSERVE, 3 REQUEST_AUTHORITY.
; D3 remains the stable witness.

qikvrt_d0_noop:              moveq   #0,d0
                            rts
qikvrt_d0_hold:              moveq   #1,d0
                            rts
qikvrt_d0_reobserve:         moveq   #2,d0
                            rts
qikvrt_d0_request_authority: moveq   #3,d0
                            rts
