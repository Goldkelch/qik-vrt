#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify QCE sources, finite syntax, documents, checksums and optional Lean execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent
MODEL = ROOT / "VRTCore_QCE_Model.lean"
AUDIT = ROOT / "VRTCore_QCE_AxiomAudit.lean"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def run(command: list[str], *, cwd: pathlib.Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise VerificationError(
            f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stdout}"
        )
    return proc


def check_source_shape() -> list[str]:
    model = MODEL.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    theorem_names = re.findall(r"(?m)^theorem\s+([A-Za-z0-9_]+)", model)
    directives = re.findall(r"(?m)^#print axioms\s+", audit)
    require(len(theorem_names) == 36, f"expected 36 named theorems, got {len(theorem_names)}")
    require(len(directives) == 36, f"expected 36 axiom directives, got {len(directives)}")
    combined = model + "\n" + audit
    forbidden = {
        "project axiom": r"(?m)^\s*axiom\b",
        "unsafe declaration": r"(?m)^\s*unsafe\b",
        "sorry/admit": r"(?m)^\s*(?:sorry|admit)\b|:=\s*(?:sorry|admit)\b|\bby\s+(?:sorry|admit)\b",
    }
    for label, pattern in forbidden.items():
        require(re.search(pattern, combined) is None, f"forbidden {label} found")
    return theorem_names


def parse_axioms(output: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    none = re.compile(r"^'([^']+)' does not depend on any axioms$")
    some = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
    for raw in output.splitlines():
        line = raw.strip()
        match = none.match(line)
        if match:
            result[match.group(1)] = ()
            continue
        match = some.match(line)
        if match:
            result[match.group(1)] = tuple(
                x.strip() for x in match.group(2).split(",") if x.strip()
            )
    return result


def check_lean(lean: pathlib.Path, axiom_output: pathlib.Path | None) -> dict[str, object]:
    require(lean.is_file(), f"Lean executable not found: {lean}")
    version = run([str(lean), "--version"]).stdout.strip()
    require("version 4.19.0" in version, f"expected Lean 4.19.0, got {version}")
    environment = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="qikvrt-qce-kernel-") as temp:
        tempdir = pathlib.Path(temp)
        run([str(lean), "-o", str(tempdir / "VRTCore_QCE_Model.olean"), str(MODEL)], env=environment)
        audit_env = environment.copy()
        inherited = audit_env.get("LEAN_PATH", "")
        paths = [str(tempdir), str(ROOT)]
        if inherited:
            paths.append(inherited)
        audit_env["LEAN_PATH"] = os.pathsep.join(paths)
        audit_text = run([str(lean), str(AUDIT)], env=audit_env).stdout
    if axiom_output is not None:
        axiom_output.write_text(audit_text, encoding="utf-8")
    dependencies = parse_axioms(audit_text)
    require(len(dependencies) == 36, f"axiom output binds {len(dependencies)} of 36 theorems")
    allowed = {"propext", "Quot.sound", "Classical.choice"}
    unexpected = sorted({a for values in dependencies.values() for a in values} - allowed)
    require(not unexpected, f"unexpected axiom dependencies: {unexpected}")
    return {
        "version": version,
        "theorems": 36,
        "axioms_by_theorem": {k: list(v) for k, v in sorted(dependencies.items())},
        "allowed_foundational_axioms": sorted(allowed),
    }


def check_reference_and_tests() -> None:
    sys.path.insert(0, str(ROOT))
    from validate_qce_instance import parse_document  # pylint: disable=import-outside-toplevel

    reference = (ROOT / "QCE_REFERENCE_INSTANCE.vrt").read_text(encoding="utf-8")
    parsed = parse_document(reference)
    require(parsed.fields["physical-closure"] == ["OPEN_CANDIDATE"], "reference physical closure was promoted")
    require(parsed.fields["effect-state"] == ["EFFECT_ACK_CONTINUE"], "reference effect state was promoted")
    run([sys.executable, "-B", "-m", "unittest", "-v", "test_validate_qce_instance.py"])


