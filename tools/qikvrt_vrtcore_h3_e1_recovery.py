#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed recovery controller for the consumed VRTCore H3 E1 decision.

The controller never creates, updates, or deletes an authorization tag.  It
recognizes one already existing, byte-exact annotated tag and keeps the
publication execution identity fixed at E1.  A synchronous checkpoint hook
persists every non-final V2 recovery phase before the original E1 publisher is
allowed to continue to the next Zenodo effect.

This module does not change the default publisher path.  The hook exists only
inside :func:`run_publisher_with_checkpoints` and is removed in ``finally``.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from typing import Any, Protocol


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from tools import qikvrt_integrity as integrity
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_publish as publish


_ZENODO_ERROR_TYPES: list[type[BaseException]] = [zenodo.ZenodoError]


BASIS_PATH = (
    ROOT
    / "release/vrtcore-relational-h3-publication-2026-08-02"
    / "H3_E1_RECOVERY_BASIS.json"
)
MANIFEST_RELATIVE = pathlib.PurePosixPath(
    "release/vrtcore-relational-h3-publication-2026-08-02/publish-request.json"
)
EVIDENCE_RELATIVE = pathlib.PurePosixPath(
    "release/vrtcore-relational-h3-publication-2026-08-02/zenodo-publication.json"
)
INTEGRITY_PATHS = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
RECEIPT_PATHS = (*INTEGRITY_PATHS, EVIDENCE_RELATIVE.as_posix())
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONTROLLER_PARENT_PLACEHOLDER = "__H3_E1_RECOVERY_EXPECTED_PARENT__"
TRIGGER_BRANCH = "recovery-execution/vrtcore-relational-h3-e1-v1"
CREATE_POST_ONCE_REF = (
    "refs/heads/qikvrt-recovery/vrtcore-zenodo/h3-create-post-once/"
    "53e757ebce929b40250f90a02ed2a9ec62de6217"
)

EXPECTED: dict[str, Any] = {
    "repository": "Goldkelch/qik-vrt",
    "e1": "53e757ebce929b40250f90a02ed2a9ec62de6217",
    "e1_parent": "cdb0e9fe8444565df665affa64463295648b1368",
    "e1_tree": "99ee39034abbdf8abd4fd9891915cf3d647365db",
    "publication_ref": "refs/heads/publication/vrtcore-relational-h3-v1",
    "recovery_ref": (
        "refs/heads/qikvrt-recovery/vrtcore-zenodo/h3/"
        "53e757ebce929b40250f90a02ed2a9ec62de6217"
    ),
    "run_id": 30753751400,
    "job_id": 91512247885,
    "tag_object": "e831a5298cb4b95011b7a53719f784d622ccc42e",
    "initial_phase": "authorization_consumed",
    "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
    "job_log_sha256": (
        "646a878b04bb2b52ecd9a4b537c0d619b29441a615ddd305547ede58574abc1c"
    ),
    "job_log_bytes": 300251,
    "failure_boundary": "NO_ZENODO_API_CALL_BEFORE_FAILURE",
    "controller_parent_placeholder": CONTROLLER_PARENT_PLACEHOLDER,
    "trigger_branch": TRIGGER_BRANCH,
    "create_post_once_ref": CREATE_POST_ONCE_REF,
    "e1_publisher_blob": "886f614106fe05f3c8f10cd485dd11455845cc54",
    "e1_publisher_bytes": 91976,
    "e1_publisher_sha256": (
        "1a914cf04d97ef646a19324a86bfb377355fc5a93f4e7eabe1e600ef93b6e707"
    ),
    "e1_actions_blob": "fbbfed55004b580e9788b8ffa7a51d59e581d09b",
    "e1_actions_bytes": 64823,
    "e1_actions_sha256": (
        "77ab829b5018143568917762328366e5698dc2cd599f0ba0cd4106a5b5c292d8"
    ),
    "e1_machine_proof_blob": "15c13591eb5e881a9b63a3b4596357194e27341b",
    "e1_machine_proof_bytes": 98062,
    "e1_machine_proof_sha256": (
        "c91b46edf68aeaa384c644c0fb2738de48abb943b14615380f8b17d6645aecb8"
    ),
    "e1_workflow_blob": "426ade15c6fceb56dc3355400d71c4f668fc93ef",
    "e1_workflow_bytes": 93343,
    "e1_workflow_sha256": (
        "8ed7450c89681d195144f7fa6a8d39ff5f0e2cf8a224d21da4cf085fe219e258"
    ),
}

R4_UNSENT_CREATE_INCIDENT: dict[str, Any] = {
    "controller": "dfcf28f9f48b5857ef3b4ef50f979d9a1979be08",
    "controller_parent": "89fa9a49a73a7194ccdbed080e9dbdc26a506d5e",
    "controller_tree": "ffef6ba9411e278e322fb9d9c2f5df36990426ec",
    "run_id": 30763216363,
    "job_id": 91537354739,
    "run_attempt": 1,
    "log_bytes": 403287,
    "log_sha256": (
        "8e699ac3e5926f9e88883be709c2133ffe14e65780224cdf07d68ce3957ee3a3"
    ),
    "artifact_id": 8838129332,
    "artifact_name": "vrtcore-h3-e1-recovery-30763216363-1",
    "artifact_size": 2848,
    "artifact_digest": (
        "sha256:e25db1d81ec283b9385af4b6eba06834ffadff52c3fa53d1e14ee89a53930ae9"
    ),
    "artifact_entry": "zenodo-publication.json",
    "artifact_entry_compressed_bytes": 2688,
    "artifact_entry_crc32": 0xB62880C8,
    "artifact_entry_unix_mode": 0o100600,
    "c0": "7bd0a61432b8f8ce7c867cde14b727e47c6d5495",
    "c0_parent": "53e757ebce929b40250f90a02ed2a9ec62de6217",
    "c0_tree": "22e221a80c99fa4fefb91af6f348bf1792f2a3a0",
    "c0_evidence_blob": "75c6bb4984c06ef7ae061b763b47fed4bf18b774",
    "c0_evidence_bytes": 7504,
    "c0_evidence_sha256": (
        "ba4829864e098aa961bb9796ee82e83f067a66e18cc3819e7465e3e60af9aced"
    ),
    "c1": "deb00ac782cc32080364a3c60d444db6098cd14c",
    "c1_parent": "7bd0a61432b8f8ce7c867cde14b727e47c6d5495",
    "c1_tree": "fe6d32d5c65be8a2a58cf8fb39a29c7804581733",
    "c1_evidence_blob": "0eeb82a0e5949ab987dd4a36cb225507e1b4baad",
    "c1_evidence_bytes": 8634,
    "c1_evidence_sha256": (
        "62444943f36c7896663a09649aebf97e0b7b5d0c1b11465daa392a8663b9e5db"
    ),
}

R4_INCIDENT_LOG_REQUIRED_COUNTS = {
    "VRTCORE_H3_E1_RECOVERY_BASIS=VALID": 1,
    "VRTCORE_H3_E1_RECOVERY_PREPARE=CHECKPOINTED": 1,
    "BLOCK: GitHub receipt ref response differs": 1,
    "Process completed with exit code 2.": 1,
    'test "2" = "0"': 1,
}
R4_INCIDENT_LOG_FORBIDDEN_MARKERS = (
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=PUBLISHED",
    "ZENODO_PUBLICATION_STATE=published",
)

R5_RECORD_CREATED_TIMEOUT_INCIDENT: dict[str, Any] = {
    "controller": "8db28488afa35549eea640f40f98321c1e56a4e0",
    "controller_parent": "dfcf28f9f48b5857ef3b4ef50f979d9a1979be08",
    "controller_tree": "bc733e7ab1917efe7d4145e869bcfcd2a75d9570",
    "run_id": 30766184456,
    "job_id": 91545233271,
    "run_attempt": 1,
    "log_bytes": 411666,
    "log_sha256": (
        "c6af2132d5b2414557af7fe6245dde82f74a0f30507ffc2521b04edba3fdd60e"
    ),
    "artifact_id": 8839044468,
    "artifact_name": "vrtcore-h3-e1-recovery-30766184456-1",
    "artifact_size": 6688,
    "artifact_digest": (
        "sha256:4ad87dc34479ff226e059718d8a8d9a0569ee69068c86faa7e4a01cf176fc605"
    ),
    "artifact_entry": "zenodo-publication.json",
    "artifact_entry_compressed_bytes": 6528,
    "artifact_entry_crc32": 0xF3A6D7EB,
    "artifact_entry_unix_mode": 0o100600,
    "c2": "376e869dc3504929b8913146cb29264d3ac585f3",
    "c2_parent": "deb00ac782cc32080364a3c60d444db6098cd14c",
    "c2_tree": "80602d60e138c4fab478b09b5d8a8aa75366521f",
    "c2_evidence_blob": "d81135af4a14c5fa3d67966761f473569c7d2689",
    "c2_evidence_bytes": 23415,
    "c2_evidence_sha256": (
        "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4"
    ),
    "phase": "record_created",
    "state": publish.CONSUMPTION_STATE,
    "record_id": 21763614,
    "doi": "10.5281/zenodo.21763614",
}

R5_TIMEOUT_LOG_REQUIRED_COUNTS = {
    "VRTCORE_H3_E1_RECOVERY_BASIS=VALID": 1,
    "VRTCORE_H3_E1_RECOVERY_PREPARE=CHECKPOINTED": 1,
    "BLOCK: timed out waiting for editable Zenodo metadata 21763614": 1,
    "Process completed with exit code 2.": 1,
    "Process completed with exit code 1.": 1,
}
R5_TIMEOUT_LOG_FORBIDDEN_MARKERS = (
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=PUBLISHED",
    "ZENODO_PUBLICATION_STATE=published",
)

R6_DRAFT_METADATA_INCIDENT: dict[str, Any] = {
    "controller": "eec6f14ad937e15764d28ccf4fc5afef0c198236",
    "controller_parent": "8db28488afa35549eea640f40f98321c1e56a4e0",
    "controller_tree": "020f983f6fa1498f4a9b03dc50c30f2f70d4c72e",
    "run_id": 30768765296,
    "job_id": 91552099457,
    "run_attempt": 1,
    "log_bytes": 420440,
    "log_sha256": (
        "3722516092e0d69bbbae63897fa589c903b0710e9fcd4ceb645e4a0ce8cf05b3"
    ),
    "artifact_id": 8839839720,
    "artifact_name": "vrtcore-h3-e1-recovery-30768765296-1",
    "artifact_size": 6688,
    "artifact_digest": (
        "sha256:b01f4a5ce3b55d2a5f60bf16ed37f200c65e79bc32c43f25a739a702e3b2f184"
    ),
    "artifact_entry": "zenodo-publication.json",
    "artifact_entry_compressed_bytes": 6528,
    "artifact_entry_crc32": 0xF3A6D7EB,
    "artifact_entry_unix_mode": 0o100600,
    "c2": "376e869dc3504929b8913146cb29264d3ac585f3",
    "c2_parent": "deb00ac782cc32080364a3c60d444db6098cd14c",
    "c2_tree": "80602d60e138c4fab478b09b5d8a8aa75366521f",
    "c2_evidence_blob": "d81135af4a14c5fa3d67966761f473569c7d2689",
    "c2_evidence_bytes": 23415,
    "c2_evidence_sha256": (
        "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4"
    ),
    "phase": "record_created",
    "state": publish.CONSUMPTION_STATE,
    "record_id": 21763614,
    "doi": "10.5281/zenodo.21763614",
}

R7_CREATOR_NORMALIZATION_INCIDENT: dict[str, Any] = {
    "controller": "d941ca6b792d569b2c37c571123c7524a53c33fd",
    "controller_parent": "eec6f14ad937e15764d28ccf4fc5afef0c198236",
    "controller_tree": "d1ac4b047b86a3fc8e8fa5f6263899aca45dc6cf",
    "run_id": 30771162129,
    "job_id": 91558446178,
    "run_attempt": 1,
    "log_bytes": 425694,
    "log_sha256": (
        "dc77e61deab0202064f0eaa50ddea6cb6c4c1d37735cae7764a054e9bb9c09d9"
    ),
    "artifact_id": 8840586492,
    "artifact_name": "vrtcore-h3-e1-recovery-30771162129-1",
    "artifact_size": 6688,
    "artifact_digest": (
        "sha256:f326e544d255d1de56eab22ff577fb6aa7530e666e35abaebcb83f6547af131d"
    ),
    "artifact_entry": "zenodo-publication.json",
    "artifact_entry_compressed_bytes": 6528,
    "artifact_entry_crc32": 0xF3A6D7EB,
    "artifact_entry_unix_mode": 0o100600,
    "c2": "376e869dc3504929b8913146cb29264d3ac585f3",
    "c2_parent": "deb00ac782cc32080364a3c60d444db6098cd14c",
    "c2_tree": "80602d60e138c4fab478b09b5d8a8aa75366521f",
    "c2_evidence_blob": "d81135af4a14c5fa3d67966761f473569c7d2689",
    "c2_evidence_bytes": 23415,
    "c2_evidence_sha256": (
        "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4"
    ),
    "phase": "record_created",
    "state": publish.CONSUMPTION_STATE,
    "record_id": 21763614,
    "doi": "10.5281/zenodo.21763614",
}

R8_NULL_AFFILIATION_EVIDENCE: dict[str, Any] = {
    "path": (
        "release/zenodo-corpus-proof-2026-07-28/"
        "ZENODO_CORPUS_INVENTORY.json"
    ),
    "git_blob_sha": "167373aa1760cad084f674271682dec94742d8bf",
    "bytes": 6348,
    "sha256": "4c5b1511f1d357798b1e42fd28466bd4438da5d3eca41832fc389ac61ec7d137",
    "record_ids": (
        21515074,
        21582781,
        21633411,
        21636774,
        21640160,
        21640173,
    ),
}

R6_METADATA_LOG_REQUIRED_COUNTS = {
    "VRTCORE_H3_E1_RECOVERY_BASIS=VALID": 1,
    "VRTCORE_H3_E1_RECOVERY_PREPARE=CHECKPOINTED": 1,
    "BLOCK: R6 draft metadata differs from exact C2 manifest": 1,
    "Process completed with exit code 2.": 1,
    "Process completed with exit code 1.": 1,
}
R6_METADATA_LOG_FORBIDDEN_MARKERS = (
    "VRTCORE_H3_E1_RECOVERY_PREPARE=FINALIZED",
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=ALREADY_FINALIZED",
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=PUBLISHED",
    "ZENODO_PUBLICATION_STATE=published",
    "create_paper",
    "publish_and_poll",
)
R7_CREATOR_LOG_REQUIRED_COUNTS = {
    "VRTCORE_H3_E1_RECOVERY_BASIS=VALID": 1,
    "VRTCORE_H3_E1_RECOVERY_PREPARE=CHECKPOINTED": 1,
    "BLOCK: R7 title, version, or creators differ from exact C2 identity": 1,
    "Process completed with exit code 2.": 1,
    "Process completed with exit code 1.": 1,
}
R7_CREATOR_LOG_FORBIDDEN_MARKERS = (
    "VRTCORE_H3_E1_RECOVERY_PREPARE=FINALIZED",
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=ALREADY_FINALIZED",
    "VRTCORE_H3_E1_RECOVERY_PUBLICATION=PUBLISHED",
    "ZENODO_PUBLICATION_STATE=published",
    "prepared_durable=true",
    "publish_requested",
    "publish_and_poll",
)
R5_GOVERNANCE_BOUNDARIES = (
    "PRIVILEGED_REPLAY_MARKER_REF_DELETION_NOT_PREVENTED",
    "AMBIGUOUS_MARKER_MUTATION_BLOCKS_WITHOUT_REARM",
    "R5_RUN_ATTEMPT_ONE_ONLY",
)
R6_GOVERNANCE_BOUNDARIES = (
    "R5_RUN_MUST_NOT_BE_RERUN",
    "R6_RUN_ATTEMPT_ONE_ONLY",
    "R6_RECONCILES_RECORD_21763614_WITHOUT_CREATE",
)
R7_GOVERNANCE_BOUNDARIES = (
    "R6_RUN_MUST_NOT_BE_RERUN",
    "R7_RUN_ATTEMPT_ONE_ONLY",
    "R7_CORRECTS_ONLY_MUTABLE_METADATA_ON_RECORD_21763614",
    "R7_REQUIRES_POST_PUT_METADATA_CONVERGENCE_BEFORE_FILES",
)
R8_GOVERNANCE_BOUNDARIES = (
    *R7_GOVERNANCE_BOUNDARIES,
    "R8_RUN_ATTEMPT_ONE_ONLY",
    "R8_ACCEPTS_ONLY_EXACT_CREATOR_NAME_PLUS_NULL_AFFILIATION_NORMALIZATION",
    "R8_TREATS_R7_METADATA_PUT_OUTCOME_AS_POTENTIALLY_AMBIGUOUS",
    "R8_SKIPS_DUPLICATE_METADATA_PUT_AFTER_DOUBLE_READ_CONVERGENCE",
)

INCIDENT_LOG_REQUIRED_COUNTS = {
    "BLOCK: GitHub Git-Data API rejected GET (HTTP 404)": 1,
    "publisher failed before durable V2 recovery evidence; no retry": 2,
    "status=2": 2,
    "prepared=false": 1,
}
INCIDENT_LOG_FORBIDDEN_MARKERS = (
    "ZENODO_PUBLICATION_STATE=published",
    "create_paper",
    "publish_and_poll",
)

