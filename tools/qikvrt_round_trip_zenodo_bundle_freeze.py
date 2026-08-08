#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed verifier for the Round Trip Zenodo v2 bundle freeze.

This is a bounded adapter over the existing QIK-VRT publication machinery.  It
performs no network access, no installation, no Git write, no repository
mutation, and no Zenodo effect.  The candidate envelope is validated through
``tools/qikvrt_zenodo_machine_proof.py`` and its metadata through the generic
``tools/qikvrt_zenodo_publish.py`` contract.

The tool intentionally does not create OWNER_ZENODO_AUTHORIZATION.json,
publish-request.json, zenodo-publication.json, a DOI, a release, or a tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RELEASE_REL = pathlib.PurePosixPath(
    "release/round-trip-canonical-publication-zenodo-v1"
)
RELEASE = ROOT / RELEASE_REL
WORK_UNIT = ROOT / "state/work_units/ROUND_TRIP_ZENODO_BUNDLE_FREEZE_V1.json"
FREEZE_RECEIPT = RELEASE / "BUNDLE_FREEZE_RECEIPT.json"
PROOF_BUNDLE = RELEASE / "MACHINE_PROOF_BUNDLE.json"
CLAIM_MATRIX = RELEASE / "CLAIM_MATRIX.json"
METADATA = RELEASE / "ZENODO_METADATA.json"
TARGET_RECORD = RELEASE / "ZENODO_TARGET_RECORD.json"
RETROSPECTIVE = RELEASE / "RETROSPECTIVE_SOURCE_CONSTITUENTS.json"
FORMAL_SOURCES = RELEASE / "PROMOTED_FORMAL_SOURCE_BINDINGS.json"
FORMAL_RECEIPTS = RELEASE / "PROMOTED_FORMAL_KERNEL_RECEIPTS.json"
BOUNDARY_REPORT = RELEASE / "BOUNDARY_TEST_REPORT.json"
FILESET = RELEASE / "ZENODO_FILESET.md"
CHECKSUMS = RELEASE / "ZENODO_SHA256SUMS"

EXPECTED_AUTHORITY = "12842e8df99553260774d53517522b2b5539c8a8"
EXPECTED_AUTHORITY_TREE = "e8bdc99712bf0eca1a94ece6e34b20059076d280"
EXPECTED_MIRROR = "c52b324914978dc5d6d80251260ce55f396909f7"
EXPECTED_MIRROR_TREE = "5d62aadb3f973aeed7cd6d911fb0b05a5faa42cb"
EXPECTED_PRIMARY_SHA256 = (
    "dc58e50161b22826152dd251db836f06f85235a470e0253aeefa1b0a380787fe",
    "e5fd9c53a0bf6c84471d9b26d0c3c06019977aa6b2367913006fa9560a3c948f",
)
EXPECTED_RETURN_SHA256 = (
    "2bcaedc6181ced96fb23c0bf11d30c80f3023b1cf1a62972f328cbb38f383ef7"
)
EXPECTED_CLOSURE_SHA256 = (
    "525d67a990d8bddc8ea447bf5bd299e1d3ca59cb3de845a3e550516fa720fb16"
)
EXPECTED_TEMPORAL_SHA256 = (
    "946f5dff73f8964918204ee129d7382cd5f23317015f1160c58d90fa2479ebe2"
)
EXPECTED_COUNTS = {
    "upload_files": 54,
    "retrospective_constituents": 34,
    "retrospective_subjects": 19,
    "retrospective_claims": 70439,
    "explicit_open_claims": 1262,
    "formal_results": 6,
    "formal_theorems": 99,
    "publication_claims": 12,
}
FORBIDDEN_CONTROL_FILES = (
    "OWNER_ZENODO_AUTHORIZATION.json",
    "publish-request.json",
    "zenodo-publication.json",
)


class FreezeError(RuntimeError):
    """A deterministic candidate-freeze contract failed."""


def fail(message: str) -> NoReturn:
    raise FreezeError(message)


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def read_bytes(path: pathlib.Path) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            fail(f"required regular file is missing: {path.relative_to(ROOT)}")
        return path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")


