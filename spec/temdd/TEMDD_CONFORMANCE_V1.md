# TEMDD v1 Conformance

TEMDD v1 conformance is an exact-subject property. It is not a repository
review, Main promotion, deployment acceptance or external effect acknowledgement.

A PASS report is emitted only when the independent conformance runner:

1. obtains a clean exact HEAD/TREE from Git;
2. invokes the v1 IR adapter through a process boundary;
3. accepts the positive language corpus and rejects every negative corpus case;
4. checks T13 causal binding, T14 evidence non-transfer and T15 Effect-Ack construction;
5. observes the T13-T15 Lean obligations in a backend receipt produced only after
   Lean 4.19/Lake compilation succeeds;
6. executes the TEMDD parser and persistent-ledger/browser/IDE regression suites itself;
7. validates a same-HEAD/TREE executable-backend receipt covering C90, Smalltalk,
   M68000-under-QEMU and Lean/Lake;
8. computes implementation and normative-suite SHA-256 digests;
9. emits a report conforming to `schemas/temdd-conformance-report-v1.schema.json`.

The report remains subject-bound. Any HEAD/TREE mutation invalidates it and
requires a fresh run. `PREDECESSOR_EVIDENCE_TRANSFER = false`.

`TEMDD_V1_CONFORMANCE_PASS != P3 != MAIN != EFFECT_ACK_DONE`.