EXPECTED_E1_DELTA = (
    "A\t.github/workflows/qikvrt_vrtcore_zenodo_publish.yml",
    "M\tREPOSITORY_FILE_MANIFEST.json",
    "M\tREPOSITORY_FILE_MANIFEST.json.sha256",
    "M\tSHA256SUMS.txt",
    "M\ttests/test_vrtcore_zenodo_publication_controls.py",
)
CHECKPOINT_PHASES = (
    "authorization_consumed",
    "create_requested",
    "record_created",
    "prepared",
    "publish_requested",
)
REF_RECONCILIATION_DELAYS_SECONDS = (0.25, 1.0, 2.0, 4.0, 8.0)


class AmbiguousRefMutation(RuntimeError):
    """The single permitted ref mutation may or may not have reached GitHub."""


class CheckpointStore(Protocol):
    """Persistence boundary installed around the unchanged E1 publisher."""

    def persist_and_readback(
        self,
        evidence_path: pathlib.Path,
        phase: str,
    ) -> str:
        """Persist one phase and return its exact receipt commit."""


def _load_pinned_e1_module(
    root: pathlib.Path,
    relative: str,
    name: str,
    *,
    blob: str,
    size: int,
    sha256: str,
) -> Any:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        _fail("pinned E1 module path is not a regular file")
    raw = path.read_bytes()
    if (
        len(raw) != size
        or hashlib.sha256(raw).hexdigest() != sha256
        or _git_blob_sha(raw) != blob
    ):
        _fail("loaded E1 module bytes differ from their exact pin")
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        _fail("cannot construct the pinned E1 module specification")
    module = importlib.util.module_from_spec(specification)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        specification.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    loaded_path = pathlib.Path(str(module.__file__)).resolve()
    if loaded_path != path.resolve():
        _fail("loaded module did not originate in the E1 worktree")
    return module


def _load_e1_publisher(root: pathlib.Path) -> Any:
    """Load the exact pinned E1 publisher and both transitive local modules."""
    actions = _load_pinned_e1_module(
        root,
        "tools/qikvrt_zenodo_actions.py",
        "qikvrt_vrtcore_h3_e1_pinned_actions",
        blob=EXPECTED["e1_actions_blob"],
        size=EXPECTED["e1_actions_bytes"],
        sha256=EXPECTED["e1_actions_sha256"],
    )
    proof = _load_pinned_e1_module(
        root,
        "tools/qikvrt_zenodo_machine_proof.py",
        "qikvrt_vrtcore_h3_e1_pinned_machine_proof",
        blob=EXPECTED["e1_machine_proof_blob"],
        size=EXPECTED["e1_machine_proof_bytes"],
        sha256=EXPECTED["e1_machine_proof_sha256"],
    )
    module = _load_pinned_e1_module(
        root,
        "tools/qikvrt_zenodo_publish.py",
        "qikvrt_vrtcore_h3_e1_pinned_publisher",
        blob=EXPECTED["e1_publisher_blob"],
        size=EXPECTED["e1_publisher_bytes"],
        sha256=EXPECTED["e1_publisher_sha256"],
    )
    module.zenodo = actions
    module.machine_proof = proof
    if actions.ZenodoError not in _ZENODO_ERROR_TYPES:
        _ZENODO_ERROR_TYPES.append(actions.ZenodoError)
    return module


def _fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    raise SystemExit("BLOCK: " + message)


def _exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        _fail(where + " keys differ")


def _read_json(path: pathlib.Path, maximum: int = 2 * 1024 * 1024) -> dict[str, Any]:
    try:
        if not path.is_file() or path.is_symlink():
            _fail("recovery JSON is not a regular file")
        raw = path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read recovery JSON: {exc}")
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
    """Validate every incident, execution, and non-rebinding control value."""
    required_top = {
        "_license",
        "schema",
        "repository",
        "profile",
        "e1",
        "e1_parent",
        "e1_tree",
        "publication_ref",
        "recovery_ref",
        "run_id",
        "job_id",
        "tag_object",
        "initial_phase",
        "recovery_mode",
        "job_log_sha256",
        "failure_boundary",
        "original_execution",
        "failed_run",
        "remote_consumption",
        "remote_state_at_recovery_design",
        "recovery_contract",
        "controller",
        "claims",
    }
    _exact_keys(value, required_top, "H3 recovery basis")
    for key in (
        "repository",
        "e1",
        "e1_parent",
        "e1_tree",
        "publication_ref",
        "recovery_ref",
        "run_id",
        "job_id",
        "tag_object",
        "initial_phase",
        "recovery_mode",
        "job_log_sha256",
        "failure_boundary",
    ):
        if value.get(key) != EXPECTED[key]:
            _fail("H3 recovery basis " + key + " differs")
    if value.get("schema") != "qikvrt_vrtcore_h3_e1_recovery_basis_v1":
        _fail("H3 recovery basis schema differs")
    if value.get("profile") != "h3":
        _fail("H3 recovery basis profile differs")
    original = value.get("original_execution")
    failed = value.get("failed_run")
    remote = value.get("remote_consumption")
    state = value.get("remote_state_at_recovery_design")
    contract = value.get("recovery_contract")
    controller = value.get("controller")
    claims = value.get("claims")
    if not all(
        isinstance(item, dict)
        for item in (original, failed, remote, state, contract, controller, claims)
    ):
        _fail("H3 recovery basis nested controls differ")
    assert isinstance(original, dict)
    assert isinstance(failed, dict)
    assert isinstance(remote, dict)
    assert isinstance(state, dict)
    assert isinstance(contract, dict)
    assert isinstance(controller, dict)
    assert isinstance(claims, dict)
    _exact_keys(
        original,
        {
            "commit",
            "sole_parent",
            "tree",
            "publication_ref",
            "publisher",
            "publisher_dependencies",
            "workflow",
            "exact_parent_delta",
        },
        "H3 recovery original execution",
    )
    _exact_keys(
        failed,
        {
            "run_id",
            "run_attempt",
            "job_id",
            "conclusion",
            "decoded_utf8_job_log",
            "artifact_inventory_count",
            "observed_boundary",
        },
        "H3 recovery failed run",
    )
    _exact_keys(
        contract,
        {
            "new_authorization",
            "replacement_nonce",
            "authorization_rebinding",
            "initial_phase",
            "existing_tag_recovery_mode",
            "remote_checkpoint_before_first_create",
            "remote_checkpoint_before_publish",
            "checkpoint_phases",
            "final_phase",
            "final_storage_ref",
        },
        "H3 recovery contract",
    )
    _exact_keys(
        controller,
        {
            "workflow_path",
            "trigger_branch",
            "expected_parent_placeholder",
            "trigger_commit_delta",
        },
        "H3 recovery controller",
    )
    publisher = original.get("publisher")
    publisher_dependencies = original.get("publisher_dependencies")
    workflow = original.get("workflow")
    log = failed.get("decoded_utf8_job_log")
    boundary = failed.get("observed_boundary")
    if not all(isinstance(item, dict) for item in (publisher, workflow, log, boundary)):
        _fail("H3 recovery basis exact evidence descriptions differ")
    if (
        original.get("commit") != EXPECTED["e1"]
        or original.get("sole_parent") != EXPECTED["e1_parent"]
        or original.get("tree") != EXPECTED["e1_tree"]
        or original.get("publication_ref") != EXPECTED["publication_ref"]
        or original.get("exact_parent_delta") != list(EXPECTED_E1_DELTA)
        or publisher
        != {
            "path": "tools/qikvrt_zenodo_publish.py",
            "git_blob_sha1": EXPECTED["e1_publisher_blob"],
            "bytes": EXPECTED["e1_publisher_bytes"],
            "sha256": EXPECTED["e1_publisher_sha256"],
        }
        or publisher_dependencies
        != [
            {
                "path": "tools/qikvrt_zenodo_actions.py",
                "git_blob_sha1": EXPECTED["e1_actions_blob"],
                "bytes": EXPECTED["e1_actions_bytes"],
                "sha256": EXPECTED["e1_actions_sha256"],
            },
            {
                "path": "tools/qikvrt_zenodo_machine_proof.py",
                "git_blob_sha1": EXPECTED["e1_machine_proof_blob"],
                "bytes": EXPECTED["e1_machine_proof_bytes"],
                "sha256": EXPECTED["e1_machine_proof_sha256"],
            },
        ]
        or workflow
        != {
            "path": ".github/workflows/qikvrt_vrtcore_zenodo_publish.yml",
            "git_blob_sha1": EXPECTED["e1_workflow_blob"],
            "bytes": EXPECTED["e1_workflow_bytes"],
            "sha256": EXPECTED["e1_workflow_sha256"],
        }
    ):
        _fail("H3 recovery basis original execution differs")
    if (
        failed.get("run_id") != EXPECTED["run_id"]
        or failed.get("run_attempt") != 1
        or failed.get("job_id") != EXPECTED["job_id"]
        or failed.get("conclusion") != "failure"
        or log
        != {
            "bytes": EXPECTED["job_log_bytes"],
            "sha256": EXPECTED["job_log_sha256"],
        }
        or failed.get("artifact_inventory_count") != 0
        or boundary
        != {
            "post_create_ref_readback_http_status": 404,
            "publisher_status": 2,
            "durable_v2_evidence": False,
            "retry_performed": False,
            "prepared_output": False,
            "zenodo_api_call_started": False,
        }
    ):
        _fail("H3 recovery basis failed-run boundary differs")
    if remote != {
        "tag_object": EXPECTED["tag_object"],
        "object_type": "tag",
        "target_commit": EXPECTED["e1"],
        "ref_source": "owner_authorization.remote_consumption_ref",
        "new_tag_write_allowed": False,
    }:
        _fail("H3 recovery basis consumption tag differs")
    if state != {
        "publication_ref_head": EXPECTED["e1"],
        "recovery_ref": EXPECTED["recovery_ref"],
        "recovery_ref_present": False,
        "v2_evidence_present": False,
    }:
        _fail("H3 recovery basis remote state differs")
    if (
        contract.get("new_authorization") is not False
        or contract.get("replacement_nonce") is not False
        or contract.get("authorization_rebinding") is not False
        or contract.get("initial_phase") != EXPECTED["initial_phase"]
        or contract.get("existing_tag_recovery_mode") != EXPECTED["recovery_mode"]
        or contract.get("remote_checkpoint_before_first_create") is not True
        or contract.get("remote_checkpoint_before_publish") is not True
        or contract.get("checkpoint_phases") != list(CHECKPOINT_PHASES)
        or contract.get("final_phase") != "public_verified"
        or contract.get("final_storage_ref") != EXPECTED["publication_ref"]
    ):
        _fail("H3 recovery basis checkpoint contract differs")
    if (
        controller.get("workflow_path")
        != ".github/workflows/qikvrt_vrtcore_h3_e1_recovery.yml"
        or controller.get("trigger_branch") != EXPECTED["trigger_branch"]
        or controller.get("expected_parent_placeholder")
        != EXPECTED["controller_parent_placeholder"]
        or controller.get("trigger_commit_delta")
        != [
            "M\t.github/workflows/qikvrt_vrtcore_h3_e1_recovery.yml",
            "M\tREPOSITORY_FILE_MANIFEST.json",
            "M\tREPOSITORY_FILE_MANIFEST.json.sha256",
            "M\tSHA256SUMS.txt",
        ]
    ):
        _fail("H3 recovery basis controller contract differs")
    if claims != {
        "zenodo_publication_completed": False,
        "github_receipt_persisted": False,
        "effect_ack_done": False,
        "final_pass": False,
    }:
        _fail("H3 recovery basis claims differ")
    return dict(value)


