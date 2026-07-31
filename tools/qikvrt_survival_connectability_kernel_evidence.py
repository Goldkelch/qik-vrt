#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Emit exact-head Lean evidence for the connectability publication.

The publication has two deliberately separate formal modules: bounded
operational continuation and viability-preserving connectability simulation.
This tool binds every plan-declared source, its direct ``.olean`` object, the
claim matrix, the locked Lean toolchain, and dynamically observed
``#print axioms`` reports to one Git commit.  The source/import inventory is
plan-driven so that adding a reviewed module requires an explicit plan and
claim-matrix update rather than an implicit tool-code exception.

Static validation accepts either the fail-closed pre-kernel claim state or a
uniform kernel-verified state.  Running the tool without ``--static-only``
does not edit or promote the claim matrix; it merely emits evidence that may
be reviewed and persisted by the publication workflow.
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
PUBLICATION = (
    ROOT / "docs/publications/2026-07-31-survival-anschlussfaehigsten"
)
WORKFLOW = ROOT / ".github/workflows/qikvrt_manuscript_proof.yml"
PROJECT_LOCK_FILES = (PROJECT / "lakefile.toml", PROJECT / "lake-manifest.json")
DEFAULT_PLAN = PUBLICATION / "KERNEL_PROOF_PLAN.json"
DEFAULT_CLAIMS = PUBLICATION / "CLAIM_MATRIX.json"
PLAN_SCHEMA = "qikvrt_survival_connectability_kernel_proof_plan_v1"
CLAIM_SCHEMA = "qikvrt_survival_connectability_claim_matrix_v1"
EVIDENCE_SCHEMA = "qikvrt_survival_connectability_kernel_evidence_v1"
PUBLICATION_ID = "qikvrt-survival-of-the-anschlussfaehigsten-v1"
ARTIFACT_NAME = "qikvrt-survival-connectability-kernel-evidence"
FORMAL_CLASSES = {"FORMAL_PENDING_KERNEL", "FORMAL_PROVED"}
CLAIM_CLASSES = FORMAL_CLASSES | {
    "EMPIRICALLY_EVIDENCED",
    "INTERPRETATIVE",
    "MATHEMATICAL_DERIVATION",
    "NORMATIVE",
    "OPEN",
    "SOURCE_BOUND",
}
NONFORMAL_STATUSES = {
    "EMPIRICALLY_EVIDENCED": {"EVIDENCED", "EMPIRICALLY_EVIDENCED"},
    "INTERPRETATIVE": {"AUTHORIAL_INTERPRETATION"},
    "MATHEMATICAL_DERIVATION": {"PAPER_DERIVATION_NOT_KERNEL_PROMOTED"},
    "NORMATIVE": {"DOES_NOT_FOLLOW"},
    "OPEN": {"NOT_CLAIMED_OUT_OF_SCOPE", "OPEN_EMPIRICAL"},
    "SOURCE_BOUND": {"BOUND"},
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
PLAN_COMPLETION_BOUNDARY = {
    "repository_promotion_complete": False,
    "system_wide_completion": "UNCLAIMED",
    "zenodo_published": False,
}
CLAIM_COMPLETION_BOUNDARY = {
    "effect_ack_done": False,
    "final_pass": False,
    "pass": False,
    "system_wide_completion": "UNCLAIMED",
}
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ARTIFACT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
LEAN_IMPORT = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")
LEAN_CONSTANT = re.compile(r"^[A-Za-z][A-Za-z0-9_'.]*(?:\.[A-Za-z][A-Za-z0-9_']*)+$")
AXIOM_REPORT = re.compile(
    r"'(?P<name>[^']+)' (?:does not depend on any axioms|"
    r"depends on axioms:\s*\[(?P<axioms>[^]]*)\])"
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
        f"{label} keys differ; missing={sorted(missing)}, "
        f"unknown={sorted(unknown)}",
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
        value = json.loads(path.read_text(encoding="utf-8"))
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


def parse_axiom_reports(
    output: str,
    expected_theorems: list[str],
) -> dict[str, list[str]]:
    """Parse Lean reports without assuming one physical output line per theorem."""
    normalized = re.sub(r"\s+", " ", output)
    expected = set(expected_theorems)
    short_names = {
        theorem.rsplit(".", 1)[-1]: theorem for theorem in expected_theorems
    }
    require(
        len(short_names) == len(expected),
        "expected theorem short names are not unique",
    )
    observed: dict[str, list[str]] = {}
    for match in AXIOM_REPORT.finditer(normalized):
        reported = match.group("name")
        theorem = reported if reported in expected else short_names.get(reported)
        if theorem is None:
            continue
        require(theorem not in observed, f"duplicate axiom report for {theorem}")
        observed[theorem] = sorted(
            {
                item.strip()
                for item in (match.group("axioms") or "").split(",")
                if item.strip()
            }
        )
    return observed


def _validate_claims(claims: dict[str, Any]) -> list[dict[str, Any]]:
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
    require(claims["schema"] == CLAIM_SCHEMA, "claim matrix schema differs")
    require(
        claims["publication_id"] == PUBLICATION_ID,
        "claim matrix publication_id differs",
    )
    raw_claims = claims["claims"]
    require(isinstance(raw_claims, list) and raw_claims, "claims must be an array")
    require(claims["claim_count"] == len(raw_claims), "claim_count differs")
    claim_ids: list[str] = []
    for item in raw_claims:
        require(isinstance(item, dict), "every claim must be an object")
        exact_keys(item, CLAIM_KEYS, f"claim {item.get('claim_id', '<missing>')}")
        claim_id = item["claim_id"]
        require(
            isinstance(claim_id, str) and re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9]{3}", claim_id),
            "claim IDs must use an uppercase prefix and three-digit suffix",
        )
        claim_ids.append(claim_id)
        require(item["classification"] in CLAIM_CLASSES, f"{claim_id} class differs")
        for key in ("boundary", "statement"):
            require(
                isinstance(item[key], str) and item[key].strip(),
                f"{claim_id} lacks {key}",
            )
        require(
            isinstance(item["sources"], list)
            and item["sources"]
            and all(isinstance(value, str) and value for value in item["sources"]),
            f"{claim_id} lacks sources",
        )
        require(
            len(item["sources"]) == len(set(item["sources"])),
            f"{claim_id} repeats a source",
        )
        require(
            isinstance(item["proof_refs"], list)
            and all(isinstance(value, str) and value for value in item["proof_refs"]),
            f"{claim_id} proof_refs differ",
        )
        require(
            len(item["proof_refs"]) == len(set(item["proof_refs"])),
            f"{claim_id} repeats a proof ref",
        )
    require(len(claim_ids) == len(set(claim_ids)), "claim IDs are not unique")

    formal = [item for item in raw_claims if item["classification"] in FORMAL_CLASSES]
    require(formal, "claim matrix has no formal claims")
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
    expected_status = (
        "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
        if formal_mode == "FORMAL_PENDING_KERNEL"
        else "KERNEL_VERIFIED"
    )
    require(
        claims["proof_state"] == expected_proof_state,
        "claim proof_state differs from aggregate formal mode",
    )
    for item in formal:
        require(item["status"] == expected_status, f"{item['claim_id']} status differs")
        require(item["proof_refs"], f"{item['claim_id']} lacks proof refs")
    for item in raw_claims:
        if item not in formal:
            require(
                item["proof_refs"] == [],
                f"nonformal claim {item['claim_id']} has proof refs",
            )
            require(
                item["status"] in NONFORMAL_STATUSES[item["classification"]],
                f"nonformal claim {item['claim_id']} status differs",
            )
    require(
        claims["completion_claims"] == CLAIM_COMPLETION_BOUNDARY,
        "claim-matrix completion boundary differs",
    )
    return formal


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
            "artifact_name",
            "axiom_audit",
            "completion_claims",
            "entrypoint",
            "lean_toolchain",
            "publication_id",
            "schema",
            "sources",
            "theorems",
        },
        "kernel plan",
    )
    require(plan["schema"] == PLAN_SCHEMA, "kernel plan schema differs")
    require(plan["publication_id"] == PUBLICATION_ID, "plan publication_id differs")
    formal = _validate_claims(claims)

    raw_sources = plan["sources"]
    require(
        isinstance(raw_sources, list) and raw_sources,
        "plan sources must be a non-empty array",
    )
    source_values: list[dict[str, Any]] = []
    observed_paths: set[str] = set()
    observed_imports: set[str] = set()
    stripped_sources: list[str] = []
    for index, source in enumerate(raw_sources):
        require(isinstance(source, dict), f"source {index} must be an object")
        exact_keys(
            source,
            {"bytes", "compiled_object", "git_blob_sha1", "import", "path", "sha256"},
            f"source {index}",
        )
        require(source["path"] not in observed_paths, "source paths are not unique")
        require(source["import"] not in observed_imports, "source imports are not unique")
        require(
            isinstance(source["import"], str)
            and LEAN_IMPORT.fullmatch(source["import"]) is not None,
            f"source {index} import is invalid",
        )
        expected_import = (
            pathlib.PurePosixPath(source["path"])
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        require(
            source["import"] == expected_import,
            f"source {index} import does not correspond to its path",
        )
        source_path = safe_regular(PROJECT, source["path"], f"source {index}.path")
        observed = identity(source_path, PROJECT)
        require(source["bytes"] == observed["bytes"], f"source {index} bytes differ")
        require(
            isinstance(source["sha256"], str)
            and HEX64.fullmatch(source["sha256"]) is not None
            and source["sha256"] == observed["sha256"],
            f"source {index} SHA-256 differs",
        )
        require(
            isinstance(source["git_blob_sha1"], str)
            and HEX40.fullmatch(source["git_blob_sha1"]) is not None
            and source["git_blob_sha1"] == observed["git_blob_sha1"],
            f"source {index} Git blob differs",
        )
        expected_object = (
            ".lake/build/lib/lean/"
            + pathlib.PurePosixPath(source["path"]).with_suffix(".olean").as_posix()
        )
        require(
            source["compiled_object"] == expected_object,
            f"source {index} compiled object does not correspond to source",
        )
        source_text = strip_lean_comments_and_strings(
            source_path.read_text(encoding="utf-8")
        )
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"\bunsafe\b"):
            require(
                re.search(prohibited, source_text) is None,
                f"source {index} contains proof escape matching {prohibited}",
            )
        source_values.append({"path": source_path, "identity": observed, "plan": source})
        stripped_sources.append(source_text)
        observed_paths.add(source["path"])
        observed_imports.add(source["import"])

    theorems = plan["theorems"]
    require(
        isinstance(theorems, list)
        and theorems
        and all(
            isinstance(theorem, str) and LEAN_CONSTANT.fullmatch(theorem) is not None
            for theorem in theorems
        )
        and len(theorems) == len(set(theorems)),
        "plan theorems must be unique qualified Lean names",
    )
    short_names = [theorem.rsplit(".", 1)[-1] for theorem in theorems]
    require(len(short_names) == len(set(short_names)), "theorem short names are not unique")
    for theorem, short_name in zip(theorems, short_names, strict=True):
        owners = [
            index
            for index, source in enumerate(stripped_sources)
            if re.search(
                rf"(?m)^\s*theorem\s+{re.escape(short_name)}\b", source
            )
        ]
        require(len(owners) == 1, f"theorem declaration count differs: {theorem}")

    formal_refs = {
        theorem for item in formal for theorem in item["proof_refs"]
    }
    require(formal_refs == set(theorems), "claim/proof theorem union differs")
    for item in formal:
        for theorem in item["proof_refs"]:
            short_name = theorem.rsplit(".", 1)[-1]
            owner = next(
                source
                for source, stripped in zip(source_values, stripped_sources, strict=True)
                if re.search(
                    rf"(?m)^\s*theorem\s+{re.escape(short_name)}\b", stripped
                )
            )
            repository_source = (
                pathlib.PurePosixPath("formalization/QIKVRT_Formalization_v2.0")
                / owner["plan"]["path"]
            ).as_posix()
            require(
                repository_source in item["sources"],
                f"{item['claim_id']} does not cite the source owning {theorem}",
            )

    entrypoint_path = safe_regular(PROJECT, plan["entrypoint"], "entrypoint")
    entrypoint_text = strip_lean_comments_and_strings(
        entrypoint_path.read_text(encoding="utf-8")
    )
    for module_import in observed_imports:
        require(
            re.search(
                rf"(?m)^\s*import\s+{re.escape(module_import)}\s*$",
                entrypoint_text,
            )
            is not None,
            f"entrypoint does not import {module_import}",
        )

    toolchain = plan["lean_toolchain"]
    require(isinstance(toolchain, dict), "lean_toolchain must be an object")
    exact_keys(toolchain, {"path", "value"}, "lean_toolchain")
    toolchain_path = safe_regular(PROJECT, toolchain["path"], "Lean toolchain")
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
            len(raw_axioms) == len(set(raw_axioms)),
            f"axiom policy for {theorem} repeats dependencies",
        )
        require(
            set(raw_axioms) <= ALLOWED_AXIOMS,
            f"axiom policy for {theorem} contains a forbidden dependency",
        )

    require(
        plan["artifact_name"] == ARTIFACT_NAME
        and SAFE_ARTIFACT.fullmatch(plan["artifact_name"]) is not None,
        "artifact_name differs",
    )
    require(
        plan["completion_claims"] == PLAN_COMPLETION_BOUNDARY,
        "kernel-plan completion boundary differs",
    )
    return {
        "claims": claims,
        "entrypoint_path": entrypoint_path,
        "formal_claims": formal,
        "plan": plan,
        "sources": source_values,
        "toolchain_path": toolchain_path,
    }


