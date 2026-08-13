#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repository-owned, fail-closed GitHub publication capability runtime.

The runtime owns tool discovery, identity/permission preflight, repository-local
Git credential-helper configuration, and redacted receipts.  It deliberately
does not own or persist credentials and never performs a publish effect during
``offline-check`` or ``prepare``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import urllib.parse
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools.qikvrt_subprocess import run_bounded

CONTRACT_PATH = ROOT / "state/autonomy/GITHUB_PUBLISH_RUNTIME_CONTRACT_V1.json"
LOCK_PATH = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
POSIX_BOOTSTRAP = ROOT / "tools/bootstrap-gh.sh"
WINDOWS_BOOTSTRAP = ROOT / "tools/bootstrap-gh.ps1"
RUNTIME_PATH = ROOT / "tools/qikvrt_github_publish_runtime.py"
DEFAULT_RECEIPT = ".qikvrt/evidence/GITHUB_PUBLISH_RUNTIME_RECEIPT.json"
EXACT_GH_VERSION = "2.96.0"
CONTINUE = 20

SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
GH_VERSION = re.compile(r"^gh version 2\.96\.0 \([0-9]{4}-[0-9]{2}-[0-9]{2}\)$")

SECRET_ENVIRONMENT_NAMES = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
)


class ContractError(RuntimeError):
    """The checked-in publication runtime contract is malformed."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _known_secret_values(environment: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if environment is None else environment
    return sorted(
        {
            value
            for name in SECRET_ENVIRONMENT_NAMES
            if len((value := source.get(name, ""))) >= 8
        },
        key=len,
        reverse=True,
    )


def redact(text: str, environment: Mapping[str, str] | None = None) -> str:
    result = text
    for secret in _known_secret_values(environment):
        result = result.replace(secret, "[REDACTED]")
    substitutions = (
        (r"(?i)(https?://)[^/@\s]+@", r"\1[REDACTED]@"),
        (r"(?i)(authorization:\s*(?:bearer|token|basic)\s+)[^\s]+", r"\1[REDACTED]"),
        (r"(?i)((?:gh_token|github_token|token|password|secret)\s*[=:]\s*)[^\s]+", r"\1[REDACTED]"),
        (r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})", "[REDACTED]"),
    )
    for pattern, replacement in substitutions:
        result = re.sub(pattern, replacement, result)
    return result[-8000:]


def _run(
    command: list[str],
    *,
    timeout: int = 60,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    child_environment = dict(os.environ if environment is None else environment)
    child_environment.setdefault("GH_PROMPT_DISABLED", "1")
    child_environment.setdefault("GIT_TERMINAL_PROMPT", "0")
    try:
        completed = run_bounded(
            command,
            cwd=ROOT,
            env=child_environment,
            timeout=timeout,
            max_output_bytes=2 * 1024 * 1024,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "command": command,
            "returncode": 1,
            "stdout": "",
            "stderr": redact(str(exc), child_environment),
            "raw_stdout": "",
        }
    diagnostic = ""
    returncode = completed.returncode
    if completed.timed_out:
        returncode = 1
        diagnostic = "command timed out"
    elif completed.output_limit_exceeded:
        returncode = 1
        diagnostic = "command output limit exceeded"
    raw_stdout = completed.stdout or ""
    return {
        "command": command,
        "returncode": returncode,
        "stdout": redact(raw_stdout, child_environment),
        "stderr": redact((diagnostic + "\n" + (completed.stderr or "")).strip(), child_environment),
        "raw_stdout": raw_stdout,
    }


def _public_step(result: Mapping[str, Any], name: str) -> dict[str, Any]:
    return {
        "name": name,
        "returncode": int(result.get("returncode", 1)),
        "stdout": str(result.get("stdout", "")),
        "stderr": str(result.get("stderr", "")),
    }


def _load_contract() -> dict[str, Any]:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"publication runtime contract is unreadable: {exc}") from exc
    if not isinstance(contract, dict):
        raise ContractError("publication runtime contract must contain an object")
    return contract


def validate_offline_contract() -> dict[str, Any]:
    """Validate repository-owned capability material without network or auth."""
    contract = _load_contract()
    if contract.get("schema") != "qikvrt_github_publish_runtime_contract_v1":
        raise ContractError("publication runtime contract schema drift")
    if contract.get("state") != "ACTIVE":
        raise ContractError("publication runtime contract is not ACTIVE")

    owned = contract.get("repository_owned")
    if not isinstance(owned, dict):
        raise ContractError("repository_owned must be an object")
    required_paths = {
        "contract": "state/autonomy/GITHUB_PUBLISH_RUNTIME_CONTRACT_V1.json",
        "runtime": "tools/qikvrt_github_publish_runtime.py",
        "bootstrap_posix": "tools/bootstrap-gh.sh",
        "bootstrap_windows": "tools/bootstrap-gh.ps1",
        "workflow": ".github/workflows/qikvrt_github_publish_runtime.yml",
        "tests": "tests/test_qikvrt_github_publish_runtime.py",
        "documentation": "docs/GITHUB_PUBLISH_RUNTIME.md",
    }
    for key, expected in required_paths.items():
        if owned.get(key) != expected:
            raise ContractError(f"repository_owned.{key} does not bind {expected}")
        path = ROOT / expected
        if not path.is_file() or path.is_symlink():
            raise ContractError(f"repository-owned publication path is absent or linked: {expected}")

    toolchain = contract.get("toolchain")
    if not isinstance(toolchain, dict) or toolchain.get("component") != "gh":
        raise ContractError("publication toolchain must bind gh")
    if toolchain.get("exact_version") != EXACT_GH_VERSION:
        raise ContractError("publication toolchain version drift")
    locked_rows = []
    try:
        for line in LOCK_PATH.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                fields = line.split("\t")
                if fields[0] == "gh":
                    locked_rows.append(fields)
    except OSError as exc:
        raise ContractError(f"toolchain lock is unreadable: {exc}") from exc
    if len(locked_rows) != 6 or any(
        len(row) != 7 or row[1] != EXACT_GH_VERSION for row in locked_rows
    ):
        raise ContractError("toolchain lock must contain six exact gh 2.96.0 targets")

    authentication = contract.get("authentication")
    if not isinstance(authentication, dict):
        raise ContractError("authentication contract must be an object")
    if authentication.get("credentials_are_external_capability") is not True:
        raise ContractError("credentials must remain an external capability")
    for key in (
        "credentials_may_be_committed",
        "credentials_may_be_cached",
        "credentials_may_appear_in_receipts",
        "credentials_may_appear_in_logs",
    ):
        if authentication.get(key) is not False:
            raise ContractError(f"authentication.{key} must be false")

    preflight = contract.get("preflight")
    if not isinstance(preflight, dict) or preflight.get("effect_free") is not True:
        raise ContractError("publication prepare preflight must remain effect-free")
    publication = contract.get("publication")
    if not isinstance(publication, dict):
        raise ContractError("publication contract must be an object")
    if publication.get("default_review_object") != "DRAFT_PULL_REQUEST":
        raise ContractError("publication must default to a draft pull request")
    forbidden = set(publication.get("forbidden_without_separate_authorization", []))
    mandatory_forbidden = {
        "MERGE",
        "FORCE_PUSH",
        "RELEASE",
        "DEPLOYMENT",
        "ZENODO_MUTATION",
        "DOI_MUTATION",
        "IETF_MUTATION",
    }
    if not mandatory_forbidden.issubset(forbidden):
        raise ContractError("publication contract weakens consequential-effect boundaries")

    return {
        "schema": "qikvrt_github_publish_runtime_receipt_v1",
        "observed_utc": utc_now(),
        "mode": "OFFLINE_CHECK",
        "state": "REPOSITORY_READY",
        "repository_owned_capability": True,
        "network_used": False,
        "credential_checked": False,
        "credential_persisted": False,
        "toolchain": {
            "component": "gh",
            "exact_version": EXACT_GH_VERSION,
            "locked_targets": len(locked_rows),
            "bootstrap_available": True,
        },
        "next_action": "Run prepare for the selected repository before any publication effect.",
    }


def _bootstrap_command(*, install: bool) -> list[str]:
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WINDOWS_BOOTSTRAP),
            "-PrintPath",
        ]
        command.append("-Install" if install else "-CheckOnly")
        if install:
            command.append("-AcceptThirdParty")
        return command
    command = ["sh", str(POSIX_BOOTSTRAP)]
    command.extend(
        ["--install", "--accept-third-party"] if install else ["--check-only"]
    )
    command.append("--print-path")
    return command


def resolve_exact_gh(
    *, install: bool, accept_third_party: bool
) -> tuple[str, pathlib.Path | None, list[dict[str, Any]], str]:
    steps: list[dict[str, Any]] = []
    if install and not accept_third_party:
        return (
            "BLOCK",
            None,
            steps,
            "--install requires --accept-third-party",
        )
    check = _run(_bootstrap_command(install=False), timeout=120)
    steps.append(_public_step(check, "exact GitHub CLI check"))
    result = check
    if check["returncode"] == CONTINUE and install:
        result = _run(_bootstrap_command(install=True), timeout=600)
        steps.append(_public_step(result, "exact GitHub CLI installation"))
    if result["returncode"] == CONTINUE:
        return (
            "CLI_REQUIRED",
            None,
            steps,
            "GitHub CLI 2.96.0 is absent; run prepare with --install --accept-third-party",
        )
    if result["returncode"] != 0:
        return "BLOCK", None, steps, "exact GitHub CLI bootstrap failed"
    output_lines = [line.strip() for line in str(result["raw_stdout"]).splitlines() if line.strip()]
    if not output_lines:
        return "BLOCK", None, steps, "GitHub CLI bootstrap returned no executable path"
    candidate = pathlib.Path(output_lines[-1]).expanduser()
    if not candidate.is_file() or candidate.is_symlink():
        return "BLOCK", None, steps, "GitHub CLI path is absent or a symlink"
    version = _run([str(candidate), "--version"])
    steps.append(_public_step(version, "exact GitHub CLI execution"))
    first_line = str(version["raw_stdout"]).splitlines()[0] if str(version["raw_stdout"]).splitlines() else ""
    if version["returncode"] != 0 or not GH_VERSION.fullmatch(first_line):
        return "BLOCK", None, steps, "GitHub CLI execution did not prove exact version 2.96.0"
    return "READY", candidate.resolve(), steps, "exact GitHub CLI is ready"


def _normalize_repository_from_remote(remote_url: str) -> str | None:
    value = remote_url.strip()
    patterns = (
        r"https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$",
        r"git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?$",
        r"ssh://git@github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def _valid_ref(value: str) -> bool:
    return bool(
        SAFE_REF.fullmatch(value)
        and ".." not in value
        and "@{" not in value
        and "//" not in value
        and not value.endswith(("/", ".", ".lock"))
    )


def _auth_source() -> str:
    if os.environ.get("GH_TOKEN"):
        return "GH_TOKEN"
    if os.environ.get("GITHUB_TOKEN"):
        return "GITHUB_ACTIONS_TOKEN" if os.environ.get("GITHUB_ACTIONS") == "true" else "GITHUB_TOKEN"
    if os.environ.get("GH_ENTERPRISE_TOKEN") or os.environ.get("GITHUB_ENTERPRISE_TOKEN"):
        return "ENTERPRISE_TOKEN"
    return "GH_SECURE_CREDENTIAL_STORE"


def _configure_local_git_helper(gh_path: pathlib.Path) -> list[dict[str, Any]]:
    executable = str(gh_path).replace("\\", "/")
    helper = f"!{shlex.quote(executable)} auth git-credential"
    key = "credential.https://github.com.helper"
    steps: list[dict[str, Any]] = []
    for name, command in (
        (
            "clear lower-priority GitHub helpers locally",
            ["git", "config", "--local", "--replace-all", key, ""],
        ),
        (
            "bind exact GitHub CLI credential helper locally",
            ["git", "config", "--local", "--add", key, helper],
        ),
    ):
        result = _run(command)
        steps.append(_public_step(result, name))
        if result["returncode"] != 0:
            break
    return steps


def _state_receipt(
    state: str,
    repository: str,
    remote: str,
    base: str,
    steps: list[dict[str, Any]],
    **details: Any,
) -> dict[str, Any]:
    next_actions = {
        "READY": "Execute only the separately authorized draft-PR publication plan, then verify the remote head and PR object.",
        "CLI_REQUIRED": "Rerun prepare with --install --accept-third-party.",
        "CREDENTIAL_REQUIRED": "Run login, or provide a caller-owned GH_TOKEN/GITHUB_TOKEN, then rerun prepare.",
        "PERMISSION_REQUIRED": "Use an identity with push and pull-request permission for the selected repository.",
        "REMOTE_MISMATCH": "Correct the selected repository or Git remote before publication.",
        "DIRTY_WORKTREE": "Commit the intended source bytes and rerun prepare.",
        "BLOCK": "Repair the named repository/runtime gate before publication.",
    }
    return {
        "schema": "qikvrt_github_publish_runtime_receipt_v1",
        "observed_utc": utc_now(),
        "mode": "PREPARE",
        "state": state,
        "repository": repository,
        "remote": remote,
        "base": base,
        "credential_persisted": False,
        "publication_effect_executed": False,
        "steps": steps,
        "next_action": next_actions.get(state, next_actions["BLOCK"]),
        **details,
    }


def prepare(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not SAFE_REPOSITORY.fullmatch(args.repository):
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason="repository must be OWNER/REPO")
    if not SAFE_REMOTE.fullmatch(args.remote):
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason="unsafe Git remote name")
    if not _valid_ref(args.base):
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason="unsafe base ref")
    try:
        offline = validate_offline_contract()
    except ContractError as exc:
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason=str(exc))
    steps.append({"name": "repository-owned capability contract", "returncode": 0, "state": offline["state"]})

    root_check = _run(["git", "rev-parse", "--show-toplevel"])
    steps.append(_public_step(root_check, "repository root"))
    try:
        observed_root = pathlib.Path(str(root_check["raw_stdout"]).strip()).resolve()
    except (OSError, RuntimeError):
        observed_root = pathlib.Path("/")
    if root_check["returncode"] != 0 or observed_root != ROOT.resolve():
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason="runtime is not executing in its bound repository")

    head_check = _run(["git", "rev-parse", "--verify", "HEAD^{commit}"])
    steps.append(_public_step(head_check, "local exact head"))
    local_head = str(head_check["raw_stdout"]).strip().lower()
    if head_check["returncode"] != 0 or not SHA1.fullmatch(local_head):
        return 1, _state_receipt("BLOCK", args.repository, args.remote, args.base, steps, reason="local exact head is unavailable")

    status_check = _run(["git", "status", "--porcelain"])
    steps.append(_public_step(status_check, "local worktree state"))
    clean = status_check["returncode"] == 0 and not str(status_check["raw_stdout"]).strip()
    if args.require_clean and not clean:
        return CONTINUE, _state_receipt(
            "DIRTY_WORKTREE", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=False,
        )

    remote_check = _run(["git", "remote", "get-url", "--push", args.remote])
    steps.append(_public_step(remote_check, "selected Git push remote"))
    remote_url = str(remote_check["raw_stdout"]).strip()
    observed_repository = _normalize_repository_from_remote(remote_url)
    if (
        remote_check["returncode"] != 0
        or observed_repository is None
        or observed_repository.casefold() != args.repository.casefold()
    ):
        return CONTINUE, _state_receipt(
            "REMOTE_MISMATCH", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean,
            observed_repository=observed_repository or "UNRESOLVED",
        )

    gh_state, gh_path, gh_steps, gh_reason = resolve_exact_gh(
        install=args.install, accept_third_party=args.accept_third_party
    )
    steps.extend(gh_steps)
    if gh_state != "READY" or gh_path is None:
        code = CONTINUE if gh_state == "CLI_REQUIRED" else 1
        return code, _state_receipt(
            gh_state, args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean, reason=gh_reason,
        )

    auth = _run([str(gh_path), "auth", "status", "--hostname", "github.com", "--active"])
    steps.append(_public_step(auth, "GitHub authentication"))
    if auth["returncode"] != 0:
        return CONTINUE, _state_receipt(
            "CREDENTIAL_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean,
            gh_path=_display_path(gh_path), auth_source="NONE",
        )

    identity = _run([str(gh_path), "api", "user", "--jq", ".login"])
    steps.append(_public_step(identity, "GitHub identity"))
    login = str(identity["raw_stdout"]).strip()
    if identity["returncode"] != 0 or not login:
        return CONTINUE, _state_receipt(
            "CREDENTIAL_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean,
            gh_path=_display_path(gh_path), auth_source=_auth_source(),
        )

    repository_check = _run([
        str(gh_path), "api", f"repos/{args.repository}", "--jq",
        "{default_branch: .default_branch, push: (.permissions.push // false), visibility: .visibility}",
    ])
    steps.append(_public_step(repository_check, "GitHub repository permission"))
    try:
        repository_metadata = json.loads(str(repository_check["raw_stdout"]))
    except (TypeError, json.JSONDecodeError):
        repository_metadata = {}
    if repository_check["returncode"] != 0:
        return CONTINUE, _state_receipt(
            "PERMISSION_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean, identity=login,
            gh_path=_display_path(gh_path), auth_source=_auth_source(),
        )
    if repository_metadata.get("push") is not True:
        return CONTINUE, _state_receipt(
            "PERMISSION_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean, identity=login,
            repository_visibility=repository_metadata.get("visibility", "UNKNOWN"),
            repository_push_permission=False, gh_path=_display_path(gh_path),
            auth_source=_auth_source(),
        )

    quoted_base = urllib.parse.quote(args.base, safe="")
    ref_check = _run([
        str(gh_path), "api", f"repos/{args.repository}/git/ref/heads/{quoted_base}",
        "--jq", ".object.sha",
    ])
    steps.append(_public_step(ref_check, "GitHub base ref"))
    remote_base_head = str(ref_check["raw_stdout"]).strip().lower()
    if ref_check["returncode"] != 0 or not SHA1.fullmatch(remote_base_head):
        return CONTINUE, _state_receipt(
            "PERMISSION_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean, identity=login,
            repository_push_permission=True, reason="selected base ref is unreadable",
            gh_path=_display_path(gh_path), auth_source=_auth_source(),
        )

    if args.configure_local_git:
        helper_steps = _configure_local_git_helper(gh_path)
        steps.extend(helper_steps)
        if not helper_steps or any(step["returncode"] != 0 for step in helper_steps):
            return 1, _state_receipt(
                "BLOCK", args.repository, args.remote, args.base, steps,
                local_head=local_head, clean_worktree=clean, identity=login,
                repository_push_permission=True,
                reason="repository-local credential helper configuration failed",
                gh_path=_display_path(gh_path), auth_source=_auth_source(),
            )

    transport = _run([
        "git", "ls-remote", "--exit-code", args.remote, f"refs/heads/{args.base}"
    ])
    steps.append(_public_step(transport, "effect-free Git transport probe"))
    advertised_heads = {
        line.split()[0].lower()
        for line in str(transport["raw_stdout"]).splitlines()
        if len(line.split()) == 2 and SHA1.fullmatch(line.split()[0].lower())
    }
    if transport["returncode"] != 0 or remote_base_head not in advertised_heads:
        return CONTINUE, _state_receipt(
            "CREDENTIAL_REQUIRED", args.repository, args.remote, args.base, steps,
            local_head=local_head, clean_worktree=clean, identity=login,
            repository_push_permission=True, remote_base_head=remote_base_head,
            gh_path=_display_path(gh_path), auth_source=_auth_source(),
            reason="Git transport could not reobserve the API-bound base head",
        )

    return 0, _state_receipt(
        "READY", args.repository, args.remote, args.base, steps,
        local_head=local_head, clean_worktree=clean, identity=login,
        repository_visibility=repository_metadata.get("visibility", "UNKNOWN"),
        repository_default_branch=repository_metadata.get("default_branch", "UNKNOWN"),
        repository_push_permission=True, remote_base_head=remote_base_head,
        gh_path=_display_path(gh_path), auth_source=_auth_source(),
        git_credential_helper_configured=bool(args.configure_local_git),
    )


def _display_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _receipt_path(raw: str) -> pathlib.Path:
    candidate = pathlib.Path(raw)
    path = candidate if candidate.is_absolute() else ROOT / candidate
    try:
        lexical_relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("receipt path must remain below .qikvrt/evidence") from exc
    if any(part in {"", ".", ".."} for part in lexical_relative.parts):
        raise ValueError("receipt path contains an unsafe lexical component")
    resolved_parent = path.parent.resolve()
    evidence_root = (ROOT / ".qikvrt/evidence").resolve()
    try:
        resolved_parent.relative_to(evidence_root)
    except ValueError as exc:
        raise ValueError("receipt path must remain below .qikvrt/evidence") from exc
    cursor = path
    while cursor != evidence_root.parent:
        if cursor.is_symlink():
            raise ValueError("receipt path must not contain a symlink")
        if cursor == evidence_root:
            break
        cursor = cursor.parent
    if cursor != evidence_root:
        raise ValueError("receipt path must remain below .qikvrt/evidence")
    return path


def write_receipt(raw_path: str, payload: dict[str, Any]) -> pathlib.Path:
    path = _receipt_path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    data = canonical_json(payload)
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def _emit(payload: dict[str, Any], *, as_json: bool, receipt: str) -> None:
    if receipt:
        path = write_receipt(receipt, payload)
        payload = {**payload, "receipt_path": _display_path(path)}
    if as_json:
        print(canonical_json(payload), end="")
    else:
        print(f"GITHUB_PUBLISH_RUNTIME_STATE={payload['state']}")
        print(f"REPOSITORY={payload.get('repository', 'UNSELECTED')}")
        print(f"LOCAL_HEAD={payload.get('local_head', 'UNOBSERVED')}")
        print(f"NEXT_ACTION={payload.get('next_action', 'NONE')}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    offline = subparsers.add_parser("offline-check", help="validate checked-in capability without network or credentials")
    offline.add_argument("--json", action="store_true")
    offline.add_argument("--receipt", default="")

    prepare_parser = subparsers.add_parser("prepare", help="run effect-free GitHub publication preflight")
    prepare_parser.add_argument("--repository", required=True, metavar="OWNER/REPO")
    prepare_parser.add_argument("--remote", default="origin")
    prepare_parser.add_argument("--base", default="main")
    prepare_parser.add_argument("--install", action="store_true")
    prepare_parser.add_argument("--accept-third-party", action="store_true")
    prepare_parser.add_argument("--configure-local-git", action="store_true")
    prepare_parser.add_argument("--require-clean", action="store_true")
    prepare_parser.add_argument("--json", action="store_true")
    prepare_parser.add_argument("--receipt", default=DEFAULT_RECEIPT)

    login = subparsers.add_parser("login", help="start caller-interactive secure GitHub login")
    login.add_argument("--install", action="store_true")
    login.add_argument("--accept-third-party", action="store_true")

    exact_gh = subparsers.add_parser("gh", help="execute the exact locked GitHub CLI")
    exact_gh.add_argument("--install", action="store_true")
    exact_gh.add_argument("--accept-third-party", action="store_true")
    exact_gh.add_argument("gh_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "offline-check":
        try:
            payload = validate_offline_contract()
            code = 0
        except ContractError as exc:
            payload = {
                "schema": "qikvrt_github_publish_runtime_receipt_v1",
                "observed_utc": utc_now(),
                "mode": "OFFLINE_CHECK",
                "state": "BLOCK",
                "network_used": False,
                "credential_checked": False,
                "credential_persisted": False,
                "reason": str(exc),
                "next_action": "Repair the named repository publication-runtime gate.",
            }
            code = 1
        try:
            _emit(payload, as_json=args.json, receipt=args.receipt)
        except (OSError, ValueError) as exc:
            print(f"BLOCK: publication receipt could not be written: {exc}", file=sys.stderr)
            return 1
        return code
    if args.command == "prepare":
        code, payload = prepare(args)
        try:
            _emit(payload, as_json=args.json, receipt=args.receipt)
        except (OSError, ValueError) as exc:
            print(f"BLOCK: publication receipt could not be written: {exc}", file=sys.stderr)
            return 1
        return code
    if args.command in {"login", "gh"}:
        state, gh_path, steps, reason = resolve_exact_gh(
            install=args.install, accept_third_party=args.accept_third_party
        )
        if state != "READY" or gh_path is None:
            stream = sys.stderr
            print(f"{state}: {reason}", file=stream)
            for step in steps:
                if step.get("stderr"):
                    print(step["stderr"], file=stream)
            return CONTINUE if state == "CLI_REQUIRED" else 1
        if args.command == "login":
            environment = dict(os.environ)
            environment.pop("GH_PROMPT_DISABLED", None)
            completed = subprocess.run(
                [str(gh_path), "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web"],
                cwd=ROOT,
                env=environment,
                check=False,
            )
            return int(completed.returncode)
        forwarded = list(args.gh_args)
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
        if not forwarded:
            print("BLOCK: gh requires arguments after --", file=sys.stderr)
            return 2
        os.execvpe(str(gh_path), [str(gh_path), *forwarded], dict(os.environ))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
