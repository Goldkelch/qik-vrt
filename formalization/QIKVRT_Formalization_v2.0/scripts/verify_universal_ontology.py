#!/usr/bin/env python3
"""Fail-closed verifier for the consolidated universal-ontology package."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
MATRICES = (
    ROOT / "universal_ontology/CLAIM_MATRIX.json",
    ROOT / "universal_ontology/WORLD_FORMULA_CLAIM_MATRIX.json",
)
SCOPE = ROOT / "universal_ontology/SOURCE_SCOPE.json"
AUDIT = ROOT / "QIKVRTUniversalOntology/AxiomAudit.lean"
LEAN_SOURCES = (
    ROOT / "QIKVRTUniversalOntology/Core.lean",
    ROOT / "QIKVRTUniversalOntology/AxiomAudit.lean",
    ROOT / "QIKVRTFormalization/WorldFormula/Relations.lean",
    ROOT / "QIKVRTFormalization/WorldFormula/AxiomAudit.lean",
)
STANDING = REPOSITORY_ROOT / "state/authorization/delegations/OWNER_WORLD_FORMULA_FORMALIZATION_AND_PUBLICATION_DELEGATION_V1.json"
WORK = REPOSITORY_ROOT / "state/work_units/UNIFIED_ONTOLOGY_KERNEL_PROGRAM_V2.json"
WORLD_WORK = REPOSITORY_ROOT / "state/work_units/WORLD_FORMULA_RELATION_KERNEL_V1.json"
IETF = REPOSITORY_ROOT / "external/ietf/UNIVERSAL_ONTOLOGY_FORMALIZATION_DISPOSITION_2026-08-06.json"
GLOBAL = REPOSITORY_ROOT / "GLOBAL_CLAIM_INVENTORY.json"
FORBIDDEN = re.compile(r"(?m)^\s*(?:sorry|admit|axiom)\b")


def load_object(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPOSITORY_ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def verify_source_bindings(scope: dict[str, Any]) -> None:
    source_commit = scope["source_commit"]
    if git("rev-parse", "--verify", f"{source_commit}^{{commit}}") != source_commit:
        raise ValueError("source commit does not resolve exactly")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
        cwd=REPOSITORY_ROOT, check=False,
    ).returncode != 0:
        raise ValueError("source commit is not an ancestor of execution HEAD")
    for entry in scope["sources"]:
        observed = git("rev-parse", "--verify", f"{source_commit}:{entry['path']}")
        if observed != entry["git_blob_sha1"]:
            raise ValueError(f"source blob mismatch: {entry['path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-git-source-bindings", action="store_true")
    args = parser.parse_args(argv)
    try:
        matrices = [load_object(path) for path in MATRICES]
        all_claims: list[dict[str, Any]] = []
        expected_constants: set[str] = set()
        expected_count = 0
        for matrix in matrices:
            claims = matrix.get("claims")
            if not isinstance(claims, list) or not claims:
                raise ValueError("claim matrix is empty")
            all_claims.extend(claims)
            formal = [claim for claim in claims if claim.get("kind") == "FORMAL_THEOREM"]
            expected_count += int(matrix.get("formal_theorem_count", -1))
            if len(formal) != matrix.get("formal_theorem_count"):
                raise ValueError("formal theorem count differs within a claim matrix")
            for claim in formal:
                if claim.get("terminal_disposition") not in {
                    "KERNEL_CANDIDATE", "KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"
                }:
                    raise ValueError(f"{claim.get('claim_id')}: formal disposition mismatch")
                constant = claim.get("proof_constant")
                if not isinstance(constant, str) or not constant:
                    raise ValueError(f"{claim.get('claim_id')}: missing proof constant")
                if constant in expected_constants:
                    raise ValueError(f"duplicate proof constant: {constant}")
                expected_constants.add(constant)
            for claim in claims:
                if claim.get("kind") != "FORMAL_THEOREM" and "proof_constant" in claim:
                    raise ValueError(f"{claim.get('claim_id')}: non-formal proof inflation")
        ids = [claim.get("claim_id") for claim in all_claims]
        if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("claim IDs are invalid or non-unique")
        if expected_count != 32 or len(expected_constants) != 32:
            raise ValueError("consolidated theorem inventory must contain exactly 32 constants")
        audit_constants = {
            line.strip().removeprefix("#print axioms ")
            for line in AUDIT.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }
        if audit_constants != expected_constants:
            raise ValueError(
                f"axiom-audit inventory differs: missing={sorted(expected_constants-audit_constants)} "
                f"extra={sorted(audit_constants-expected_constants)}"
            )
        for path in LEAN_SOURCES:
            if FORBIDDEN.search(path.read_text(encoding="utf-8")):
                raise ValueError(f"forbidden Lean escape hatch in {path}")

        scope = load_object(SCOPE)
        standing = load_object(STANDING)
        work = load_object(WORK)
        world_work = load_object(WORLD_WORK)
        ietf = load_object(IETF)
        global_inventory = load_object(GLOBAL)
        global_claims = global_inventory.get("claims")
        if not isinstance(global_claims, list) or not global_claims:
            raise ValueError("global claim inventory is absent or empty")
        if any(not item.get("terminal_disposition") for item in global_claims):
            raise ValueError("global inventory contains an undisposed claim")
        permissions = standing.get("autonomous_permissions", {})
        if standing.get("authorizing_owner") != "Ingolf Lohmann":
            raise ValueError("Product Owner delegation principal differs")
        if permissions.get("test_and_ci_execution") is not True:
            raise ValueError("Lean execution is not authorized")
        if standing.get("mandatory_status_separation", {}).get("scientific_consensus") != "NOT_CLAIMED":
            raise ValueError("scientific-consensus boundary weakened")
        if work.get("physical_correspondence") != "OPEN_CANDIDATE":
            raise ValueError("ontology work-unit physical boundary weakened")
        if world_work.get("claim_boundary", {}).get("physical_correspondence") != "NOT_INFERRED":
            raise ValueError("world-formula physical boundary weakened")
        if ietf.get("disposition") != "NO_PROTOCOL_CHANGE_REQUIRED":
            raise ValueError("IETF disposition differs")
        if ietf.get("wire_version_changed") is not False or ietf.get("done_predicate_changed") is not False:
            raise ValueError("IETF no-change disposition is inconsistent")
        if matrices[0].get("completion_claims") != {
            "PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False
        }:
            raise ValueError("completion boundary weakened")
        if not args.skip_git_source_bindings:
            verify_source_bindings(scope)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1

    print(
        "VERIFIED consolidated ontology/world-formula package: "
        f"claims={len(all_claims)} formal_theorems={len(expected_constants)} "
        "physical_correspondence=OPEN_CANDIDATE"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
