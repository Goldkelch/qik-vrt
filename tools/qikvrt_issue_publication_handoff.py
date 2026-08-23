#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact issue-to-platform publication handoff.

The finite READY/HOLD/REOBSERVE/REQUEST_AUTHORITY decision is executed by the
proof-bound M68000 Spark kernel. Only the host adapter may use credentials and
perform the Zenodo effect. DONE is written only after public record and exact
bytes have been reobserved by the hardened generic publisher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Mapping

try:
    from tools import qikvrt_mesh_patterns as patterns
    from tools import qikvrt_zenodo_publish as zenodo_publish
except ModuleNotFoundError:  # direct execution from tools/
    import qikvrt_mesh_patterns as patterns  # type: ignore[no-redef]
    import qikvrt_zenodo_publish as zenodo_publish  # type: ignore[no-redef]

SCHEMA_ROUTE = "qikvrt_issue_publication_route_v1"
SCHEMA_ASSESSMENT = "qikvrt_issue_publication_handoff_assessment_v1"
SCHEMA_RECEIPT = "qikvrt_issue_publication_effect_receipt_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ROUTE_KEYS = {
    "schema",
    "issue_number",
    "required",
    "platform",
    "state",
    "manifest_path",
    "manifest_sha256",
    "adapter",
    "receipt_path",
}


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def hash_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git identity


def git_output(root: pathlib.Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=root,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def git_head(root: pathlib.Path) -> str:
    value = git_output(root, "rev-parse", "--verify", "HEAD^{commit}")
    if HEX40.fullmatch(value) is None:
        raise ValueError("invalid repository HEAD")
    return value


def safe_relative(root: pathlib.Path, raw: Any, label: str) -> pathlib.Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a non-empty path")
    pure = pathlib.PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"{label} must be repository-relative")
    candidate = (root / pure).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes repository root") from exc
    return candidate


def _load_object(path: pathlib.Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _committed_identity(
    root: pathlib.Path,
    path: pathlib.Path,
) -> dict[str, Any]:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    raw = path.read_bytes()
    expected_blob = git_blob_sha(raw)
    observed_blob = git_output(
        root,
        "rev-parse",
        "--verify",
        f"HEAD:{relative}",
    )
    if observed_blob != expected_blob:
        raise ValueError(f"{relative} differs from committed HEAD bytes")
    status = git_output(
        root,
        "status",
        "--porcelain=v1",
        "--",
        relative,
    )
    if status:
        raise ValueError(f"{relative} is dirty")
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha": expected_blob,
    }


def route_path_for_issue(root: pathlib.Path, issue: int) -> pathlib.Path:
    return root / "evidence" / "issues" / str(issue) / "PUBLICATION_ROUTE.json"


def status_path_for_issue(root: pathlib.Path, issue: int) -> pathlib.Path:
    return root / "evidence" / "issues" / str(issue) / "STATUS.json"


