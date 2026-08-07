#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Persist application-visible I/O as metadata-only, provenance-bound evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_interaction_archive as archive

REQUEST_SCHEMA = "qikvrt_io_roundtrip_capture_request_v1"
RECEIPT_SCHEMA = "qikvrt_io_roundtrip_persistence_receipt_v1"
DISPOSITION_SCHEMA = "qikvrt_io_roundtrip_publication_disposition_v1"
WORK_UNIT_SCHEMA = "qikvrt_io_roundtrip_work_unit_v1"
CONFIRM_CAPTURE = "PERSIST_QIKVRT_IO_METADATA"
RETENTION_MODE = "METADATA_ONLY"
FALSE_CLAIMS = {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}
SAFE = re.compile(r"^[A-Za-z0-9._=-]{8,160}$")
H40 = re.compile(r"^[0-9a-f]{40}$")
H64 = re.compile(r"^[0-9a-f]{64}$")
RAW_KEYS = {"content_utf8", "raw_content", "raw_transcript", "payload_b64",
            "audio_b64", "transcript"}
DISPOSITIONS = {"HOLD", "BLOCK", "NOT_APPLICABLE", "CANDIDATE_PENDING_PROOF"}


class RoundTripError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise RoundTripError(f"BLOCK: {message}")


def canonical(value: object) -> bytes:
    return archive.canonical(value)


def sha256(raw: bytes) -> str:
    return archive.sha256(raw)


