#!/usr/bin/env python3
"""Minimal fail-closed QIK-VRT Stage-1 trusted handoff.

Untrusted intake creates canonical request data only. Trusted execution checks
that data against live GitHub facts, then creates/verifies a keyed authorization
receipt. Candidate-controlled files are never imported or executed here.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class HandoffBlock(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HandoffBlock(f"{label} must be an object")
    return value


def validate_request(value: Any) -> dict[str, Any]:
    request = dict(_mapping(value, "request"))
    expected = {"schema", "transaction_id", "repository", "source_kind", "source_number", "base_sha", "head_sha", "tree_sha", "delta_sha256", "requested_operation"}
    if set(request) != expected:
        raise HandoffBlock("request fields are not canonical")
    if request["schema"] != "qikvrt_execution_request_v1":
        raise HandoffBlock("request schema mismatch")
    txid = request["transaction_id"]
    if not isinstance(txid, str) or not 8 <= len(txid) <= 160 or re.fullmatch(r"[a-zA-Z0-9._:-]+", txid) is None:
        raise HandoffBlock("transaction_id invalid")
    if not isinstance(request["repository"], str) or REPOSITORY.fullmatch(request["repository"]) is None:
        raise HandoffBlock("repository invalid")
    if request["source_kind"] not in {"pull_request", "issue", "repository_dispatch"}:
        raise HandoffBlock("source_kind invalid")
    if not isinstance(request["source_number"], int) or isinstance(request["source_number"], bool) or request["source_number"] < 0:
        raise HandoffBlock("source_number invalid")
    for name in ("base_sha", "head_sha", "tree_sha"):
        if not isinstance(request[name], str) or SHA1.fullmatch(request[name]) is None:
            raise HandoffBlock(f"{name} invalid")
    if not isinstance(request["delta_sha256"], str) or SHA256.fullmatch(request["delta_sha256"]) is None:
        raise HandoffBlock("delta_sha256 invalid")
    if request["requested_operation"] not in {"VALIDATE", "EXECUTE"}:
        raise HandoffBlock("requested_operation invalid")
    return request


def make_authorization(request: Mapping[str, Any], *, key: bytes, principal: str, installation_id: int) -> dict[str, Any]:
    if not key:
        raise HandoffBlock("handoff key missing")
    if not principal or installation_id <= 0:
        raise HandoffBlock("trusted principal identity invalid")
    req = validate_request(request)
    unsigned = {
        "schema": "qikvrt_execution_authorization_v1",
        "transaction_id": req["transaction_id"],
        "repository": req["repository"],
        "base_sha": req["base_sha"],
        "head_sha": req["head_sha"],
        "tree_sha": req["tree_sha"],
        "delta_sha256": req["delta_sha256"],
        "request_sha256": digest(req),
        "principal": principal,
        "installation_id": installation_id,
        "decision": "ALLOW",
    }
    signature = hmac.new(key, canonical_bytes(unsigned), hashlib.sha256).hexdigest()
    return {**unsigned, "signature_hmac_sha256": signature}


def verify_authorization(request: Mapping[str, Any], authorization: Mapping[str, Any], *, key: bytes, expected_principal: str, expected_installation_id: int) -> dict[str, Any]:
    req = validate_request(request)
    auth = dict(_mapping(authorization, "authorization"))
    signature = auth.pop("signature_hmac_sha256", None)
    if not isinstance(signature, str) or SHA256.fullmatch(signature) is None:
        raise HandoffBlock("authorization signature invalid")
    expected = make_authorization(req, key=key, principal=expected_principal, installation_id=expected_installation_id)
    expected_signature = expected.pop("signature_hmac_sha256")
    if auth != expected or not hmac.compare_digest(signature, expected_signature):
        raise HandoffBlock("authorization is not exactly bound to request and trusted principal")
    return {
        "schema": "qikvrt_execution_result_v1",
        "transaction_id": req["transaction_id"],
        "repository": req["repository"],
        "head_sha": req["head_sha"],
        "tree_sha": req["tree_sha"],
        "state": "AUTHORIZATION_CHECKED",
        "failure_class": None,
        "request_sha256": digest(req),
        "authorization_sha256": digest({**auth, "signature_hmac_sha256": signature}),
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-request")
    validate.add_argument("--request", type=Path, required=True)
    authorize = sub.add_parser("authorize")
    authorize.add_argument("--request", type=Path, required=True)
    authorize.add_argument("--out", type=Path, required=True)
    authorize.add_argument("--key-file", type=Path, required=True)
    authorize.add_argument("--principal", required=True)
    authorize.add_argument("--installation-id", type=int, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--request", type=Path, required=True)
    verify.add_argument("--authorization", type=Path, required=True)
    verify.add_argument("--result", type=Path, required=True)
    verify.add_argument("--key-file", type=Path, required=True)
    verify.add_argument("--principal", required=True)
    verify.add_argument("--installation-id", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-request":
            result = {"state": "REQUEST_VALID", "request_sha256": digest(validate_request(load(args.request)))}
        elif args.command == "authorize":
            result = make_authorization(validate_request(load(args.request)), key=args.key_file.read_bytes(), principal=args.principal, installation_id=args.installation_id)
            write(args.out, result)
        else:
            result = verify_authorization(load(args.request), load(args.authorization), key=args.key_file.read_bytes(), expected_principal=args.principal, expected_installation_id=args.installation_id)
            write(args.result, result)
        print(canonical_bytes(result).decode("utf-8"), end="")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, HandoffBlock) as exc:
        print(json.dumps({"state": "BLOCK", "failure_class": "TRUSTED_HANDOFF_INVALID", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
