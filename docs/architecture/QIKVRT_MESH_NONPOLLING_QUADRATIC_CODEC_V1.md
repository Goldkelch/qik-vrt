# QIK-VRT Mesh: non-polling quadratic codec

The mesh is activated only by a concrete repository event (`push`,
`pull_request`, `workflow_run`, `workflow_dispatch`, or
`repository_dispatch`).  Periodic Actions schedules, cron wakeups, and blind
retry loops are forbidden.  A heartbeat may publish an already materialized
local receipt, but it must not discover work by scanning or remote polling on
the API hot path.

For a finite mesh parameter `N`, the codec instantiates exactly `N*N` lanes.
The frame width is `N*N*WORD_BITS`.  Lane `(row,column)` is assigned index
`row*N + column`, and bit `b` of that lane is wire bit
`(row*N + column)*WORD_BITS + b`.  Wire order is row-major, least-significant
bit first.  Consequently, for a complete valid frame:

`deserialize(serialize(lanes)) = lanes`.

## Deterministic admission, not sampled inference

After a frame is complete, the companion admission gate makes one total,
reproducible classification: incomplete input is `CONTINUE`; an explicitly
declared ambiguity is `HOLD`; a complete canonical match is `ACCEPT`; and every
other complete input is `BLOCK`.  The same truth table is present in
`tools/qikvrt_mesh_quadratic_codec.py` and
`hardware/vhdl/qikvrt_deterministic_admission_gate.vhd`.

This is the precise computational claim: uncertainty is never silently sampled
into a decision.  It is represented as an input/state and remains visible until
resolved by separately supplied canonical evidence.  The contract does not
assert that the external world or physical hardware is noise-free.

At the VHDL interface, `ACCEPT` is deliberately restricted to the exact values
`frame_complete_i='1'`, `ambiguity_present_i='0'`, and
`canonical_equal_i='1'`.  A non-`'0'` ambiguity `std_logic` value, including
`U`, `X`, or `Z` in simulation, maps to `HOLD`; a non-`'1'` canonical match
maps to `BLOCK`.  This is a fail-closed RTL interface rule, not a claim that a
physical asynchronous input cannot become metastable.  Input synchronization,
target timing closure, and board measurement remain separate open evidence.
`hardware/vhdl/qikvrt_deterministic_admission_gate_tb.vhd` is a self-checking
simulation testbench for the exact and non-binary `std_logic` cases.  Its
deterministic invocation is `make vhdl-admission-gate-test`; before GHDL is
added to the runtime lock and cache registry, that target deliberately blocks
instead of claiming an HDL simulation result.

## Protected finite wire frame

The canonical payload is not released directly from a merely width-complete
serial stream.  The existing codec encodes one finite wire frame in this exact
least-significant-bit-first order:

`SYNC_8 | SESSION_32 | SEQUENCE_16 | PAYLOAD_(N*N*WORD_BITS) | CRC16_CCITT_16`.

`SESSION_32` is the exact configured receive context, sampled at the first bit
of an attempted frame and required to remain unchanged through its final bit.
The enclosing endpoint/control plane must provision a binary value and change
it only at a frame boundary.  `SEQUENCE_16` is the receiver's next expected
value and advances only after an exactly verified frame.  The receiver accepts
neither non-binary wire/context values nor a non-matching sync, session,
sequence, or recomputed tag.  On a failed check it retains the last verified
payload and expected sequence; it does not silently resynchronize.  In the
iCE40 loopback top a visible framing failure latches a transport hold, so a
modeled mismatch cannot turn into an automatic restart.

The finite sequence counter is non-wrapping.  Its final value can be used once;
both endpoints then enter an explicit exhausted state until a separately
authorized **fresh-session** reset/rekeying boundary.  Reset with the same
session is not asserted to separate stale frames across resets.  The iCE40
top's constant session is only a local RTL demonstration, not external session
provisioning or an authentication protocol.

This gives a bounded source-level failure-handling rule: an incomplete or short
input is `CONTINUE`; an exact received frame with a tested sync, session,
sequence, modeled insertion/reorder, or tag mismatch is `HOLD`; those modeled
test cases do not reach `ACCEPT`.  It does **not** prove that every possible
loss, insertion, reorder, CRC collision, or physical-channel corruption is
detected before it can form a different apparently exact frame.
`hardware/vhdl/qikvrt_mesh_quadratic_codec_tb.vhd` injects a short frame,
reordered bits, an inserted/shifted bit, replayed sequence, session mismatch,
in-frame session-context change, and digest mismatch.  It runs through the
same locked-GHDL command as the admission testbench once GHDL is declared.
`hardware/fpga/ice40up5k_breakout/qikvrt_mesh_prototype_top_tb.vhd` separately
checks that the reset-bound iCE40 top performs one serialization burst only;
it cannot launch a second frame in the transition that makes admission visible.

CRC-16 is a fixed hardware-friendly error-detection tag, not a cryptographic
authenticator and not a claim that every adversarial collision or every
physical transport fault is detected.  The claim is deterministic, fail-closed
handling for exact received frames and explicit modeled mismatch cases only.
Link synchronization, session provisioning, target timing closure, physical
fault model, and board evidence remain open.

## Exact scaling and throughput unit

The quadratic rule is a **frame-width/resource rule**, not an assertion that a
whole mesh transaction completes in one clock.  This RTL has one serial
ready/valid bit edge.  Thus a complete frame contains, and needs at least,
`N*N*WORD_BITS` accepted payload handshakes.  At a clock `f` with no stalls,
its payload-only upper bound is:

`raw_frames_per_second = f / (N*N*WORD_BITS)`.

For the prototype setting `N=2`, `WORD_BITS=8`, that is 32 payload handshakes
per frame (375,000 raw frames/s at 12 MHz).  Frame launch, backpressure,
hashing, receipt construction, ledger persistence, deduplication, fanout and
network transport are intentionally outside this codec and reduce any
end-to-end rate.  Consequently a raw frame rate is neither a Receipt/s result
nor a comparison metric for LLM token/s.

The protected wire-frame profile adds a fixed 72-bit overhead, so it uses
`N*N*WORD_BITS+72` wire handshakes (104 for the `2 x 2`, 8-bit prototype).  This
does not change the quadratic payload/resource rule and it is likewise not a
receipt, cognitive-workload, or physical performance measurement.

`hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd` realizes the finite mapping as
clocked RTL with explicit ready/valid handshakes.  It intentionally contains no
`wait`, `after`, generated clock, timer, or polling interface.  This is a
synthesis-oriented VHDL description and an executable Python reference mapping;
it is not a board synthesis, timing-closure, fabrication, or physical-measurement
receipt.  Such a claim additionally requires a locked VHDL tool, a named target
device, and the resulting tool-bound synthesis report.
