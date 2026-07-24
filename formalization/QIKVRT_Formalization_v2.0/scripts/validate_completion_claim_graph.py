#!/usr/bin/env python3
"""Validate the completed manuscript claim graph and its Lean bindings."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import materialize_completion as completion
import validate_claim_graph as legacy

ROOT = completion.PROJECT_ROOT
ENVIRONMENTS = completion.DEFAULT_ENVIRONMENTS
MATRIX = completion.DEFAULT_MATRIX
GRAPH = completion.DEFAULT_GRAPH
CLOSED = completion.CLOSED_STATUSES
VALID_SCOPES = {
    "FULL_ENVIRONMENT",
    "CONDITIONAL_ENVIRONMENT",
    "SOURCE_SUBCLAIM",
    "DEFINITION_BINDING",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _declaration_exists(path: Path, fully_qualified: str, kinds: str) -> bool:
    name = fully_qualified.rsplit(".", 1)[-1]
    text = path.read_text(encoding="utf-8")
    return re.search(rf"(?m)^\s*(?:{kinds})\s+{re.escape(name)}\b", text) is not None


def validate(
    graph: dict[str, Any],
    inventory: dict[str, Any],
    matrix: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    environments = inventory.get("environments", [])
    proofs = inventory.get("proofBlocks", [])
    rows = matrix.get("rows", [])
    nodes = graph.get("nodes", [])
    if not all(isinstance(value, list) for value in (environments, proofs, rows, nodes)):
        return ["inventory, matrix, and graph arrays are malformed"]

    environment_ids = [item.get("id") for item in environments if isinstance(item, dict)]
    node_ids = [item.get("id") for item in nodes if isinstance(item, dict)]
    for label, values in (("environment", environment_ids), ("claim", node_ids)):
        duplicates = _duplicates([value for value in values if isinstance(value, str)])
        if duplicates:
            errors.append(f"duplicate {label} IDs: {duplicates}")

    expected_counts = completion.base.EXPECTED_COUNTS
    actual_counts = {
        "definitions": sum(item.get("group") == "definition" for item in environments),
        "theoremLike": sum(item.get("group") == "theoremLike" for item in environments),
        "formal": sum(item.get("formal") is True for item in environments),
        "remarks": sum(item.get("group") == "remark" for item in environments),
        "proofBlocks": len(proofs),
        "matrixRows": len(rows),
    }
    for key, expected in expected_counts.items():
        if actual_counts[key] != expected:
            errors.append(f"{key}: expected {expected}, got {actual_counts[key]}")

    nodes_by_id = {
        item["id"]: item
        for item in nodes
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    environments_by_id = {
        item["id"]: item
        for item in environments
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    all_span_ids: set[str] = set()
    for owner in [*environments, *proofs, *rows]:
        span = owner.get("sourceSpan") if isinstance(owner, dict) else None
        if not legacy._valid_span(span):
            errors.append(f"{owner.get('id')} has an invalid source span")
            continue
        all_span_ids.add(span["id"])

    reverse: defaultdict[str, set[str]] = defaultdict(set)
    for environment in environments:
        environment_id = environment.get("id")
        claim_ids = environment.get("claimIds", [])
        if environment.get("formal") is True and not claim_ids:
            errors.append(f"formal environment {environment_id} has no claim IDs")
        for claim_id in claim_ids:
            if claim_id not in nodes_by_id:
                errors.append(f"environment {environment_id} references unknown {claim_id}")
            reverse[environment_id].add(claim_id)

    graph_reverse: defaultdict[str, set[str]] = defaultdict(set)
    bound: set[str] = set()
    for claim_id, node in nodes_by_id.items():
        category = node.get("epistemicCategory")
        if category not in legacy.KNOWN_CATEGORIES:
            errors.append(f"claim {claim_id} has unknown category {category}")
        dependencies = node.get("dependencies", [])
        if not isinstance(dependencies, list):
            errors.append(f"claim {claim_id}.dependencies is not an array")
            dependencies = []
        for dependency in dependencies:
            dependency_node = nodes_by_id.get(dependency)
            if dependency_node is None:
                errors.append(f"claim {claim_id} references unknown dependency {dependency}")
                continue
            allowed = legacy.ALLOWED_DEPENDENCY_CATEGORIES.get(category, set())
            if dependency_node.get("epistemicCategory") not in allowed:
                errors.append(f"forbidden dependency/promotion: {claim_id} -> {dependency}")

        for environment_id in node.get("environmentIds", []):
            if environment_id not in environments_by_id:
                errors.append(f"claim {claim_id} references unknown environment {environment_id}")
            graph_reverse[environment_id].add(claim_id)
        for span_id in node.get("sourceSpanIds", []):
            if span_id not in all_span_ids:
                errors.append(f"claim {claim_id} references unknown source span {span_id}")

        binding = node.get("formalBinding")
        status = node.get("formalizationStatus")
        if category in legacy.PROOF_FORBIDDEN and binding is not None:
            errors.append(f"proof binding forbidden for {category} claim {claim_id}")
        if binding is None:
            if category in {"DEFINITION", "MATHEMATICAL", "CONDITIONAL"}:
                errors.append(f"formal claim {claim_id} remains unbound")
            continue

        bound.add(claim_id)
        expected = completion.ALL_FORMAL_BINDINGS.get(claim_id)
        if expected is None:
            errors.append(f"unexpected formal binding on {claim_id}")
            continue
        for key, value in expected.items():
            if binding.get(key) != value:
                errors.append(f"{claim_id} binding {key}: expected {value}, got {binding.get(key)}")
        if binding.get("proofSystem") != "Lean4" or binding.get("bindingStrength") != "STRONG":
            errors.append(f"{claim_id} binding is not a strong Lean4 binding")
        scope = binding.get("claimScope")
        if scope not in VALID_SCOPES:
            errors.append(f"{claim_id} has invalid claim scope {scope}")
        expected_status = "CONDITIONAL_CHECKED" if scope == "CONDITIONAL_ENVIRONMENT" else "KERNEL_CHECKED"
        if status != expected_status:
            errors.append(f"{claim_id} status must be {expected_status}")
        if not node.get("sourceSpanIds"):
            errors.append(f"{claim_id} binding has no source span")

        source = ROOT / str(binding.get("sourcePath", ""))
        registry = ROOT / str(binding.get("registrySourcePath", ""))
        if not source.is_file():
            errors.append(f"{claim_id} missing Lean source")
        else:
            if binding.get("leanSourceSha256") != _sha256(source):
                errors.append(f"{claim_id} stale Lean source fingerprint")
            if not _declaration_exists(source, str(binding.get("statementConstant", "")), "def"):
                errors.append(f"{claim_id} statement declaration is absent")
            if not _declaration_exists(source, str(binding.get("proofConstant", "")), "theorem"):
                errors.append(f"{claim_id} proof declaration is absent")
        if not registry.is_file():
            errors.append(f"{claim_id} missing registry source")
        else:
            if binding.get("registrySourceSha256") != _sha256(registry):
                errors.append(f"{claim_id} stale registry source fingerprint")
            if not _declaration_exists(registry, str(binding.get("registryConstant", "")), "def"):
                errors.append(f"{claim_id} indexed registry constructor is absent")

    for environment in environments:
        if environment.get("formal") is not True:
            continue
        environment_id = environment["id"]
        if reverse[environment_id] != graph_reverse[environment_id]:
            errors.append(f"formal environment {environment_id} mapping differs")
        for claim_id in environment.get("claimIds", []):
            if nodes_by_id.get(claim_id, {}).get("formalizationStatus") not in CLOSED:
                errors.append(f"formal environment {environment_id} is not closed by {claim_id}")

    for cycle in legacy._detect_cycles(nodes_by_id):
        errors.append(f"claim dependency cycle: {' -> '.join(cycle)}")

    expected_bound = set(completion.ALL_FORMAL_BINDINGS)
    if bound != expected_bound:
        errors.append(f"formal binding set mismatch: expected {sorted(expected_bound)}, got {sorted(bound)}")
    if len(bound) != 42:
        errors.append(f"expected 42 strong bindings, got {len(bound)}")
    if graph.get("counts", {}).get("pendingNodes") != 0:
        errors.append("graph count reports pending nodes")
    if any(
        node.get("formalizationStatus") == "PENDING"
        and node.get("epistemicCategory") in {"DEFINITION", "MATHEMATICAL", "CONDITIONAL"}
        for node in nodes
    ):
        errors.append("at least one formal node remains PENDING")
    return errors


def main() -> int:
    try:
        errors = validate(_load(GRAPH), _load(ENVIRONMENTS), _load(MATRIX))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "PASS completed claim graph: 40 formal environments closed, "
        "42 strong bindings, 0 pending formal nodes, no forbidden promotions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
