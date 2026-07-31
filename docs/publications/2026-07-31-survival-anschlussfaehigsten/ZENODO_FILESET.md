<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Proposed Zenodo fileset

State: `FROZEN_CANDIDATE_AWAITING_EXACT_OWNER_AUTHORIZATION`

This file does not authorize an upload. The actual v2 publish request must bind
every selected file to its exact Git blob, SHA-256 digest and candidate-bound
owner authorization.

## Primary files

- `Survival_der_Anschlussfaehigsten_2026-07-31.pdf`
- `Survival_der_Anschlussfaehigsten_2026-07-31.tex`
- `ARTICLE_DE.md`
- `CANONICAL_STATEMENT.md`
- `ORIGINAL_THESIS_TRANSCRIPT.md`
- `CHANGE_NOTICE.md`
- `README.md`
- `EVIDENCE_BOUNDARY.md`
- `CLAIM_MATRIX.json`
- `CLAIM_MATRIX_H0_PENDING.json`
- `CLAIM_MATRIX_H1_FIT_VERIFIED.json`
- `CLAIM_MATRIX_H2_FULL_PENDING.json`
- `SOURCE_EVIDENCE_BINDINGS.json`
- `KERNEL_PROOF_PLAN.json`
- `KERNEL_EVIDENCE_H0_PENDING.json`
- `KERNEL_EVIDENCE_H1_TARGET.json`
- `KERNEL_EVIDENCE_H2_FULL_PENDING.json`
- `KERNEL_EVIDENCE_H3_FULL_TARGET.json`
- `FORMAL_OperationalContinuation.lean`
- `FORMAL_ConnectabilitySimulation.lean`
- `FORMAL_WeightedConnectability.lean`
- `FORMAL_SOURCE_SNAPSHOT.json`
- `BOUNDARY_TEST_REPORT.json`
- `KERNEL_RECEIPT.json`
- `MACHINE_PROOF_BUNDLE.json`
- `PREPUBLICATION_RETURN_RECEIPT.json`
- `PDF_RENDER_VALIDATION.json`
- `CITATION.cff`
- `LICENSE_NOTICE.md`
- `ZENODO_FILESET.md`
- `ZENODO_SHA256SUMS`

The authoritative Lean sources remain in the linked repositories and are
bound by the kernel receipt and machine-proof bundle. Byte-identical source
snapshots are included in this fileset so that the archive remains
self-contained. The machine-proof bundle can establish upload eligibility;
it is not the natural-person authorization required by policy. Until the exact
return, metadata and bundle hashes are authorized after candidate return, the
production upload gate remains fail-closed.
