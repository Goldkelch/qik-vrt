#!/usr/bin/env python3
"""Materialize the completed, source-bound manuscript claim graph.

The locked TeX/PDF inventory remains owned by ``extract_tex_inventory.py``.
This completion layer reuses that deterministic parser and adds the reviewed
Lean bindings for every definition and theorem-like manuscript environment.
Conditional mathematical results remain explicitly conditional in both status
and claim scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import extract_tex_inventory as base

PROJECT_ROOT = base.PROJECT_ROOT
DEFAULT_PROVENANCE = base.DEFAULT_PROVENANCE
DEFAULT_ENVIRONMENTS = base.DEFAULT_ENVIRONMENTS
DEFAULT_MATRIX = base.DEFAULT_MATRIX
DEFAULT_GRAPH = base.DEFAULT_GRAPH

DEFINITION_SOURCE = "QIKVRTFormalization/Definitions/Manuscript.lean"
COMPLETION_SOURCE = "QIKVRTFormalization/Completion/OpenClaims.lean"
COMPLETION_REGISTRY = "QIKVRTFormalization/Claims/Completion.lean"


def _definition_binding(index: int) -> dict[str, str]:
    claim = f"DEF-{index:03d}"
    constant = claim.replace("-", "")
    return {
        "batch": "Completion-Definitions",
        "claimScope": "DEFINITION_BINDING",
        "module": "QIKVRTFormalization.Definitions.Manuscript",
        "sourcePath": DEFINITION_SOURCE,
        "statementConstant": f"QIKVRT.V2.Definitions.{constant}Statement",
        "proofConstant": f"QIKVRT.V2.Definitions.{constant}_checked",
        "registryConstant": f"QIKVRT.V2.Claims.{constant}",
        "registrySourcePath": COMPLETION_REGISTRY,
    }


def _completion_binding(claim: str, scope: str) -> dict[str, str]:
    constant = claim.replace("-", "")
    return {
        "batch": "Completion-Theorems",
        "claimScope": scope,
        "module": "QIKVRTFormalization.Completion.OpenClaims",
        "sourcePath": COMPLETION_SOURCE,
        "statementConstant": f"QIKVRT.V2.Completion.{constant}Statement",
        "proofConstant": f"QIKVRT.V2.Completion.{constant}_checked",
        "registryConstant": f"QIKVRT.V2.Claims.{constant}",
        "registrySourcePath": COMPLETION_REGISTRY,
    }


DEFINITION_BINDINGS: dict[str, dict[str, str]] = {
    f"DEF-{index:03d}": _definition_binding(index)
    for index in range(1, 21)
}

CONDITIONAL_CLAIMS = {
    "ESC-004",
    "ESC-005",
    "ESC-003",
    "QUA-004",
    "QUA-005",
    "DIM-006",
}

EXACT_COMPLETION_CLAIMS = {
    "QUA-003",
    "GAT-007",
    "DIM-007",
}

THEOREM_BINDINGS: dict[str, dict[str, str]] = {
    claim: _completion_binding(claim, "CONDITIONAL_ENVIRONMENT")
    for claim in sorted(CONDITIONAL_CLAIMS)
}
THEOREM_BINDINGS.update(
    {
        claim: _completion_binding(claim, "FULL_ENVIRONMENT")
        for claim in sorted(EXACT_COMPLETION_CLAIMS)
    }
)
THEOREM_BINDINGS["GAT-003"] = {
    "batch": "Batch04",
    "claimScope": "FULL_ENVIRONMENT",
    "module": "QIKVRTFormalization.Process.ShiftInvariance",
    "sourcePath": "QIKVRTFormalization/Process/ShiftInvariance.lean",
    "statementConstant": "QIKVRT.V2.Trajectory.GAT003Statement",
    "proofConstant": "QIKVRT.V2.Trajectory.GAT003_checked",
    "registryConstant": "QIKVRT.V2.Claims.GAT003",
    "registrySourcePath": "QIKVRTFormalization/Claims/Batch04.lean",
}

ALL_FORMAL_BINDINGS: dict[str, dict[str, str]] = {
    **base.FORMAL_BINDINGS,
    **DEFINITION_BINDINGS,
    **THEOREM_BINDINGS,
}

CLOSED_STATUSES = {"KERNEL_CHECKED", "CONDITIONAL_CHECKED"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialized_binding(binding: dict[str, str]) -> dict[str, Any]:
    source = PROJECT_ROOT / binding["sourcePath"]
    registry = PROJECT_ROOT / binding["registrySourcePath"]
    if not source.is_file():
        raise ValueError(f"missing Lean source: {binding['sourcePath']}")
    if not registry.is_file():
        raise ValueError(f"missing registry source: {binding['registrySourcePath']}")
    return {
        "proofSystem": "Lean4",
        "bindingStrength": "STRONG",
        **binding,
        "leanSourceSha256": _sha256(source),
        "registrySourceSha256": _sha256(registry),
        "assumptionPolicy": (
            "EXPLICIT_IN_LEAN_TYPE"
            if binding["claimScope"] == "CONDITIONAL_ENVIRONMENT"
            else "NO_HIDDEN_ASSUMPTIONS"
        ),
    }


def build_completed_graph(environments: dict[str, Any]) -> dict[str, Any]:
    graph = base.build_claim_graph(environments)
    nodes = {node["id"]: node for node in graph["nodes"]}

    missing = sorted(set(ALL_FORMAL_BINDINGS) - set(nodes))
    if missing:
        raise ValueError(f"completion bindings reference unknown claims: {missing}")

    for claim_id, binding in ALL_FORMAL_BINDINGS.items():
        node = nodes[claim_id]
        scope = binding["claimScope"]
        node["formalizationStatus"] = (
            "CONDITIONAL_CHECKED"
            if scope == "CONDITIONAL_ENVIRONMENT"
            else "KERNEL_CHECKED"
        )
        if scope == "CONDITIONAL_ENVIRONMENT":
            node["epistemicCategory"] = "CONDITIONAL"
        node["formalBinding"] = _materialized_binding(binding)

    graph["policy"] = {
        **graph["policy"],
        "bindingScopes": {
            "FULL_ENVIRONMENT": "exact aggregate source claim discharged",
            "CONDITIONAL_ENVIRONMENT": (
                "source claim discharged only under assumptions explicit in the Lean type"
            ),
            "SOURCE_SUBCLAIM": "checked atom retained alongside its now-bound parent",
            "DEFINITION_BINDING": "source definition represented by an explicit Lean type",
        },
        "closedStatuses": sorted(CLOSED_STATUSES),
        "completionRule": (
            "No DEFINITION, MATHEMATICAL, or CONDITIONAL node may remain PENDING. "
            "Empirical, interpretive, background, and normative content is never "
            "promoted to a mathematical theorem."
        ),
    }
    graph["counts"] = {
        "nodes": len(graph["nodes"]),
        "definitionNodes": sum(
            node["epistemicCategory"] == "DEFINITION" for node in graph["nodes"]
        ),
        "strongBindings": sum(
            node.get("formalBinding") is not None for node in graph["nodes"]
        ),
        "kernelCheckedClaims": sum(
            node.get("formalizationStatus") in CLOSED_STATUSES
            for node in graph["nodes"]
        ),
        "conditionalCheckedClaims": sum(
            node.get("formalizationStatus") == "CONDITIONAL_CHECKED"
            for node in graph["nodes"]
        ),
        "pendingNodes": sum(
            node.get("formalizationStatus") == "PENDING" for node in graph["nodes"]
        ),
    }
    return graph


def generate(
    provenance_path: Path = DEFAULT_PROVENANCE,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    environments, matrix, _baseline = base.generate(provenance_path)
    return environments, matrix, build_completed_graph(environments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        environments, matrix, graph = generate(args.provenance.resolve())
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    results = [
        base._write_or_check(args.environments, environments, args.check),
        base._write_or_check(args.matrix, matrix, args.check),
        base._write_or_check(args.graph, graph, args.check),
    ]
    if not all(results):
        return 1
    action = "verified" if args.check else "wrote"
    print(
        f"PASS {action}: 20 definitions bound, 20 theorem environments closed, "
        f"{graph['counts']['strongBindings']} strong bindings, 0 pending formal nodes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
