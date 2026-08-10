#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed QIK-VRT publication planner and explicitly gated publisher."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_initial_acceptance_gate as effect_authorization
from tools import qikvrt_github_publish_runtime as github_publish_runtime
from tools import qikvrt_integrity
from tools import qikvrt_runtime_logger as qlog
from tools.qikvrt_subprocess import run_bounded

CONFIRMATION = "PUBLISH_QIKVRT"
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QIK-VRT CI/CD: dry-run by default; publication requires explicit opt-in."
    )
    parser.add_argument("--mode", choices=("dry-run", "plan", "execute"), default="dry-run")
    parser.add_argument("--evidence-dir", default=".qikvrt/evidence")
    parser.add_argument("--github-enable", action="store_true")
    parser.add_argument("--github-push", action="store_true")
    parser.add_argument("--github-release", action="store_true")
    parser.add_argument("--github-repository", default="", metavar="OWNER/REPO")
    parser.add_argument("--github-remote", default="origin")
    parser.add_argument("--github-base", default="main")
    parser.add_argument("--github-branch", default="main")
    parser.add_argument("--github-tag", default="qikvrt-current")
    parser.add_argument("--release-title", default="QIK-VRT release")
    parser.add_argument("--release-notes", default="QIK-VRT verified release.")
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--zenodo-enable", action="store_true")
    parser.add_argument("--allow-publish", action="store_true")
    parser.add_argument("--confirm-publish", default="")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _inside_root(raw: str, must_exist: bool = False) -> pathlib.Path:
    candidate = pathlib.Path(raw)
    lexical = candidate if candidate.is_absolute() else ROOT / candidate
    try:
        relative = lexical.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {raw}") from exc
    if not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise ValueError(f"unsafe repository path: {raw}")
    cursor = ROOT
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"repository path contains a symlink: {raw}")
    path = lexical.resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {raw}") from exc
    if must_exist and not path.is_file():
        raise ValueError(f"file does not exist: {raw}")
    return path


