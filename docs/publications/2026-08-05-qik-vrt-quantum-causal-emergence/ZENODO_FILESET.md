<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Vorgesehenes Zenodo-Fileset

Die Veröffentlichung darf erst nach erfolgreicher Repository-Prüfung, einem
source- und commit-gebundenen Lean-Receipt, Authority/Mirror-Scopeprüfung und
ausdrücklicher Owner-Autorisierung materialisiert werden.

## Einzuschließende Artefakte

- `README.md`
- `QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.md`
- `QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.txt`
- `QIK-VRT_QCE_Fachartikel_DE_2026-08-05.md`
- `QIK-VRT_QCE_Fachartikel_DE_2026-08-05.tex`
- `QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf`
- `VRTCore_QCE_Model.lean`
- `VRTCore_QCE_AxiomAudit.lean`
- `lean-toolchain`
- `lakefile.lean`
- `VRTCore_QCE_Syntax.ebnf`
- `QCE_REFERENCE_INSTANCE.vrt`
- `validate_qce_instance.py`
- `test_validate_qce_instance.py`
- `verify_qce_package.py`
- `make_qce_kernel_receipt.py`
- `QCE_KERNEL_RECEIPT.json`
- `QCE_KERNEL_ARTIFACT_PROVENANCE.json`
- `qce-axiom-output.txt`
- `qce-verification.json`
- `CLAIM_MATRIX.json`
- `SOURCE_EVIDENCE_BINDINGS.json`
- `FORMALIZATION_ROADMAP.md`
- `REVIEW_PROTOCOL.md`
- `MACHINE_PROOF_BUNDLE.json`
- `CITATION.cff`
- `LICENSE_MAP.md`
- `ZENODO_METADATA.json`
- `MANIFEST.json`
- `SHA256SUMS`

## Auszuschließen

- `.olean`-Dateien
- temporäre LaTeX-Hilfsdateien
- nicht gebundene Workflow-Logs
- lokale Caches
- ein etwaig erzeugtes `KERNEL_RECEIPT_TEMPLATE.json`; dieses Paket enthält
  stattdessen ausschließlich das ausgeführte Receipt
- Zugangstoken, Zenodo-Secrets und GitHub-Credentials

`ZENODO_UPLOAD = NOT_EXECUTED`
