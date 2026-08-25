#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Role-bound Seed workflow adapter with exact-run artifact quarantine.

The adapter keeps the semantic Seed state separate from GitHub Actions
transport.  PASS and CONTINUE both mean that the adapter completed and wrote a
fresh, exact-run receipt; only the receipt carries the semantic state.  BLOCK
and unclassified states remain hard failures.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from tools.qikvrt_seed_common import (
        DEFAULT_SEED_REPOSITORY,
        FetchedJson,
        HttpJsonFetcher,
        SeedError,
        canonical_json_bytes,
        parse_json_bytes,
        read_json,
        run_acceptance,
        run_audit_export,
        run_dashboard,
        run_maintenance,
        run_revalidation,
        write_json,
    )
except ModuleNotFoundError:  # Script execution keeps tools/ as sys.path[0].
    from qikvrt_seed_common import (  # type: ignore[no-redef]
        DEFAULT_SEED_REPOSITORY,
        FetchedJson,
        HttpJsonFetcher,
        SeedError,
        canonical_json_bytes,
        parse_json_bytes,
        read_json,
        run_acceptance,
        run_audit_export,
        run_dashboard,
        run_maintenance,
        run_revalidation,
        write_json,
    )


FAILURE_CLASS = "SEED_TYPED_CONTINUE_COLLAPSED_TO_JOB_FAILURE"
MESH_CONTRACT_PATH = "state/mesh/QIKVRT_AUTHORITY_MIRROR_MESH_INSTANCE_V1.json"
PROFILES = ("audit", "dashboard", "maintenance", "registry", "revalidation")
ALLOWED_EVENTS = frozenset({"push", "workflow_dispatch"})
SHA256_RE = re.compile(r"[0-9a-f]{40,64}\Z")
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
STATUS_PRIORITY = {"PASS": 0, "CONTINUE": 1, "BLOCK": 2}


def _utc(now: dt.datetime | None = None) -> str:
    value = now or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        raise SeedError("control-plane time must be timezone-aware")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise SeedError("run id must be 1-128 safe filename characters")
    return run_id


def _validate_sha(value: str, label: str) -> str:
    if not SHA256_RE.fullmatch(value):
        raise SeedError(f"{label} must be a lower-case 40-64 character Git object digest")
    return value


def aggregate_statuses(results: Iterable[Mapping[str, Any]]) -> str:
    status = "PASS"
    observed = False
    for result in results:
        candidate = result.get("status")
        if candidate not in STATUS_PRIORITY:
            raise SeedError(f"unclassified Seed result status: {candidate!r}")
        observed = True
        if STATUS_PRIORITY[str(candidate)] > STATUS_PRIORITY[status]:
            status = str(candidate)
    if not observed:
        raise SeedError("Seed control-plane execution produced no semantic result")
    return status


def workflow_transport_exit_code(result: Mapping[str, Any]) -> int:
    """Map a complete adapter receipt to transport, never to semantic PASS."""
    status = result.get("status")
    if status in {"PASS", "CONTINUE"}:
        return 0
    if status == "BLOCK":
        return 1
    raise SeedError(f"unclassified Seed workflow status: {status!r}")


def validate_admission(
    root: Path,
    *,
    profile: str,
    actual_repository: str,
    seed_repository: str,
    event_name: str,
    source_head: str,
    source_tree: str,
    expected_head: str,
) -> dict[str, Any]:
    if profile not in PROFILES:
        raise SeedError(f"unsupported Seed control-plane profile: {profile!r}")
    if event_name not in ALLOWED_EVENTS:
        raise SeedError(f"SEED_EVENT_HOLD unsupported semantic event: {event_name!r}")
    _validate_sha(source_head, "source head")
    _validate_sha(source_tree, "source tree")
    _validate_sha(expected_head, "expected head")
    if source_head != expected_head:
        raise SeedError("SEED_EVENT_HOLD checked-out head differs from the authenticated event head")

    contract = read_json(root / MESH_CONTRACT_PATH, "Authority/Mirror mesh instance")
    if contract.get("schema") != "qikvrt_authority_mirror_mesh_instance_contract_v1":
        raise SeedError("SEED_ROLE_HOLD invalid Authority/Mirror mesh contract schema")
    topology = contract.get("topology")
    if not isinstance(topology, dict):
        raise SeedError("SEED_ROLE_HOLD mesh topology is missing")
    authority = topology.get("authority")
    mirror = topology.get("mirror")
    if not isinstance(authority, dict) or not isinstance(mirror, dict):
        raise SeedError("SEED_ROLE_HOLD Authority/Mirror role records are missing")
    if authority.get("role") != "AUTHORITY" or authority.get("repository") != seed_repository:
        raise SeedError("SEED_ROLE_HOLD configured Seed is not the machine-declared Authority")
    if actual_repository != seed_repository:
        declared_role = "MIRROR" if mirror.get("repository") == actual_repository else "UNDECLARED"
        raise SeedError(
            f"SEED_ROLE_HOLD repository {actual_repository!r} has role {declared_role}, "
            f"not the configured Seed Authority {seed_repository!r}"
        )
    return {
        "schema": "qikvrt_seed_control_plane_binding_v1",
        "profile": profile,
        "repository": actual_repository,
        "repository_role": "AUTHORITY",
        "seed_repository": seed_repository,
        "event": event_name,
        "source_head": source_head,
        "source_tree": source_tree,
        "expected_head": expected_head,
        "role_contract_path": MESH_CONTRACT_PATH,
    }


