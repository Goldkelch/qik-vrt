#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tools/qikvrt_adaptive_runtime.sh \
    --observations DIRECTORY \
    --output .qikvrt/evidence/collective-adaptive/RUN_ID \
    [--run-id RUN_ID]

The runtime validates and hashes attributable observations, then writes a
proposal-only evidence bundle. It never applies a proposal or emits
EFFECT_ACK_DONE.
EOF
}

observations=''
output=''
run_id=''

while (($#)); do
  case "$1" in
    --observations)
      (($# >= 2)) || { echo 'BLOCK: --observations requires a value' >&2; exit 2; }
      observations=$2
      shift 2
      ;;
    --output)
      (($# >= 2)) || { echo 'BLOCK: --output requires a value' >&2; exit 2; }
      output=$2
      shift 2
      ;;
    --run-id)
      (($# >= 2)) || { echo 'BLOCK: --run-id requires a value' >&2; exit 2; }
      run_id=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "BLOCK: unsupported argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "$observations" ]] || { echo 'BLOCK: --observations is required' >&2; exit 2; }
[[ -n "$output" ]] || { echo 'BLOCK: --output is required' >&2; exit 2; }

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(git -C "$script_dir/.." rev-parse --show-toplevel)
policy="$root/policy/COLLECTIVE_ADAPTIVE_COGNITION.json"
self="$root/tools/qikvrt_adaptive_runtime.sh"

command -v python3 >/dev/null 2>&1 || {
  echo 'BLOCK: python3 is required for deterministic JSON validation' >&2
  exit 2
}
[[ -f "$policy" ]] || { echo 'BLOCK: fixed cognition policy is missing' >&2; exit 2; }

python3 -B - "$root" "$policy" "$self" "$observations" "$output" "$run_id" <<'PY'
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any


class Blocked(RuntimeError):
    pass


def block(message: str) -> None:
    raise Blocked(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def load_no_duplicates(payload: bytes, label: str) -> Any:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                block(f"{label}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=pairs_hook)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        block(f"{label}: invalid UTF-8 JSON: {exc}")


def fixed_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def tracked_state(root: Path) -> str:
    return fixed_git(root, "status", "--porcelain=v1", "--untracked-files=no")


def reject_symlinked_output_base(root: Path) -> None:
    current = root
    for component in (".qikvrt", "evidence", "collective-adaptive"):
        current = current / component
        if os.path.lexists(current):
            metadata = os.lstat(current)
            if stat.S_ISLNK(metadata.st_mode):
                block(f"output base component is a symbolic link: {component}")
            if not stat.S_ISDIR(metadata.st_mode):
                block(f"output base component is not a directory: {component}")


def open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent_fd)
        except FileExistsError:
            pass
        return os.open(name, flags, dir_fd=parent_fd)


def same_open_directory(path: Path, file_descriptor: int) -> bool:
    try:
        path_metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    open_metadata = os.fstat(file_descriptor)
    return (
        stat.S_ISDIR(path_metadata.st_mode)
        and not stat.S_ISLNK(path_metadata.st_mode)
        and path_metadata.st_dev == open_metadata.st_dev
        and path_metadata.st_ino == open_metadata.st_ino
    )


def create_confined_output(root: Path, run_id: str) -> tuple[int, list[tuple[Path, int]]]:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    root_fd = os.open(root, flags)
    opened: list[tuple[Path, int]] = [(root, root_fd)]
    try:
        parent_fd = root_fd
        current = root
        for component in (".qikvrt", "evidence", "collective-adaptive"):
            current = current / component
            child_fd = open_directory_at(parent_fd, component)
            opened.append((current, child_fd))
            parent_fd = child_fd
        try:
            os.mkdir(run_id, mode=0o755, dir_fd=parent_fd)
        except FileExistsError:
            block("output directory already exists; runs are append-only")
        output_fd = open_directory_at(parent_fd, run_id)
        output_path = current / run_id
        opened.append((output_path, output_fd))
        if not all(same_open_directory(path, descriptor) for path, descriptor in opened):
            block("output path changed during no-follow directory creation")
        return output_fd, opened
    except Exception:
        for _, descriptor in reversed(opened):
            os.close(descriptor)
        raise


def write_new_file_at(directory_fd: int, name: str, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o644, dir_fd=directory_fd)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
OBSERVATION_KEYS = {
    "schema",
    "observation_id",
    "observer_id",
    "subject",
    "measured_at_utc",
    "measurements",
    "findings",
    "recommendations",
    "limitations",
}
MEASUREMENT_KEYS = {"name", "value", "unit", "method"}
FINDING_KEYS = {"finding_id", "statement", "status", "measurement_refs"}
RECOMMENDATION_KEYS = {
    "proposal_id",
    "description",
    "rationale",
    "risk",
    "finding_refs",
}
FINDING_STATES = {"PASS", "CONTINUE", "BLOCK", "UNKNOWN"}
RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def bounded_text(value: Any, label: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        block(f"{label}: expected string")
    if not empty and not value.strip():
        block(f"{label}: empty string is not allowed")
    if len(value) > maximum:
        block(f"{label}: exceeds {maximum} characters")
    return value


def identifier(value: Any, label: str) -> str:
    text = bounded_text(value, label, 128)
    if ID_RE.fullmatch(text) is None:
        block(f"{label}: invalid identifier")
    return text


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        block(f"{label}: expected object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        block(f"{label}: key mismatch; missing={missing}, unknown={unknown}")
    return value


def string_refs(value: Any, allowed: set[str], label: str) -> list[str]:
    if not isinstance(value, list):
        block(f"{label}: expected array")
    result: list[str] = []
    for index, item in enumerate(value):
        ref = identifier(item, f"{label}[{index}]")
        if ref not in allowed:
            block(f"{label}[{index}]: unresolved reference {ref!r}")
        result.append(ref)
    if len(result) != len(set(result)):
        block(f"{label}: duplicate references")
    if not result:
        block(f"{label}: at least one evidence reference is required")
    return result


def validate_observation(
    document: Any,
    label: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    item = exact_keys(document, OBSERVATION_KEYS, label)
    expected_schema = policy["observation_schema"]
    if item["schema"] != expected_schema:
        block(f"{label}: unsupported schema")

    observation_id = identifier(item["observation_id"], f"{label}.observation_id")
    observer_id = identifier(item["observer_id"], f"{label}.observer_id")
    maximum_text = policy["input_limits"]["maximum_text_characters"]
    bounded_text(item["subject"], f"{label}.subject", maximum_text)
    measured = bounded_text(item["measured_at_utc"], f"{label}.measured_at_utc", 20)
    if UTC_RE.fullmatch(measured) is None:
        block(f"{label}.measured_at_utc: expected YYYY-MM-DDTHH:MM:SSZ")
    try:
        dt.datetime.strptime(measured, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        block(f"{label}.measured_at_utc: invalid timestamp: {exc}")

    measurements = item["measurements"]
    if not isinstance(measurements, list) or not measurements:
        block(f"{label}.measurements: non-empty array required")
    if len(measurements) > policy["input_limits"]["maximum_measurements_each"]:
        block(f"{label}.measurements: limit exceeded")
    measurement_names: set[str] = set()
    for index, raw in enumerate(measurements):
        measurement = exact_keys(raw, MEASUREMENT_KEYS, f"{label}.measurements[{index}]")
        name = identifier(measurement["name"], f"{label}.measurements[{index}].name")
        if name in measurement_names:
            block(f"{label}.measurements: duplicate name {name!r}")
        measurement_names.add(name)
        scalar = measurement["value"]
        if not isinstance(scalar, (str, int, float, bool)) or scalar is None:
            block(f"{label}.measurements[{index}].value: scalar required")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            block(f"{label}.measurements[{index}].value: finite number required")
        if isinstance(scalar, str):
            bounded_text(scalar, f"{label}.measurements[{index}].value", maximum_text, empty=True)
        bounded_text(measurement["unit"], f"{label}.measurements[{index}].unit", 128)
        bounded_text(measurement["method"], f"{label}.measurements[{index}].method", maximum_text)

    findings = item["findings"]
    if not isinstance(findings, list) or not findings:
        block(f"{label}.findings: non-empty array required")
    if len(findings) > policy["input_limits"]["maximum_findings_each"]:
        block(f"{label}.findings: limit exceeded")
    finding_ids: set[str] = set()
    for index, raw in enumerate(findings):
        finding = exact_keys(raw, FINDING_KEYS, f"{label}.findings[{index}]")
        finding_id = identifier(finding["finding_id"], f"{label}.findings[{index}].finding_id")
        if finding_id in finding_ids:
            block(f"{label}.findings: duplicate id {finding_id!r}")
        finding_ids.add(finding_id)
        bounded_text(finding["statement"], f"{label}.findings[{index}].statement", maximum_text)
        if finding["status"] not in FINDING_STATES:
            block(f"{label}.findings[{index}].status: unsupported status")
        string_refs(
            finding["measurement_refs"],
            measurement_names,
            f"{label}.findings[{index}].measurement_refs",
        )

    recommendations = item["recommendations"]
    if not isinstance(recommendations, list):
        block(f"{label}.recommendations: expected array")
    if len(recommendations) > policy["input_limits"]["maximum_recommendations_each"]:
        block(f"{label}.recommendations: limit exceeded")
    proposal_ids: set[str] = set()
    for index, raw in enumerate(recommendations):
        proposal = exact_keys(raw, RECOMMENDATION_KEYS, f"{label}.recommendations[{index}]")
        proposal_id = identifier(proposal["proposal_id"], f"{label}.recommendations[{index}].proposal_id")
        if proposal_id in proposal_ids:
            block(f"{label}.recommendations: duplicate id {proposal_id!r}")
        proposal_ids.add(proposal_id)
        bounded_text(proposal["description"], f"{label}.recommendations[{index}].description", maximum_text)
        bounded_text(proposal["rationale"], f"{label}.recommendations[{index}].rationale", maximum_text)
        if proposal["risk"] not in RISKS:
            block(f"{label}.recommendations[{index}].risk: unsupported risk")
        string_refs(
            proposal["finding_refs"],
            finding_ids,
            f"{label}.recommendations[{index}].finding_refs",
        )

    limitations = item["limitations"]
    if not isinstance(limitations, list) or not limitations:
        block(f"{label}.limitations: non-empty array required")
    for index, limitation in enumerate(limitations):
        bounded_text(limitation, f"{label}.limitations[{index}]", maximum_text)

    return {
        **item,
        "observation_id": observation_id,
        "observer_id": observer_id,
    }


def main() -> None:
    root = Path(sys.argv[1]).resolve(strict=True)
    policy_path = Path(sys.argv[2]).resolve(strict=True)
    runtime_path = Path(sys.argv[3]).resolve(strict=True)
    observations_arg = Path(sys.argv[4])
    output_arg = Path(sys.argv[5])
    requested_run_id = sys.argv[6]

    if not observations_arg.is_absolute():
        observations_arg = Path.cwd() / observations_arg
    observations_dir = observations_arg.resolve(strict=True)
    if not observations_dir.is_dir():
        block("observations path is not a directory")

    if not output_arg.is_absolute():
        output_arg = root / output_arg
    output_dir = Path(os.path.abspath(output_arg))
    allowed_root = root / ".qikvrt/evidence/collective-adaptive"
    try:
        relative_output = output_dir.relative_to(allowed_root)
    except ValueError:
        block("output must be below .qikvrt/evidence/collective-adaptive")
    if len(relative_output.parts) != 1:
        block("output must be exactly one new run-id directory below the allowed root")
    derived_run_id = identifier(relative_output.name, "output run id")
    run_id = identifier(requested_run_id, "--run-id") if requested_run_id else derived_run_id
    if run_id != derived_run_id:
        block("--run-id must equal the output directory name")
    if os.path.lexists(output_dir):
        block("output directory already exists; runs are append-only")
    if output_dir == observations_dir or output_dir in observations_dir.parents or observations_dir in output_dir.parents:
        block("observation and output directories must not contain one another")
    reject_symlinked_output_base(root)

    policy_payload = policy_path.read_bytes()
    policy = load_no_duplicates(policy_payload, "policy")
    if not isinstance(policy, dict):
        block("policy: expected object")
    required_policy = {
        "schema": "qikvrt_collective_adaptive_cognition_policy_v1",
        "mode": "MEASURE_HASH_PROPOSE_ONLY",
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            block(f"policy: fixed {key} invariant failed")
    boundary = policy.get("effect_boundary", {})
    if boundary != {
        "runtime_state": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
        "human_review_required": True,
        "separate_effect_ack_required": True,
        "release_state": "EFFECT_ACK_DONE",
        "runtime_may_issue_release_state": False,
        "runtime_may_infer_release_state": False,
    }:
        block("policy: effect boundary is not fail-closed")
    threshold = policy.get("collective_threshold", {})
    if (
        threshold.get("minimum_observations", 0) < 2
        or threshold.get("minimum_distinct_observer_identifiers", 0) < 2
        or threshold.get("observer_identifier_required") is not True
        or threshold.get("disagreement_must_be_preserved") is not True
    ):
        block("policy: collective threshold is not fail-closed")
    collectivity_boundary = policy.get("collectivity_boundary", {})
    if collectivity_boundary != {
        "basis": "DISTINCT_OBSERVER_IDENTIFIERS_ONLY",
        "organizational_independence_verified": False,
        "causal_independence_verified": False,
        "person_identity_verified": False,
        "observer_identifier_authentication_verified": False,
        "consensus_claim_allowed": False,
    }:
        block("policy: collectivity boundary is overstated or ambiguous")
    required_checks = {
        "full_repository_test_suite",
        "provenance_and_rights_review",
        "security_review",
        "scientific_claim_boundary_review",
        "downstream_effect_review",
        "codeowner_review",
        "responsible_human_approval",
        "fresh_authenticated_effect_ack_evaluation",
    }
    if set(policy.get("mandatory_checks_before_implementation", [])) != required_checks:
        block("policy: mandatory check set is incomplete or ambiguous")
    required_prohibitions = {
        "execute_observation_content",
        "modify_tracked_files",
        "modify_policy_or_runtime",
        "commit",
        "push",
        "open_or_modify_pull_request",
        "approve_or_merge",
        "tag",
        "release",
        "publish",
        "deploy",
        "change_permissions_or_secrets",
        "network_access",
        "network_write",
        "auto_install_or_update",
        "recursive_agent_spawn",
        "self_mutation",
    }
    if set(policy.get("forbidden_actions", [])) != required_prohibitions:
        block("policy: forbidden action set is incomplete or ambiguous")

    entries = sorted(observations_dir.iterdir(), key=lambda path: path.name)
    if not entries:
        block("no observations found")
    for entry in entries:
        if entry.is_symlink() or not entry.is_file() or entry.suffix != ".json":
            block(f"unsupported observation entry: {entry.name}")
    maximum_files = policy["input_limits"]["maximum_observation_files"]
    if len(entries) > maximum_files:
        block("observation file limit exceeded")

    observations: list[dict[str, Any]] = []
    evidence_inputs: list[dict[str, Any]] = []
    seen_observations: set[str] = set()
    maximum_bytes = policy["input_limits"]["maximum_observation_bytes_each"]
    for entry in entries:
        payload = entry.read_bytes()
        if len(payload) > maximum_bytes:
            block(f"{entry.name}: byte limit exceeded")
        document = load_no_duplicates(payload, entry.name)
        observation = validate_observation(document, entry.name, policy)
        if observation["observation_id"] in seen_observations:
            block(f"duplicate observation id: {observation['observation_id']}")
        seen_observations.add(observation["observation_id"])
        observations.append(observation)
        evidence_inputs.append(
            {
                "file": entry.name,
                "bytes": len(payload),
                "sha256": sha256(payload),
                "observation_id": observation["observation_id"],
                "observer_id": observation["observer_id"],
                "subject": observation["subject"],
                "measured_at_utc": observation["measured_at_utc"],
            }
        )

    if len(observations) < threshold["minimum_observations"]:
        block("minimum observation count not met")
    distinct_observer_identifiers = sorted({item["observer_id"] for item in observations})
    if len(distinct_observer_identifiers) < threshold["minimum_distinct_observer_identifiers"]:
        block("minimum distinct-observer-identifier count not met")

    tracked_before = tracked_state(root)
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    aggregate_input = "".join(
        f"{item['file']}\0{item['sha256']}\n" for item in evidence_inputs
    ).encode("utf-8")
    evidence = {
        "schema": policy["output_schemas"]["evidence"],
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "mode": policy["mode"],
        "repository": {
            "commit": fixed_git(root, "rev-parse", "HEAD"),
            "tree": fixed_git(root, "rev-parse", "HEAD^{tree}"),
            "tracked_worktree_state_sha256": sha256(tracked_before.encode("utf-8")),
        },
        "policy": {
            "path": "policy/COLLECTIVE_ADAPTIVE_COGNITION.json",
            "sha256": sha256(policy_payload),
        },
        "runtime": {
            "path": "tools/qikvrt_adaptive_runtime.sh",
            "sha256": sha256(runtime_path.read_bytes()),
        },
        "observations": evidence_inputs,
        "observation_set_sha256": sha256(aggregate_input),
    }
    evidence_payload = canonical_bytes(evidence)
    evidence_digest = sha256(evidence_payload)

    finding_counts = {state: 0 for state in sorted(FINDING_STATES)}
    proposal_groups: dict[str, dict[str, Any]] = {}
    for observation in observations:
        for finding in observation["findings"]:
            finding_counts[finding["status"]] += 1
        for recommendation in observation["recommendations"]:
            proposal_id = recommendation["proposal_id"]
            group = proposal_groups.setdefault(proposal_id, {"variants": {}})
            variant_body = {
                "description": recommendation["description"],
                "rationale": recommendation["rationale"],
                "risk": recommendation["risk"],
            }
            variant_key = sha256(canonical_bytes(variant_body))
            variant = group["variants"].setdefault(
                variant_key,
                {
                    **variant_body,
                    "observer_ids": set(),
                    "observation_ids": set(),
                    "finding_refs": set(),
                },
            )
            variant["observer_ids"].add(observation["observer_id"])
            variant["observation_ids"].add(observation["observation_id"])
            variant["finding_refs"].update(recommendation["finding_refs"])

    proposals: list[dict[str, Any]] = []
    conflicts: list[str] = []
    for proposal_id in sorted(proposal_groups):
        raw_variants = proposal_groups[proposal_id]["variants"]
        variants: list[dict[str, Any]] = []
        all_observers: set[str] = set()
        for variant_key in sorted(raw_variants):
            raw_variant = raw_variants[variant_key]
            observer_identifiers = sorted(raw_variant["observer_ids"])
            all_observers.update(observer_identifiers)
            variants.append(
                {
                    "variant_sha256": variant_key,
                    "description": raw_variant["description"],
                    "rationale": raw_variant["rationale"],
                    "risk": raw_variant["risk"],
                    "observer_identifiers": observer_identifiers,
                    "observation_ids": sorted(raw_variant["observation_ids"]),
                    "finding_refs": sorted(raw_variant["finding_refs"]),
                }
            )
        content_match = len(variants) == 1
        if not content_match:
            conflicts.append(proposal_id)
        proposals.append(
            {
                "proposal_id": proposal_id,
                "content_match": content_match,
                "supporting_observer_identifier_count": len(all_observers),
                "variants": variants,
            }
        )

    mandatory_checks = policy["mandatory_checks_before_implementation"]
    proposal = {
        "schema": policy["output_schemas"]["proposal"],
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "mode": policy["mode"],
        "evidence_sha256": evidence_digest,
        "collective_summary": {
            "observation_count": len(observations),
            "distinct_observer_identifier_count": len(distinct_observer_identifiers),
            "observer_identifiers": distinct_observer_identifiers,
            "organizational_independence_verified": False,
            "causal_independence_verified": False,
            "person_identity_verified": False,
            "observer_identifier_authentication_verified": False,
            "consensus_claimed": False,
            "finding_counts": finding_counts,
            "proposal_count": len(proposals),
            "conflicting_proposal_ids": conflicts,
        },
        "proposals": proposals,
        "mandatory_checks": [
            {"check": check, "status": "PENDING_SEPARATE_REVIEW"}
            for check in mandatory_checks
        ],
        "human_review": {
            "required": True,
            "completed": False,
            "runtime_may_approve": False,
        },
        "effect_ack": {
            "required": True,
            "state": "EFFECT_ACK_CONTINUE",
            "ordinary_release": False,
            "runtime_may_issue_done": False,
            "next_required_checks": mandatory_checks,
        },
        "limitations": {
            "independence_verified": False,
            "consensus_claimed": False,
            "statements": [
                "Distinct observer identifiers do not prove distinct persons, organizations, methods, or causal independence.",
                "Observer identifiers are labels; this runtime does not authenticate the person or organization behind them.",
                "Matching proposal content is not organizational consensus and is not evidence of truth or authorization.",
            ],
            "reported_by_observation": [
                {
                    "observation_id": observation["observation_id"],
                    "observer_identifier": observation["observer_id"],
                    "limitations": observation["limitations"],
                }
                for observation in observations
            ],
        },
    }
    proposal_payload = canonical_bytes(proposal)

    output_fd, opened_directories = create_confined_output(root, run_id)
    try:
        write_new_file_at(output_fd, "evidence.json", evidence_payload)
        write_new_file_at(output_fd, "proposal.json", proposal_payload)
        if not all(
            same_open_directory(path, descriptor)
            for path, descriptor in opened_directories
        ):
            block("output path changed during evidence write")
    finally:
        for _, descriptor in reversed(opened_directories):
            os.close(descriptor)

    evidence_path = output_dir / "evidence.json"
    proposal_path = output_dir / "proposal.json"

    tracked_after = tracked_state(root)
    if tracked_after != tracked_before:
        block("tracked repository state changed during proposal generation")

    print(
        json.dumps(
            {
                "status": "PROPOSAL_GENERATED",
                "effect_ack_state": "EFFECT_ACK_CONTINUE",
                "ordinary_release": False,
                "evidence": str(evidence_path.relative_to(root)),
                "proposal": str(proposal_path.relative_to(root)),
                "evidence_sha256": evidence_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


try:
    main()
except Blocked as exc:
    print(f"BLOCK: {exc}", file=sys.stderr)
    raise SystemExit(2)
except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
    print(f"BLOCK: validation failed: {exc}", file=sys.stderr)
    raise SystemExit(2)
PY
