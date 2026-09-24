# TEMDD Normative Semantic Core v1

Status: normative successor contract.  
Authority repository: `Goldkelch/qik-vrt`.  
Predecessor evidence transfer: **DENY**.

TEMDD v1 is an event- and evidence-oriented control-language successor to the
v0.1 bootstrap. It does **not** retroactively redefine historical v0.1 receipts.

## Seven-layer product contract

1. **Language** — grammar plus operational `Request → Execute → Follow → Learn`.
2. **IR** — canonical deterministic machine-readable representations.
3. **IDE** — Source, IR, Event Graph, Ledger and Conformance views.
4. **Ledger** — append-only actual events with exact subject, cause and evidence bindings.
5. **Formalization** — machine-checked subject, causality, evidence and Effect-Ack invariants.
6. **Tests** — positive and negative parser/IR/ledger/provenance/property/E2E vectors.
7. **Conformance** — a suite separated from the implementation by a process boundary,
   producing an exact-subject machine-readable report.

No earlier layer is evidence for a later layer merely because it executed.

## Result domain

```text
RESULT := PASS | FAIL | CONTINUE | HOLD_UNVERIFIED

TRANSPORT_ACK != EFFECT_ACK
RESULT        != EFFECT
SEQUENCE      != CAUSALITY
PREDECESSOR_EVIDENCE_TRANSFER = false
```

`CONTINUE` and `HOLD_UNVERIFIED` are semantic outcomes, not presentation
conventions, and never imply `DONE`.

## T13 — CAUSAL_BINDING

Ledger sequence, timestamps and observation order do not manufacture causality.

```text
sequence(e1,e2) MUST NOT imply cause(e1,e2)
cause(e1,e2) iff e1.event_id in e2.cause_event_ids
```

## T14 — EVIDENCE_NON_TRANSFER

Evidence is valid only for its exact observed subject.

```text
mutation(S0,S1)
  => S0 != S1
  => Evidence(S0) MUST NOT validate S1
```

Subject identity includes repository, HEAD and TREE (and the enclosing PR when
the runtime subject is a PR). A successor may retain predecessor evidence only
as immutable history.

## T15 — EFFECT_CONSTRUCTION

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

A v1 conformance PASS binds all of:

- implementation repository, exact HEAD and exact TREE;
- implementation digest;
- normative suite version, file inventory and suite digest;
- language, IR, IDE, event semantics, ledger, evidence binding, causality,
  Effect-Ack, formal invariants, tests and negative vectors;
- same-subject C90, Smalltalk, M68000/QEMU and Lean/Lake execution receipt.

The conformance runner is under `conformance/temdd/` and invokes the language
adapter through a subprocess boundary rather than importing implementation
internals as its semantic oracle.

## Canonical pipeline

```text
TEMDD_PROGRAM
  → parse
AST
  → elaborate/type/effect check
TEMDD_IR
  → execute
EVENTS
  → observe + bind
LEDGER
  → evaluate contracts
RESULT
```

IDE projection:

```text
SOURCE ↔ IR ↔ EVENT GRAPH ↔ LEDGER ↔ CONFORMANCE
```

Only explicit `cause_event_ids` create Event-Graph causal edges.

`IDE_ANALYSIS != EXECUTION`  
`IDE_RUNS != CONFORMANCE`  
`LEDGER_ROW != EVIDENCE_TRUTH`  
`CONFORMANCE != P3`  
`CONFORMANCE != MAIN`  
`CONFORMANCE != EFFECT`

## DONE boundary

`DONE` requires fresh, exact-subject-bound required evidence and successful
conformance. Native review, protected promotion, exact-Main reobservation,
release/deployment and fresh external effect readback remain separate later gates.
