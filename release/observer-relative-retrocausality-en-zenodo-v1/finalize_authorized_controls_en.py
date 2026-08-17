#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Create and verify final English Zenodo-v2 controls after exact authorization.

This release-specific helper is intentionally local-only.  It creates the
repository-side authorization and production manifest once from a fresh,
externally supplied exact owner decision.  The generic publisher remains the
sole component that can contact Zenodo or create a publication effect.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_machine_proof as machine_proof
from tools import qikvrt_zenodo_publish as publish


RELEASE_RELATIVE = "release/observer-relative-retrocausality-en-zenodo-v1"
RELEASE = ROOT / RELEASE_RELATIVE
PUBLICATION_ID = "qikvrt-observer-relative-retrocausality-en-current-synthesis-v1"
REPOSITORY = "Goldkelch/qik-vrt"
PRINCIPAL = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
INPUT_SCHEMA = "qikvrt_observer_relative_retrocausality_en_zenodo_action_time_authorization_v1"
EXPECTED_UPLOADS = 20
AUTHORIZATION_PATH = RELEASE / "OWNER_ZENODO_AUTHORIZATION.json"
MANIFEST_PATH = RELEASE / "publish-request.json"
EVIDENCE_RELATIVE = f"{RELEASE_RELATIVE}/zenodo-publication.json"
LICENSE = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


