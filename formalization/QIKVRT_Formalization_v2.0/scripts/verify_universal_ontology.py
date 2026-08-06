#!/usr/bin/env python3
"""Fail-closed verifier for the universal-ontology finite-model package."""
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
MATRIX = ROOT / "universal_ontology/CLAIM_MATRIX.json"
SCOPE = ROOT / "universal_ontology/SOURCE_SCOPE.json"
CORE = ROOT / "QIKVRTUniversalOntology/Core.lean"
AUDIT = ROOT / "QIKVRTUniversalOntology/AxiomAudit.lean"
STANDING = REPOSITORY_ROOT / "state/authorization/delegations/OWNER_WORLD_FORMULA_FORMALIZATION_AND_PUBLICATION_DELEGATION_V1.json"
WORK = REPOSITORY_ROOT / "state/work_units/UNIFIED_ONTOLOGY_KERNEL_PROGRAM_V2.json"
IETF = REPOSITORY_ROOT / "external/ietf/UNIVERSAL_ONTOLOGY_FORMALIZATION_DISPOSITION_2026-08-06.json"
GLOBAL = REPOSITORY_ROOT / "GLOBAL_CLAIM_INVENTORY.json"

FORMAL_KINDS = {"FORMAL_THEOREM"}
NON_FORMAL_KINDS = {
    "DEFINITION", "ASSUMPTION", "CORRESPONDENCE_POSTULATE",
    "EMPIRICAL_CLAIM", "INTERPRETATION", "NORMATIVE_RULE",
}
TERMINAL = {
    "SOURCE_BOUND", "KERNEL_CANDIDATE", "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL", "EVIDENCE_REQUIRED", "OPEN_CANDIDATE",
    "INTERPRETIVE", "NORMATIVE", "REFUTED", "OUT_OF_SCOPE",
    "NO_PROTOCOL_CHANGE_REQUIRED",
}
FORBIDDEN_LEAN = re.compile(r"\b(?:sorry|admit|axiom)\b")


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
    resolved = git("rev-parse", "--verify", f"{source_commit}^{{commit}}")
    if resolved != source_commit:
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
        matrix = load_object(MATRIX)
        scope = load_object(SCOPE)
        standing = load_object(STANDING)
        work = load_object(WORK)
        ietf = load_object(IETF)
        global_inventory = load_object(GLOBAL)

        if matrix.get("schema") != "qikvrt_universal_ontology_claim_matrix_v1":
            raise ValueError("claim-matrix schema mismatch")
        claims = matrix.get("claims")
        if not isinstance(claims, list) or not claims:
            raise ValueError("claim matrix is empty")
        ids = [item.get("claim_id") for item in claims]
        if not all(isinstance(item, str) and item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("claim IDs are invalid or non-unique")
        proof_constants: set[str] = set()
        for item in claims:
            kind = item.get("kind")
            disposition = item.get("terminal_disposition")
            if kind not in FORMAL_KINDS | NON_FORMAL_KINDS:
                raise ValueError(f"{item.get('claim_id')}: unsupported claim kind")
            if disposition not in TERMINAL:
                raise ValueError(f"{item.get('claim_id')}: unsupported disposition")
            constant = item.get("proof_constant")
            if kind in FORMAL_KINDS:
                if disposition not in {"KERNEL_CANDIDATE", "KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}:
                    raise ValueError(f"{item.get('claim_id')}: formal disposition mismatch")
                if not isinstance(constant, str) or not constant:
                    raise ValueError(f"{item.get('claim_id')}: formal claim lacks constant")
                proof_constants.add(constant)
            elif constant is not None:
                raise ValueError(f"{item.get('claim_id')}: non-formal proof inflation")

        if len(proof_constants) != matrix.get("formal_theorem_count"):
            raise ValueError("formal theorem count differs")
        audit_lines = {
            line.strip().removeprefix("#print axioms ")
            for line in AUDIT.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }
        if audit_lines != proof_constants:
            raise ValueError(
                f"axiom-audit inventory differs: missing={sorted(proof_constants-audit_lines)} "
                f"extra={sorted(audit_lines-proof_constants)}"
            )
        for path in (CORE, AUDIT):
            text = path.read_text(encoding="utf-8")
            stripped = "\n".join(
                line for line in text.splitlines()
                if not line.lstrip().startswith(("--", "/-", "*", "-/"))
            )
            if FORBIDDEN_LEAN.search(stripped):
                raise ValueError(f"forbidden Lean escape hatch in {path}")

        global_claims = global_inventory.get("claims")
        if not isinstance(global_claims, list) or not global_claims:
            raise ValueError("global claim inventory is absent or empty")
        global_ids = [item.get("inventory_id") for item in global_claims]
        if len(global_ids) != len(set(global_ids)) or any(not item for item in global_ids):
            raise ValueError("global inventory IDs are not unique")
        if any(not isinstance(item.get("terminal_disposition"), str) or not item["terminal_disposition"] for item in global_claims):
            raise ValueError("global inventory contains an undisposed claim")

        if standing.get("schema") != "qikvrt-owner-delegation/1.0":
            raise ValueError("canonical Product Owner delegation schema differs")
        if standing.get("authorizing_owner") != "Ingolf Lohmann":
            raise ValueError("canonical Product Owner delegation principal differs")
        permissions = standing.get("autonomous_permissions", {})
        if permissions.get("test_and_ci_execution") is not True:
            raise ValueError("Lean execution is not authorized")
        if permissions.get("credentialed_zenodo_write") != (
            "AUTHORIZED_IN_PRINCIPLE_BUT_REQUIRES_AVAILABLE_VALID_CREDENTIALS_AND_PRE_EFFECT_GATES"
        ):
            raise ValueError("Zenodo delegation boundary differs")
        if standing.get("mandatory_status_separation", {}).get("scientific_consensus") != "NOT_CLAIMED":
            raise ValueError("scientific-consensus boundary weakened")
        if standing.get("completion_predicate", {}).get("global_completion") != (
            "NOT_PREAUTHORIZED_AS_A_CLAIM; it may be emitted only when all declared predicates are evidenced."
        ):
            raise ValueError("global-completion boundary weakened")
        if work.get("effect_state") != "EFFECT_ACK_CONTINUE":
            raise ValueError("work-unit effect state differs")
        if ietf.get("disposition") != "NO_PROTOCOL_CHANGE_REQUIRED":
            raise ValueError("IETF disposition differs")
        if ietf.get("wire_version_changed") is not False or ietf.get("done_predicate_changed") is not False:
            raise ValueError("IETF no-change disposition is internally inconsistent")
        if matrix.get("physical_correspondence") != "OPEN_CANDIDATE":
            raise ValueError("physical correspondence boundary weakened")
        if matrix.get("completion_claims") != {
            "PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False
        }:
            raise ValueError("claim matrix weakens completion boundary")
        if not args.skip_git_source_bindings:
            verify_source_bindings(scope)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1

    print(
        "VERIFIED universal ontology package: "
        f"new_claims={len(claims)} formal_theorems={len(proof_constants)} "
        f"global_dispositions={len(global_claims)} "
        "physical_correspondence=OPEN_CANDIDATE"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