def _asset_descriptor(raw: str) -> dict[str, Any]:
    """Bind one release asset to stable in-tree bytes without following links."""
    path = _inside_root(raw, must_exist=True)
    relative = path.relative_to(ROOT.resolve()).as_posix()
    data = qikvrt_integrity._regular_file_bytes(ROOT, relative)
    return {
        "path": relative,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def validate_args(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    for name in ("github_remote", "github_base", "github_branch", "github_tag"):
        value = getattr(args, name)
        if not SAFE_REF.fullmatch(value) or ".." in value or value.endswith("/"):
            errors.append(f"unsafe {name.replace('_', '-')} value")
    if args.github_repository and not SAFE_REPOSITORY.fullmatch(args.github_repository):
        errors.append("github-repository must be OWNER/REPO")
    if args.github_push or args.github_release:
        if not args.github_enable:
            errors.append("github-enable is required for GitHub effects")
        if not args.github_repository:
            errors.append("github-repository is required for GitHub effects")
    if args.asset and not args.github_release:
        errors.append("release assets require github-release")
    if args.zenodo_enable:
        errors.append(
            "zenodo-enable is not implemented by the current reference publisher; "
            "no Zenodo effect can be authorized"
        )
    try:
        _inside_root(args.evidence_dir)
        for asset in args.asset:
            _inside_root(asset, must_exist=True)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    assets = [_asset_descriptor(asset) for asset in args.asset]
    if (
        len({asset["path"] for asset in assets}) != len(assets)
        or len({pathlib.PurePosixPath(asset["path"]).name for asset in assets}) != len(assets)
    ):
        raise ValueError("release asset paths and basenames must be unique")
    if args.github_push:
        actions.append({
            "effect": "github_push",
            "command": [
                "git", "push", args.github_remote,
                f"HEAD:refs/heads/{args.github_branch}",
            ],
        })
    if args.github_release:
        command = [
            "gh", "release", "create", args.github_tag,
            "--repo", args.github_repository,
            "--target", args.github_branch,
            "--title", args.release_title,
            "--notes", args.release_notes,
        ]
        command.extend(str(ROOT / asset["path"]) for asset in assets)
        actions.append({"effect": "github_release", "command": command})
    return {
        "mode": args.mode,
        "default_is_non_effectful": args.mode in {"dry-run", "plan"},
        "github_repository": args.github_repository or "NONE",
        "github_remote": args.github_remote,
        "github_base": args.github_base,
        "github_branch": args.github_branch,
        "github_tag": args.github_tag,
        "zenodo_integration_supported": False,
        "assets": assets,
        "actions": actions,
    }


def run_master_gate() -> tuple[int, str, str]:
    try:
        process = run_bounded(
            [sys.executable, "-B", str(ROOT / "tools/qikvrt_master_acceptance_gate.py")],
            cwd=ROOT,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "QIKVRT_LAUNCHED_BY_QIKVRT": "1",
            },
            timeout=900,
            max_output_bytes=4 * 1024 * 1024,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return 1, "", f"master gate could not start: {exc}"
    if process.timed_out:
        return 1, process.stdout, "master gate timed out\n" + process.stderr
    if process.output_limit_exceeded:
        return 1, process.stdout, "master gate output limit exceeded\n" + process.stderr
    return process.returncode, process.stdout, process.stderr


def publisher_effect_is_authorized() -> bool:
    """Require the publisher's own operation scope, including on direct use."""
    return effect_authorization.require_acceptance("cicd-publish")


def _redact(text: str) -> str:
    patterns = (
        r"(?i)(https?://)[^/@\s]+@",
        r"(?i)(authorization:\s*(?:bearer|token)\s+)[^\s]+",
        r"(?i)((?:token|password|secret)=)[^\s]+",
        r"gh[pousr]_[A-Za-z0-9_]{20,}",
    )
    result = text
    for pattern in patterns:
        result = re.sub(pattern, r"\1[REDACTED]" if "(" in pattern else "[REDACTED]", result)
    return result[-8000:]


def _run(command: list[str], timeout: int = 180) -> dict[str, Any]:
    actual_command = command
    if command and command[0] == "gh":
        state, gh_path, _steps, reason = github_publish_runtime.resolve_exact_gh(
            install=False, accept_third_party=False
        )
        if state != "READY" or gh_path is None:
            return {
                "command": command,
                "returncode": 20 if state == "CLI_REQUIRED" else 1,
                "stdout": "",
                "stderr": _redact(reason),
            }
        actual_command = [str(gh_path), *command[1:]]
    try:
        process = run_bounded(
            actual_command,
            cwd=ROOT,
            timeout=timeout,
            max_output_bytes=2 * 1024 * 1024,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {"command": actual_command, "returncode": 1, "stdout": "", "stderr": str(exc)}
    if process.timed_out or process.output_limit_exceeded:
        reason = "command timed out" if process.timed_out else "command output limit exceeded"
        return {
            "command": actual_command,
            "returncode": 1,
            "stdout": _redact(process.stdout or ""),
            "stderr": reason + "\n" + _redact(process.stderr or ""),
        }
    return {
        "command": actual_command,
        "returncode": process.returncode,
        "stdout": _redact(process.stdout or ""),
        "stderr": _redact(process.stderr or ""),
    }


def _github_repository_from_remote(remote_url: str) -> str | None:
    """Return a normalized OWNER/REPO only for an unambiguous GitHub URL."""
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


def _ls_remote_hashes(result: dict[str, Any]) -> set[str]:
    hashes: set[str] = set()
    for line in str(result.get("stdout", "")).splitlines():
        fields = line.split()
        if len(fields) == 2 and re.fullmatch(r"[0-9a-fA-F]{40}", fields[0]):
            hashes.add(fields[0].lower())
    return hashes


def _verify_plan_assets(
    plan: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]], str]:
    """Verify planned release bytes are stable, tracked and identical to HEAD."""
    steps: list[dict[str, Any]] = []
    raw_assets = plan.get("assets", [])
    if not isinstance(raw_assets, list):
        return False, steps, "release asset plan must be a list"
    seen_paths: set[str] = set()
    seen_names: set[str] = set()
    for raw_descriptor in raw_assets:
        if not isinstance(raw_descriptor, dict) or set(raw_descriptor) != {
            "path", "bytes", "sha256"
        }:
            return False, steps, "release asset descriptor has an invalid schema"
        relative = raw_descriptor.get("path")
        expected_bytes = raw_descriptor.get("bytes")
        expected_sha256 = raw_descriptor.get("sha256")
        if not isinstance(relative, str):
            return False, steps, "release asset path must be text"
        try:
            relative = qikvrt_integrity._safe_path(relative)
        except ValueError as exc:
            return False, steps, str(exc)
        name = pathlib.PurePosixPath(relative).name
        if relative in seen_paths or name in seen_names:
            return False, steps, "release asset paths and basenames must be unique"
        seen_paths.add(relative)
        seen_names.add(name)
        if type(expected_bytes) is not int or not 0 <= expected_bytes <= qikvrt_integrity.MAX_IMMUTABLE_FILE_BYTES:
            return False, steps, "release asset byte count is invalid"
        if not isinstance(expected_sha256, str) or not qikvrt_integrity.SHA256_RE.fullmatch(
            expected_sha256
        ):
            return False, steps, "release asset SHA-256 is invalid"
        try:
            data = qikvrt_integrity._regular_file_bytes(ROOT, relative)
        except (OSError, RuntimeError, ValueError) as exc:
            return False, steps, f"release asset cannot be read safely: {exc}"
        if len(data) != expected_bytes or hashlib.sha256(data).hexdigest() != expected_sha256:
            return False, steps, f"release asset changed after planning: {relative}"
        commands = (
            ("asset_is_tracked", ["git", "ls-files", "--error-unmatch", "--", relative]),
            ("asset_worktree_object", ["git", "hash-object", "--", relative]),
            ("asset_head_object", ["git", "rev-parse", f"HEAD:{relative}"]),
        )
        object_ids: dict[str, str] = {}
        for label, command in commands:
            result = _run(command)
            result["verification"] = label
            result["asset"] = relative
            steps.append(result)
            if result["returncode"] != 0:
                return False, steps, f"release asset is not tracked at HEAD: {relative}"
            if label != "asset_is_tracked":
                value = str(result["stdout"]).strip().lower()
                if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value):
                    return False, steps, f"release asset object id is invalid: {relative}"
                object_ids[label] = value
        if object_ids["asset_worktree_object"] != object_ids["asset_head_object"]:
            return False, steps, f"release asset does not match HEAD: {relative}"
    return True, steps, "all release assets match the planned bytes and HEAD"


