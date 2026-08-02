#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Verify the H6 virtual-sphere package and reproduce its Lean result.

The verifier is deliberately fail-closed.  It requires exact equality between
the directory, manifest and checksum inventories; compiles the source twice;
compares both results to the persisted ``.olean``; reruns the complete axiom
audit twice; and preserves the PhysicalClosure/effect boundaries.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from xml.etree import ElementTree


ROOT = pathlib.Path(__file__).resolve().parent
LEAN_SOURCE = ROOT / "VRTCore_VirtualSphere.lean"
AXIOM_SOURCE = ROOT / "VRTCore_VirtualSphere_AxiomAudit.lean"
PERSISTED_OLEAN = ROOT / "VRTCore_VirtualSphere.olean"
TOP_THEOREM = (
    "QIKVRT.VRTCore.VirtualSphereH6.h6_virtualSphere_noHole_complete"
)
EXPECTED_THEOREMS = 55
EXPECTED_AXIOM_COUNTS = {
    (): 24,
    ("propext",): 19,
    ("propext", "Quot.sound"): 2,
    ("propext", "Classical.choice", "Quot.sound"): 10,
}
CHAIN_FILES = {"MANIFEST.json", "H6_LOCAL_KERNEL_RECEIPT.json",
               "SHA256SUMS", "PACKAGE_ROOT.sha256"}


