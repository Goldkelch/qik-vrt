# TEMDD v0.1 Conformance

TEMDD v0.1 conformance is a seven-layer, exact-subject contract:

`LANGUAGE ∧ IR ∧ IDE ∧ LEDGER ∧ FORMALIZATION ∧ TESTS ∧ CONFORMANCE`.

A conforming candidate MUST parse the positive corpus, reject the negative
corpus, preserve exact-subject binding, distinguish transport/result/effect
acknowledgement, fail closed on stale or unknown critical evidence, preserve
T01-T16, and construct DONE only from the complete declared DoD.

## Canonical representations

Program meaning is carried by `temdd_ir_v0_1`. Durable native ledger rows are
projected conservatively to `temdd_event_ir_v1`; evidence is represented as
`temdd_evidence_ir_v1`. Event sequence and causal ancestry are independent:
`observation_order` never manufactures `cause_event_ids`.

Evidence admission requires a fresh evidence object bound to exactly the same
repository, PR, HEAD and TREE. Any subject mutation denies predecessor evidence
transfer and requires fresh validation.

## Executable implementation classes

- Python: parser/elaborator, T01-T16 semantic checks and canonical Event/Evidence IR projection.
- IDE: browser editor, typed diagnostic program IR, exact-subject view and persistent ledger trace; local analysis has no effect authority.
- Ledger: durable append-only SQLite/WAL event store with exact-subject replay isolation and dual source/observation order.
- C90: executable deterministic partial projection.
- Smalltalk: hash-locked Pharo 13 executable partial projection.
- M68000: cross-built fixed relation executed under `qemu-m68k`; this is not physical M68000 evidence.
- Lean/Lake: pinned Lean 4.19 formal obligations, T13-T16 and axiom audit.

## Exact-subject report

The workflow emits `temdd_conformance_report_v1` only after all preceding
candidate gates have succeeded on one immutable HEAD/TREE. The report binds:

- implementation repository, HEAD, TREE and implementation digest;
- normative suite version, file inventory and suite digest;
- language, program IR, IDE, event semantics, ledger, evidence binding,
  causality, Effect-Ack, formal invariants, tests and negative vectors;
- executed C90, Smalltalk, M68000/QEMU and Lean backends.

`overall=PASS` is scoped TEMDD candidate conformance only. It does not imply
native P3 review, Main adoption, production deployment, physical hardware
execution, scientific validation or general `EFFECT_ACK_DONE`.

v0.1 therefore distinguishes `BOOTSTRAP/CANDIDATE_CONFORMANT` from
`STABLE_LANGUAGE`. Stable-language status remains gated by Main adoption and
fresh production readback.
