#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize and verify the scoped Denk-Mengenlehre finite gate model."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = pathlib.PurePosixPath("policy/DENK_MENGENLEHRE_V1.json")
CONTEXT_PATH = pathlib.PurePosixPath("AI_CONTEXT.json")
MANIFEST_PATH = pathlib.PurePosixPath("REPOSITORY_FILE_MANIFEST.json")
SCOPE_ID = "qikvrt-denk-mengenlehre-v1"
POLICY_SCHEMA = "qikvrt-denk-mengenlehre/1.0"
POWER_SET_SCHEMA = "qikvrt-denk-mengenlehre-power-set/1.0"
REPORT_SCHEMA = "qikvrt-denk-mengenlehre-gate-report/1.0"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    """Fail-closed contract violation."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json(relative: pathlib.PurePosixPath) -> dict[str, Any]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"required regular file is absent: {relative}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON in {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {relative}")
    return value


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_path(value: object, label: str) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty repository path")
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ContractError(f"{label} is not a normalized repository path")
    return path


def _file_record(relative: pathlib.PurePosixPath) -> dict[str, object]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"required regular file is absent: {relative}")
    data = path.read_bytes()
    return {
        "path": str(relative),
        "bytes": len(data),
        "sha256": _sha256(data),
    }


def _require_string_list(
    container: Mapping[str, Any],
    key: str,
    *,
    unique: bool = True,
) -> list[str]:
    value = container.get(key)
    if (
        not isinstance(value, list)
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ContractError(f"{key} must be a non-empty-string list")
    if unique and len(set(value)) != len(value):
        raise ContractError(f"{key} must not contain duplicates")
    return list(value)


def _load_policy() -> dict[str, Any]:
    policy = _load_json(POLICY_PATH)
    if policy.get("schema") != POLICY_SCHEMA:
        raise ContractError("unsupported Denk-Mengenlehre policy schema")
    if policy.get("scope_id") != SCOPE_ID:
        raise ContractError("Denk-Mengenlehre scope identity drift")
    if policy.get("author") != "Ingolf Lohmann":
        raise ContractError("Denk-Mengenlehre author binding drift")
    if policy.get("epistemic_classification") != "INTERPRETIVE_FORMAL_MODEL":
        raise ContractError("Denk-Mengenlehre epistemic classification drift")
    return policy


def _gate_ids(policy: Mapping[str, Any]) -> list[str]:
    model = policy.get("set_model")
    if not isinstance(model, dict):
        raise ContractError("set_model must be an object")
    gate_ids = _require_string_list(model, "gate_ids")
    if gate_ids != [f"G{index}" for index in range(1, 7)]:
        raise ContractError("gate_ids must be exactly G1 through G6")
    gates = policy.get("gates")
    if (
        not isinstance(gates, list)
        or [gate.get("id") for gate in gates if isinstance(gate, dict)]
        != gate_ids
    ):
        raise ContractError("gate definitions do not match gate_ids")
    return gate_ids


def build_power_set(policy: Mapping[str, Any]) -> dict[str, Any]:
    gate_ids = _gate_ids(policy)
    subsets: list[dict[str, object]] = []
    for cardinality in range(len(gate_ids) + 1):
        for members in itertools.combinations(gate_ids, cardinality):
            subsets.append(
                {
                    "index": len(subsets),
                    "cardinality": cardinality,
                    "passed_gate_ids": list(members),
                }
            )
    return {
        "_license": {
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "rights_holder": "Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "classification": "finite_gate_power_set_json",
        },
        "schema": POWER_SET_SCHEMA,
        "scope_id": SCOPE_ID,
        "qualified_batch_alias": policy.get("qualified_batch_alias"),
        "gate_ids": gate_ids,
        "cardinality": len(subsets),
        "semantics": (
            "All subsets of gate IDs classified as passed; this is not the "
            "set of all ternary PENDING/FAIL/PASS assignments."
        ),
        "subsets": subsets,
    }


def _atomic_write(relative: pathlib.PurePosixPath, data: bytes) -> None:
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temporary = pathlib.Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def materialize() -> dict[str, object]:
    policy = _load_policy()
    artifacts = policy.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ContractError("artifacts must be an object")
    power_set_path = _relative_path(artifacts.get("power_set"), "power_set")
    data = _canonical_json(build_power_set(policy))
    _atomic_write(power_set_path, data)
    return {
        "scope_id": SCOPE_ID,
        "state": "MATERIALIZED",
        "artifact": {
            "path": str(power_set_path),
            "bytes": len(data),
            "sha256": _sha256(data),
        },
    }


def _run_git(*arguments: str) -> str:
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    process = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=environment,
    )
    if process.returncode != 0:
        diagnostic = process.stderr.strip() or process.stdout.strip()
        raise ContractError(
            f"git {' '.join(arguments)} failed: "
            f"{diagnostic or f'exit {process.returncode}'}"
        )
    return process.stdout.strip()


def _manifest_records() -> dict[str, Mapping[str, Any]]:
    manifest = _load_json(MANIFEST_PATH)
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ContractError("repository manifest files must be a list")
    records: dict[str, Mapping[str, Any]] = {}
    for record in files:
        if not isinstance(record, dict):
            raise ContractError("repository manifest record must be an object")
        path = record.get("path")
        if not isinstance(path, str) or path in records:
            raise ContractError("repository manifest path is invalid or duplicate")
        records[path] = record
    return records


def _manifest_binds(
    records: Mapping[str, Mapping[str, Any]],
    relative: pathlib.PurePosixPath,
) -> bool:
    current = _file_record(relative)
    record = records.get(str(relative))
    return bool(
        record is not None
        and record.get("bytes") == current["bytes"]
        and record.get("sha256") == current["sha256"]
        and SHA256_RE.fullmatch(str(record.get("sha256", "")))
    )


def _context_descriptor(
    policy: Mapping[str, Any],
) -> tuple[bool, dict[str, Any] | None]:
    context = _load_json(CONTEXT_PATH)
    self_reference = policy.get("self_reference")
    if not isinstance(self_reference, dict):
        raise ContractError("self_reference must be an object")
    collection_name = self_reference.get("descriptor_collection")
    descriptor_key = self_reference.get("descriptor_key")
    if not isinstance(collection_name, str) or not isinstance(descriptor_key, str):
        raise ContractError("self-reference descriptor keys must be strings")
    collection = context.get(collection_name)
    descriptor = collection.get(descriptor_key) if isinstance(collection, dict) else None
    if not isinstance(descriptor, dict):
        return False, None
    expected_artifacts = policy.get("artifacts")
    bound = bool(
        descriptor.get("scope_id") == SCOPE_ID
        and descriptor.get("specification") == expected_artifacts.get("specification")
        and descriptor.get("prompt_template")
        == expected_artifacts.get("prompt_template")
        and descriptor.get("policy") == str(POLICY_PATH)
        and descriptor.get("classification") == "INTERPRETIVE_FORMAL_MODEL"
        and descriptor.get("self_reference_relation")
        == "descriptor_references_scope"
        and descriptor.get("system_member_of_itself") is False
    )
    read_order = context.get("required_read_order")
    required_paths = {
        str(expected_artifacts.get("specification")),
        str(expected_artifacts.get("prompt_template")),
        str(POLICY_PATH),
    }
    bound = bool(
        bound
        and isinstance(read_order, list)
        and required_paths.issubset(set(read_order))
    )
    return bound, descriptor


def _integrity_result() -> tuple[bool, str]:
    sys.path.insert(0, str(ROOT))
    try:
        from tools import qikvrt_integrity

        result = qikvrt_integrity.verify(ROOT)
    except (ImportError, OSError, RuntimeError, UnicodeError, ValueError) as exc:
        return False, f"integrity invocation failed: {exc}"
    return bool(result.ok), result.message


def _gate(
    gate_id: str,
    name: str,
    passed: bool,
    evidence: object,
    blocker: str | None = None,
) -> dict[str, object]:
    return {
        "id": gate_id,
        "name": name,
        "state": "PASS" if passed else "BLOCK",
        "pass": passed,
        "evidence": evidence,
        "blocker": None if passed else blocker,
    }


def conjunctive_batch_pass(gates: list[Mapping[str, Any]]) -> bool:
    """Return true only for exactly six successful, unique G1..G6 gates."""

    expected = [f"G{index}" for index in range(1, 7)]
    observed = [gate.get("id") for gate in gates]
    return observed == expected and all(gate.get("pass") is True for gate in gates)


def build_report() -> dict[str, Any]:
    policy = _load_policy()
    gate_ids = _gate_ids(policy)
    artifacts = policy.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ContractError("artifacts must be an object")

    core_names = ("specification", "prompt_template", "policy")
    core_records = [
        _file_record(_relative_path(artifacts.get(name), name))
        for name in core_names
    ]
    context_bound, descriptor = _context_descriptor(policy)
    g1_pass = context_bound and len(core_records) == len(core_names)
    g1 = _gate(
        "G1",
        "MATERIALIZATION",
        g1_pass,
        {"artifacts": core_records, "context_descriptor": descriptor},
        "core artifacts or AI_CONTEXT binding are incomplete",
    )

    manifest_records = _manifest_records()
    validator_path = _relative_path(artifacts.get("validator"), "validator")
    descriptor_path = _relative_path(
        policy.get("self_reference", {}).get("descriptor_path"),
        "descriptor_path",
    )
    validator_bound = _manifest_binds(manifest_records, validator_path)
    descriptor_bound = _manifest_binds(manifest_records, descriptor_path)
    self_reference = policy.get("self_reference")
    typed_reference = bool(
        isinstance(self_reference, dict)
        and self_reference.get("referent_scope_id") == SCOPE_ID
        and self_reference.get("relation") == "descriptor_references_scope"
        and self_reference.get("system_member_of_itself") is False
        and context_bound
    )
    g2_pass = validator_bound and descriptor_bound and typed_reference
    g2 = _gate(
        "G2",
        "TYPED_SELF_REFERENCE",
        g2_pass,
        {
            "descriptor_path": str(descriptor_path),
            "descriptor_references_scope": typed_reference,
            "descriptor_manifest_bound": descriptor_bound,
            "validator_path": str(validator_path),
            "validator_manifest_bound": validator_bound,
            "system_member_of_itself": False,
        },
        "typed descriptor or manifest self-inclusion is incomplete",
    )

    power_set_path = _relative_path(artifacts.get("power_set"), "power_set")
    expected_power_set = _canonical_json(build_power_set(policy))
    actual_power_set = (ROOT / power_set_path).read_bytes()
    power_set = _load_json(power_set_path)
    subsets = power_set.get("subsets")
    unique_subsets = {
        tuple(entry.get("passed_gate_ids", []))
        for entry in subsets
        if isinstance(entry, dict)
    } if isinstance(subsets, list) else set()
    g3_pass = bool(
        actual_power_set == expected_power_set
        and power_set.get("schema") == POWER_SET_SCHEMA
        and power_set.get("gate_ids") == gate_ids
        and power_set.get("cardinality") == 64
        and isinstance(subsets, list)
        and len(subsets) == 64
        and len(unique_subsets) == 64
        and () in unique_subsets
        and tuple(gate_ids) in unique_subsets
    )
    g3 = _gate(
        "G3",
        "POWER_SET",
        g3_pass,
        {
            "artifact": _file_record(power_set_path),
            "declared_cardinality": power_set.get("cardinality"),
            "observed_unique_subsets": len(unique_subsets),
            "semantics": "subsets of passed gate IDs",
        },
        "power-set artifact is absent, non-canonical or incomplete",
    )

    set_model = policy.get("set_model")
    formal_boundary = policy.get("formal_boundary")
    universe = set(_require_string_list(policy, "candidate_input_universe"))
    allowed = set(_require_string_list(policy, "allowed_inputs"))
    loaded = set(_require_string_list(policy, "loaded_inputs"))
    excluded = set(_require_string_list(policy, "excluded_inputs"))
    complement_partition = bool(
        allowed.isdisjoint(excluded)
        and allowed | excluded == universe
        and excluded == universe - allowed
    )
    no_excluded_loaded = loaded.isdisjoint(excluded) and loaded <= allowed
    g5_pass = complement_partition and no_excluded_loaded

    requirement_checks: dict[str, bool] = {
        "R1_CORE_ARTIFACTS_MATERIALIZED": g1_pass,
        "R2_EMPTY_INITIAL_STATE": bool(
            isinstance(set_model, dict) and set_model.get("initial_evidence") == []
        ),
        "R3_TYPED_SELF_REFERENCE": g2_pass,
        "R4_POWER_SET_ENUMERATED": g3_pass,
        "R5_CONJUNCTIVE_PASS_SEMANTICS": bool(
            isinstance(set_model, dict)
            and set_model.get("batch_pass_formula")
            == "AND(status(G_i) == PASS for every G_i in G)"
            and set_model.get("evidence_formula")
            == "UNION(Evidence(G_i) for every G_i in G)"
        ),
        "R6_RELATIVE_COMPLEMENT_PARTITION": complement_partition,
        "R7_SCOPE_IDENTITY_DISTINCT": bool(
            policy.get("qualified_batch_alias") == "DENK-MENGENLEHRE-BATCH-002"
            and "CONTENT-DISPOSITION-BATCH-002"
            in _require_string_list(policy, "distinct_from")
            and "github-actions-artifact-8696689772"
            in _require_string_list(policy, "distinct_from")
        ),
        "R8_FALSE_PASS_EXCLUDED": bool(
            isinstance(formal_boundary, dict)
            and formal_boundary.get("cognition_identical_to_zfc_proved") is False
            and formal_boundary.get("self_membership_claim") is False
            and formal_boundary.get("repository_evidence_is_truth_claim") is False
            and formal_boundary.get("poster_is_proof") is False
            and formal_boundary.get("scoped_pass_is_repository_wide_pass") is False
        ),
    }
    required = set(_require_string_list(policy, "requirements"))
    verified = {key for key, value in requirement_checks.items() if value}
    missing_requirements = sorted(required - verified)
    additional_requirements = sorted(verified - required)
    g4_pass = not missing_requirements
    g4 = _gate(
        "G4",
        "REQUIREMENT_COVERAGE",
        g4_pass,
        {
            "required": sorted(required),
            "verified": sorted(verified),
            "required_minus_verified": missing_requirements,
            "verified_minus_required": additional_requirements,
            "checks": requirement_checks,
        },
        "required requirement IDs are not fully verified",
    )

    g5 = _gate(
        "G5",
        "RELATIVE_COMPLEMENT",
        g5_pass,
        {
            "universe": sorted(universe),
            "allowed": sorted(allowed),
            "excluded": sorted(excluded),
            "loaded": sorted(loaded),
            "partition_complete": complement_partition,
            "loaded_intersection_excluded": sorted(loaded & excluded),
        },
        "input universe is not partitioned or an excluded input is loaded",
    )

    integrity_ok, integrity_message = _integrity_result()
    commit = _run_git("rev-parse", "HEAD")
    ref_name = _run_git("rev-parse", "--abbrev-ref", "HEAD")
    worktree_status = _run_git(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    exact_checkout = bool(
        SHA1_RE.fullmatch(commit)
        and ref_name != "HEAD"
        and not worktree_status
    )
    prerequisite_pass = all(gate["pass"] for gate in (g1, g2, g3, g4, g5))
    g6_pass = bool(prerequisite_pass and integrity_ok and exact_checkout)
    g6 = _gate(
        "G6",
        "CONJUNCTIVE_FINALIZATION",
        g6_pass,
        {
            "prerequisite_gate_ids": gate_ids[:5],
            "all_prerequisite_gates_pass": prerequisite_pass,
            "integrity_pass": integrity_ok,
            "integrity_message": integrity_message,
            "git_commit": commit,
            "git_ref": ref_name,
            "worktree_clean": not bool(worktree_status),
        },
        "one or more prerequisite gates, integrity or exact-checkout checks failed",
    )

    gates = [g1, g2, g3, g4, g5, g6]
    batch_pass = conjunctive_batch_pass(gates)
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "scope_id": SCOPE_ID,
        "qualified_batch_alias": policy.get("qualified_batch_alias"),
        "repository": _run_git("config", "--get", "remote.origin.url"),
        "git_ref": ref_name,
        "git_commit": commit,
        "state": "PASS" if batch_pass else "BLOCK",
        "batch_pass": batch_pass,
        "gates_passed": sum(1 for gate in gates if gate["pass"]),
        "gates_total": len(gates),
        "gates": gates,
        "initial_evidence": [],
        "evidence_accumulation": (
            "E_(i+1) = E_i union Evidence(G_(i+1))"
        ),
        "pass_semantics": "logical conjunction of G1 through G6",
        "boundary": (
            "Scoped interpretive-formal model verification only; no "
            "repository-wide PASS, FINAL_PASS, EFFECT_ACK_DONE, merge, "
            "synchronization, publication or deployment claim."
        ),
    }
    artifact_digest = _sha256(_canonical_json(report))
    report["artifact"] = {
        "kind": "content-addressed-scoped-gate-report",
        "sha256": artifact_digest,
        "numeric_artifact_id": None,
    }
    return report


def _render_text(report: Mapping[str, Any]) -> str:
    lines = [
        f"SCOPE: {report['scope_id']}",
        f"COMMIT: {report['git_commit']}",
        f"STATE: {report['state']}",
        f"GATES: {report['gates_passed']}/{report['gates_total']}",
        "ARTIFACT_SHA256: " + str(report["artifact"]["sha256"]),
        "BOUNDARY: scoped model verification only",
    ]
    for gate in report["gates"]:
        lines.append(
            f"{gate['id']}: {gate['state']}"
            + (f" — {gate['blocker']}" if gate["blocker"] else "")
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("materialize", "verify"))
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit canonical machine-readable JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "materialize":
            result = materialize()
            if args.json:
                sys.stdout.buffer.write(_canonical_json(result))
            else:
                artifact = result["artifact"]
                print(
                    "MATERIALIZED "
                    f"{artifact['path']} "
                    f"sha256={artifact['sha256']}"
                )
            return 0

        report = build_report()
        if args.json:
            sys.stdout.buffer.write(_canonical_json(report))
        else:
            print(_render_text(report))
        return 0 if report["batch_pass"] else 1
    except (
        ContractError,
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        if args.json:
            sys.stdout.buffer.write(
                _canonical_json(
                    {
                        "schema": REPORT_SCHEMA,
                        "scope_id": SCOPE_ID,
                        "state": "BLOCK",
                        "batch_pass": False,
                        "blocker": str(exc),
                    }
                )
            )
        else:
            print(f"BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
