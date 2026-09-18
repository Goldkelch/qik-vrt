# TEMDD canonical Event/Evidence IR and conformance report v1

Status: candidate semantic closure layered on TEMDD v0.1. This document does not
retroactively redefine historical v0.1 receipts.

## Canonical boundary

The source program IR remains `temdd_ir_v0_1`. Runtime observations are
projected from the durable ledger into `temdd_event_ir_v1`; evidence objects are
`temdd_evidence_ir_v1`. The projection is conservative: absent causal ancestry,
inputs, outputs, evidence references or a decision are represented explicitly as
empty lists or `UNSPECIFIED`; they are never inferred from sequence.

`SEQUENCE != CAUSALITY` is therefore structural: observation order is carried
independently from `cause_event_ids`.

Every event binds repository, PR, HEAD and TREE. Every evidence object repeats
the exact observed subject and carries `evidence_transfer=DENY`. Fresh evidence
is admissible only for that identical subject. A successor must create fresh
evidence.

## Conformance report

`temdd_conformance_report_v1` is produced only after the normative language,
IR, persistent ledger/browser regressions, negative corpus, C90, Smalltalk,
M68000/QEMU and Lean/Lake gates have executed on the same immutable HEAD/TREE.
It binds both an implementation digest and a suite digest.

`overall=PASS` means only scoped TEMDD candidate conformance for that exact
subject. It does not mean native review, Main adoption, production deployment,
scientific validation or general `EFFECT_ACK_DONE`.

Subject mutation invalidates the report:

```text
S != S'
=> report(S) cannot establish TEMDD_CONFORMANT(S')
=> HOLD_UNVERIFIED
=> fresh suite execution required
```