def text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                      allow_nan=False) + "\n"


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    need(path.is_file() and not path.is_symlink(), f"unsafe JSON path: {path}")
    raw = path.read_bytes()

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            need(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=lambda item: need(
                               False, f"non-finite JSON number: {item}"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoundTripError(f"BLOCK: invalid UTF-8 JSON: {exc}") from exc
    need(isinstance(value, dict), "top-level JSON must be an object")
    return value, raw


def write_once(path: Path, value: Mapping[str, Any]) -> str:
    data = text(value).encode("utf-8")
    if path.exists():
        need(not path.is_symlink() and path.read_bytes() == data,
             f"append-only output differs: {path}")
        return "ALREADY_PRESENT"
    path.parent.mkdir(parents=True, exist_ok=True)
    need(not path.parent.is_symlink(), f"unsafe output parent: {path.parent}")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return "WRITTEN"


def no_raw(value: Any, where: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            need(key not in RAW_KEYS,
                 f"raw-content key forbidden in METADATA_ONLY: {where}.{key}")
            no_raw(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            no_raw(child, f"{where}[{index}]")


def valid_time(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def validate_event(event: Any, sequence: int) -> None:
    keys = {"event_id", "sequence", "role", "created_at", "purpose", "consent_id",
            "retention_until", "media_type", "content_binding",
            "semantic_projection", "external_references", "epistemic_class"}
    need(isinstance(event, dict) and set(event) == keys,
         f"event fields differ at sequence {sequence}")
    need(isinstance(event["event_id"], str) and SAFE.fullmatch(event["event_id"]),
         "invalid event_id")
    need(event["sequence"] == sequence and event["role"] in archive.ROLE_VALUES,
         "invalid event sequence or role")
    need(valid_time(event["created_at"]) and valid_time(event["retention_until"]),
         "invalid event time")
    need(all(isinstance(event[key], str) and event[key]
             for key in ("purpose", "consent_id", "media_type", "epistemic_class")),
         "incomplete event metadata")
    binding = event["content_binding"]
    bkeys = {"scope", "normalization", "bytes", "sha256",
             "transport_exact_bytes_available", "raw_content_persisted",
             "raw_content_absence_reason"}
    need(isinstance(binding, dict) and set(binding) == bkeys,
         "content binding fields differ")
    need(binding["scope"] in {"APPLICATION_VISIBLE_UTF8", "TOOL_VISIBLE_BYTES",
                              "PREPARED_ASSISTANT_MARKDOWN"}
         and binding["normalization"] in {"NONE", "UTF8_LF"},
         "unsupported content binding scope")
    need(type(binding["bytes"]) is int and binding["bytes"] >= 0
         and isinstance(binding["sha256"], str) and H64.fullmatch(binding["sha256"]),
         "invalid byte/hash binding")
    need(type(binding["transport_exact_bytes_available"]) is bool
         and binding["raw_content_persisted"] is False
         and isinstance(binding["raw_content_absence_reason"], str)
         and bool(binding["raw_content_absence_reason"]),
         "raw-content boundary differs")
    need(isinstance(event["semantic_projection"], dict)
         and isinstance(event["external_references"], list),
         "event projection/references malformed")
    for ref in event["external_references"]:
        need(isinstance(ref, dict)
             and set(ref) == {"uri", "relation", "retrieval_state",
                              "evidence_status", "content_digest"}
             and isinstance(ref["uri"], str)
             and ref["uri"].startswith(("https://", "urn:"))
             and ref["retrieval_state"] in {"NOT_RETRIEVED", "RETRIEVED_HASH_BOUND"}
             and ref["evidence_status"] in {"REFERENCE_ONLY",
                                            "TRANSPORT_CONTEXT_ONLY",
                                            "HASH_BOUND_SOURCE"},
             "external reference malformed")
        need(ref["content_digest"] is None
             or (isinstance(ref["content_digest"], str)
                 and H64.fullmatch(ref["content_digest"])),
             "external reference digest malformed")


def validate(request: dict[str, Any], path: Path, root: Path) -> None:
    keys = {"_license", "schema", "request_id", "work_unit_id", "conversation_id",
            "created_at", "retention_mode", "source", "authorization", "actors",
            "events", "publication_disposition", "integration_gaps",
            "release_claims"}
    need(set(request) == keys and request["schema"] == REQUEST_SCHEMA
         and request["retention_mode"] == RETENTION_MODE,
         "request schema, fields, or retention mode differ")
    for key in ("request_id", "work_unit_id", "conversation_id"):
        need(isinstance(request[key], str) and SAFE.fullmatch(request[key]),
             f"invalid {key}")
    need(valid_time(request["created_at"]), "invalid request time")
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RoundTripError("BLOCK: request outside repository") from exc
    need(relative.parts[:2] == ("requests", "io"),
         "request must be below requests/io")

    source = request["source"]
    need(isinstance(source, dict)
         and set(source) == {"repository", "ref", "commit", "tree"}
         and source["repository"] == "Goldkelch/qik-vrt"
         and isinstance(source["ref"], str)
         and source["ref"].startswith("refs/heads/")
         and isinstance(source["commit"], str) and H40.fullmatch(source["commit"])
         and isinstance(source["tree"], str) and H40.fullmatch(source["tree"]),
         "source binding differs")
    need(request["authorization"] == {
        "owner_authorization_id": "OWNER_IO_ROUNDTRIP_PERSISTENCE_AUTOMATION_V1",
        "repository_continuation_delegation_id":
            "OWNER-AUTONOMOUS-REPOSITORY-CONTINUATION-V2",
        "persistence_confirmation": CONFIRM_CAPTURE,
        "external_effects_default": "FORBIDDEN",
    }, "authorization binding differs")
    need(request["release_claims"] == FALSE_CLAIMS,
         "unsupported release claim")
    actors = request["actors"]
    need(isinstance(actors, dict)
         and set(actors) == {"human", "artificial_cognitive_system"}
         and all(isinstance(actor, dict) and actor.get("attribution_id")
                 and actor.get("role") for actor in actors.values()),
         "actor attribution differs")
    events = request["events"]
    need(isinstance(events, list) and bool(events), "events missing")
    for sequence, event in enumerate(events, 1):
        validate_event(event, sequence)
    event_ids = [event["event_id"] for event in events]
    need(len(event_ids) == len(set(event_ids)), "duplicate event_id")

    disposition = request["publication_disposition"]
    need(isinstance(disposition, dict)
         and set(disposition) == {"candidate_knowledge", "zenodo", "ietf"}
         and isinstance(disposition["candidate_knowledge"], list),
         "publication disposition malformed")
    for target in ("zenodo", "ietf"):
        decision = disposition[target]
        need(isinstance(decision, dict)
             and decision.get("state") in DISPOSITIONS
             and decision.get("external_effect_authorized") is False
             and decision.get("external_effect_executed") is False
             and bool(decision.get("reason_codes"))
             and bool(decision.get("next_gate")),
             f"{target} disposition is not fail-closed")
    for claim in disposition["candidate_knowledge"]:
        need(isinstance(claim, dict)
             and set(claim) == {"claim_id", "summary", "epistemic_class",
                                "verification_state", "source_event_ids"}
             and isinstance(claim["claim_id"], str)
             and SAFE.fullmatch(claim["claim_id"])
             and set(claim["source_event_ids"]).issubset(set(event_ids)),
             "candidate knowledge binding differs")
    need(isinstance(request["integration_gaps"], list),
         "integration_gaps malformed")
    no_raw(request)


def event_projection(request: Mapping[str, Any], event: Mapping[str, Any],
                     request_sha: str) -> dict[str, Any]:
    binding = event["content_binding"]
    return {
        "schema": archive.SCHEMA,
        "event_id": event["event_id"],
        "conversation_id": request["conversation_id"],
        "role": event["role"],
        "created_at": event["created_at"],
        "purpose": event["purpose"],
        "consent": {"consent_id": event["consent_id"],
                    "scope": "metadata_only_io_persistence"},
        "privacy": {"plaintext_in_repository": False,
                    "encryption": "NONE_METADATA_ONLY",
                    "metadata_minimized": True,
                    "retention_until": event["retention_until"],
                    "retention_mode": RETENTION_MODE},
        "payload": {
            "media_type": event["media_type"],
            "plaintext_bytes": binding["bytes"],
            "plaintext_sha256": binding["sha256"],
            "ciphertext_path": "",
            "ciphertext_bytes": 0,
            "ciphertext_sha256": "",
            "content_binding_scope": binding["scope"],
            "normalization": binding["normalization"],
            "transport_exact_bytes_available":
                binding["transport_exact_bytes_available"],
            "raw_content_persisted": False,
            "raw_content_absence_reason": binding["raw_content_absence_reason"],
        },
        "provenance": {
            "request_id": request["request_id"],
            "request_sha256": request_sha,
            "source_repository": request["source"]["repository"],
            "source_ref": request["source"]["ref"],
            "source_commit": request["source"]["commit"],
            "source_tree": request["source"]["tree"],
            "owner_authorization_id":
                request["authorization"]["owner_authorization_id"],
            "artificial_cognitive_attribution_id":
                request["actors"]["artificial_cognitive_system"]["attribution_id"],
        },
        "semantic_projection": event["semantic_projection"],
        "semantic_projection_sha256": sha256(canonical(event["semantic_projection"])),
        "external_references": event["external_references"],
        "external_references_sha256": sha256(canonical(event["external_references"])),
        "epistemic_class": event["epistemic_class"],
        "tombstone": False,
    }


def core(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items()
            if key not in {"sequence", "previous_event_hash", "event_hash"}}


def append_events(root: Path, request: Mapping[str, Any],
                  request_sha: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive_root = archive.secure_root(
        root / "state" / "interaction_archive" / "io-roundtrip")
    bindings: list[dict[str, Any]] = []
    for source in request["events"]:
        path = archive_root / "events" / f"{source['event_id']}.json"
        expected = event_projection(request, source, request_sha)
        if path.exists():
            event, _ = read_json(path)
            need(core(event) == expected, f"existing event differs: {source['event_id']}")
            status = "ALREADY_PRESENT"
        else:
            state = archive.verify(archive_root)
            event = {**expected, "sequence": state["event_count"] + 1,
                     "previous_event_hash": state["head_event_hash"]}
            event["event_hash"] = sha256(canonical(event))
            write_once(path, event)
            archive.verify(archive_root)
            status = "WRITTEN"
        bindings.append({
            "event_id": source["event_id"],
            "path": str(path.relative_to(root)),
            "sequence": event["sequence"],
            "event_hash": event["event_hash"],
            "content_sha256": source["content_binding"]["sha256"],
            "write_status": status,
        })
    return bindings, archive.verify(archive_root)


def stable(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in item.items() if key != "write_status"}
            for item in bindings]


def output_paths(root: Path, request: Mapping[str, Any]) -> dict[str, Path]:
    request_id = request["request_id"]
    return {
        "disposition": root / "state" / "io_roundtrip" / "dispositions"
                       / f"{request_id}.json",
        "receipt": root / "evidence" / "receipts"
                   / f"io-roundtrip-{request_id}.json",
        "work_unit": root / "state" / "work_units"
                     / f"{request['work_unit_id']}.json",
    }


def build(request: Mapping[str, Any], request_path: Path, request_sha: str,
          bindings: list[dict[str, Any]], state: Mapping[str, Any], root: Path
          ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bound, paths = stable(bindings), output_paths(root, request)
    disposition = {
        "_license": request["_license"],
        "schema": DISPOSITION_SCHEMA,
        "request_id": request["request_id"],
        "created_at": request["created_at"],
        "request": {"path": str(request_path), "sha256": request_sha},
        "event_bindings": bound,
        "candidate_knowledge":
            request["publication_disposition"]["candidate_knowledge"],
        "zenodo": request["publication_disposition"]["zenodo"],
        "ietf": request["publication_disposition"]["ietf"],
        "classification_boundary": {
            "repository_persistence_is_publication": False,
            "owner_assertion_is_formal_proof": False,
            "reference_uri_is_retrieved_evidence": False,
            "machine_verification_required_before_publication": True,
        },
        "release_claims": FALSE_CLAIMS,
    }
    disposition_sha = sha256(text(disposition).encode("utf-8"))
    receipt = {
        "_license": request["_license"],
        "schema": RECEIPT_SCHEMA,
        "request_id": request["request_id"],
        "created_at": request["created_at"],
        "retention_mode": RETENTION_MODE,
        "request": {"path": str(request_path), "sha256": request_sha},
        "events": bound,
        "archive": {
            "path": "state/interaction_archive/io-roundtrip",
            "event_count_at_capture": state["event_count"],
            "request_terminal_event_hash": bound[-1]["event_hash"],
            "archive_head_event_hash_observed_at_capture": state["head_event_hash"],
            "verification_state": state["state"],
        },
        "disposition": {"path": str(paths["disposition"].relative_to(root)),
                        "sha256": disposition_sha},
        "source_binding": request["source"],
        "verification": {
            "request_validated": True,
            "event_chain_verified": True,
            "raw_content_persisted": False,
            "publication_effect_executed": False,
            "repository_integrity": "PENDING_MATERIALIZATION",
            "exact_head_ci": "PENDING",
        },
        "integration_gaps": request["integration_gaps"],
        "state": "MATERIALIZED_CONTINUE",
        "release_claims": FALSE_CLAIMS,
    }
    receipt_sha = sha256(text(receipt).encode("utf-8"))
    work_unit = {
        "_license": request["_license"],
        "schema": WORK_UNIT_SCHEMA,
        "work_unit_id": request["work_unit_id"],
        "created_at": request["created_at"],
        "source_repository": request["source"]["repository"],
        "source_ref": request["source"]["ref"],
        "source_commit": request["source"]["commit"],
        "source_tree": request["source"]["tree"],
        "human_actor": request["actors"]["human"],
        "artificial_cognitive_actor":
            request["actors"]["artificial_cognitive_system"],
        "contributions": {
            "human": ["canonical workspace declaration", "evidence boundary",
                      "reference context"],
            "artificial_cognitive_system": ["repository reobservation",
                                            "reuse analysis",
                                            "capture and disposition"],
        },
        "inputs": {"retention_mode": RETENTION_MODE,
                   "request_path": str(request_path),
                   "request_sha256": request_sha,
                   "raw_transcript_persisted": False,
                   "events": [{"event_id": item["event_id"],
                               "content_sha256": item["content_sha256"],
                               "event_hash": item["event_hash"]}
                              for item in bound]},
        "outputs": {"paths": [item["path"] for item in bound] + [
                        str(paths["disposition"].relative_to(root)),
                        str(paths["receipt"].relative_to(root))],
                    "disposition_sha256": disposition_sha,
                    "receipt_sha256": receipt_sha,
                    "self_binding_rule":
                        "The containing Git commit/tree binds this file."},
        "git_history": {"branch": request["source"]["ref"].removeprefix("refs/heads/"),
                        "base_commit": request["source"]["commit"],
                        "content_commit": "PENDING_CALLER_COMMIT",
                        "force_push": False, "history_rewrite": False,
                        "merge": "NOT_EXECUTED"},
        "verification": {
            "focused_command":
                "python3 -B -m unittest -v tests.test_qikvrt_io_roundtrip",
            "archive_chain": "VERIFIED",
            "repository_native_integrity": "PENDING",
            "exact_head_ci": "PENDING",
            "first_current_blocker":
                "GIT_BINDING_REPOSITORY_INTEGRITY_AND_EXACT_HEAD_CI_PENDING",
        },
        "human_decision": {"directive": "RECEIVED",
                           "candidate_review": "PENDING",
                           "acceptance": "NOT_YET_RECORDED",
                           "rejection": "NOT_RECORDED"},
        "external_effects": {"repository_file_commit": "PENDING_CALLER_COMMIT",
                             "pull_request": "EXISTING_DRAFT_PR_501",
                             "merge": "NOT_EXECUTED",
                             "release": "NOT_EXECUTED",
                             "deployment": "NOT_EXECUTED",
                             "zenodo": "NOT_EXECUTED",
                             "ietf": "NOT_EXECUTED"},
        "candidate_state":
            "MATERIALIZED_PENDING_GIT_INTEGRITY_EXACT_HEAD_CI_AND_REVIEW",
        "release_claims": FALSE_CLAIMS,
    }
    return disposition, receipt, work_unit


def capture(root: Path, request_path: Path, *, confirm: str) -> dict[str, Any]:
    need(confirm == CONFIRM_CAPTURE,
         f"exact confirmation {CONFIRM_CAPTURE!r} required")
    root, request_path = root.resolve(), request_path.resolve()
    request, raw = read_json(request_path)
    validate(request, request_path, root)
    relative, request_sha = request_path.relative_to(root), sha256(raw)
    paths = output_paths(root, request)
    if all(path.is_file() and not path.is_symlink() for path in paths.values()):
        return {**verify(root, request_path), "operation": "capture",
                "write_status": "NOOP_ALREADY_MATERIALIZED"}

    bindings, state = append_events(root, request, request_sha)
    disposition, receipt, work_unit = build(
        request, relative, request_sha, bindings, state, root)
    statuses = {"events": [item["write_status"] for item in bindings],
                "disposition": write_once(paths["disposition"], disposition),
                "receipt": write_once(paths["receipt"], receipt),
                "work_unit": write_once(paths["work_unit"], work_unit)}
    return {**verify(root, request_path), "operation": "capture",
            "write_status": statuses}


def safe_event_path(root: Path, raw: Any) -> Path:
    need(isinstance(raw, str), "event path missing")
    relative = Path(raw)
    prefix = Path("state/interaction_archive/io-roundtrip/events").parts
    need(not relative.is_absolute() and ".." not in relative.parts
         and relative.parts[:len(prefix)] == prefix, "unsafe event path")
    path = root / relative
    resolved = path.parent.resolve()
    need(resolved == root.resolve() or root.resolve() in resolved.parents,
         "event path escapes repository")
    return path


def verify(root: Path, request_path: Path) -> dict[str, Any]:
    root, request_path = root.resolve(), request_path.resolve()
    request, raw = read_json(request_path)
    validate(request, request_path, root)
    relative, request_sha = request_path.relative_to(root), sha256(raw)
    paths = output_paths(root, request)
    need(all(path.is_file() and not path.is_symlink() for path in paths.values()),
         "receipt, disposition and work unit are not all materialized")
    state = archive.verify(archive.secure_root(
        root / "state" / "interaction_archive" / "io-roundtrip"))
    disposition, _ = read_json(paths["disposition"])
    receipt, _ = read_json(paths["receipt"])
    work_unit, _ = read_json(paths["work_unit"])
    need(disposition.get("schema") == DISPOSITION_SCHEMA
         and receipt.get("schema") == RECEIPT_SCHEMA
         and work_unit.get("schema") == WORK_UNIT_SCHEMA,
         "persisted schema binding differs")
    expected_request = {"path": str(relative), "sha256": request_sha}
    need(receipt.get("request") == expected_request
         and disposition.get("request") == expected_request,
         "request path/hash binding differs")
    need(work_unit.get("work_unit_id") == request["work_unit_id"],
         "work-unit identity differs")

    request_events = {item["event_id"]: item for item in request["events"]}
    bindings = receipt.get("events")
    need(isinstance(bindings, list) and len(bindings) == len(request_events),
         "receipt event count differs")
    terminal = None
    for binding in bindings:
        event_id = binding.get("event_id")
        need(event_id in request_events, "receipt references unknown event")
        event, _ = read_json(safe_event_path(root, binding.get("path")))
        projection = dict(event)
        event_hash = projection.pop("event_hash", None)
        need(event_hash == sha256(canonical(projection))
             and event_hash == binding.get("event_hash"),
             f"event/receipt hash differs: {event_id}")
        need(core(event) == event_projection(
            request, request_events[event_id], request_sha),
            f"event provenance differs: {event_id}")
        need(binding.get("content_sha256")
             == request_events[event_id]["content_binding"]["sha256"],
             f"content digest differs: {event_id}")
        terminal = event_hash
    need(receipt.get("archive", {}).get("request_terminal_event_hash") == terminal,
         "request-terminal event hash differs")

    disposition_sha = sha256(paths["disposition"].read_bytes())
    need(receipt.get("disposition") == {
        "path": str(paths["disposition"].relative_to(root)),
        "sha256": disposition_sha}, "disposition receipt binding differs")
    need(work_unit.get("outputs", {}).get("receipt_sha256")
         == sha256(paths["receipt"].read_bytes())
         and work_unit.get("outputs", {}).get("disposition_sha256")
         == disposition_sha, "work-unit output digest differs")
    for value in (request, disposition, receipt, work_unit):
        no_raw(value)
        need(value.get("release_claims") == FALSE_CLAIMS,
             "unsupported release claim persisted")
    need(disposition["zenodo"]["external_effect_executed"] is False
         and disposition["ietf"]["external_effect_executed"] is False,
         "external publication effect improperly claimed")
    return {
        "state": "VERIFIED_CONTINUE",
        "request_id": request["request_id"],
        "work_unit_id": request["work_unit_id"],
        "request_sha256": request_sha,
        "event_count": len(bindings),
        "archive_event_count": state["event_count"],
        "archive_head_event_hash": state["head_event_hash"],
        "receipt_path": str(paths["receipt"].relative_to(root)),
        "receipt_sha256": sha256(paths["receipt"].read_bytes()),
        "disposition_path": str(paths["disposition"].relative_to(root)),
        "disposition_sha256": disposition_sha,
        "work_unit_path": str(paths["work_unit"].relative_to(root)),
        "raw_content_persisted": False,
        "zenodo_effect": "NOT_EXECUTED",
        "ietf_effect": "NOT_EXECUTED",
        "release_claims": FALSE_CLAIMS,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    capture_command = commands.add_parser("capture")
    capture_command.add_argument("--repository-root", default=".")
    capture_command.add_argument("--request", required=True)
    capture_command.add_argument("--confirm", required=True)
    verify_command = commands.add_parser("verify")
    verify_command.add_argument("--repository-root", default=".")
    verify_command.add_argument("--request", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = Path(args.repository_root)
        request = Path(args.request)
        if not request.is_absolute():
            request = root / request
        result = capture(root, request, confirm=args.confirm) \
            if args.command == "capture" else verify(root, request)
    except (RoundTripError, archive.ArchiveError, OSError, ValueError,
            json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
