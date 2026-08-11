#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regenerate QCE MANIFEST.json and SHA256SUMS deterministically."""

from __future__ import annotations

import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parent
EXCLUDED = {"MANIFEST.json", "SHA256SUMS"}

ROLES = {
    "README.md": "package-readme",
    "QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.md": "public-article-markdown",
    "QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.txt": "public-article-whatsapp-native",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.md": "scientific-article-source",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.tex": "scientific-article-typeset-source",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf": "scientific-article-pdf",
    "VRTCore_QCE_Model.lean": "lean-model",
    "VRTCore_QCE_AxiomAudit.lean": "lean-axiom-audit",
    "lean-toolchain": "lean-toolchain-pin",
    "lakefile.lean": "lean-build-definition",
    "VRTCore_QCE_Syntax.ebnf": "formal-syntax",
    "QCE_REFERENCE_INSTANCE.vrt": "reference-instance",
    "validate_qce_instance.py": "reference-validator",
    "test_validate_qce_instance.py": "validator-tests",
    "verify_qce_package.py": "package-verifier",
    "make_qce_kernel_receipt.py": "kernel-receipt-generator",
    "regenerate_qce_integrity.py": "integrity-regenerator",
    "build_zenodo_candidate.py": "zenodo-archive-builder",
    "build_qce_pdf.sh": "pdf-builder",
    "CLAIM_MATRIX.json": "claim-matrix",
    "SOURCE_EVIDENCE_BINDINGS.json": "source-evidence-bindings",
    "QCE_KERNEL_RECEIPT.json": "executed-kernel-receipt",
    "QCE_KERNEL_ARTIFACT_PROVENANCE.json": "executed-kernel-artifact-provenance",
    "qce-axiom-output.txt": "executed-axiom-audit-output",
    "qce-verification.json": "executed-package-verification-output",
    "MACHINE_PROOF_BUNDLE.json": "machine-proof-index",
    "ZENODO_METADATA.json": "zenodo-metadata-candidate",
    "ZENODO_FILESET.md": "zenodo-fileset-plan",
    "ZENODO_LICENSE_NOTICE.md": "zenodo-license-notice",
    "CITATION.cff": "citation-metadata",
    "LICENSE_MAP.md": "license-map",
    "REPRODUCIBILITY.md": "reproduction-guide",
    "FORMALIZATION_ROADMAP.md": "formalization-roadmap",
    "REVIEW_PROTOCOL.md": "review-protocol",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def license_for(path: pathlib.Path) -> str:
    if path.suffix in {".lean", ".py", ".sh"} or path.name == "lakefile.lean":
        return "PolyForm-Noncommercial-1.0.0"
    return "CC-BY-NC-ND-4.0"


def main() -> int:
    files = []
    for path in sorted(ROOT.iterdir()):
        if not path.is_file() or path.name in EXCLUDED:
            continue
        files.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "role": ROLES.get(path.name, "supporting-artifact"),
                "license": license_for(path),
            }
        )

    executed = (ROOT / "QCE_KERNEL_RECEIPT.json").is_file()
    manifest = {
        "schema": "qikvrt-qce-manifest/1.0",
        "publication_id": "qikvrt-quantum-causal-emergence-v1",
        "author": "Ingolf Lohmann",
        "date": "2026-08-05",
        "file_count_excluding_manifest_and_checksum": len(files),
        "files": files,
        "kernel_execution": "EXECUTED_RECEIPT_PRESENT" if executed else "PENDING_REPOSITORY_RUN",
        "physical_correspondence": "OPEN_CANDIDATE",
        "effect_state": "EFFECT_ACK_CONTINUE",
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = []
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{sha256(path)}  {path.name}")
    (ROOT / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_files": len(files), "sha256_entries": len(lines)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