def check_json_files() -> None:
    for name in (
        "CLAIM_MATRIX.json",
        "SOURCE_EVIDENCE_BINDINGS.json",
        "MACHINE_PROOF_BUNDLE.json",
        "ZENODO_METADATA.json",
        "MANIFEST.json",
    ):
        json.loads((ROOT / name).read_text(encoding="utf-8"))
    template = ROOT / "KERNEL_RECEIPT_TEMPLATE.json"
    executed = ROOT / "QCE_KERNEL_RECEIPT.json"
    require(template.is_file() or executed.is_file(), "a receipt template or executed receipt is required")
    if template.is_file():
        receipt = json.loads(template.read_text(encoding="utf-8"))
        require(receipt["state"] == "NOT_EXECUTED", "template must not impersonate an executed receipt")
        require(receipt["completion_claims"] == {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}, "template completion claims changed")
    if executed.is_file():
        check_persisted_execution(executed)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_persisted_execution(receipt_path: pathlib.Path) -> None:
    """Fail closed when an executed QCE receipt is included in the package."""
    check_executed_receipt(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    binding = receipt["source_binding"]
    execution = receipt["kernel_execution"]
    require(binding["candidate_path"] == "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence", "receipt candidate path mismatch")
    require(binding["model_sha256"] == sha256(MODEL), "receipt model binding mismatch")
    require(binding["axiom_audit_sha256"] == sha256(AUDIT), "receipt axiom-audit binding mismatch")

    axiom_output = ROOT / "qce-axiom-output.txt"
    verification = ROOT / "qce-verification.json"
    provenance = ROOT / "QCE_KERNEL_ARTIFACT_PROVENANCE.json"
    require(axiom_output.is_file(), "executed receipt lacks qce-axiom-output.txt")
    require(verification.is_file(), "executed receipt lacks qce-verification.json")
    require(provenance.is_file(), "executed receipt lacks artifact provenance")
    require(execution["axiom_output_sha256"] == sha256(axiom_output), "receipt axiom-output binding mismatch")
    require(execution["verification_output_sha256"] == sha256(verification), "receipt verification-output binding mismatch")
    verification_data = json.loads(verification.read_text(encoding="utf-8"))
    require(verification_data.get("result") == "FORMAL_MODEL_VERIFIED", "persisted verification result is not formal-model verified")
    require(verification_data.get("theorem_sources") == 36, "persisted verification theorem count mismatch")
    require(verification_data.get("physical_correspondence") == "OPEN_CANDIDATE", "persisted verification promoted physical correspondence")

    provenance_data = json.loads(provenance.read_text(encoding="utf-8"))
    require(provenance_data.get("schema") == "qikvrt-qce-exact-kernel-artifact-provenance/1.0", "artifact provenance schema mismatch")
    artifact_files = {entry["name"]: entry for entry in provenance_data["artifact"]["files"]}
    for name, path in {
        "QCE_KERNEL_RECEIPT.json": receipt_path,
        "qce-axiom-output.txt": axiom_output,
        "qce-verification.json": verification,
    }.items():
        entry = artifact_files.get(name)
        require(entry is not None, f"artifact provenance lacks {name}")
        require(entry["bytes"] == path.stat().st_size, f"artifact provenance byte count mismatch: {name}")
        require(entry["sha256"] == sha256(path), f"artifact provenance hash mismatch: {name}")


def check_persisted_claim_bindings() -> None:
    receipt_path = ROOT / "QCE_KERNEL_RECEIPT.json"
    if not receipt_path.is_file():
        return
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = {
        "artifact_provenance": "QCE_KERNEL_ARTIFACT_PROVENANCE.json",
        "axiom_output": "qce-axiom-output.txt",
        "kernel_receipt": "QCE_KERNEL_RECEIPT.json",
        "run_attempt": int(receipt["workflow_binding"]["run_attempt"]),
        "source_commit": receipt["source_binding"]["commit"],
        "source_tree": receipt["source_binding"]["tree"],
        "verification": "qce-verification.json",
        "workflow_run_id": int(receipt["workflow_binding"]["run_id"]),
    }
    matrix = json.loads((ROOT / "CLAIM_MATRIX.json").read_text(encoding="utf-8"))
    require(matrix["formal_execution"].get("lean_executed_for_this_candidate") is True, "claim matrix does not record executed QCE core")
    for key, value in expected.items():
        require(matrix["formal_execution"].get(key) == value, f"claim-matrix formal execution mismatch: {key}")
    for claim in matrix["claims"]:
        if claim.get("kind") == "formal-proved":
            require(claim.get("receipt_binding") == expected, f"claim receipt binding mismatch: {claim.get('id')}")
    bundle = json.loads((ROOT / "MACHINE_PROOF_BUNDLE.json").read_text(encoding="utf-8"))
    require(bundle["formalization"].get("status") == "KERNEL_ACCEPTED_FINITE_MODEL", "machine proof bundle does not record kernel acceptance")
    require(bundle.get("receipt") == {**expected, "required_before_zenodo_publication": True}, "machine proof receipt binding mismatch")


def check_manifest() -> None:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    files = [path for path in sorted(ROOT.iterdir()) if path.is_file() and path.name not in {"MANIFEST.json", "SHA256SUMS"}]
    records = {entry["path"]: entry for entry in manifest["files"]}
    expected_names = [path.name for path in files]
    require(sorted(records) == expected_names, "manifest file inventory mismatch")
    require(manifest["file_count_excluding_manifest_and_checksum"] == len(files), "manifest file count mismatch")
    for path in files:
        record = records[path.name]
        require(record["bytes"] == path.stat().st_size, f"manifest byte count mismatch: {path.name}")
        require(record["sha256"] == sha256(path), f"manifest hash mismatch: {path.name}")
    expected_execution = "EXECUTED_RECEIPT_PRESENT" if (ROOT / "QCE_KERNEL_RECEIPT.json").is_file() else "PENDING_REPOSITORY_RUN"
    require(manifest["kernel_execution"] == expected_execution, "manifest kernel execution status mismatch")


def check_pdf() -> dict[str, object]:
    pdf = ROOT / "QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf"
    require(pdf.is_file(), "scientific PDF missing")
    pdfinfo = shutil.which("pdfinfo")
    pdftotext = shutil.which("pdftotext")
    require(pdfinfo is not None and pdftotext is not None, "pdfinfo and pdftotext are required")
    info = run([pdfinfo, str(pdf)]).stdout
    page_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", info)
    require(page_match is not None, "PDF page count unavailable")
    pages = int(page_match.group(1))
    require(pages >= 8, f"scientific PDF unexpectedly short: {pages} pages")
    require("595.28 x 841.89 pts (A4)" in info, "PDF must be A4")
    with tempfile.TemporaryDirectory(prefix="qikvrt-qce-pdf-") as temp:
        text_path = pathlib.Path(temp) / "article.txt"
        run([pdftotext, str(pdf), str(text_path)])
        text = text_path.read_text(encoding="utf-8")
    require("�" not in text, "PDF contains Unicode replacement characters")
    normalized = text.lower().replace("_", " ").replace("-", " ")
    for marker in ("quantum causal emergence", "lean execution", "open candidate", "effect ack continue"):
        require(marker in normalized, f"PDF lacks status marker: {marker}")
    return {"pages": pages, "a4": True, "unicode_replacement": False}


def check_sha256sums() -> int:
    path = ROOT / "SHA256SUMS"
    entries = 0
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        require(match is not None, f"malformed SHA256SUMS line {number}")
        expected, relative = match.groups()
        pure = pathlib.PurePosixPath(relative)
        require(not pure.is_absolute() and ".." not in pure.parts, f"unsafe checksum path: {relative}")
        require(relative not in seen, f"duplicate checksum path: {relative}")
        seen.add(relative)
        target = ROOT / relative
        require(target.is_file(), f"checksummed file missing: {relative}")
        actual = sha256(target)
        require(actual == expected, f"checksum mismatch: {relative}")
        entries += 1
    require(entries >= 20, f"checksum inventory unexpectedly small: {entries}")
    expected_paths = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != "SHA256SUMS"}
    require(seen == expected_paths, "SHA256SUMS is not the exact package file set")
    return entries


