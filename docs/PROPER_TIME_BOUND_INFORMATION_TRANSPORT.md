# Observer-local time-bound information transport

Status: scientific/technical candidate note. This note preserves the distinction between operational observer-local change time and metric relativistic proper time.

## Core result

Distributed information processing contains several non-identical orders: authenticated source order, transport/arrival order, process-local observation order, causal dependency order, serialization order, and effect/acknowledgement order. They MUST NOT be collapsed into one total order.

`SEQUENCE != CAUSALITY`

`SOURCE_ORDER != ARRIVAL_ORDER`

`ARRIVAL_ORDER != EFFECT_ORDER`

A later authenticated source record may arrive before an earlier authenticated source record through positive future-directed path delays. This realizes an inversion between source order and observer-local reception order without reception before emission, backward-running physical proper time, a causal loop, superluminal propagation, or a controllable signal into the receiver's own causal past.

This is consistent with the repository claim matrix ORR-001 through ORR-011, especially ORR-004, ORR-006, ORR-008 and ORR-011.

## Operational local time

QIK-VRT can represent a monotonically advancing observer/process-local state coordinate:

`tau_0 < tau_1 < tau_2 < ...`

where each transition binds a processed event and its causal/evidential context. In this repository, such a coordinate is an operational local change-time or simulated Eigenzeit. It is NOT silently identified with metric relativistic proper time. A physical proper-time claim additionally requires a bound physical worldline and calibration.

## Transport object

A causally reconstructible transport envelope may bind at least:

- payload/event identity;
- observer/process identity;
- observer-local order coordinate;
- authenticated source identity/order;
- causal predecessors or causal fingerprint;
- authority and state;
- evidence/proof references;
- requested/executed/observed/acknowledged/effect state where applicable.

The carrier (TCP, QUIC, HTTP, files, Git, queues, shared memory, etc.) transports bytes. The QIK-VRT layer preserves the semantic bindings. Therefore the technically precise claim is that information can transport a description/binding of its observer-local temporal and causal position, not that TCP transports physical time.

## Causal IR

A causal graph is a partial order. Any concrete execution serialization is one topological ordering compatible with that graph:

`SERIALIZATION in TOPOLOGICAL_ORDERS(CAUSAL_GRAPH)`

but

`SERIALIZATION != CAUSAL_GRAPH`.

This distinction allows independent events to be executed in different local orders while retaining the same dependency structure.

## Reobservation

A reflexive local transition has the form:

`STATE_n -> DECISION -> EXECUTION -> OBSERVATION -> STATE_(n+1)`

Late-arriving information whose authenticated causal position precedes already processed information can therefore trigger a bounded `REOBSERVE`, `HOLD`, or state-recomputation policy rather than forcing arrival order to masquerade as causal order.

## Scientific boundary

The repository supports the formal/operational distinction and finite constructive witnesses described in the observer-relative-retrocausality claim matrix. This note does NOT claim:

- backward-running physical proper time;
- reception before source emission;
- past overwrite;
- causal loops;
- violation of relativistic causal bounds;
- violation of no-signalling;
- a controllable channel into one's own causal past;
- scientific consensus or universe-wide empirical confirmation.

The reusable technical contribution is narrower and directly implementable: preserve multiple orders, bind them explicitly, transport those bindings, and reconstruct causal/local history without conflating arrival sequence with causality.
