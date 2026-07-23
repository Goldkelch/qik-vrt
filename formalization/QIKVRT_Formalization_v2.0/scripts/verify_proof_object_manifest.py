#!/usr/bin/env python3
"""Verify persistent proof objects and emit hash-bound runtime evidence.

This verifier does not kernel-check an ``.olean`` file.  The workflow must run
``lake build`` from a fresh build directory first.  Cache entries may
accelerate toolchain/package setup, but never replace that kernel build.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "proofs" / "PROOF_OBJECT_MANIFEST.json"
EXPECTED_SCHEMA = "qikvrt_proof_object_manifest_v2"
EXPECTED_MATRIX_SCHEMA = "qikvrt_effect_ack_draft01_claim_matrix_v1"
EXPECTED_EFFECT_ACK_CLAIMS = 15
REQUIRED_LEGACY_CLAIMS = {"GAT-003", "ESC-003A"}
KERNEL_STATUSES = {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}
OPEN_STATUSES = {"OPEN", "EMPIRICAL_OPEN"}
SCOPE_ANCHOR = ".lake/build/lib/lean/QIKVRTEffectAck.olean"


class VerificationError(RuntimeError):
    """A fail-closed manifest, binding, or proof-object error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def require_object(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def require_array(value: Any, label: str) -> list[Any]:
    require(isinstance(value, list), f"{label} must be an array")
    return value


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} cannot be read: {exc}") from exc
    return require_object(value, label)


def safe_relative_path(relative: Any, label: str) -> PurePosixPath:
    require(isinstance(relative, str) and relative, f"{label} must be a path")
    value = PurePosixPath(relative)
    require(not value.is_absolute(), f"{label} must be relative")
    require(".." not in value.parts, f"{label} must not traverse parents")
    require(value.parts and value.parts != (".",), f"{label} is empty")
    return value


def regular_file(root: Path, relative: Any, label: str) -> tuple[Path, int]:
    value = safe_relative_path(relative, label)
    path = root.joinpath(*value.parts)
    try:
        metadata = path.lstat()
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except OSError as exc:
        raise VerificationError(f"{label} is missing: {value}") from exc
    require(
        resolved_path.is_relative_to(resolved_root),
        f"{label} resolves outside the formalization root: {value}",
    )
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {value}")
    require(metadata.st_size > 0, f"{label} is empty: {value}")
    return path, metadata.st_size


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_receipt(root: Path, relative: str, label: str) -> dict[str, Any]:
    path, size = regular_file(root, relative, label)
    return {"path": relative, "bytes": size, "sha256": sha256(path)}


def strip_lean_comments_and_strings(source: str) -> str:
    output: list[str] = []
    index = 0
    comment_depth = 0
    in_string = False
    escaped = False
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if comment_depth:
            if current == "/" and following == "-":
                comment_depth += 1
                output.extend("  ")
                index += 2
            elif current == "-" and following == "/":
                comment_depth -= 1
                output.extend("  ")
                index += 2
            else:
                output.append("\n" if current == "\n" else " ")
                index += 1
            continue
        if in_string:
            output.append("\n" if current == "\n" else " ")
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue
        if current == "-" and following == "-":
            while index < len(source) and source[index] != "\n":
                output.append(" ")
                index += 1
            continue
        if current == "/" and following == "-":
            comment_depth = 1
            output.extend("  ")
            index += 2
            continue
        if current == '"':
            in_string = True
            output.append(" ")
            index += 1
            continue
        output.append(current)
        index += 1
    require(comment_depth == 0, "Lean source contains an unterminated block comment")
    require(not in_string, "Lean source contains an unterminated string")
    return "".join(output)


def require_declaration(
    root: Path,
    source_relative: str,
    constant: str,
    label: str,
) -> str:
    source_path, _ = regular_file(root, source_relative, f"{label} source")
    source = strip_lean_comments_and_strings(
        source_path.read_text(encoding="utf-8")
    )
    require("." in constant, f"{label} constant must be fully qualified")
    namespace, name = constant.rsplit(".", 1)
    namespace_pattern = re.compile(
        rf"(?m)^\s*namespace\s+{re.escape(namespace)}\s*$"
    )
    namespace_end_pattern = re.compile(
        rf"(?m)^\s*end\s+{re.escape(namespace)}\s*$"
    )
    declaration_pattern = re.compile(
        rf"(?m)^\s*(?:theorem|def)\s+{re.escape(name)}\b"
    )
    namespace_match = namespace_pattern.search(source)
    namespace_end_match = namespace_end_pattern.search(source)
    declaration_match = declaration_pattern.search(source)
    require(
        namespace_match is not None and namespace_end_match is not None,
        f"{label} namespace {namespace} is absent from {source_relative}",
    )
    require(
        declaration_match is not None
        and namespace_match.end() < declaration_match.start()
        and declaration_match.end() < namespace_end_match.start(),
        f"{label} declaration {constant} is absent from {source_relative}",
    )
    return sha256(source_path)


def module_object_for_source(source_relative: str) -> str:
    source = safe_relative_path(source_relative, "Lean source path")
    require(source.suffix == ".lean", f"Lean source must end in .lean: {source}")
    return str(
        PurePosixPath(".lake/build/lib/lean").joinpath(
            source.with_suffix(".olean")
        )
    )


def index_by_claim_id(items: list[Any], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(items):
        item = require_object(raw_item, f"{label}[{index}]")
        claim_id = item.get("claimId")
        require(
            isinstance(claim_id, str) and claim_id,
            f"{label}[{index}].claimId is missing",
        )
        require(claim_id not in indexed, f"{label} duplicates {claim_id}")
        indexed[claim_id] = item
    return indexed


def matrix_claim_index(items: list[Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(items):
        item = require_object(raw_item, f"matrix claims[{index}]")
        claim_id = item.get("id")
        require(
            isinstance(claim_id, str) and claim_id,
            f"matrix claims[{index}].id is missing",
        )
        require(claim_id not in indexed, f"claim matrix duplicates {claim_id}")
        indexed[claim_id] = item
    return indexed


def require_effect_ack_coverage(
    matrix_claims: dict[str, dict[str, Any]],
    manifest_claims: dict[str, dict[str, Any]],
) -> None:
    require(
        len(matrix_claims) == EXPECTED_EFFECT_ACK_CLAIMS,
        f"claim matrix must contain {EXPECTED_EFFECT_ACK_CLAIMS} claims",
    )
    missing = sorted(set(matrix_claims) - set(manifest_claims))
    extra = sorted(set(manifest_claims) - set(matrix_claims))
    require(
        not missing and not extra,
        f"EFFECT_ACK manifest coverage differs; missing={missing}, extra={extra}",
    )


def compiled_receipt(root: Path, relative: str) -> dict[str, Any]:
    return file_receipt(root, relative, "compiledObject")


def verify(
    root: Path = ROOT,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_path or root / "proofs" / "PROOF_OBJECT_MANIFEST.json"
    manifest = load_object(manifest_path, "proof-object manifest")
    require(manifest.get("schema") == EXPECTED_SCHEMA, "unknown manifest schema")

    policy = require_object(manifest.get("policy"), "manifest policy")
    require(
        policy.get("cacheMayReplaceKernelVerification") is False,
        "cache must never replace kernel verification",
    )
    require(
        policy.get("cacheMissRequiresRebuild") is True,
        "cache miss must require rebuild",
    )
    require(
        policy.get("sourceOrToolchainChangeInvalidates") is True,
        "source/toolchain changes must invalidate cached objects",
    )

    object_evidence: dict[str, dict[str, Any]] = {}

    def bind_object(relative: str, claim_id: str, role: str) -> None:
        receipt = object_evidence.get(relative)
        if receipt is None:
            receipt = compiled_receipt(root, relative)
            receipt["claimIds"] = set()
            receipt["roles"] = set()
            object_evidence[relative] = receipt
        receipt["claimIds"].add(claim_id)
        receipt["roles"].add(role)

    legacy = index_by_claim_id(
        require_array(manifest.get("objects"), "manifest objects"),
        "manifest objects",
    )
    require(
        REQUIRED_LEGACY_CLAIMS <= set(legacy),
        "legacy GAT-003/ESC-003A entries must be preserved",
    )
    legacy_evidence: list[dict[str, Any]] = []
    for claim_id, item in legacy.items():
        for key in (
            "statementConstant",
            "proofConstant",
            "registryConstant",
            "sourcePath",
            "registrySourcePath",
            "compiledObject",
            "status",
        ):
            require(
                isinstance(item.get(key), str) and item[key],
                f"{claim_id}: {key} is missing",
            )
        require(
            item["status"] == "KERNEL_CHECK_REQUIRED_ON_EVERY_DISTINCT_INPUT_SET",
            f"{claim_id}: cache/kernel policy differs",
        )
        require(
            item["compiledObject"] == module_object_for_source(item["sourcePath"]),
            f"{claim_id}: compiledObject does not match sourcePath",
        )
        source_sha256 = require_declaration(
            root, item["sourcePath"], item["statementConstant"], claim_id
        )
        require_declaration(
            root, item["sourcePath"], item["proofConstant"], claim_id
        )
        registry_sha256 = require_declaration(
            root,
            item["registrySourcePath"],
            item["registryConstant"],
            claim_id,
        )
        bind_object(item["compiledObject"], claim_id, "legacy-proof-object")
        legacy_evidence.append(
            {
                "claimId": claim_id,
                "statementConstant": item["statementConstant"],
                "proofConstant": item["proofConstant"],
                "registryConstant": item["registryConstant"],
                "sourcePath": item["sourcePath"],
                "sourceSha256": source_sha256,
                "registrySourcePath": item["registrySourcePath"],
                "registrySourceSha256": registry_sha256,
                "compiledObject": item["compiledObject"],
            }
        )

    effect_ack = require_object(manifest.get("effectAck"), "effectAck")
    matrix_relative = effect_ack.get("claimMatrix")
    matrix_path, _ = regular_file(root, matrix_relative, "claim matrix")
    matrix = load_object(matrix_path, "claim matrix")
    require(
        matrix.get("schema") == EXPECTED_MATRIX_SCHEMA,
        "unknown EFFECT_ACK claim-matrix schema",
    )
    matrix_claims = matrix_claim_index(
        require_array(matrix.get("claims"), "claim matrix claims")
    )
    manifest_claims = index_by_claim_id(
        require_array(effect_ack.get("claims"), "effectAck claims"),
        "effectAck claims",
    )
    require_effect_ack_coverage(matrix_claims, manifest_claims)

    registry_source = effect_ack.get("registrySourcePath")
    regular_file(root, registry_source, "EFFECT_ACK registry source")
    claim_evidence: list[dict[str, Any]] = []

    for claim_id in sorted(matrix_claims):
        matrix_claim = matrix_claims[claim_id]
        item = manifest_claims[claim_id]
        matrix_proofs = matrix_claim.get("proof_constants")
        require(
            isinstance(matrix_proofs, list)
            and all(isinstance(value, str) and value for value in matrix_proofs),
            f"{claim_id}: matrix proof_constants are invalid",
        )
        matrix_registry = matrix_claim.get("registry_constant")
        require(
            matrix_registry is None
            or isinstance(matrix_registry, str) and matrix_registry,
            f"{claim_id}: matrix registry_constant is invalid",
        )
        matrix_source = matrix_claim.get("source_path")
        require(
            matrix_source is None or isinstance(matrix_source, str) and matrix_source,
            f"{claim_id}: matrix source_path is invalid",
        )
        require(
            item.get("proofConstants") == matrix_proofs,
            f"{claim_id}: proofConstants differ from the claim matrix",
        )
        require(
            item.get("registryConstant") == matrix_registry,
            f"{claim_id}: registryConstant differs from the claim matrix",
        )
        require(
            item.get("sourcePath") == matrix_source,
            f"{claim_id}: sourcePath differs from the claim matrix",
        )

        status = matrix_claim.get("status")
        source_sha256: str | None = None
        registry_sha256: str | None = None
        if status in KERNEL_STATUSES:
            expected_kind = "KERNEL_PROOF"
            require(matrix_proofs and matrix_source, f"{claim_id}: kernel binding missing")
            expected_objects = [module_object_for_source(matrix_source)]
            for constant in matrix_proofs:
                source_sha256 = require_declaration(
                    root, matrix_source, constant, claim_id
                )
            if matrix_registry is not None:
                registry_sha256 = require_declaration(
                    root, registry_source, matrix_registry, claim_id
                )
                registry_object = module_object_for_source(registry_source)
                if registry_object not in expected_objects:
                    expected_objects.append(registry_object)
        else:
            require(status in OPEN_STATUSES, f"{claim_id}: unsupported claim status")
            expected_kind = "SCOPE_BOUNDARY"
            require(
                not matrix_proofs
                and matrix_registry is None
                and matrix_source is None,
                f"{claim_id}: open scope claim must not carry a kernel proof",
            )
            expected_objects = [SCOPE_ANCHOR]

        require(
            item.get("bindingKind") == expected_kind,
            f"{claim_id}: bindingKind differs from matrix status",
        )
        require(
            item.get("compiledObjects") == expected_objects,
            f"{claim_id}: compiledObjects differ; expected {expected_objects}",
        )
        for relative in expected_objects:
            role = (
                "effect-scope-anchor"
                if expected_kind == "SCOPE_BOUNDARY"
                else (
                    "effect-registry-object"
                    if relative == module_object_for_source(registry_source)
                    else "effect-proof-object"
                )
            )
            bind_object(relative, claim_id, role)
        claim_evidence.append(
            {
                "claimId": claim_id,
                "status": status,
                "bindingKind": expected_kind,
                "proofConstants": matrix_proofs,
                "registryConstant": matrix_registry,
                "sourcePath": matrix_source,
                "sourceSha256": source_sha256,
                "registrySourcePath": (
                    registry_source if matrix_registry is not None else None
                ),
                "registrySourceSha256": registry_sha256,
                "compiledObjects": expected_objects,
            }
        )

    compiled_evidence = []
    for relative in sorted(object_evidence):
        receipt = object_evidence[relative]
        receipt["claimIds"] = sorted(receipt["claimIds"])
        receipt["roles"] = sorted(receipt["roles"])
        compiled_evidence.append(receipt)

    return {
        "schema": "qikvrt_proof_object_manifest_verification_v2",
        "status": "PASS",
        "cache_replaces_kernel": False,
        "kernel_build_required_before_this_check": True,
        "verification_scope": (
            "regular-file, SHA-256, claim-matrix, source-declaration and "
            "compiled-module binding; not an independent kernel check"
        ),
        "manifestSha256": sha256(manifest_path),
        "claimMatrixSha256": sha256(matrix_path),
        "legacyClaims": sorted(
            legacy_evidence, key=lambda item: item["claimId"]
        ),
        "effectAckClaims": claim_evidence,
        "effectAckClaimCount": len(claim_evidence),
        "compiledObjects": compiled_evidence,
    }


def main() -> int:
    try:
        evidence = verify()
    except (OSError, UnicodeError, json.JSONDecodeError, VerificationError) as exc:
        print(f"BLOCK PROOF_OBJECT_MANIFEST_INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