def _artifact_root(root: Path, run_id: str) -> Path:
    artifact = root / ".qikvrt/seed-workflow" / _validate_run_id(run_id) / "artifact"
    current = artifact
    while current != root.parent and current != root:
        if current.is_symlink():
            raise SeedError(f"symlink artifact path is forbidden: {current}")
        current = current.parent
    if artifact.exists():
        raise SeedError(f"exact-run artifact directory already exists: {artifact}")
    artifact.mkdir(parents=True)
    return artifact


def _read_regular(path: Path, maximum: int = 16 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise SeedError(f"required exact-run output is missing or unsafe: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise SeedError(f"required exact-run output is not a bounded regular file: {path}")
        raw = b""
        while len(raw) <= maximum:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
        after = os.fstat(descriptor)
        if len(raw) > maximum or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise SeedError(f"required exact-run output changed or exceeded its bound: {path}")
        return raw
    finally:
        os.close(descriptor)


def _json_output(root: Path, relative: str, run_id: str, run_key: str = "run_id") -> tuple[str, bytes, str]:
    if "LATEST.json" in relative:
        raise SeedError("LATEST.json is forbidden in exact-run artifacts")
    raw = _read_regular(root / relative)
    document = parse_json_bytes(raw, relative)
    if document.get(run_key) != run_id:
        raise SeedError(f"{relative}: {run_key} is not bound to the current run")
    return relative, raw, "CURRENT_RUN_JSON"


def _text_output(root: Path, relative: str, run_id: str) -> tuple[str, bytes, str]:
    raw = _read_regular(root / relative)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SeedError(f"{relative}: invalid UTF-8") from exc
    if run_id not in text:
        raise SeedError(f"{relative}: current run id is absent")
    return relative, raw, "CURRENT_RUN_TEXT"


def _ledger_projection(root: Path, run_id: str) -> tuple[str, bytes, str]:
    raw = _read_regular(root / "ledger/NODE_REGISTRATION_LEDGER.jsonl")
    selected: list[bytes] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        document = parse_json_bytes(line, f"ledger line {line_number}")
        if document.get("run_id") == run_id:
            selected.append(
                json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                + b"\n"
            )
    if not selected:
        raise SeedError("current-run ledger projection is empty")
    return "ledger/NODE_REGISTRATION_LEDGER.current-run.jsonl", b"".join(selected), "CURRENT_RUN_PROJECTION"


def _fresh_outputs(
    root: Path,
    run_id: str,
    profile: str,
    steps: list[dict[str, Any]],
) -> list[tuple[str, bytes, str]]:
    names = {str(step["step"]): step for step in steps}
    outputs: list[tuple[str, bytes, str]] = []
    receipts = {
        "acceptance": "evidence/seed_acceptance/runs/{run_id}.json",
        "maintenance": "evidence/seed_mesh_maintenance/runs/{run_id}.json",
        "revalidation": "evidence/seed_node_revalidation/runs/{run_id}.json",
        "dashboard": "evidence/seed_dashboard/runs/{run_id}.json",
        "audit": "evidence/seed_mesh_audit/runs/{run_id}.json",
    }
    for name in names:
        outputs.append(_json_output(root, receipts[name].format(run_id=run_id), run_id))

    if "maintenance" in names:
        outputs.extend(
            _json_output(root, relative, run_id)
            for relative in ("registry/NODEMESH_INDEX.json", "registry/NODEMESH_STATUS.json")
        )
    if "revalidation" in names:
        outputs.append(_json_output(root, "registry/NODEMESH_REVALIDATION.json", run_id))
    if "dashboard" in names:
        outputs.extend(
            _text_output(root, relative, run_id)
            for relative in ("docs/qikvrt_mesh_dashboard.html", "docs/QIKVRT_MESH_DASHBOARD.md")
        )
    if "audit" in names:
        outputs.extend(
            (
                _json_output(root, "audit/QIKVRT_MESH_AUDIT_SUMMARY.json", run_id),
                _text_output(root, "audit/QIKVRT_MESH_AUDIT_REPORT.md", run_id),
                _text_output(root, "docs/QIKVRT_AUDIT_EXPORT.md", run_id),
            )
        )
    if profile == "registry" and names.get("acceptance", {}).get("status") != "BLOCK":
        acceptance = read_json(root / receipts["acceptance"].format(run_id=run_id))
        results = acceptance.get("results")
        if not isinstance(results, list):
            raise SeedError("current-run acceptance results are missing")
        for result in results:
            if not isinstance(result, dict) or not isinstance(result.get("guid"), str):
                raise SeedError("current-run acceptance result has no GUID")
            guid = str(result["guid"])
            outputs.append(_json_output(root, f"registry/nodes/{guid}.json", run_id, "last_acceptance_run_id"))
            outputs.append(_json_output(root, f"evidence/seed_acceptance/{guid}.json", run_id))
        outputs.append(_ledger_projection(root, run_id))

    paths = [relative for relative, _, _ in outputs]
    if len(paths) != len(set(paths)):
        raise SeedError("duplicate path in exact-run artifact selection")
    return outputs


def _write_artifact_file(artifact: Path, relative: str, raw: bytes) -> None:
    if relative.startswith("/") or ".." in Path(relative).parts or "LATEST.json" in relative:
        raise SeedError(f"unsafe exact-run artifact path: {relative}")
    destination = artifact / "outputs" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.exists():
        raise SeedError(f"artifact path already exists or is unsafe: {destination}")
    destination.write_bytes(raw)


def _write_manifest(artifact: Path, metadata: Mapping[str, str]) -> None:
    files: list[dict[str, Any]] = []
    for path in sorted(artifact.rglob("*")):
        if path.is_dir():
            continue
        if path.is_symlink() or not path.is_file():
            raise SeedError(f"unsafe artifact member: {path}")
        relative = path.relative_to(artifact).as_posix()
        if relative == "MANIFEST.json" or "LATEST.json" in relative:
            continue
        raw = _read_regular(path)
        files.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    write_json(
        artifact / "MANIFEST.json",
        {
            "schema": "qikvrt_seed_exact_run_artifact_manifest_v1",
            **metadata,
            "files": files,
            "rules": {
                "current_run_only": True,
                "latest_alias_forbidden": True,
                "tracked_stale_fallback_forbidden": True,
            },
        },
    )


def _completion_claims() -> dict[str, bool]:
    return {
        "authority_mirror_synchronization": False,
        "PASS": False,
        "FINAL_PASS": False,
        "deployment": False,
        "EFFECT_ACK_DONE": False,
    }


def run_control_plane(
    root: Path,
    profile: str,
    run_id: str,
    *,
    actual_repository: str,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
    event_name: str,
    source_head: str,
    source_tree: str,
    expected_head: str,
    fetch: Callable[[str], FetchedJson] | None = None,
    timeout_seconds: float = 15.0,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_utc = _utc(now)
    artifact = _artifact_root(root, run_id)
    steps: list[dict[str, Any]] = []
    binding: dict[str, Any] | None = None
    error: str | None = None
    try:
        binding = validate_admission(
            root,
            profile=profile,
            actual_repository=actual_repository,
            seed_repository=seed_repository,
            event_name=event_name,
            source_head=source_head,
            source_tree=source_tree,
            expected_head=expected_head,
        )
        binding["run_id"] = run_id
        binding["generated_utc"] = generated_utc
        write_json(artifact / "exact-head-binding.json", binding)

        fetcher = fetch or HttpJsonFetcher(timeout_seconds)

        def execute(name: str) -> str:
            if name == "acceptance":
                result = run_acceptance(root, run_id, fetcher, now=now, seed_repository=seed_repository)
            elif name == "maintenance":
                result = run_maintenance(root, run_id, fetcher, now=now, seed_repository=seed_repository)
            elif name == "revalidation":
                result = run_revalidation(root, run_id, now=now, seed_repository=seed_repository)
            elif name == "dashboard":
                result = run_dashboard(root, run_id, now=now, seed_repository=seed_repository)
            elif name == "audit":
                result = run_audit_export(root, run_id, now=now, seed_repository=seed_repository)
            else:  # pragma: no cover - profile table is fixed below.
                raise SeedError(f"unknown Seed step: {name}")
            status = aggregate_statuses((result,))
            steps.append({"step": name, "status": status})
            return status

        sequence = {
            "registry": ("acceptance", "maintenance", "revalidation"),
            "dashboard": ("maintenance", "revalidation", "dashboard"),
            "audit": ("maintenance", "revalidation", "audit"),
            "maintenance": ("maintenance", "revalidation"),
            "revalidation": ("maintenance", "revalidation"),
        }[profile]
        for name in sequence:
            if execute(name) == "BLOCK":
                break
        status = aggregate_statuses(steps)
        outputs = _fresh_outputs(root, run_id, profile, steps)
        for relative, raw, _kind in outputs:
            _write_artifact_file(artifact, relative, raw)
    except (SeedError, OSError, ValueError) as exc:
        status = "BLOCK"
        error = str(exc)

    receipt = {
        "schema": "qikvrt_seed_control_plane_receipt_v1",
        "failure_class": FAILURE_CLASS,
        "generated_utc": generated_utc,
        "run_id": run_id,
        "profile": profile,
        "status": status,
        "transport_status": "COMPLETE" if status in {"PASS", "CONTINUE"} else "FAILED",
        "disposition": (
            "SEMANTIC_CONTINUE_REPORTED"
            if status == "CONTINUE"
            else "SEMANTIC_RESULT_REPORTED"
            if status == "PASS"
            else "ROLE_EVENT_OR_SEMANTIC_BLOCK"
        ),
        "binding": binding,
        "steps": steps,
        "error": error,
        "artifact_scope": "EXACT_RUN_ONLY",
        "completion_claims": _completion_claims(),
    }
    write_json(artifact / "control-plane-receipt.json", receipt)
    _write_manifest(
        artifact,
        {
            "run_id": run_id,
            "profile": profile,
            "semantic_status": status,
            "repository": actual_repository,
            "source_head": source_head,
            "source_tree": source_tree,
        },
    )
    return receipt


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run-id", default=os.environ.get("QIKVRT_RUN_ID", ""))
    parser.add_argument("--actual-repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--seed-repository", default=os.environ.get("QIKVRT_SEED_REPOSITORY", DEFAULT_SEED_REPOSITORY))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--source-head", default=os.environ.get("QIKVRT_SOURCE_HEAD", os.environ.get("GITHUB_SHA", "")))
    parser.add_argument("--source-tree", default=os.environ.get("QIKVRT_SOURCE_TREE", ""))
    parser.add_argument("--expected-head", default=os.environ.get("QIKVRT_EXPECTED_HEAD", ""))
    parser.add_argument("--timeout-seconds", type=float, default=float(os.environ.get("QIKVRT_SEED_HTTP_TIMEOUT_SECONDS", "15")))
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    if not arguments.run_id:
        arguments.run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        result = run_control_plane(
            arguments.root,
            arguments.profile,
            arguments.run_id,
            actual_repository=arguments.actual_repository,
            seed_repository=arguments.seed_repository,
            event_name=arguments.event_name,
            source_head=arguments.source_head,
            source_tree=arguments.source_tree,
            expected_head=arguments.expected_head,
            timeout_seconds=arguments.timeout_seconds,
        )
        print(
            "QIKVRT_SEED_CONTROL_PLANE "
            f"semantic_status={result['status']} transport_status={result['transport_status']} "
            f"profile={arguments.profile} run_id={arguments.run_id}"
        )
        return workflow_transport_exit_code(result)
    except (SeedError, OSError, ValueError) as exc:
        print(f"BLOCK QIKVRT_SEED_CONTROL_PLANE {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