def _git(
    root: pathlib.Path,
    *arguments: str,
    accepted: frozenset[int] = frozenset({0}),
    credential_free: bool = False,
    environment: Mapping[str, str] | None = None,
) -> tuple[int, bytes]:
    child_environment = dict(os.environ if environment is None else environment)
    for key in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ZENODO_ACCESS_TOKEN",
    ):
        child_environment.pop(key, None)
    if credential_free:
        for key in (
            "GIT_ASKPASS",
            "SSH_ASKPASS",
        ):
            child_environment.pop(key, None)
        child_environment["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=child_environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in accepted:
        _fail("recovery Git command failed")
    return result.returncode, result.stdout


def validate_e1_repository_objects(
    root: pathlib.Path,
    basis: Mapping[str, Any],
) -> None:
    """Prove the locally available E1 commit, tree, blobs, and five-path delta."""
    validate_recovery_basis(dict(basis))
    e1 = str(basis["e1"])
    parent = str(basis["e1_parent"])
    _status, resolved = _git(root, "rev-parse", "--verify", f"{e1}^{{commit}}")
    if resolved.decode("ascii").strip() != e1:
        _fail("local E1 object identity differs")
    _status, parents = _git(root, "show", "-s", "--format=%P", e1)
    if parents.decode("ascii").strip() != parent:
        _fail("E1 sole parent differs")
    _status, tree = _git(root, "rev-parse", "--verify", f"{e1}^{{tree}}")
    if tree.decode("ascii").strip() != basis["e1_tree"]:
        _fail("E1 tree differs")
    _status, delta = _git(
        root,
        "diff",
        "--name-status",
        "--no-renames",
        parent,
        e1,
        "--",
    )
    if tuple(delta.decode("utf-8").splitlines()) != EXPECTED_E1_DELTA:
        _fail("E1 exact parent delta differs")
    for path, blob_key, bytes_key, digest_key in (
        (
            "tools/qikvrt_zenodo_publish.py",
            "e1_publisher_blob",
            "e1_publisher_bytes",
            "e1_publisher_sha256",
        ),
        (
            ".github/workflows/qikvrt_vrtcore_zenodo_publish.yml",
            "e1_workflow_blob",
            "e1_workflow_bytes",
            "e1_workflow_sha256",
        ),
        (
            "tools/qikvrt_zenodo_actions.py",
            "e1_actions_blob",
            "e1_actions_bytes",
            "e1_actions_sha256",
        ),
        (
            "tools/qikvrt_zenodo_machine_proof.py",
            "e1_machine_proof_blob",
            "e1_machine_proof_bytes",
            "e1_machine_proof_sha256",
        ),
    ):
        _status, blob = _git(root, "rev-parse", "--verify", f"{e1}:{path}")
        _status, raw = _git(root, "show", f"{e1}:{path}")
        if (
            blob.decode("ascii").strip() != EXPECTED[blob_key]
            or len(raw) != EXPECTED[bytes_key]
            or hashlib.sha256(raw).hexdigest() != EXPECTED[digest_key]
        ):
            _fail("E1 pinned executable blob differs for " + path)


class _NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


class GitHubAPI:
    """Pinned, bounded GitHub Git-Data REST transport with redacted errors."""

    def __init__(
        self,
        token: str,
        *,
        transport: Callable[..., tuple[int, dict[str, Any]]] | None = None,
        raw_transport: Callable[[str, int], bytes] | None = None,
    ) -> None:
        if len(token) < 20 or any(character.isspace() for character in token):
            _fail("GITHUB_TOKEN is missing or structurally invalid")
        self._token = token
        self._transport = transport
        self._raw_transport = raw_transport

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        accept: tuple[int, ...] = (200,),
        allow_ambiguous_transport: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        if self._transport is not None:
            return self._transport(
                method,
                path,
                payload=payload,
                accept=accept,
                allow_ambiguous_transport=allow_ambiguous_transport,
            )
        prefix = "/repos/Goldkelch/qik-vrt/"
        if (
            not path.startswith(prefix)
            or any(character in path for character in ("\x00", "\r", "\n", "?", "#"))
        ):
            _fail("GitHub API path escaped the pinned repository")
        if method not in {"GET", "POST", "PATCH"}:
            _fail("unsupported GitHub Git-Data method")
        body = None if payload is None else zenodo._json_bytes(dict(payload))
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self._token,
                "User-Agent": "qik-vrt-h3-e1-recovery",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        opener = urllib.request.build_opener(_NoCredentialRedirect())
        try:
            response: Any = opener.open(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError) as exc:
            if allow_ambiguous_transport and method in {"POST", "PATCH"}:
                raise AmbiguousRefMutation from exc
            _fail("GitHub Git-Data transport failed")
        try:
            status = int(response.status)
            raw = response.read(2 * 1024 * 1024 + 1)
        finally:
            response.close()
        if len(raw) > 2 * 1024 * 1024:
            _fail("GitHub Git-Data response exceeds its byte limit")
        if status >= 500 and allow_ambiguous_transport and method in {"POST", "PATCH"}:
            raise AmbiguousRefMutation
        if status not in accept:
            _fail(f"GitHub Git-Data API rejected {method} (HTTP {status})")
        if not raw:
            return status, {}
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            _fail("GitHub Git-Data API returned invalid JSON")
        if not isinstance(value, dict):
            _fail("GitHub Git-Data API returned a non-object")
        if self._token.encode("utf-8") in zenodo._json_bytes(value):
            _fail("GitHub Git-Data response contained its bearer credential")
        return status, value

    @staticmethod
    def _validate_log_redirect(url: str) -> None:
        if len(url) > 16384 or any(
            character in url for character in ("\x00", "\r", "\n")
        ):
            _fail("GitHub Actions log redirect is structurally unsafe")
        parts = urllib.parse.urlsplit(url)
        hostname = (parts.hostname or "").lower()
        allowed = (
            hostname == "pipelines.actions.githubusercontent.com"
            or hostname.endswith(".actions.githubusercontent.com")
            or hostname.endswith(".blob.core.windows.net")
            or hostname.endswith(".githubusercontent.com")
        )
        try:
            port = parts.port
        except ValueError:
            _fail("GitHub Actions log redirect port differs")
        if (
            parts.scheme != "https"
            or not allowed
            or parts.username is not None
            or parts.password is not None
            or port not in {None, 443}
            or not parts.path.startswith("/")
            or parts.fragment
        ):
            _fail("GitHub Actions log redirect escaped its credential-free allowlist")

    def request_bytes(self, path: str, maximum: int) -> bytes:
        """Read one bounded Actions object without forwarding credentials."""
        allowed = {
            (
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(EXPECTED["job_id"])
                + "/logs"
            ): EXPECTED["job_log_bytes"],
            (
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(R4_UNSENT_CREATE_INCIDENT["job_id"])
                + "/logs"
            ): R4_UNSENT_CREATE_INCIDENT["log_bytes"],
            (
                "/repos/Goldkelch/qik-vrt/actions/artifacts/"
                + str(R4_UNSENT_CREATE_INCIDENT["artifact_id"])
                + "/zip"
            ): R4_UNSENT_CREATE_INCIDENT["artifact_size"],
            (
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(R5_RECORD_CREATED_TIMEOUT_INCIDENT["job_id"])
                + "/logs"
            ): R5_RECORD_CREATED_TIMEOUT_INCIDENT["log_bytes"],
            (
                "/repos/Goldkelch/qik-vrt/actions/artifacts/"
                + str(R5_RECORD_CREATED_TIMEOUT_INCIDENT["artifact_id"])
                + "/zip"
            ): R5_RECORD_CREATED_TIMEOUT_INCIDENT["artifact_size"],
            (
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(R6_DRAFT_METADATA_INCIDENT["job_id"])
                + "/logs"
            ): R6_DRAFT_METADATA_INCIDENT["log_bytes"],
            (
                "/repos/Goldkelch/qik-vrt/actions/artifacts/"
                + str(R6_DRAFT_METADATA_INCIDENT["artifact_id"])
                + "/zip"
            ): R6_DRAFT_METADATA_INCIDENT["artifact_size"],
            (
                "/repos/Goldkelch/qik-vrt/actions/jobs/"
                + str(R7_CREATOR_NORMALIZATION_INCIDENT["job_id"])
                + "/logs"
            ): R7_CREATOR_NORMALIZATION_INCIDENT["log_bytes"],
            (
                "/repos/Goldkelch/qik-vrt/actions/artifacts/"
                + str(R7_CREATOR_NORMALIZATION_INCIDENT["artifact_id"])
                + "/zip"
            ): R7_CREATOR_NORMALIZATION_INCIDENT["artifact_size"],
        }
        if path not in allowed or maximum != allowed[path]:
            _fail("GitHub Actions raw-read boundary differs")
        if self._raw_transport is not None:
            raw = self._raw_transport(path, maximum)
            if not isinstance(raw, bytes) or len(raw) > maximum:
                _fail("GitHub Actions raw transport differs")
            return raw

        api_url = "https://api.github.com" + path
        request = urllib.request.Request(
            api_url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self._token,
                "User-Agent": "qik-vrt-h3-e1-recovery",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        no_redirect = urllib.request.build_opener(_NoCredentialRedirect())
        try:
            response: Any = no_redirect.open(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError):
            _fail("GitHub Actions log transport failed")
        try:
            status = int(response.status)
            location = response.headers.get("Location")
            response.read(1)
        finally:
            response.close()
        if status not in {301, 302, 303, 307, 308} or not isinstance(location, str):
            _fail("GitHub Actions log endpoint did not return a signed redirect")

        # Follow at most three redirects without Authorization, Cookie, or any
        # other credential-bearing header.  Every origin remains allowlisted.
        url = location
        for _redirect in range(3):
            self._validate_log_redirect(url)
            unsigned_request = urllib.request.Request(
                url,
                method="GET",
                headers={"User-Agent": "qik-vrt-h3-e1-recovery"},
            )
            try:
                unsigned: Any = no_redirect.open(unsigned_request, timeout=30)
            except urllib.error.HTTPError as exc:
                unsigned = exc
            except (OSError, urllib.error.URLError):
                _fail("credential-free GitHub Actions log download failed")
            try:
                unsigned_status = int(unsigned.status)
                if unsigned_status in {301, 302, 303, 307, 308}:
                    next_url = unsigned.headers.get("Location")
                    unsigned.read(1)
                    if not isinstance(next_url, str):
                        _fail("GitHub Actions log redirect lacks a location")
                    url = urllib.parse.urljoin(url, next_url)
                    continue
                if unsigned_status != 200:
                    _fail("GitHub Actions log download status differs")
                raw = unsigned.read(maximum + 1)
            finally:
                unsigned.close()
            if len(raw) > maximum:
                _fail("GitHub Actions job log exceeds its exact byte bound")
            if self._token.encode("utf-8") in raw:
                _fail("GitHub Actions job log contained its bearer credential")
            return raw
        _fail("GitHub Actions log redirect chain exceeds its bound")


def _call_api(
    api: Any,
    method: str,
    path: str,
    *,
    payload: Mapping[str, Any] | None = None,
    accept: tuple[int, ...] = (200,),
    allow_ambiguous_transport: bool = False,
) -> tuple[int, dict[str, Any]]:
    callable_value = api.request if hasattr(api, "request") else api
    return callable_value(
        method,
        path,
        payload=payload,
        accept=accept,
        allow_ambiguous_transport=allow_ambiguous_transport,
    )


def _call_api_bytes(api: Any, path: str, maximum: int) -> bytes:
    callable_value = getattr(api, "request_bytes", None)
    if callable_value is None:
        _fail("GitHub Actions raw transport is unavailable")
    raw = callable_value(path, maximum)
    if not isinstance(raw, bytes) or len(raw) > maximum:
        _fail("GitHub Actions raw response differs")
    return raw


def verify_historical_incident(
    api: Any,
    basis: Mapping[str, Any],
) -> None:
    """Re-observe the exact failed E1 run before reconstructing its receipt.

    The decoded log is held only in memory, is never printed or persisted, and
    is reduced to exact byte/digest and marker-count assertions.
    """
    validate_recovery_basis(dict(basis))
    base_run_path = (
        "/repos/Goldkelch/qik-vrt/actions/runs/" + str(EXPECTED["run_id"])
    )
    run_path = base_run_path + "/attempts/1"
    _status, run = _call_api(api, "GET", run_path, accept=(200,))
    repository = run.get("repository")
    head_repository = run.get("head_repository")
    if (
        run.get("id") != EXPECTED["run_id"]
        or run.get("run_attempt") != 1
        or run.get("head_sha") != EXPECTED["e1"]
        or run.get("head_branch")
        != EXPECTED["publication_ref"].removeprefix("refs/heads/")
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != EXPECTED["repository"]
    ):
        _fail("historical E1 workflow run differs")

    job_path = (
        "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(EXPECTED["job_id"])
    )
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    expected_run_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
        + str(EXPECTED["run_id"])
    )
    if (
        job.get("id") != EXPECTED["job_id"]
        or job.get("run_id") != EXPECTED["run_id"]
        or job.get("run_attempt") != 1
        or job.get("head_sha") != EXPECTED["e1"]
        or job.get("status") != "completed"
        or job.get("conclusion") != "failure"
        or job.get("run_url") != expected_run_url
    ):
        _fail("historical E1 workflow job differs")

    artifacts_path = base_run_path + "/artifacts"
    _status, artifacts = _call_api(api, "GET", artifacts_path, accept=(200,))
    if artifacts.get("total_count") != 0 or artifacts.get("artifacts") != []:
        _fail("historical E1 run artifact inventory differs")

    log_path = job_path + "/logs"
    raw = _call_api_bytes(api, log_path, EXPECTED["job_log_bytes"])
    if (
        len(raw) != EXPECTED["job_log_bytes"]
        or hashlib.sha256(raw).hexdigest() != EXPECTED["job_log_sha256"]
    ):
        _fail("historical E1 decoded job log identity differs")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail("historical E1 job log is not exact UTF-8")
    for marker, count in INCIDENT_LOG_REQUIRED_COUNTS.items():
        if decoded.count(marker) != count:
            _fail("historical E1 job log required marker count differs")
    if any(marker in decoded for marker in INCIDENT_LOG_FORBIDDEN_MARKERS):
        _fail("historical E1 job log crossed the claimed effect boundary")


def _verify_pinned_incident_artifact_evidence(
    api: Any,
    root: pathlib.Path,
    incident: Mapping[str, Any],
    *,
    evidence_prefix: str,
    expected_phase: str,
    expected_state: str,
) -> None:
    """Bind one bounded Actions artifact exactly to one receipt checkpoint."""
    artifact_path = (
        "/repos/Goldkelch/qik-vrt/actions/artifacts/"
        + str(incident["artifact_id"])
        + "/zip"
    )
    raw = _call_api_bytes(api, artifact_path, int(incident["artifact_size"]))
    expected_digest = str(incident["artifact_digest"])
    if (
        len(raw) != incident["artifact_size"]
        or not expected_digest.startswith("sha256:")
        or hashlib.sha256(raw).hexdigest()
        != expected_digest.removeprefix("sha256:")
    ):
        _fail("historical recovery artifact ZIP identity differs")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), mode="r") as archive:
            entries = archive.infolist()
            if archive.comment != b"" or len(entries) != 1:
                _fail("historical recovery artifact ZIP inventory differs")
            entry = entries[0]
            unix_mode = entry.external_attr >> 16
            if (
                entry.filename != incident["artifact_entry"]
                or entry.orig_filename != incident["artifact_entry"]
                or entry.is_dir()
                or entry.create_system != 3
                or unix_mode != incident["artifact_entry_unix_mode"]
                or entry.file_size
                != incident[evidence_prefix + "_evidence_bytes"]
                or entry.compress_size
                != incident["artifact_entry_compressed_bytes"]
                or entry.CRC != incident["artifact_entry_crc32"]
                or entry.compress_type != zipfile.ZIP_DEFLATED
                or entry.flag_bits & 0x1
                or entry.extra != b""
                or entry.comment != b""
            ):
                _fail("historical recovery artifact ZIP entry differs")
            evidence = archive.read(entry)
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, NotImplementedError):
        _fail("historical recovery artifact ZIP is invalid")
    commit = str(incident[evidence_prefix])
    _status, expected = _git(
        root,
        "show",
        f"{commit}:{EVIDENCE_RELATIVE.as_posix()}",
    )
    _status, blob = _git(
        root,
        "rev-parse",
        "--verify",
        f"{commit}:{EVIDENCE_RELATIVE.as_posix()}",
    )
    if (
        evidence != expected
        or blob.decode("ascii").strip()
        != incident[evidence_prefix + "_evidence_blob"]
        or len(evidence) != incident[evidence_prefix + "_evidence_bytes"]
        or hashlib.sha256(evidence).hexdigest()
        != incident[evidence_prefix + "_evidence_sha256"]
    ):
        _fail("historical recovery artifact evidence differs from its checkpoint")
    try:
        value = json.loads(evidence.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("historical recovery artifact evidence JSON is invalid")
    expected_record = incident.get("record_id")
    expected_doi = incident.get("doi")
    if (
        not isinstance(value, dict)
        or value.get("phase") != expected_phase
        or value.get("state") != expected_state
        or (
            expected_record is None
            and ("record_id" in value or "doi" in value)
        )
        or (
            expected_record is not None
            and (
                value.get("record_id") != expected_record
                or value.get("doi") != expected_doi
            )
        )
    ):
        _fail("historical recovery artifact crossed its evidence boundary")


def _verify_r4_artifact_evidence(api: Any, root: pathlib.Path) -> None:
    """Download the bounded R4 artifact and bind its only entry exactly to C1."""
    _verify_pinned_incident_artifact_evidence(
        api,
        root,
        R4_UNSENT_CREATE_INCIDENT,
        evidence_prefix="c1",
        expected_phase="create_requested",
        expected_state=publish.CONSUMPTION_STATE,
    )


def _verify_r5_artifact_evidence(api: Any, root: pathlib.Path) -> None:
    """Bind the sole R5 artifact exactly to record-created checkpoint C2."""
    _verify_pinned_incident_artifact_evidence(
        api,
        root,
        R5_RECORD_CREATED_TIMEOUT_INCIDENT,
        evidence_prefix="c2",
        expected_phase="record_created",
        expected_state=publish.CONSUMPTION_STATE,
    )


def _verify_r6_artifact_evidence(api: Any, root: pathlib.Path) -> None:
    """Prove that R6 uploaded only the unchanged record-created C2 receipt."""
    _verify_pinned_incident_artifact_evidence(
        api,
        root,
        R6_DRAFT_METADATA_INCIDENT,
        evidence_prefix="c2",
        expected_phase="record_created",
        expected_state=publish.CONSUMPTION_STATE,
    )


def _verify_r7_artifact_evidence(api: Any, root: pathlib.Path) -> None:
    """Prove that R7 also uploaded only the unchanged C2 checkpoint."""
    _verify_pinned_incident_artifact_evidence(
        api,
        root,
        R7_CREATOR_NORMALIZATION_INCIDENT,
        evidence_prefix="c2",
        expected_phase="record_created",
        expected_state=publish.CONSUMPTION_STATE,
    )


def verify_historical_r4_unsent_create_incident(
    api: Any,
    root: pathlib.Path,
) -> None:
    """Bind the one R4 failure that advanced C0 to C1 before any Zenodo create.

    The R4 log does not expose a Python traceback.  R5 therefore protects both
    possible response-validation sites and treats the exact run, job, artifact
    inventory, and decoded log as one indivisible read-only incident record.
    """
    incident = R4_UNSENT_CREATE_INCIDENT
    base_run_path = (
        "/repos/Goldkelch/qik-vrt/actions/runs/" + str(incident["run_id"])
    )
    _status, run = _call_api(
        api,
        "GET",
        base_run_path + "/attempts/1",
        accept=(200,),
    )
    repository = run.get("repository")
    head_repository = run.get("head_repository")
    if (
        run.get("id") != incident["run_id"]
        or run.get("run_attempt") != incident["run_attempt"]
        or run.get("event") != "push"
        or run.get("head_sha") != incident["controller"]
        or run.get("head_branch") != EXPECTED["trigger_branch"]
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != EXPECTED["repository"]
    ):
        _fail("historical R4 workflow run differs")

    job_path = (
        "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(incident["job_id"])
    )
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    expected_run_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
        + str(incident["run_id"])
    )
    if (
        job.get("id") != incident["job_id"]
        or job.get("run_id") != incident["run_id"]
        or job.get("run_attempt") != incident["run_attempt"]
        or job.get("head_sha") != incident["controller"]
        or job.get("status") != "completed"
        or job.get("conclusion") != "failure"
        or job.get("run_url") != expected_run_url
    ):
        _fail("historical R4 workflow job differs")

    _status, artifacts = _call_api(
        api,
        "GET",
        base_run_path + "/artifacts",
        accept=(200,),
    )
    items = artifacts.get("artifacts")
    if (
        artifacts.get("total_count") != 1
        or not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("id") != incident["artifact_id"]
        or items[0].get("name") != incident["artifact_name"]
        or items[0].get("size_in_bytes") != incident["artifact_size"]
        or items[0].get("digest") != incident["artifact_digest"]
        or items[0].get("expired") is not False
    ):
        _fail("historical R4 workflow artifact inventory differs")

    raw = _call_api_bytes(
        api,
        job_path + "/logs",
        int(incident["log_bytes"]),
    )
    if (
        len(raw) != incident["log_bytes"]
        or hashlib.sha256(raw).hexdigest() != incident["log_sha256"]
        or not raw.startswith(b"\xef\xbb\xbf")
    ):
        _fail("historical R4 decoded job log identity differs")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("historical R4 job log is not exact UTF-8 with BOM")
    for marker, count in R4_INCIDENT_LOG_REQUIRED_COUNTS.items():
        if decoded.count(marker) != count:
            _fail("historical R4 job log required marker count differs")
    if any(marker in decoded for marker in R4_INCIDENT_LOG_FORBIDDEN_MARKERS):
        _fail("historical R4 job log crossed the claimed effect boundary")
    _verify_r4_artifact_evidence(api, root)