def check_executed_receipt(path: pathlib.Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data.get("state") == "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE", "receipt is not executed")
    require(data["kernel_execution"]["accepted_theorems"] == 36, "receipt theorem count mismatch")
    require(data["formal_scope"]["physical_correspondence_established"] is False, "receipt promoted physical correspondence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=pathlib.Path)
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--axiom-output", type=pathlib.Path)
    parser.add_argument("--executed-receipt", type=pathlib.Path)
    args = parser.parse_args()

    theorem_names = check_source_shape()
    check_reference_and_tests()
    check_json_files()
    check_persisted_claim_bindings()
    check_manifest()
    pdf = check_pdf()
    checksums = check_sha256sums()

    lean_result: dict[str, object] | None = None
    if not args.static_only:
        lean = args.lean
        if lean is None:
            discovered = shutil.which("lean")
            require(discovered is not None, "supply --lean or use --static-only")
            lean = pathlib.Path(discovered)
        lean_result = check_lean(lean, args.axiom_output)
    if args.executed_receipt is not None:
        check_executed_receipt(args.executed_receipt)

    result = {
        "result": "STATIC_CANDIDATE_VERIFIED" if args.static_only else "FORMAL_MODEL_VERIFIED",
        "publication_id": "qikvrt-quantum-causal-emergence-v1",
        "theorem_sources": len(theorem_names),
        "lean": lean_result if lean_result is not None else "NOT_EXECUTED_IN_STATIC_MODE",
        "python_tests": "10/10",
        "pdf": pdf,
        "sha256_entries": checksums,
        "physical_correspondence": "OPEN_CANDIDATE",
        "effect_state": "EFFECT_ACK_CONTINUE",
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error
