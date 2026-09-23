#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed freshness and public-effect gate for Zenodo-bound subjects."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from typing import Any

DEFAULT_REGISTRY = "policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json"
ZENODO_DOI = re.compile(r"^10\.5281/zenodo\.[1-9][0-9]*$")


class GuardError(RuntimeError):
    pass


def _safe(root: pathlib.Path, raw: str, *, must_exist: bool = True) -> pathlib.Path:
    if not isinstance(raw, str) or not raw or any(ord(c) < 32 for c in raw):
        raise GuardError("path must be non-empty text without control characters")
    pure = pathlib.PurePosixPath(raw)
    if pure.is_absolute() or "\\" in raw or any(part in {"", ".", ".."} for part in pure.parts):
        raise GuardError(f"unsafe repository-relative path: {raw}")
    path = root.joinpath(*pure.parts)
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise GuardError(f"symlink path is forbidden: {raw}")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise GuardError(f"path escapes repository root: {raw}") from None
    if must_exist:
        try:
            st = resolved.stat()
        except FileNotFoundError:
            raise GuardError(f"required file is absent: {raw}") from None
        if not stat.S_ISREG(st.st_mode):
            raise GuardError(f"required path is not a regular file: {raw}")
    return resolved


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"invalid JSON at {path.name}: {exc}") from None
    if not isinstance(value, dict):
        raise GuardError(f"{path.name} must contain a JSON object")
    return value


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()  # noqa: S324


def identity(root: pathlib.Path, raw: str) -> dict[str, Any]:
    data = _safe(root, raw).read_bytes()
    return {"path": raw, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "git_blob_sha1": _git_blob(data)}


def _registry(root: pathlib.Path, registry: str) -> dict[str, Any]:
    value = _read_json(_safe(root, registry))
    if value.get("schema") != "qikvrt_zenodo_successor_targets_v1":
        raise GuardError("unsupported successor target registry schema")
    targets = value.get("targets")
    if not isinstance(targets, list) or not targets:
        raise GuardError("successor target registry must contain targets")
    ids = [item.get("id") for item in targets if isinstance(item, dict)]
    if len(ids) != len(targets) or any(not isinstance(v, str) or not v for v in ids):
        raise GuardError("every successor target must have a non-empty id")
    if len(ids) != len(set(ids)):
        raise GuardError("successor target ids must be unique")
    return value


def target(root: pathlib.Path, target_id: str, registry: str = DEFAULT_REGISTRY) -> dict[str, Any]:
    matches = [item for item in _registry(root, registry)["targets"] if item.get("id") == target_id]
    if len(matches) != 1:
        raise GuardError(f"target must resolve exactly once: {target_id}")
    value = matches[0]
    paths = value.get("source_paths")
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        raise GuardError("source_paths must be a non-empty unique list")
    for raw in paths:
        _safe(root, raw)
    for key in ("candidate_path", "publish_request_path", "owner_authorization_path", "publication_receipt_path"):
        raw = value.get(key)
        if not isinstance(raw, str):
            raise GuardError(f"target lacks {key}")
        _safe(root, raw, must_exist=False)
    return value


def target_ids(root: pathlib.Path, registry: str = DEFAULT_REGISTRY) -> list[str]:
    return [item["id"] for item in _registry(root, registry)["targets"]]


def source_set(root: pathlib.Path, value: dict[str, Any]) -> list[dict[str, Any]]:
    return [identity(root, raw) for raw in value["source_paths"]]


def source_set_sha256(items: list[dict[str, Any]]) -> str:
    raw = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def candidate_payload(root: pathlib.Path, value: dict[str, Any]) -> dict[str, Any]:
    items = source_set(root, value)
    return {
        "schema": "qikvrt_zenodo_auto_successor_candidate_v1",
        "target_id": value["id"],
        "publication_id": value["publication_id"],
        "state": "MATERIALIZED_AWAITING_EXACT_OWNER_AUTHORIZATION",
        "source_files": items,
        "source_set_sha256": source_set_sha256(items),
        "predecessor_evidence_transfer": False,
        "candidate_specific_owner_authorization_required": True,
        "public_effect_ack_done": False,
    }