def _release_assets_match(
    release: dict[str, Any], planned: list[dict[str, Any]]
) -> bool:
    """Require GitHub's remote SHA-256 and size for every planned release asset."""
    if not planned:
        return True
    remote = release.get("assets")
    if not isinstance(remote, list):
        return False
    expected = {
        pathlib.PurePosixPath(item["path"]).name: (
            item["bytes"],
            f"sha256:{item['sha256']}",
        )
        for item in planned
    }
    actual: dict[str, tuple[Any, Any]] = {}
    for item in remote:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return False
        actual[item["name"]] = (item.get("size"), item.get("digest"))
    return actual == expected


class PublicationJournal:
    """Durable intent/effect journal that survives failure after a remote effect."""

    def __init__(self, path: pathlib.Path, plan: dict[str, Any]) -> None:
        self.path = path
        self.payload: dict[str, Any] = {
            "schema": "qikvrt_publication_effect_journal_v1",
            "journal_id": path.stem,
            "created_utc": qlog.utc_now(),
            "state": "INITIALIZED",
            "plan": plan,
            "events": [],
            "external_state": "NO_EFFECT_EXECUTED",
        }

    def record(self, state: str, **details: Any) -> None:
        self.payload["state"] = state
        self.payload["updated_utc"] = qlog.utc_now()
        self.payload["external_state"] = details.pop(
            "external_state", self.payload["external_state"]
        )
        events = self.payload["events"]
        assert isinstance(events, list)
        events.append({"state": state, "utc": qlog.utc_now(), **details})
        _atomic_write_json(self.path, self.payload)


