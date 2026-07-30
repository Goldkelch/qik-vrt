<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Proposed Zenodo fileset

State: `CANDIDATE_PREPUBLICATION`

No upload is authorized by this file. The final v2 `publish-request.json` must
bind each selected file to its exact Git blob and include the
machine-proof bundle itself.

## Primary and reproducibility files

- `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf`
- `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex`
- `README.md`
- `EVIDENCE_BOUNDARY.md`
- `CLAIM_MATRIX.json`
- `CLAIM_MATRIX_H0_PENDING.json`
- `SOURCE_EVIDENCE_BINDINGS.json`
- `KERNEL_PROOF_PLAN.json`
- `KERNEL_RECEIPT.json`
- `KERNEL_EVIDENCE_H0_PENDING.json`
- `KERNEL_EVIDENCE_H1_TARGET.json`
- `BOUNDARY_TEST_REPORT.json`
- `PDF_RENDER_VALIDATION.json`
- `CHANGE_NOTICE.md`
- `ORIGINAL_THESIS_TRANSCRIPT.md`
- `CITATION.cff`
- `LICENSE_NOTICE.md`
- `ZENODO_FILESET.md`
- `ZENODO_SHA256SUMS`

## Required prepublication proof files

The following files do not exist until their prerequisites are satisfied:

- `PREPUBLICATION_RETURN_RECEIPT.json` after the exact candidate is returned to
  Ingolf Lohmann;
- `MACHINE_PROOF_BUNDLE.json` after every claim and referenced artifact is
  bound to that returned candidate.

Both are mandatory members of the actual upload fileset. Erst danach kann die
repositoryseitige Owner-Autorisierung den exakten Bundle-Hash und Upload-Scope
freigeben; das v2-`publish-request.json` bindet wiederum diese einmalige
Autorisierung. Owner-Autorisierung und Publish-Request sind mandatory Gates,
werden aber nicht hochgeladen. Jede Inhaltskorrektur nach der Rückgabe
erfordert eine sichtbare `CHANGE_NOTICE.md`, neue Hashes und eine neue
kandidatenspezifische Autorisierung.

The Apache-2.0 Lean source remains in the linked repository and is bound by
the kernel receipt. The IETF XML/TXT/HTML are excluded from the Zenodo paper
record because they have a separate legal and publication lifecycle.
