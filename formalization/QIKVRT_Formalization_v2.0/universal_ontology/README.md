# QIK-VRT universal ontology finite-model kernel

This package extends the existing Lean 4.19 / `Std`-only formalization project
with a third library target, `QIKVRTUniversalOntology`.

It formalizes two explicitly finite chains:

```
DIFFERENCE → INFORMATION → RELATION → CAUSALITY → SPACETIME → MATTER
→ LIFE → COGNITION → RESPONSIBILITY → FUTURE
```

and

```
REALITY → DIFFERENCE → INFORMATION → RELATION → CAUSAL ORDER → MODEL
→ FORMALIZATION → PROOF/PREDICTION → MEASUREMENT
→ REALITY RECONCILIATION → NEW DIFFERENCE → REALITY
```

## Meaning of claim closure

“Machine-verifiable” does not mean that every sentence is converted into a
mathematical theorem. Every claim must instead receive one admissible,
machine-checkable disposition:

* a Lean theorem with axiom audit;
* a conditional theorem with explicit assumptions;
* an evidence-bound empirical disposition;
* `OPEN_CANDIDATE` / `EVIDENCE_REQUIRED`;
* `INTERPRETIVE`, `NORMATIVE`, `REFUTED`, or `OUT_OF_SCOPE`.

This prevents kernel acceptance of a finite model from being represented as
measurement, independent replication, physical correspondence, or scientific
consensus.

## Reproduction

```sh
cd formalization/QIKVRT_Formalization_v2.0
python3 -B scripts/verify_universal_ontology.py
lake build QIKVRTUniversalOntology
lake env lean QIKVRTUniversalOntology/AxiomAudit.lean
```

The exact-head workflow creates an execution-bound receipt only after all three
commands succeed. `PASS`, `FINAL_PASS`, and `EFFECT_ACK_DONE` remain outside the
finite-model receipt.

## Shell-only fallback acquisition boundary

The shell-only fallback has one bounded network attempt to acquire the declared
Lean release. It does not use a retry/backoff loop or an implicit replacement
source. A failed fetch is recorded as `HOLD_LEAN_SINGLE_FETCH_FAILED`; an
undersized, unextractable, or version-mismatched archive is `BLOCK`. Each path
writes `QIKVRT_UNIVERSAL_ONTOLOGY_LEAN_ACQUISITION_RECEIPT_V1` as an Actions
artifact with `attempts = 1` and `retry_policy = NONE`.

The repository toolchain currently declares Lean through a version contract,
not an archive-SHA lock. The receipt therefore records the observed archive
SHA-256 and the observed Lean version; it does not represent that observation
as a release signature, an external effect, or a proof beyond the exact
workflow run.
