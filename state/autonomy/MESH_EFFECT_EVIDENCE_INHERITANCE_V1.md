# QIK-VRT Mesh: Effect-Evidence Invariant

Status: normative mesh inheritance contract
Authority repository: Goldkelch/qik-vrt

Every current Mesh node and every future Mesh repository/node MUST inherit this contract before admission.

## Core invariants

- TRANSPORT_ACK != EFFECT_ACK
- PROCESS_COMPLETION != GOAL_COMPLETION
- FAILURE_REPORT != FAILURE_RECOVERY
- UNKNOWN => FAIL_CLOSED
- CLAIM_SCOPE <= EVIDENCE_SCOPE
- PREDECESSOR_EVIDENCE_TRANSFER = FALSE
- MUTATION => REBIND_EXACT_SUBJECT

No UI, workflow, transport, queue, API, mail client, cloud service, agent, or node may represent a stronger success state than its evidence establishes.

## Required evidence classification

Every material claim MUST be classified as exactly one of:
1. DOCUMENTED_FACT — directly supported by retained primary evidence.
2. DERIVED_FINDING — follows directly from documented facts; derivation must be stated.
3. INTERPRETATION — system/ethical analysis, explicitly marked as interpretation.
4. UNKNOWN — not established by available evidence.

UNKNOWN MUST NOT be promoted to success, fact, delivery, recovery, effect, or completion.

## Communication-specific invariant

SENT != DELIVERED.
DELIVERED != HUMAN_READ.
NDR_GENERATED != RECOVERY_SUCCESS.

A delivery failure or NDR is a new recovery work unit. A message remains effect-open until the claimed communication postcondition is supported by evidence within the same claim scope.

The documented September 2026 incident establishes only the evidence scope retained for that incident: a send attempt, NDR generation, recipient-specific delivery failures reported with 550 5.7.520 / AS(4810), and no established successful recovery in that evidence. It does NOT establish that the content was objectively spam, intent by any operator, universal cloud failure, or a legal violation.

## Node admission and inheritance

Every node registration, split, clone, successor repository, and future Mesh repository MUST:
- contain this contract or a byte-identical canonical reference resolved from Authority;
- validate it during admission;
- fail closed if absent, altered without an Authority successor, or unresolved;
- preserve the fact/derivation/interpretation/UNKNOWN separation in generated evidence and user-visible status;
- propagate this requirement to its own descendants.

A node that cannot prove inheritance is NOT admitted as a conforming QIK-VRT Mesh node.

## Effect closure

EFFECT_ACK_DONE may be asserted as machine evidence only when the claimed postcondition is freshly observed, subject-bound, provenance-bound, and within evidence scope. Authority declarations remain distinct from machine-effect witnesses.

This contract is recursive: future Mesh creation MUST install and validate the same invariant before the new node may claim conformance.


## QIK-VRT MVP inheritance

Every conforming node MUST also inherit and enforce state/autonomy/QIKVRT_MVP_EXACT_SUBJECT_RECOVERY_V1.md (or an Authority-bound byte-identical canonical reference). MVP conformance is fail-closed when this recovery contract is absent or unresolved.


## Unified architecture principle

Every conforming node MUST inherit and expose state/autonomy/QIKVRT_UNIFIED_ARCHITECTURE_PRINCIPLE_V1.md or an Authority-bound byte-identical canonical reference. This binds Haltepunktdefinition, TEMDD, Effect Acknowledgment, Metatransistor and artificial cognition to the same evidence-bounded transition semantics; it does not transfer implementation or effect evidence between those domains.


## Binding / Acceptance safety invariant

Every conforming current or future Mesh node MUST inherit and enforce `state/autonomy/BINDING_ACCEPTANCE_SAFETY_INVARIANT_V1.md` or an Authority-bound byte-identical canonical reference. Syntax, byte identity, effect evidence and Acceptance remain distinct validation layers. A hash PASS MUST NOT open an Acceptance gate. Missing inheritance or enforcement is fail-closed and MUST NOT be reported as Mesh conformance.