def verify_historical_r5_record_created_timeout(
    api: Any,
    root: pathlib.Path,
) -> None:
    """Bind the exact R5 timeout after C2 and before public verification."""
    incident = R5_RECORD_CREATED_TIMEOUT_INCIDENT
    base_run_path = (
        "/repos/Goldkelch/qik-vrt/actions/runs/" + str(incident["run_id"])
    )
    _status, run = _call_api(
        api,
        "GET",
        base_run_path + "/attempts/1",
        accept=(200,),
    )
    repository = run.get("repository")
    head_repository = run.get("head_repository")
    if (
        run.get("id") != incident["run_id"]
        or run.get("run_attempt") != incident["run_attempt"]
        or run.get("event") != "push"
        or run.get("head_sha") != incident["controller"]
        or run.get("head_branch") != EXPECTED["trigger_branch"]
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != EXPECTED["repository"]
    ):
        _fail("historical R5 workflow run differs")

    job_path = (
        "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(incident["job_id"])
    )
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    expected_run_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
        + str(incident["run_id"])
    )
    if (
        job.get("id") != incident["job_id"]
        or job.get("run_id") != incident["run_id"]
        or job.get("run_attempt") != incident["run_attempt"]
        or job.get("head_sha") != incident["controller"]
        or job.get("status") != "completed"
        or job.get("conclusion") != "failure"
        or job.get("run_url") != expected_run_url
    ):
        _fail("historical R5 workflow job differs")

    _status, artifacts = _call_api(
        api,
        "GET",
        base_run_path + "/artifacts",
        accept=(200,),
    )
    items = artifacts.get("artifacts")
    if (
        artifacts.get("total_count") != 1
        or not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("id") != incident["artifact_id"]
        or items[0].get("name") != incident["artifact_name"]
        or items[0].get("size_in_bytes") != incident["artifact_size"]
        or items[0].get("digest") != incident["artifact_digest"]
        or items[0].get("expired") is not False
    ):
        _fail("historical R5 workflow artifact inventory differs")

    raw = _call_api_bytes(
        api,
        job_path + "/logs",
        int(incident["log_bytes"]),
    )
    if (
        len(raw) != incident["log_bytes"]
        or hashlib.sha256(raw).hexdigest() != incident["log_sha256"]
        or not raw.startswith(b"\xef\xbb\xbf")
    ):
        _fail("historical R5 decoded job log identity differs")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("historical R5 job log is not exact UTF-8 with BOM")
    for marker, count in R5_TIMEOUT_LOG_REQUIRED_COUNTS.items():
        if decoded.count(marker) != count:
            _fail("historical R5 job log required marker count differs")
    if any(marker in decoded for marker in R5_TIMEOUT_LOG_FORBIDDEN_MARKERS):
        _fail("historical R5 job log crossed the public effect boundary")
    _verify_r5_artifact_evidence(api, root)


def verify_historical_r6_draft_metadata_incident(
    api: Any,
    root: pathlib.Path,
) -> None:
    """Bind the exact R6 identity-only block and unchanged C2 artifact."""
    incident = R6_DRAFT_METADATA_INCIDENT
    base_run_path = (
        "/repos/Goldkelch/qik-vrt/actions/runs/" + str(incident["run_id"])
    )
    _status, run = _call_api(
        api,
        "GET",
        base_run_path + "/attempts/1",
        accept=(200,),
    )
    repository = run.get("repository")
    head_repository = run.get("head_repository")
    if (
        run.get("id") != incident["run_id"]
        or run.get("run_attempt") != incident["run_attempt"]
        or run.get("event") != "push"
        or run.get("head_sha") != incident["controller"]
        or run.get("head_branch") != EXPECTED["trigger_branch"]
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != EXPECTED["repository"]
    ):
        _fail("historical R6 workflow run differs")

    job_path = (
        "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(incident["job_id"])
    )
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    expected_run_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
        + str(incident["run_id"])
    )
    if (
        job.get("id") != incident["job_id"]
        or job.get("run_id") != incident["run_id"]
        or job.get("run_attempt") != incident["run_attempt"]
        or job.get("head_sha") != incident["controller"]
        or job.get("status") != "completed"
        or job.get("conclusion") != "failure"
        or job.get("run_url") != expected_run_url
    ):
        _fail("historical R6 workflow job differs")

    _status, artifacts = _call_api(
        api,
        "GET",
        base_run_path + "/artifacts",
        accept=(200,),
    )
    items = artifacts.get("artifacts")
    if (
        artifacts.get("total_count") != 1
        or not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("id") != incident["artifact_id"]
        or items[0].get("name") != incident["artifact_name"]
        or items[0].get("size_in_bytes") != incident["artifact_size"]
        or items[0].get("digest") != incident["artifact_digest"]
        or items[0].get("expired") is not False
    ):
        _fail("historical R6 workflow artifact inventory differs")

    raw = _call_api_bytes(
        api,
        job_path + "/logs",
        int(incident["log_bytes"]),
    )
    if (
        len(raw) != incident["log_bytes"]
        or hashlib.sha256(raw).hexdigest() != incident["log_sha256"]
        or not raw.startswith(b"\xef\xbb\xbf")
    ):
        _fail("historical R6 decoded job log identity differs")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("historical R6 job log is not exact UTF-8 with BOM")
    for marker, count in R6_METADATA_LOG_REQUIRED_COUNTS.items():
        if decoded.count(marker) != count:
            _fail("historical R6 job log required marker count differs")
    if any(marker in decoded for marker in R6_METADATA_LOG_FORBIDDEN_MARKERS):
        _fail("historical R6 job log crossed the public effect boundary")
    _verify_r6_artifact_evidence(api, root)


def verify_historical_r7_creator_normalization_incident(
    api: Any,
    root: pathlib.Path,
) -> None:
    """Bind R7's creator-normalization block and unchanged C2 artifact."""
    incident = R7_CREATOR_NORMALIZATION_INCIDENT
    base_run_path = (
        "/repos/Goldkelch/qik-vrt/actions/runs/" + str(incident["run_id"])
    )
    _status, run = _call_api(
        api,
        "GET",
        base_run_path + "/attempts/1",
        accept=(200,),
    )
    repository = run.get("repository")
    head_repository = run.get("head_repository")
    if (
        run.get("id") != incident["run_id"]
        or run.get("run_attempt") != incident["run_attempt"]
        or run.get("event") != "push"
        or run.get("head_sha") != incident["controller"]
        or run.get("head_branch") != EXPECTED["trigger_branch"]
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_repository, dict)
        or head_repository.get("full_name") != EXPECTED["repository"]
    ):
        _fail("historical R7 workflow run differs")

    job_path = (
        "/repos/Goldkelch/qik-vrt/actions/jobs/" + str(incident["job_id"])
    )
    _status, job = _call_api(api, "GET", job_path, accept=(200,))
    expected_run_url = (
        "https://api.github.com/repos/Goldkelch/qik-vrt/actions/runs/"
        + str(incident["run_id"])
    )
    if (
        job.get("id") != incident["job_id"]
        or job.get("run_id") != incident["run_id"]
        or job.get("run_attempt") != incident["run_attempt"]
        or job.get("head_sha") != incident["controller"]
        or job.get("status") != "completed"
        or job.get("conclusion") != "failure"
        or job.get("run_url") != expected_run_url
    ):
        _fail("historical R7 workflow job differs")

    _status, artifacts = _call_api(
        api,
        "GET",
        base_run_path + "/artifacts",
        accept=(200,),
    )
    items = artifacts.get("artifacts")
    if (
        artifacts.get("total_count") != 1
        or not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("id") != incident["artifact_id"]
        or items[0].get("name") != incident["artifact_name"]
        or items[0].get("size_in_bytes") != incident["artifact_size"]
        or items[0].get("digest") != incident["artifact_digest"]
        or items[0].get("expired") is not False
    ):
        _fail("historical R7 workflow artifact inventory differs")

    raw = _call_api_bytes(
        api,
        job_path + "/logs",
        int(incident["log_bytes"]),
    )
    if (
        len(raw) != incident["log_bytes"]
        or hashlib.sha256(raw).hexdigest() != incident["log_sha256"]
        or not raw.startswith(b"\xef\xbb\xbf")
    ):
        _fail("historical R7 decoded job log identity differs")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail("historical R7 job log is not exact UTF-8 with BOM")
    for marker, count in R7_CREATOR_LOG_REQUIRED_COUNTS.items():
        if decoded.count(marker) != count:
            _fail("historical R7 job log required marker count differs")
    if any(marker in decoded for marker in R7_CREATOR_LOG_FORBIDDEN_MARKERS):
        _fail("historical R7 job log crossed the public effect boundary")
    _verify_r7_artifact_evidence(api, root)


def _verify_r4_local_object_chain(root: pathlib.Path) -> None:
    incident = R4_UNSENT_CREATE_INCIDENT
    for prefix in ("controller", "c0", "c1"):
        commit = str(incident[prefix])
        _status, resolved = _git(
            root,
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
        )
        _status, parents = _git(root, "show", "-s", "--format=%P", commit)
        _status, tree = _git(root, "rev-parse", "--verify", f"{commit}^{{tree}}")
        if (
            resolved.decode("ascii").strip() != commit
            or parents.decode("ascii").strip() != incident[prefix + "_parent"]
            or tree.decode("ascii").strip() != incident[prefix + "_tree"]
        ):
            _fail("R4 unsent-create local object chain differs")
    for prefix in ("c0", "c1"):
        commit = str(incident[prefix])
        _status, blob = _git(
            root,
            "rev-parse",
            "--verify",
            f"{commit}:{EVIDENCE_RELATIVE.as_posix()}",
        )
        _status, raw = _git(
            root,
            "show",
            f"{commit}:{EVIDENCE_RELATIVE.as_posix()}",
        )
        if (
            blob.decode("ascii").strip() != incident[prefix + "_evidence_blob"]
            or len(raw) != incident[prefix + "_evidence_bytes"]
            or hashlib.sha256(raw).hexdigest()
            != incident[prefix + "_evidence_sha256"]
        ):
            _fail("R4 unsent-create evidence identity differs")


def _verify_r5_local_object_chain(root: pathlib.Path) -> None:
    """Bind the R5 controller and its sole durable record-created checkpoint."""
    _verify_r4_local_object_chain(root)
    incident = R5_RECORD_CREATED_TIMEOUT_INCIDENT
    for prefix in ("controller", "c2"):
        commit = str(incident[prefix])
        _status, resolved = _git(
            root,
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
        )
        _status, parents = _git(root, "show", "-s", "--format=%P", commit)
        _status, tree = _git(root, "rev-parse", "--verify", f"{commit}^{{tree}}")
        if (
            resolved.decode("ascii").strip() != commit
            or parents.decode("ascii").strip() != incident[prefix + "_parent"]
            or tree.decode("ascii").strip() != incident[prefix + "_tree"]
        ):
            _fail("R5 record-created local object chain differs")
    _status, blob = _git(
        root,
        "rev-parse",
        "--verify",
        f"{incident['c2']}:{EVIDENCE_RELATIVE.as_posix()}",
    )
    _status, evidence = _git(
        root,
        "show",
        f"{incident['c2']}:{EVIDENCE_RELATIVE.as_posix()}",
    )
    if (
        blob.decode("ascii").strip() != incident["c2_evidence_blob"]
        or len(evidence) != incident["c2_evidence_bytes"]
        or hashlib.sha256(evidence).hexdigest()
        != incident["c2_evidence_sha256"]
    ):
        _fail("R5 record-created evidence object differs")


def _verify_r6_local_object_chain(root: pathlib.Path) -> None:
    """Bind R6 as the exact no-receipt successor of R5 and unchanged C2."""
    _verify_r5_local_object_chain(root)
    incident = R6_DRAFT_METADATA_INCIDENT
    commit = str(incident["controller"])
    _status, resolved = _git(
        root,
        "rev-parse",
        "--verify",
        f"{commit}^{{commit}}",
    )
    _status, parents = _git(root, "show", "-s", "--format=%P", commit)
    _status, tree = _git(root, "rev-parse", "--verify", f"{commit}^{{tree}}")
    if (
        resolved.decode("ascii").strip() != commit
        or parents.decode("ascii").strip() != incident["controller_parent"]
        or tree.decode("ascii").strip() != incident["controller_tree"]
    ):
        _fail("R6 draft-metadata local object chain differs")


def _verify_r7_local_object_chain(root: pathlib.Path) -> None:
    """Bind R7 as the exact no-receipt successor of R6 and unchanged C2."""
    _verify_r6_local_object_chain(root)
    incident = R7_CREATOR_NORMALIZATION_INCIDENT
    commit = str(incident["controller"])
    _status, resolved = _git(
        root,
        "rev-parse",
        "--verify",
        f"{commit}^{{commit}}",
    )
    _status, parents = _git(root, "show", "-s", "--format=%P", commit)
    _status, tree = _git(root, "rev-parse", "--verify", f"{commit}^{{tree}}")
    if (
        resolved.decode("ascii").strip() != commit
        or parents.decode("ascii").strip() != incident["controller_parent"]
        or tree.decode("ascii").strip() != incident["controller_tree"]
    ):
        _fail("R7 creator-normalization local object chain differs")


def _verify_r8_null_affiliation_evidence(root: pathlib.Path) -> None:
    """Pin the sole accepted server creator normalization to E1 evidence."""
    expected = R8_NULL_AFFILIATION_EVIDENCE
    relative = pathlib.PurePosixPath(str(expected["path"]))
    path = root.joinpath(*relative.parts)
    if not path.is_file() or path.is_symlink():
        _fail("R8 null-affiliation evidence path differs")
    raw = path.read_bytes()
    _status, blob = _git(
        root,
        "rev-parse",
        "--verify",
        f"{EXPECTED['e1']}:{relative.as_posix()}",
    )
    if (
        len(raw) != expected["bytes"]
        or hashlib.sha256(raw).hexdigest() != expected["sha256"]
        or blob.decode("ascii").strip() != expected["git_blob_sha"]
    ):
        _fail("R8 null-affiliation evidence bytes differ")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("R8 null-affiliation evidence is invalid JSON")
    records = value.get("records") if isinstance(value, dict) else None
    if not isinstance(records, list):
        _fail("R8 null-affiliation evidence records are absent")
    observed = tuple(
        item.get("record_id")
        for item in records
        if isinstance(item, dict)
        and item.get("creators")
        == [{"affiliation": None, "name": "Lohmann, Ingolf"}]
    )
    if observed != expected["record_ids"]:
        _fail("R8 null-affiliation evidence inventory differs")


def _head_ref_path(ref: str, *, plural: bool) -> str:
    if (
        ref not in {EXPECTED["recovery_ref"], EXPECTED["publication_ref"]}
        or not ref.startswith("refs/heads/")
    ):
        _fail("receipt target ref is outside the exact H3 allowlist")
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    return (
        "/repos/Goldkelch/qik-vrt/git/refs/" + suffix
        if plural
        else "/repos/Goldkelch/qik-vrt/git/ref/" + suffix
    )


def _validate_ref(value: Mapping[str, Any], ref: str, sha: str) -> None:
    target = value.get("object")
    if (
        value.get("ref") != ref
        or not isinstance(target, dict)
        or target.get("sha") != sha
        or target.get("type") != "commit"
    ):
        _fail("GitHub receipt ref response differs")


def _validate_ref_target_sha(value: Mapping[str, Any], sha: str) -> None:
    """Validate the authoritative target while the requested endpoint binds ref.

    GitHub has already demonstrated that a mutation/read response envelope can
    differ after the ref effect is visible.  The endpoint and expected SHA are
    therefore authoritative here; a following credential-free Git read binds
    the actual ref name, commit, and tree independently.
    """
    target = value.get("object")
    if not isinstance(target, dict) or target.get("sha") != sha:
        _fail("GitHub receipt ref target differs")


def persist_receipt_create_only_or_ff(
    api: Any,
    *,
    repository: str,
    ref: str,
    expected_old_sha: str | None,
    commit_sha: str,
) -> str:
    """Perform at most one create/FF request and bounded exact readback."""
    if repository != EXPECTED["repository"]:
        _fail("receipt repository differs")
    if HEX40.fullmatch(commit_sha) is None:
        _fail("receipt commit identity is invalid")
    if expected_old_sha is not None and HEX40.fullmatch(expected_old_sha) is None:
        _fail("receipt expected-old identity is invalid")
    singular = _head_ref_path(ref, plural=False)
    status, before = _call_api(api, "GET", singular, accept=(200, 404))
    if status == 200:
        # A prior invocation may have reached GitHub and then lost only its
        # readback.  Exact-target replay is already complete and must not emit
        # a second mutation; any different target remains a hard boundary.
        target = before.get("object")
        if isinstance(target, dict) and target.get("sha") == commit_sha:
            _validate_ref_target_sha(before, commit_sha)
            return commit_sha
    if expected_old_sha is None:
        if status != 404:
            _fail("create-only receipt ref already exists")
        operation = "create"
    else:
        if status != 200:
            _fail("fast-forward receipt ref is absent")
        _validate_ref_target_sha(before, expected_old_sha)
        operation = "update"
    mutation_status: int | None = None
    try:
        if operation == "create":
            mutation_status, _changed = _call_api(
                api,
                "POST",
                "/repos/Goldkelch/qik-vrt/git/refs",
                payload={"ref": ref, "sha": commit_sha},
                accept=(201, 409, 422),
                allow_ambiguous_transport=True,
            )
            success = 201
        else:
            mutation_status, _changed = _call_api(
                api,
                "PATCH",
                _head_ref_path(ref, plural=True),
                payload={"sha": commit_sha, "force": False},
                accept=(200, 409, 422),
                allow_ambiguous_transport=True,
            )
            success = 200
    except AmbiguousRefMutation:
        success = 201 if operation == "create" else 200
        mutation_status = None
    if mutation_status not in {success, None, 409, 422}:
        _fail("receipt ref mutation status differs")
    for attempt in range(len(REF_RECONCILIATION_DELAYS_SECONDS) + 1):
        status, after = _call_api(api, "GET", singular, accept=(200, 404))
        if status == 200:
            # A visible but different ref is not eventual consistency and is
            # rejected immediately without another write.
            _validate_ref_target_sha(after, commit_sha)
            return commit_sha
        if attempt < len(REF_RECONCILIATION_DELAYS_SECONDS):
            time.sleep(REF_RECONCILIATION_DELAYS_SECONDS[attempt])
    _fail("receipt ref mutation has no exact readback")