def _atomic_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temp = path.with_name("." + path.name + f".{os.getpid()}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def materialize(root: pathlib.Path, target_id: str, registry: str = DEFAULT_REGISTRY) -> dict[str, Any]:
    value = target(root, target_id, registry)
    payload = candidate_payload(root, value)
    _atomic_json(_safe(root, value["candidate_path"], must_exist=False), payload)
    return payload


def materialize_all(root: pathlib.Path, registry: str = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    return [materialize(root, target_id, registry) for target_id in target_ids(root, registry)]


def _candidate_current(root: pathlib.Path, value: dict[str, Any]) -> tuple[bool, str]:
    path = _safe(root, value["candidate_path"], must_exist=False)
    if not path.exists():
        return False, "MISSING"
    candidate = _read_json(path)
    expected = candidate_payload(root, value)
    return candidate == expected, "CURRENT" if candidate == expected else "STALE"


def _files_bind_current(files: Any, current: list[dict[str, Any]]) -> bool:
    if not isinstance(files, list):
        return False
    by_path = {item.get("path"): item for item in files if isinstance(item, dict) and isinstance(item.get("path"), str)}
    return all(
        isinstance(by_path.get(source["path"]), dict)
        and by_path[source["path"]].get("git_blob_sha") == source["git_blob_sha1"]
        for source in current
    )


def _manifest_current(root: pathlib.Path, value: dict[str, Any], current: list[dict[str, Any]]) -> tuple[bool, str]:
    path = _safe(root, value["publish_request_path"], must_exist=False)
    if not path.exists():
        return False, "MISSING"
    manifest = _read_json(path)
    if (
        manifest.get("schema") != "qikvrt_zenodo_publication_manifest_v2"
        or manifest.get("state") != "publish"
        or manifest.get("confirm") != "PUBLISH_TO_PRODUCTION_ZENODO"
        or manifest.get("repository") != value["authority_repository"]
        or not _files_bind_current(manifest.get("files"), current)
    ):
        return False, "STALE"
    return True, "CURRENT"


def _authorization_current(root: pathlib.Path, value: dict[str, Any], current: list[dict[str, Any]]) -> tuple[bool, str]:
    path = _safe(root, value["owner_authorization_path"], must_exist=False)
    if not path.exists():
        return False, "MISSING"
    authorization = _read_json(path)
    if (
        authorization.get("schema") != "qikvrt_zenodo_owner_authorization_v1"
        or authorization.get("repository") != value["authority_repository"]
        or authorization.get("publication_id") != value["publication_id"]
        or authorization.get("single_use") is not True
        or not _files_bind_current(authorization.get("uploads"), current)
    ):
        return False, "STALE"
    event = authorization.get("authorization_event")
    if not isinstance(event, dict) or event.get("decision") != "AUTHORIZE_EXACT_UPLOAD":
        return False, "INVALID"
    return True, "CURRENT"


def _receipt_current(root: pathlib.Path, value: dict[str, Any], current: list[dict[str, Any]]) -> tuple[bool, str]:
    path = _safe(root, value["publication_receipt_path"], must_exist=False)
    if not path.exists():
        return False, "MISSING"
    receipt = _read_json(path)
    recovery = receipt.get("recovery")
    if (
        receipt.get("schema") != "qikvrt_zenodo_publication_evidence_v2"
        or receipt.get("state") != "published"
        or receipt.get("phase") != "public_verified"
        or not isinstance(recovery, dict)
        or recovery.get("public_verified") is not True
        or recovery.get("remote_state_requires_reconciliation") is not False
        or not _files_bind_current(receipt.get("files"), current)
    ):
        return False, "STALE"
    doi = receipt.get("doi")
    conceptdoi = receipt.get("conceptdoi")
    record_url = receipt.get("record_url")
    record_id = receipt.get("record_id")
    if (
        not isinstance(doi, str) or ZENODO_DOI.fullmatch(doi) is None
        or not isinstance(conceptdoi, str) or ZENODO_DOI.fullmatch(conceptdoi) is None
        or isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0
        or record_url != f"https://zenodo.org/records/{record_id}"
    ):
        return False, "INVALID_PUBLIC_IDENTITY"
    return True, "CURRENT"


def evaluate(root: pathlib.Path, target_id: str, registry: str = DEFAULT_REGISTRY) -> dict[str, Any]:
    value = target(root, target_id, registry)
    current = source_set(root, value)
    candidate_ok, candidate_state = _candidate_current(root, value)
    manifest_ok, manifest_state = _manifest_current(root, value, current)
    authorization_ok, authorization_state = _authorization_current(root, value, current)
    receipt_ok, receipt_state = _receipt_current(root, value, current)
    effect = candidate_ok and manifest_ok and authorization_ok and receipt_ok
    return {
        "target_id": target_id,
        "source_set_sha256": source_set_sha256(current),
        "candidate": {"current": candidate_ok, "state": candidate_state},
        "publish_request": {"current": manifest_ok, "state": manifest_state},
        "owner_authorization": {"current": authorization_ok, "state": authorization_state},
        "public_receipt": {"current": receipt_ok, "state": receipt_state},
        "PUBLICATION_EFFECT_ACK_DONE": effect,
    }


def _check(result: dict[str, Any], *, require_publish_request: bool, require_authorization: bool, require_public_effect: bool) -> int:
    if not result["candidate"]["current"]:
        return 2
    if require_publish_request and not result["publish_request"]["current"]:
        return 3
    if require_authorization and not result["owner_authorization"]["current"]:
        return 4
    if require_public_effect and not result["PUBLICATION_EFFECT_ACK_DONE"]:
        return 5
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("materialize")
    one.add_argument("--target", required=True)
    sub.add_parser("materialize-all")

    one = sub.add_parser("status")
    one.add_argument("--target", required=True)
    sub.add_parser("status-all")

    one = sub.add_parser("check")
    one.add_argument("--target", required=True)
    for command in (one, sub.add_parser("check-all")):
        command.add_argument("--require-publish-request", action="store_true")
        command.add_argument("--require-authorization", action="store_true")
        command.add_argument("--require-public-effect", action="store_true")

    args = parser.parse_args(argv)
    root = pathlib.Path(args.repository_root).resolve()
    try:
        if args.command == "materialize":
            materialize(root, args.target, args.registry)
            result = evaluate(root, args.target, args.registry)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "materialize-all":
            materialize_all(root, args.registry)
            results = [evaluate(root, target_id, args.registry) for target_id in target_ids(root, args.registry)]
            print(json.dumps(results, ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "status":
            print(json.dumps(evaluate(root, args.target, args.registry), ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "status-all":
            results = [evaluate(root, target_id, args.registry) for target_id in target_ids(root, args.registry)]
            print(json.dumps(results, ensure_ascii=False, sort_keys=True))
            return 0
        ids = [args.target] if args.command == "check" else target_ids(root, args.registry)
        worst = 0
        results = []
        for target_id in ids:
            result = evaluate(root, target_id, args.registry)
            results.append(result)
            worst = max(worst, _check(
                result,
                require_publish_request=args.require_publish_request,
                require_authorization=args.require_authorization,
                require_public_effect=args.require_public_effect,
            ))
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, sort_keys=True))
        return worst
    except GuardError as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
