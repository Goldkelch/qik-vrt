#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Encrypted, append-only, machine-readable archive for accountable interactions."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid

SCHEMA = "qikvrt_interaction_event_v1"
CONFIRM_APPEND = "PERSIST_ENCRYPTED_INTERACTION"
CONFIRM_EXPORT = "EXPORT_AUTHORIZED_INTERACTIONS"
CONFIRM_TOMBSTONE = "RECORD_RETENTION_TOMBSTONE"
ROLE_VALUES = {"user", "assistant", "tool", "system"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class ArchiveError(RuntimeError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require_regular(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ArchiveError(f"BLOCK: unsafe or missing {label}: {path}")


def secure_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    if root == Path("/") or len(root.parts) < 3:
        raise ArchiveError("BLOCK: archive root is too broad")
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ArchiveError("BLOCK: archive root must not be a symlink")
    for name in ("events", "blobs"):
        child = root / name
        child.mkdir(exist_ok=True)
        if child.is_symlink() or not child.is_dir():
            raise ArchiveError(f"BLOCK: unsafe archive directory: {child}")
    return root


def read_json(path: Path) -> dict[str, object]:
    require_regular(path, "JSON document")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ArchiveError(f"BLOCK: expected JSON object: {path}")
    return value


def ordered_events(root: Path) -> list[tuple[Path, dict[str, object]]]:
    values: list[tuple[int, Path, dict[str, object]]] = []
    for path in (root / "events").glob("*.json"):
        event = read_json(path)
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ArchiveError(f"BLOCK: invalid event sequence at {path}")
        values.append((sequence, path, event))
    values.sort(key=lambda item: item[0])
    if [item[0] for item in values] != list(range(1, len(values) + 1)):
        raise ArchiveError("BLOCK: event sequence is incomplete or duplicated")
    return [(path, event) for _, path, event in values]


def run_age_encrypt(age_binary: str, recipient: str, source: Path, target: Path) -> None:
    if not recipient.strip():
        raise ArchiveError("BLOCK: age recipient is required")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        completed = subprocess.run(
            [age_binary, "--encrypt", "--recipient", recipient, "--output", str(temporary), str(source)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            raise ArchiveError("BLOCK: age encryption failed: " + completed.stderr.decode("utf-8", "replace")[-400:])
        require_regular(temporary, "encrypted payload")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def run_age_decrypt(age_binary: str, identity: Path, source: Path) -> bytes:
    require_regular(identity, "age identity")
    require_regular(source, "encrypted payload")
    completed = subprocess.run(
        [age_binary, "--decrypt", "--identity", str(identity), str(source)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise ArchiveError("BLOCK: age decryption failed: " + completed.stderr.decode("utf-8", "replace")[-400:])
    return completed.stdout


def verify(root: Path) -> dict[str, object]:
    previous = "0" * 64
    seen: set[str] = set()
    events = ordered_events(root)
    for path, event in events:
        projection = dict(event)
        event_hash = str(projection.pop("event_hash", ""))
        event_id = str(event.get("event_id", ""))
        if event.get("schema") != SCHEMA:
            raise ArchiveError(f"BLOCK: unsupported event schema: {path}")
        if not event_id or event_id in seen or path.stem != event_id:
            raise ArchiveError(f"BLOCK: duplicate or mismatched event identity: {path}")
        seen.add(event_id)
        if event.get("previous_event_hash") != previous:
            raise ArchiveError(f"BLOCK: broken event chain at {path}")
        if event_hash != sha256(canonical(projection)):
            raise ArchiveError(f"BLOCK: event hash mismatch at {path}")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise ArchiveError(f"BLOCK: payload descriptor is absent at {path}")
        blob_name = str(payload.get("ciphertext_path", ""))
        if blob_name:
            blob = (root / blob_name).resolve()
            if root not in blob.parents:
                raise ArchiveError(f"BLOCK: ciphertext path escapes archive: {path}")
            require_regular(blob, "ciphertext blob")
            raw = blob.read_bytes()
            expected = str(payload.get("ciphertext_sha256", ""))
            if not HEX64.fullmatch(expected) or sha256(raw) != expected:
                raise ArchiveError(f"BLOCK: ciphertext digest mismatch at {path}")
        previous = event_hash
    return {"state": "VERIFIED", "event_count": len(events), "head_event_hash": previous}


def append(args: argparse.Namespace) -> dict[str, object]:
    if args.confirm != CONFIRM_APPEND:
        raise ArchiveError("BLOCK: exact persistence confirmation is required")
    if args.role not in ROLE_VALUES or not args.consent_id.strip() or not args.purpose.strip():
        raise ArchiveError("BLOCK: role, consent identity and purpose are required")
    source = Path(args.content_file).expanduser().resolve()
    require_regular(source, "plaintext input")
    raw = source.read_bytes()
    if not raw or len(raw) > args.max_bytes:
        raise ArchiveError("BLOCK: plaintext payload is empty or exceeds the configured bound")
    root = secure_root(Path(args.archive_root))
    state = verify(root)
    event_id = args.event_id or uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9._-]{8,128}", event_id):
        raise ArchiveError("BLOCK: invalid event identity")
    target = root / "blobs" / f"{event_id}.age"
    event_path = root / "events" / f"{event_id}.json"
    if target.exists() or event_path.exists():
        raise ArchiveError("BLOCK: event identity already exists")
    run_age_encrypt(args.age_binary, args.recipient, source, target)
    encrypted = target.read_bytes()
    event: dict[str, object] = {
        "schema": SCHEMA,
        "event_id": event_id,
        "conversation_id": args.conversation_id,
        "sequence": int(state["event_count"]) + 1,
        "role": args.role,
        "created_at": args.created_at,
        "purpose": args.purpose,
        "consent": {"consent_id": args.consent_id, "scope": "encrypted_interaction_persistence"},
        "privacy": {
            "plaintext_in_repository": False,
            "encryption": "age",
            "recipient_fingerprint": sha256(args.recipient.encode("utf-8")),
            "metadata_minimized": True,
            "retention_until": args.retention_until,
        },
        "payload": {
            "media_type": args.media_type,
            "plaintext_bytes": len(raw),
            "plaintext_sha256": sha256(raw),
            "ciphertext_path": str(target.relative_to(root)).replace(os.sep, "/"),
            "ciphertext_bytes": len(encrypted),
            "ciphertext_sha256": sha256(encrypted),
        },
        "previous_event_hash": state["head_event_hash"],
        "tombstone": False,
    }
    event["event_hash"] = sha256(canonical(event))
    event_path.write_text(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    verify(root)
    return {"state": "PERSISTED_ENCRYPTED", "event_id": event_id, "event_hash": event["event_hash"]}


def export(args: argparse.Namespace) -> dict[str, object]:
    if args.confirm != CONFIRM_EXPORT:
        raise ArchiveError("BLOCK: exact export confirmation is required")
    root = secure_root(Path(args.archive_root))
    verify(root)
    identity = Path(args.identity_file).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if output.exists() and not args.overwrite:
        raise ArchiveError("BLOCK: export output already exists")
    records: list[dict[str, object]] = []
    for _, event in ordered_events(root):
        if args.conversation_id and event.get("conversation_id") != args.conversation_id:
            continue
        record = dict(event)
        payload = dict(record["payload"])
        ciphertext_path = str(payload.get("ciphertext_path", ""))
        if ciphertext_path and not record.get("tombstone"):
            plaintext = run_age_decrypt(args.age_binary, identity, root / ciphertext_path)
            if sha256(plaintext) != payload.get("plaintext_sha256") or len(plaintext) != payload.get("plaintext_bytes"):
                raise ArchiveError(f"BLOCK: decrypted payload does not match event {event['event_id']}")
            payload["content_utf8"] = plaintext.decode("utf-8")
        record["payload"] = payload
        records.append(record)
    value = {
        "schema": "qikvrt_interaction_export_v1",
        "authorization": {"request_id": args.request_id, "confirm": args.confirm},
        "event_count": len(records),
        "events": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return {"state": "EXPORTED", "event_count": len(records), "output": str(output), "sha256": sha256(output.read_bytes())}


def tombstone(args: argparse.Namespace) -> dict[str, object]:
    if args.confirm != CONFIRM_TOMBSTONE:
        raise ArchiveError("BLOCK: exact tombstone confirmation is required")
    root = secure_root(Path(args.archive_root))
    state = verify(root)
    source_event = read_json(root / "events" / f"{args.event_id}.json")
    event_id = uuid.uuid4().hex
    event: dict[str, object] = {
        "schema": SCHEMA,
        "event_id": event_id,
        "conversation_id": source_event.get("conversation_id"),
        "sequence": int(state["event_count"]) + 1,
        "role": "system",
        "created_at": args.created_at,
        "purpose": "retention_tombstone",
        "consent": {"consent_id": args.authorization_id, "scope": "retention_tombstone"},
        "privacy": {"plaintext_in_repository": False, "metadata_minimized": True},
        "payload": {"target_event_id": args.event_id, "ciphertext_path": ""},
        "previous_event_hash": state["head_event_hash"],
        "tombstone": True,
    }
    event["event_hash"] = sha256(canonical(event))
    (root / "events" / f"{event_id}.json").write_text(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    verify(root)
    return {"state": "TOMBSTONE_RECORDED", "event_id": event_id, "target_event_id": args.event_id}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--archive-root", required=True)
    append_parser = sub.add_parser("append")
    append_parser.add_argument("--archive-root", required=True)
    append_parser.add_argument("--content-file", required=True)
    append_parser.add_argument("--recipient", required=True)
    append_parser.add_argument("--age-binary", default="age")
    append_parser.add_argument("--event-id")
    append_parser.add_argument("--conversation-id", required=True)
    append_parser.add_argument("--role", required=True, choices=sorted(ROLE_VALUES))
    append_parser.add_argument("--created-at", required=True)
    append_parser.add_argument("--purpose", required=True)
    append_parser.add_argument("--consent-id", required=True)
    append_parser.add_argument("--retention-until", required=True)
    append_parser.add_argument("--media-type", default="text/plain; charset=utf-8")
    append_parser.add_argument("--max-bytes", type=int, default=4 * 1024 * 1024)
    append_parser.add_argument("--confirm", required=True)
    export_parser = sub.add_parser("export")
    export_parser.add_argument("--archive-root", required=True)
    export_parser.add_argument("--identity-file", required=True)
    export_parser.add_argument("--age-binary", default="age")
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--request-id", required=True)
    export_parser.add_argument("--conversation-id")
    export_parser.add_argument("--overwrite", action="store_true")
    export_parser.add_argument("--confirm", required=True)
    tombstone_parser = sub.add_parser("tombstone")
    tombstone_parser.add_argument("--archive-root", required=True)
    tombstone_parser.add_argument("--event-id", required=True)
    tombstone_parser.add_argument("--authorization-id", required=True)
    tombstone_parser.add_argument("--created-at", required=True)
    tombstone_parser.add_argument("--confirm", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "verify":
            result = verify(secure_root(Path(args.archive_root)))
        elif args.command == "append":
            result = append(args)
        elif args.command == "export":
            result = export(args)
        else:
            result = tombstone(args)
    except (ArchiveError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
