# QCE measurement-independence / superdeterminism boundary

Status: **formalization candidate; physical exclusion not claimed**.

This tranche connects the QIK-VRT world-formula epistemic boundary to the Bell measurement-independence question.

## Kernel claims

1. `MeasurementIndependent M -> ¬ SuperdeterministicCandidate M`.
2. A finite common-cause support model has structurally local two-wing response functions while violating measurement independence.
3. Therefore local/spacelike response structure alone is insufficient to derive measurement independence.
4. `QCEFreedomCertificate M` is the explicit outstanding obligation required before a QCE-level formal exclusion can be promoted.

## Physical boundary

The Lean kernel does **not** establish that nature satisfies measurement independence. The repository must not infer

`Nature |= ¬Superdeterminism`

from the conditional formal theorem alone. Physical qualification requires an interpretation/reference map and evidence in the sense of `QIKVRT.V2.WorldFormula.PhysicallyQualified`.

## Files

- `PAPER.tex` — mathematical/scientific technical note.
- `WHATSAPP_DE.md` — generally understandable WhatsApp-optimized German article.
- `formalization/.../QuantumFoundations/MeasurementIndependence.lean` — formal definitions, conditional theorem and countermodel.
- `formalization/.../QuantumFoundations/AxiomAudit.lean` — axiom audit.
- `.github/workflows/qikvrt_measurement_independence_formalization.yml` — exact-head Lean 4.19 verification and execution-bound receipt generation.

## External literature

- Stanford Encyclopedia of Philosophy, *Bell's Theorem*: https://plato.stanford.edu/entries/bell-theorem/
- Kim et al., *Delayed “Choice” Quantum Eraser*, Phys. Rev. Lett. 84, 1 (2000), DOI 10.1103/PhysRevLett.84.1.
- Chaves, Lemos, Pienaar, *Causal Modeling the Delayed-Choice Experiment*, Phys. Rev. Lett. 120, 190401 (2018), DOI 10.1103/PhysRevLett.120.190401.
- BIG Bell Test Collaboration, *Challenging local realism with human choices*, Nature 557, 212–216 (2018), DOI 10.1038/s41586-018-0085-3.
- Hossenfelder & Palmer, *Rethinking Superdeterminism*, arXiv:1912.06462.

## Existing QIK-VRT provenance

The repository already contains a verified Zenodo publication receipt for the pre-spacetime ontology tranche:

- DOI: `10.5281/zenodo.21804399`
- repository receipt: `evidence/receipts/zenodo/pre-spacetime-ontology-2026-08-05-publication.json`

This new tranche is intended to be published only after an exact-head Lean receipt exists and the repository's Zenodo pre-effect gates are satisfied.

## IETF disposition

No wire-format, state-machine, DONE predicate, security rule, or interoperability requirement of the Effect Acknowledgement protocol is changed by this mathematical result. Therefore the appropriate current IETF disposition is `NO_PROTOCOL_CHANGE_REQUIRED`; a new IETF submission would be unjustified unless a later implementation introduces an actual normative protocol delta.
