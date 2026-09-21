| Independent Motorola 68000 carrier for QIK-VRT core invariant v1.
| C ABI arguments: transport, block_required, isolate_required, release_ready
| D0 result: NACK=0 CONTINUE=1 DONE=2 ISOLATE=3 BLOCK=4
        .text
        .globl qikvrt_core_invariant_m68000
qikvrt_core_invariant_m68000:
        tst.l   4(%sp)
        beq.s   .nack
        tst.l   8(%sp)
        bne.s   .block
        tst.l   12(%sp)
        bne.s   .isolate
        tst.l   16(%sp)
        bne.s   .done
        moveq   #1,%d0
        rts
.nack: moveq #0,%d0
        rts
.done: moveq #2,%d0
        rts
.isolate: moveq #3,%d0
        rts
.block: moveq #4,%d0
        rts

| C ABI argument: Effect_State; D0 result: ordinary release 0 or 1.
| The C harness only prints this result; it does not define the release rule.
        .globl qikvrt_core_ordinary_release_m68000
qikvrt_core_ordinary_release_m68000:
        moveq   #0,%d0
        cmpi.l  #2,4(%sp)
        bne.s   .release_return
        moveq   #1,%d0
.release_return:
        rts
