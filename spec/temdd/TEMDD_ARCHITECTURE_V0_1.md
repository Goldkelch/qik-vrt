# TEMDD architecture v0.1

TEMDD is the single normative semantic core. Python, Smalltalk, C90, M68000, Lean, GitHub Actions and deployment systems are projections or adapters, not independent control-plane semantics.

The architecture is layered: language source; deterministic frontend; canonical typed IR; semantic conformance; backend projections; transport adapters; effect executors; readback observers. Only the semantic core decides status. Transport layers may deliver events but may not synthesize authority, evidence, DONE or EFFECT_ACK.

This separation permits gradual replacement of duplicated Python/YAML control logic while preserving observable behavior through shared vectors and exact-subject evidence.
