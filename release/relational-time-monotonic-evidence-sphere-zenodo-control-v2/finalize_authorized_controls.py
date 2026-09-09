#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Create exact repository controls only after a fresh P7-bound decision.

This local helper has no network client, token handling, remote-ref operation,
or publication-evidence write. Default and check modes never write. Explicit
write mode creates controls only on checked-out main after the supplied P7
attestation binds that same head and tree.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RELEASE_RELATIVE = "release/relational-time-monotonic-evidence-sphere-zenodo-control-v2"
RELEASE = ROOT / RELEASE_RELATIVE
FROZEN_PATH = RELEASE / "FROZEN_UPLOAD_CANDIDATE.json"
AUTHORIZATION_PATH = RELEASE / "OWNER_ZENODO_AUTHORIZATION.json"
MANIFEST_PATH = RELEASE / "publish-request.json"
PUBLICATION_ID = "qikvrt-relational-time-monotonic-evidence-sphere-v1"
REPOSITORY = "Goldkelch/qik-vrt"
PRINCIPAL = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
INPUT_SCHEMA = "qikvrt_relational_time_evidence_sphere_zenodo_action_time_authorization_v2"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
LEGACY_AUTHORIZATION_ID = "qikvrt-relational-time-evidence-sphere-v1-20260831-2f5a9b9aa7cc4f92"
LICENSE = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}
AUTHORIZED_EFFECTS = [
    "ACQUIRE_REPOSITORY_REMOTE_CONSUMPTION_LOCK",
    "CREATE_PRODUCTION_ZENODO_RECORD",
    "UPLOAD_EXACT_AUTHORIZED_FILES",
    "PUBLISH_PRODUCTION_ZENODO_RECORD",
    "VERIFY_PUBLIC_BYTE_EXACT_REDOWNLOAD",
    "PERSIST_PUBLICATION_EVIDENCE",
]