def block(message: str) -> None:
    raise SystemExit("BLOCK: " + message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(publish.zenodo._json_bytes(value)).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324


def git(*arguments: str, accepted: frozenset[int] = frozenset({0})) -> tuple[int, str]:
    environment = {key: value for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT") if (value := os.environ.get(key)) is not None}
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    try:
        completed = subprocess.run(
            ["git", *arguments], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        block(f"cannot execute repository Git gate: {exc}")
    if completed.returncode not in accepted:
        block("repository Git gate rejected " + " ".join(arguments[:2]))
    return completed.returncode, completed.stdout.strip()


def current_head() -> str:
    _status, head = git("rev-parse", "--verify", "HEAD^{commit}")
    if publish.HEX40.fullmatch(head) is None:
        block("repository HEAD is not a lowercase Git commit SHA-1")
    return head


def require_clean_worktree() -> None:
    _status, status = git("status", "--porcelain=v1")
    if status:
        block("repository worktree must be clean")


def identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        block("required regular file is absent: " + relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob_sha": git_blob_sha1(raw)}


def load_json(relative: str) -> dict[str, Any]:
    try:
        value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        block(f"cannot read {relative}: {exc}")
    if not isinstance(value, dict):
        block(relative + " must contain a JSON object")
    return value


def source_blob(source_head: str, relative: str) -> str:
    _status, blob = git("rev-parse", "--verify", f"{source_head}:{relative}")
    if publish.HEX40.fullmatch(blob) is None:
        block("source head has an invalid blob for " + relative)
    return blob


def parse_rfc3339(value: Any, where: str) -> str:
    try:
        return publish._validate_rfc3339(value, where)
    except Exception as exc:
        block(str(exc))


def parse_time(value: str, where: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        block(f"{where} is not parseable: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        block(where + " has no timezone")
    return parsed


def source_commit_time(source_head: str) -> dt.datetime:
    _status, raw = git("show", "-s", "--format=%cI", source_head)
    return parse_time(parse_rfc3339(raw, "authorization source commit timestamp"), "authorization source commit timestamp")


def require_action_time_after_source(action_time: dt.datetime, source_head: str) -> None:
    if action_time < source_commit_time(source_head):
        block("authorization input predates the selected source commit")
    if action_time > dt.datetime.now(dt.timezone.utc):
        block("authorization input is future-dated")


def release_state() -> dict[str, Any]:
    draft_relative = f"{RELEASE_RELATIVE}/PUBLISH_REQUEST_DRAFT.json"
    bundle_relative = f"{RELEASE_RELATIVE}/MACHINE_PROOF_BUNDLE_EN.json"
    metadata_relative = f"{RELEASE_RELATIVE}/ZENODO_METADATA_DRAFT.json"
    draft = load_json(draft_relative)
    bundle = load_json(bundle_relative)
    metadata = load_json(metadata_relative)
    if draft.get("publication_id") != PUBLICATION_ID or draft.get("repository") != REPOSITORY:
        block("publish-request draft identity differs")
    if bundle.get("publication_id") != PUBLICATION_ID:
        block("machine-proof publication ID differs")
    raw_uploads = draft.get("exact_upload_files")
    if not isinstance(raw_uploads, list) or len(raw_uploads) != EXPECTED_UPLOADS:
        block(f"publish-request draft must carry exactly {EXPECTED_UPLOADS} upload files")
    files: list[dict[str, str]] = []
    authorization_uploads: list[dict[str, Any]] = []
    paths: set[str] = set()
    names: set[str] = set()
    for index, listed in enumerate(raw_uploads):
        if not isinstance(listed, dict):
            block(f"upload draft entry {index} is not an object")
        relative = listed.get("path")
        name = listed.get("name")
        if not isinstance(relative, str) or not isinstance(name, str):
            block(f"upload draft entry {index} lacks path or name")
        observed = identity(relative)
        for key in ("bytes", "sha256"):
            if listed.get(key) != observed[key]:
                block(f"upload draft {key} differs for {relative}")
        if listed.get("git_blob_sha1") != observed["git_blob_sha"]:
            block("upload draft Git blob differs for " + relative)
        if relative in paths or name in names:
            block("upload draft contains duplicate path or name")
        paths.add(relative)
        names.add(name)
        files.append({"path": relative, "name": name, "git_blob_sha": observed["git_blob_sha"]})
        authorization_uploads.append({"path": relative, "name": name, "bytes": observed["bytes"], "sha256": observed["sha256"], "git_blob_sha": observed["git_blob_sha"]})
    bundle_identity = identity(bundle_relative)
    receipt_path = bundle.get("prepublication_return", {}).get("receipt_path")
    if not isinstance(receipt_path, str):
        block("machine proof lacks prepublication return receipt path")
    receipt_identity = identity(receipt_path)
    receipt = load_json(receipt_path)
    returned_at = parse_rfc3339(receipt.get("return", {}).get("returned_at"), "prepublication return timestamp")
    return {
        "metadata": metadata,
        "metadata_sha256": canonical_json_sha256(metadata),
        "files": files,
        "authorization_uploads": authorization_uploads,
        "bundle_relative": bundle_relative,
        "bundle_identity": bundle_identity,
        "receipt_identity": receipt_identity,
        "returned_at": returned_at,
    }


def load_action(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    if not path.is_absolute():
        block("authorization input path must be absolute")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        block("authorization input must remain outside the repository")
    if not path.is_file() or path.is_symlink():
        block("authorization input must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        block(f"cannot read authorization input: {exc}")
    if not isinstance(value, dict):
        block("authorization input must be an object")
    expected = {"schema", "authorization_id", "nonce", "source_head", "principal", "authorized_at", "exact_statement"}
    if set(value) != expected or value["schema"] != INPUT_SCHEMA:
        block("authorization input schema or keys differ")
    authorization_id = value["authorization_id"]
    nonce = value["nonce"]
    source_head = value["source_head"]
    if not isinstance(authorization_id, str) or publish.SAFE_AUTHORIZATION_ID.fullmatch(authorization_id) is None:
        block("authorization input authorization_id is unsafe")
    if not isinstance(nonce, str) or publish.HEX64.fullmatch(nonce) is None or nonce == "0" * 64:
        block("authorization input nonce must be a non-zero lowercase 256-bit value")
    if not isinstance(source_head, str) or publish.HEX40.fullmatch(source_head) is None:
        block("authorization input source_head is invalid")
    if value["principal"] != PRINCIPAL:
        block("authorization input principal differs from rights holder")
    authorized_at = parse_rfc3339(value["authorized_at"], "authorization input authorized_at")
    authorized_time = parse_time(authorized_at, "authorization input authorized_at")
    if authorized_time < parse_time(state["returned_at"], "prepublication return timestamp"):
        block("authorization input predates the candidate prepublication return")
    require_action_time_after_source(authorized_time, source_head)
    expected_statement = publish._canonical_authorization_statement(authorization_id, PUBLICATION_ID, state["receipt_identity"]["sha256"], state["metadata_sha256"], state["bundle_identity"]["sha256"])
    if value["exact_statement"] != expected_statement:
        block("authorization input exact statement differs from canonical upload authorization")
    return {"authorization_id": authorization_id, "nonce": nonce, "source_head": source_head, "authorized_at": authorized_at, "exact_statement": expected_statement}


def build_controls(action: dict[str, Any], state: dict[str, Any]) -> tuple[bytes, bytes]:
    source_head = action["source_head"]
    _status, resolved = git("rev-parse", "--verify", f"{source_head}^{{commit}}")
    if resolved != source_head:
        block("authorization input source_head does not resolve")
    for upload in state["authorization_uploads"]:
        if source_blob(source_head, upload["path"]) != upload["git_blob_sha"]:
            block("source head differs from exact upload blob: " + upload["path"])
    authorization = {
        "_license": LICENSE,
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": action["authorization_id"],
        "nonce": action["nonce"],
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": PRINCIPAL,
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "source_head": source_head,
        "candidate_return_receipt": state["receipt_identity"],
        "canonical_metadata_sha256": state["metadata_sha256"],
        "uploads": state["authorization_uploads"],
        "machine_proof": state["bundle_identity"],
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": EVIDENCE_RELATIVE,
        "authorization_event": {
            "channel": "ChatGPT Work exact hash-bound owner authorization",
            "authorized_at": action["authorized_at"],
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": action["exact_statement"],
            "statement_sha256": hashlib.sha256(action["exact_statement"].encode("utf-8")).hexdigest(),
            "principal": PRINCIPAL,
            "candidate_return_receipt_sha256": state["receipt_identity"]["sha256"],
        },
    }
    authorization_raw = json_bytes(authorization)
    authorization_identity = {"path": AUTHORIZATION_PATH.relative_to(ROOT).as_posix(), "bytes": len(authorization_raw), "sha256": hashlib.sha256(authorization_raw).hexdigest(), "git_blob_sha": git_blob_sha1(authorization_raw)}
    manifest = {
        "schema": publish.SCHEMA_V2,
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": REPOSITORY,
        "source_head": source_head,
        "metadata": state["metadata"],
        "files": state["files"],
        "machine_proof": {"path": state["bundle_relative"], "git_blob_sha": state["bundle_identity"]["git_blob_sha"], "policy_id": machine_proof.POLICY_ID},
        "owner_authorization": authorization_identity,
        "evidence_path": EVIDENCE_RELATIVE,
    }
    return authorization_raw, json_bytes(manifest)


def create_once(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        block("refusing to replace final control: " + path.relative_to(ROOT).as_posix())
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        block(f"cannot create final control {path.relative_to(ROOT)}: {exc}")
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)


def validate_working_controls(source_head: str) -> dict[str, Any]:
    try:
        normalized = publish.load_manifest(MANIFEST_PATH, ROOT)
    except Exception as exc:
        block("generic publisher read-only validation rejected controls: " + str(exc))
    if normalized["source_head"] != source_head or normalized["owner_authorization"]["publication_id"] != PUBLICATION_ID:
        block("normalized final controls differ from the selected source")
    if len(normalized["files"]) != EXPECTED_UPLOADS:
        block("normalized upload count differs")
    return normalized


def write_controls(authorization_input: Path) -> None:
    require_clean_worktree()
    state = release_state()
    action = load_action(authorization_input, state)
    if action["source_head"] != current_head():
        block("--write requires authorization source_head to equal the clean execution HEAD")
    if AUTHORIZATION_PATH.exists() or MANIFEST_PATH.exists():
        block("final controls already exist; replacement is forbidden")
    authorization_raw, manifest_raw = build_controls(action, state)
    create_once(AUTHORIZATION_PATH, authorization_raw)
    create_once(MANIFEST_PATH, manifest_raw)
    normalized = validate_working_controls(action["source_head"])
    print(f"PASS materialized final English controls uploads={len(normalized['files'])} source_head={action['source_head']} authorization_id={action['authorization_id']}")


def check_controls() -> None:
    require_clean_worktree()
    if not AUTHORIZATION_PATH.is_file() or not MANIFEST_PATH.is_file():
        block("final controls are absent")
    manifest = load_json(MANIFEST_PATH.relative_to(ROOT).as_posix())
    source_head = manifest.get("source_head")
    if not isinstance(source_head, str) or publish.HEX40.fullmatch(source_head) is None:
        block("final manifest source_head is invalid")
    normalized = validate_working_controls(source_head)
    authorization_time = parse_time(normalized["owner_authorization"]["authorization_event"]["authorized_at"], "owner authorization authorized_at")
    require_action_time_after_source(authorization_time, source_head)
    execution_head = current_head()
    if source_head == execution_head:
        block("execution HEAD must be a descendant, not the source head itself")
    ancestor, _output = git("merge-base", "--is-ancestor", source_head, execution_head, accepted=frozenset({0, 1}))
    if ancestor != 0:
        block("execution HEAD is not a descendant of pre-authorization source head")
    for entry in normalized["machine_proof"]["returned_candidate_files"]:
        if source_blob(source_head, entry["path"]) != entry["git_blob_sha"]:
            block("source candidate blob differs at " + entry["path"])
    for path in (AUTHORIZATION_PATH, MANIFEST_PATH):
        relative = path.relative_to(ROOT).as_posix()
        if source_blob(execution_head, relative) != git_blob_sha1(path.read_bytes()):
            block("final control is not committed at execution HEAD: " + relative)
    print(f"PASS verified final English controls uploads={len(normalized['files'])} source_head={source_head} execution_head={execution_head}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="create the two final controls once")
    mode.add_argument("--check", action="store_true", help="verify committed final controls")
    parser.add_argument("--authorization-input", type=Path)
    args = parser.parse_args()
    if args.write:
        if args.authorization_input is None:
            parser.error("--write requires --authorization-input")
        write_controls(args.authorization_input)
    elif args.authorization_input is not None:
        parser.error("--authorization-input is valid only with --write")
    else:
        check_controls()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
