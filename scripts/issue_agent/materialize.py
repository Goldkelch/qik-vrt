#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import canonical_bytes as bound_canonical_bytes
from scripts.issue_agent.binding import issue_snapshot
from scripts.issue_agent.binding import json_loads_strict
from scripts.issue_agent.binding import worktree_code_sha256
from scripts.issue_agent.handlers import validate_policy

MAX_FILES = 40
MAX_BYTES = 180_000
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def context_priority(name: str) -> tuple[int, str] | None:
    if "/" not in name and name.startswith("README") and name.endswith(".md"):
        return (0, name)
    if name.startswith("docs/") and name.endswith(".md"):
        return (1, name)
    if name.startswith("formalization/") and name.endswith((".md", ".lean")):
        return (2, name)
    if name.startswith("spec/") and name.endswith(".md"):
        return (3, name)
    return None


def canonical_bytes(value: object) -> bytes:
    return bound_canonical_bytes(value)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha(value: str, label: str) -> str:
    if not HEX40.fullmatch(value):
        raise SystemExit(f"{label} must be an exact 40-hex Git object id")
    return value


def event_binding(issue: dict, event: dict, event_name: str, event_action: str) -> dict:
    event_issue = event.get("issue")
    if isinstance(event_issue, dict) and event_issue.get("number") != issue.get("number"):
        raise SystemExit("event issue number differs from resolved issue")

    actor = event.get("sender") or {}
    actor_login = actor.get("login") or "UNAVAILABLE"
    comment = event.get("comment") if event_name == "issue_comment" else None
    if event_name == "issue_comment":
        if not isinstance(comment, dict):
            raise SystemExit("issue_comment event is missing its exact comment")
        if isinstance(event_issue, dict) and event_issue.get("pull_request") is not None:
            raise SystemExit("pull-request comments are not issue work orders")
        selected_body = comment.get("body") or ""
        selected_source = "ISSUE_COMMENT"
        selected_author = (comment.get("user") or {}).get("login") or actor_login
        association = comment.get("author_association") or "UNAVAILABLE"
        comment_id = comment.get("id")
        comment_node_id = comment.get("node_id")
        comment_url = comment.get("html_url")
        source_updated_at = comment.get("updated_at") or comment.get("created_at")
        if not isinstance(comment_id, int) or comment_id < 1:
            raise SystemExit("issue comment id is invalid")
    else:
        selected_body = issue.get("body") or ""
        selected_source = "ISSUE_BODY"
        selected_author = (issue.get("user") or {}).get("login") or actor_login
        association = issue.get("author_association") or "UNAVAILABLE"
        comment_id = None
        comment_node_id = None
        comment_url = None
        source_updated_at = issue.get("updated_at")

    selected_bytes = selected_body.encode("utf-8")
    return {
        "event_name": event_name,
        "event_action": event_action,
        "actor_login": actor_login,
        "selected_author_login": selected_author,
        "selected_author_association": association,
        "selected_source": selected_source,
        "selected_body": selected_body,
        "selected_body_sha256": sha256_bytes(selected_bytes),
        "comment_id": comment_id,
        "comment_node_id": comment_node_id,
        "comment_url": comment_url,
        "source_updated_at": source_updated_at,
    }


