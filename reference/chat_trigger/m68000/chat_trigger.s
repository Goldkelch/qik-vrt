        * QIK-VRT chat trigger closure, Motorola 68000 reference mapping
        * D0..D5 are byte booleans. D0=1 iff all closure edges are present.
        * Syntax: GNU as m68k-compatible source.
        .text
        .globl qikvrt_chat_trigger_closed
qikvrt_chat_trigger_closed:
        moveq   #0,%d0
        tst.b   (%a0)           | repository_processing
        beq.s   hold
        tst.b   1(%a0)          | durable_readback
        beq.s   hold
        tst.b   2(%a0)          | autonomous chat trigger
        beq.s   hold
        tst.b   3(%a0)          | observation
        beq.s   hold
        tst.b   4(%a0)          | continuation
        beq.s   hold
        tst.b   5(%a0)          | fresh E2E validation
        beq.s   hold
        moveq   #1,%d0
hold:
        rts
