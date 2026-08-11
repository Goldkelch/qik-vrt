#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build a deterministic QCE Zenodo archive only after all mandatory receipts exist."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile


ROOT = pathlib.Path(__file__).resolve().parent
FIXED_ZIP_TIME = (2026, 8, 5, 0, 0, 0)

FILES = [
    "README.md",
    "QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.md",
    "QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.txt",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.md",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.tex",
    "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf",
    "VRTCore_QCE_Model.lean",
    "VRTCore_QCE_AxiomAudit.lean",
    "lean-toolchain",
    "lakefile.lean",
    "VRTCore_QCE_Syntax.ebnf",
    "QCE_REFERENCE_INSTANCE.vrt",
    "validate_qce_instance.py",
    "test_validate_qce_instance.py",
    "verify_qce_package.py",
    "make_qce_kernel_receipt.py",
    "regenerate_qce_integrity.py",
    "QCE_KERNEL_RECEIPT.json",
    "QCE_KERNEL_ARTIFACT_PROVENANCE.json",
    "qce-axiom-output.txt",
    "qce-verification.json",
    "CLAIM_MATRIX.json",
    "SOURCE_EVIDENCE_BINDINGS.json",
    "MACHINE_PROOF_BUNDLE.json",
    "CITATION.cff",
    "LICENSE_MAP.md",
    "ZENODO_METADATA.json",
    "ZENODO_LICENSE_NOTICE.md",
    "REPRODUCIBILITY.md",
    "FORMALIZATION_ROADMAP.md",
    "REVIEW_PROTOCOL.md",
    "MANIFEST.json",
    "SHA256SUMS",
]


class BuildError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--authorization", type=pathlib.Path, required=True)
    args = parser.parse_args()

    receipt_path = ROOT / "QCE_KERNEL_RECEIPT.json"
    require(receipt_path.is_file(), "executed QCE_KERNEL_RECEIPT.json is required")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("state") == "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE", "kernel receipt is not executed")
    require(receipt["kernel_execution"]["accepted_theorems"] == 36, "kernel receipt does not bind 36 theorems")
    require(receipt["formal_scope"]["physical_correspondence_established"] is False, "receipt improperly promotes physical correspondence")

    authorization = json.loads(args.authorization.read_text(encoding="utf-8"))
    require(authorization.get("authorization_status") == "PRESENT_AND_VALID", "explicit owner authorization is required")
    require(authorization.get("publication_id") == "qikvrt-quantum-causal-emergence-v1", "authorization publication mismatch")

    subprocess.run([sys.executable, "-B", str(ROOT / "regenerate_qce_integrity.py")], cwd=ROOT, check=True)
    for name in FILES:
        require((ROOT / name).is_file(), f"required Zenodo file missing: {name}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (ROOT / name).read_bytes()
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)

    archive_receipt = {
        "schema": "qikvrt-qce-zenodo-archive-receipt/1.0",
        "publication_id": "qikvrt-quantum-causal-emergence-v1",
        "archive": args.output.name,
        "bytes": args.output.stat().st_size,
        "sha256": sha256(args.output),
        "kernel_receipt_sha256": sha256(receipt_path),
        "owner_authorization_sha256": sha256(args.authorization),
        "physical_correspondence": "OPEN_CANDIDATE",
        "upload_executed": False,
        "effect_state": "EFFECT_ACK_CONTINUE",
    }
    receipt_out = args.output.with_suffix(args.output.suffix + ".receipt.json")
    receipt_out.write_text(json.dumps(archive_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(archive_receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error