def assess(root: pathlib.Path, issue: int) -> dict[str, Any]:
    root = root.resolve()
    route_path = route_path_for_issue(root, issue)
    status_path = status_path_for_issue(root, issue)
    head = git_head(root)

    if not route_path.is_file():
        return {
            "schema": SCHEMA_ASSESSMENT,
            "issue": issue,
            "repository_head": head,
            "state": "NOT_REQUESTED",
            "ready": False,
            "effect_adapter": None,
            "m68000_decision": patterns.machine_decision(
                implemented=False,
                verified=False,
                persisted=False,
                reobserved=False,
                unclassified_remainder=False,
                witness=issue,
            ),
            "first_blocker": None,
            "next_action": "NONE",
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }

    first_blocker: str | None = None
    next_action = "repair the exact publication route"
    route: dict[str, Any] = {}
    status: dict[str, Any] = {}
    route_identity: dict[str, Any] | None = None
    manifest_identity: dict[str, Any] | None = None
    manifest: dict[str, Any] = {}
    committed = False
    verified = False
    reobserved = False
    authority_present = False
    stale = False
    unclassified = False

    try:
        route = _load_object(route_path, "PUBLICATION_ROUTE.json")
        if set(route) != REQUIRED_ROUTE_KEYS:
            raise ValueError("publication route keys mismatch")
        if route["schema"] != SCHEMA_ROUTE:
            raise ValueError("publication route schema mismatch")
        if route["issue_number"] != issue:
            raise ValueError("publication route issue mismatch")
        if route["required"] is not True:
            raise ValueError("publication route required must equal true")
        if route["platform"] != "zenodo":
            unclassified = True
            raise ValueError("no bound adapter for requested platform")
        if route["adapter"] != "tools/qikvrt_zenodo_publish.py":
            raise ValueError("publication route adapter mismatch")
        if route["state"] != "READY":
            stale = route["state"] not in {"READY", "PUBLIC_VERIFIED"}
            raise ValueError(
                f"publication route state is {route['state']!r}, not READY"
            )
        if (
            not isinstance(route["manifest_sha256"], str)
            or HEX64.fullmatch(route["manifest_sha256"]) is None
        ):
            raise ValueError("publication route manifest digest invalid")
        route_identity = _committed_identity(root, route_path)
        manifest_path = safe_relative(
            root,
            route["manifest_path"],
            "manifest_path",
        )
        if not manifest_path.is_file():
            raise ValueError("publication manifest is missing")
        manifest_identity = _committed_identity(root, manifest_path)
        committed = True
        if manifest_identity["sha256"] != route["manifest_sha256"]:
            stale = True
            raise ValueError("publication manifest SHA-256 drift")
        manifest = _load_object(manifest_path, "publication manifest")
        if (
            manifest.get("schema")
            != zenodo_publish.SCHEMA_V2
            or manifest.get("state") != "publish"
            or manifest.get("confirm")
            != "PUBLISH_TO_PRODUCTION_ZENODO"
            or manifest.get("repository")
            != zenodo_publish.PRODUCTION_REPOSITORY
            or not isinstance(manifest.get("machine_proof"), dict)
            or not isinstance(manifest.get("owner_authorization"), dict)
        ):
            raise ValueError(
                "publication manifest lacks the closed v2 proof/authorization contract"
            )
        authority_present = True
        status = _load_object(status_path, "STATUS.json")
        if (
            status.get("pre_effect_ready") is not True
            or status.get("publication_required") is not True
            or status.get("publication_state") != "READY"
            or status.get("status") != "CONTINUE"
            or status.get("model_inference_completed") is not True
            or status.get("no_false_pass") is not True
        ):
            raise ValueError("issue status is not exact pre-effect publication READY")
        verified = True
        reobserved = (
            hash_file(route_path) == route_identity["sha256"]
            and hash_file(manifest_path) == manifest_identity["sha256"]
        )
        next_action = (
            "execute the generic Zenodo publisher and persist public reobservation"
        )
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        first_blocker = str(exc)

    decision = patterns.machine_decision(
        implemented=True,
        verified=verified,
        persisted=committed,
        reobserved=reobserved,
        stale=stale,
        authority_required=True,
        authority_present=authority_present,
        unclassified_remainder=unclassified,
        witness=issue,
    )
    ready = (
        first_blocker is None
        and decision["decision"] == "NOOP_COMPLETE"
        and decision["completion_witness"] == 1
    )
    return {
        "schema": SCHEMA_ASSESSMENT,
        "issue": issue,
        "repository_head": head,
        "state": "READY" if ready else "HOLD",
        "ready": ready,
        "effect_adapter": (
            "tools/qikvrt_zenodo_publish.py"
            if route.get("platform") == "zenodo"
            else None
        ),
        "route": route_identity,
        "manifest": manifest_identity,
        "m68000_decision": decision,
        "first_blocker": first_blocker,
        "next_action": next_action,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def execute(root: pathlib.Path, issue: int) -> dict[str, Any]:
    root = root.resolve()
    assessment = assess(root, issue)
    if assessment["state"] != "READY":
        raise RuntimeError(
            "publication handoff is not READY: "
            + str(assessment.get("first_blocker"))
        )
    route_path = route_path_for_issue(root, issue)
    route = _load_object(route_path, "PUBLICATION_ROUTE.json")
    manifest_path = safe_relative(
        root,
        route["manifest_path"],
        "manifest_path",
    )
    evidence = zenodo_publish.publish(manifest_path, root)
    if (
        evidence.get("state") != "published"
        or evidence.get("phase") != "public_verified"
        or not isinstance(evidence.get("record_id"), int)
        or not isinstance(evidence.get("doi"), str)
    ):
        raise RuntimeError(
            "generic publisher did not return exact public_verified evidence"
        )

    evidence_path = safe_relative(
        root,
        _load_object(manifest_path, "publication manifest")["evidence_path"],
        "evidence_path",
    )
    evidence_identity = {
        "path": evidence_path.relative_to(root).as_posix(),
        "bytes": evidence_path.stat().st_size,
        "sha256": hash_file(evidence_path),
    }
    receipt_path = safe_relative(
        root,
        route["receipt_path"],
        "receipt_path",
    )
    receipt_body = {
        "schema": SCHEMA_RECEIPT,
        "issue": issue,
        "platform": "zenodo",
        "repository": zenodo_publish.PRODUCTION_REPOSITORY,
        "execution_head": assessment["repository_head"],
        "route_sha256": assessment["route"]["sha256"],
        "manifest_sha256": assessment["manifest"]["sha256"],
        "publication_evidence": evidence_identity,
        "record_id": evidence["record_id"],
        "doi": evidence["doi"],
        "conceptdoi": evidence.get("conceptdoi"),
        "record_url": evidence.get("record_url"),
        "state": "PUBLIC_VERIFIED",
        "public_bytes_reobserved": True,
        "m68000_pre_effect_decision": assessment["m68000_decision"],
        "physical_m68000_execution_observed": False,
        "peer_review_claimed": False,
        "physical_truth_claimed": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": True,
    }
    receipt = {
        **receipt_body,
        "receipt_sha256": hashlib.sha256(
            canonical_bytes(receipt_body)
        ).hexdigest(),
    }
    write_json(receipt_path, receipt)

    route["state"] = "PUBLIC_VERIFIED"
    write_json(route_path, route)

    status_path = status_path_for_issue(root, issue)
    status = _load_object(status_path, "STATUS.json")
    status.update(
        {
            "status": "DONE",
            "issue_disposition": "CLOSE_COMPLETED",
            "disposition_reason": (
                "PLATFORM_PUBLICATION_PUBLICLY_REOBSERVED"
            ),
            "next_action": "NONE",
            "first_blocker": None,
            "closure_recommended": True,
            "automatic_issue_close": True,
            "automatic_merge": True,
            "mirror_sync_required": True,
            "common_tag_required": True,
            "publication_required": True,
            "publication_state": "PUBLIC_VERIFIED",
            "publication_effect_receipt": route["receipt_path"],
            "machine_owned_work_remaining": False,
            "owner_decision_required": False,
            "effect_ack_done": True,
            "effect_ack_state": "EFFECT_ACK_DONE",
            "validated_completion_promoted_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "no_false_pass": True,
        }
    )
    write_json(status_path, status)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("assess", "execute"),
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    try:
        value = (
            assess(root, args.issue)
            if args.command == "assess"
            else execute(root, args.issue)
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
        zenodo_publish.zenodo.ZenodoError,
    ) as exc:
        print(
            "BLOCK: issue platform publication handoff failed: "
            + type(exc).__name__,
            file=sys.stderr,
        )
        return 2
    if args.output:
        write_json(pathlib.Path(args.output), value)
    else:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
