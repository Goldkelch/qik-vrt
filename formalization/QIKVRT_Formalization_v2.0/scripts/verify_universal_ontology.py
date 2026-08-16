#!/usr/bin/env python3
"""Fail-closed verifier for the consolidated universal-ontology package."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
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
SHA1 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_REPOSITORY = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
MIRROR_REPOSITORY = "ingolf-lohmann/qik-vrt"
AUTHORITY_REMOTE = "https://github.com/Goldkelch/qik-vrt.git"
EXPECTED_EXECUTION_POLICY = {
    AUTHORITY_REPOSITORY: {"source_commit_must_be_ancestor": True},
    MIRROR_REPOSITORY: {"source_commit_must_be_ancestor": False},
}


def load_object(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def git(*args: str, repository_root: pathlib.Path = REPOSITORY_ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repository_root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def git_succeeds(*args: str, repository_root: pathlib.Path) -> bool:
    return subprocess.run(
        ["git", *args], cwd=repository_root, text=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode == 0


def execution_repository(
    repository_root: pathlib.Path,
    environment: Mapping[str, str],
) -> str:
    remote = git("remote", "get-url", "origin", repository_root=repository_root)
    match = GITHUB_REPOSITORY.fullmatch(remote)
    if match is None:
        raise ValueError("origin is not an exact GitHub repository remote")
    remote_repository = match.group("repository")
    event_repository = environment.get("GITHUB_REPOSITORY")
    if event_repository is not None and event_repository != remote_repository:
        raise ValueError("GITHUB_REPOSITORY and origin repository differ")
    return event_repository or remote_repository


def fetch_exact_source_commit(
    destination: pathlib.Path,
    canonical_remote: str,
    source_commit: str,
) -> None:
    completed = subprocess.run(
        [
            "git", "-c", "fetch.fsckObjects=true", "fetch",
            "--no-tags", "--depth=1", "--no-write-fetch-head",
            canonical_remote, source_commit,
        ],
        cwd=destination,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if completed.returncode != 0:
        raise ValueError(
            "exact source commit fetch failed: " + completed.stderr.strip()
        )


def verify_source_object_store(
    scope: dict[str, Any],
    source_store: pathlib.Path,
) -> None:
    source_commit = scope["source_commit"]
    if git(
        "rev-parse", "--verify", f"{source_commit}^{{commit}}",
        repository_root=source_store,
    ) != source_commit:
        raise ValueError("source commit does not resolve exactly")
    observed_tree = git(
        "rev-parse", "--verify", f"{source_commit}^{{tree}}",
        repository_root=source_store,
    )
    if observed_tree != scope["source_tree"]:
        raise ValueError("source tree mismatch")
    for entry in scope["sources"]:
        observed = git(
            "rev-parse", "--verify", f"{source_commit}:{entry['path']}",
            repository_root=source_store,
        )
        if observed != entry["git_blob_sha1"]:
            raise ValueError(f"source blob mismatch: {entry['path']}")
        if git("cat-file", "-t", observed, repository_root=source_store) != "blob":
            raise ValueError(f"source path is not a blob: {entry['path']}")


def verify_source_bindings(
    scope: dict[str, Any],
    *,
    repository_root: pathlib.Path = REPOSITORY_ROOT,
    environment: Mapping[str, str] | None = None,
) -> None:
    if scope.get("schema") != "qikvrt_universal_ontology_source_scope_v2":
        raise ValueError("source-scope schema mismatch")
    source_commit = scope.get("source_commit")
    source_tree = scope.get("source_tree")
    if not isinstance(source_commit, str) or SHA1.fullmatch(source_commit) is None:
        raise ValueError("source commit is not an exact SHA-1")
    if not isinstance(source_tree, str) or SHA1.fullmatch(source_tree) is None:
        raise ValueError("source tree is not an exact SHA-1")

    source_repository = scope.get("repository")
    resolution = scope.get("source_resolution")
    if not isinstance(source_repository, str) or not isinstance(resolution, dict):
        raise ValueError("source-resolution policy is absent")
    if source_repository != AUTHORITY_REPOSITORY:
        raise ValueError("source repository differs from the fixed Authority")
    canonical_remote = resolution.get("canonical_remote")
    if canonical_remote != AUTHORITY_REMOTE:
        raise ValueError("canonical source remote differs from the fixed Authority")
    if resolution.get("fetch_policy") != "EXACT_COMMIT_IF_MISSING":
        raise ValueError("source fetch policy differs")
    permitted = resolution.get("permitted_execution_repositories")
    if permitted != EXPECTED_EXECUTION_POLICY or any(
        not isinstance(policy, dict)
        or policy.get("source_commit_must_be_ancestor") is not
        EXPECTED_EXECUTION_POLICY[repository]["source_commit_must_be_ancestor"]
        for repository, policy in permitted.items()
    ):
        raise ValueError("execution repository policy differs from the fixed pair")

    observed_repository = execution_repository(
        repository_root,
        os.environ if environment is None else environment,
    )
    repository_policy = permitted.get(observed_repository)
    if not isinstance(repository_policy, dict):
        raise ValueError(f"execution repository is not permitted: {observed_repository}")
    require_ancestor = repository_policy.get("source_commit_must_be_ancestor")
    if not isinstance(require_ancestor, bool):
        raise ValueError("source ancestry policy is absent")

    source_is_local = git_succeeds(
        "rev-parse", "--verify", "--quiet", f"{source_commit}^{{commit}}",
        repository_root=repository_root,
    )
    if require_ancestor:
        if not source_is_local or not git_succeeds(
            "merge-base", "--is-ancestor", source_commit, "HEAD",
            repository_root=repository_root,
        ):
            raise ValueError("source commit is not an ancestor of execution HEAD")

    if source_is_local:
        verify_source_object_store(scope, repository_root)
        return

    with tempfile.TemporaryDirectory(prefix="qikvrt-source-provenance-") as temporary:
        source_store = pathlib.Path(temporary) / "source.git"
        git("init", "--bare", str(source_store), repository_root=repository_root)
        fetch_exact_source_commit(source_store, canonical_remote, source_commit)
        verify_source_object_store(scope, source_store)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
