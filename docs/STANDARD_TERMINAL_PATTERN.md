# QIK-VRT Standard Terminal Pattern V1

The Standard Terminal Pattern is the common fail-closed boundary semantics for repository mesh operation. It does not add a writer and it does not turn an observer into proof authority. It projects one exact-head-bound semantic event in two coupled directions.

**Outward reflection** is audit-facing: exact repository/head/tree, architectural locus, classification, blocker and the shared deterministic event ID. It is explicitly non-authoritative for scientific truth, PASS, FINAL_PASS or EFFECT_ACK_DONE.

**Inward reflexivity** is runtime-facing: the same event ID yields admission information for the node itself (`blocks_productive_progress`, `admit_productive_writer`, `admit_observer`, `requires_human`, `retryable`, `next_action`). A missing, stale or differently bound inward projection fails closed for productive work. Observation remains admissible during HOLD so that the system can discover that a blocker has cleared.

## Architectural placement

V1 applies at Mesh ingress and egress; Mesh-node ingress and egress; and node-internal pre-dispatch, pre-action, post-action, integrity-projection, persistence-write, exact-head-reobservation, gate-aggregation and Effect-Ack boundaries. These are semantic loci, not twelve independent daemons. One canonical observation can therefore be projected consistently across all loci without creating races or contradictory local truth states.

## Classification

Classification is deterministic and ordered. Exact-head mismatch outranks stale-writer/lease state; stale writers outrank integrity projection defects; integrity defects outrank platform pre-job barriers; platform barriers outrank executed workflow failures; executed failures outrank expected semantic HOLD; only actually observed exact-head success can produce the corresponding success classification. `action_required`, startup failure and zero-job terminal execution never count as trusted success.

Expected semantic HOLD remains a valid state. In particular, the terminal layer cannot manufacture physical measurements, independent replication, scientific consensus or another missing evidence predicate. A separate integrity defect remains a separate defect even when a semantic HOLD is simultaneously correct.

## Continuous reflexive loop

`qikvrt_standard_terminal.yml` consumes the exact-head artifact from `QIKVRT reflexive repository watchdog`. It is event-driven on watchdog completion and has a five-minute schedule fallback. It emits `terminal-outward.json` and `terminal-inward.json` as Action artifacts only. The previous exact-head inward projection is reobserved on the next cycle, yielding `REFLEXIVE_STABLE` or `REFLEXIVE_TRANSITION` without changing the event identity.

The workflow executor consumes the latest exact-head inward projection before dispatching its no-effect observer. This makes the terminal channel operationally inward-facing rather than merely a status display. Productive writers must use the stricter productive-writer admission mode as they adopt the standard; observer admission intentionally stays available during HOLD to preserve liveness and reobservation.

No force update, automatic productive-writer cancellation, merge, release, deployment, Zenodo/IETF mutation or semantic promotion is authorized by this pattern.
