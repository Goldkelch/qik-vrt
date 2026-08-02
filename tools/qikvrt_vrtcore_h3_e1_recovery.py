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
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
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
        """Read one bounded job log; bearer credentials never follow redirects."""
        expected = (
            "/repos/Goldkelch/qik-vrt/actions/jobs/"
            + str(EXPECTED["job_id"])
            + "/logs"
        )
        if path != expected or maximum != EXPECTED["job_log_bytes"]:
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


def persist_receipt_create_only_or_ff(
    api: Any,
    *,
    repository: str,
    ref: str,
    expected_old_sha: str | None,
    commit_sha: str,
) -> str:
    """Perform one create/FF request and one exact reconciliation readback."""
    if repository != EXPECTED["repository"]:
        _fail("receipt repository differs")
    if HEX40.fullmatch(commit_sha) is None:
        _fail("receipt commit identity is invalid")
    if expected_old_sha is not None and HEX40.fullmatch(expected_old_sha) is None:
        _fail("receipt expected-old identity is invalid")
    singular = _head_ref_path(ref, plural=False)
    status, before = _call_api(api, "GET", singular, accept=(200, 404))
    if expected_old_sha is None:
        if status != 404:
            _fail("create-only receipt ref already exists")
        operation = "create"
    else:
        if status != 200:
            _fail("fast-forward receipt ref is absent")
        _validate_ref(before, ref, expected_old_sha)
        operation = "update"
    mutation_status: int | None = None
    changed: dict[str, Any] = {}
    try:
        if operation == "create":
            mutation_status, changed = _call_api(
                api,
                "POST",
                "/repos/Goldkelch/qik-vrt/git/refs",
                payload={"ref": ref, "sha": commit_sha},
                accept=(201, 409, 422),
                allow_ambiguous_transport=True,
            )
            success = 201
        else:
            mutation_status, changed = _call_api(
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
    if mutation_status == success:
        _validate_ref(changed, ref, commit_sha)
    elif mutation_status not in {None, 409, 422}:
        _fail("receipt ref mutation status differs")
    status, after = _call_api(api, "GET", singular, accept=(200, 404))
    if status != 200:
        _fail("receipt ref mutation has no exact readback")
    _validate_ref(after, ref, commit_sha)
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
    """Exact four-path Git receipt chain for one fixed E1 publication."""

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
        self._prepared_replay_pending = False

    def _recheck_remote_boundary(self) -> None:
        if _read_head_ref(self.api, "refs/heads/main") != self.controller_parent:
            _fail("main moved across the exact recovery boundary")
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
        observed = _validate_existing_consumption_tag(self.api, self.manifest)
        if observed != self.remote_consumption:
            _fail("consumption tag moved across the recovery boundary")

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
                if phase == "publish_requested":
                    self._prepared_replay_pending = False
                return self.current_tip
            if self._prepared_replay_pending:
                _fail("prepared replay lacks identical publish_requested confirmation")
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
        raw = _git(
            self.root,
            "show",
            f"{self.current_tip}:{EVIDENCE_RELATIVE.as_posix()}",
        )[1]
        _write_exclusive_regular(self.evidence_path, raw)
        return False, self.current_tip

    def validate_recovery_chain(self, tip: str) -> list[dict[str, Any]]:
        reverse: list[dict[str, Any]] = []
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
            cursor = parent
        chain = list(reversed(reverse))
        phases = [str(item["phase"]) for item in chain]
        if phases != list(CHECKPOINT_PHASES[: len(phases)]):
            _fail("recovery receipt chain is not the exact phase prefix")
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


def run_publisher_with_checkpoints(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    store: CheckpointStore,
    *,
    publish_callable: Callable[[pathlib.Path, pathlib.Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the unchanged publisher with synchronous, remote phase checkpoints.

    The hook wraps only the publisher's atomic evidence writer.  A phase write
    returns to the original publisher only after ``store`` has persisted and
    read back that phase.  Consequently ``create_requested`` is durable before
    ``create_paper`` and ``publish_requested`` before ``publish_and_poll``.
    """
    publisher_module = publish if publish_callable is not None else _load_e1_publisher(root)
    callable_value = publish_callable or publisher_module.publish
    original_exclusive = publisher_module._create_consumption_receipt
    original_atomic = publisher_module._atomic_recovery_evidence
    original_acquire = publisher_module._acquire_remote_consumption_lock

    def reject_new_consumption_lock(*_args: Any, **_kwargs: Any) -> Any:
        _fail("recovery may not acquire or create an authorization lock")

    def persist_after_write(path: pathlib.Path, value: Mapping[str, Any]) -> None:
        phase = value.get("phase")
        if phase in CHECKPOINT_PHASES:
            store.persist_and_readback(path, str(phase))

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

    publisher_module._create_consumption_receipt = checkpointing_exclusive_writer
    publisher_module._atomic_recovery_evidence = checkpointing_atomic_writer
    publisher_module._acquire_remote_consumption_lock = reject_new_consumption_lock
    try:
        try:
            return callable_value(manifest_path, root)
        except publisher_module.zenodo.ZenodoError as exc:
            if isinstance(exc, zenodo.ZenodoError):
                raise
            raise zenodo.ZenodoError(str(exc)) from None
    finally:
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
