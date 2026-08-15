#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Recover one exact consumed ORR v2 Zenodo record without another create.

The controller is deliberately narrower than the generic publisher.  It starts
from the already durable ``record_created`` receipt for record 21947141, loads
the unchanged publisher bytes from the authorized execution commit, and wraps
that publisher with the established VRTCore H3 synchronous Git-Data receipt
pattern.  ``prepared``, ``publish_requested``, and ``public_verified`` become
non-force fast-forward commits on the same receipt branch before the wrapped
publisher may cross the next effect boundary.

The sole metadata relaxation is a directional, exact SHA-256 pair measured by
the read-only probe: the authorized German smart-quote description may be read
back in Zenodo's ASCII-quote form.  No general text normalization is performed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from tools import qikvrt_integrity as integrity
from tools import qikvrt_vrtcore_h3_e1_recovery as h3
from tools import qikvrt_zenodo_actions as zenodo


BASIS_PATH = (
    ROOT
    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
    / "ORR_V2_RECOVERY_BASIS.json"
)
MANIFEST_RELATIVE = pathlib.PurePosixPath(
    "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/"
    "publish-request.json"
)
EVIDENCE_RELATIVE = pathlib.PurePosixPath(
    "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/"
    "zenodo-publication.json"
)
WORKFLOW_RELATIVE = (
    ".github/workflows/"
    "qikvrt_observer_relative_retrocausality_zenodo_recovery.yml"
)
TOOL_RELATIVE = "tools/qikvrt_observer_relative_retrocausality_zenodo_recovery.py"
TEST_RELATIVE = "tests/test_observer_relative_retrocausality_zenodo_recovery.py"
INTEGRITY_PATHS = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
RECEIPT_PATHS = (*INTEGRITY_PATHS, EVIDENCE_RELATIVE.as_posix())
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REPOSITORY = "Goldkelch/qik-vrt"
MAIN = "60b4b3209e7b47b3572663e204b04e2e4176566b"
MAIN_TREE = "e3984c07a0e757f657cf49edcc042a6a72453446"
ACTIVATION_REF = (
    "refs/heads/publication/observer-relative-retrocausality-v2-4025b85c"
)
ACTIVATION = "63d26a3f8a7ddb74ba1eed4aab44d6decffc5cbc"
ACTIVATION_TREE = "1780ebf3e557af0681add01aeadd29d7d9878462"
TRIGGER_BRANCH = (
    "recovery-execution/observer-relative-retrocausality-v2-21947141-v1"
)
TRIGGER_REF = "refs/heads/" + TRIGGER_BRANCH
EXECUTION = "a7cd4011b8cdf06e650e22dc3e8dda6df22a5bf0"
EXECUTION_PARENT = "56127a6fd7dadea331fea98ed6cba19b4b96c6b2"
EXECUTION_TREE = "3f6b96dd007d259f54d944380ba218d454b7363d"
RECEIPT_REF = (
    "refs/heads/receipt/observer-relative-retrocausality-zenodo-v2-31881167575"
)
SEED = "059bf7a353b6a524cd272071276f80fd08e710c4"
SEED_TREE = "173b610a862499a7a611a9063b7bf4194d01a0e7"
SEED_EVIDENCE_BLOB = "fb1a0e88602a59f2b7e99280be47e9094223801b"
SEED_EVIDENCE_BYTES = 19743
SEED_EVIDENCE_SHA256 = (
    "9d4c3832992685b8c8b33846fe9b43c8707bc1b3ee6d3690707bafcb74529a53"
)
CONSUMPTION_REF = (
    "refs/tags/qikvrt-zenodo-auth/"
    "98655d056beb7a6df29c4dab9b4efea5064db63ac1e961f21aa305245cd8a4c9"
)
TAG_OBJECT = "36c516a4dc42d8571edbdb825a3334626a07f3f3"
RECORD_ID = 21947141
DOI = "10.5281/zenodo.21947141"
PROBE_HEAD = "5c4cba7e8dd6c179c9be4731801691c47d472c16"
PROBE_BRANCH = "recovery-probe/observer-relative-retrocausality-v2-21947141-v1"
PROBE_WORKFLOW_ID = 334975743
PROBE_WORKFLOW_NAME = "Probe exact ORR v2 Zenodo recovery metadata"
PROBE_WORKFLOW_PATH = ".github/workflows/qikvrt_orr_v2_zenodo_recovery_probe.yml"
PROBE_RUN_ID = 31881807652
PROBE_JOB_ID = 95005347027
PROBE_ARTIFACT_ID = 9246223317
PROBE_ARTIFACT_NAME = "orr-v2-zenodo-metadata-probe-31881807652-1"
PROBE_ARTIFACT_SIZE = 2194
PROBE_ARTIFACT_SHA256 = (
    "721f3e67f99ea198f5f35f7e6fa7c4392cbcc9066bd7e687d534f6ecc5b39377"
)
NORMALIZED_EXPECTED_BYTES = 1738
NORMALIZED_EXPECTED_SHA256 = (
    "95d5cc65ac566c2b63a8b0b1e0f1d5e07e5c28ed86ed55cefbcce99500497d10"
)
NORMALIZED_ACTUAL_BYTES = 1734
NORMALIZED_ACTUAL_SHA256 = (
    "dec665920bfc5a8476f782c16d29053aab822cf35ad2f961329da8000a221f73"
)
CHECKPOINT_PHASES = ("prepared", "publish_requested", "public_verified")
FULL_PHASES = ("record_created", *CHECKPOINT_PHASES)
COMMIT_MESSAGE = "zenodo: persist observer-relative retrocausality recovery receipt"
BOT_IDENTITY = {
    "name": "qik-vrt-zenodo-publication[bot]",
    "email": "qik-vrt-zenodo-publication[bot]@users.noreply.github.com",
    "date": "2026-08-15T11:08:30Z",
}
EXPECTED_TRIGGER_DELTA = (
    f"A\t{WORKFLOW_RELATIVE}",
    "M\tREPOSITORY_FILE_MANIFEST.json",
    "M\tREPOSITORY_FILE_MANIFEST.json.sha256",
    "M\tSHA256SUMS.txt",
    "A\trelease/observer-relative-retrocausality-current-synthesis-zenodo-v2/"
    "ORR_V2_RECOVERY_BASIS.json",
    f"A\t{TEST_RELATIVE}",
    f"A\t{TOOL_RELATIVE}",
)
PINNED_EXECUTION_FILES = (
    (
        MANIFEST_RELATIVE.as_posix(),
        "9885b5f8da41222520a9052da6a3cc139ed968b7",
        9570,
        "beb740b7dd4475114b6c4a8a34fa071ba623dc1c4391ebc01e59aacb6ad887bd",
    ),
    (
        "tools/qikvrt_zenodo_publish.py",
        "886f614106fe05f3c8f10cd485dd11455845cc54",
        91976,
        "1a914cf04d97ef646a19324a86bfb377355fc5a93f4e7eabe1e600ef93b6e707",
    ),
    (
        "tools/qikvrt_zenodo_actions.py",
        "fbbfed55004b580e9788b8ffa7a51d59e581d09b",
        64823,
        "77ab829b5018143568917762328366e5698dc2cd599f0ba0cd4106a5b5c292d8",
    ),
    (
        "tools/qikvrt_zenodo_machine_proof.py",
        "15c13591eb5e881a9b63a3b4596357194e27341b",
        98062,
        "c91b46edf68aeaa384c644c0fb2738de48abb943b14615380f8b17d6645aecb8",
    ),
)


class CheckpointStore(Protocol):
    def persist_and_readback(self, path: pathlib.Path, phase: str) -> str:
        """Persist one phase before returning control to the publisher."""

    def recheck_remote_boundary(self) -> None:
        """Re-observe every exact remote identity before a mutation."""


def _fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    raise SystemExit("BLOCK: " + message)


def _exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        _fail(where + " keys differ")


