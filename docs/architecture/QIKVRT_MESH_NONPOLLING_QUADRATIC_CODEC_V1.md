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

`hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd` realizes the finite mapping as
clocked RTL with explicit ready/valid handshakes.  It intentionally contains no
`wait`, `after`, generated clock, timer, or polling interface.  This is a
synthesis-oriented VHDL description and an executable Python reference mapping;
it is not a board synthesis, timing-closure, fabrication, or physical-measurement
receipt.  Such a claim additionally requires a locked VHDL tool, a named target
device, and the resulting tool-bound synthesis report.
