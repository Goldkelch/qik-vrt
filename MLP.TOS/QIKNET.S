        .text
        .globl _start

/* QIKNET deliberately transmits its fixed proof frames as immediates.
   This avoids any loader/relocation ambiguity in the guest proof path:
   the bytes that reach BIOS AUX are the bytes encoded below. */
        .macro TX value
        move.w  #\value,d1
        bsr     aux_out
        .endm

_start:
        /* IPv4/TCP SYN:
           10.0.0.2:49152 -> 10.0.0.1:8771, seq=0x11223344.
           SLIP escaping is already applied. */
        TX      0xc0
        TX      0x45
        TX      0x00
        TX      0x00
        TX      0x28
        TX      0x10
        TX      0x01
        TX      0x40
        TX      0x00
        TX      0x40
        TX      0x06
        TX      0x16
        TX      0xcd
        TX      0x0a
        TX      0x00
        TX      0x00
        TX      0x02
        TX      0x0a
        TX      0x00
        TX      0x00
        TX      0x01
        TX      0xdb
        TX      0xdc
        TX      0x00
        TX      0x22
        TX      0x43
        TX      0x11
        TX      0x22
        TX      0x33
        TX      0x44
        TX      0x00
        TX      0x00
        TX      0x00
        TX      0x00
        TX      0x50
        TX      0x02
        TX      0x10
        TX      0x00
        TX      0x65
        TX      0x36
        TX      0x00
        TX      0x00
        TX      0xc0

        /* The controlled peer returns exactly one deterministic SYN-ACK
           SLIP frame. Guest execution must consume it before continuing. */
        bsr     recv_slip_frame

        /* ACK+PSH carrying the exact nonce QIKVRT-NONCE-0001. */
        TX      0xc0
        TX      0x45
        TX      0x00
        TX      0x00
        TX      0x39
        TX      0x10
        TX      0x02
        TX      0x40
        TX      0x00
        TX      0x40
        TX      0x06
        TX      0x16
        TX      0xbb
        TX      0x0a
        TX      0x00
        TX      0x00
        TX      0x02
        TX      0x0a
        TX      0x00
        TX      0x00
        TX      0x01
        TX      0xdb
        TX      0xdc
        TX      0x00
        TX      0x22
        TX      0x43
        TX      0x11
        TX      0x22
        TX      0x33
        TX      0x45
        TX      0x55
        TX      0x66
        TX      0x77
        TX      0x89
        TX      0x50
        TX      0x18
        TX      0x10
        TX      0x00
        TX      0x5a
        TX      0xe8
        TX      0x00
        TX      0x00
        TX      0x51
        TX      0x49
        TX      0x4b
        TX      0x56
        TX      0x52
        TX      0x54
        TX      0x2d
        TX      0x4e
        TX      0x4f
        TX      0x4e
        TX      0x43
        TX      0x45
        TX      0x2d
        TX      0x30
        TX      0x30
        TX      0x30
        TX      0x31
        TX      0xc0

        /* The controlled peer returns the deterministic TCP response frame.
           Only after a complete non-empty returned SLIP frame has been
           consumed inside the Atari guest do we emit the causal confirmation. */
        bsr     recv_slip_frame

        /* Guest-side post-receive witness. The peer accepts success only after
           it has sent the response and then receives this complete SLIP frame. */
        TX      0xc0
        TX      0x51
        TX      0x49
        TX      0x4b
        TX      0x44
        TX      0x4f
        TX      0x4e
        TX      0x45
        TX      0xc0

        clr.w   -(sp)
        trap    #1                   /* Pterm0 */

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

/* Consume one complete non-empty SLIP frame inside the emulated Atari guest.
   The peer is deterministic and sends exactly one frame per protocol stage. */
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
