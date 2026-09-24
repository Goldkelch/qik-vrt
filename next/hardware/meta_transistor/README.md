# Minimal reproducible Meta-Transistor RTL carrier

This directory is an RTL successor of the C reference in `next/core/src/qikvrt_kernel.c`.

It deliberately proves only a bounded claim: the fail-closed transition semantics can be represented as synthesizable VHDL and checked by an RTL testbench. It does **not** claim FPGA execution, physical chip realization, global novelty, patentability, or EFFECT_ACK_DONE.

Required evidence ladder:

`C reference -> RTL -> simulation -> synthesis -> FPGA bitstream -> physical execution -> independent readback -> acceptance`

The RTL maps the current controls `binding`, `authority`, `distinction`, `drift`, and `requested` to OBSERVE/HOLD/CONTINUE. Missing authority/binding/distinction or drift forces HOLD. A computed LUT value is valid only for CONTINUE.

Transport completion remains distinct from effect acknowledgement: `TRANSPORT_ACK != EFFECT_ACK`.