def persist_create_post_once_marker(
    api: Any,
    root: pathlib.Path,
    *,
    repository: str,
    commit_sha: str,
) -> str:
    """Create the R5 replay latch exactly once before a possible Zenodo create.

    Unlike normal receipt refs, an already-existing marker, a conflict, an
    ambiguous transport result, or a non-exact immediate response is never
    reconciled as success in this invocation.  That deliberately sacrifices
    availability so the unchanged publisher cannot cross the create boundary
    after an uncertain latch mutation.
    """
    if repository != EXPECTED["repository"]:
        _fail("create-post-once marker repository differs")
    if commit_sha != R4_UNSENT_CREATE_INCIDENT["c1"]:
        _fail("create-post-once marker target differs")
    ref = EXPECTED["create_post_once_ref"]
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    singular = "/repos/Goldkelch/qik-vrt/git/ref/" + suffix
    status, _before = _call_api(api, "GET", singular, accept=(200, 404))
    if status != 404:
        _fail("create-post-once marker already exists")
    try:
        mutation_status, changed = _call_api(
            api,
            "POST",
            "/repos/Goldkelch/qik-vrt/git/refs",
            payload={"ref": ref, "sha": commit_sha},
            accept=(201, 409, 422),
            allow_ambiguous_transport=True,
        )
    except AmbiguousRefMutation:
        _fail("create-post-once marker mutation is ambiguous and cannot rearm")
    if mutation_status != 201:
        _fail("create-post-once marker was not created by this invocation")
    _validate_ref(changed, ref, commit_sha)
    status, after = _call_api(api, "GET", singular, accept=(200, 404))
    if status != 200:
        _fail("create-post-once marker lacks authenticated exact readback")
    _validate_ref(after, ref, commit_sha)
    _fetch_credential_free(root, ref, commit_sha)
    return commit_sha


def _read_head_ref(
    api: Any,
    ref: str,
    *,
    allow_absent: bool = False,
) -> str | None:
    if not ref.startswith("refs/heads/") or any(
        character in ref for character in ("\x00", "\r", "\n")
    ):
        _fail("read-only branch ref is unsafe")
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    status, value = _call_api(
        api,
        "GET",
        "/repos/Goldkelch/qik-vrt/git/ref/" + suffix,
        accept=(200, 404) if allow_absent else (200,),
    )
    if status == 404:
        return None
    target = value.get("object")
    sha = target.get("sha") if isinstance(target, dict) else None
    if (
        value.get("ref") != ref
        or not isinstance(sha, str)
        or HEX40.fullmatch(sha) is None
        or target.get("type") != "commit"
    ):
        _fail("read-only branch ref response differs")
    return sha


