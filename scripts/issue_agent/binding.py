#!/usr/bin/env python3
"""Shared exact-binding validation for repository-native issue work."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
POLICY_PATH = "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"
REGISTRY_PATH = "registry/NODEMESH_INDEX.json"
INTAKE_CODE_PATHS = (
    "scripts/issue_agent/binding.py",
    "scripts/issue_agent/epoch.py",
    "scripts/issue_agent/finalize.py",
    "scripts/issue_agent/handlers.py",
    "scripts/issue_agent/infer.py",
    "scripts/issue_agent/materialize.py",
    "scripts/issue_agent/promote.py",
    "scripts/issue_agent/validate.py",
)
ISSUE_SNAPSHOT_KEYS = (
    "number",
    "title",
    "body",
    "author",
    "author_type",
    "html_url",
    "created_at",
    "updated_at",
)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def json_loads_strict(value: str | bytes) -> Any:
    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON number: {token}")

    return json.loads(
        value,
        object_pairs_hook=_unique_object,
        parse_constant=reject_constant,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def issue_snapshot(request_value: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": request_value.get("issue_number", request_value.get("number")),
        **{key: request_value.get(key) for key in ISSUE_SNAPSHOT_KEYS if key != "number"},
    }


def code_set_sha256(blobs: dict[str, bytes]) -> str:
    projection = [
        {"path": path, "sha256": sha256_bytes(blobs[path])}
        for path in sorted(blobs)
    ]
    return sha256_bytes(canonical_bytes(projection))


def worktree_code_sha256(root: Path) -> str:
    return code_set_sha256({path: (root / path).read_bytes() for path in INTAKE_CODE_PATHS})


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.output.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git binding read failed: {detail}") from exc


def _git_blob(root: Path, commit: str, path: str) -> bytes:
    if path not in {POLICY_PATH, REGISTRY_PATH, *INTAKE_CODE_PATHS}:
        raise ValueError("request references an untrusted binding path")
    return _git(root, "show", f"{commit}:{path}")


def _canonical_string_list(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or value != sorted(set(value))
        or not all(isinstance(item, str) and "/" in item for item in value)
    ):
        raise ValueError(f"{label} is not a canonical repository list")
    return value


def validate_request(
    request_value: Any,
    *,
    repository_root: Path,
    verify_git: bool,
) -> dict[str, Any]:
    if not isinstance(request_value, dict) or request_value.get("schema") != "qikvrt_issue_agent_request_v2":
        raise ValueError("issue-agent request schema is invalid")
    repository = request_value.get("repository")
    issue_number = request_value.get("issue_number")
    if not isinstance(repository, str) or "/" not in repository:
        raise ValueError("issue-agent repository is invalid")
    if type(issue_number) is not int or issue_number < 1:
        raise ValueError("issue-agent issue number is invalid")
    binding = request_value.get("binding")
    trigger = request_value.get("trigger")
    if not isinstance(binding, dict) or not isinstance(trigger, dict):
        raise ValueError("issue-agent binding or trigger is invalid")

    fingerprint = request_value.get("request_fingerprint")
    if not isinstance(fingerprint, str) or not HEX64.fullmatch(fingerprint):
        raise ValueError("issue-agent request fingerprint is invalid")
    if sha256_bytes(canonical_bytes(binding)) != fingerprint:
        raise ValueError("issue-agent request fingerprint does not match binding")
    if binding.get("issue_number") != issue_number:
        raise ValueError("request issue number differs from binding")
    if not HEX40.fullmatch(str(binding.get("authority_head") or "")):
        raise ValueError("authority head is not a Git object id")
    if not HEX40.fullmatch(str(binding.get("authority_tree") or "")):
        raise ValueError("authority tree is not a Git object id")
    for key in (
        "selected_body_sha256",
        "issue_snapshot_sha256",
        "context_sha256",
        "handler_policy_sha256",
        "registry_sha256",
        "intake_code_sha256",
    ):
        if not HEX64.fullmatch(str(binding.get(key) or "")):
            raise ValueError(f"{key} is not a SHA-256 digest")

    selected_body = trigger.get("selected_body")
    if not isinstance(selected_body, str):
        raise ValueError("selected request body is invalid")
    selected_digest = sha256_bytes(selected_body.encode("utf-8"))
    if trigger.get("selected_body_sha256") != selected_digest or binding.get("selected_body_sha256") != selected_digest:
        raise ValueError("selected request body digest mismatch")
    for key in ("event_name", "event_action", "actor_login"):
        if trigger.get(key) != binding.get(key):
            raise ValueError(f"trigger {key} differs from binding")
    if trigger.get("selected_author_association") != binding.get("selected_author_association"):
        raise ValueError("selected author association differs from binding")
    for key in ("selected_author_login", "selected_source", "source_updated_at"):
        if trigger.get(key) != binding.get(key):
            raise ValueError(f"trigger {key} differs from binding")
    for trigger_key, binding_key in (
        ("comment_id", "comment_id_or_null"),
        ("comment_node_id", "comment_node_id_or_null"),
        ("comment_url", "comment_url_or_null"),
    ):
        if trigger.get(trigger_key) != binding.get(binding_key):
            raise ValueError(f"trigger {trigger_key} differs from binding")
    selected_source = trigger.get("selected_source")
    source_updated_at = trigger.get("source_updated_at")
    if not isinstance(source_updated_at, str) or not source_updated_at:
        raise ValueError("selected source timestamp is invalid")
    if binding.get("event_name") == "issue_comment":
        if selected_source != "ISSUE_COMMENT":
            raise ValueError("issue-comment event must select the exact comment")
        if type(trigger.get("comment_id")) is not int or trigger["comment_id"] < 1:
            raise ValueError("issue-comment binding lacks a valid comment id")
        if not all(isinstance(trigger.get(key), str) and trigger[key] for key in ("comment_node_id", "comment_url")):
            raise ValueError("issue-comment binding lacks immutable comment identity")
        expected_comment_url = (
            f"https://github.com/{repository}/issues/{issue_number}"
            f"#issuecomment-{trigger['comment_id']}"
        )
        if trigger.get("comment_url") != expected_comment_url:
            raise ValueError("issue-comment URL differs from bound repository, issue, or comment id")
    elif binding.get("event_name") in {"issues", "workflow_dispatch"}:
        if selected_source != "ISSUE_BODY":
            raise ValueError("issue-body event must select the issue body")
        if any(trigger.get(key) is not None for key in ("comment_id", "comment_node_id", "comment_url")):
            raise ValueError("issue-body event may not carry comment identity")
        if selected_body != request_value.get("body"):
            raise ValueError("issue-body selection differs from issue snapshot")
        if trigger.get("selected_author_login") != request_value.get("author"):
            raise ValueError("issue-body author differs from issue snapshot")
        if source_updated_at != request_value.get("updated_at"):
            raise ValueError("issue-body timestamp differs from issue snapshot")
    else:
        raise ValueError("request event name is invalid")
    if sha256_bytes(canonical_bytes(issue_snapshot(request_value))) != binding.get("issue_snapshot_sha256"):
        raise ValueError("issue snapshot digest mismatch")

    registered = _canonical_string_list(
        binding.get("active_registered_nodes"),
        "active registered nodes",
        allow_empty=True,
    )
    mesh = _canonical_string_list(binding.get("active_mesh_nodes"), "active mesh nodes")
    if mesh != sorted(set(registered) | {repository}):
        raise ValueError("active mesh nodes differ from Authority union registered nodes")
    handler_policy = request_value.get("handler_policy")
    registry = request_value.get("registry")
    if not isinstance(handler_policy, dict) or handler_policy.get("path") != POLICY_PATH:
        raise ValueError("handler policy path is invalid")
    if not isinstance(registry, dict) or registry.get("path") != REGISTRY_PATH:
        raise ValueError("registry path is invalid")
    if handler_policy.get("sha256") != binding.get("handler_policy_sha256"):
        raise ValueError("handler policy metadata digest mismatch")
    if registry.get("sha256") != binding.get("registry_sha256"):
        raise ValueError("registry metadata digest mismatch")
    if registry.get("active_registered_nodes") != registered or registry.get("active_mesh_nodes") != mesh:
        raise ValueError("registry metadata node projection mismatch")

    if verify_git:
        head = binding["authority_head"]
        _git(repository_root, "cat-file", "-e", f"{head}^{{commit}}")
        actual_tree = _git(repository_root, "rev-parse", f"{head}^{{tree}}").decode().strip()
        if actual_tree != binding["authority_tree"]:
            raise ValueError("authority tree differs from bound head tree")
        policy_bytes = _git_blob(repository_root, head, POLICY_PATH)
        registry_bytes = _git_blob(repository_root, head, REGISTRY_PATH)
        if sha256_bytes(policy_bytes) != binding["handler_policy_sha256"]:
            raise ValueError("bound policy digest differs from exact authority head")
        if sha256_bytes(registry_bytes) != binding["registry_sha256"]:
            raise ValueError("bound registry digest differs from exact authority head")
        policy_value = json_loads_strict(policy_bytes)
        registry_value = json_loads_strict(registry_bytes)
        if policy_value.get("schema") != "qikvrt_issue_agent_deterministic_intake_v1":
            raise ValueError("bound deterministic intake policy schema is invalid")
        if policy_value.get("authority_repository") != repository:
            raise ValueError("bound policy Authority differs from request repository")
        accepted = policy_value.get("accepted_event_actions") or {}
        if binding.get("event_action") not in accepted.get(binding.get("event_name"), []):
            raise ValueError("bound event is not admitted by exact-head policy")
        exact_registered = sorted({
            node.get("repository")
            for node in registry_value.get("nodes", [])
            if isinstance(node, dict)
            and node.get("effective_status") == "ACTIVE"
            and isinstance(node.get("repository"), str)
        })
        if exact_registered != registered:
            raise ValueError("registered node projection differs from exact-head registry")
        code_blobs = {path: _git_blob(repository_root, head, path) for path in INTAKE_CODE_PATHS}
        if code_set_sha256(code_blobs) != binding["intake_code_sha256"]:
            raise ValueError("intake implementation digest differs from exact authority head")
    return request_value