def repository_context(authority_head: str) -> str:
    selected = []
    total = 0
    tree = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", authority_head],
        stderr=subprocess.STDOUT,
    )
    tracked: list[str] = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0]
        if mode not in {b"100644", b"100755"}:
            continue
        try:
            tracked.append(raw_name.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    prioritized = sorted(
        priority
        for name in tracked
        if (priority := context_priority(name)) is not None
    )
    for _, name in prioritized:
        data = subprocess.check_output(
            ["git", "show", f"{authority_head}:{name}"],
            stderr=subprocess.STDOUT,
        )
        if len(selected) >= MAX_FILES or total + len(data) > MAX_BYTES:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        selected.append((name, text))
        total += len(data)

    lines = [
        "# Repository context for deterministic issue intake",
        "",
        "This context is deterministic, size-bounded, and derived from the exact bound Git tree.",
        "It is evidence input, not an assertion that every included file is relevant.",
        "",
    ]
    for name, text in selected:
        lines.extend([f"## `{name}`", "", text, ""])
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue", required=True)
    p.add_argument("--event", required=True)
    p.add_argument("--event-name", required=True)
    p.add_argument("--event-action", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--authority-head", required=True)
    p.add_argument("--authority-tree", required=True)
    p.add_argument(
        "--policy",
        default="policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json",
    )
    p.add_argument("--registry", default="registry/NODEMESH_INDEX.json")
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    issue = json_loads_strict(Path(args.issue).read_text(encoding="utf-8"))
    event = json_loads_strict(Path(args.event).read_text(encoding="utf-8"))
    policy_path = Path(args.policy)
    policy_bytes = policy_path.read_bytes()
    policy = json_loads_strict(policy_bytes)
    try:
        validate_policy(policy)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.repository != policy.get("authority_repository"):
        raise SystemExit("repository differs from deterministic intake authority")
    accepted_actions = policy.get("accepted_event_actions")
    if not isinstance(accepted_actions, dict) or args.event_name not in accepted_actions:
        raise SystemExit("event name is not admitted by deterministic intake policy")
    event_name_actions = accepted_actions[args.event_name]
    if not isinstance(event_name_actions, list) or args.event_action not in event_name_actions:
        raise SystemExit("event action is not admitted by deterministic intake policy")
    if not isinstance(issue.get("number"), int) or issue["number"] < 1:
        raise SystemExit("resolved issue number is invalid")
    authority_head = require_sha(args.authority_head, "authority head")
    authority_tree = require_sha(args.authority_tree, "authority tree")
    registry_path = Path(args.registry)
    registry_bytes = registry_path.read_bytes()
    registry = json_loads_strict(registry_bytes)
    nodes = registry.get("nodes")
    if not isinstance(nodes, list):
        raise SystemExit("mesh registry nodes are invalid")
    active_registered_nodes = sorted({
        value.get("repository")
        for value in nodes
        if isinstance(value, dict)
        and value.get("effective_status") == "ACTIVE"
        and isinstance(value.get("repository"), str)
    })
    active_mesh_nodes = sorted(set(active_registered_nodes) | {args.repository})
    trigger = event_binding(issue, event, args.event_name, args.event_action)
    context = repository_context(authority_head)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    binding = {
        "event_name": trigger["event_name"],
        "event_action": trigger["event_action"],
        "issue_number": issue["number"],
        "source_updated_at": trigger["source_updated_at"],
        "comment_id_or_null": trigger["comment_id"],
        "comment_node_id_or_null": trigger["comment_node_id"],
        "comment_url_or_null": trigger["comment_url"],
        "actor_login": trigger["actor_login"],
        "selected_author_association": trigger["selected_author_association"],
        "selected_author_login": trigger["selected_author_login"],
        "selected_source": trigger["selected_source"],
        "selected_body_sha256": trigger["selected_body_sha256"],
        "issue_snapshot_sha256": sha256_bytes(bound_canonical_bytes(issue_snapshot({
            "number": issue["number"],
            "title": issue.get("title", ""),
            "body": issue.get("body") or "",
            "author": (issue.get("user") or {}).get("login"),
            "author_type": (issue.get("user") or {}).get("type"),
            "html_url": issue.get("html_url"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
        }))),
        "context_sha256": sha256_bytes(context.encode("utf-8")),
        "authority_head": authority_head,
        "authority_tree": authority_tree,
        "handler_policy_sha256": sha256_bytes(policy_bytes),
        "registry_sha256": sha256_bytes(registry_bytes),
        "intake_code_sha256": worktree_code_sha256(Path(".")),
        "active_registered_nodes": active_registered_nodes,
        "active_mesh_nodes": active_mesh_nodes,
    }
    request_fingerprint = sha256_bytes(canonical_bytes(binding))
    request = {
        "schema": "qikvrt_issue_agent_request_v2",
        "repository": args.repository,
        "issue_number": issue["number"],
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "author": (issue.get("user") or {}).get("login"),
        "author_type": (issue.get("user") or {}).get("type"),
        "html_url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "trigger": trigger,
        "binding": binding,
        "request_fingerprint": request_fingerprint,
        "handler_policy": {
            "path": policy_path.as_posix(),
            "sha256": binding["handler_policy_sha256"],
        },
        "registry": {
            "path": registry_path.as_posix(),
            "sha256": binding["registry_sha256"],
            "active_registered_nodes": active_registered_nodes,
            "active_mesh_nodes": active_mesh_nodes,
        },
    }
    canonical = json.dumps(
        request,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    (out / "REQUEST.json").write_text(canonical, encoding="utf-8")
    (out / "REQUEST.sha256").write_text(hashlib.sha256(canonical.encode()).hexdigest() + "  REQUEST.json\n", encoding="utf-8")
    event_record = {
        "schema": "qikvrt_issue_agent_event_binding_v1",
        "binding": binding,
        "request_fingerprint": request_fingerprint,
    }
    (out / "EVENT.json").write_bytes(canonical_bytes(event_record))
    (out / "EVENT.sha256").write_text(
        f"{sha256_bytes((out / 'EVENT.json').read_bytes())}  EVENT.json\n",
        encoding="utf-8",
    )

    (out / "CONTEXT.md").write_text(context, encoding="utf-8")


if __name__ == "__main__":
    main()