def load_json(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    raw = read_bytes(path)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain an object")
    return value, raw


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def identity(path: pathlib.Path) -> dict[str, Any]:
    raw = read_bytes(path)
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }


def require_equal(observed: Any, expected: Any, where: str) -> None:
    if observed != expected:
        fail(f"{where} differs: observed={observed!r} expected={expected!r}")


def safe_repo_path(raw: Any, where: str) -> pathlib.Path:
    if not isinstance(raw, str) or not raw:
        fail(f"{where} must be a non-empty repository-relative path")
    rel = pathlib.PurePosixPath(raw)
    if rel.is_absolute() or ".." in rel.parts or ".git" in {p.casefold() for p in rel.parts}:
        fail(f"{where} is unsafe")
    path = ROOT.joinpath(*rel.parts)
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError:
        fail(f"{where} escapes the repository")
    return path


def verify_identity(record: Mapping[str, Any], where: str) -> dict[str, Any]:
    path = safe_repo_path(record.get("path"), where + ".path")
    observed = identity(path)
    for key in ("sha256", "git_blob_sha1"):
        require_equal(record.get(key), observed[key], f"{where}.{key}")
    if "bytes" in record:
        require_equal(record.get("bytes"), observed["bytes"], f"{where}.bytes")
    return {"path": path.relative_to(ROOT).as_posix(), **observed}


