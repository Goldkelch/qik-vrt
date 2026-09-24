# TEMDD Normative Semantic Core v1

Status: normative successor contract.
Authority repository: Goldkelch/qik-vrt.
Predecessor evidence transfer: DENY.

TEMDD v1 is an event- and evidence-oriented control language. It does not
retroactively redefine TEMDD v0.1 receipts. A subject mutation creates a new
subject and invalidates subject-bound conformance evidence until fresh
validation is produced.

## Seven-layer product contract

1. Language — grammar plus operational Request -> Execute -> Follow -> Learn semantics.
2. IR — canonical deterministic machine-readable representation.
3. IDE — authoring, diagnostics, IR inspection, event graph, ledger and conformance projection.
4. Ledger — append-only event history with exact subject, cause and evidence bindings.
5. Formalization — machine-checked invariants for subject, causality, evidence and effect acknowledgement.
6. Tests — parser, semantic, IR, ledger, provenance, property and end-to-end negative/positive vectors.
7. Conformance — an implementation-independent runner and exact-subject machine-readable report.

No layer is evidence for a later layer merely because it executed successfully.

## Result domain

```text
RESULT := PASS | FAIL | CONTINUE | HOLD_UNVERIFIED
TRANSPORT_ACK != EFFECT_ACK
RESULT        != EFFECT
SEQUENCE      != CAUSALITY
PREDECESSOR_EVIDENCE_TRANSFER = false
```

`CONTINUE` and `HOLD_UNVERIFIED` are language-level outcomes. They are not
CI presentation conventions and they never imply `DONE`.

## T13 — CAUSAL_BINDING

Event order is not causal order. Causality exists only through explicit
`cause_event_ids` bound to immutable event identities.

```text
sequence(e1,e2) MUST NOT imply cause(e1,e2)
cause(e1,e2) iff e1.event_id in e2.cause_event_ids
```

A timestamp, ledger sequence number, PR number or file order MUST NOT manufacture
a causal edge.

## T14 — EVIDENCE_NON_TRANSFER

Evidence is valid only for the exact subject it observed.

```text
mutation(S0,S1)
  => S0 != S1
  => Evidence(S0) MUST NOT validate S1
```

Subject identity includes repository, logical subject identifier, HEAD and TREE.
A successor MAY preserve predecessor evidence as immutable history, but MUST NOT
relabel it as fresh evidence for the successor.

## T15 — EFFECT_CONSTRUCTION

Transport success, computation result and commit acknowledgement are not effect
acknowledgement.

```text
EffectAck(a)
  iff Authority(a)
  and Commit(a)
  and FreshReadback(a)
  and ExactSubject(a)
  and Match(Expected(a), Observed(a))
```

Therefore `PUT_SUCCESS != EFFECT_ACK`, `COMMIT != EFFECT_ACK`, and
`RESULT != EFFECT`. Missing, stale, ambiguous or mismatching readback is
`HOLD_UNVERIFIED`.

## T16 — CONFORMANCE_BINDING

A TEMDD v1 PASS is valid only when the conformance report binds all of:

- implementation repository;
- exact implementation HEAD;
- exact implementation TREE;
- implementation digest;
- normative suite version and digest;
- all required semantic layers;
- positive and negative vector results.

The conformance runner MUST be separated from the reference implementation and
MUST invoke the implementation through an adapter/process boundary rather than
importing implementation internals as its oracle.

```text
TEMDD_CONFORMANT(S) :=
  LANGUAGE_CONFORMANT(S)
  and IR_CONFORMANT(S)
  and EVENT_SEMANTICS_CONFORMANT(S)
  and LEDGER_CONFORMANT(S)
  and EVIDENCE_BINDING_CONFORMANT(S)
  and FORMAL_INVARIANTS_SATISFIED(S)
  and TEST_SUITE_PASS(S)
  and NEGATIVE_VECTORS_PASS(S)
  and INTEROPERABILITY_BY_EXECUTABLE_PROOF(S)
  and REPORT.subject == S
  and REPORT.suite == normative_suite
```

## T17 — INTEROPERABILITY_BY_EXECUTABLE_PROOF

A TEMDD v1 conformance PASS additionally requires an executable interoperability
proof over the bounded decision model defined by
`spec/temdd/TEMDD_INTEROPERABILITY_V1.md`.

For every required conformance vector and every required implementation:

```text
Canonicalize_I(Input(V)) = ExpectedCanonical(V)
and Evaluate_I(Input(V)) = ExpectedDecision(V)
```

The required implementations MUST execute through distinct source/runtime process
boundaries. Equal implementation decisions without equality to the vector's
normative expected decision are insufficient because common-mode defects remain
possible.

```text
MACHINE_VERIFIABLE_STANDARD
and CANONICAL_SERIALIZATION
and DETERMINISTIC_EVALUATION
and CONFORMANCE_VECTORS
and INDEPENDENT_IMPLEMENTATIONS
and IDENTICAL_EXPECTED_DECISIONS
= INTEROPERABILITY_BY_EXECUTABLE_PROOF
```

This is a bounded conformance property. It does not establish independent
authorship or governance and does not imply Main adoption, deployment or
`EFFECT_ACK_DONE`.

## Canonical pipeline

```text
TEMDD_PROGRAM
  -> parse
AST
  -> elaborate/type/effect check
TEMDD_IR
  -> execute
EVENTS
  -> observe + bind
LEDGER
  -> evaluate contracts
RESULT
```

The IDE is a projection over this pipeline:

```text
SOURCE <-> IR <-> EVENT GRAPH <-> LEDGER <-> CONFORMANCE
```

`IDE_ANALYSIS != EXECUTION`, `IDE_RUNS != CONFORMANCE`,
`LEDGER_ROW != EVIDENCE_TRUTH`, `CONFORMANCE != P3`,
`CONFORMANCE != MAIN`, and `CONFORMANCE != EFFECT`.

## DONE

`DONE` requires fresh, exact-subject-bound required evidence and successful
conformance. Repository review, protected promotion, exact-Main reobservation
and external EFFECT readback remain separate later gates.
