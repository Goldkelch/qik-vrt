#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Execute the one authorized audited recovery of VRTCore H3 run 30753751400.

This execution-only helper never creates a GitHub consumption ref and never
creates a Zenodo deposition.  It first proves the exact existing decision lock,
then performs two stable authenticated inventory passes.  Exactly one canonical
owned draft/public record may be resumed.  Any other stable cardinality creates
only a terminal, non-publication recovery receipt requiring a new natural-person
decision.  The promoted candidate is always based on the exact Authority main
and differs only by one recovery/publication receipt plus repository-native
integrity outputs.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

REPOSITORY = "Goldkelch/qik-vrt"
GITHUB_API = "https://api.github.com"
EXPECTED_MAIN = "ad947e6e1c3665c8c9fd838d53ccc2ea17641b1b"
ORIGINAL_EXECUTION_HEAD = "53e757ebce929b40250f90a02ed2a9ec62de6217"
ORIGINAL_EXECUTION_PARENT = "cdb0e9fe8444565df665affa64463295648b1368"
ORIGINAL_RUN_ID = 30753751400
ORIGINAL_ATTEMPT_1_JOB = 91512247885
ORIGINAL_ATTEMPT_2_JOB = 91514264546
CONSUMPTION_REF = (
    "refs/tags/qikvrt-zenodo-auth/"
    "a330351c76975a00afb644e739ed1cc3504b8a63581285b62d68abca13a5d0e1"
)
CONSUMPTION_TAG_OBJECT = "e831a5298cb4b95011b7a53719f784d622ccc42e"
PROXY_BRANCH = "trusted/vrtcore-h3-audited-recovery-run30753751400-v1"
TARGET_BRANCH = "recovery/vrtcore-h3-audited-outcome-run30753751400-v1"
WORKFLOW_NAME = "QIK-VRT audited H3 Zenodo recovery successor"
MANIFEST_RELATIVE = (
    "release/vrtcore-relational-h3-publication-2026-08-02/publish-request.json"
)
PUBLICATION_EVIDENCE_RELATIVE = (
    "release/vrtcore-relational-h3-publication-2026-08-02/zenodo-publication.json"
)
TERMINAL_EVIDENCE_RELATIVE = (
    "release/vrtcore-relational-h3-publication-2026-08-02/"
    "AUDITED_H3_RECOVERY_RECEIPT.json"
)
PROXY_SCOPE = frozenset(
    {
        ".github/workflows/qikvrt_vrtcore_h3_audited_recovery.yml",
        "tools/qikvrt_vrtcore_h3_audited_recovery.py",
        "tests/test_vrtcore_h3_audited_recovery.py",
        "REPOSITORY_FILE_MANIFEST.json",
        "REPOSITORY_FILE_MANIFEST.json.sha256",
        "SHA256SUMS.txt",
    }
)
INTEGRITY_PATHS = frozenset(
    {
        "REPOSITORY_FILE_MANIFEST.json",
        "REPOSITORY_FILE_MANIFEST.json.sha256",
        "SHA256SUMS.txt",
    }
)
REQUIRED_GATE_NAMES = frozenset(
    {
        "QIKVRT CI",
        "QIKVRT Collective Proposal Review",
        "QIKVRT repository evidence materialization",
        "QIK-VRT global claim completion",
        "QIKVRT Batch-003 remaining subject disposition",
        "QIKVRT live status watch",
    }
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
MAX_API_BYTES = 8 * 1024 * 1024


class RecoveryBlocked(RuntimeError):
    """The audited recovery stopped before an authorized remote effect."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
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


def block(message: str) -> NoReturn:
    raise RecoveryBlocked(message)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def sanitized_environment(*, include_python: bool = True) -> dict[str, str]:
    allowed = (
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "SYSTEMROOT",
        "HOME",
        "TMPDIR",
    )
    result = {key: value for key in allowed if (value := os.environ.get(key))}
    result.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    if not include_python:
        result.pop("PYTHONDONTWRITEBYTECODE", None)
        result.pop("PYTHONNOUSERSITE", None)
    return result


def run(
    command: Sequence[str],
    *,
    cwd: pathlib.Path,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    accepted: frozenset[int] = frozenset({0}),
    timeout: int = 1800,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else sanitized_environment(),
        input=input_text,
        stdin=None if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode not in accepted:
        block(
            "command failed without exposing credentials: "
            + " ".join(command[:3])
            + f" (exit {completed.returncode})\n"
            + completed.stdout[-4000:]
        )
    return completed


def git(
    root: pathlib.Path,
    *arguments: str,
    accepted: frozenset[int] = frozenset({0}),
    timeout: int = 600,
) -> str:
    return run(
        ["git", *arguments],
        cwd=root,
        accepted=accepted,
        timeout=timeout,
    ).stdout.strip()


def github_request(
    token: str,
    method: str,
    path: str,
    *,
    payload: Mapping[str, Any] | None = None,
    accept: tuple[int, ...] = (200,),
) -> Any:
    prefix = "/repos/Goldkelch/qik-vrt/"
    if not path.startswith(prefix) or any(c in path for c in ("\x00", "\r", "\n", "#")):
        block("GitHub API path escaped the pinned repository")
    if len(token) < 20 or any(character.isspace() for character in token):
        block("GITHUB_TOKEN is unavailable or structurally invalid")
    url = GITHUB_API + path
    body = None if payload is None else json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "qik-vrt-h3-audited-recovery/1",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    response: Any
    try:
        response = opener.open(request, timeout=60)
    except urllib.error.HTTPError as exc:
        response = exc
    except (OSError, urllib.error.URLError) as exc:
        block(f"GitHub API transport failed: {type(exc).__name__}")
    try:
        status = int(response.status)
        if response.geturl() != url:
            block("GitHub API response origin changed")
        raw = response.read(MAX_API_BYTES + 1)
    finally:
        response.close()
    if len(raw) > MAX_API_BYTES:
        block("GitHub API response exceeded its byte bound")
    if status not in accept:
        block(f"GitHub API rejected {method} with HTTP {status}")
    if not raw:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        block("GitHub API returned invalid JSON")
    if token.encode("utf-8") in raw:
        block("GitHub API response contained its bearer credential")
    return value


def exact_remote_head(root: pathlib.Path, ref: str) -> str:
    output = git(root, "ls-remote", "--heads", "origin", ref)
    fields = output.split()
    if len(fields) != 2 or fields[1] != ref or HEX40.fullmatch(fields[0]) is None:
        block("remote branch resolution differs for " + ref)
    return fields[0]


def exact_remote_tag_object(root: pathlib.Path, ref: str) -> str:
    if not ref.startswith("refs/tags/"):
        block("remote consumption identity is not a tag ref")
    output = git(root, "ls-remote", "--refs", "origin", ref)
    fields = output.split()
    if len(fields) != 2 or fields[1] != ref or HEX40.fullmatch(fields[0]) is None:
        block("remote tag resolution differs for " + ref)
    return fields[0]


def verify_proxy_scope(root: pathlib.Path) -> str:
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        block("workflow repository differs")
    if os.environ.get("GITHUB_REF_NAME") != PROXY_BRANCH:
        block("workflow branch differs")
    head = git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if head != os.environ.get("GITHUB_SHA") or HEX40.fullmatch(head) is None:
        block("checked-out proxy head differs from GITHUB_SHA")
    if exact_remote_head(root, "refs/heads/main") != EXPECTED_MAIN:
        block("Authority main lease changed before recovery")
    if exact_remote_head(root, "refs/heads/" + PROXY_BRANCH) != head:
        block("proxy branch head changed before recovery")
    # Inspect ancestry by return code; merge-base emits no output here.
    ancestry = run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_MAIN, head],
        cwd=root,
        accepted=frozenset({0, 1}),
    ).returncode
    if ancestry != 0:
        block("proxy head is not a descendant of exact current main")
    changed = {
        line
        for line in git(
            root,
            "diff",
            "--name-only",
            "--no-renames",
            EXPECTED_MAIN,
            head,
            "--",
        ).splitlines()
        if line
    }
    if changed != set(PROXY_SCOPE):
        block("proxy changed-path scope differs: " + ",".join(sorted(changed)))
    run(
        [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
        cwd=root,
        timeout=600,
    )
    run(
        [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "-v",
            "tests.test_vrtcore_h3_audited_recovery",
        ],
        cwd=root,
        timeout=300,
    )
    return head


def matching_proxy_pr(token: str, head: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode(
        {
            "state": "open",
            "head": "Goldkelch:" + PROXY_BRANCH,
            "base": "main",
            "per_page": 10,
        }
    )
    value = github_request(
        token,
        "GET",
        "/repos/Goldkelch/qik-vrt/pulls?" + query,
    )
    if not isinstance(value, list):
        block("GitHub pull-list response is not an array")
    matches = [
        item
        for item in value
        if isinstance(item, dict)
        and isinstance(item.get("head"), dict)
        and item["head"].get("sha") == head
        and item["head"].get("ref") == PROXY_BRANCH
        and isinstance(item.get("base"), dict)
        and item["base"].get("sha") == EXPECTED_MAIN
        and item["base"].get("ref") == "main"
    ]
    if len(matches) > 1:
        block("multiple open proxy PRs bind the same recovery head")
    return matches[0] if matches else None


def latest_runs_by_name(runs: Sequence[Any], current_run_id: int) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for raw in runs:
        if not isinstance(raw, dict):
            continue
        run_id = raw.get("id")
        name = raw.get("name")
        if (
            not isinstance(run_id, int)
            or run_id == current_run_id
            or not isinstance(name, str)
            or name == WORKFLOW_NAME
            or raw.get("head_sha") != os.environ.get("GITHUB_SHA")
        ):
            continue
        current = latest.get(name)
        if current is None or int(current.get("id", 0)) < run_id:
            latest[name] = raw
    return latest


def wait_for_exact_head_gates(token: str, head: str) -> int | None:
    current_run_id = int(os.environ.get("GITHUB_RUN_ID", "0"))
    deadline = time.monotonic() + 30 * 60
    pr: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        pr = matching_proxy_pr(token, head)
        if pr is not None:
            break
        time.sleep(5)
    if pr is None:
        block("proxy PR was not opened before the bounded wait expired")
    pr_number = pr.get("number")
    if not isinstance(pr_number, int):
        block("proxy PR lacks a numeric identity")

    while time.monotonic() < deadline:
        current = github_request(
            token,
            "GET",
            f"/repos/Goldkelch/qik-vrt/pulls/{pr_number}",
        )
        if not isinstance(current, dict) or not isinstance(current.get("head"), dict):
            block("proxy PR reobservation differs")
        current_head = current["head"].get("sha")
        if current_head != head:
            print("AUDITED_RECOVERY_PROXY_HEAD_SUPERSEDED_NO_EFFECT=true")
            return None
        query = urllib.parse.urlencode({"head_sha": head, "per_page": 100})
        listing = github_request(
            token,
            "GET",
            "/repos/Goldkelch/qik-vrt/actions/runs?" + query,
        )
        if not isinstance(listing, dict) or not isinstance(
            listing.get("workflow_runs"), list
        ):
            block("workflow-run listing differs")
        latest = latest_runs_by_name(listing["workflow_runs"], current_run_id)
        required = {name: latest.get(name) for name in REQUIRED_GATE_NAMES}
        if any(value is None for value in required.values()):
            time.sleep(10)
            continue
        if any(value.get("status") != "completed" for value in latest.values()):
            time.sleep(10)
            continue
        bad = {
            name: value.get("conclusion")
            for name, value in latest.items()
            if value.get("conclusion") not in {"success", "skipped", "neutral"}
        }
        if bad:
            block(
                "exact-head gate matrix contains a non-success disposition: "
                + json.dumps(bad, sort_keys=True)
            )
        if any(value.get("conclusion") != "success" for value in required.values()):
            block("one or more required exact-head gates did not succeed")
        print(
            "AUDITED_RECOVERY_PROXY_GATES=TERMINAL_ZERO_FAILURE "
            f"runs={len(latest)}"
        )
        return pr_number
    block("exact-head gate matrix did not become terminal within the bounded wait")


def atomic_secret_free_json(
    path: pathlib.Path,
    value: Mapping[str, Any],
    secrets: Mapping[str, str],
) -> None:
    raw = canonical_json_bytes(value)
    for name, secret in secrets.items():
        if secret and secret.encode("utf-8") in raw:
            block("recovery receipt contains secret bytes for " + name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        block("recovery receipt path is not create-only")
    with temporary.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def terminal_receipt(
    *,
    reason: str,
    remote_consumption: Mapping[str, Any],
    matches: Sequence[tuple[int, str, Mapping[str, Any] | None]],
) -> dict[str, Any]:
    summaries = [
        {
            "record_id": record_id,
            "doi": doi,
            "state": "published" if public is not None else "draft",
        }
        for record_id, doi, public in matches
    ]
    if not summaries:
        state = "NO_ZENODO_EFFECT"
        prior_state = "NO_MATCHING_OWNED_DRAFT_OR_PUBLIC_RECORD_OBSERVED"
    else:
        state = "AMBIGUOUS_MULTIPLE_CANONICAL_MATCHES"
        prior_state = "AMBIGUOUS_MULTIPLE_CANONICAL_OWNED_RECORDS"
    return {
        "_license": {
            "classification": "machine_readable_external_effect_recovery_evidence",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_vrtcore_h3_audited_recovery_terminal_v1",
        "state": state,
        "disposition": "MANUAL_REAUTH_REQUIRED",
        "manual_reauthorization_required": True,
        "reason": reason,
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "repository": REPOSITORY,
        "successor_parent": EXPECTED_MAIN,
        "original_execution": {
            "workflow": "Publish one causally ordered VRTCore stage to Zenodo",
            "run_id": ORIGINAL_RUN_ID,
            "run_attempts": 2,
            "attempt_1_job": ORIGINAL_ATTEMPT_1_JOB,
            "attempt_2_job": ORIGINAL_ATTEMPT_2_JOB,
            "execution_head": ORIGINAL_EXECUTION_HEAD,
            "execution_parent": ORIGINAL_EXECUTION_PARENT,
        },
        "original_run_audit": {
            "github_consumption_lock_created": True,
            "attempt_1_ref_readback_http_status": 404,
            "attempt_1_failed_before_zenodo_client_construction": True,
            "attempt_1_zenodo_create_upload_publish_operations": False,
            "attempt_1_recovery_receipt_persisted": False,
            "attempt_1_actions_artifact_persisted": False,
            "attempt_2_failed_at_stale_expected_parent_before_publisher": True,
            "zenodo_effect_by_original_run": "NONE",
        },
        "remote_consumption": dict(remote_consumption),
        "authenticated_zenodo_inventory": {
            "api_origin": "https://zenodo.org/api",
            "stable_complete_double_pass": True,
            "canonical_match_count": len(summaries),
            "canonical_matches": summaries,
            "prior_remote_effect_state": prior_state,
        },
        "prohibitions": {
            "new_consumption_ref": True,
            "second_deposition": True,
            "unbound_record_adoption": True,
            "publication_without_exact_single_match": True,
        },
        "effects_by_this_recovery_run": {
            "github_consumption_ref_created": False,
            "zenodo_record_created": False,
            "zenodo_file_uploaded": False,
            "zenodo_publish_requested": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "authority_mirror_synchronized": False,
        },
    }


def import_original_publisher(original_root: pathlib.Path) -> tuple[Any, Any]:
    sys.path.insert(0, str(original_root))
    try:
        from tools import qikvrt_zenodo_actions as zenodo  # type: ignore
        from tools import qikvrt_zenodo_publish as publish  # type: ignore
    except Exception as exc:  # noqa: BLE001 - fail closed on exact import
        block(f"cannot import exact original publisher: {type(exc).__name__}")
    return publish, zenodo


def execute_authenticated_reconciliation(
    repository_root: pathlib.Path,
    original_root: pathlib.Path,
) -> tuple[pathlib.Path, dict[str, Any]]:
    if exact_remote_head(
        repository_root, "refs/heads/publication/vrtcore-relational-h3-v1"
    ) != ORIGINAL_EXECUTION_HEAD:
        block("H3 publication branch no longer points to the bound execution head")
    if git(original_root, "rev-parse", "--verify", "HEAD^{commit}") != ORIGINAL_EXECUTION_HEAD:
        block("original worktree is not at the exact execution head")
    if git(original_root, "show", "-s", "--format=%P", "HEAD") != ORIGINAL_EXECUTION_PARENT:
        block("original execution parent differs")
    run(
        [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
        cwd=original_root,
        timeout=600,
    )

    os.environ["GITHUB_REPOSITORY"] = REPOSITORY
    os.environ["GITHUB_SHA"] = ORIGINAL_EXECUTION_HEAD
    os.environ["ZENODO_API_BASE"] = "https://zenodo.org/api"
    publish, zenodo = import_original_publisher(original_root)
    manifest_path = original_root / MANIFEST_RELATIVE
    manifest = publish.load_manifest(manifest_path, original_root)
    secrets = publish._validated_network_secrets()
    zenodo_token = secrets[zenodo.TOKEN_ENVIRONMENT_VARIABLE]
    github_token = secrets[publish.GITHUB_TOKEN_ENVIRONMENT_VARIABLE]
    execution_head = publish._validate_repository_source_head(
        original_root, manifest_path, manifest
    )
    if execution_head != ORIGINAL_EXECUTION_HEAD:
        block("normalized exact execution head differs")
    publish._validate_origin_repository(original_root, manifest["repository"])
    verified = publish.verify_files(manifest, original_root, zenodo_token)
    publish._reject_tokens_in_publication_bytes(
        manifest_path,
        original_root,
        manifest,
        verified,
        secrets,
    )
    if manifest["owner_authorization"]["remote_consumption_ref"] != CONSUMPTION_REF:
        block("derived consumption ref differs from the audited binding")
    observed_tag_object = exact_remote_tag_object(
        repository_root,
        CONSUMPTION_REF,
    )
    if observed_tag_object != CONSUMPTION_TAG_OBJECT:
        block("existing consumption ref points to a different tag object")
    # The original run created the tag ref but its immediate REST ref readback
    # returned 404.  Recovery therefore binds the immutable public Git ref
    # first and passes the exact ref shape into the original hardened tag-object
    # validator.  No ref create/update endpoint is reachable from this script.
    ref_value = {
        "ref": CONSUMPTION_REF,
        "object": {
            "sha": observed_tag_object,
            "type": "tag",
        },
    }
    remote_consumption = publish._read_exact_existing_consumption_lock(
        manifest,
        ORIGINAL_EXECUTION_HEAD,
        github_token,
        ref_value,
    )
    if (
        remote_consumption["ref"] != CONSUMPTION_REF
        or remote_consumption["tag_object"] != CONSUMPTION_TAG_OBJECT
        or remote_consumption["recovery_mode"] != "EXISTING_EXACT_REF_NO_CREATE"
    ):
        block("existing exact consumption lock identity differs")

    client = zenodo.ZenodoClient(zenodo_token, "https://zenodo.org/api")
    entries = publish._shared_entries(manifest["files"])
    matches = publish._canonical_inventory_candidates(
        client,
        zenodo_token,
        manifest["metadata"],
        entries,
    )
    if len(matches) != 1:
        receipt = terminal_receipt(
            reason=(
                "NO_CANONICAL_MATCH"
                if not matches
                else "NON_UNIQUE_CANONICAL_MATCH"
            ),
            remote_consumption=remote_consumption,
            matches=matches,
        )
        terminal_path = original_root / TERMINAL_EVIDENCE_RELATIVE
        atomic_secret_free_json(terminal_path, receipt, secrets)
        return terminal_path, receipt

    evidence_path = original_root / PUBLICATION_EVIDENCE_RELATIVE
    if evidence_path.exists() or evidence_path.is_symlink():
        block("original execution worktree unexpectedly contains publication evidence")
    record_id, doi, already_public = matches[0]
    # The exact record already exists.  Persist its bound identity directly;
    # do not manufacture a create intent and never call the deposition creator.
    record_created = publish._phase_evidence(
        manifest_path,
        original_root,
        manifest,
        ORIGINAL_EXECUTION_HEAD,
        remote_consumption,
        "record_created",
        record_id=record_id,
        doi=doi,
    )
    publish._create_consumption_receipt(evidence_path, record_created, secrets)
    try:
        outcome = publish._complete_exact_record(
            evidence_path,
            manifest_path,
            original_root,
            manifest,
            ORIGINAL_EXECUTION_HEAD,
            remote_consumption,
            record_id,
            doi,
            client,
            verified,
            secrets,
            already_public=already_public,
        )
    except zenodo.ZenodoError:
        # The exact V2 phase receipt is intentionally retained for later
        # reconciliation; no replacement record or lock is ever created.
        raw = json.loads(evidence_path.read_text(encoding="utf-8"))
        outcome = publish._validate_recovery_evidence(
            raw,
            manifest_path,
            original_root,
            manifest,
            ORIGINAL_EXECUTION_HEAD,
        )
    return evidence_path, outcome


def candidate_scope(root: pathlib.Path, head: str, receipt_relative: str) -> None:
    changed = {
        line
        for line in git(
            root,
            "diff",
            "--name-only",
            "--no-renames",
            EXPECTED_MAIN,
            head,
            "--",
        ).splitlines()
        if line
    }
    expected = set(INTEGRITY_PATHS) | {receipt_relative}
    if changed != expected:
        block("candidate changed-path scope differs: " + ",".join(sorted(changed)))


def push_candidate(
    repository_root: pathlib.Path,
    receipt_source: pathlib.Path,
    outcome: Mapping[str, Any],
    github_token: str,
) -> tuple[str, str]:
    if SAFE_BRANCH.fullmatch(TARGET_BRANCH) is None:
        block("target branch name is unsafe")
    existing = git(
        repository_root,
        "ls-remote",
        "--heads",
        "origin",
        "refs/heads/" + TARGET_BRANCH,
    )
    if existing:
        block("target recovery branch already exists")

    with tempfile.TemporaryDirectory(prefix="qikvrt-h3-candidate-") as temporary:
        candidate = pathlib.Path(temporary) / "candidate"
        git(repository_root, "worktree", "add", "--detach", str(candidate), EXPECTED_MAIN)
        try:
            receipt_relative = (
                PUBLICATION_EVIDENCE_RELATIVE
                if receipt_source.name == pathlib.PurePosixPath(
                    PUBLICATION_EVIDENCE_RELATIVE
                ).name
                else TERMINAL_EVIDENCE_RELATIVE
            )
            destination = candidate / receipt_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() or destination.is_symlink():
                block("candidate receipt destination is not create-only")
            shutil.copyfile(receipt_source, destination)
            run(
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "generate"],
                cwd=candidate,
                timeout=600,
            )
            run(
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
                cwd=candidate,
                timeout=600,
            )
            run(["make", "test"], cwd=candidate, timeout=2400)
            run(
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
                cwd=candidate,
                timeout=600,
            )
            status = git(
                candidate,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).splitlines()
            observed = {line[3:] for line in status if line}
            expected = set(INTEGRITY_PATHS) | {receipt_relative}
            if observed != expected:
                block(
                    "candidate worktree delta differs: "
                    + ",".join(sorted(observed))
                )
            git(candidate, "add", "--", *sorted(expected))
            git(candidate, "diff", "--cached", "--check")
            tree = git(candidate, "write-tree")
            timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
            commit_env = sanitized_environment()
            commit_env.update(
                {
                    "GIT_AUTHOR_NAME": "QIK-VRT Audited Recovery",
                    "GIT_AUTHOR_EMAIL": "qik-vrt-recovery@users.noreply.github.com",
                    "GIT_COMMITTER_NAME": "QIK-VRT Audited Recovery",
                    "GIT_COMMITTER_EMAIL": "qik-vrt-recovery@users.noreply.github.com",
                    "GIT_AUTHOR_DATE": timestamp,
                    "GIT_COMMITTER_DATE": timestamp,
                }
            )
            message = (
                "zenodo: persist audited VRTCore H3 recovery outcome\n\n"
                f"Original run: {ORIGINAL_RUN_ID}\n"
                f"Original execution head: {ORIGINAL_EXECUTION_HEAD}\n"
                f"Existing consumption ref: {CONSUMPTION_REF}\n"
                f"Existing tag object: {CONSUMPTION_TAG_OBJECT}\n"
                f"Outcome state: {outcome.get('state')}\n"
                "No new consumption ref or Zenodo deposition was created.\n"
                "PASS, FINAL_PASS, and EFFECT_ACK_DONE are not claimed.\n"
            )
            commit = run(
                ["git", "commit-tree", tree, "-p", EXPECTED_MAIN],
                cwd=candidate,
                env=commit_env,
                input_text=message,
                timeout=300,
            ).stdout.strip()
            if HEX40.fullmatch(commit) is None:
                block("candidate commit identity is invalid")
            candidate_scope(candidate, commit, receipt_relative)
            encoded = base64.b64encode(
                ("x-access-token:" + github_token).encode("utf-8")
            ).decode("ascii")
            push_env = sanitized_environment()
            push_env.update(
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                    "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic " + encoded,
                }
            )
            run(
                [
                    "git",
                    "push",
                    "--porcelain",
                    "origin",
                    commit + ":refs/heads/" + TARGET_BRANCH,
                ],
                cwd=candidate,
                env=push_env,
                timeout=600,
            )
            if exact_remote_head(
                candidate, "refs/heads/" + TARGET_BRANCH
            ) != commit:
                block("target branch readback differs")
            print(f"AUDITED_RECOVERY_TARGET_BRANCH={TARGET_BRANCH}")
            return commit, tree
        finally:
            with contextlib.suppress(Exception):
                git(repository_root, "worktree", "remove", "--force", str(candidate))


def execute(root: pathlib.Path) -> int:
    head = verify_proxy_scope(root)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    zenodo_token = os.environ.get("ZENODO_ACCESS_TOKEN", "")
    if len(github_token) < 20 or len(zenodo_token) < 20:
        block("required GitHub or Zenodo recovery credential is absent")
    proxy_pr = wait_for_exact_head_gates(github_token, head)
    if proxy_pr is None:
        return 0
    if exact_remote_head(root, "refs/heads/main") != EXPECTED_MAIN:
        block("Authority main changed after proxy gates")

    with tempfile.TemporaryDirectory(prefix="qikvrt-h3-original-") as temporary:
        original = pathlib.Path(temporary) / "original"
        git(root, "worktree", "add", "--detach", str(original), ORIGINAL_EXECUTION_HEAD)
        try:
            receipt_source, outcome = execute_authenticated_reconciliation(root, original)
            if exact_remote_head(root, "refs/heads/main") != EXPECTED_MAIN:
                block("Authority main changed during authenticated reconciliation")
            commit, tree = push_candidate(
                root,
                receipt_source,
                outcome,
                github_token,
            )
        finally:
            with contextlib.suppress(Exception):
                git(root, "worktree", "remove", "--force", str(original))
    print(f"AUDITED_RECOVERY_PROXY_PR={proxy_pr}")
    print(f"AUDITED_RECOVERY_TARGET_HEAD={commit}")
    print(f"AUDITED_RECOVERY_TARGET_TREE={tree}")
    print(f"AUDITED_RECOVERY_OUTCOME_STATE={outcome.get('state')}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        block("only the explicit --execute audited recovery mode is supported")
    try:
        return execute(pathlib.Path.cwd().resolve())
    except RecoveryBlocked as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