def verify_git_base(work_unit: Mapping[str, Any]) -> dict[str, Any]:
    source = work_unit.get("source_base")
    if not isinstance(source, dict):
        fail("work unit source_base must be an object")
    require_equal(source.get("authority_commit"), EXPECTED_AUTHORITY, "authority commit")
    require_equal(source.get("authority_tree"), EXPECTED_AUTHORITY_TREE, "authority tree")
    require_equal(source.get("mirror_commit"), EXPECTED_MIRROR, "mirror commit")
    require_equal(source.get("mirror_tree"), EXPECTED_MIRROR_TREE, "mirror tree")
    require_equal(source.get("portable_scope_paths_last_verified"), 43, "portable scope")

    observed: dict[str, Any] = {
        "repository_is_git_worktree": False,
        "authority_base_is_ancestor": None,
        "authority_base_tree_matches": None,
    }
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return observed
    observed["repository_is_git_worktree"] = True
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_AUTHORITY, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    observed["authority_base_is_ancestor"] = ancestor.returncode == 0
    if ancestor.returncode != 0:
        fail("candidate HEAD does not descend from the bound Authority base")
    tree = subprocess.run(
        ["git", "rev-parse", f"{EXPECTED_AUTHORITY}^{{tree}}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tree.returncode != 0:
        fail("bound Authority base commit is unavailable in local Git history")
    observed_tree = tree.stdout.strip()
    observed["authority_base_tree_matches"] = observed_tree == EXPECTED_AUTHORITY_TREE
    if observed_tree != EXPECTED_AUTHORITY_TREE:
        fail("bound Authority base tree differs")
    return observed


def verify_metadata() -> dict[str, Any]:
    metadata, raw = load_json(METADATA)
    try:
        from tools import qikvrt_zenodo_publish as publisher
    except ModuleNotFoundError as exc:
        fail(f"generic Zenodo publisher is unavailable: {exc}")
    validated = publisher._validate_metadata(metadata)  # reuse canonical contract
    require_equal(validated.get("creators"), [{"name": "Lohmann, Ingolf"}], "creators")
    require_equal(validated.get("license"), "cc-by-nc-nd-4.0", "metadata license")
    require_equal(validated.get("language"), "deu", "metadata language")
    require_equal(validated.get("upload_type"), "publication", "upload type")
    require_equal(validated.get("publication_type"), "workingpaper", "publication type")
    related = validated.get("related_identifiers")
    if not isinstance(related, list) or len(related) < 4:
        fail("metadata must bind Authority, Mirror and canonical entrypoints")
    return {
        "path": METADATA.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_metadata_sha256": hashlib.sha256(json_bytes(metadata)).hexdigest(),
    }


def verify_target_record() -> dict[str, Any]:
    target, raw = load_json(TARGET_RECORD)
    require_equal(target.get("mode"), "CREATE_NEW_RECORD", "target record mode")
    require_equal(target.get("prereserve_doi"), True, "target record prereserve_doi")
    require_equal(target.get("existing_record_id"), None, "existing record id")
    require_equal(target.get("existing_concept_doi"), None, "existing concept DOI")
    effect = target.get("effect_boundary")
    if not isinstance(effect, dict) or any(value is not False for value in effect.values()):
        fail("target-record contract must keep every production effect false")
    return {
        "path": TARGET_RECORD.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def verify_primary_files(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = receipt.get("primary_files")
    if not isinstance(values, list) or len(values) != 2:
        fail("freeze receipt must bind exactly two primary files")
    observed = [verify_identity(item, f"primary_files[{i}]") for i, item in enumerate(values)]
    require_equal(tuple(item["sha256"] for item in observed), EXPECTED_PRIMARY_SHA256, "primary SHA-256 order")
    return observed


def verify_retrospective() -> dict[str, Any]:
    value, raw = load_json(RETROSPECTIVE)
    require_equal(value.get("constituent_count"), EXPECTED_COUNTS["retrospective_constituents"], "constituent count")
    require_equal(value.get("claim_matrix_count"), 19, "claim-matrix count")
    require_equal(value.get("subject_receipt_count"), 7, "subject-receipt count")
    require_equal(value.get("content_change_decision_count"), 6, "change-decision count")
    require_equal(value.get("corpus_index_count"), 1, "corpus-index count")
    require_equal(value.get("corpus_receipt_count"), 1, "corpus-receipt count")
    require_equal(value.get("subjects"), EXPECTED_COUNTS["retrospective_subjects"], "subjects")
    require_equal(value.get("claims"), EXPECTED_COUNTS["retrospective_claims"], "claims")
    require_equal(value.get("explicit_open_claims"), EXPECTED_COUNTS["explicit_open_claims"], "open claims")
    constituents = value.get("constituents")
    if not isinstance(constituents, list) or len(constituents) != 34:
        fail("retrospective constituent inventory differs")
    paths = [item.get("path") for item in constituents if isinstance(item, dict)]
    identifiers = [item.get("constituent_id") for item in constituents if isinstance(item, dict)]
    upload_names = [item.get("upload_name") for item in constituents if isinstance(item, dict)]
    if len(paths) != 34 or len(set(paths)) != 34:
        fail("retrospective constituent paths are missing or duplicated")
    if len(set(identifiers)) != 34 or len(set(upload_names)) != 34:
        fail("retrospective constituent identities or upload names are duplicated")
    for index, item in enumerate(constituents):
        if not isinstance(item, dict):
            fail(f"constituents[{index}] must be an object")
        verify_identity(item, f"constituents[{index}]")
    return {
        "path": RETROSPECTIVE.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "constituent_count": 34,
    }


def verify_formal_bindings() -> dict[str, Any]:
    sources, source_raw = load_json(FORMAL_SOURCES)
    receipts, receipt_raw = load_json(FORMAL_RECEIPTS)
    source_results = sources.get("bindings")
    receipt_results = receipts.get("receipts")
    if not isinstance(source_results, list) or len(source_results) != 6:
        fail("formal source result inventory differs")
    if not isinstance(receipt_results, list) or len(receipt_results) != 6:
        fail("formal receipt result inventory differs")
    source_ids = [item.get("binding_id") for item in source_results if isinstance(item, dict)]
    receipt_ids = [item.get("binding_id") for item in receipt_results if isinstance(item, dict)]
    require_equal(source_ids, receipt_ids, "formal result order")
    require_equal(receipts.get("exact_head"), "d43175421f3a5b33dc18bf36686d61c8c00b396b", "formal exact head")
    require_equal(receipts.get("exact_tree"), "9e606990a00bb09b423d8d13d1b1f16be24d92d8", "formal exact tree")
    theorem_count = 0
    for index, item in enumerate(source_results):
        if not isinstance(item, dict):
            fail(f"formal source result {index} must be an object")
        source_path = safe_repo_path(item.get("source_path"), f"formal source result {index}.source_path")
        source_identity = identity(source_path)
        require_equal(item.get("source_git_blob_sha1"), source_identity["git_blob_sha1"], f"formal source result {index}.source_git_blob_sha1")
        work_unit_path = safe_repo_path(item.get("work_unit_path"), f"formal source result {index}.work_unit_path")
        work_unit_identity = identity(work_unit_path)
        require_equal(item.get("work_unit_git_blob_sha1"), work_unit_identity["git_blob_sha1"], f"formal source result {index}.work_unit_git_blob_sha1")
        for path_key in ("axiom_audit_path", "workflow_path"):
            path = safe_repo_path(item.get(path_key), f"formal source result {index}.{path_key}")
            read_bytes(path)
        require_equal(item.get("toolchain"), "leanprover/lean4:v4.19.0", f"formal source result {index}.toolchain")
        assumptions = item.get("assumptions")
        if not isinstance(assumptions, list) or not assumptions or not all(isinstance(value, str) and value for value in assumptions):
            fail(f"formal source result {index} assumptions differ")
        theorems = item.get("theorems")
        if not isinstance(theorems, list) or not theorems or len(theorems) != len(set(theorems)):
            fail(f"formal source result {index} theorem inventory differs")
        require_equal(item.get("theorem_count"), len(theorems), f"formal source result {index} theorem_count")
        theorem_count += len(theorems)
        boundary = item.get("scientific_boundary")
        if not isinstance(boundary, dict):
            fail(f"formal source result {index} lacks scientific boundary")
        if boundary.get("physical_correspondence") not in {"NOT_INFERRED", "NOT_ESTABLISHED"}:
            fail(f"formal source result {index} overstates physical correspondence")
    require_equal(theorem_count, EXPECTED_COUNTS["formal_theorems"], "formal theorem total")
    for index, item in enumerate(receipt_results):
        if not isinstance(item, dict):
            fail(f"formal receipt result {index} must be an object")
        require_equal(item.get("toolchain"), "leanprover/lean4:v4.19.0", f"formal receipt {index} toolchain")
        if item.get("project_axioms") != []:
            fail(f"formal receipt {index} contains project axioms")
        require_equal(item.get("receipt_scope"), "EXACT_HEAD_GITHUB_ACTIONS_ARTIFACT_BOUND", f"formal receipt {index} scope")
        artifact_id = item.get("artifact_id")
        run_id = item.get("workflow_run_id")
        if isinstance(artifact_id, bool) or not isinstance(artifact_id, int) or artifact_id <= 0:
            fail(f"formal receipt {index} artifact_id differs")
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
            fail(f"formal receipt {index} workflow_run_id differs")
        digest = item.get("artifact_archive_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            fail(f"formal receipt {index} archive digest differs")
    return {
        "source_path": FORMAL_SOURCES.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(source_raw).hexdigest(),
        "receipt_path": FORMAL_RECEIPTS.relative_to(ROOT).as_posix(),
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "result_count": 6,
        "theorem_count": theorem_count,
    }


def verify_claim_matrix() -> dict[str, Any]:
    matrix, raw = load_json(CLAIM_MATRIX)
    require_equal(matrix.get("publication_id"), "qikvrt-round-trip-retrospective-proof-v1", "claim matrix publication_id")
    claims = matrix.get("claims")
    require_equal(matrix.get("claim_count"), EXPECTED_COUNTS["publication_claims"], "publication claim count")
    if not isinstance(claims, list) or len(claims) != 12:
        fail("publication-level claim inventory differs")
    claim_ids = [item.get("claim_id") for item in claims if isinstance(item, dict)]
    if len(claim_ids) != 12 or len(set(claim_ids)) != 12:
        fail("publication claim identifiers are missing or duplicated")
    allowed = {
        "FORMAL_PROVED": ("PROVED", "ESTABLISHED_WITHIN_SCOPE"),
        "EMPIRICALLY_EVIDENCED": ("EVIDENCED", "EMPIRICALLY_SUPPORTED"),
        "SOURCE_BOUND": ("BOUND", "SOURCE_ATTRIBUTED"),
        "NORMATIVE": ("DECLARED", "NORMATIVE_DECLARATION"),
        "INTERPRETATIVE": ("DECLARED", "INTERPRETATIVE_DECLARATION"),
        "OPEN": ("OPEN", "EXPLICITLY_OPEN"),
    }
    formal = 0
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            fail(f"claims[{index}] must be an object")
        classification = claim.get("classification")
        if classification not in allowed:
            fail(f"claims[{index}] classification is invalid")
        require_equal(
            (claim.get("status"), claim.get("publication_wording")),
            allowed[classification],
            f"claims[{index}] disposition",
        )
        for key in ("proof_refs", "evidence_refs", "source_refs"):
            refs = claim.get(key)
            if not isinstance(refs, list) or len(refs) != len(set(refs)):
                fail(f"claims[{index}].{key} must be a unique list")
        if classification == "FORMAL_PROVED":
            formal += 1
            if not claim.get("proof_refs"):
                fail(f"formal claim {claim.get('claim_id')} lacks proof refs")
        if classification == "OPEN" and claim.get("publication_wording") != "EXPLICITLY_OPEN":
            fail(f"open claim {claim.get('claim_id')} is worded as a fact")
    require_equal(formal, 6, "formal publication claim count")
    return {
        "path": CLAIM_MATRIX.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "claim_count": len(claims),
        "formal_claim_count": formal,
    }


def fileset_aggregate(entries: Sequence[Mapping[str, Any]]) -> str:
    material = [
        {
            "name": item["name"],
            "path": item["path"],
            "sha256": item["sha256"],
            "git_blob_sha1": item["git_blob_sha1"],
        }
        for item in entries
    ]
    return hashlib.sha256(json_bytes(material)).hexdigest()


def verify_upload_fileset(receipt: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    fileset = receipt.get("upload_fileset")
    if not isinstance(fileset, dict):
        fail("freeze receipt upload_fileset must be an object")
    entries = fileset.get("entries")
    if not isinstance(entries, list) or len(entries) != EXPECTED_COUNTS["upload_files"]:
        fail("upload fileset count differs")
    names = [item.get("name") for item in entries if isinstance(item, dict)]
    paths = [item.get("path") for item in entries if isinstance(item, dict)]
    if len(names) != 54 or len(set(names)) != 54 or names != sorted(names):
        fail("upload names must be unique and sorted")
    if len(paths) != 54 or len(set(paths)) != 54:
        fail("upload paths must be unique")
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            fail(f"upload_fileset.entries[{index}] must be an object")
        verify_identity(item, f"upload_fileset.entries[{index}]")
    require_equal(fileset.get("count"), len(entries), "upload fileset count")
    require_equal(fileset.get("canonical_order"), "UPLOAD_NAME_ASCENDING", "upload order")
    require_equal(fileset.get("aggregate_sha256"), fileset_aggregate(entries), "upload fileset aggregate")

    bundle_paths = [item["path"] for item in bundle["candidate"]["files"]]
    bundle_paths.extend(item["path"] for item in bundle["artifacts"])
    bundle_paths.append(PROOF_BUNDLE.relative_to(ROOT).as_posix())
    require_equal(set(paths), set(bundle_paths), "freeze receipt versus machine-proof fileset")

    checksum_lines = read_bytes(CHECKSUMS).decode("utf-8").splitlines()
    expected_header = [
        "# SHA-256 for the exact upload fileset components generated before the proof bundle.",
        "# MACHINE_PROOF_BUNDLE.json is bound by BUNDLE_FREEZE_RECEIPT.json after generation.",
    ]
    checksum_entries = [
        item for item in entries
        if item["name"] not in {"ZENODO_SHA256SUMS", "MACHINE_PROOF_BUNDLE.json"}
    ]
    expected_lines = expected_header + [
        f"{item['sha256']}  {item['name']}"
        for item in sorted(checksum_entries, key=lambda value: value["name"])
    ]
    require_equal(checksum_lines, expected_lines, "ZENODO_SHA256SUMS")
    fileset_text = read_bytes(FILESET).decode("utf-8")
    for item in entries:
        if f"`{item['name']}`" not in fileset_text:
            fail(f"ZENODO_FILESET.md omits {item['name']}")
    return {
        "count": len(entries),
        "aggregate_sha256": fileset["aggregate_sha256"],
        "paths": paths,
    }


def verify_effect_boundary(receipt: Mapping[str, Any]) -> None:
    effect = receipt.get("effect_boundary")
    if not isinstance(effect, dict) or any(value is not False for value in effect.values()):
        fail("freeze receipt effect boundary must remain entirely false")
    completion = receipt.get("completion_claims")
    if completion != {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}:
        fail("freeze receipt completion claims differ")
    for basename in FORBIDDEN_CONTROL_FILES:
        if (RELEASE / basename).exists():
            fail(f"separate effect control file must remain absent: {basename}")


def verify_official_machine_proof(upload_paths: Sequence[str]) -> dict[str, Any]:
    try:
        from tools import qikvrt_zenodo_machine_proof as proof
    except ModuleNotFoundError as exc:
        fail(f"machine-proof validator is unavailable: {exc}")
    try:
        result = proof.validate_bundle(ROOT, PROOF_BUNDLE, upload_paths=list(upload_paths))
    except Exception as exc:  # validator has its own typed fail-closed exception
        fail(f"existing v2 machine-proof validator rejected candidate: {exc}")
    if result.get("machine_proof_complete") is not True:
        fail("machine-proof validator did not establish candidate completeness")
    return dict(result)


def check() -> dict[str, Any]:
    work_unit, work_raw = load_json(WORK_UNIT)
    receipt, receipt_raw = load_json(FREEZE_RECEIPT)
    bundle, bundle_raw = load_json(PROOF_BUNDLE)

    require_equal(work_unit.get("work_unit_id"), "ROUND_TRIP_ZENODO_BUNDLE_FREEZE_V1", "work unit id")
    require_equal(receipt.get("publication_id"), "qikvrt-round-trip-retrospective-proof-v1", "freeze publication_id")
    require_equal(bundle.get("publication_id"), receipt.get("publication_id"), "proof publication_id")
    base = verify_git_base(work_unit)
    primary = verify_primary_files(receipt)

    returned = receipt.get("prepublication_return_receipt")
    closure = receipt.get("effective_closure_receipt")
    temporal = receipt.get("temporal_precedence_receipt")
    if not all(isinstance(item, dict) for item in (returned, closure, temporal)):
        fail("bound receipt identities are incomplete")
    require_equal(returned.get("sha256"), EXPECTED_RETURN_SHA256, "return receipt digest")
    require_equal(closure.get("sha256"), EXPECTED_CLOSURE_SHA256, "closure receipt digest")
    require_equal(temporal.get("sha256"), EXPECTED_TEMPORAL_SHA256, "temporal receipt digest")
    verify_identity(returned, "prepublication return receipt")
    verify_identity(closure, "effective closure receipt")
    verify_identity(temporal, "temporal precedence receipt")
    require_equal(closure.get("current_unresolved_correction_subject_count"), 0, "current unresolved corrections")
    require_equal(temporal.get("historical_correction_subject_count"), 6, "historical corrections")
    require_equal(temporal.get("current_unresolved_correction_subject_count"), 0, "current unresolved temporal corrections")

    metadata = verify_metadata()
    target = verify_target_record()
    retrospective = verify_retrospective()
    formal = verify_formal_bindings()
    claims = verify_claim_matrix()
    verify_identity(
        {"path": BOUNDARY_REPORT.relative_to(ROOT).as_posix(), **identity(BOUNDARY_REPORT)},
        "boundary report",
    )
    fileset = verify_upload_fileset(receipt, bundle)
    verify_effect_boundary(receipt)
    official = verify_official_machine_proof(fileset["paths"])

    generated = work_unit.get("generated_candidate")
    if not isinstance(generated, dict):
        fail("work unit generated_candidate must be an object")
    verify_identity(generated["bundle_freeze_receipt"], "work unit freeze receipt")
    verify_identity(generated["machine_proof_bundle"], "work unit machine-proof bundle")
    require_equal(generated.get("retrospective_constituent_count"), 34, "work unit constituent count")
    require_equal(generated.get("promoted_formal_result_count"), 6, "work unit formal result count")
    require_equal(generated.get("promoted_theorem_count"), 99, "work unit theorem count")
    require_equal(generated.get("upload_file_count"), 54, "work unit upload count")
    require_equal(generated.get("upload_fileset_aggregate_sha256"), fileset["aggregate_sha256"], "work unit fileset aggregate")

    return {
        "schema": "qikvrt_round_trip_zenodo_bundle_freeze_check_v1",
        "state": "PASS",
        "scope": "LOCAL_EXACT_BUNDLE_FREEZE_CANDIDATE_ONLY",
        "repository": "Goldkelch/qik-vrt",
        "source_base": {
            "authority_commit": EXPECTED_AUTHORITY,
            "authority_tree": EXPECTED_AUTHORITY_TREE,
            "mirror_commit": EXPECTED_MIRROR,
            "mirror_tree": EXPECTED_MIRROR_TREE,
            **base,
        },
        "work_unit": {
            "path": WORK_UNIT.relative_to(ROOT).as_posix(),
            "bytes": len(work_raw),
            "sha256": hashlib.sha256(work_raw).hexdigest(),
            "git_blob_sha1": git_blob_sha1(work_raw),
        },
        "freeze_receipt": {
            "path": FREEZE_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": len(receipt_raw),
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
            "git_blob_sha1": git_blob_sha1(receipt_raw),
        },
        "machine_proof_bundle": {
            "path": PROOF_BUNDLE.relative_to(ROOT).as_posix(),
            "bytes": len(bundle_raw),
            "sha256": hashlib.sha256(bundle_raw).hexdigest(),
            "git_blob_sha1": git_blob_sha1(bundle_raw),
            "official_validator": official,
        },
        "primary_files": primary,
        "metadata": metadata,
        "target_record": target,
        "retrospective_proof": retrospective,
        "promoted_formal_results": formal,
        "claim_matrix": claims,
        "upload_fileset": {
            "count": fileset["count"],
            "aggregate_sha256": fileset["aggregate_sha256"],
        },
        "effect_boundary": {
            "owner_authorization_present": False,
            "publish_request_present": False,
            "zenodo_publication_evidence_present": False,
            "repository_promotion_executed": False,
            "mirror_port_executed": False,
            "zenodo_effect_executed": False,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
        "next_action": (
            "REGENERATE_AUTHORITY_NATIVE_INTEGRITY_THEN_RUN_ALL_APPLICABLE_"
            "EXACT_HEAD_GATES"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the frozen candidate")
    parser.add_argument("--json", action="store_true", help="emit one JSON result")
    args = parser.parse_args()
    if not args.check:
        parser.error("--check is required; this bounded adapter does not perform effects")
    try:
        result = check()
    except FreezeError as exc:
        result = {
            "schema": "qikvrt_round_trip_zenodo_bundle_freeze_check_v1",
            "state": "BLOCK",
            "blocker": str(exc),
            "effect_boundary": {
                "repository_mutation": False,
                "zenodo_mutation": False,
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("ROUND_TRIP_ZENODO_BUNDLE_FREEZE=BLOCK")
            print("BLOCKER=" + str(exc))
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("ROUND_TRIP_ZENODO_BUNDLE_FREEZE=PASS")
        print("SCOPE=LOCAL_EXACT_BUNDLE_FREEZE_CANDIDATE_ONLY")
        print("UPLOAD_FILES=54")
        print("NEXT_ACTION=" + result["next_action"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