def block(message: str) -> None:
    raise SystemExit("BLOCK: " + message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324


def git(*arguments: str) -> str:
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    if completed.returncode:
        block("repository Git gate rejected " + " ".join(arguments[:2]))
    return completed.stdout.strip()


def current_head() -> str:
    head = git("rev-parse", "--verify", "HEAD^{commit}")
    if HEX40.fullmatch(head) is None:
        block("current repository head is not a lowercase Git commit SHA-1")
    return head


def current_tree() -> str:
    tree = git("rev-parse", "--verify", "HEAD^{tree}")
    if HEX40.fullmatch(tree) is None:
        block("current repository tree is not a lowercase Git tree SHA-1")
    return tree


def require_clean_main() -> None:
    if git("branch", "--show-current") != "main":
        block("P7 finalization is permitted only on the checked-out main branch")
    if git("status", "--porcelain=v1"):
        block("P7 finalization requires a clean repository worktree")


def load_json(path: Path, where: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        block(f"cannot read {where}: {exc}")
    if not isinstance(value, dict):
        block(where + " must be a JSON object")
    return value


def require_rfc3339(value: Any, where: str) -> dt.datetime:
    if not isinstance(value, str):
        block(where + " must be an RFC3339 string")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        block(f"{where} is not RFC3339: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        block(where + " must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def source_commit_time(source_head: str) -> dt.datetime:
    return require_rfc3339(
        git("show", "-s", "--format=%cI", source_head),
        "selected source commit time",
    )


def identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        block("frozen candidate path is not a regular file: " + relative)
    raw = path.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha": git_blob_sha(raw),
    }


def frozen_candidate() -> dict[str, Any]:
    frozen = load_json(FROZEN_PATH, FROZEN_PATH.relative_to(ROOT).as_posix())
    if frozen.get("schema") != "qikvrt_relational_time_evidence_sphere_frozen_upload_candidate_v2":
        block("unexpected frozen-candidate schema")
    if frozen.get("state") != "FROZEN_PRE_P7":
        block("frozen candidate is not pre-P7")
    if frozen.get("publication_id") != PUBLICATION_ID or frozen.get("repository") != REPOSITORY:
        block("frozen candidate authority differs")
    files = frozen.get("files")
    if not isinstance(files, list) or len(files) != 9:
        block("frozen candidate must contain exactly nine files")
    names: set[str] = set()
    paths: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            block(f"frozen candidate entry {index} is not an object")
        if set(item) != {"path", "name", "bytes", "sha256", "git_blob_sha"}:
            block(f"frozen candidate entry {index} has an unexpected shape")
        relative = item["path"]
        name = item["name"]
        if not isinstance(relative, str) or not isinstance(name, str):
            block(f"frozen candidate entry {index} has unsafe names")
        observed = identity(relative)
        if item != {**observed, "name": name}:
            block("frozen candidate identity differs for " + relative)
        if relative in paths or name in names:
            block("frozen candidate has duplicate upload identity")
        paths.add(relative)
        names.add(name)
    for key in ("candidate_return_receipt", "machine_proof"):
        item = frozen.get(key)
        if not isinstance(item, dict):
            block("frozen candidate lacks " + key)
        observed = identity(item.get("path", ""))
        required = {name: item.get(name) for name in ("path", "bytes", "sha256", "git_blob_sha")}
        if required != observed:
            block("frozen candidate " + key + " identity differs")
    metadata = frozen.get("metadata")
    if not isinstance(metadata, dict):
        block("frozen candidate metadata is absent")
    canonical = hashlib.sha256(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if frozen.get("canonical_metadata_sha256") != canonical:
        block("frozen candidate metadata digest differs")
    return frozen


def expected_statement(authorization_id: str, frozen: dict[str, Any]) -> str:
    return (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={authorization_id} "
        f"publication_id={PUBLICATION_ID} "
        f"return_sha256={frozen['candidate_return_receipt']['sha256']} "
        f"metadata_sha256={frozen['canonical_metadata_sha256']} "
        f"machine_proof_sha256={frozen['machine_proof']['sha256']}"
    )


def load_action(path: Path, frozen: dict[str, Any]) -> dict[str, Any]:
    if not path.is_absolute():
        block("action-time authorization input path must be absolute")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        block("action-time authorization input must remain external to the repository")
    action = load_json(path, "action-time authorization input")
    expected_keys = {
        "schema",
        "authorization_id",
        "nonce",
        "principal",
        "source_head",
        "authorized_at",
        "exact_statement",
        "p7_reobservation",
    }
    if set(action) != expected_keys:
        block("action-time authorization input has an unexpected shape")
    if action["schema"] != INPUT_SCHEMA or action["principal"] != PRINCIPAL:
        block("action-time authorization input authority differs")
    authorization_id = action["authorization_id"]
    nonce = action["nonce"]
    if not isinstance(authorization_id, str) or AUTHORIZATION_ID.fullmatch(authorization_id) is None:
        block("action-time authorization ID is unsafe")
    if authorization_id == LEGACY_AUTHORIZATION_ID:
        block("consumed legacy authorization ID must not be reused")
    if not isinstance(nonce, str) or HEX64.fullmatch(nonce) is None or nonce == "0" * 64:
        block("action-time authorization nonce must be non-zero lowercase 256-bit hex")
    source_head = action["source_head"]
    if source_head != current_head() or HEX40.fullmatch(source_head) is None:
        block("action-time authorization source head is not the current head")
    authorized_at = require_rfc3339(action["authorized_at"], "authorized_at")
    if authorized_at > dt.datetime.now(dt.timezone.utc):
        block("action-time authorization is future-dated")
    p7 = action["p7_reobservation"]
    if not isinstance(p7, dict) or set(p7) != {
        "state",
        "trusted_main_head",
        "trusted_main_tree",
        "external_obligations",
        "observed_at",
        "evidence_locator",
    }:
        block("P7 reobservation has an unexpected shape")
    if (
        p7["state"] != "SATISFIED"
        or p7["external_obligations"] != "SATISFIED"
        or p7["trusted_main_head"] != source_head
        or p7["trusted_main_tree"] != current_tree()
        or not isinstance(p7["evidence_locator"], str)
        or not p7["evidence_locator"].strip()
    ):
        block("P7 reobservation does not bind the current trusted main state")
    observed_at = require_rfc3339(p7["observed_at"], "P7 observed_at")
    if observed_at < source_commit_time(source_head):
        block("P7 reobservation predates the selected source commit")
    if observed_at > authorized_at:
        block("action-time authorization predates P7 reobservation")
    if action["exact_statement"] != expected_statement(authorization_id, frozen):
        block("action-time authorization exact statement differs")
    return action


def build_controls(action: dict[str, Any], frozen: dict[str, Any]) -> tuple[bytes, bytes]:
    uploads = [
        {
            "path": item["path"],
            "name": item["name"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
            "git_blob_sha": item["git_blob_sha"],
        }
        for item in frozen["files"]
    ]
    authorization = {
        "_license": LICENSE,
        "schema": "qikvrt_zenodo_owner_authorization_v1",
        "authorization_id": action["authorization_id"],
        "nonce": action["nonce"],
        "single_use": True,
        "single_use_scope": "AUTHORITY_REPOSITORY_GLOBAL_FAIL_CLOSED",
        "principal": PRINCIPAL,
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "source_head": action["source_head"],
        "candidate_return_receipt": frozen["candidate_return_receipt"],
        "canonical_metadata_sha256": frozen["canonical_metadata_sha256"],
        "uploads": uploads,
        "machine_proof": {
            key: frozen["machine_proof"][key]
            for key in ("path", "bytes", "sha256", "git_blob_sha")
        },
        "authorized_effects": AUTHORIZED_EFFECTS,
        "publication_evidence_path": f"{RELEASE_RELATIVE}/zenodo-publication.json",
        "authorization_event": {
            "channel": "external P7-bound action-time owner authorization",
            "authorized_at": action["authorized_at"],
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": action["exact_statement"],
            "statement_sha256": hashlib.sha256(action["exact_statement"].encode("utf-8")).hexdigest(),
            "principal": PRINCIPAL,
            "candidate_return_receipt_sha256": frozen["candidate_return_receipt"]["sha256"],
        },
    }
    authorization_raw = json_bytes(authorization)
    authorization_identity = {
        "path": f"{RELEASE_RELATIVE}/OWNER_ZENODO_AUTHORIZATION.json",
        "bytes": len(authorization_raw),
        "sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "git_blob_sha": git_blob_sha(authorization_raw),
    }
    manifest = {
        "schema": "qikvrt_zenodo_publication_manifest_v2",
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": REPOSITORY,
        "source_head": action["source_head"],
        "metadata": frozen["metadata"],
        "files": [
            {key: item[key] for key in ("path", "name", "git_blob_sha")}
            for item in frozen["files"]
        ],
        "machine_proof": {
            "path": frozen["machine_proof"]["path"],
            "git_blob_sha": frozen["machine_proof"]["git_blob_sha"],
            "policy_id": frozen["machine_proof"]["policy_id"],
        },
        "owner_authorization": authorization_identity,
        "evidence_path": f"{RELEASE_RELATIVE}/zenodo-publication.json",
    }
    return authorization_raw, json_bytes(manifest)


def check_staged() -> dict[str, Any]:
    frozen = frozen_candidate()
    if AUTHORIZATION_PATH.exists() or MANIFEST_PATH.exists():
        block("production controls are already present; staged check is pre-P7 only")
    return frozen


def write_controls(action_path: Path) -> None:
    require_clean_main()
    frozen = check_staged()
    action = load_action(action_path, frozen)
    authorization_raw, manifest_raw = build_controls(action, frozen)
    created: list[Path] = []
    try:
        for path, raw in (
            (AUTHORIZATION_PATH, authorization_raw),
            (MANIFEST_PATH, manifest_raw),
        ):
            with path.open("xb") as output:
                output.write(raw)
            created.append(path)
    except OSError as exc:
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        block(f"cannot create both production controls atomically: {exc}")
    print("LOCAL_CONTROLS_CREATED: commit the two new controls separately before any effect carrier.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify inert pre-P7 staging only")
    mode.add_argument("--write", action="store_true", help="create local controls after P7")
    parser.add_argument(
        "--authorization",
        type=Path,
        help="absolute external action-time authorization JSON; required with --write",
    )
    arguments = parser.parse_args(argv)
    if arguments.write:
        if arguments.authorization is None:
            parser.error("--write requires --authorization")
        write_controls(arguments.authorization)
        return 0
    if arguments.authorization is not None:
        parser.error("--authorization is accepted only with --write")
    check_staged()
    print("CHECK: inert pre-P7 control carrier; no production controls were written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