class VerificationError(RuntimeError):
    """A declared H6 verification condition failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(name: str) -> dict[str, Any]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{name} must contain a JSON object")
    return value


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if process.returncode != 0:
        raise VerificationError(
            f"command failed ({process.returncode}): {' '.join(command)}\n"
            f"{process.stdout}"
        )
    return process


def safe_inventory_path(relative: str) -> pathlib.PurePosixPath:
    path = pathlib.PurePosixPath(relative)
    require(relative == path.as_posix(), f"non-canonical inventory path: {relative}")
    require(not path.is_absolute() and ".." not in path.parts,
            f"unsafe inventory path: {relative}")
    require(len(path.parts) == 1, f"H6 inventory must be flat: {relative}")
    return path


def check_manifest_and_fixity() -> dict[str, Any]:
    manifest = load_json("MANIFEST.json")
    inventory_entries = manifest.get("inventory")
    payload_entries = manifest.get("payload")
    require(isinstance(inventory_entries, list), "manifest inventory must be a list")
    require(isinstance(payload_entries, list), "manifest payload must be a list")

    inventory_paths: list[str] = []
    for entry in inventory_entries:
        require(isinstance(entry, dict) and isinstance(entry.get("path"), str),
                "every inventory entry needs a path")
        relative = entry["path"]
        safe_inventory_path(relative)
        inventory_paths.append(relative)
    require(len(inventory_paths) == len(set(inventory_paths)),
            "duplicate manifest inventory path")

    directory_files = {item.name for item in ROOT.iterdir() if item.is_file()}
    directory_directories = {item.name for item in ROOT.iterdir() if item.is_dir()}
    require(not directory_directories,
            f"unexpected directories in exact H6 package: {sorted(directory_directories)}")
    require(set(inventory_paths) == directory_files,
            "manifest inventory and package directory differ: "
            f"missing={sorted(set(inventory_paths) - directory_files)}, "
            f"extra={sorted(directory_files - set(inventory_paths))}")
    require(CHAIN_FILES <= directory_files, "fixity chain files are incomplete")

    payload_paths: list[str] = []
    canonical_lines: list[str] = []
    for entry in payload_entries:
        require(isinstance(entry, dict), "every payload entry must be an object")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_bytes = entry.get("bytes")
        require(isinstance(relative, str), "payload path missing")
        safe_inventory_path(relative)
        require(relative not in CHAIN_FILES,
                f"self-referential chain file cannot be payload: {relative}")
        require(re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)) is not None,
                f"invalid payload digest: {relative}")
        require(isinstance(expected_bytes, int) and expected_bytes >= 0,
                f"invalid payload size: {relative}")
        target = ROOT / relative
        require(target.is_file(), f"payload file missing: {relative}")
        actual = target.read_bytes()
        require(len(actual) == expected_bytes, f"payload size mismatch: {relative}")
        require(sha256_bytes(actual) == expected_hash,
                f"payload checksum mismatch: {relative}")
        payload_paths.append(relative)
        canonical_lines.append(f"{expected_hash}  {relative}\n")
    require(len(payload_paths) == len(set(payload_paths)), "duplicate payload path")
    require(set(payload_paths) == directory_files - CHAIN_FILES,
            "manifest payload is not the exact non-chain inventory")
    canonical_payload = "".join(sorted(canonical_lines)).encode("utf-8")
    payload_root = sha256_bytes(canonical_payload)
    require(manifest.get("payload_root_sha256") == payload_root,
            "manifest payload root mismatch")

    checksum_lines = (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    checksum_map: dict[str, str] = {}
    for number, line in enumerate(checksum_lines, 1):
        require(line != "", f"blank SHA256SUMS line {number}")
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        require(match is not None, f"malformed SHA256SUMS line {number}")
        digest, relative = match.groups()
        safe_inventory_path(relative)
        require(relative not in checksum_map, f"duplicate checksum path: {relative}")
        checksum_map[relative] = digest
    expected_checksum_paths = directory_files - {"SHA256SUMS", "PACKAGE_ROOT.sha256"}
    require(set(checksum_map) == expected_checksum_paths,
            "checksum inventory is not exact")
    for relative, expected_hash in checksum_map.items():
        require(sha256_file(ROOT / relative) == expected_hash,
                f"SHA256SUMS mismatch: {relative}")

    root_match = re.fullmatch(
        r"([0-9a-f]{64})  SHA256SUMS\n?",
        (ROOT / "PACKAGE_ROOT.sha256").read_text(encoding="ascii"),
    )
    require(root_match is not None, "malformed PACKAGE_ROOT.sha256")
    package_root = sha256_file(ROOT / "SHA256SUMS")
    require(root_match.group(1) == package_root, "package root mismatch")

    require(manifest.get("self_inclusion_claimed") is False,
            "manifest must not claim impossible self-inclusion")
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_file(ROOT / "MANIFEST.json"),
        "payload_root_sha256": payload_root,
        "package_root_sha256": package_root,
        "inventory_count": len(directory_files),
        "checksum_count": len(checksum_map),
    }


def check_source_shape() -> dict[str, Any]:
    lean_text = LEAN_SOURCE.read_text(encoding="utf-8")
    audit_text = AXIOM_SOURCE.read_text(encoding="utf-8")
    theorem_names = re.findall(r"(?m)^theorem\s+([A-Za-z][A-Za-z0-9_]*)", lean_text)
    audit_names = re.findall(
        r"(?m)^#print axioms\s+QIKVRT\.VRTCore\.VirtualSphereH6\."
        r"([A-Za-z][A-Za-z0-9_]*)\s*$",
        audit_text,
    )
    require(len(theorem_names) == EXPECTED_THEOREMS,
            f"expected {EXPECTED_THEOREMS} theorems, got {len(theorem_names)}")
    require(len(audit_names) == EXPECTED_THEOREMS,
            f"expected {EXPECTED_THEOREMS} audit directives, got {len(audit_names)}")
    require(len(set(theorem_names)) == EXPECTED_THEOREMS,
            "duplicate theorem declaration")
    require(set(theorem_names) == set(audit_names),
            "axiom audit does not cover exactly every H6 theorem")
    require("theorem h6_virtualSphere_noHole_complete " in lean_text,
            "top theorem missing")
    require("(binding : ExactArtifactBinding)" in lean_text,
            "external byte-binding boundary missing from top theorem")
    forbidden = {
        "project-local axiom": r"(?m)^\s*axiom\s+",
        "unsafe declaration": r"(?m)^\s*unsafe\s+",
        "sorry/admit": (
            r"(?m)^\s*(?:sorry|admit)\b|:=\s*(?:sorry|admit)\b|"
            r"\bby\s+(?:sorry|admit)\b"
        ),
    }
    combined = lean_text + "\n" + audit_text
    for label, pattern in forbidden.items():
        require(re.search(pattern, combined) is None, f"forbidden {label} found")
    return {"theorem_names": theorem_names, "audit_names": audit_names}


def parse_axiom_output(output: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for name in re.findall(
        r"'([^']+)' does not depend on any axioms", output
    ):
        result[name] = ()
    for name, body in re.findall(
        r"'([^']+)' depends on axioms: \[(.*?)\]", output, flags=re.DOTALL
    ):
        axioms = tuple(item.strip() for item in body.split(",") if item.strip())
        require(name not in result, f"duplicate axiom output: {name}")
        result[name] = axioms
    return result


def check_runtime_file(path: pathlib.Path, expected: str, label: str) -> None:
    require(path.is_file(), f"{label} missing: {path}")
    require(sha256_file(path) == expected, f"{label} digest mismatch")


def check_lean(
    lean: pathlib.Path,
    preload: pathlib.Path | None,
    trust: dict[str, Any],
) -> dict[str, Any]:
    runtime = trust["runtime_artifacts"]
    check_runtime_file(lean, runtime["lean_executable_sha256"], "Lean executable")
    environment = os.environ.copy()
    if preload is not None:
        check_runtime_file(
            preload, runtime["compatibility_preload_sha256"], "compatibility preload"
        )
        environment["LD_PRELOAD"] = str(preload)
    else:
        require(runtime.get("compatibility_preload_required") is False,
                "trust base must declare compatibility_preload_required=false "
                "when --preload is omitted")

    version = run([str(lean), "--version"], env=environment).stdout.strip()
    require(version == trust["logic"]["lean_version"],
            f"Lean version mismatch: {version}")
    prefix = lean.parent.parent
    check_runtime_file(prefix / "lib/lean/Init.olean",
                       runtime["init_olean_sha256"], "Init.olean")
    check_runtime_file(prefix / "lib/lean/Std.olean",
                       runtime["std_olean_sha256"], "Std.olean")

    with tempfile.TemporaryDirectory(prefix="qikvrt-h6-reproduce-") as temporary:
        temporary_root = pathlib.Path(temporary)
        module_dirs = [temporary_root / "pass1", temporary_root / "pass2"]
        for module_dir in module_dirs:
            module_dir.mkdir()
        compiled: list[bytes] = []
        audit_outputs: list[str] = []
        for module_dir in module_dirs:
            output = module_dir / "VRTCore_VirtualSphere.olean"
            run(
                [str(lean), "-o", str(output), LEAN_SOURCE.name],
                env=environment,
            )
            compiled.append(output.read_bytes())
            audit_environment = environment.copy()
            inherited = audit_environment.get("LEAN_PATH", "")
            paths = [str(module_dir)]
            if inherited:
                paths.append(inherited)
            audit_environment["LEAN_PATH"] = os.pathsep.join(paths)
            audit_outputs.append(
                run([str(lean), AXIOM_SOURCE.name], env=audit_environment).stdout
            )

    require(compiled[0] == compiled[1], "double compile produced different .olean bytes")
    require(compiled[0] == PERSISTED_OLEAN.read_bytes(),
            "fresh .olean differs from persisted package artifact")
    require(audit_outputs[0] == audit_outputs[1],
            "double axiom audit produced different output")
    dependencies = parse_axiom_output(audit_outputs[0])
    require(len(dependencies) == EXPECTED_THEOREMS,
            "axiom output does not bind all H6 theorems")
    counts = collections.Counter(dependencies.values())
    require(dict(counts) == EXPECTED_AXIOM_COUNTS,
            f"unexpected axiom distribution: {dict(counts)}")
    allowed = set(trust["logic"]["allowed_foundational_axioms"])
    observed = {axiom for axioms in dependencies.values() for axiom in axioms}
    require(observed <= allowed, f"undeclared axiom dependency: {sorted(observed - allowed)}")
    require(dependencies.get(TOP_THEOREM) == tuple(trust["logic"]["top_theorem_axioms"]),
            "top theorem axiom dependency mismatch")
    return {
        "version": version,
        "olean_sha256": sha256_bytes(compiled[0]),
        "audit_stdout_sha256": sha256_bytes(audit_outputs[0].encode("utf-8")),
        "axiom_counts": {
            "none": counts[()],
            "propext": counts[("propext",)],
            "propext+Quot.sound": counts[("propext", "Quot.sound")],
            "propext+Classical.choice+Quot.sound": counts[
                ("propext", "Classical.choice", "Quot.sound")
            ],
        },
    }


def check_documents() -> dict[str, Any]:
    claim = load_json("CLAIM_MATRIX.json")
    bindings = load_json("SOURCE_EVIDENCE_BINDINGS.json")
    trust = load_json("TRUST_BASE.json")
    load_json("COMMANDS.json")

    grammar = (ROOT / "VRTCore_VirtualSphere_Syntax.ebnf").read_text(encoding="utf-8")
    obligations = {int(value) for value in re.findall(r"H6-S(\d{2})\.", grammar)}
    require(obligations == set(range(1, 40)), "EBNF must contain exactly H6-S01..H6-S39")
    require("surface-parser-status" in grammar and "not-kernel-proved" in grammar,
            "surface-parser boundary missing")
    require("VirtualClosureCertificate and PhysicalClosureEvidence" in grammar,
            "virtual/physical type boundary missing")

    reference = (ROOT / "H6_REFERENCE_OBJECT.vsphere").read_text(encoding="utf-8")
    required_reference = [
        "kernel-result = audit-accepted;",
        "projection-theorem = kernelClosureProjection_all_true;",
        "byte-bound = true;",
        "result = VIRTUAL_CLOSURE_TRUE;",
        "kernel-model-closure-status = kernel-proved;",
        "receipt-bound-package-closure-status = kernel-proved;",
        "physical-closure-status = open;",
        "virtual-to-physical-promotion = false;",
        "ordinary-release = false;",
        "external-mutation = false;",
        "effect-state = EFFECT_ACK_CONTINUE;",
    ]
    for text in required_reference:
        require(text in reference, f"reference object lacks: {text}")
    require("TO_BE_BOUND" not in reference and "pending-receipt" not in reference,
            "reference object still contains unresolved binding markers")

    closure = claim["closure_state"]
    require(
        closure["VirtualClosure"]["receipt_bound_package_status"] ==
        "VIRTUAL_CLOSURE_TRUE_RELATIVE_TO_DECLARED_H6_MODEL_AND_RECEIPT",
        "claim matrix does not bind package VirtualClosure",
    )
    require(closure["PhysicalClosure"]["status"] == "OPEN",
            "PhysicalClosure must remain OPEN")
    release = claim["release_claims"]
    require(release == {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "external_mutation": False,
    }, "release boundary changed")
    require(claim["kernel_audit_summary"]["exact_byte_receipt"] ==
            "BOUND_AND_VERIFIED_LOCALLY",
            "claim matrix receipt status is not final")
    require(bindings["binding_status"] == "EXACT_BYTE_BINDING_VERIFIED_LOCALLY",
            "source-evidence binding is not final")
    require(bindings["local_kernel_observation"]["package_byte_binding"] ==
            "BOUND_AND_VERIFIED_LOCALLY",
            "source-evidence package binding is not final")

    article = (ROOT / "QIK-VRT_VirtualSphere_NoHole_DE.md").read_text(encoding="utf-8")
    for text in (
        "VIRTUAL_CLOSURE_SCOPE = PASS",
        "PHYSICAL_CLOSURE = OPEN",
        "EFFECT_STATE = EFFECT_ACK_CONTINUE",
    ):
        require(text in article, f"article status boundary missing: {text}")
    require("PENDING_KERNEL_AUDIT" not in article,
            "article still contains pre-audit status")

    svg = ROOT / "VRTCore_VirtualSphere_EBNF_Map_DE.svg"
    ElementTree.parse(svg)
    svg_text = svg.read_text(encoding="utf-8")
    require("<script" not in svg_text.lower(), "SVG scripts are prohibited")
    require(re.search(r"(?:href|xlink:href)=['\"]https?://", svg_text) is None,
            "SVG external references are prohibited")
    return {"claim": claim, "bindings": bindings, "trust": trust}


def check_receipt(
    fixity: dict[str, Any],
    lean_result: dict[str, Any],
) -> dict[str, Any]:
    receipt = load_json("H6_LOCAL_KERNEL_RECEIPT.json")
    artifact = receipt["artifact_binding"]
    expected = {
        "manifest_sha256": fixity["manifest_sha256"],
        "payload_root_sha256": fixity["payload_root_sha256"],
        "lean_source_sha256": sha256_file(LEAN_SOURCE),
        "axiom_audit_source_sha256": sha256_file(AXIOM_SOURCE),
        "persisted_olean_sha256": sha256_file(PERSISTED_OLEAN),
        "trust_base_sha256": sha256_file(ROOT / "TRUST_BASE.json"),
        "commands_sha256": sha256_file(ROOT / "COMMANDS.json"),
        "top_theorem_statement_sha256": top_theorem_statement_digest(),
    }
    for key, value in expected.items():
        require(artifact.get(key) == value, f"receipt binding mismatch: {key}")
    require(
        artifact.get("package_root_sha256") ==
        "BOUND_EXTERNALLY_BY_PACKAGE_ROOT.sha256",
        "receipt must not claim a self-referential package-root digest",
    )
    require(artifact["persisted_olean_sha256"] == lean_result["olean_sha256"],
            "receipt .olean does not match reproduction")
    kernel = receipt["kernel_execution"]
    require(kernel["named_theorems"] == EXPECTED_THEOREMS and
            kernel["accepted_theorems"] == EXPECTED_THEOREMS and
            kernel["audit_directives"] == EXPECTED_THEOREMS,
            "receipt theorem counts mismatch")
    require(kernel["compile_runs"] == 2 and kernel["audit_runs"] == 2,
            "receipt does not record double execution")
    require(kernel["double_compile_byte_identical"] is True and
            kernel["double_audit_output_identical"] is True,
            "receipt double-execution identity missing")
    require(kernel["audit_stdout_sha256"] == lean_result["audit_stdout_sha256"],
            "receipt audit output digest mismatch")
    require(kernel["axiom_counts"] == lean_result["axiom_counts"],
            "receipt axiom counts mismatch")
    require(receipt["scope_result"] == {
        "virtual_closure_scope": "PASS",
        "physical_closure": "OPEN",
        "physical_big_bang_identity": "NOT_CLAIMED",
        "independent_external_reproduction": "OPEN",
        "global_pass": False,
        "final_pass": False,
        "effect_ack_done": False,
        "effect_state": "EFFECT_ACK_CONTINUE",
    }, "receipt scope boundary mismatch")
    require(receipt["external_effects"] == {
        "remote_mutation_performed": False,
        "github_mutated": False,
        "zenodo_mutated": False,
        "ietf_datatracker_mutated": False,
        "external_publication_claimed": False,
    }, "receipt external-effect boundary mismatch")
    require(receipt["self_reference"]["self_inclusion_claimed"] is False,
            "receipt must not claim self-inclusion")
    require(receipt["self_reference"]["receipt_bound_by"] == "SHA256SUMS",
            "receipt must be externally checksummed")
    return receipt


def top_theorem_statement_digest() -> str:
    source = LEAN_SOURCE.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^theorem h6_virtualSphere_noHole_complete .*? := by\n",
        source,
    )
    require(match is not None, "cannot isolate top theorem statement")
    statement = match.group(0).removesuffix(" := by\n") + "\n"
    return sha256_bytes(statement.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lean",
        type=pathlib.Path,
        default=(pathlib.Path(os.environ["QIKVRT_LEAN"])
                 if "QIKVRT_LEAN" in os.environ else None),
        help="path to the receipt-bound Lean 4.19.0 executable",
    )
    parser.add_argument(
        "--preload",
        type=pathlib.Path,
        default=(pathlib.Path(os.environ["QIKVRT_LEAN_PRELOAD"])
                 if "QIKVRT_LEAN_PRELOAD" in os.environ else None),
        help="path to the receipt-bound local compatibility preload",
    )
    arguments = parser.parse_args()
    if arguments.lean is None:
        discovered = shutil.which("lean")
        require(discovered is not None, "supply --lean or QIKVRT_LEAN")
        arguments.lean = pathlib.Path(discovered)

    fixity = check_manifest_and_fixity()
    check_source_shape()
    documents = check_documents()
    lean_result = check_lean(arguments.lean, arguments.preload, documents["trust"])
    receipt = check_receipt(fixity, lean_result)
    require(
        receipt["artifact_binding"]["top_theorem_statement_sha256"] ==
        top_theorem_statement_digest(),
        "top theorem statement digest mismatch",
    )
    print(json.dumps({
        "result": "PASS",
        "scope": "QIK-VRT VRTCore Virtual Sphere H6 exact local package",
        "virtual_closure_scope": "PASS",
        "physical_closure": "OPEN",
        "lean": lean_result["version"],
        "theorems": "55/55",
        "axioms": lean_result["axiom_counts"],
        "double_compile_olean_sha256": lean_result["olean_sha256"],
        "exact_inventory_files": fixity["inventory_count"],
        "package_root_sha256": fixity["package_root_sha256"],
        "independent_external_reproduction": "OPEN",
        "effect_state": "EFFECT_ACK_CONTINUE",
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, KeyError, json.JSONDecodeError) as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error