def _read_json(path: pathlib.Path, maximum: int = 2 * 1024 * 1024) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        _fail("recovery JSON is not a regular file")
    raw = path.read_bytes()
    if len(raw) > maximum:
        _fail("recovery JSON exceeds its byte limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"recovery JSON is invalid: {exc}")
    if not isinstance(value, dict):
        _fail("recovery JSON is not an object")
    return value


def load_recovery_basis(path: pathlib.Path = BASIS_PATH) -> dict[str, Any]:
    return validate_recovery_basis(_read_json(path))


def validate_recovery_basis(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the fixed seed, observation, and zero-create contract."""
    _exact_keys(
        value,
        {
            "_license",
            "schema",
            "repository",
            "controller",
            "execution",
            "seed_receipt",
            "consumption",
            "metadata_probe",
            "normalization",
            "recovery_contract",
            "claims",
        },
        "ORR v2 recovery basis",
    )
    if (
        value.get("schema") != "qikvrt_orr_v2_zenodo_recovery_basis_v1"
        or value.get("repository") != REPOSITORY
    ):
        _fail("ORR v2 recovery basis identity differs")
    license_value = value.get("_license")
    if license_value != {
        "classification": "machine_readable_recovery_basis",
        "copyright": "Copyright 2026 Ingolf Lohmann",
        "license": "CC-BY-NC-ND-4.0",
        "rights_holder": "Ingolf Lohmann",
    }:
        _fail("ORR v2 recovery basis license differs")
    controller = value.get("controller")
    execution = value.get("execution")
    seed = value.get("seed_receipt")
    consumption = value.get("consumption")
    probe = value.get("metadata_probe")
    normalization = value.get("normalization")
    contract = value.get("recovery_contract")
    claims = value.get("claims")
    if not all(
        isinstance(item, dict)
        for item in (
            controller,
            execution,
            seed,
            consumption,
            probe,
            normalization,
            contract,
            claims,
        )
    ):
        _fail("ORR v2 recovery basis nested values differ")
    assert isinstance(controller, dict)
    assert isinstance(execution, dict)
    assert isinstance(seed, dict)
    assert isinstance(consumption, dict)
    assert isinstance(probe, dict)
    assert isinstance(normalization, dict)
    assert isinstance(contract, dict)
    assert isinstance(claims, dict)
    if controller != {
        "main_parent": MAIN,
        "main_tree": MAIN_TREE,
        "activation_ref": ACTIVATION_REF,
        "activation_head": ACTIVATION,
        "activation_tree": ACTIVATION_TREE,
        "trigger_branch": TRIGGER_BRANCH,
        "trigger_commit_delta": list(EXPECTED_TRIGGER_DELTA),
    }:
        _fail("ORR v2 recovery controller basis differs")
    expected_execution = {
        "commit": EXECUTION,
        "sole_parent": EXECUTION_PARENT,
        "tree": EXECUTION_TREE,
        "manifest": {
            "path": PINNED_EXECUTION_FILES[0][0],
            "git_blob_sha1": PINNED_EXECUTION_FILES[0][1],
            "bytes": PINNED_EXECUTION_FILES[0][2],
            "sha256": PINNED_EXECUTION_FILES[0][3],
        },
        "publisher": {
            "path": PINNED_EXECUTION_FILES[1][0],
            "git_blob_sha1": PINNED_EXECUTION_FILES[1][1],
            "bytes": PINNED_EXECUTION_FILES[1][2],
            "sha256": PINNED_EXECUTION_FILES[1][3],
        },
        "publisher_dependencies": [
            {
                "path": path,
                "git_blob_sha1": blob,
                "bytes": size,
                "sha256": digest,
            }
            for path, blob, size, digest in PINNED_EXECUTION_FILES[2:]
        ],
    }
    if execution != expected_execution:
        _fail("ORR v2 recovery execution basis differs")
    if seed != {
        "ref": RECEIPT_REF,
        "commit": SEED,
        "sole_parent": EXECUTION,
        "tree": SEED_TREE,
        "evidence": {
            "path": EVIDENCE_RELATIVE.as_posix(),
            "git_blob_sha1": SEED_EVIDENCE_BLOB,
            "bytes": SEED_EVIDENCE_BYTES,
            "sha256": SEED_EVIDENCE_SHA256,
        },
        "state": "EFFECT_RELEASED/AWAITING_REMOTE_RECONCILIATION",
        "phase": "record_created",
        "record_id": RECORD_ID,
        "doi": DOI,
        "source_run_id": 31881167575,
        "source_run_attempt": 1,
        "source_artifact_id": 9246080267,
        "source_artifact_sha256": (
            "eede2bf7fb99bb205ca1ef8eb7afbcd62e68db6573eee865af4b831ee4e46215"
        ),
    }:
        _fail("ORR v2 seed receipt basis differs")
    if consumption != {
        "ref": CONSUMPTION_REF,
        "tag_object": TAG_OBJECT,
        "peeled_execution": EXECUTION,
        "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
    }:
        _fail("ORR v2 consumption basis differs")
    if probe != {
        "effect": "READ_ONLY",
        "controller_head": PROBE_HEAD,
        "controller_tree": "1eed1fbefb83774ae6f483d2e070bf68af373303",
        "controller_parent": MAIN,
        "workflow_id": PROBE_WORKFLOW_ID,
        "run_id": PROBE_RUN_ID,
        "run_attempt": 1,
        "job_id": PROBE_JOB_ID,
        "artifact_id": PROBE_ARTIFACT_ID,
        "artifact_name": PROBE_ARTIFACT_NAME,
        "artifact_size": PROBE_ARTIFACT_SIZE,
        "artifact_zip_sha256": (
            PROBE_ARTIFACT_SHA256
        ),
        "json_name": "orr-v2-zenodo-metadata-probe.json",
        "json_bytes": 11238,
        "json_sha256": (
            "ab895c408f7239790b1d689336b7b196d33c89a7931a0429a7b305da624c0bd6"
        ),
        "http_status": 200,
        "submitted": False,
        "server_file_count": 0,
        "difference_count": 1,
    }:
        _fail("ORR v2 metadata probe basis differs")
    if normalization != {
        "path": "metadata.description",
        "classification": "ZENODO_SMART_QUOTES_TO_ASCII_EXACT_HASH_PAIR",
        "expected_utf8_bytes": NORMALIZED_EXPECTED_BYTES,
        "expected_sha256": NORMALIZED_EXPECTED_SHA256,
        "actual_utf8_bytes": NORMALIZED_ACTUAL_BYTES,
        "actual_sha256": NORMALIZED_ACTUAL_SHA256,
        "all_other_controlled_metadata_exact": True,
    }:
        _fail("ORR v2 normalization basis differs")
    if contract != {
        "new_authorization": False,
        "new_consumption_lock": False,
        "new_deposition": False,
        "replacement_nonce": False,
        "authorization_rebinding": False,
        "restore_seed_before_effect": True,
        "checkpoint_phases": list(CHECKPOINT_PHASES),
        "checkpoint_transport": (
            "GITHUB_GIT_DATA_API_NON_FORCE_FAST_FORWARD_WITH_READBACK"
        ),
        "checkpoint_ref": RECEIPT_REF,
        "final_storage_ref": RECEIPT_REF,
        "normalization_scope": "EXACT_DIRECTIONAL_SHA256_PAIR_ONLY",
        "final_phase": "public_verified",
    }:
        _fail("ORR v2 recovery contract differs")
    if claims != {
        "zenodo_publication_completed": False,
        "public_record_verified": False,
        "effect_ack_done": False,
        "final_pass": False,
    }:
        _fail("ORR v2 recovery claims differ")
    return dict(value)


def _git(
    root: pathlib.Path,
    *arguments: str,
    accepted: frozenset[int] = frozenset({0}),
    credential_free: bool = False,
    environment: Mapping[str, str] | None = None,
) -> tuple[int, bytes]:
    return h3._git(  # reuse the audited H3 credential-stripping subprocess path
        root,
        *arguments,
        accepted=accepted,
        credential_free=credential_free,
        environment=environment,
    )


def _git_blob_sha(raw: bytes) -> str:
    return h3._git_blob_sha(raw)


def _git_object(root: pathlib.Path, expression: str) -> str:
    _status, raw = _git(root, "rev-parse", "--verify", expression)
    value = raw.decode("ascii").strip()
    if HEX40.fullmatch(value) is None:
        _fail("local Git object identity is invalid")
    return value


def _receipt_delta(root: pathlib.Path, parent: str, child: str) -> dict[str, str]:
    _status, raw = _git(
        root,
        "diff",
        "--name-status",
        "--no-renames",
        parent,
        child,
        "--",
    )
    result: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        status, path = line.split("\t", 1)
        if path in result:
            _fail("receipt delta repeats a path")
        result[path] = status
    return result


def _expected_receipt_integrity(
    root: pathlib.Path,
    evidence_raw: bytes,
) -> dict[str, bytes]:
    """Rebuild the canonical integrity trio from execution plus evidence."""
    _status, base_raw = _git(
        root,
        "show",
        f"{EXECUTION}:REPOSITORY_FILE_MANIFEST.json",
    )
    try:
        base = json.loads(base_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"execution integrity base is invalid: {exc}")
    entries = base.get("files")
    if (
        not isinstance(entries, list)
        or any(not isinstance(item, dict) for item in entries)
        or any(item.get("path") == EVIDENCE_RELATIVE.as_posix() for item in entries)
    ):
        _fail("execution integrity base already contains recovery evidence")
    evidence_entry = {
        "path": EVIDENCE_RELATIVE.as_posix(),
        "classification": "repository_content",
        "immutable": True,
        "excluded_from_sha256_index": False,
        "bytes": len(evidence_raw),
        "sha256": hashlib.sha256(evidence_raw).hexdigest(),
        "file_type": "regular",
    }
    expected_entries = sorted(
        [*entries, evidence_entry],
        key=lambda item: item["path"],
    )
    expected_manifest = dict(base)
    expected_manifest["files"] = expected_entries
    expected_manifest["file_count"] = len(expected_entries)
    expected_manifest["immutable_file_count"] = sum(
        item.get("immutable") is True for item in expected_entries
    )
    expected_manifest["excluded_file_count"] = (
        len(expected_entries) - expected_manifest["immutable_file_count"]
    )
    expected_manifest["repository_content_tree_sha256"] = (
        integrity._content_tree_sha256(expected_entries)
    )
    manifest_raw = (
        json.dumps(
            expected_manifest,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    index_raw = "".join(
        f"{item['sha256']}  {item['path']}\n"
        for item in expected_entries
        if item.get("immutable") is True
    ).encode("utf-8")
    detached_raw = (
        hashlib.sha256(manifest_raw).hexdigest()
        + "  REPOSITORY_FILE_MANIFEST.json\n"
    ).encode("ascii")
    return {
        "REPOSITORY_FILE_MANIFEST.json": manifest_raw,
        "SHA256SUMS.txt": index_raw,
        "REPOSITORY_FILE_MANIFEST.json.sha256": detached_raw,
    }


def _validate_integrity_bytes(
    root: pathlib.Path,
    commit: str,
    evidence_raw: bytes,
) -> None:
    for path, expected in _expected_receipt_integrity(root, evidence_raw).items():
        _status, actual = _git(root, "show", f"{commit}:{path}")
        if actual != expected:
            _fail("receipt integrity differs for " + path)


def validate_execution_objects(
    root: pathlib.Path,
    basis: Mapping[str, Any],
) -> None:
    """Verify execution bytes plus the exact durable record-created seed."""
    validate_recovery_basis(dict(basis))
    if _git_object(root, "HEAD^{commit}") != EXECUTION:
        _fail("execution worktree is not at the authorized execution commit")
    _status, parents = _git(root, "show", "-s", "--format=%P", EXECUTION)
    if parents.decode("ascii").strip() != EXECUTION_PARENT:
        _fail("execution sole parent differs")
    if _git_object(root, f"{EXECUTION}^{{tree}}") != EXECUTION_TREE:
        _fail("execution tree differs")
    for path, blob, size, digest in PINNED_EXECUTION_FILES:
        _status, raw = _git(root, "show", f"{EXECUTION}:{path}")
        if (
            _git_object(root, f"{EXECUTION}:{path}") != blob
            or len(raw) != size
            or hashlib.sha256(raw).hexdigest() != digest
        ):
            _fail("pinned execution bytes differ for " + path)
    if (
        _git_object(root, f"{SEED}^{{commit}}") != SEED
        or _git_object(root, f"{SEED}^{{tree}}") != SEED_TREE
    ):
        _fail("seed receipt object differs")
    _status, seed_parent = _git(root, "show", "-s", "--format=%P", SEED)
    if seed_parent.decode("ascii").strip() != EXECUTION:
        _fail("seed receipt parent differs")
    expected_delta = {
        **{path: "M" for path in INTEGRITY_PATHS},
        EVIDENCE_RELATIVE.as_posix(): "A",
    }
    if _receipt_delta(root, EXECUTION, SEED) != expected_delta:
        _fail("seed receipt exact four-path delta differs")
    _status, evidence_raw = _git(root, "show", f"{SEED}:{EVIDENCE_RELATIVE}")
    if (
        _git_object(root, f"{SEED}:{EVIDENCE_RELATIVE}") != SEED_EVIDENCE_BLOB
        or len(evidence_raw) != SEED_EVIDENCE_BYTES
        or hashlib.sha256(evidence_raw).hexdigest() != SEED_EVIDENCE_SHA256
    ):
        _fail("seed receipt evidence identity differs")
    _validate_integrity_bytes(root, SEED, evidence_raw)
    publisher = h3._load_e1_publisher(root)
    manifest_path = root / MANIFEST_RELATIVE
    manifest = publisher.load_manifest(manifest_path, root)
    try:
        evidence = json.loads(evidence_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"seed receipt evidence is invalid: {exc}")
    validated = publisher._validate_recovery_evidence(
        evidence,
        manifest_path,
        root,
        manifest,
        EXECUTION,
    )
    if (
        validated.get("phase") != "record_created"
        or validated.get("state") != publisher.CONSUMPTION_STATE
        or validated.get("record_id") != RECORD_ID
        or validated.get("doi") != DOI
        or validated.get("remote_consumption", {}).get("ref") != CONSUMPTION_REF
        or validated.get("remote_consumption", {}).get("tag_object") != TAG_OBJECT
    ):
        _fail("seed receipt recovery binding differs")


def _description_normalization(actual: Any, expected: Any) -> str | None:
    """Accept exact text or the one directional probe-bound SHA-256 pair."""
    if not isinstance(actual, str) or not isinstance(expected, str):
        return None
    if actual == expected:
        return "EXACT"
    actual_raw = actual.encode("utf-8")
    expected_raw = expected.encode("utf-8")
    if (
        expected.count("„") == 1
        and expected.count("“") == 1
        and actual == expected.translate({0x201E: '"', 0x201C: '"'})
        and len(expected_raw) == NORMALIZED_EXPECTED_BYTES
        and hashlib.sha256(expected_raw).hexdigest() == NORMALIZED_EXPECTED_SHA256
        and len(actual_raw) == NORMALIZED_ACTUAL_BYTES
        and hashlib.sha256(actual_raw).hexdigest() == NORMALIZED_ACTUAL_SHA256
    ):
        return "ZENODO_SMART_QUOTES_TO_ASCII_EXACT_HASH_PAIR"
    return None


def _draft_metadata_mismatch_keys(
    publisher_module: Any,
    actual: Any,
    expected: Mapping[str, Any],
) -> tuple[str, ...]:
    """Port H3 R9's scoped comparator with only the ORR hash-pair exception."""
    if not isinstance(actual, dict):
        return tuple(sorted(key for key in expected if key != "prereserve_doi"))
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        if key == "prereserve_doi":
            continue
        if key == "description":
            if _description_normalization(actual.get(key), expected_value) is None:
                mismatches.append(key)
        elif not publisher_module.zenodo._metadata_matches(
            actual.get(key),
            expected_value,
        ):
            mismatches.append(key)
    return tuple(sorted(mismatches))


def _normalize_description_for_original_gate(
    value: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = value.get("metadata")
    if not isinstance(metadata, dict):
        _fail("Zenodo record metadata is absent")
    if _description_normalization(
        metadata.get("description"),
        expected.get("description"),
    ) is None:
        _fail("Zenodo description escaped the exact observed normalization pair")
    normalized = dict(value)
    normalized_metadata = dict(metadata)
    normalized_metadata["description"] = expected["description"]
    normalized["metadata"] = normalized_metadata
    return normalized


def _call_api(
    api: Any,
    method: str,
    path: str,
    *,
    payload: Mapping[str, Any] | None = None,
    accept: tuple[int, ...] = (200,),
    allow_ambiguous_transport: bool = False,
) -> tuple[int, dict[str, Any]]:
    return h3._call_api(
        api,
        method,
        path,
        payload=payload,
        accept=accept,
        allow_ambiguous_transport=allow_ambiguous_transport,
    )


def _validate_probe_run(value: Mapping[str, Any], where: str) -> None:
    repository = value.get("repository")
    head_repository = value.get("head_repository")
    if (
        value.get("id") != PROBE_RUN_ID
        or value.get("run_attempt") != 1
        or value.get("workflow_id") != PROBE_WORKFLOW_ID
        or value.get("name") != PROBE_WORKFLOW_NAME
        or value.get("path") != PROBE_WORKFLOW_PATH
        or value.get("event") != "push"
        or value.get("head_sha") != PROBE_HEAD
        or value.get("head_branch") != PROBE_BRANCH
        or value.get("status") != "completed"
        or value.get("conclusion") != "success"
        or not isinstance(repository, dict)
        or repository.get("full_name") != REPOSITORY
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != REPOSITORY
    ):
        _fail("probe workflow run differs at " + where)


def _validate_probe_artifact(value: Mapping[str, Any], where: str) -> None:
    if (
        value.get("id") != PROBE_ARTIFACT_ID
        or value.get("name") != PROBE_ARTIFACT_NAME
        or value.get("size_in_bytes") != PROBE_ARTIFACT_SIZE
        or value.get("digest") != "sha256:" + PROBE_ARTIFACT_SHA256
        or value.get("expired") is not False
    ):
        _fail("probe artifact differs at " + where)


def verify_metadata_probe(api: Any) -> None:
    """Bind the live successful read-only probe before any recovery effect."""
    run_path = "/repos/Goldkelch/qik-vrt/actions/runs/" + str(PROBE_RUN_ID)
    _status, latest = _call_api(api, "GET", run_path, accept=(200,))
    _validate_probe_run(latest, "latest run")
    _status, attempt = _call_api(
        api,
        "GET",
        run_path + "/attempts/1",
        accept=(200,),
    )
    _validate_probe_run(attempt, "attempt one")
    for key in (
        "id",
        "run_attempt",
        "workflow_id",
        "name",
        "path",
        "event",
        "head_sha",
        "head_branch",
        "status",
        "conclusion",
    ):
        if latest.get(key) != attempt.get(key):
            _fail("probe workflow run changed between exact reads")

    job_path = "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(PROBE_JOB_ID)
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    if (
        job.get("id") != PROBE_JOB_ID
        or job.get("run_id") != PROBE_RUN_ID
        or job.get("run_attempt") != 1
        or job.get("name") != "probe"
        or job.get("head_sha") != PROBE_HEAD
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
        or job.get("run_url") != "https://api.github.com" + run_path
    ):
        _fail("probe workflow job differs")

    _status, inventory = _call_api(
        api,
        "GET",
        run_path + "/artifacts",
        accept=(200,),
    )
    artifacts = inventory.get("artifacts")
    if (
        inventory.get("total_count") != 1
        or not isinstance(artifacts, list)
        or len(artifacts) != 1
        or not isinstance(artifacts[0], dict)
    ):
        _fail("probe artifact inventory differs")
    _validate_probe_artifact(artifacts[0], "run inventory")
    _status, artifact = _call_api(
        api,
        "GET",
        "/repos/Goldkelch/qik-vrt/actions/artifacts/" + str(PROBE_ARTIFACT_ID),
        accept=(200,),
    )
    _validate_probe_artifact(artifact, "direct readback")
    for key in ("id", "name", "size_in_bytes", "digest", "expired"):
        if artifacts[0].get(key) != artifact.get(key):
            _fail("probe artifact changed between exact reads")


def _ref_api_path(ref: str, *, plural: bool) -> str:
    allowed = {
        "refs/heads/main",
        ACTIVATION_REF,
        TRIGGER_REF,
        RECEIPT_REF,
        CONSUMPTION_REF,
    }
    if ref not in allowed or any(character in ref for character in ("\x00", "\r", "\n")):
        _fail("GitHub ref escaped the exact ORR recovery allowlist")
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    return (
        "/repos/Goldkelch/qik-vrt/git/refs/" + suffix
        if plural
        else "/repos/Goldkelch/qik-vrt/git/ref/" + suffix
    )


def _validate_ref(value: Mapping[str, Any], ref: str, sha: str, kind: str) -> None:
    target = value.get("object")
    if (
        value.get("ref") != ref
        or not isinstance(target, dict)
        or target.get("sha") != sha
        or target.get("type") != kind
    ):
        _fail("GitHub ref response differs")


def _read_ref(api: Any, ref: str, *, kind: str = "commit") -> str:
    _status, value = _call_api(
        api,
        "GET",
        _ref_api_path(ref, plural=False),
        accept=(200,),
    )
    target = value.get("object")
    sha = target.get("sha") if isinstance(target, dict) else None
    if not isinstance(sha, str) or HEX40.fullmatch(sha) is None:
        _fail("GitHub ref object identity is invalid")
    _validate_ref(value, ref, sha, kind)
    return sha


def _validate_consumption_tag(
    api: Any,
    publisher_module: Any,
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    if manifest["owner_authorization"]["remote_consumption_ref"] != CONSUMPTION_REF:
        _fail("manifest consumption ref differs")
    _status, ref_value = _call_api(
        api,
        "GET",
        _ref_api_path(CONSUMPTION_REF, plural=False),
        accept=(200,),
    )
    _validate_ref(ref_value, CONSUMPTION_REF, TAG_OBJECT, "tag")
    _status, tag_value = _call_api(
        api,
        "GET",
        "/repos/Goldkelch/qik-vrt/git/tags/" + TAG_OBJECT,
        accept=(200,),
    )
    publisher_module._validate_github_tag_response(
        tag_value,
        publisher_module._expected_consumption_tag(manifest, EXECUTION),
        TAG_OBJECT,
    )
    return {
        "remote": "github_git_data_api",
        "api_origin": publisher_module.GITHUB_API_BASE,
        "repository": REPOSITORY,
        "ref": CONSUMPTION_REF,
        "tag_object": TAG_OBJECT,
        "object_type": "tag",
        "execution_head": EXECUTION,
        "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
        "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
    }


def persist_receipt_fast_forward(
    api: Any,
    *,
    expected_old_sha: str,
    commit_sha: str,
) -> str:
    """Move only the existing receipt ref by one non-force fast-forward."""
    if HEX40.fullmatch(expected_old_sha) is None or HEX40.fullmatch(commit_sha) is None:
        _fail("receipt fast-forward identity is invalid")
    singular = _ref_api_path(RECEIPT_REF, plural=False)
    _status, before = _call_api(api, "GET", singular, accept=(200,))
    _validate_ref(before, RECEIPT_REF, expected_old_sha, "commit")
    mutation_status: int | None = None
    changed: dict[str, Any] = {}
    try:
        mutation_status, changed = _call_api(
            api,
            "PATCH",
            _ref_api_path(RECEIPT_REF, plural=True),
            payload={"sha": commit_sha, "force": False},
            accept=(200, 409, 422),
            allow_ambiguous_transport=True,
        )
    except h3.AmbiguousRefMutation:
        mutation_status = None
    if mutation_status == 200:
        _validate_ref(changed, RECEIPT_REF, commit_sha, "commit")
    elif mutation_status not in {None, 409, 422}:
        _fail("receipt fast-forward status differs")
    _status, after = _call_api(api, "GET", singular, accept=(200,))
    _validate_ref(after, RECEIPT_REF, commit_sha, "commit")
    return commit_sha


def _fetch_receipt(root: pathlib.Path, commit: str) -> None:
    h3._fetch_credential_free(root, RECEIPT_REF, commit)


def _validate_commit_provenance(root: pathlib.Path, commit: str) -> None:
    format_string = "%s%x00%b%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI"
    _status, observed = _git(
        root,
        "show",
        "-s",
        "--no-show-signature",
        "--format=" + format_string,
        commit,
    )
    expected = "\0".join(
        (
            COMMIT_MESSAGE,
            "",
            BOT_IDENTITY["name"],
            BOT_IDENTITY["email"],
            BOT_IDENTITY["date"],
            BOT_IDENTITY["name"],
            BOT_IDENTITY["email"],
            BOT_IDENTITY["date"],
        )
    ).encode("utf-8") + b"\n"
    if observed != expected:
        _fail("receipt commit provenance differs")


def _validate_receipt_commit(
    root: pathlib.Path,
    commit: str,
    parent: str,
    publisher_module: Any,
    manifest: Mapping[str, Any],
    *,
    expected_phase: str | None = None,
) -> dict[str, Any]:
    _status, parents = _git(root, "show", "-s", "--format=%P", commit)
    if parents.decode("ascii").strip() != parent:
        _fail("receipt commit is not an exact single-parent continuation")
    if _receipt_delta(root, parent, commit) != {
        **{path: "M" for path in INTEGRITY_PATHS},
        EVIDENCE_RELATIVE.as_posix(): "M",
    }:
        _fail("receipt commit exact four-path delta differs")
    _status, entries = _git(root, "ls-tree", "-z", commit, "--", *RECEIPT_PATHS)
    modes: dict[str, tuple[str, str]] = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, object_type, _sha = metadata.decode("ascii").split()
        modes[raw_path.decode("utf-8")] = (mode, object_type)
    if modes != {path: ("100644", "blob") for path in RECEIPT_PATHS}:
        _fail("receipt path mode differs")
    _status, evidence_raw = _git(root, "show", f"{commit}:{EVIDENCE_RELATIVE}")
    try:
        value = json.loads(evidence_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"receipt evidence JSON is invalid: {exc}")
    validated = publisher_module._validate_recovery_evidence(
        value,
        root / MANIFEST_RELATIVE,
        root,
        manifest,
        EXECUTION,
    )
    phase = validated.get("phase")
    if phase not in CHECKPOINT_PHASES:
        _fail("receipt continuation phase differs")
    if expected_phase is not None and phase != expected_phase:
        _fail("receipt phase differs from requested checkpoint")
    if (
        validated.get("record_id") != RECORD_ID
        or validated.get("doi") != DOI
        or validated.get("remote_consumption", {}).get("tag_object") != TAG_OBJECT
    ):
        _fail("receipt record or consumption identity differs")
    _validate_commit_provenance(root, commit)
    _validate_integrity_bytes(root, commit, evidence_raw)
    return validated


def _validate_local_candidate(root: pathlib.Path, evidence_path: pathlib.Path) -> None:
    if _git_object(root, "HEAD^{commit}") != EXECUTION:
        _fail("local receipt candidate is not based on execution")
    if evidence_path != root / EVIDENCE_RELATIVE:
        _fail("local receipt evidence path differs")
    _status, staged = _git(
        root,
        "diff",
        "--cached",
        "--name-status",
        "--no-renames",
        "HEAD",
        "--",
    )
    if staged:
        _fail("local receipt candidate has staged paths")
    _status, tracked = _git(
        root,
        "diff",
        "--name-status",
        "--no-renames",
        "HEAD",
        "--",
    )
    observed: dict[str, str] = {}
    for line in tracked.decode("utf-8").splitlines():
        status, path = line.split("\t", 1)
        observed[path] = status
    if observed != {path: "M" for path in INTEGRITY_PATHS}:
        _fail("local worktree differs outside receipt integrity paths")
    _status, untracked = _git(
        root,
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        ".",
    )
    names = {os.fsdecode(item) for item in untracked.split(b"\0") if item}
    if names != {EVIDENCE_RELATIVE.as_posix()}:
        _fail("local worktree has unexpected untracked recovery paths")
    evidence_raw = evidence_path.read_bytes()
    for relative, expected in _expected_receipt_integrity(root, evidence_raw).items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != expected:
            _fail("local generated receipt integrity differs for " + relative)


class RecoveryReceiptStore:
    """Synchronous exact-phase receipt chain on the existing receipt ref."""

    def __init__(
        self,
        execution_root: pathlib.Path,
        api: Any,
        *,
        controller_head: str,
    ) -> None:
        self.root = execution_root.resolve()
        self.api = api
        self.basis = load_recovery_basis()
        if HEX40.fullmatch(controller_head) is None:
            _fail("controller head is unresolved or invalid")
        self.controller_head = controller_head
        validate_execution_objects(self.root, self.basis)
        verify_metadata_probe(self.api)
        self.publisher = h3._load_e1_publisher(self.root)
        self.manifest_path = self.root / MANIFEST_RELATIVE
        self.evidence_path = self.root / EVIDENCE_RELATIVE
        self.manifest = self.publisher.load_manifest(self.manifest_path, self.root)
        with h3._without_effect_credentials():
            self.publisher._validate_origin_repository(self.root, REPOSITORY)
        self.remote_consumption = _validate_consumption_tag(
            self.api,
            self.publisher,
            self.manifest,
        )
        if _read_ref(self.api, "refs/heads/main") != MAIN:
            _fail("main differs from the exact controller parent")
        if _read_ref(self.api, ACTIVATION_REF) != ACTIVATION:
            _fail("activation branch differs")
        if _read_ref(self.api, TRIGGER_REF) != self.controller_head:
            _fail("one-shot trigger branch differs")
        self.current_tip = _read_ref(self.api, RECEIPT_REF)
        self._prepared_replay_pending = False

    def recheck_remote_boundary(self) -> None:
        if _read_ref(self.api, "refs/heads/main") != MAIN:
            _fail("main moved across the exact recovery boundary")
        if _read_ref(self.api, ACTIVATION_REF) != ACTIVATION:
            _fail("activation branch moved across the recovery boundary")
        if _read_ref(self.api, TRIGGER_REF) != self.controller_head:
            _fail("trigger branch moved across the recovery boundary")
        if _read_ref(self.api, RECEIPT_REF) != self.current_tip:
            _fail("receipt branch moved across the checkpoint boundary")
        if _validate_consumption_tag(
            self.api,
            self.publisher,
            self.manifest,
        ) != self.remote_consumption:
            _fail("consumption tag moved across the recovery boundary")

    def _prepare_integrity(self) -> None:
        with h3._without_effect_credentials():
            generated = integrity.generate(self.root)
            if not generated.ok:
                _fail("cannot generate exact recovery receipt integrity")
            verified = integrity.verify(self.root)
            if not verified.ok:
                _fail("generated recovery receipt integrity does not verify")

    def _expected_tree(self, parent: str, blobs: Mapping[str, str]) -> str:
        with tempfile.TemporaryDirectory(prefix="qikvrt-orr-receipt-index-") as directory:
            environment = dict(os.environ)
            environment["GIT_INDEX_FILE"] = str(pathlib.Path(directory) / "index")
            _git(self.root, "read-tree", f"{parent}^{{tree}}", environment=environment)
            for path in RECEIPT_PATHS:
                _git(
                    self.root,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"100644,{blobs[path]},{path}",
                    environment=environment,
                )
            _status, raw = _git(self.root, "write-tree", environment=environment)
        tree = raw.decode("ascii").strip()
        if HEX40.fullmatch(tree) is None:
            _fail("local expected receipt tree is invalid")
        return tree

    def _create_receipt_commit(self, parent: str) -> tuple[str, str]:
        self._prepare_integrity()
        _validate_local_candidate(self.root, self.evidence_path)
        raw_by_path: dict[str, bytes] = {}
        blobs: dict[str, str] = {}
        for relative in RECEIPT_PATHS:
            path = self.root / relative
            if not path.is_file() or path.is_symlink():
                _fail("receipt input is not a regular file")
            raw = path.read_bytes()
            raw_by_path[relative] = raw
            blobs[relative] = _git_blob_sha(raw)
        for relative, raw in raw_by_path.items():
            result = subprocess.run(
                ["git", "hash-object", "-w", "--stdin"],
                cwd=self.root,
                env={
                    key: value
                    for key, value in os.environ.items()
                    if key not in {"GITHUB_TOKEN", "GH_TOKEN", "ZENODO_ACCESS_TOKEN"}
                },
                input=raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0 or result.stdout.decode("ascii").strip() != blobs[relative]:
                _fail("local receipt blob materialization differs")
        expected_tree = self._expected_tree(parent, blobs)
        for relative in RECEIPT_PATHS:
            _status, response = _call_api(
                self.api,
                "POST",
                "/repos/Goldkelch/qik-vrt/git/blobs",
                payload={
                    "content": base64.b64encode(raw_by_path[relative]).decode("ascii"),
                    "encoding": "base64",
                },
                accept=(201,),
            )
            if response.get("sha") != blobs[relative]:
                _fail("GitHub receipt blob identity differs")
        _status, parent_value = _call_api(
            self.api,
            "GET",
            "/repos/Goldkelch/qik-vrt/git/commits/" + parent,
            accept=(200,),
        )
        parent_tree = parent_value.get("tree")
        if (
            parent_value.get("sha") != parent
            or not isinstance(parent_tree, dict)
            or HEX40.fullmatch(str(parent_tree.get("sha", ""))) is None
        ):
            _fail("GitHub receipt parent commit differs")
        _status, tree_value = _call_api(
            self.api,
            "POST",
            "/repos/Goldkelch/qik-vrt/git/trees",
            payload={
                "base_tree": parent_tree["sha"],
                "tree": [
                    {
                        "path": relative,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blobs[relative],
                    }
                    for relative in RECEIPT_PATHS
                ],
            },
            accept=(201,),
        )
        if tree_value.get("sha") != expected_tree:
            _fail("GitHub receipt tree identity differs")
        _status, commit_value = _call_api(
            self.api,
            "POST",
            "/repos/Goldkelch/qik-vrt/git/commits",
            payload={
                "message": COMMIT_MESSAGE,
                "tree": expected_tree,
                "parents": [parent],
                "author": BOT_IDENTITY,
                "committer": BOT_IDENTITY,
            },
            accept=(201,),
        )
        commit = commit_value.get("sha")
        if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
            _fail("GitHub receipt commit identity is invalid")
        response_tree = commit_value.get("tree")
        response_parents = commit_value.get("parents")
        if (
            commit_value.get("message") != COMMIT_MESSAGE
            or not isinstance(response_tree, dict)
            or response_tree.get("sha") != expected_tree
            or not isinstance(response_parents, list)
            or [
                item.get("sha") if isinstance(item, dict) else None
                for item in response_parents
            ]
            != [parent]
        ):
            _fail("GitHub receipt commit response differs")
        return commit, expected_tree

    def _parent_of(self, commit: str) -> str:
        _status, raw = _git(self.root, "show", "-s", "--format=%P", commit)
        parent = raw.decode("ascii").strip()
        if HEX40.fullmatch(parent) is None:
            _fail("receipt parent identity differs")
        return parent

    def validate_chain(self, tip: str) -> list[dict[str, Any]]:
        reverse: list[dict[str, Any]] = []
        cursor = tip
        visited: set[str] = set()
        while cursor != SEED:
            if cursor in visited or len(visited) >= len(CHECKPOINT_PHASES):
                _fail("receipt chain is cyclic or unbounded")
            visited.add(cursor)
            parent = self._parent_of(cursor)
            reverse.append(
                _validate_receipt_commit(
                    self.root,
                    cursor,
                    parent,
                    self.publisher,
                    self.manifest,
                )
            )
            cursor = parent
        chain = list(reversed(reverse))
        phases = [str(item["phase"]) for item in chain]
        if phases != list(CHECKPOINT_PHASES[: len(phases)]):
            _fail("receipt chain is not the exact phase prefix")
        for item in chain:
            if (
                item.get("record_id") != RECORD_ID
                or item.get("doi") != DOI
                or item.get("remote_consumption") != self.remote_consumption
            ):
                _fail("receipt chain identity changes")
        return chain

    def restore_seed_or_tip(self) -> tuple[bool, str]:
        self.recheck_remote_boundary()
        _fetch_receipt(self.root, self.current_tip)
        if self.current_tip == SEED:
            chain: list[dict[str, Any]] = []
        else:
            chain = self.validate_chain(self.current_tip)
        _status, raw = _git(
            self.root,
            "show",
            f"{self.current_tip}:{EVIDENCE_RELATIVE}",
        )
        if os.path.lexists(self.evidence_path):
            _fail("local recovery evidence exists before exact restoration")
        h3._write_exclusive_regular(self.evidence_path, raw)
        return bool(chain and chain[-1]["phase"] == "public_verified"), self.current_tip

    def persist_and_readback(self, path: pathlib.Path, phase: str) -> str:
        self.recheck_remote_boundary()
        if path.resolve() != self.evidence_path.resolve():
            _fail("checkpoint evidence path differs")
        if phase not in CHECKPOINT_PHASES:
            _fail("checkpoint phase differs from the exact recovery suffix")
        value = _read_json(path)
        validated = self.publisher._validate_recovery_evidence(
            value,
            self.manifest_path,
            self.root,
            self.manifest,
            EXECUTION,
        )
        if (
            validated.get("phase") != phase
            or validated.get("record_id") != RECORD_ID
            or validated.get("doi") != DOI
            or validated.get("remote_consumption") != self.remote_consumption
        ):
            _fail("checkpoint evidence binding differs")
        chain = self.validate_chain(self.current_tip) if self.current_tip != SEED else []
        prior_phase = chain[-1]["phase"] if chain else "record_created"
        left = FULL_PHASES.index(prior_phase)
        right = FULL_PHASES.index(phase)
        if right < left:
            if (
                prior_phase == "publish_requested"
                and phase == "prepared"
                and any(item["phase"] == "prepared" for item in chain)
            ):
                self._prepared_replay_pending = True
                return self.current_tip
            _fail("checkpoint phase moves backwards")
        if right == left:
            _status, existing = _git(
                self.root,
                "show",
                f"{self.current_tip}:{EVIDENCE_RELATIVE}",
            )
            if existing != path.read_bytes():
                _fail("same-phase checkpoint evidence differs")
            if phase == "publish_requested":
                self._prepared_replay_pending = False
            return self.current_tip
        if right != left + 1:
            _fail("checkpoint phase skipped a durable predecessor")
        if self._prepared_replay_pending and phase != "publish_requested":
            _fail("prepared replay lacks identical publish intent confirmation")
        parent = self.current_tip
        commit, expected_tree = self._create_receipt_commit(parent)
        self.recheck_remote_boundary()
        persist_receipt_fast_forward(
            self.api,
            expected_old_sha=parent,
            commit_sha=commit,
        )
        _fetch_receipt(self.root, commit)
        if _git_object(self.root, f"{commit}^{{tree}}") != expected_tree:
            _fail("credential-free receipt tree differs")
        _validate_receipt_commit(
            self.root,
            commit,
            parent,
            self.publisher,
            self.manifest,
            expected_phase=phase,
        )
        self.current_tip = commit
        if phase == "publish_requested":
            self._prepared_replay_pending = False
        return commit


def run_publisher_with_checkpoints(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    store: CheckpointStore,
    *,
    publisher_module: Any | None = None,
) -> dict[str, Any]:
    """Wrap the unchanged pinned publisher with H3-style synchronous gates."""
    module = publisher_module or h3._load_e1_publisher(root)
    callable_value = module.publish
    original_exclusive = module._create_consumption_receipt
    original_atomic = module._atomic_recovery_evidence
    original_acquire = module._acquire_remote_consumption_lock
    original_resume = module._resume_publication
    original_list_owned = module._list_all_owned_depositions
    original_inventory_candidates = module._canonical_inventory_candidates
    original_recover_create_requested = module._recover_create_requested_record
    original_gate_precreate_inventory = module._gate_precreate_inventory
    client_type = module.zenodo.ZenodoClient
    original_request = client_type.request
    original_create_paper = client_type.create_paper
    original_prepare_draft = client_type.prepare_draft
    original_wait_for_editable_metadata = client_type.wait_for_editable_metadata
    original_gate_record = client_type.gate_record
    state: dict[str, Any] = {
        "armed": False,
        "starting_phase": None,
        "manifest": None,
        "entries": None,
        "verified": None,
        "bucket_path": None,
        "metadata_confirmed": False,
        "metadata_put_skipped": False,
        "upload_index": 0,
        "upload_in_flight": False,
        "prepared_durable": False,
        "publish_intent_durable": False,
        "publish_post_attempted": False,
    }

    def reject_new_consumption_lock(*_args: Any, **_kwargs: Any) -> Any:
        _fail("recovery may not acquire or create an authorization lock")

    def reject_create_paper(*_args: Any, **_kwargs: Any) -> Any:
        _fail("recovery forbids creation of a Zenodo deposition")

    def reject_precreate_path(*_args: Any, **_kwargs: Any) -> Any:
        _fail("record-created recovery forbids every pre-create inventory path")

    def persist_after_write(path: pathlib.Path, value: Mapping[str, Any]) -> None:
        phase = value.get("phase")
        if phase in CHECKPOINT_PHASES:
            store.persist_and_readback(path, str(phase))
            if phase == "prepared":
                entries = state["entries"]
                if (
                    state["metadata_confirmed"] is not True
                    or not isinstance(entries, list)
                    or state["upload_index"] != len(entries)
                ):
                    _fail("prepared checkpoint preceded exact upload completion")
                state["prepared_durable"] = True
            elif phase == "publish_requested":
                if state["prepared_durable"] is not True:
                    _fail("publish intent preceded durable preparation")
                state["publish_intent_durable"] = True

    def checkpointing_exclusive_writer(
        path: pathlib.Path,
        value: Mapping[str, Any],
        secrets: Mapping[str, str],
    ) -> None:
        original_exclusive(path, value, secrets)
        persist_after_write(path, value)

    def checkpointing_atomic_writer(
        path: pathlib.Path,
        value: Mapping[str, Any],
        secrets: Mapping[str, str],
    ) -> None:
        original_atomic(path, value, secrets)
        persist_after_write(path, value)

    def exact_bucket_path(instance: Any, current: Mapping[str, Any]) -> str:
        links = current.get("links")
        bucket = links.get("bucket") if isinstance(links, dict) else None
        if not isinstance(bucket, str):
            _fail("exact ORR draft lacks its upload bucket")
        safe = module.zenodo.validate_response_url(bucket, instance.base_url)
        parts = urllib.parse.urlsplit(safe)
        path = parts.path.rstrip("/")
        if (
            parts.query
            or parts.fragment
            or re.fullmatch(
                r"/api/files/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                path,
            )
            is None
        ):
            _fail("exact ORR upload bucket escaped its canonical API shape")
        return path

    def validate_record_identity(
        current_state: str,
        current: Mapping[str, Any],
        *,
        require_files_empty: bool,
    ) -> None:
        if module.zenodo._record_id(current, "ORR recovery record") != RECORD_ID:
            _fail("ORR recovery record ID differs")
        if module.zenodo._doi_from_deposition(current, "ORR recovery record") != DOI:
            _fail("ORR recovery DOI differs")
        if current_state not in {"draft", "published"}:
            _fail("ORR recovery record state differs")
        manifest = state.get("manifest")
        if not isinstance(manifest, Mapping):
            _fail("ORR recovery manifest is not armed")
        if current_state == "published":
            normalized = _normalize_description_for_original_gate(
                current,
                manifest["metadata"],
            )
            if not module.zenodo._published_metadata_matches(
                normalized.get("metadata"),
                manifest["metadata"],
            ):
                _fail("ORR published controlled metadata differs")
        else:
            mismatches = _draft_metadata_mismatch_keys(
                module,
                current.get("metadata"),
                manifest["metadata"],
            )
            if mismatches:
                _fail("ORR controlled metadata differs: " + ",".join(mismatches))
        if require_files_empty and client_type._server_files(current):
            _fail("ORR record-created seed gained files before recovery")

    def wait_for_exact_metadata(
        instance: Any,
        record_id: int,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        manifest = state.get("manifest")
        if (
            state["armed"] is not True
            or record_id != RECORD_ID
            or not isinstance(manifest, Mapping)
            or metadata != manifest["metadata"]
            or state["metadata_put_skipped"] is not True
        ):
            _fail("metadata confirmation lacks the exact no-op preflight")
        for attempt in range(instance.poll_attempts):
            status, value = instance.get(
                f"/api/deposit/depositions/{RECORD_ID}",
                accept=(200, 202),
            )
            validate_record_identity("draft", value, require_files_empty=True)
            links = value.get("links")
            if status == 200 and isinstance(links, dict) and isinstance(
                links.get("bucket"), str
            ):
                store.recheck_remote_boundary()
                second_status, confirmed = instance.get(
                    f"/api/deposit/depositions/{RECORD_ID}",
                    accept=(200, 202),
                )
                if second_status != 200:
                    _fail("exact ORR metadata changed during confirmation")
                validate_record_identity(
                    "draft",
                    confirmed,
                    require_files_empty=True,
                )
                state["bucket_path"] = exact_bucket_path(instance, confirmed)
                state["metadata_confirmed"] = True
                store.recheck_remote_boundary()
                return dict(confirmed)
            if attempt + 1 < instance.poll_attempts:
                instance.sleeper(instance.poll_interval)
        _fail("timed out waiting for the exact ORR metadata normalization")

    def gate_exact_record(
        instance: Any,
        value: Mapping[str, Any],
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        expected_doi: str,
        *,
        published: bool,
    ) -> None:
        manifest = state.get("manifest")
        if (
            state["armed"] is not True
            or record_id != RECORD_ID
            or expected_doi != DOI
            or not isinstance(manifest, Mapping)
            or metadata != manifest["metadata"]
            or entries != state["entries"]
        ):
            _fail("ORR record gate inputs differ")
        validate_record_identity(
            "published" if published else "draft",
            value,
            require_files_empty=False,
        )
        normalized = _normalize_description_for_original_gate(value, metadata)
        original_gate_record(
            instance,
            normalized,
            record_id,
            metadata,
            entries,
            expected_doi,
            published=published,
        )

    def prepare_exact_draft(
        instance: Any,
        kind: str,
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        verified: Mapping[tuple[str, str], bytes],
        expected_doi: str,
    ) -> str:
        phase = state.get("starting_phase")
        if phase == "record_created":
            return original_prepare_draft(
                instance,
                kind,
                record_id,
                metadata,
                entries,
                verified,
                expected_doi,
            )
        if (
            phase not in {"prepared", "publish_requested"}
            or kind != "publication"
            or record_id != RECORD_ID
            or expected_doi != DOI
            or entries != state.get("entries")
            or verified != state.get("verified")
            or metadata != state.get("manifest", {}).get("metadata")
        ):
            _fail("ORR prepared replay inputs differ")
        current_state, current = instance.get_deposition_or_record(RECORD_ID)
        if current_state == "published":
            if phase != "publish_requested":
                _fail("ORR public record lacks durable publish intent")
            instance.wait_for_gated_record(
                RECORD_ID,
                metadata,
                entries,
                DOI,
                published=True,
                initial=current,
            )
            return "published"
        if current_state != "draft":
            _fail("ORR prepared replay record state differs")
        validate_record_identity("draft", current, require_files_empty=False)
        instance.gate_record(
            current,
            RECORD_ID,
            metadata,
            entries,
            DOI,
            published=False,
        )
        state.update(
            {
                "metadata_put_skipped": True,
                "metadata_confirmed": True,
                "bucket_path": exact_bucket_path(instance, current),
                "upload_index": len(entries),
                "prepared_durable": True,
                "publish_intent_durable": phase == "publish_requested",
            }
        )
        store.recheck_remote_boundary()
        return "draft"

    def gate_uploaded_prefix(instance: Any, current: Mapping[str, Any]) -> None:
        entries = state["entries"]
        index = state["upload_index"]
        if not isinstance(entries, list) or not isinstance(index, int):
            _fail("ORR upload-prefix state differs")
        expected = entries[:index]
        server_files = instance._server_files(current)
        by_name: dict[str, Mapping[str, Any]] = {}
        for item in server_files:
            name = instance._server_file_name(item)
            if name in by_name:
                _fail("ORR upload prefix contains a duplicate file")
            by_name[name] = item
        if set(by_name) != {entry["name"] for entry in expected}:
            _fail("ORR upload prefix differs from completed manifest entries")
        for entry in expected:
            item = by_name[entry["name"]]
            size = item.get("filesize", item.get("size"))
            if isinstance(size, str) and size.isdecimal():
                size = int(size)
            if size != entry["size"] or item.get("checksum") not in {
                entry["md5"],
                "md5:" + entry["md5"],
            }:
                _fail("ORR upload-prefix file identity differs")

    def guarded_request(instance: Any, method: str, url: str, **kwargs: Any) -> Any:
        normalized_method = str(method).upper()
        safe_url = module.zenodo.validate_response_url(url, instance.base_url)
        parts = urllib.parse.urlsplit(safe_url)
        path = parts.path
        if normalized_method == "GET":
            return original_request(instance, normalized_method, safe_url, **kwargs)
        if normalized_method == "POST" and path == "/api/deposit/depositions":
            _fail("ORR recovery blocked the Zenodo create endpoint")
        if (
            state["armed"] is not True
            or parts.query
            or parts.fragment
            or not isinstance(state.get("manifest"), Mapping)
        ):
            _fail("ORR Zenodo mutation preceded exact reconciliation")
        deposition_path = f"/api/deposit/depositions/{RECORD_ID}"
        metadata_put = normalized_method == "PUT" and path == deposition_path
        publish_path = deposition_path + "/actions/publish"
        store.recheck_remote_boundary()
        current_state, current = instance.get_deposition_or_record(RECORD_ID)
        if current_state != "draft":
            _fail("ORR recovery forbids mutation after publication")
        validate_record_identity(
            current_state,
            current,
            require_files_empty=state["upload_index"] == 0,
        )
        if metadata_put:
            manifest = state["manifest"]
            if (
                state["metadata_put_skipped"] is True
                or set(kwargs) != {"payload", "accept"}
                or kwargs.get("payload") != {"metadata": manifest["metadata"]}
                or kwargs.get("accept") != (200, 202)
                or instance._server_files(current)
                or _draft_metadata_mismatch_keys(
                    module,
                    current.get("metadata"),
                    manifest["metadata"],
                )
            ):
                _fail("ORR exact metadata no-op contract differs")
            first_bucket = exact_bucket_path(instance, current)
            result = original_request(instance, "GET", safe_url, accept=(200,))
            response, confirmed = result
            if getattr(response, "status", None) != 200:
                _fail("ORR metadata no-op GET status differs")
            validate_record_identity("draft", confirmed, require_files_empty=True)
            if exact_bucket_path(instance, confirmed) != first_bucket:
                _fail("ORR metadata no-op changed the upload bucket")
            state["metadata_put_skipped"] = True
            store.recheck_remote_boundary()
            return result
        if normalized_method == "DELETE":
            _fail("ORR record-created recovery forbids file deletion")
        if state["metadata_confirmed"] is not True:
            _fail("ORR upload or publish preceded metadata confirmation")
        gate_uploaded_prefix(instance, current)
        bucket_path = state["bucket_path"]
        if not isinstance(bucket_path, str) or exact_bucket_path(instance, current) != bucket_path:
            _fail("ORR upload bucket changed after metadata confirmation")
        entries = state["entries"]
        verified = state["verified"]
        index = state["upload_index"]
        if (
            normalized_method == "PUT"
            and isinstance(entries, list)
            and isinstance(verified, Mapping)
            and isinstance(index, int)
            and index < len(entries)
        ):
            entry = entries[index]
            expected_path = bucket_path + "/" + urllib.parse.quote(entry["name"], safe="")
            data = verified.get(("publication", entry["name"]))
            if (
                path != expected_path
                or state["upload_in_flight"] is True
                or set(kwargs) != {"data", "content_type", "accept"}
                or not isinstance(data, bytes)
                or kwargs.get("data") != data
                or len(data) != entry["size"]
                or hashlib.md5(data).hexdigest() != entry["md5"]  # noqa: S324
                or hashlib.sha256(data).hexdigest() != entry["sha256"]
                or kwargs.get("content_type") != "application/octet-stream"
                or kwargs.get("accept") != (200, 201, 202)
            ):
                _fail("ORR bounded upload request differs")
            state["upload_in_flight"] = True
            result = original_request(instance, normalized_method, safe_url, **kwargs)
            state["upload_in_flight"] = False
            state["upload_index"] = index + 1
            return result
        if normalized_method == "POST" and path == publish_path:
            if (
                not isinstance(entries, list)
                or state["upload_index"] != len(entries)
                or state["upload_in_flight"] is True
                or state["prepared_durable"] is not True
                or state["publish_intent_durable"] is not True
                or state["publish_post_attempted"] is True
                or set(kwargs) != {"accept"}
                or kwargs.get("accept") != (200, 201, 202, 409)
            ):
                _fail("ORR publish request preceded durable exact gates")
            instance.gate_record(
                current,
                RECORD_ID,
                state["manifest"]["metadata"],
                entries,
                DOI,
                published=False,
            )
            store.recheck_remote_boundary()
            state["publish_post_attempted"] = True
            return original_request(instance, normalized_method, safe_url, **kwargs)
        _fail("ORR Zenodo mutation escaped the exact record state machine")

    def reconcile_exact_seed(
        evidence: Mapping[str, Any],
        evidence_path: pathlib.Path,
        pinned_manifest_path: pathlib.Path,
        pinned_root: pathlib.Path,
        manifest: Mapping[str, Any],
        execution_head: str,
        verified: Mapping[tuple[str, str], bytes],
        client: Any,
        secrets: Mapping[str, str],
    ) -> dict[str, Any]:
        phase = evidence.get("phase")
        remote_consumption = evidence.get("remote_consumption")
        if (
            phase not in {"record_created", "prepared", "publish_requested"}
            or evidence.get("state") != module.CONSUMPTION_STATE
            or evidence.get("record_id") != RECORD_ID
            or evidence.get("doi") != DOI
            or not isinstance(remote_consumption, Mapping)
            or remote_consumption.get("ref") != CONSUMPTION_REF
            or remote_consumption.get("tag_object") != TAG_OBJECT
            or remote_consumption.get("execution_head") != EXECUTION
            or remote_consumption.get("recovery_mode")
            != "EXISTING_EXACT_REF_NO_CREATE"
            or execution_head != EXECUTION
            or pinned_root.resolve() != root.resolve()
            or pinned_manifest_path.resolve() != manifest_path.resolve()
        ):
            _fail("ORR resume input differs from the exact durable seed")
        entries = module._shared_entries(manifest["files"])
        if not isinstance(entries, list) or not isinstance(verified, Mapping):
            _fail("ORR immutable publication inputs differ")
        state.update(
            {
                "armed": True,
                "starting_phase": phase,
                "manifest": manifest,
                "entries": entries,
                "verified": verified,
            }
        )
        current_state, current = client.get_deposition_or_record(RECORD_ID)
        if current_state == "published":
            if phase != "publish_requested":
                _fail("ORR public record lacks an exact publish_requested checkpoint")
            validate_record_identity("published", current, require_files_empty=False)
        elif current_state == "draft":
            validate_record_identity(
                "draft",
                current,
                require_files_empty=phase == "record_created",
            )
            if phase in {"prepared", "publish_requested"}:
                client.gate_record(
                    current,
                    RECORD_ID,
                    manifest["metadata"],
                    entries,
                    DOI,
                    published=False,
                )
            if exact_bucket_path(client, current) == "":
                _fail("ORR upload bucket is empty")
        else:
            _fail("probe-bound ORR record state differs")
        store.recheck_remote_boundary()
        print(
            "ORR_V2_DESCRIPTION_NORMALIZATION="
            + str(
                _description_normalization(
                    current.get("metadata", {}).get("description"),
                    manifest["metadata"]["description"],
                )
            )
        )
        return original_resume(
            evidence,
            evidence_path,
            pinned_manifest_path,
            pinned_root,
            manifest,
            execution_head,
            verified,
            client,
            secrets,
        )

    module._create_consumption_receipt = checkpointing_exclusive_writer
    module._atomic_recovery_evidence = checkpointing_atomic_writer
    module._acquire_remote_consumption_lock = reject_new_consumption_lock
    module._resume_publication = reconcile_exact_seed
    module._list_all_owned_depositions = reject_precreate_path
    module._canonical_inventory_candidates = reject_precreate_path
    module._recover_create_requested_record = reject_precreate_path
    module._gate_precreate_inventory = reject_precreate_path
    client_type.request = guarded_request
    client_type.create_paper = reject_create_paper
    client_type.prepare_draft = prepare_exact_draft
    client_type.wait_for_editable_metadata = wait_for_exact_metadata
    client_type.gate_record = gate_exact_record
    try:
        return callable_value(manifest_path, root)
    finally:
        client_type.request = original_request
        client_type.create_paper = original_create_paper
        client_type.prepare_draft = original_prepare_draft
        client_type.wait_for_editable_metadata = original_wait_for_editable_metadata
        client_type.gate_record = original_gate_record
        module._resume_publication = original_resume
        module._create_consumption_receipt = original_exclusive
        module._atomic_recovery_evidence = original_atomic
        module._acquire_remote_consumption_lock = original_acquire
        module._list_all_owned_depositions = original_list_owned
        module._canonical_inventory_candidates = original_inventory_candidates
        module._recover_create_requested_record = original_recover_create_requested
        module._gate_precreate_inventory = original_gate_precreate_inventory


def _write_outputs(path: pathlib.Path | None, values: Mapping[str, object]) -> None:
    if path is None:
        return
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for key, raw in values.items():
                value = str(raw).lower() if isinstance(raw, bool) else str(raw)
                if (
                    re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
                    or not value
                    or "\n" in value
                    or "\r" in value
                ):
                    _fail("unsafe GitHub output value")
                handle.write(f"{key}={value}\n")
    except OSError as exc:
        _fail(f"cannot write GitHub output: {exc}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument("--verify-basis", action="store_true")
    operations.add_argument("--prepare", action="store_true")
    operations.add_argument("--publish", action="store_true")
    parser.add_argument("--execution-root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--controller-head")
    parser.add_argument("--github-output", type=pathlib.Path)
    return parser


def _store(args: argparse.Namespace) -> RecoveryReceiptStore:
    if not isinstance(args.controller_head, str):
        _fail("controller head argument is required")
    return RecoveryReceiptStore(
        args.execution_root.resolve(),
        h3.GitHubAPI(os.environ.get("GITHUB_TOKEN", "")),
        controller_head=args.controller_head,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.verify_basis:
            basis = load_recovery_basis()
            validate_execution_objects(args.execution_root.resolve(), basis)
            print("ORR_V2_ZENODO_RECOVERY_BASIS=VALID")
            return 0
        store = _store(args)
        finalized, tip = store.restore_seed_or_tip()
        if args.prepare:
            _write_outputs(
                args.github_output,
                {
                    "prepared": True,
                    "finalized": finalized,
                    "receipt_commit": tip,
                },
            )
            print(
                "ORR_V2_ZENODO_RECOVERY_PREPARE="
                + ("FINALIZED" if finalized else "SEED_RESTORED")
            )
            return 0
        if finalized:
            _write_outputs(
                args.github_output,
                {
                    "status": 0,
                    "finalized": True,
                    "receipt_commit": tip,
                },
            )
            print("ORR_V2_ZENODO_RECOVERY_PUBLICATION=ALREADY_FINALIZED")
            return 0
        if not args.publish:
            _fail("no recovery controller operation was selected")
        os.environ["GITHUB_SHA"] = EXECUTION
        result = run_publisher_with_checkpoints(
            store.manifest_path,
            store.root,
            store,
            publisher_module=store.publisher,
        )
        if (
            result.get("phase") != "public_verified"
            or result.get("state") != "published"
            or result.get("record_id") != RECORD_ID
            or result.get("doi") != DOI
        ):
            _fail("unchanged publisher did not return exact public evidence")
        chain = store.validate_chain(store.current_tip)
        if not chain or chain[-1].get("phase") != "public_verified":
            _fail("public_verified evidence is not durable on the receipt branch")
        _write_outputs(
            args.github_output,
            {
                "status": 0,
                "finalized": False,
                "phase": "public_verified",
                "state": "published",
                "record_id": RECORD_ID,
                "doi": DOI,
                "receipt_commit": store.current_tip,
            },
        )
        print("ORR_V2_ZENODO_RECOVERY_PUBLICATION=PUBLISHED")
        return 0
    except tuple(h3._ZENODO_ERROR_TYPES) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        _write_outputs(args.github_output, {"status": 2})
        return 2
    except SystemExit as exc:
        message = str(exc)
        print(message if message.startswith("BLOCK:") else "BLOCK: recovery failed", file=sys.stderr)
        _write_outputs(args.github_output, {"status": 2})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