def _validate_existing_consumption_tag(
    api: Any,
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    """GET and validate the one existing tag; this function has no write path."""
    authorization = manifest["owner_authorization"]
    ref = authorization["remote_consumption_ref"]
    if not isinstance(ref, str) or not ref.startswith("refs/tags/"):
        _fail("owner authorization consumption ref is not an exact tag ref")
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    status, ref_value = _call_api(
        api,
        "GET",
        "/repos/Goldkelch/qik-vrt/git/ref/" + suffix,
        accept=(200,),
    )
    if status != 200:
        _fail("existing consumption tag ref is absent")
    target = ref_value.get("object")
    tag_object = target.get("sha") if isinstance(target, dict) else None
    if tag_object != EXPECTED["tag_object"]:
        _fail("existing consumption tag object differs")
    publish._validate_github_ref_response(ref_value, ref, tag_object)
    status, tag_value = _call_api(
        api,
        "GET",
        "/repos/Goldkelch/qik-vrt/git/tags/" + tag_object,
        accept=(200,),
    )
    if status != 200:
        _fail("existing consumption annotated tag is absent")
    publish._validate_github_tag_response(
        tag_value,
        publish._expected_consumption_tag(manifest, EXPECTED["e1"]),
        tag_object,
    )
    return {
        "remote": "github_git_data_api",
        "api_origin": publish.GITHUB_API_BASE,
        "repository": EXPECTED["repository"],
        "ref": ref,
        "tag_object": tag_object,
        "object_type": "tag",
        "execution_head": EXPECTED["e1"],
        "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
        "recovery_mode": EXPECTED["recovery_mode"],
    }


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _credential_free_remote_head(root: pathlib.Path, ref: str) -> str | None:
    _status, raw = _git(
        root,
        "ls-remote",
        "--heads",
        "origin",
        ref,
        credential_free=True,
    )
    fields = raw.decode("utf-8").split()
    if not fields:
        return None
    if len(fields) != 2 or fields[1] != ref or HEX40.fullmatch(fields[0]) is None:
        _fail("credential-free remote branch response differs")
    return fields[0]


def _fetch_credential_free(root: pathlib.Path, ref: str, expected: str) -> None:
    if _credential_free_remote_head(root, ref) != expected:
        _fail("credential-free branch head differs")
    _git(
        root,
        "fetch",
        "--no-tags",
        "origin",
        ref,
        credential_free=True,
    )
    _status, fetched = _git(root, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if fetched.decode("ascii").strip() != expected:
        _fail("credential-free fetched receipt differs")


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
    observed: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        status, path = line.split("\t", 1)
        if path in observed:
            _fail("duplicate receipt delta path")
        observed[path] = status
    return observed


def _expected_receipt_integrity(
    root: pathlib.Path,
    evidence_raw: bytes,
) -> dict[str, bytes]:
    """Reconstruct the canonical integrity trio from E1 plus exact evidence."""
    _status, base_raw = _git(
        root,
        "show",
        f"{EXPECTED['e1']}:REPOSITORY_FILE_MANIFEST.json",
    )
    try:
        base = json.loads(base_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"E1 integrity base is invalid: {exc}")
    entries = base.get("files")
    if (
        not isinstance(entries, list)
        or any(not isinstance(entry, dict) for entry in entries)
        or any(
            entry.get("path") == EVIDENCE_RELATIVE.as_posix()
            for entry in entries
        )
    ):
        _fail("E1 integrity base already contains recovery evidence")
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
        key=lambda entry: entry["path"],
    )
    expected_manifest = dict(base)
    expected_manifest["files"] = expected_entries
    expected_manifest["file_count"] = len(expected_entries)
    expected_manifest["immutable_file_count"] = sum(
        entry.get("immutable") is True for entry in expected_entries
    )
    expected_manifest["excluded_file_count"] = (
        len(expected_entries) - expected_manifest["immutable_file_count"]
    )
    expected_manifest["repository_content_tree_sha256"] = (
        integrity._content_tree_sha256(expected_entries)
    )
    expected_manifest_raw = (
        json.dumps(
            expected_manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    expected_index = "".join(
        f"{entry['sha256']}  {entry['path']}\n"
        for entry in expected_entries
        if entry.get("immutable") is True
    ).encode("utf-8")
    expected_detached = (
        hashlib.sha256(expected_manifest_raw).hexdigest()
        + "  REPOSITORY_FILE_MANIFEST.json\n"
    ).encode("ascii")
    return {
        "REPOSITORY_FILE_MANIFEST.json": expected_manifest_raw,
        "SHA256SUMS.txt": expected_index,
        "REPOSITORY_FILE_MANIFEST.json.sha256": expected_detached,
    }


def _validate_receipt_integrity(
    root: pathlib.Path,
    commit: str,
    evidence_raw: bytes,
) -> None:
    expected = _expected_receipt_integrity(root, evidence_raw)
    for path, wanted in expected.items():
        _status, observed = _git(root, "show", f"{commit}:{path}")
        if observed != wanted:
            _fail("fetched receipt integrity differs for " + path)


def _validate_receipt_commit_provenance(
    root: pathlib.Path,
    commit: str,
    phase: str,
) -> None:
    message = (
        "zenodo: persist VRTCore H3 publication"
        if phase == "public_verified"
        else "zenodo: persist VRTCore h3 recovery receipt"
    )
    _status, date_raw = _git(
        root,
        "show",
        "-s",
        "--format=%cI",
        EXPECTED["e1"],
    )
    effect_date = date_raw.decode("ascii").strip()
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
            message,
            "",
            "qik-vrt-zenodo-publication[bot]",
            "qik-vrt-zenodo-publication[bot]@users.noreply.github.com",
            effect_date,
            "qik-vrt-zenodo-publication[bot]",
            "qik-vrt-zenodo-publication[bot]@users.noreply.github.com",
            effect_date,
        )
    ).encode("utf-8") + b"\n"
    if observed != expected:
        _fail("fetched receipt commit provenance differs")


def _validate_local_receipt_candidate(
    root: pathlib.Path,
    parent: str,
    evidence_path: pathlib.Path,
) -> None:
    """Prove the local four-path candidate before any GitHub object/ref write."""
    if HEX40.fullmatch(parent) is None:
        _fail("local receipt parent identity differs")
    _status, head = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if head.decode("ascii").strip() != EXPECTED["e1"]:
        _fail("local receipt candidate is not based on E1")
    if evidence_path != root / EVIDENCE_RELATIVE:
        _fail("local receipt evidence path differs")
    if not evidence_path.is_file() or evidence_path.is_symlink():
        _fail("local receipt evidence is not a regular file")

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
    expected_tracked = {
        path: "M" for path in INTEGRITY_PATHS
    }
    observed_tracked: dict[str, str] = {}
    for line in tracked.decode("utf-8").splitlines():
        status, path = line.split("\t", 1)
        if path in observed_tracked:
            _fail("local receipt candidate repeats a tracked path")
        observed_tracked[path] = status
    if observed_tracked != expected_tracked:
        _fail("local worktree differs from E1 outside receipt integrity paths")
    _status, untracked = _git(
        root,
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        ".",
    )
    observed_untracked = {
        os.fsdecode(item) for item in untracked.split(b"\0") if item
    }
    if observed_untracked != {EVIDENCE_RELATIVE.as_posix()}:
        _fail("local worktree has an unexpected untracked recovery path")

    evidence_raw = evidence_path.read_bytes()
    expected = _expected_receipt_integrity(root, evidence_raw)
    for relative, wanted in expected.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != wanted:
            _fail("local generated receipt integrity differs for " + relative)


def _validate_receipt_commit(
    root: pathlib.Path,
    commit: str,
    parent: str,
    *,
    expected_phase: str | None = None,
) -> dict[str, Any]:
    _status, parents = _git(root, "show", "-s", "--format=%P", commit)
    if parents.decode("ascii").strip() != parent:
        _fail("receipt commit is not exact single-parent continuation")
    expected_delta = {
        **{path: "M" for path in INTEGRITY_PATHS},
        EVIDENCE_RELATIVE.as_posix(): "A" if parent == EXPECTED["e1"] else "M",
    }
    if _receipt_delta(root, parent, commit) != expected_delta:
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
    _status, evidence_raw = _git(
        root,
        "show",
        f"{commit}:{EVIDENCE_RELATIVE.as_posix()}",
    )
    try:
        evidence = json.loads(evidence_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"receipt evidence JSON differs: {exc}")
    manifest_path = root / MANIFEST_RELATIVE
    manifest = publish.load_manifest(manifest_path, root)
    validated = publish._validate_recovery_evidence(
        evidence,
        manifest_path,
        root,
        manifest,
        EXPECTED["e1"],
    )
    if expected_phase is not None and validated["phase"] != expected_phase:
        _fail("receipt phase differs from requested checkpoint")
    if validated["remote_consumption"]["tag_object"] != EXPECTED["tag_object"]:
        _fail("receipt consumption tag identity differs")
    _validate_receipt_commit_provenance(
        root,
        commit,
        str(validated["phase"]),
    )
    _validate_receipt_integrity(root, commit, evidence_raw)
    return validated


def _write_exclusive_regular(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail("refusing to overwrite an existing local recovery evidence path")
    except OSError as exc:
        _fail(f"cannot create local recovery evidence: {exc}")
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("local recovery evidence write made no progress")
            offset += written
        os.fsync(descriptor)
    except OSError as exc:
        _fail(f"local recovery evidence write failed: {exc}")
    finally:
        os.close(descriptor)


def _validate_r5_one_shot_execution(root: pathlib.Path) -> str:
    """Bind the replay permit to the first, non-forced R4 -> R5 push attempt."""
    controller = os.environ.get("GITHUB_SHA", "")
    event_path_raw = os.environ.get("GITHUB_EVENT_PATH", "")
    if (
        HEX40.fullmatch(controller) is None
        or os.environ.get("GITHUB_REPOSITORY") != EXPECTED["repository"]
        or os.environ.get("GITHUB_EVENT_NAME") != "push"
        or os.environ.get("GITHUB_REF") != "refs/heads/" + EXPECTED["trigger_branch"]
        or os.environ.get("GITHUB_REF_NAME") != EXPECTED["trigger_branch"]
        or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
        or not event_path_raw
    ):
        _fail("R5 replay execution environment differs")
    event = _read_json(pathlib.Path(event_path_raw), maximum=2 * 1024 * 1024)
    repository = event.get("repository")
    head_commit = event.get("head_commit")
    if (
        event.get("ref") != "refs/heads/" + EXPECTED["trigger_branch"]
        or event.get("before") != R4_UNSENT_CREATE_INCIDENT["controller"]
        or event.get("after") != controller
        or event.get("created") is not False
        or event.get("deleted") is not False
        or event.get("forced") is not False
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_commit, dict)
        or head_commit.get("id") != controller
    ):
        _fail("R5 replay push event differs")
    _fetch_credential_free(
        root,
        "refs/heads/" + EXPECTED["trigger_branch"],
        controller,
    )
    _status, parent = _git(root, "show", "-s", "--format=%P", controller)
    if parent.decode("ascii").strip() != R4_UNSENT_CREATE_INCIDENT["controller"]:
        _fail("R5 controller is not the exact single successor of R4")
    return controller


def _validate_r8_one_shot_execution(root: pathlib.Path) -> str:
    """Bind correction to the first non-forced R7 -> R8 push attempt."""
    controller = os.environ.get("GITHUB_SHA", "")
    event_path_raw = os.environ.get("GITHUB_EVENT_PATH", "")
    if (
        HEX40.fullmatch(controller) is None
        or os.environ.get("GITHUB_REPOSITORY") != EXPECTED["repository"]
        or os.environ.get("GITHUB_EVENT_NAME") != "push"
        or os.environ.get("GITHUB_REF") != "refs/heads/" + EXPECTED["trigger_branch"]
        or os.environ.get("GITHUB_REF_NAME") != EXPECTED["trigger_branch"]
        or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
        or not event_path_raw
    ):
        _fail("R8 reconciliation execution environment differs")
    event = _read_json(pathlib.Path(event_path_raw), maximum=2 * 1024 * 1024)
    repository = event.get("repository")
    head_commit = event.get("head_commit")
    if (
        event.get("ref") != "refs/heads/" + EXPECTED["trigger_branch"]
        or event.get("before")
        != R7_CREATOR_NORMALIZATION_INCIDENT["controller"]
        or event.get("after") != controller
        or event.get("created") is not False
        or event.get("deleted") is not False
        or event.get("forced") is not False
        or not isinstance(repository, dict)
        or repository.get("full_name") != EXPECTED["repository"]
        or not isinstance(head_commit, dict)
        or head_commit.get("id") != controller
    ):
        _fail("R8 reconciliation push event differs")
    _fetch_credential_free(
        root,
        "refs/heads/" + EXPECTED["trigger_branch"],
        controller,
    )
    _status, parent = _git(root, "show", "-s", "--format=%P", controller)
    if (
        parent.decode("ascii").strip()
        != R7_CREATOR_NORMALIZATION_INCIDENT["controller"]
    ):
        _fail("R8 controller is not the exact single successor of R7")
    return controller


@contextlib.contextmanager
def _without_effect_credentials() -> Any:
    """Temporarily hide effect credentials from synchronous local helpers."""
    names = ("GITHUB_TOKEN", "GH_TOKEN", "ZENODO_ACCESS_TOKEN")
    saved = {name: os.environ[name] for name in names if name in os.environ}
    try:
        for name in names:
            os.environ.pop(name, None)
        yield
    finally:
        for name in names:
            os.environ.pop(name, None)
        os.environ.update(saved)


class RecoveryReceiptStore:
    """Exact four-path receipt chain plus one orthogonal create-only R5 latch."""

    def __init__(
        self,
        execution_root: pathlib.Path,
        api: Any,
        *,
        controller_parent: str,
    ) -> None:
        self.root = execution_root.resolve()
        self.api = api
        self.basis = load_recovery_basis()
        if HEX40.fullmatch(controller_parent) is None:
            _fail("controller parent is unresolved or invalid")
        self.controller_parent = controller_parent
        validate_e1_repository_objects(self.root, self.basis)
        verify_historical_incident(self.api, self.basis)
        _status, checked_out = _git(
            self.root,
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        )
        if checked_out.decode("ascii").strip() != EXPECTED["e1"]:
            _fail("publisher worktree is not checked out at E1")
        self.manifest_path = self.root / MANIFEST_RELATIVE
        self.evidence_path = self.root / EVIDENCE_RELATIVE
        self.publisher = _load_e1_publisher(self.root)
        self.manifest = self.publisher.load_manifest(self.manifest_path, self.root)
        with _without_effect_credentials():
            self.publisher._validate_origin_repository(
                self.root,
                EXPECTED["repository"],
            )
        self.remote_consumption = _validate_existing_consumption_tag(
            self.api,
            self.manifest,
        )
        main = _read_head_ref(self.api, "refs/heads/main")
        if main != self.controller_parent:
            _fail("main differs from the exact recovery controller parent")
        self.publication_head = _read_head_ref(
            self.api,
            EXPECTED["publication_ref"],
        )
        self.current_tip = _read_head_ref(
            self.api,
            EXPECTED["recovery_ref"],
            allow_absent=True,
        )
        self.create_post_once_head = _read_head_ref(
            self.api,
            EXPECTED["create_post_once_ref"],
            allow_absent=True,
        )
        if self.create_post_once_head not in {
            None,
            R4_UNSENT_CREATE_INCIDENT["c1"],
        }:
            _fail("create-post-once marker target differs")
        self._prepared_replay_pending = False
        self._initial_create_replay_pending = False
        self._record_created_reconciliation_armed = False
        self._r8_controller: str | None = None

    def _recheck_remote_boundary(self) -> None:
        if _read_head_ref(self.api, "refs/heads/main") != self.controller_parent:
            _fail("main moved across the exact recovery boundary")
        r8_controller = getattr(self, "_r8_controller", None)
        if (
            r8_controller is not None
            and _read_head_ref(
                self.api,
                "refs/heads/" + EXPECTED["trigger_branch"],
            )
            != r8_controller
        ):
            _fail("R8 trigger branch moved across the reconciliation boundary")
        if _read_head_ref(self.api, EXPECTED["publication_ref"]) != EXPECTED["e1"]:
            _fail("publication branch moved across the recovery boundary")
        if (
            _read_head_ref(
                self.api,
                EXPECTED["recovery_ref"],
                allow_absent=True,
            )
            != self.current_tip
        ):
            _fail("recovery branch moved across the checkpoint boundary")
        if (
            _read_head_ref(
                self.api,
                EXPECTED["create_post_once_ref"],
                allow_absent=True,
            )
            != self.create_post_once_head
        ):
            _fail("create-post-once marker moved across the checkpoint boundary")
        observed = _validate_existing_consumption_tag(self.api, self.manifest)
        if observed != self.remote_consumption:
            _fail("consumption tag moved across the recovery boundary")

    def arm_exact_unsent_create_replay(self) -> bool:
        """Arm only the exact R4 C1-without-Zenodo-effect state once."""
        if self.publication_head != EXPECTED["e1"]:
            return False
        if self.create_post_once_head == R4_UNSENT_CREATE_INCIDENT["c1"]:
            if self.current_tip is None:
                _fail("create-post-once marker exists without a recovery chain")
            _fetch_credential_free(
                self.root,
                EXPECTED["recovery_ref"],
                self.current_tip,
            )
            chain = self.validate_recovery_chain(self.current_tip)
            if (
                not chain
                or self.publisher.RECOVERY_PHASES.index(str(chain[-1]["phase"]))
                < self.publisher.RECOVERY_PHASES.index("create_requested")
            ):
                _fail("create-post-once marker precedes the exact C1 checkpoint")
            return False
        if (
            self.create_post_once_head is not None
            or self.current_tip != R4_UNSENT_CREATE_INCIDENT["c1"]
        ):
            _fail("R5 unsent-create replay state differs")
        _validate_r5_one_shot_execution(self.root)
        _fetch_credential_free(
            self.root,
            EXPECTED["recovery_ref"],
            R4_UNSENT_CREATE_INCIDENT["c1"],
        )
        _verify_r4_local_object_chain(self.root)
        verify_historical_r4_unsent_create_incident(self.api, self.root)
        chain = self.validate_recovery_chain(self.current_tip)
        if [item["phase"] for item in chain] != [
            "authorization_consumed",
            "create_requested",
        ]:
            _fail("R4 unsent-create recovery chain differs")
        self._initial_create_replay_pending = True
        return True

    def arm_exact_record_created_reconciliation(self) -> None:
        """Arm exact C2 after the pinned R7 creator-normalization failure."""
        incident = R6_DRAFT_METADATA_INCIDENT
        if (
            self.publication_head != EXPECTED["e1"]
            or self.create_post_once_head != R4_UNSENT_CREATE_INCIDENT["c1"]
            or self.current_tip != incident["c2"]
            or self._initial_create_replay_pending
        ):
            _fail("R8 record-created reconciliation state differs")
        self._r8_controller = _validate_r8_one_shot_execution(self.root)
        _fetch_credential_free(
            self.root,
            EXPECTED["publication_ref"],
            EXPECTED["e1"],
        )
        _fetch_credential_free(
            self.root,
            EXPECTED["create_post_once_ref"],
            R4_UNSENT_CREATE_INCIDENT["c1"],
        )
        _fetch_credential_free(
            self.root,
            EXPECTED["recovery_ref"],
            incident["c2"],
        )
        _verify_r7_local_object_chain(self.root)
        _verify_r8_null_affiliation_evidence(self.root)
        verify_historical_r5_record_created_timeout(self.api, self.root)
        verify_historical_r6_draft_metadata_incident(self.api, self.root)
        verify_historical_r7_creator_normalization_incident(self.api, self.root)
        chain = self.validate_recovery_chain(incident["c2"])
        if [item["phase"] for item in chain] != [
            "authorization_consumed",
            "create_requested",
            "record_created",
        ]:
            _fail("R8 record-created recovery chain differs")
        last = chain[-1]
        if (
            last.get("record_id") != incident["record_id"]
            or last.get("doi") != incident["doi"]
            or last.get("state") != incident["state"]
        ):
            _fail("R8 record-created recovery identity differs")
        self._record_created_reconciliation_armed = True

    def _prepare_integrity(self) -> None:
        with _without_effect_credentials():
            result = integrity.generate(self.root)
            if not result.ok:
                _fail("cannot generate exact recovery receipt integrity")
            result = integrity.verify(self.root)
            if not result.ok:
                _fail("generated recovery receipt integrity does not verify")

    def _expected_tree(self, parent: str, blobs: Mapping[str, str]) -> str:
        with tempfile.TemporaryDirectory(prefix="qikvrt-h3-receipt-index-") as directory:
            index = pathlib.Path(directory) / "index"
            environment = dict(os.environ)
            environment["GIT_INDEX_FILE"] = str(index)
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
            _status, tree = _git(
                self.root,
                "write-tree",
                environment=environment,
            )
        value = tree.decode("ascii").strip()
        if HEX40.fullmatch(value) is None:
            _fail("local expected receipt tree is invalid")
        return value

    def _create_receipt_commit(self, parent: str, phase: str) -> tuple[str, str]:
        self._prepare_integrity()
        _validate_local_receipt_candidate(
            self.root,
            parent,
            self.evidence_path,
        )
        local_blobs: dict[str, str] = {}
        raw_by_path: dict[str, bytes] = {}
        for relative in RECEIPT_PATHS:
            path = self.root / relative
            if not path.is_file() or path.is_symlink():
                _fail("receipt input is not a regular file")
            raw = path.read_bytes()
            raw_by_path[relative] = raw
            local_blobs[relative] = _git_blob_sha(raw)
        # Materialize local blob objects without shell interpolation.  They are
        # used only to derive and verify the exact expected tree.
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
            if (
                result.returncode != 0
                or result.stdout.decode("ascii").strip() != local_blobs[relative]
            ):
                _fail("local receipt blob materialization differs")
        expected_tree = self._expected_tree(parent, local_blobs)
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
            if response.get("sha") != local_blobs[relative]:
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
                        "sha": local_blobs[relative],
                    }
                    for relative in RECEIPT_PATHS
                ],
            },
            accept=(201,),
        )
        if tree_value.get("sha") != expected_tree:
            _fail("GitHub receipt tree identity differs")
        _status, date_raw = _git(
            self.root,
            "show",
            "-s",
            "--format=%cI",
            EXPECTED["e1"],
        )
        effect_date = date_raw.decode("ascii").strip()
        identity = {
            "name": "qik-vrt-zenodo-publication[bot]",
            "email": "qik-vrt-zenodo-publication[bot]@users.noreply.github.com",
            "date": effect_date,
        }
        message = (
            "zenodo: persist VRTCore H3 publication"
            if phase == "public_verified"
            else "zenodo: persist VRTCore h3 recovery receipt"
        )
        _status, commit_value = _call_api(
            self.api,
            "POST",
            "/repos/Goldkelch/qik-vrt/git/commits",
            payload={
                "message": message,
                "tree": expected_tree,
                "parents": [parent],
                "author": identity,
                "committer": identity,
            },
            accept=(201,),
        )
        commit = commit_value.get("sha")
        if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
            _fail("GitHub receipt commit identity is invalid")
        response_tree = commit_value.get("tree")
        response_parents = commit_value.get("parents")
        if (
            commit_value.get("message") != message
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

    def _readback(
        self,
        ref: str,
        commit: str,
        parent: str,
        phase: str,
        expected_tree: str,
    ) -> dict[str, Any]:
        _fetch_credential_free(self.root, ref, commit)
        _status, tree = _git(
            self.root,
            "rev-parse",
            "--verify",
            f"{commit}^{{tree}}",
        )
        if tree.decode("ascii").strip() != expected_tree:
            _fail("credential-free receipt tree differs")
        return _validate_receipt_commit(
            self.root,
            commit,
            parent,
            expected_phase=phase,
        )

    def persist_and_readback(
        self,
        evidence_path: pathlib.Path,
        phase: str,
    ) -> str:
        self._recheck_remote_boundary()
        if evidence_path.resolve() != self.evidence_path.resolve():
            _fail("checkpoint evidence path differs")
        if phase not in CHECKPOINT_PHASES:
            _fail("checkpoint phase is not a non-final recovery phase")
        if self._initial_create_replay_pending and phase != "create_requested":
            _fail("R5 initial create replay emitted an unexpected phase")
        value = _read_json(evidence_path)
        validated = self.publisher._validate_recovery_evidence(
            value,
            self.manifest_path,
            self.root,
            self.manifest,
            EXPECTED["e1"],
        )
        if (
            validated["phase"] != phase
            or validated["remote_consumption"] != self.remote_consumption
        ):
            _fail("checkpoint evidence binding differs")
        parent = self.current_tip or EXPECTED["e1"]
        if self.current_tip is not None:
            chain = self.validate_recovery_chain(self.current_tip)
            if not chain:
                _fail("recovery receipt chain is unexpectedly empty")
            prior = chain[-1]
            left = self.publisher.RECOVERY_PHASES.index(prior["phase"])
            right = self.publisher.RECOVERY_PHASES.index(phase)
            prior_identity = (prior.get("record_id"), prior.get("doi"))
            current_identity = (validated.get("record_id"), validated.get("doi"))
            if left >= self.publisher.RECOVERY_PHASES.index("record_created"):
                if current_identity != prior_identity:
                    _fail("checkpoint record identity differs from recovery tip")
            if right < left:
                if (
                    prior["phase"] == "publish_requested"
                    and phase == "prepared"
                    and current_identity == prior_identity
                    and any(
                        item["phase"] == "prepared"
                        and (item.get("record_id"), item.get("doi"))
                        == prior_identity
                        for item in chain
                    )
                ):
                    # E1 re-runs draft preparation before re-emitting its exact
                    # publish intent.  The already-durable stronger checkpoint
                    # stays remote; no ref is moved backwards.
                    self._prepared_replay_pending = True
                    return self.current_tip
                _fail("checkpoint phase does not increase")
            if right == left:
                _status, existing = _git(
                    self.root,
                    "show",
                    f"{self.current_tip}:{EVIDENCE_RELATIVE.as_posix()}",
                )
                if existing != evidence_path.read_bytes():
                    _fail("same-phase checkpoint evidence differs")
                if self._initial_create_replay_pending:
                    raw = evidence_path.read_bytes()
                    if (
                        self.current_tip != R4_UNSENT_CREATE_INCIDENT["c1"]
                        or phase != "create_requested"
                        or self.create_post_once_head is not None
                        or len(raw)
                        != R4_UNSENT_CREATE_INCIDENT["c1_evidence_bytes"]
                        or hashlib.sha256(raw).hexdigest()
                        != R4_UNSENT_CREATE_INCIDENT["c1_evidence_sha256"]
                    ):
                        _fail("R5 create-request replay evidence differs")
                    persist_create_post_once_marker(
                        self.api,
                        self.root,
                        repository=EXPECTED["repository"],
                        commit_sha=R4_UNSENT_CREATE_INCIDENT["c1"],
                    )
                    self.create_post_once_head = R4_UNSENT_CREATE_INCIDENT["c1"]
                    self._initial_create_replay_pending = False
                if phase == "publish_requested":
                    self._prepared_replay_pending = False
                return self.current_tip
            if self._prepared_replay_pending:
                _fail("prepared replay lacks identical publish_requested confirmation")
            if self.create_post_once_head != R4_UNSENT_CREATE_INCIDENT["c1"]:
                _fail("recovery phase advance lacks the create-post-once marker")
        commit, tree = self._create_receipt_commit(parent, phase)
        self._recheck_remote_boundary()
        persist_receipt_create_only_or_ff(
            self.api,
            repository=EXPECTED["repository"],
            ref=EXPECTED["recovery_ref"],
            expected_old_sha=self.current_tip,
            commit_sha=commit,
        )
        self._readback(
            EXPECTED["recovery_ref"],
            commit,
            parent,
            phase,
            tree,
        )
        self.current_tip = commit
        return commit

    def _parent_of(self, commit: str) -> str:
        _status, raw = _git(self.root, "show", "-s", "--format=%P", commit)
        value = raw.decode("ascii").strip()
        if HEX40.fullmatch(value) is None:
            _fail("receipt parent identity differs")
        return value

    def restore_or_bootstrap(self) -> tuple[bool, str]:
        if self.publication_head != EXPECTED["e1"]:
            self.verify_finalized(self.publication_head)
            return True, self.publication_head
        if self.current_tip is None:
            if os.path.lexists(self.evidence_path):
                _fail("unpersisted local evidence exists before bootstrap")
            evidence = self.publisher._phase_evidence(
                self.manifest_path,
                self.root,
                self.manifest,
                EXPECTED["e1"],
                self.remote_consumption,
                "authorization_consumed",
            )
            self.publisher._create_consumption_receipt(
                self.evidence_path,
                evidence,
                {},
            )
            tip = self.persist_and_readback(
                self.evidence_path,
                "authorization_consumed",
            )
            return False, tip
        _fetch_credential_free(
            self.root,
            EXPECTED["recovery_ref"],
            self.current_tip,
        )
        chain = self.validate_recovery_chain(self.current_tip)
        if not chain:
            _fail("durable recovery branch has no exact receipt chain")
        last_phase = str(chain[-1]["phase"])
        if (
            self.create_post_once_head == R4_UNSENT_CREATE_INCIDENT["c1"]
            and self.publisher.RECOVERY_PHASES.index(last_phase)
            < self.publisher.RECOVERY_PHASES.index("create_requested")
        ):
            _fail("create-post-once marker is not cross-bound to C1 ancestry")
        if (
            self.publisher.RECOVERY_PHASES.index(last_phase)
            >= self.publisher.RECOVERY_PHASES.index("record_created")
            and self.create_post_once_head != R4_UNSENT_CREATE_INCIDENT["c1"]
        ):
            _fail("durable record recovery lacks the create-post-once marker")
        source_commit = (
            R4_UNSENT_CREATE_INCIDENT["c0"]
            if self._initial_create_replay_pending
            else self.current_tip
        )
        raw = _git(
            self.root,
            "show",
            f"{source_commit}:{EVIDENCE_RELATIVE.as_posix()}",
        )[1]
        _write_exclusive_regular(self.evidence_path, raw)
        return False, self.current_tip

    def validate_recovery_chain(self, tip: str) -> list[dict[str, Any]]:
        reverse: list[dict[str, Any]] = []
        reverse_commits: list[str] = []
        cursor = tip
        visited: set[str] = set()
        while cursor != EXPECTED["e1"]:
            if cursor in visited or len(visited) >= len(CHECKPOINT_PHASES):
                _fail("recovery receipt chain is cyclic or unbounded")
            visited.add(cursor)
            parent = self._parent_of(cursor)
            evidence = _validate_receipt_commit(self.root, cursor, parent)
            if evidence["phase"] == "public_verified":
                _fail("recovery branch contains final public evidence")
            reverse.append(evidence)
            reverse_commits.append(cursor)
            cursor = parent
        chain = list(reversed(reverse))
        commits = list(reversed(reverse_commits))
        phases = [str(item["phase"]) for item in chain]
        if phases != list(CHECKPOINT_PHASES[: len(phases)]):
            _fail("recovery receipt chain is not the exact phase prefix")
        if (
            not commits
            or commits[0] != R4_UNSENT_CREATE_INCIDENT["c0"]
            or (
                len(commits) >= 2
                and commits[1] != R4_UNSENT_CREATE_INCIDENT["c1"]
            )
        ):
            _fail("recovery chain diverges from the exact C0/C1 incident ancestry")
        record_identity: tuple[Any, Any] | None = None
        for item in chain:
            if item["remote_consumption"] != self.remote_consumption:
                _fail("recovery chain consumption identity changes")
            has_record = "record_id" in item or "doi" in item
            if has_record:
                current = (item.get("record_id"), item.get("doi"))
                if None in current:
                    _fail("recovery chain record identity is incomplete")
                if record_identity is None:
                    record_identity = current
                elif current != record_identity:
                    _fail("recovery chain record identity changes")
        return chain

    def persist_final(self) -> str:
        if self.current_tip is None:
            _fail("final receipt lacks a durable recovery parent")
        if self._prepared_replay_pending:
            _fail("final receipt lacks replayed publish intent confirmation")
        if self._initial_create_replay_pending:
            _fail("final receipt crossed an unconsumed initial create replay")
        if self.create_post_once_head != R4_UNSENT_CREATE_INCIDENT["c1"]:
            _fail("final receipt lacks the create-post-once marker")
        self._recheck_remote_boundary()
        value = _read_json(self.evidence_path)
        validated = self.publisher._validate_recovery_evidence(
            value,
            self.manifest_path,
            self.root,
            self.manifest,
            EXPECTED["e1"],
        )
        if (
            validated["phase"] != "public_verified"
            or validated["state"] != "published"
            or validated["remote_consumption"] != self.remote_consumption
        ):
            _fail("final publication evidence differs")
        chain = self.validate_recovery_chain(self.current_tip)
        prior = chain[-1] if chain else None
        if (
            prior is None
            or prior["phase"] != "publish_requested"
            or (validated.get("record_id"), validated.get("doi"))
            != (prior.get("record_id"), prior.get("doi"))
        ):
            _fail("final publication diverges from durable publish intent")
        parent = self.current_tip
        commit, tree = self._create_receipt_commit(parent, "public_verified")
        self._recheck_remote_boundary()
        persist_receipt_create_only_or_ff(
            self.api,
            repository=EXPECTED["repository"],
            ref=EXPECTED["publication_ref"],
            expected_old_sha=EXPECTED["e1"],
            commit_sha=commit,
        )
        self._readback(
            EXPECTED["publication_ref"],
            commit,
            parent,
            "public_verified",
            tree,
        )
        if _read_head_ref(self.api, EXPECTED["recovery_ref"]) != parent:
            _fail("final receipt changed the recovery ref")
        return commit

    def verify_finalized(self, final: str | None) -> dict[str, Any]:
        if not isinstance(final, str) or HEX40.fullmatch(final) is None:
            _fail("finalized publication ref identity differs")
        if self.create_post_once_head != R4_UNSENT_CREATE_INCIDENT["c1"]:
            _fail("finalized publication lacks the create-post-once marker")
        _fetch_credential_free(self.root, EXPECTED["publication_ref"], final)
        parent = self._parent_of(final)
        evidence = _validate_receipt_commit(
            self.root,
            final,
            parent,
            expected_phase="public_verified",
        )
        recovery = _read_head_ref(
            self.api,
            EXPECTED["recovery_ref"],
            allow_absent=True,
        )
        if recovery != parent:
            _fail("finalized publication recovery parent differs")
        _fetch_credential_free(self.root, EXPECTED["recovery_ref"], recovery)
        chain = self.validate_recovery_chain(recovery)
        prior = chain[-1] if chain else None
        if (
            prior is None
            or prior["phase"] != "publish_requested"
            or evidence["remote_consumption"] != prior["remote_consumption"]
            or (evidence.get("record_id"), evidence.get("doi"))
            != (prior.get("record_id"), prior.get("doi"))
        ):
            _fail("finalized publication diverges from durable publish intent")
        return evidence


def _creators_match_r8_null_affiliation_normalization(
    actual: Any,
    expected: Any,
) -> bool:
    """Accept exact creator objects plus Zenodo's evidenced null affiliation."""

    def exact_json_value(observed: Any, authorized: Any) -> bool:
        """Compare nested JSON without Python's bool/int equality aliasing."""
        try:
            observed_bytes = json.dumps(
                observed,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            authorized_bytes = json.dumps(
                authorized,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError):
            return False
        return observed_bytes == authorized_bytes

    if (
        not isinstance(actual, list)
        or not isinstance(expected, list)
        or not expected
        or len(actual) != len(expected)
    ):
        return False
    for observed, authorized in zip(actual, expected):
        if not isinstance(observed, dict) or not isinstance(authorized, dict):
            return False
        name = authorized.get("name")
        if not isinstance(name, str) or not name or name != name.strip():
            return False
        if not set(authorized).issubset(observed):
            return False
        if any(
            not exact_json_value(observed[key], value)
            for key, value in authorized.items()
        ):
            return False
        extras = set(observed) - set(authorized)
        if extras and (
            extras != {"affiliation"}
            or observed.get("affiliation") is not None
        ):
            return False
    return True


def _r7_draft_metadata_mismatch_keys(
    publisher_module: Any,
    actual: Any,
    expected: Mapping[str, Any],
) -> tuple[str, ...]:
    """Compare every authorized field across legacy/normalized draft shapes."""
    if not isinstance(actual, dict):
        return tuple(sorted(key for key in expected if key != "prereserve_doi"))
    allowed_keys = set(expected) | {"doi", "resource_type"}
    mismatches: list[str] = [
        "unexpected:" + key for key in sorted(set(actual) - allowed_keys)
    ]
    resource_type = actual.get("resource_type")
    for key, expected_value in expected.items():
        if key == "prereserve_doi":
            continue
        if key == "creators":
            if not _creators_match_r8_null_affiliation_normalization(
                actual.get("creators"),
                expected_value,
            ):
                mismatches.append(key)
            continue
        if key == "license":
            license_value = actual.get("license")
            actual_value = (
                license_value.get("id")
                if isinstance(license_value, dict)
                else license_value
            )
        elif key == "upload_type":
            candidates = []
            if "upload_type" in actual:
                candidates.append(actual.get("upload_type"))
            if "resource_type" in actual:
                candidates.append(
                    resource_type.get("type")
                    if isinstance(resource_type, dict)
                    else resource_type
                )
            if not candidates or any(
                not publisher_module.zenodo._metadata_matches(
                    candidate,
                    expected_value,
                )
                for candidate in candidates
            ):
                mismatches.append(key)
            continue
        elif key == "publication_type":
            candidates = []
            if "publication_type" in actual:
                candidates.append(actual.get("publication_type"))
            if "resource_type" in actual:
                candidates.append(
                    resource_type.get("subtype")
                    if isinstance(resource_type, dict)
                    else resource_type
                )
            if not candidates or any(
                not publisher_module.zenodo._metadata_matches(
                    candidate,
                    expected_value,
                )
                for candidate in candidates
            ):
                mismatches.append(key)
            continue
        else:
            actual_value = actual.get(key)
        if not publisher_module.zenodo._metadata_matches(
            actual_value,
            expected_value,
        ):
            mismatches.append(key)
    return tuple(sorted(mismatches))


def _validate_r7_record_identity(
    publisher_module: Any,
    manifest: Mapping[str, Any],
    state: str,
    current: Mapping[str, Any],
    *,
    require_exact_draft_metadata: bool,
) -> None:
    """Bind immutable C2 identity; relax only mutable draft fields pre-PUT."""
    incident = R6_DRAFT_METADATA_INCIDENT
    record_id = publisher_module.zenodo._record_id(
        current,
        "R7 record-created reconciliation record",
    )
    doi = publisher_module.zenodo._doi_from_deposition(
        current,
        "R7 record-created reconciliation record",
    )
    if record_id != incident["record_id"] or doi != incident["doi"]:
        _fail("R7 owned record identity differs from exact C2")

    def require_exact_optional_record_id(value: Any, where: str) -> None:
        if value is None:
            return
        normalized = int(value) if isinstance(value, str) and value.isdecimal() else value
        if (
            isinstance(normalized, bool)
            or not isinstance(normalized, int)
            or normalized != incident["record_id"]
        ):
            _fail("R7 owned record exposes a conflicting " + where)

    for key in ("record_id", "recid"):
        require_exact_optional_record_id(current.get(key), "record identity")
    actual_metadata = current.get("metadata")
    metadata = manifest["metadata"]
    doi_candidates: list[Any] = [current.get("doi")]
    if isinstance(actual_metadata, dict):
        reserved = actual_metadata.get("prereserve_doi")
        doi_candidates.append(actual_metadata.get("doi"))
        if isinstance(reserved, dict):
            if reserved.get("doi") != incident["doi"]:
                _fail("R7 owned record exposes a conflicting DOI identity")
            doi_candidates.append(reserved.get("doi"))
            require_exact_optional_record_id(
                reserved.get("recid"),
                "reserved record identity",
            )
        elif reserved is not None:
            doi_candidates.append(reserved)
    if any(
        candidate is not None and candidate != incident["doi"]
        for candidate in doi_candidates
    ):
        _fail("R7 owned record exposes a conflicting DOI identity")
    if (
        not isinstance(actual_metadata, dict)
        or not _creators_match_r8_null_affiliation_normalization(
            actual_metadata.get("creators"),
            metadata["creators"],
        )
    ):
        _fail("R8 title, version, or creators differ from exact C2 identity")
    if state == "published":
        if not publisher_module.zenodo._published_metadata_matches(
            actual_metadata,
            metadata,
        ):
            _fail("R7 published record metadata differs from exact C2 manifest")
        conflicting_aliases = tuple(
            key
            for key in _r7_draft_metadata_mismatch_keys(
                publisher_module,
                actual_metadata,
                metadata,
            )
            if not key.startswith("unexpected:")
        )
        if conflicting_aliases:
            _fail(
                "R7 published record exposes conflicting metadata aliases: "
                + ",".join(conflicting_aliases)
            )
        return
    if state != "draft":
        _fail("R7 owned record state is unsupported")
    if not publisher_module._inventory_publication_identity_candidate(
        current,
        metadata,
    ):
        _fail("R8 draft title, version, or creators differ from exact C2 identity")
    mismatches = _r7_draft_metadata_mismatch_keys(
        publisher_module,
        actual_metadata,
        metadata,
    )
    if require_exact_draft_metadata and mismatches:
        _fail(
            "R7 draft metadata differs after exact correction: "
            + ",".join(mismatches)
        )


def _gate_r7_owned_inventory_identity(
    publisher_module: Any,
    manifest: Mapping[str, Any],
    client: Any,
    zenodo_token: str,
) -> tuple[str, Mapping[str, Any]]:
    """Require one stable, empty, owned C2 draft before R7 correction."""
    metadata = manifest["metadata"]
    entries = publisher_module._shared_entries(manifest["files"])
    inventory = publisher_module._list_all_owned_depositions(client, zenodo_token)
    matches: list[tuple[int, str, str, Mapping[str, Any]]] = []
    for item in inventory:
        if not publisher_module._inventory_publication_identity_candidate(
            item,
            metadata,
        ):
            continue
        record_id = publisher_module.zenodo._record_id(
            item,
            "R7 owned inventory candidate",
        )
        state, current = client.get_deposition_or_record(record_id)
        _validate_r7_record_identity(
            publisher_module,
            manifest,
            state,
            current,
            require_exact_draft_metadata=False,
        )
        doi = publisher_module.zenodo._doi_from_deposition(
            current,
            "R7 owned inventory candidate",
        )
        if state == "draft" and client._server_files(current):
            _fail("R7 exact C2 draft contains unexpected preexisting files")
        matches.append((record_id, doi, state, current))
    if len(matches) != 1:
        _fail(
            "R7 reconciliation requires exactly one canonically matching "
            f"owned deposition; observed {len(matches)}"
        )
    record_id, doi, state, current = matches[0]
    incident = R6_DRAFT_METADATA_INCIDENT
    if record_id != incident["record_id"] or doi != incident["doi"]:
        _fail("R7 sole owned candidate differs from exact C2 identity")
    if state == "published":
        current = client.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            doi,
            published=True,
            initial=current,
        )
    return state, current


def run_publisher_with_checkpoints(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    store: CheckpointStore,
    *,
    publish_callable: Callable[[pathlib.Path, pathlib.Path], dict[str, Any]] | None = None,
    reconcile_record: tuple[int, str] | None = None,
) -> dict[str, Any]:
    """Run the unchanged publisher with synchronous, remote phase checkpoints.

    The hook wraps only the publisher's atomic evidence writer.  A phase write
    returns to the original publisher only after ``store`` has persisted and
    read back that phase.  Consequently ``create_requested`` is durable before
    ``create_paper`` and ``publish_requested`` before ``publish_and_poll``.
    """
    if reconcile_record is not None and publish_callable is not None:
        _fail("R7 reconciliation may only run the freshly loaded E1 publisher")
    if reconcile_record is not None:
        incident = R6_DRAFT_METADATA_INCIDENT
        if reconcile_record != (
            int(incident["record_id"]),
            str(incident["doi"]),
        ):
            _fail("R7 reconciliation target differs from exact C2")
    publisher_module = (
        publish if publish_callable is not None else _load_e1_publisher(root)
    )
    callable_value = publish_callable or publisher_module.publish
    original_exclusive = publisher_module._create_consumption_receipt
    original_atomic = publisher_module._atomic_recovery_evidence
    original_acquire = publisher_module._acquire_remote_consumption_lock
    client_type: Any | None = None
    original_client_init: Any | None = None
    original_request: Any | None = None
    original_create_paper: Any | None = None
    original_wait_for_editable_metadata: Any | None = None
    original_gate_record: Any | None = None
    original_resume: Any | None = None
    if reconcile_record is not None:
        client_type = publisher_module.zenodo.ZenodoClient
        original_client_init = client_type.__init__
        original_request = client_type.request
        original_create_paper = client_type.create_paper
        original_wait_for_editable_metadata = client_type.wait_for_editable_metadata
        original_gate_record = client_type.gate_record
        original_resume = publisher_module._resume_publication
    reconciliation: dict[str, Any] = {
        "inventory_complete": False,
        "manifest": None,
        "entries": None,
        "verified": None,
        "bucket_path": None,
        "metadata_preconverged": False,
        "metadata_preflight_mismatches": None,
        "metadata_put_attempted": False,
        "metadata_put_succeeded": False,
        "metadata_put_skipped": False,
        "metadata_confirmed": False,
        "upload_index": 0,
        "upload_in_flight": False,
        "prepared_durable": False,
        "publish_intent_durable": False,
        "publish_post_attempted": False,
    }

    def reject_new_consumption_lock(*_args: Any, **_kwargs: Any) -> Any:
        _fail("recovery may not acquire or create an authorization lock")

    def persist_after_write(path: pathlib.Path, value: Mapping[str, Any]) -> None:
        phase = value.get("phase")
        if phase in CHECKPOINT_PHASES:
            store.persist_and_readback(path, str(phase))
            if reconcile_record is not None and phase == "prepared":
                if (
                    reconciliation["metadata_confirmed"] is not True
                    or not isinstance(reconciliation["entries"], list)
                    or reconciliation["upload_index"]
                    != len(reconciliation["entries"])
                ):
                    _fail("R7 prepared checkpoint preceded exact upload completion")
                reconciliation["prepared_durable"] = True
            elif reconcile_record is not None and phase == "publish_requested":
                if reconciliation["prepared_durable"] is not True:
                    _fail("R7 publish intent preceded durable preparation")
                reconciliation["publish_intent_durable"] = True

    def checkpointing_exclusive_writer(
        path: pathlib.Path,
        value: Mapping[str, Any],
        secrets_by_name: Mapping[str, str],
    ) -> None:
        original_exclusive(path, value, secrets_by_name)
        persist_after_write(path, value)

    def checkpointing_atomic_writer(
        path: pathlib.Path,
        value: Mapping[str, Any],
        secrets_by_name: Mapping[str, str],
    ) -> None:
        original_atomic(path, value, secrets_by_name)
        persist_after_write(path, value)

    def extended_client_init(
        instance: Any,
        token: str,
        base_url: str,
        transport: Any | None = None,
        *,
        poll_attempts: int = 30,
        poll_interval: float = 2.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if poll_attempts != 30 or poll_interval != 2.0:
            _fail("R7 reconciliation client polling inputs differ")
        if original_client_init is None:
            _fail("R7 reconciliation client initializer is unavailable")
        original_client_init(
            instance,
            token,
            base_url,
            transport,
            poll_attempts=120,
            poll_interval=2.0,
            sleeper=sleeper,
        )

    def reject_create_paper(*_args: Any, **_kwargs: Any) -> Any:
        _fail("R7 reconciliation forbids creation of a Zenodo deposition")

    def exact_bucket_path(instance: Any, current: Mapping[str, Any]) -> str:
        links = current.get("links")
        bucket = links.get("bucket") if isinstance(links, dict) else None
        if not isinstance(bucket, str):
            _fail("R7 exact C2 draft lacks its bounded upload bucket")
        safe_bucket = publisher_module.zenodo.validate_response_url(
            bucket,
            instance.base_url,
        )
        parts = urllib.parse.urlsplit(safe_bucket)
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
            _fail("R7 exact C2 upload bucket escaped its canonical API shape")
        return path

    def wait_for_semantically_exact_metadata(
        instance: Any,
        record_id: int,
        metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        incident = R6_DRAFT_METADATA_INCIDENT
        mutated = (
            reconciliation["metadata_put_attempted"] is True
            and reconciliation["metadata_put_succeeded"] is True
            and reconciliation["metadata_put_skipped"] is False
        )
        skipped = (
            reconciliation["metadata_preconverged"] is True
            and reconciliation["metadata_put_attempted"] is False
            and reconciliation["metadata_put_succeeded"] is False
            and reconciliation["metadata_put_skipped"] is True
        )
        if (
            record_id != incident["record_id"]
            or not (mutated or skipped)
            or not isinstance(reconciliation["manifest"], Mapping)
            or metadata != reconciliation["manifest"]["metadata"]
        ):
            _fail("R8 metadata confirmation lacks an exact PUT or no-op proof")
        last_mismatches: tuple[str, ...] = ()
        for attempt in range(instance.poll_attempts):
            status, value = instance.get(
                f"/api/deposit/depositions/{record_id}",
                accept=(200, 202),
            )
            _validate_r7_record_identity(
                publisher_module,
                reconciliation["manifest"],
                "draft",
                value,
                require_exact_draft_metadata=False,
            )
            if instance._server_files(value):
                _fail("R7 exact C2 draft gained files after metadata correction")
            last_mismatches = _r7_draft_metadata_mismatch_keys(
                publisher_module,
                value.get("metadata"),
                metadata,
            )
            links = value.get("links")
            candidate_bucket = (
                links.get("bucket") if isinstance(links, dict) else None
            )
            if status == 200 and not last_mismatches and isinstance(
                candidate_bucket,
                str,
            ):
                store._recheck_remote_boundary()  # type: ignore[attr-defined]
                second_status, confirmed = instance.get(
                    f"/api/deposit/depositions/{record_id}",
                    accept=(200, 202),
                )
                if second_status != 200:
                    _fail("R7 exact metadata changed during confirmation")
                _validate_r7_record_identity(
                    publisher_module,
                    reconciliation["manifest"],
                    "draft",
                    confirmed,
                    require_exact_draft_metadata=True,
                )
                if instance._server_files(confirmed):
                    _fail("R7 exact C2 draft gained files before bounded upload")
                bucket_path = exact_bucket_path(instance, confirmed)
                store._recheck_remote_boundary()  # type: ignore[attr-defined]
                reconciliation["bucket_path"] = bucket_path
                reconciliation["metadata_confirmed"] = True
                return dict(confirmed)
            if attempt + 1 < instance.poll_attempts:
                instance.sleeper(instance.poll_interval)
        suffix = ",".join(last_mismatches) if last_mismatches else "response"
        _fail("R7 timed out waiting for exact corrected metadata: " + suffix)

    def gate_semantically_exact_record(
        instance: Any,
        value: Mapping[str, Any],
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Any,
        expected_doi: str,
        *,
        published: bool,
    ) -> None:
        if published:
            if original_gate_record is None:
                _fail("R7 published-record gate is unavailable")
            original_gate_record(
                instance,
                value,
                record_id,
                metadata,
                entries,
                expected_doi,
                published=True,
            )
            return
        incident = R6_DRAFT_METADATA_INCIDENT
        if (
            record_id != incident["record_id"]
            or expected_doi != incident["doi"]
            or reconciliation["metadata_confirmed"] is not True
            or metadata
            != reconciliation.get("manifest", {}).get("metadata")
            or entries != reconciliation["entries"]
        ):
            _fail("R7 draft gate inputs differ from exact C2")
        _validate_r7_record_identity(
            publisher_module,
            reconciliation["manifest"],
            "draft",
            value,
            require_exact_draft_metadata=True,
        )
        instance.gate_files(value, entries)

    def gate_uploaded_prefix(instance: Any, current: Mapping[str, Any]) -> None:
        entries = reconciliation["entries"]
        index = reconciliation["upload_index"]
        if not isinstance(entries, list) or not isinstance(index, int):
            _fail("R7 upload prefix state differs")
        expected = entries[:index]
        server_files = instance._server_files(current)
        by_name: dict[str, Mapping[str, Any]] = {}
        for item in server_files:
            name = instance._server_file_name(item)
            if name in by_name:
                _fail("R7 upload prefix contains a duplicate file")
            by_name[name] = item
        if set(by_name) != {entry["name"] for entry in expected}:
            _fail("R7 upload prefix differs from completed manifest entries")
        for entry in expected:
            item = by_name[entry["name"]]
            size = item.get("filesize", item.get("size"))
            if isinstance(size, str) and size.isdecimal():
                size = int(size)
            checksum = item.get("checksum")
            if size != entry["size"] or checksum not in (
                entry["md5"],
                "md5:" + entry["md5"],
            ):
                _fail("R7 upload prefix file identity differs")

    def guarded_request(
        instance: Any,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        normalized_method = str(method).upper()
        safe_url = publisher_module.zenodo.validate_response_url(
            url,
            instance.base_url,
        )
        parts = urllib.parse.urlsplit(safe_url)
        path = parts.path
        if original_request is None:
            _fail("R7 reconciliation request transport is unavailable")
        if normalized_method == "GET":
            return original_request(instance, normalized_method, safe_url, **kwargs)
        if normalized_method == "POST" and path == "/api/deposit/depositions":
            _fail("R7 reconciliation blocked the exact Zenodo create endpoint")
        incident = R6_DRAFT_METADATA_INCIDENT
        if (
            parts.query
            or parts.fragment
            or reconcile_record
            != (int(incident["record_id"]), str(incident["doi"]))
            or getattr(store, "_record_created_reconciliation_armed", False)
            is not True
            or reconciliation["inventory_complete"] is not True
            or not isinstance(reconciliation["manifest"], Mapping)
        ):
            _fail("R7 Zenodo mutation preceded its exact reconciliation gate")
        record_id = int(incident["record_id"])
        deposition_path = f"/api/deposit/depositions/{record_id}"
        publish_path = deposition_path + "/actions/publish"
        metadata_put = normalized_method == "PUT" and path == deposition_path

        store._recheck_remote_boundary()  # type: ignore[attr-defined]
        state, current = instance.get_deposition_or_record(record_id)
        if state != "draft":
            _fail("R7 forbids mutation after the exact C2 record is public")
        _validate_r7_record_identity(
            publisher_module,
            reconciliation["manifest"],
            state,
            current,
            require_exact_draft_metadata=not metadata_put,
        )

        if metadata_put:
            if (
                reconciliation["metadata_put_attempted"] is True
                or reconciliation["metadata_put_skipped"] is True
                or set(kwargs) != {"payload", "accept"}
                or kwargs.get("payload")
                != {"metadata": reconciliation["manifest"]["metadata"]}
                or kwargs.get("accept") != (200, 202)
                or instance._server_files(current)
            ):
                _fail("R8 exact metadata PUT contract differs")
            current_mismatches = _r7_draft_metadata_mismatch_keys(
                publisher_module,
                current.get("metadata"),
                reconciliation["manifest"]["metadata"],
            )
            if (
                reconciliation["metadata_preconverged"] is True
                or not current_mismatches
            ):
                if current_mismatches:
                    _fail("R8 metadata changed after its no-op preflight")
                reconciliation["metadata_preconverged"] = True
                reconciliation["metadata_preflight_mismatches"] = ()
                first_bucket = exact_bucket_path(instance, current)
                store._recheck_remote_boundary()  # type: ignore[attr-defined]
                result = original_request(
                    instance,
                    "GET",
                    safe_url,
                    accept=(200,),
                )
                response, confirmed = result
                if getattr(response, "status", None) != 200:
                    _fail("R8 metadata no-op GET status differs")
                _validate_r7_record_identity(
                    publisher_module,
                    reconciliation["manifest"],
                    "draft",
                    confirmed,
                    require_exact_draft_metadata=True,
                )
                if (
                    instance._server_files(confirmed)
                    or exact_bucket_path(instance, confirmed) != first_bucket
                ):
                    _fail("R8 metadata no-op readback changed the exact draft")
                store._recheck_remote_boundary()  # type: ignore[attr-defined]
                reconciliation["metadata_put_skipped"] = True
                return result
            if current_mismatches != reconciliation["metadata_preflight_mismatches"]:
                _fail("R8 metadata changed before its exact idempotent PUT")
            store._recheck_remote_boundary()  # type: ignore[attr-defined]
            reconciliation["metadata_put_attempted"] = True
            result = original_request(
                instance,
                normalized_method,
                safe_url,
                **kwargs,
            )
            reconciliation["metadata_put_succeeded"] = True
            return result

        if (
            not (
                reconciliation["metadata_put_succeeded"] is True
                or reconciliation["metadata_put_skipped"] is True
            )
            or reconciliation["metadata_confirmed"] is not True
        ):
            _fail("R8 file or publish effect preceded metadata convergence")
        gate_uploaded_prefix(instance, current)
        bucket_path = reconciliation["bucket_path"]
        if (
            not isinstance(bucket_path, str)
            or exact_bucket_path(instance, current) != bucket_path
        ):
            _fail("R7 exact C2 upload bucket changed after metadata confirmation")
        entries = reconciliation["entries"]
        verified = reconciliation["verified"]
        upload_index = reconciliation["upload_index"]
        if (
            normalized_method == "PUT"
            and isinstance(bucket_path, str)
            and isinstance(entries, list)
            and isinstance(verified, Mapping)
            and isinstance(upload_index, int)
            and upload_index < len(entries)
        ):
            entry = entries[upload_index]
            expected_path = bucket_path + "/" + urllib.parse.quote(
                entry["name"],
                safe="",
            )
            data = verified.get(("publication", entry["name"]))
            if (
                path != expected_path
                or reconciliation["upload_in_flight"] is True
                or set(kwargs) != {"data", "content_type", "accept"}
                or not isinstance(data, bytes)
                or kwargs.get("data") != data
                or len(data) != entry["size"]
                or hashlib.md5(data).hexdigest() != entry["md5"]  # noqa: S324
                or hashlib.sha256(data).hexdigest() != entry["sha256"]
                or kwargs.get("content_type") != "application/octet-stream"
                or kwargs.get("accept") != (200, 201, 202)
            ):
                _fail("R7 bounded upload request differs")
            store._recheck_remote_boundary()  # type: ignore[attr-defined]
            reconciliation["upload_in_flight"] = True
            result = original_request(
                instance,
                normalized_method,
                safe_url,
                **kwargs,
            )
            reconciliation["upload_in_flight"] = False
            reconciliation["upload_index"] = upload_index + 1
            return result

        if normalized_method == "POST" and path == publish_path:
            if (
                not isinstance(entries, list)
                or reconciliation["upload_index"] != len(entries)
                or reconciliation["upload_in_flight"] is True
                or reconciliation["prepared_durable"] is not True
                or reconciliation["publish_intent_durable"] is not True
                or reconciliation["publish_post_attempted"] is True
                or set(kwargs) != {"accept"}
                or kwargs.get("accept") != (200, 201, 202, 409)
            ):
                _fail("R7 publish request preceded its exact durable gates")
            instance.gate_record(
                current,
                record_id,
                reconciliation["manifest"]["metadata"],
                entries,
                str(incident["doi"]),
                published=False,
            )
            store._recheck_remote_boundary()  # type: ignore[attr-defined]
            reconciliation["publish_post_attempted"] = True
            return original_request(
                instance,
                normalized_method,
                safe_url,
                **kwargs,
            )

        _fail("R7 Zenodo mutation escaped the exact C2 state machine")

    def reconcile_exact_record(
        evidence: Mapping[str, Any],
        evidence_path: pathlib.Path,
        pinned_manifest_path: pathlib.Path,
        pinned_root: pathlib.Path,
        manifest: Mapping[str, Any],
        execution_head: str,
        verified: Mapping[tuple[str, str], bytes],
        client: Any,
        secrets_by_name: Mapping[str, str],
    ) -> dict[str, Any]:
        incident = R6_DRAFT_METADATA_INCIDENT
        if (
            reconcile_record
            != (int(incident["record_id"]), str(incident["doi"]))
            or getattr(store, "_record_created_reconciliation_armed", False)
            is not True
            or evidence.get("phase") != incident["phase"]
            or evidence.get("state") != incident["state"]
            or evidence.get("record_id") != incident["record_id"]
            or evidence.get("doi") != incident["doi"]
        ):
            _fail("R7 resume input differs from the exact durable C2 checkpoint")
        zenodo_token = secrets_by_name.get(
            publisher_module.zenodo.TOKEN_ENVIRONMENT_VARIABLE,
            "",
        )
        if not isinstance(zenodo_token, str) or not zenodo_token:
            _fail("R7 reconciliation lacks its validated Zenodo credential")
        state, current = _gate_r7_owned_inventory_identity(
            publisher_module,
            manifest,
            client,
            zenodo_token,
        )
        store._recheck_remote_boundary()  # type: ignore[attr-defined]
        _validate_r7_record_identity(
            publisher_module,
            manifest,
            state,
            current,
            require_exact_draft_metadata=False,
        )
        preflight_mismatches: tuple[str, ...] | None = None
        if state == "draft":
            preflight_mismatches = _r7_draft_metadata_mismatch_keys(
                publisher_module,
                current.get("metadata"),
                manifest["metadata"],
            )
            print(
                "VRTCORE_H3_R8_CREATOR_NORMALIZATION="
                + (
                    "NULL_AFFILIATION_ACCEPTED"
                    if current.get("metadata", {}).get("creators")
                    != manifest["metadata"]["creators"]
                    else "EXACT"
                )
            )
            print(
                "VRTCORE_H3_R8_METADATA_PRECONVERGED="
                + ("true" if not preflight_mismatches else "false")
            )
        entries = publisher_module._shared_entries(manifest["files"])
        reconciliation.update(
            {
                "inventory_complete": True,
                "manifest": manifest,
                "entries": entries,
                "verified": verified,
                "metadata_preconverged": preflight_mismatches == (),
                "metadata_preflight_mismatches": preflight_mismatches,
            }
        )
        if original_resume is None:
            _fail("R7 reconciliation resume function is unavailable")
        result = original_resume(
            evidence,
            evidence_path,
            pinned_manifest_path,
            pinned_root,
            manifest,
            execution_head,
            verified,
            client,
            secrets_by_name,
        )
        if (
            result.get("record_id") != incident["record_id"]
            or result.get("doi") != incident["doi"]
        ):
            _fail("R7 publisher result changed the exact C2 record identity")
        return result

    publisher_module._create_consumption_receipt = checkpointing_exclusive_writer
    publisher_module._atomic_recovery_evidence = checkpointing_atomic_writer
    publisher_module._acquire_remote_consumption_lock = reject_new_consumption_lock
    if reconcile_record is not None:
        if client_type is None:
            _fail("R7 reconciliation client type is unavailable")
        client_type.__init__ = extended_client_init
        client_type.request = guarded_request
        client_type.create_paper = reject_create_paper
        client_type.wait_for_editable_metadata = wait_for_semantically_exact_metadata
        client_type.gate_record = gate_semantically_exact_record
        publisher_module._resume_publication = reconcile_exact_record
    try:
        try:
            return callable_value(manifest_path, root)
        except publisher_module.zenodo.ZenodoError as exc:
            if isinstance(exc, zenodo.ZenodoError):
                raise
            raise zenodo.ZenodoError(str(exc)) from None
    finally:
        if client_type is not None:
            client_type.__init__ = original_client_init
            client_type.request = original_request
            client_type.create_paper = original_create_paper
            client_type.wait_for_editable_metadata = original_wait_for_editable_metadata
            client_type.gate_record = original_gate_record
            publisher_module._resume_publication = original_resume
        publisher_module._create_consumption_receipt = original_exclusive
        publisher_module._atomic_recovery_evidence = original_atomic
        publisher_module._acquire_remote_consumption_lock = original_acquire


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument(
        "--verify-basis",
        action="store_true",
        help="validate the committed H3 E1 recovery basis and local E1 objects",
    )
    operations.add_argument(
        "--prepare",
        action="store_true",
        help="create/read back authorization_consumed or restore an exact receipt",
    )
    operations.add_argument(
        "--publish",
        action="store_true",
        help="resume E1 with remote checkpoints and persist the final receipt",
    )
    parser.add_argument("--execution-root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--controller-parent")
    parser.add_argument("--github-output", type=pathlib.Path)
    return parser


def _write_outputs(path: pathlib.Path | None, values: Mapping[str, object]) -> None:
    if path is None:
        return
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            for key, raw in values.items():
                value = str(raw).lower() if isinstance(raw, bool) else str(raw)
                if (
                    not re.fullmatch(r"[a-z][a-z0-9_]*", key)
                    or not value
                    or "\n" in value
                    or "\r" in value
                ):
                    _fail("unsafe GitHub output value")
                handle.write(f"{key}={value}\n")
    except OSError as exc:
        _fail(f"cannot write GitHub output: {exc}")


def _controller_store(args: argparse.Namespace) -> RecoveryReceiptStore:
    if not isinstance(args.controller_parent, str):
        _fail("controller parent argument is required")
    token = os.environ.get("GITHUB_TOKEN", "")
    api = GitHubAPI(token)
    return RecoveryReceiptStore(
        args.execution_root.resolve(),
        api,
        controller_parent=args.controller_parent,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.verify_basis:
            basis = load_recovery_basis()
            validate_e1_repository_objects(args.execution_root.resolve(), basis)
            print("VRTCORE_H3_E1_RECOVERY_BASIS=VALID")
            return 0
        store = _controller_store(args)
        if args.publish:
            store.arm_exact_record_created_reconciliation()
        finalized, tip = store.restore_or_bootstrap()
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
                "VRTCORE_H3_E1_RECOVERY_PREPARE="
                + ("FINALIZED" if finalized else "CHECKPOINTED")
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
            print("VRTCORE_H3_E1_RECOVERY_PUBLICATION=ALREADY_FINALIZED")
            return 0
        if not args.publish:
            _fail("no recovery controller operation was selected")
        os.environ["GITHUB_SHA"] = EXPECTED["e1"]
        result = run_publisher_with_checkpoints(
            store.manifest_path,
            store.root,
            store,
            reconcile_record=(
                int(R6_DRAFT_METADATA_INCIDENT["record_id"]),
                str(R6_DRAFT_METADATA_INCIDENT["doi"]),
            ),
        )
        if (
            result.get("phase") != "public_verified"
            or result.get("state") != "published"
        ):
            _fail("E1 publisher did not return final public evidence")
        final_commit = store.persist_final()
        _write_outputs(
            args.github_output,
            {
                "status": 0,
                "finalized": False,
                "phase": "public_verified",
                "state": "published",
                "receipt_commit": final_commit,
            },
        )
        print("VRTCORE_H3_E1_RECOVERY_PUBLICATION=PUBLISHED")
        return 0
    except tuple(_ZENODO_ERROR_TYPES) as exc:
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
