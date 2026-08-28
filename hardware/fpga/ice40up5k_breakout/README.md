# QIK-VRT iCE40UP5K FPGA prototype

Target: Lattice **iCE40 UltraPlus Breakout Board**, model `iCE40UP5K-B-EVN`,
device `iCE40UP5K`, package `SG48`.  The official board provides USB
programming and the device provides 5,280 LUTs, embedded RAM and DSP resources.

The top-level is a bounded bring-up: it instantiates the `2 x 2`, 8-bit
quadratic Mesh codec, sends `0x5AA55AA5`, and receives it through an on-chip
ready/valid loopback.  Blue indicates reset, green an active serialization and
red a complete received frame.  It does not claim external data transport,
timing closure, programming, hardware execution or manufacture.

Required physical items:

- one `iCE40UP5K-B-EVN` board and its USB cable;
- a host with the exact approved OSS CAD Suite tool receipt;
- no additional adapter is required for this LED-only bring-up.

Required tool evidence before programming:

1. exact OSS CAD Suite archive/version, SHA-256 and license acceptance;
2. `ghdl` analysis of both VHDL sources;
3. target-specific synthesis, place-and-route and timing report for `up5k/sg48`;
4. generated bitstream digest and programmer readback/board observation receipt.

The repository records the first three as `OPEN` until the toolchain is locked
and executed.  This prevents a source-only claim from being presented as a
fabricated prototype.
