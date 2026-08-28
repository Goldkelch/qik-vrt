# QIK-VRT iCE40UP5K FPGA prototype

Target: Lattice **iCE40 UltraPlus Breakout Board**, model `iCE40UP5K-B-EVN`,
device `iCE40UP5K`, package `SG48`.  The official board provides USB
programming and the device provides 5,280 LUTs, embedded RAM and DSP resources.

The top-level is a bounded bring-up: it instantiates the `2 x 2`, 8-bit
quadratic Mesh codec, sends `0x5AA55AA5`, and receives it through an on-chip
ready/valid loopback.  Every wire frame has fixed `SYNC_8`, `SESSION_32`,
`SEQUENCE_16` and `CRC16_CCITT_16` fields around the canonical 32-bit payload.
For the exact received frames and modeled mismatch cases in the testbench, a
frame is valid only after all those fields match exactly; an integrity failure
latches a transport hold rather than retrying or silently resynchronizing.
The fixed top-level session is a local RTL binding demonstration, not external
session provisioning or an authentication protocol.  CRC-16 is not asserted to
detect every channel corruption or collision.  Blue indicates reset, green an
active serialization and red a verified deterministic ACCEPT state.  The
reset-bound one-shot sends exactly one automatic frame; it cannot issue a
second one while the admission result becomes visible.  It does not claim
external data transport, timing closure, programming, hardware execution or
manufacture.

Required physical items:

- one `iCE40UP5K-B-EVN` board and its USB cable;
- a host with the exact approved OSS CAD Suite tool receipt;
- no additional adapter is required for this LED-only bring-up.

Required tool evidence before programming:

1. exact OSS CAD Suite archive/version, SHA-256, cache-bound compiler binary
   path and SHA-256, and license acceptance;
2. `ghdl` analysis of the RTL plus the self-checking admission and protected
   codec testbenches (`qikvrt_deterministic_admission_gate_tb.vhd` and
   `qikvrt_mesh_quadratic_codec_tb.vhd`) and the reset-bound top testbench
   (`qikvrt_mesh_prototype_top_tb.vhd`);
3. target-specific synthesis, place-and-route and timing report for `up5k/sg48`;
4. generated bitstream digest and programmer readback/board observation receipt.

At this revision none of those FPGA tools is pinned in
`runtime/toolchains/TOOLCHAIN.lock.tsv` or its cache registry.  Under the
repository runtime policy they must first receive an exact version/archive
digest, license, cache/provision path and self-test before they can be used.
The repository records the entire toolchain-to-board path as `OPEN` until that
work is completed and the resulting receipts are preserved.  This prevents a
source-only claim from being presented as a compiled, fabricated, or observed
prototype.

Once GHDL is present in the lock and cache registry, run
`make vhdl-admission-gate-test`.  It analyzes, elaborates, and runs the
self-checking testbenches in a temporary work directory.  Until then the target
returns an explicit `BLOCK`; it never silently substitutes a static source test
for an HDL execution receipt.  The runner does not accept `PATH` or
`QIKVRT_GHDL` overrides: a future GHDL activation must name an exact binary
below the repository tool cache and verify its SHA-256 before invocation.
