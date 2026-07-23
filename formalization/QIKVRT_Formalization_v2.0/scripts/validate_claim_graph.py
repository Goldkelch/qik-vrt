#!/usr/bin/env python3
"""Validate claim IDs, source-span bindings, epistemic edges, and proof policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from extract_tex_inventory import EXPECTED_COUNTS, FORMAL_BINDINGS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENVIRONMENTS = PROJECT_ROOT / "claims" / "TEX_ENVIRONMENTS.json"
DEFAULT_MATRIX = PROJECT_ROOT / "claims" / "APPENDIX_MATRIX.json"
DEFAULT_GRAPH = PROJECT_ROOT / "claims" / "CLAIM_GRAPH.json"

KNOWN_CATEGORIES = {
    "SOURCE",
    "DEFINITION",
    "ASSUMPTION",
    "MATHEMATICAL",
    "CONDITIONAL",
    "BACKGROUND",
    "EMPIRICAL",
    "INTERPRETIVE",
    "VALUE_PREMISE",
    "NORMATIVE",
}
PROOF_FORBIDDEN = {"EMPIRICAL", "INTERPRETIVE", "NORMATIVE"}
ALLOWED_DEPENDENCY_CATEGORIES = {
    "SOURCE": set(),
    "DEFINITION": {"SOURCE", "DEFINITION"},
    "ASSUMPTION": {"SOURCE", "DEFINITION", "BACKGROUND"},
    "MATHEMATICAL": {"SOURCE", "DEFINITION", "MATHEMATICAL", "BACKGROUND"},
    "CONDITIONAL": {
        "SOURCE",
        "DEFINITION",
        "ASSUMPTION",
        "MATHEMATICAL",
        "CONDITIONAL",
        "BACKGROUND",
    },
    "BACKGROUND": {"SOURCE", "DEFINITION", "MATHEMATICAL", "BACKGROUND"},
    "EMPIRICAL": {
        "SOURCE",
        "DEFINITION",
        "ASSUMPTION",
        "MATHEMATICAL",
        "CONDITIONAL",
        "BACKGROUND",
        "EMPIRICAL",
    },
    "INTERPRETIVE": KNOWN_CATEGORIES - {"NORMATIVE"},
    "VALUE_PREMISE": {"SOURCE", "DEFINITION", "BACKGROUND", "VALUE_PREMISE"},
    "NORMATIVE": KNOWN_CATEGORIES,
}
EXPECTED_FORMAL_ENVIRONMENTS = {
    "SET-001": ["ENV-THM-001"],
    "MAP-001": ["ENV-THM-005"],
    "QUA-003A": ["ENV-THM-008"],
    "SET-003": ["ENV-THM-009"],
    "MAP-003": ["ENV-THM-010"],
    "GAT-004": ["ENV-THM-012"],
    "GAT-005": ["ENV-THM-013"],
    "GAT-006": ["ENV-THM-013"],
    "RET-011": ["ENV-THM-015", "ENV-THM-019", "ENV-THM-020"],
    "GAT-002": ["ENV-THM-016"],
    "DIM-006A": ["ENV-THM-017"],
    "DIM-007A": ["ENV-THM-018"],
}
EXPECTED_FORMAL_SPANS = {
    "SET-001": ["SPAN-TEX-0441-0457"],
    "MAP-001": ["SPAN-TEX-0601-0607"],
    "QUA-003A": ["SPAN-TEX-0731-0736"],
    "SET-003": ["SPAN-TEX-0767-0773"],
    "MAP-003": ["SPAN-TEX-0780-0798"],
    "GAT-004": ["SPAN-TEX-0979-0991"],
    "GAT-005": ["SPAN-TEX-1010-1024"],
    "GAT-006": ["SPAN-TEX-1010-1024"],
    "RET-011": [
        "SPAN-TEX-1101-1107",
        "SPAN-TEX-2672-2681",
        "SPAN-TEX-2703-2710",
    ],
    "GAT-002": ["SPAN-TEX-1233-1242"],
    "DIM-006A": ["SPAN-TEX-1483-1488"],
    "DIM-007A": ["SPAN-TEX-1560-1564"],
}
SUBCLAIM_PARENTS = {
    "QUA-003A": "QUA-003",
    "DIM-006A": "DIM-006",
    "DIM-007A": "DIM-007",
}


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _valid_span(span: Any) -> bool:
    if not isinstance(span, dict):
        return False
    return (
        isinstance(span.get("id"), str)
        and isinstance(span.get("startLine"), int)
        and isinstance(span.get("endLine"), int)
        and 1 <= span["startLine"] <= span["endLine"]
        and isinstance(span.get("sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", span["sha256"]) is not None
        and span.get("hashMode") == "raw-bytes-inclusive-lines-v1"
        and isinstance(span.get("physicalPdfPage"), int)
        and 1 <= span["physicalPdfPage"] <= 62
        and span.get("pageMappingMethod") == "synctex-forward-clean-rebuild-v1"
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detect_cycles(nodes_by_id: dict[str, dict[str, Any]]) -> list[list[str]]:
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node_id: str) -> None:
        current = state.get(node_id, 0)
        if current == 2:
            return
        if current == 1:
            start = stack.index(node_id)
            cycles.append(stack[start:] + [node_id])
            return
        state[node_id] = 1
        stack.append(node_id)
        for dependency in nodes_by_id[node_id].get("dependencies", []):
            if dependency in nodes_by_id:
                visit(dependency)
        stack.pop()
        state[node_id] = 2

    for node_id in nodes_by_id:
        if state.get(node_id, 0) == 0:
            visit(node_id)
    return cycles


def validate_claim_graph(
    graph: dict[str, Any],
    environments_data: dict[str, Any],
    matrix_data: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    environments = environments_data.get("environments", [])
    proof_blocks = environments_data.get("proofBlocks", [])
    rows = matrix_data.get("rows", [])
    nodes = graph.get("nodes", [])
    if not all(isinstance(item, list) for item in (environments, proof_blocks, rows, nodes)):
        return ["environments, proofBlocks, rows, and nodes must all be arrays"]
    binding_scopes = graph.get("policy", {}).get("bindingScopes", {})
    if set(binding_scopes) != {"FULL_ENVIRONMENT", "SOURCE_SUBCLAIM"}:
        errors.append("claim graph policy must declare both binding scopes")

    environment_ids = [item.get("id") for item in environments if isinstance(item, dict)]
    proof_ids = [item.get("id") for item in proof_blocks if isinstance(item, dict)]
    matrix_ids = [item.get("id") for item in rows if isinstance(item, dict)]
    node_ids = [item.get("id") for item in nodes if isinstance(item, dict)]
    for label, ids in (
        ("environment", environment_ids),
        ("proof", proof_ids),
        ("matrix", matrix_ids),
        ("claim", node_ids),
    ):
        duplicates = _duplicates([item for item in ids if isinstance(item, str)])
        if duplicates:
            errors.append(f"duplicate {label} IDs: {duplicates}")

    environments_by_id = {
        item["id"]: item
        for item in environments
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    proofs_by_id = {
        item["id"]: item
        for item in proof_blocks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    nodes_by_id = {
        item["id"]: item
        for item in nodes
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    actual_counts = {
        "definitions": sum(item.get("group") == "definition" for item in environments),
        "theoremLike": sum(item.get("group") == "theoremLike" for item in environments),
        "formal": sum(item.get("formal") is True for item in environments),
        "remarks": sum(item.get("group") == "remark" for item in environments),
        "proofBlocks": len(proof_blocks),
        "matrixRows": len(rows),
    }
    for key, expected in EXPECTED_COUNTS.items():
        if actual_counts[key] != expected:
            errors.append(f"{key}: expected {expected}, got {actual_counts[key]}")

    all_span_ids: set[str] = set()
    for owner_type, owners in (
        ("environment", environments),
        ("proof", proof_blocks),
        ("matrix", rows),
    ):
        for owner in owners:
            span = owner.get("sourceSpan") if isinstance(owner, dict) else None
            if not _valid_span(span):
                errors.append(f"{owner_type} {owner.get('id')} has invalid raw-byte sourceSpan")
                continue
            if span["id"] in all_span_ids:
                errors.append(f"duplicate sourceSpan ID: {span['id']}")
            all_span_ids.add(span["id"])

    reverse_environment_claims: defaultdict[str, set[str]] = defaultdict(set)
    for environment in environments:
        environment_id = environment.get("id")
        claim_ids = environment.get("claimIds", [])
        if environment.get("formal") is True and not claim_ids:
            errors.append(f"formal environment {environment_id} has no stable claim mapping")
        for claim_id in claim_ids:
            if claim_id not in nodes_by_id:
                errors.append(f"environment {environment_id} references unknown claim {claim_id}")
            reverse_environment_claims[environment_id].add(claim_id)
        for proof_id in environment.get("proofBlockIds", []):
            if proof_id not in proofs_by_id:
                errors.append(f"environment {environment_id} references unknown proof {proof_id}")
            elif proofs_by_id[proof_id].get("associatedEnvironmentId") != environment_id:
                errors.append(f"proof {proof_id} reverse association is inconsistent")

    proof_associations: Counter[str] = Counter()
    for proof in proof_blocks:
        associated = proof.get("associatedEnvironmentId")
        if associated not in environments_by_id:
            errors.append(f"proof {proof.get('id')} references unknown environment {associated}")
        else:
            proof_associations[associated] += 1
            if environments_by_id[associated].get("group") != "theoremLike":
                errors.append(f"proof {proof.get('id')} is not attached to a theorem-like environment")
    if any(count > 1 for count in proof_associations.values()):
        errors.append("more than one proof block is attached to a theorem-like environment")

    for row in rows:
        category = row.get("epistemicCategory")
        if category not in KNOWN_CATEGORIES:
            errors.append(f"matrix row {row.get('id')} has unknown category {category}")
        if category in PROOF_FORBIDDEN and row.get("machineProofBindingAllowed") is not False:
            errors.append(f"matrix row {row.get('id')} permits a forbidden proof binding")
        for claim_id in row.get("relatedClaimIds", []):
            if claim_id not in nodes_by_id:
                errors.append(f"matrix row {row.get('id')} references unknown claim {claim_id}")

    graph_environment_claims: defaultdict[str, set[str]] = defaultdict(set)
    for node_id, node in nodes_by_id.items():
        category = node.get("epistemicCategory")
        if category not in KNOWN_CATEGORIES:
            errors.append(f"claim {node_id} has unknown category {category}")
        dependencies = node.get("dependencies", [])
        if not isinstance(dependencies, list):
            errors.append(f"claim {node_id}.dependencies must be an array")
            dependencies = []
        for dependency in dependencies:
            if dependency not in nodes_by_id:
                errors.append(f"claim {node_id} references unknown dependency {dependency}")
                continue
            dependency_category = nodes_by_id[dependency].get("epistemicCategory")
            if dependency_category not in ALLOWED_DEPENDENCY_CATEGORIES.get(category, set()):
                errors.append(
                    f"forbidden dependency/promotion: {node_id} ({category}) -> "
                    f"{dependency} ({dependency_category})"
                )

        for environment_id in node.get("environmentIds", []):
            if environment_id not in environments_by_id:
                errors.append(f"claim {node_id} references unknown environment {environment_id}")
            else:
                graph_environment_claims[environment_id].add(node_id)
        for span_id in node.get("sourceSpanIds", []):
            if span_id not in all_span_ids:
                errors.append(f"claim {node_id} references unknown sourceSpan {span_id}")
        for proof_id in node.get("proofBlockIds", []):
            if proof_id not in proofs_by_id:
                errors.append(f"claim {node_id} references unknown proof block {proof_id}")

        binding = node.get("formalBinding")
        status = node.get("formalizationStatus")
        if category in PROOF_FORBIDDEN and binding is not None:
            errors.append(f"proof binding forbidden for {category} claim {node_id}")
        if status == "KERNEL_CHECKED" and binding is None:
            errors.append(f"claim {node_id} is KERNEL_CHECKED without a formal binding")
        if binding is not None:
            if status != "KERNEL_CHECKED":
                errors.append(f"claim {node_id} has a formal binding but is not KERNEL_CHECKED")
            if binding.get("bindingStrength") != "STRONG":
                errors.append(f"claim {node_id} binding is not STRONG")
            if binding.get("claimScope") not in {"FULL_ENVIRONMENT", "SOURCE_SUBCLAIM"}:
                errors.append(f"claim {node_id} has invalid claimScope")
            if not node.get("sourceSpanIds"):
                errors.append(f"claim {node_id} binding has no normative source span")
            source_path_raw = binding.get("sourcePath")
            registry_path_raw = binding.get("registrySourcePath")
            for role, raw_path, digest_key in (
                ("Lean source", source_path_raw, "leanSourceSha256"),
                ("registry source", registry_path_raw, "registrySourceSha256"),
            ):
                if not isinstance(raw_path, str) or not raw_path:
                    errors.append(f"claim {node_id} has no {role} path")
                    continue
                candidate = (PROJECT_ROOT / raw_path).resolve()
                try:
                    candidate.relative_to(PROJECT_ROOT.resolve())
                except ValueError:
                    errors.append(f"claim {node_id} {role} escapes project root")
                    continue
                if not candidate.is_file():
                    errors.append(f"claim {node_id} missing {role}: {raw_path}")
                    continue
                expected_digest = binding.get(digest_key)
                actual_digest = _sha256_file(candidate)
                if expected_digest != actual_digest:
                    errors.append(
                        f"claim {node_id} stale {role} fingerprint: expected "
                        f"{expected_digest}, got {actual_digest}"
                    )

            if isinstance(source_path_raw, str):
                source_path = PROJECT_ROOT / source_path_raw
                if source_path.is_file():
                    source_text = source_path.read_text(encoding="utf-8")
                    statement_name = str(binding.get("statementConstant", "")).rsplit(".", 1)[-1]
                    proof_name = str(binding.get("proofConstant", "")).rsplit(".", 1)[-1]
                    if re.search(rf"(?m)^\s*def\s+{re.escape(statement_name)}\b", source_text) is None:
                        errors.append(f"claim {node_id} statement declaration is absent from bound module")
                    if re.search(rf"(?m)^\s*theorem\s+{re.escape(proof_name)}\b", source_text) is None:
                        errors.append(f"claim {node_id} proof declaration is absent from bound module")
            if isinstance(registry_path_raw, str):
                registry_path = PROJECT_ROOT / registry_path_raw
                if registry_path.is_file():
                    registry_text = registry_path.read_text(encoding="utf-8")
                    registry_name = str(binding.get("registryConstant", "")).rsplit(".", 1)[-1]
                    if re.search(rf"(?m)^\s*def\s+{re.escape(registry_name)}\b", registry_text) is None:
                        errors.append(f"claim {node_id} indexed registry constructor is absent")

    for environment in environments:
        if environment.get("formal") is not True:
            continue
        environment_id = environment["id"]
        if reverse_environment_claims[environment_id] != graph_environment_claims[environment_id]:
            errors.append(
                f"formal environment {environment_id} claim mapping differs between inventory and graph"
            )

    for cycle in _detect_cycles(nodes_by_id):
        errors.append(f"claim dependency cycle: {' -> '.join(cycle)}")

    for claim_id, expected_binding in FORMAL_BINDINGS.items():
        node = nodes_by_id.get(claim_id)
        if node is None:
            errors.append(f"missing formally bound claim {claim_id}")
            continue
        binding = node.get("formalBinding") or {}
        for key, expected_value in expected_binding.items():
            if binding.get(key) != expected_value:
                errors.append(
                    f"formal {claim_id} binding {key}: expected {expected_value}, "
                    f"got {binding.get(key)}"
                )
        if node.get("environmentIds") != EXPECTED_FORMAL_ENVIRONMENTS[claim_id]:
            errors.append(f"formal {claim_id} has wrong environment binding")
        if node.get("sourceSpanIds") != EXPECTED_FORMAL_SPANS[claim_id]:
            errors.append(f"formal {claim_id} has wrong source-span binding")

    bound_claim_ids = {
        node_id for node_id, node in nodes_by_id.items()
        if node.get("formalBinding") is not None
    }
    if bound_claim_ids != set(FORMAL_BINDINGS):
        errors.append(
            "formal binding set mismatch: expected "
            f"{sorted(FORMAL_BINDINGS)}, got {sorted(bound_claim_ids)}"
        )
    for subclaim_id, parent_id in SUBCLAIM_PARENTS.items():
        subclaim = nodes_by_id.get(subclaim_id, {})
        parent = nodes_by_id.get(parent_id, {})
        if (subclaim.get("formalBinding") or {}).get("claimScope") != "SOURCE_SUBCLAIM":
            errors.append(f"{subclaim_id} is not marked as a source subclaim")
        if parent.get("formalizationStatus") != "PENDING" or parent.get("formalBinding") is not None:
            errors.append(f"parent claim {parent_id} must remain pending without a binding")

    if len(nodes_by_id) != len(nodes):
        errors.append("some graph nodes lack a unique string ID")
    return errors


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    args = parser.parse_args(argv)
    try:
        errors = validate_claim_graph(
            _load_json(args.graph),
            _load_json(args.environments),
            _load_json(args.matrix),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "PASS claim graph: 40 formal environments mapped, 34 matrix rows classified, "
        "12 strong bindings, no unknown IDs/cycles/forbidden promotions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