def _new_publication_journal(
    args: argparse.Namespace, plan: dict[str, Any]
) -> PublicationJournal:
    directory = _inside_root(args.evidence_dir) / "publication-journal"
    identifier = f"qikvrt-publish-{os.getpid()}-{secrets.token_hex(8)}"
    return PublicationJournal(directory / f"{identifier}.json", plan)


def execute_plan(
    plan: dict[str, Any], journal: PublicationJournal | None = None
) -> tuple[int, list[dict[str, Any]], str]:
    """Run read-only preflights, then exactly the explicitly planned effects."""
    steps: list[dict[str, Any]] = []
    preflights = [
        ["git", "rev-parse", "--is-inside-work-tree"],
        ["git", "rev-parse", "HEAD"],
        ["git", "status", "--porcelain"],
        ["git", "remote", "get-url", "--push", plan["github_remote"]],
    ]
    if plan["actions"]:
        preflights.append([
            sys.executable,
            "-B",
            "tools/qikvrt_github_publish_runtime.py",
            "prepare",
            "--repository",
            plan["github_repository"],
            "--remote",
            plan["github_remote"],
            "--base",
            plan.get("github_base", "main"),
            "--configure-local-git",
            "--require-clean",
            "--json",
        ])
    if any(action["effect"] == "github_release" for action in plan["actions"]):
        preflights.extend((["gh", "--version"], ["gh", "auth", "status"]))
    local_head = ""
    remote_url = ""
    for command in preflights:
        result = _run(command)
        steps.append(result)
        if result["returncode"] != 0:
            if any(part.endswith("qikvrt_github_publish_runtime.py") for part in command):
                return 20, steps, "repository-owned GitHub publication capability preflight failed"
            return 20, steps, "publication preflight failed"
        if command[1:] == ["status", "--porcelain"] and result["stdout"].strip():
            return 20, steps, "tracked and untracked source changes must be committed before publication"
        if command[1:] == ["rev-parse", "HEAD"]:
            local_head = result["stdout"].strip().lower()
            if not re.fullmatch(r"[0-9a-f]{40}", local_head):
                return 20, steps, "local HEAD could not be established"
        if command[1:4] == ["remote", "get-url", "--push"]:
            remote_url = result["stdout"].strip()
    remote_repository = _github_repository_from_remote(remote_url)
    if (
        remote_repository is None
        or remote_repository.casefold() != str(plan["github_repository"]).casefold()
    ):
        return 20, steps, "GitHub push remote does not match the explicitly selected repository"
    assets_ok, asset_steps, asset_reason = _verify_plan_assets(plan)
    steps.extend(asset_steps)
    if not assets_ok:
        return 20, steps, asset_reason
    if journal is None:
        return 20, steps, "durable publication effect journal is required"
    try:
        journal.record(
            "PREPARED",
            local_head=local_head,
            remote_url=remote_url,
            repository=plan["github_repository"],
            external_state="NO_EFFECT_EXECUTED",
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return 20, steps, f"durable publication journal could not be prepared: {exc}"
    steps.append({"journal": str(journal.path), "state": "PREPARED"})
    effect_executed = False
    for action in plan["actions"]:
        if action["effect"] == "github_release":
            assets_ok, asset_steps, asset_reason = _verify_plan_assets(plan)
            steps.extend(asset_steps)
            if not assets_ok:
                code = 1 if effect_executed else 20
                try:
                    journal.record(
                        "ABORTED" if not effect_executed else "EXTERNAL_STATE_UNKNOWN",
                        reason=asset_reason,
                        external_state=(
                            "NO_EFFECT_EXECUTED" if not effect_executed else "PARTIAL_EFFECTS_POSSIBLE"
                        ),
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return code, steps, asset_reason
            branch_check = _run([
                "git", "ls-remote", plan["github_remote"],
                f"refs/heads/{plan['github_branch']}",
            ])
            branch_check["verification"] = "release_target_branch_matches_local_head"
            steps.append(branch_check)
            if branch_check["returncode"] != 0 or local_head not in _ls_remote_hashes(branch_check):
                code = 1 if effect_executed else 20
                try:
                    journal.record(
                        "ABORTED" if not effect_executed else "EXTERNAL_STATE_UNKNOWN",
                        reason="release target branch preflight failed",
                        external_state=(
                            "NO_EFFECT_EXECUTED" if not effect_executed else "PARTIAL_EFFECTS_POSSIBLE"
                        ),
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return code, steps, "release target branch does not match the verified local HEAD"
        result = _run(action["command"], timeout=600)
        result["effect"] = action["effect"]
        steps.append(result)
        if result["returncode"] != 0:
            try:
                journal.record(
                    "EXTERNAL_STATE_UNKNOWN",
                    effect=action["effect"],
                    command_returncode=result["returncode"],
                    external_state="EFFECT_COMMAND_ATTEMPTED_REMOTE_STATE_UNKNOWN",
                )
            except (OSError, UnicodeError, ValueError):
                pass
            return 1, steps, f"external effect failed: {action['effect']}"
        effect_executed = True
        if action["effect"] == "github_release":
            assets_ok, asset_steps, asset_reason = _verify_plan_assets(plan)
            steps.extend(asset_steps)
            if not assets_ok:
                try:
                    journal.record(
                        "EXTERNAL_STATE_UNKNOWN",
                        effect=action["effect"],
                        reason=asset_reason,
                        external_state="EFFECT_APPLIED_REMOTE_ASSET_BYTES_UNKNOWN",
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return 1, steps, asset_reason
        try:
            journal.record(
                "APPLIED",
                effect=action["effect"],
                command_returncode=0,
                external_state="EFFECT_APPLIED_NOT_YET_VERIFIED",
            )
        except (OSError, UnicodeError, ValueError) as exc:
            return 1, steps, (
                "external effect returned success but durable journal update failed; "
                f"remote state is unknown: {exc}"
            )
        if action["effect"] == "github_push":
            verification = _run([
                "git", "ls-remote", plan["github_remote"],
                f"refs/heads/{plan['github_branch']}",
            ])
            verification["verification"] = "remote_branch_matches_local_head"
            steps.append(verification)
            remote_heads = _ls_remote_hashes(verification)
            if verification["returncode"] != 0 or local_head not in remote_heads:
                try:
                    journal.record(
                        "EXTERNAL_STATE_UNKNOWN",
                        effect=action["effect"],
                        reason="remote branch verification failed",
                        external_state="EFFECT_APPLIED_REMOTE_STATE_UNKNOWN",
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return 1, steps, "GitHub push could not be verified against remote HEAD"
            try:
                journal.record(
                    "VERIFIED",
                    effect=action["effect"],
                    verified_head=local_head,
                    external_state="LATEST_EFFECT_VERIFIED",
                )
            except (OSError, UnicodeError, ValueError) as exc:
                return 1, steps, f"push verified but journal verification update failed: {exc}"
        elif action["effect"] == "github_release":
            verification = _run([
                "gh", "release", "view", plan["github_tag"],
                "--repo", plan["github_repository"],
                "--json", "tagName,targetCommitish,url,assets",
            ])
            verification["verification"] = "github_release_is_readable"
            steps.append(verification)
            try:
                release = json.loads(verification["stdout"])
            except (TypeError, json.JSONDecodeError):
                release = {}
            if (
                verification["returncode"] != 0
                or release.get("tagName") != plan["github_tag"]
                or release.get("targetCommitish") not in {plan["github_branch"], local_head}
                or not str(release.get("url", "")).startswith("https://github.com/")
                or not _release_assets_match(release, plan.get("assets", []))
            ):
                try:
                    journal.record(
                        "EXTERNAL_STATE_UNKNOWN",
                        effect=action["effect"],
                        reason="release metadata verification failed",
                        external_state="EFFECT_APPLIED_REMOTE_STATE_UNKNOWN",
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return 1, steps, "GitHub release could not be verified after creation"
            tag_verification = _run([
                "git", "ls-remote", plan["github_remote"],
                f"refs/tags/{plan['github_tag']}",
                f"refs/tags/{plan['github_tag']}^{{}}",
            ])
            tag_verification["verification"] = "github_release_tag_matches_local_head"
            steps.append(tag_verification)
            if (
                tag_verification["returncode"] != 0
                or local_head not in _ls_remote_hashes(tag_verification)
            ):
                try:
                    journal.record(
                        "EXTERNAL_STATE_UNKNOWN",
                        effect=action["effect"],
                        reason="release tag verification failed",
                        external_state="EFFECT_APPLIED_REMOTE_STATE_UNKNOWN",
                    )
                except (OSError, UnicodeError, ValueError):
                    pass
                return 1, steps, "GitHub release tag does not resolve to the verified local HEAD"
            try:
                journal.record(
                    "VERIFIED",
                    effect=action["effect"],
                    verified_head=local_head,
                    external_state="LATEST_EFFECT_VERIFIED",
                )
            except (OSError, UnicodeError, ValueError) as exc:
                return 1, steps, f"release verified but journal verification update failed: {exc}"
    try:
        journal.record(
            "COMMITTED",
            verified_effect_count=len(plan["actions"]),
            external_state="ALL_PLANNED_EFFECTS_VERIFIED",
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return 1, steps, f"external effects verified but journal commit failed: {exc}"
    return 0, steps, "all explicitly enabled publication effects completed and were verified"


def evidence_payload(
    args: argparse.Namespace,
    plan: dict[str, Any],
    status: str,
    exit_code: int,
    reason: str,
    master_gate_returncode: int,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "_license": {
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "rights_holder": "Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "classification": "cicd_evidence_ledger_json",
        },
        "schema": "qikvrt_cicd_evidence_ledger_v2",
        "created_utc": qlog.utc_now(),
        "status": status,
        "exit_code": exit_code,
        "reason": reason,
        "master_gate_returncode": master_gate_returncode,
        "plan": plan,
        "steps": steps or [],
        "external_done_claim": status == "PASS_EXTERNAL_EFFECTS_VERIFIED",
        "zenodo_done_claim": False,
    }


def _atomic_write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    root = ROOT.resolve()
    candidate = path if path.is_absolute() else ROOT / path
    try:
        lexical_relative = candidate.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"evidence path escapes repository root: {path}") from exc
    if not lexical_relative.parts or any(
        part in {"", ".", ".."} for part in lexical_relative.parts
    ):
        raise ValueError(f"unsafe evidence path: {path}")
    cursor = candidate.parent
    while True:
        if cursor.is_symlink():
            raise ValueError(f"evidence path contains a symlink: {cursor}")
        if cursor == root:
            break
        parent = cursor.parent
        if parent == cursor:
            raise ValueError(f"evidence path escapes repository root: {path}")
        cursor = parent
    candidate.parent.mkdir(parents=True, exist_ok=True)
    try:
        candidate.parent.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"evidence path escapes repository root: {path}") from exc
    if candidate.is_symlink():
        raise ValueError(f"evidence path must not be a symlink: {path}")
    temporary = candidate.with_name(candidate.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, candidate)
        directory_descriptor = os.open(candidate.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_evidence(args: argparse.Namespace, payload: dict[str, Any]) -> pathlib.Path:
    directory = _inside_root(args.evidence_dir)
    path = directory / "QIKVRT_CICD_EVIDENCE_LEDGER.json"
    _atomic_write_json(path, payload)
    return path


def _finish(
    args: argparse.Namespace,
    plan: dict[str, Any],
    status: str,
    exit_code: int,
    reason: str,
    master_gate_returncode: int,
    steps: list[dict[str, Any]] | None = None,
) -> int:
    payload = evidence_payload(
        args, plan, status, exit_code, reason, master_gate_returncode, steps
    )
    path = write_evidence(args, payload)
    stream = sys.stdout if exit_code == 0 else sys.stderr
    print(f"{status} {reason}. Evidence: {path}", file=stream)
    return exit_code


def _run_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate_args(args)
    if errors:
        print("BLOCK " + "; ".join(errors), file=sys.stderr)
        return 1
    plan = build_plan(args)
    if not publisher_effect_is_authorized():
        print(
            "CONTINUE bound launcher effect authorization for cicd-publish is required; "
            "no CI/CD evidence or external effect was written.",
            file=sys.stderr,
        )
        return 20
    gate_code, gate_stdout, gate_stderr = run_master_gate()
    if gate_stdout:
        print(gate_stdout, end="")
    if gate_stderr:
        print(gate_stderr, end="", file=sys.stderr)
    if gate_code != 0:
        if gate_code == 20:
            print(
                "CONTINUE bound launcher effect authorization is required; no CI/CD evidence or external effect was written.",
                file=sys.stderr,
            )
            return 20
        return _finish(
            args, plan, "BLOCK_MASTER_GATE", 1,
            "master verification gate did not PASS", gate_code,
        )
    if args.mode == "dry-run":
        return _finish(
            args, plan, "PASS_DRY_RUN", 0,
            "plan validated; no external effect executed", gate_code,
        )
    if args.mode == "plan":
        return _finish(
            args, plan, "PASS_PUBLISH_PLAN", 0,
            "publish plan materialized; no external effect executed", gate_code,
        )
    if not plan["actions"]:
        return _finish(
            args, plan, "CONTINUE_NO_EFFECT_SELECTED", 20,
            "execute mode requires at least one explicit effect flag", gate_code,
        )
    if not args.allow_publish or args.confirm_publish != CONFIRMATION:
        return _finish(
            args, plan, "CONTINUE_EXPLICIT_CONFIRMATION_REQUIRED", 20,
            f"execute requires --allow-publish and --confirm-publish {CONFIRMATION}", gate_code,
        )
    if not publisher_effect_is_authorized():
        return _finish(
            args, plan, "CONTINUE_EFFECT_AUTHORIZATION_EXPIRED", 20,
            "cicd-publish effect authorization expired before execution", gate_code,
        )
    journal = _new_publication_journal(args, plan)
    code, steps, reason = execute_plan(plan, journal)
    status = "PASS_EXTERNAL_EFFECTS_VERIFIED" if code == 0 else (
        "CONTINUE_PUBLISH_PREFLIGHT" if code == 20 else "BLOCK_PUBLISH_FAILED"
    )
    return _finish(args, plan, status, code, reason, gate_code, steps)


def main(argv: list[str] | None = None) -> int:
    log_managed_by_parent = os.environ.get("QIKVRT_LAUNCHED_BY_QIKVRT") == "1"
    if not log_managed_by_parent:
        qlog.reset_log("tools/qikvrt_cicd_publish.py")
    try:
        code = _run_main(argv)
    except SystemExit as exc:
        code = int(exc.code or 0)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(
            "BLOCK publisher failed; inspect any PREPARED or APPLIED publication journal "
            f"before retrying: {exc}",
            file=sys.stderr,
        )
        code = 1
    if not log_managed_by_parent:
        return qlog.finish(
            code,
            status="PASS" if code == 0 else ("CONTINUE" if code == 20 else "BLOCK"),
            error_class="NONE" if code == 0 else "CICD_PUBLISH_NOT_COMPLETED",
            continue_path="NONE" if code == 0 else "INSPECT_CICD_EVIDENCE_AND_RERUN",
            repair_hint="NONE" if code == 0 else "Inspect QIKVRT_CICD_EVIDENCE_LEDGER.json.",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