def git_exact_head(paths: list[pathlib.Path]) -> dict[str, Any]:
    """Require selected worktree bytes to be tracked and equal to ``HEAD``."""
    head_run, head_output = run(["git", "rev-parse", "HEAD"], ROOT)
    head = head_output.strip()
    require(HEX40.fullmatch(head) is not None, "Git HEAD is not a SHA-1 commit")
    github_sha = os.environ.get("GITHUB_SHA", "")
    if github_sha:
        require(github_sha == head, "GITHUB_SHA differs from checked-out HEAD")

    bindings: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        require(tracked.returncode == 0, f"exact-head input is untracked: {relative}")
        at_head = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        require(at_head.returncode == 0, f"cannot read exact-head input: {relative}")
        worktree = path.read_bytes()
        require(at_head.stdout == worktree, f"worktree bytes differ from HEAD: {relative}")
        bindings.append(identity(path, ROOT))
    return {
        "commit": head,
        "head_command": head_run,
        "inputs": bindings,
        "github_sha": github_sha,
    }


def runtime_evidence(
    plan_path: pathlib.Path = DEFAULT_PLAN,
    claims_path: pathlib.Path = DEFAULT_CLAIMS,
) -> dict[str, Any]:
    static = static_validation(plan_path, claims_path)
    plan = static["plan"]
    tool_path = pathlib.Path(__file__).resolve()
    exact_head = git_exact_head(
        [
            plan_path,
            claims_path,
            WORKFLOW,
            static["entrypoint_path"],
            static["toolchain_path"],
            tool_path,
            *PROJECT_LOCK_FILES,
            *[item["path"] for item in static["sources"]],
        ]
    )

    source_runs: list[dict[str, Any]] = []
    compiled_objects: list[dict[str, Any]] = []
    for item in static["sources"]:
        source_run, _ = run(["lake", "env", "lean", item["plan"]["path"]], PROJECT)
        source_runs.append(source_run)
        compiled_path = safe_regular(
            PROJECT,
            item["plan"]["compiled_object"],
            "compiled publication object",
        )
        compiled_objects.append(identity(compiled_path, PROJECT))

    audit_path = PROJECT / ".lake/build/SurvivalConnectabilityAxiomAudit.lean"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_text = (
        "\n".join(f"import {item['plan']['import']}" for item in static["sources"])
        + "\n\n"
        + "\n".join(f"#print axioms {theorem}" for theorem in plan["theorems"])
        + "\n"
    )
    audit_path.write_text(audit_text, encoding="utf-8")
    audit_run, audit_output = run(
        ["lake", "env", "lean", str(audit_path.relative_to(PROJECT))],
        PROJECT,
    )
    observed_axioms = parse_axiom_reports(audit_output, plan["theorems"])
    require(
        set(observed_axioms) == set(plan["theorems"]),
        "runtime axiom reports are incomplete",
    )
    expected_axioms = {
        theorem: sorted(axioms)
        for theorem, axioms in plan["axiom_audit"]["expected_axioms_by_theorem"].items()
    }
    require(
        observed_axioms == expected_axioms,
        f"runtime axiom dependencies differ: observed={observed_axioms}",
    )

    source_by_theorem: dict[str, dict[str, Any]] = {}
    for theorem in plan["theorems"]:
        short_name = theorem.rsplit(".", 1)[-1]
        matches = [
            item
            for item in static["sources"]
            if re.search(
                rf"(?m)^\s*theorem\s+{re.escape(short_name)}\b",
                strip_lean_comments_and_strings(item["path"].read_text(encoding="utf-8")),
            )
        ]
        require(len(matches) == 1, f"runtime theorem/source binding differs: {theorem}")
        source_by_theorem[theorem] = matches[0]["identity"]

    formal_bindings = [
        {
            "claim_id": item["claim_id"],
            "proof_refs": item["proof_refs"],
            "sources_by_theorem": {
                theorem: source_by_theorem[theorem] for theorem in item["proof_refs"]
            },
            "axioms_by_theorem": {
                theorem: observed_axioms[theorem] for theorem in item["proof_refs"]
            },
        }
        for item in static["formal_claims"]
    ]
    return {
        "schema": EVIDENCE_SCHEMA,
        "state": "KERNEL_VERIFIED",
        "publication_id": PUBLICATION_ID,
        "exact_head": exact_head,
        "tool": identity(tool_path, ROOT),
        "workflow_definition": identity(WORKFLOW, ROOT),
        "plan": identity(plan_path, ROOT),
        "claim_matrix": identity(claims_path, ROOT),
        "sources": [item["identity"] for item in static["sources"]],
        "compiled_objects": compiled_objects,
        "entrypoint": identity(static["entrypoint_path"], PROJECT),
        "lean_toolchain": {
            **identity(static["toolchain_path"], PROJECT),
            "value": plan["lean_toolchain"]["value"],
        },
        "project_lock_files": [identity(path, PROJECT) for path in PROJECT_LOCK_FILES],
        "formal_claim_count": len(static["formal_claims"]),
        "theorem_count": len(plan["theorems"]),
        "formal_bindings": formal_bindings,
        "axioms_by_theorem": observed_axioms,
        "runtime": {
            "exact_source_kernel_checks": source_runs,
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
        help="validate tracked inputs without invoking Lean or checking Git HEAD",
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
                "sources": [item["identity"] for item in value["sources"]],
                "formal_claim_count": len(value["formal_claims"]),
                "theorem_count": len(value["plan"]["theorems"]),
            }
        else:
            output = runtime_evidence(plan_path, claims_path)
    except EvidenceError as exc:
        print(f"BLOCK FIT_KERNEL_EVIDENCE_INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
