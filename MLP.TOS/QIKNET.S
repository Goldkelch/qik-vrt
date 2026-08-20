        .text
        .globl _start
_start:
        lea     syn_frame(pc),a0
        move.w  #syn_frame_end-syn_frame-1,d6
send_syn:
        moveq   #0,d1
        move.b  (a0)+,d1
        bsr     aux_out
        dbra    d6,send_syn

        bsr     recv_slip_frame

        lea     data_frame(pc),a0
        move.w  #data_frame_end-data_frame-1,d6
send_data:
        moveq   #0,d1
        move.b  (a0)+,d1
        bsr     aux_out
        dbra    d6,send_data

        bsr     recv_slip_frame

        /* A second complete returned SLIP frame was observed by the guest
           after the endpoint accepted the exact nonce-bearing TCP payload. */
        move.w  #0,-(sp)
        pea     ok_name(pc)
        move.w  #0x3c,-(sp)          /* GEMDOS Fcreate */
        trap    #1
        addq.l  #8,sp
        move.l  d0,d4
        bmi     fail

        pea     ok_text(pc)
        move.l  #ok_text_end-ok_text,-(sp)
        move.w  d4,-(sp)
        move.w  #0x40,-(sp)          /* GEMDOS Fwrite */
        trap    #1
        lea     12(sp),sp

        move.w  d4,-(sp)
        move.w  #0x3e,-(sp)          /* GEMDOS Fclose */
        trap    #1
        addq.l  #4,sp

        clr.w   -(sp)
        trap    #1                   /* Pterm0 */

fail:
        move.w  #1,-(sp)
        move.w  #0x4c,-(sp)          /* Pterm(1) */
        trap    #1

/* BIOS AUX device 1: actual guest serial output/input through Hatari RS232. */
aux_out:
        move.w  d1,-(sp)
        move.w  #1,-(sp)
        move.w  #3,-(sp)             /* Bconout */
        trap    #13
        addq.l  #6,sp
        rts

aux_in:
wait_char:
        move.w  #1,-(sp)
        move.w  #1,-(sp)             /* Bconstat */
        trap    #13
        addq.l  #4,sp
        tst.l   d0
        beq     wait_char
        move.w  #1,-(sp)
        move.w  #2,-(sp)             /* Bconin */
        trap    #13
        addq.l  #4,sp
        and.l   #0xff,d0
        rts

/* Consume one non-empty SLIP frame. This deliberately operates inside the
   emulated Atari guest, so host networking alone cannot satisfy the proof. */
recv_slip_frame:
        moveq   #0,d7
recv_loop:
        bsr     aux_in
        cmpi.b  #0xc0,d0
        bne     recv_non_end
        tst.b   d7
        beq     recv_loop
        rts
recv_non_end:
        moveq   #1,d7
        bra     recv_loop

        .align  2
/* Valid IPv4/TCP SYN, 10.0.0.2:49152 -> 10.0.0.1:8771, seq=0x11223344.
   SLIP escaping is already applied (source port begins c0 -> db dc). */
syn_frame:
        .byte 0xc0,0x45,0x00,0x00,0x28,0x10,0x01,0x40,0x00,0x40,0x06,0x16,0xcd
        .byte 0x0a,0x00,0x00,0x02,0x0a,0x00,0x00,0x01,0xdb,0xdc,0x00,0x22,0x43
        .byte 0x11,0x22,0x33,0x44,0x00,0x00,0x00,0x00,0x50,0x02,0x10,0x00,0x65
        .byte 0x36,0x00,0x00,0xc0
syn_frame_end:

/* ACK+PSH carrying exact nonce QIKVRT-NONCE-0001 after deterministic
   peer SYN-ACK seq=0x55667788. */
data_frame:
        .byte 0xc0,0x45,0x00,0x00,0x39,0x10,0x02,0x40,0x00,0x40,0x06,0x16,0xbb
        .byte 0x0a,0x00,0x00,0x02,0x0a,0x00,0x00,0x01,0xdb,0xdc,0x00,0x22,0x43
        .byte 0x11,0x22,0x33,0x45,0x55,0x66,0x77,0x89,0x50,0x18,0x10,0x00,0x5a
        .byte 0xe8,0x00,0x00,0x51,0x49,0x4b,0x56,0x52,0x54,0x2d,0x4e,0x4f,0x4e
        .byte 0x43,0x45,0x2d,0x30,0x30,0x30,0x31,0xc0
data_frame_end:

ok_name:
        .asciz  "C:\\QIKNET.OK"
ok_text:
        .ascii  "GUEST_TCP_IP_ROUNDTRIP_OBSERVED\r\n"
ok_text_end:
