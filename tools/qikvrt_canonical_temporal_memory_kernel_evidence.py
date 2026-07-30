#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Emit exact-head Lean evidence for the canonical temporal-memory paper.

The historical Alpha-2 proof manifest is immutable and deliberately excludes
future publication scopes.  This tool therefore treats the paper's own claim
matrix and kernel plan as the scoped authorities, while reusing the locked
Lean project.  It validates source identity and claim coverage, invokes Lean
on the exact source, audits theorem dependencies with ``#print axioms``, binds
the direct ``.olean`` object, and records the GitHub runtime context.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
from typing import Any, NoReturn


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
DEFAULT_PLAN = (
    ROOT
    / "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack"
    / "KERNEL_PROOF_PLAN.json"
)
DEFAULT_CLAIMS = (
    ROOT
    / "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack"
    / "CLAIM_MATRIX.json"
)
PLAN_SCHEMA = "qikvrt_publication_kernel_proof_plan_v1"
CLAIM_SCHEMAS = {
    "qikvrt_canonical_temporal_memory_claim_matrix_v2",
}
EVIDENCE_SCHEMA = "qikvrt_canonical_temporal_memory_kernel_evidence_v1"
PUBLICATION_ID = "qikvrt-canonical-temporal-memory-effect-ack-v1"
FORMAL_CLASSES = {"FORMAL_PENDING_KERNEL", "FORMAL_PROVED"}
FORMAL_IDS = {"CTM-001", "CTM-002", "CTM-003", "CTM-004"}
CLAIM_CLASSES = FORMAL_CLASSES | {
    "EMPIRICALLY_EVIDENCED",
    "INTERPRETATIVE",
    "NORMATIVE",
    "OPEN",
    "SOURCE_BOUND",
}
CLAIM_KEYS = {
    "boundary",
    "claim_id",
    "classification",
    "proof_refs",
    "sources",
    "statement",
    "status",
}
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ARTIFACT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
AXIOM_LINE = re.compile(
    r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
    r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
)


class EvidenceError(RuntimeError):
    """Fail-closed publication evidence error."""


def fail(message: str) -> NoReturn:
    raise EvidenceError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    require(
        not missing and not unknown,
        f"{label} keys differ; missing={sorted(missing)}, unknown={sorted(unknown)}",
    )


def safe_regular(root: pathlib.Path, raw: Any, label: str) -> pathlib.Path:
    require(isinstance(raw, str) and raw, f"{label} must be a non-empty path")
    relative = pathlib.PurePosixPath(raw)
    require(
        not relative.is_absolute()
        and relative.parts
        and all(part not in {"", ".", ".."} for part in relative.parts),
        f"{label} must be a safe relative path",
    )
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"{label} contains a symbolic link")
    try:
        metadata = cursor.lstat()
        resolved = cursor.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        fail(f"{label} cannot be resolved: {exc}")
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file")
    require(metadata.st_size > 0, f"{label} is empty")
    return resolved


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"{label} cannot be read: {exc}")
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def git_blob(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def identity(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": git_blob(data),
    }


def run(command: list[str], cwd: pathlib.Path) -> tuple[dict[str, Any], str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    require(
        result.returncode == 0,
        f"command failed ({' '.join(command)}):\n{output}",
    )
    return (
        {
            "argv": command,
            "exit_code": result.returncode,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        },
        output,
    )


def strip_lean_comments_and_strings(source: str) -> str:
    output: list[str] = []
    index = 0
    depth = 0
    in_string = False
    escaped = False
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if depth:
            if current == "/" and following == "-":
                depth += 1
                output.extend("  ")
                index += 2
            elif current == "-" and following == "/":
                depth -= 1
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
            depth = 1
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
    require(depth == 0, "Lean source has an unterminated block comment")
    require(not in_string, "Lean source has an unterminated string")
    return "".join(output)


def static_validation(
    plan_path: pathlib.Path = DEFAULT_PLAN,
    claims_path: pathlib.Path = DEFAULT_CLAIMS,
) -> dict[str, Any]:
    plan = load_json(plan_path, "kernel plan")
    claims = load_json(claims_path, "claim matrix")
    exact_keys(
        plan,
        {
            "_license",
            "schema",
            "publication_id",
            "source",
            "entrypoint",
            "lean_toolchain",
            "axiom_audit",
            "theorems",
            "artifact_name",
            "completion_claims",
        },
        "kernel plan",
    )
    require(plan["schema"] == PLAN_SCHEMA, "kernel plan schema differs")
    require(
        plan["publication_id"] == PUBLICATION_ID,
        "kernel plan publication_id differs",
    )
    require(
        claims.get("schema") in CLAIM_SCHEMAS,
        "claim matrix schema differs",
    )
    exact_keys(
        claims,
        {
            "_license",
            "author",
            "claim_count",
            "claims",
            "completion_claims",
            "proof_state",
            "publication_id",
            "schema",
        },
        "claim matrix",
    )
    require(
        claims.get("publication_id") == PUBLICATION_ID,
        "claim matrix publication_id differs",
    )
    raw_claims = claims.get("claims")
    require(isinstance(raw_claims, list) and raw_claims, "claims must be an array")
    require(
        claims.get("claim_count") == len(raw_claims),
        "claim_count differs from the claim array",
    )
    claim_ids = [item.get("claim_id") for item in raw_claims if isinstance(item, dict)]
    require(
        len(claim_ids) == len(raw_claims)
        and claim_ids == [f"CTM-{index:03d}" for index in range(1, len(raw_claims) + 1)],
        "claim IDs must be complete, ordered and contiguous",
    )
    for item in raw_claims:
        exact_keys(item, CLAIM_KEYS, f"claim {item['claim_id']}")
        require(
            item["classification"] in CLAIM_CLASSES,
            f"{item['claim_id']} classification differs",
        )
        require(
            isinstance(item["boundary"], str) and item["boundary"].strip(),
            f"{item['claim_id']} lacks a boundary",
        )
        require(
            isinstance(item["statement"], str) and item["statement"].strip(),
            f"{item['claim_id']} lacks a statement",
        )
        require(
            isinstance(item["sources"], list)
            and item["sources"]
            and all(isinstance(source_id, str) and source_id for source_id in item["sources"]),
            f"{item['claim_id']} lacks sources",
        )
        require(
            isinstance(item["proof_refs"], list),
            f"{item['claim_id']} proof_refs must be a list",
        )
    formal = [
        item
        for item in raw_claims
        if isinstance(item, dict) and item.get("classification") in FORMAL_CLASSES
    ]
    require(
        {item["claim_id"] for item in formal} == FORMAL_IDS,
        "formal claim set differs",
    )
    formal_modes = {item["classification"] for item in formal}
    require(
        len(formal_modes) == 1,
        "formal claims mix pending and kernel-verified modes",
    )
    formal_mode = next(iter(formal_modes))
    expected_proof_state = (
        "AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
        if formal_mode == "FORMAL_PENDING_KERNEL"
        else "KERNEL_VERIFIED"
    )
    require(
        claims["proof_state"] == expected_proof_state,
        "claim-matrix proof_state differs from the aggregate formal mode",
    )
    for item in formal:
        status = item.get("status")
        if item["classification"] == "FORMAL_PENDING_KERNEL":
            require(
                status == "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT",
                f"{item['claim_id']} pending status differs",
            )
        else:
            require(
                status == "KERNEL_VERIFIED",
                f"{item['claim_id']} proved status lacks kernel verification",
            )
        require(
            isinstance(item.get("proof_refs"), list) and item["proof_refs"],
            f"{item['claim_id']} lacks proof refs",
        )
    require(
        claims["completion_claims"]
        == {
            "effect_ack_done": False,
            "final_pass": False,
            "pass": False,
            "system_wide_completion": "UNCLAIMED",
        },
        "claim-matrix completion boundary differs",
    )

    theorems = plan["theorems"]
    require(
        isinstance(theorems, list)
        and theorems
        and all(isinstance(item, str) and item for item in theorems)
        and len(theorems) == len(set(theorems)),
        "plan theorems must be a unique non-empty list",
    )
    formal_refs = {
        theorem
        for item in formal
        for theorem in item["proof_refs"]
        if isinstance(theorem, str)
    }
    require(formal_refs == set(theorems), "claim/proof theorem union differs")

    source = plan["source"]
    require(isinstance(source, dict), "plan source must be an object")
    exact_keys(
        source,
        {"path", "bytes", "sha256", "git_blob_sha1", "compiled_object"},
        "plan source",
    )
    source_path = safe_regular(PROJECT, source["path"], "plan source.path")
    observed_source = identity(source_path, PROJECT)
    require(
        isinstance(source["bytes"], int)
        and not isinstance(source["bytes"], bool)
        and source["bytes"] == observed_source["bytes"],
        "plan source byte count differs",
    )
    require(
        isinstance(source["sha256"], str)
        and HEX64.fullmatch(source["sha256"]) is not None
        and source["sha256"] == observed_source["sha256"],
        "plan source SHA-256 differs",
    )
    require(
        isinstance(source["git_blob_sha1"], str)
        and HEX40.fullmatch(source["git_blob_sha1"]) is not None
        and source["git_blob_sha1"] == observed_source["git_blob_sha1"],
        "plan source Git blob differs",
    )
    expected_object = (
        ".lake/build/lib/lean/"
        + pathlib.PurePosixPath(source["path"]).with_suffix(".olean").as_posix()
    )
    require(
        source["compiled_object"] == expected_object,
        "compiled object does not correspond to source",
    )

    source_text = strip_lean_comments_and_strings(
        source_path.read_text(encoding="utf-8")
    )
    for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"\bunsafe\b"):
        require(
            re.search(prohibited, source_text) is None,
            f"source contains proof escape matching {prohibited}",
        )
    for theorem in theorems:
        short_name = theorem.rsplit(".", 1)[-1]
        require(
            re.search(rf"(?m)^\s*theorem\s+{re.escape(short_name)}\b", source_text)
            is not None,
            f"source declaration is absent: {theorem}",
        )

    entrypoint_path = safe_regular(PROJECT, plan["entrypoint"], "entrypoint")
    require(
        "import QIKVRTEffectAck.CanonicalTemporalMemory"
        in entrypoint_path.read_text(encoding="utf-8"),
        "entrypoint does not import the publication source",
    )
    toolchain = plan["lean_toolchain"]
    require(isinstance(toolchain, dict), "lean_toolchain must be an object")
    exact_keys(toolchain, {"path", "value"}, "lean_toolchain")
    toolchain_path = safe_regular(PROJECT, toolchain["path"], "lean toolchain")
    require(
        toolchain_path.read_text(encoding="utf-8").strip() == toolchain["value"],
        "locked Lean toolchain value differs",
    )

    audit = plan["axiom_audit"]
    require(isinstance(audit, dict), "axiom_audit must be an object")
    exact_keys(audit, {"expected_axioms_by_theorem"}, "axiom_audit")
    policy = audit["expected_axioms_by_theorem"]
    require(isinstance(policy, dict), "axiom policy must be an object")
    require(set(policy) == set(theorems), "axiom policy theorem set differs")
    for theorem, raw_axioms in policy.items():
        require(
            isinstance(raw_axioms, list)
            and all(isinstance(item, str) and item for item in raw_axioms),
            f"axiom policy for {theorem} must be a string list",
        )
        require(
            set(raw_axioms) <= ALLOWED_AXIOMS,
            f"axiom policy for {theorem} contains a forbidden dependency",
        )

    artifact_name = plan["artifact_name"]
    require(
        isinstance(artifact_name, str)
        and SAFE_ARTIFACT.fullmatch(artifact_name) is not None,
        "artifact_name is unsafe",
    )
    require(
        plan["completion_claims"]
        == {
            "ietf_revision_02_posted": False,
            "system_wide_completion": "UNCLAIMED",
            "zenodo_published": False,
        },
        "kernel plan completion boundary differs",
    )
    return {
        "plan": plan,
        "claims": claims,
        "formal_claims": formal,
        "source_path": source_path,
        "source": observed_source,
        "entrypoint_path": entrypoint_path,
        "toolchain_path": toolchain_path,
    }


def runtime_evidence(
    plan_path: pathlib.Path = DEFAULT_PLAN,
    claims_path: pathlib.Path = DEFAULT_CLAIMS,
) -> dict[str, Any]:
    static = static_validation(plan_path, claims_path)
    plan = static["plan"]
    source = plan["source"]

    source_run, _source_output = run(
        ["lake", "env", "lean", source["path"]],
        PROJECT,
    )
    compiled_path = safe_regular(
        PROJECT, source["compiled_object"], "compiled publication object"
    )

    audit_path = PROJECT / ".lake/build/CanonicalTemporalMemoryAxiomAudit.lean"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_text = "import QIKVRTEffectAck.CanonicalTemporalMemory\n\n" + "\n".join(
        f"#print axioms {theorem}" for theorem in plan["theorems"]
    ) + "\n"
    audit_path.write_text(audit_text, encoding="utf-8")
    audit_run, audit_output = run(
        ["lake", "env", "lean", str(audit_path.relative_to(PROJECT))],
        PROJECT,
    )
    observed_axioms: dict[str, list[str]] = {}
    for line in audit_output.splitlines():
        match = AXIOM_LINE.match(line.strip())
        if match is None:
            continue
        theorem = match.group("name")
        if theorem not in plan["theorems"]:
            continue
        observed_axioms[theorem] = sorted(
            {
                item.strip()
                for item in (match.group("axioms") or "").split(",")
                if item.strip()
            }
        )
    require(
        set(observed_axioms) == set(plan["theorems"]),
        "runtime axiom reports are incomplete",
    )
    expected_policy = {
        theorem: sorted(axioms)
        for theorem, axioms in plan["axiom_audit"][
            "expected_axioms_by_theorem"
        ].items()
    }
    require(
        observed_axioms == expected_policy,
        f"runtime axiom dependencies differ: observed={observed_axioms}",
    )

    formal_bindings = [
        {
            "claim_id": item["claim_id"],
            "proof_refs": item["proof_refs"],
            "source_sha256": static["source"]["sha256"],
            "compiled_object_sha256": identity(compiled_path, PROJECT)["sha256"],
            "axioms_by_theorem": {
                theorem: observed_axioms[theorem]
                for theorem in item["proof_refs"]
            },
        }
        for item in static["formal_claims"]
    ]
    return {
        "schema": EVIDENCE_SCHEMA,
        "state": "KERNEL_VERIFIED",
        "publication_id": PUBLICATION_ID,
        "plan": identity(plan_path, ROOT),
        "claim_matrix": identity(claims_path, ROOT),
        "source": static["source"],
        "compiled_object": identity(compiled_path, PROJECT),
        "entrypoint": identity(static["entrypoint_path"], PROJECT),
        "lean_toolchain": {
            **identity(static["toolchain_path"], PROJECT),
            "value": plan["lean_toolchain"]["value"],
        },
        "formal_claim_count": len(static["formal_claims"]),
        "theorem_count": len(plan["theorems"]),
        "formal_bindings": formal_bindings,
        "axioms_by_theorem": observed_axioms,
        "runtime": {
            "exact_source_kernel_check": source_run,
            "dynamic_axiom_audit": audit_run,
            "fresh_project_build_required_before_object_binding": True,
            "cache_replaces_kernel_verification": False,
        },
        "workflow": {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "sha": os.environ.get("GITHUB_SHA", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "event": os.environ.get("GITHUB_EVENT_NAME", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        },
        "completion_claims": plan["completion_claims"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        default=DEFAULT_PLAN.relative_to(ROOT).as_posix(),
        help="repository-relative kernel plan",
    )
    parser.add_argument(
        "--claims",
        default=DEFAULT_CLAIMS.relative_to(ROOT).as_posix(),
        help="repository-relative claim matrix",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="validate tracked inputs without invoking Lean",
    )
    args = parser.parse_args(argv)
    try:
        plan_path = safe_regular(ROOT, args.plan, "--plan")
        claims_path = safe_regular(ROOT, args.claims, "--claims")
        if args.static_only:
            value = static_validation(plan_path, claims_path)
            output = {
                "schema": EVIDENCE_SCHEMA,
                "state": "STATIC_INPUTS_VERIFIED",
                "publication_id": PUBLICATION_ID,
                "plan": identity(plan_path, ROOT),
                "claim_matrix": identity(claims_path, ROOT),
                "source": value["source"],
                "formal_claim_count": len(value["formal_claims"]),
                "theorem_count": len(value["plan"]["theorems"]),
            }
        else:
            output = runtime_evidence(plan_path, claims_path)
    except EvidenceError as exc:
        print(f"BLOCK CTM_KERNEL_EVIDENCE_INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
