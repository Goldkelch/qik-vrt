#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed, exact-request GitHub administration effect executor.

The executor intentionally supports only repository ruleset pull-request review
policy updates. It performs GET -> compare-and-swap validation -> full PUT ->
GET verification and emits a redacted machine receipt. Credentials are read
only from an environment variable and are never serialized.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

SCHEMA = "qikvrt_github_admin_effect_request_v1"
RECEIPT_SCHEMA = "qikvrt_github_admin_effect_receipt_v1"
ALLOWED_PARAMETER_KEYS = {
    "required_approving_review_count",
    "require_code_owner_review",
    "dismiss_stale_reviews_on_push",
    "require_last_push_approval",
}


class AdminEffectError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdminEffectError("request must be a JSON object")
    return value


def validate_request(request: dict[str, Any]) -> None:
    if request.get("schema") != SCHEMA:
        raise AdminEffectError("unsupported request schema")
    if request.get("effect_type") != "RULESET_PULL_REQUEST_REVIEW_POLICY":
        raise AdminEffectError("unsupported effect type")
    repository = request.get("repository")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise AdminEffectError("repository must be owner/name")
    principal = request.get("admin_principal")
    if not isinstance(principal, dict):
        raise AdminEffectError("admin_principal is required")
    if principal.get("account_login") != repository.split("/", 1)[0]:
        raise AdminEffectError("admin_principal account must match repository owner")
    installation_id = principal.get("installation_id")
    if isinstance(installation_id, bool) or not isinstance(installation_id, int) or installation_id <= 0:
        raise AdminEffectError("admin_principal installation_id must be a positive integer")
    if principal.get("required_repository_permission") != "administration:write":
        raise AdminEffectError("admin_principal must require administration:write")
    ruleset_id = request.get("ruleset_id")
    if isinstance(ruleset_id, bool) or not isinstance(ruleset_id, int) or ruleset_id <= 0:
        raise AdminEffectError("ruleset_id must be a positive integer")
    expected = request.get("expected_before")
    desired = request.get("desired_after")
    if not isinstance(expected, dict) or not isinstance(desired, dict):
        raise AdminEffectError("expected_before and desired_after must be objects")
    if set(expected) != ALLOWED_PARAMETER_KEYS or set(desired) != ALLOWED_PARAMETER_KEYS:
        raise AdminEffectError("request must bind exactly the allowlisted review parameters")
    count = desired["required_approving_review_count"]
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 6:
        raise AdminEffectError("desired approving review count must be between 1 and 6")
    for key in ALLOWED_PARAMETER_KEYS - {"required_approving_review_count"}:
        if not isinstance(desired[key], bool) or not isinstance(expected[key], bool):
            raise AdminEffectError(f"{key} must be boolean")
    expected_count = expected["required_approving_review_count"]
    if isinstance(expected_count, bool) or not isinstance(expected_count, int):
        raise AdminEffectError("expected approving review count must be integer")
    authorization_id = request.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id.strip():
        raise AdminEffectError("authorization_id is required")
    if request.get("force") is not False:
        raise AdminEffectError("force must be false")


def _pull_request_parameters(ruleset: dict[str, Any]) -> dict[str, Any]:
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        raise AdminEffectError("live ruleset has no rules list")
    matches = [rule for rule in rules if isinstance(rule, dict) and rule.get("type") == "pull_request"]
    if len(matches) != 1 or not isinstance(matches[0].get("parameters"), dict):
        raise AdminEffectError("live ruleset must contain exactly one pull_request rule")
    return matches[0]["parameters"]


def _projection(parameters: dict[str, Any]) -> dict[str, Any]:
    return {key: parameters.get(key) for key in sorted(ALLOWED_PARAMETER_KEYS)}


def build_put_payload(live: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    validate_request(request)
    if live.get("id") != request["ruleset_id"]:
        raise AdminEffectError("live ruleset id differs from request")
    if live.get("name") != request.get("ruleset_name"):
        raise AdminEffectError("live ruleset name differs from request")
    if live.get("target") != "branch" or live.get("enforcement") != "active":
        raise AdminEffectError("live ruleset target/enforcement differs from contract")
    conditions = live.get("conditions")
    if conditions != request.get("expected_conditions"):
        raise AdminEffectError("live ruleset conditions differ from exact request")
    params = _pull_request_parameters(live)
    observed = _projection(params)
    desired = request["desired_after"]
    expected = request["expected_before"]
    if observed == desired:
        return {"already_applied": True, "payload": None, "observed": observed}
    if observed != expected:
        raise AdminEffectError(f"compare-and-swap mismatch: observed={observed!r}")
    payload = {
        "name": live["name"],
        "target": live["target"],
        "enforcement": live["enforcement"],
        "bypass_actors": copy.deepcopy(live.get("bypass_actors", [])),
        "conditions": copy.deepcopy(live["conditions"]),
        "rules": copy.deepcopy(live["rules"]),
    }
    target = _pull_request_parameters(payload)
    for key, value in desired.items():
        target[key] = value
    return {"already_applied": False, "payload": payload, "observed": observed}


def _api(base_url: str, token: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    data = None if payload is None else _canonical(payload)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "qikvrt-github-admin-effect-executor/1",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise AdminEffectError(f"GitHub API {method} {path} failed with HTTP {exc.code}: {detail}") from exc
    value = json.loads(body.decode("utf-8")) if body else {}
    if not isinstance(value, dict):
        raise AdminEffectError("GitHub API response must be an object")
    return value


def execute(request: dict[str, Any], *, token: str, api_base: str = "https://api.github.com", dry_run: bool = False, credential_source: str = "runtime") -> dict[str, Any]:
    validate_request(request)
    repository = request["repository"]
    ruleset_id = request["ruleset_id"]
    path = f"repos/{repository}/rulesets/{ruleset_id}"
    live_before = _api(api_base, token, "GET", path)
    plan = build_put_payload(live_before, request)
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "authorization_id": request["authorization_id"],
        "request_id": request["request_id"],
        "repository": repository,
        "admin_principal": copy.deepcopy(request["admin_principal"]),
        "credential_source": credential_source,
        "ruleset_id": ruleset_id,
        "before_sha256": _sha256(live_before),
        "observed_before": plan["observed"],
        "desired_after": request["desired_after"],
        "force": False,
        "credential_serialized": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if plan["already_applied"]:
        receipt.update({"state": "ALREADY_APPLIED", "put_executed": False, "verified": True})
        return receipt
    if dry_run:
        receipt.update({"state": "DRY_RUN", "put_executed": False, "verified": False, "payload_sha256": _sha256(plan["payload"])})
        return receipt
    _api(api_base, token, "PUT", path, plan["payload"])
    live_after = _api(api_base, token, "GET", path)
    after = _projection(_pull_request_parameters(live_after))
    if after != request["desired_after"]:
        raise AdminEffectError(f"post-effect verification mismatch: {after!r}")
    receipt.update({
        "state": "APPLIED_VERIFIED",
        "put_executed": True,
        "verified": True,
        "payload_sha256": _sha256(plan["payload"]),
        "after_sha256": _sha256(live_after),
        "observed_after": after,
        "ruleset_updated_at": live_after.get("updated_at"),
    })
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--token-env", default="QIKVRT_GITHUB_ADMIN_TOKEN")
    parser.add_argument("--credential-source", default=os.environ.get("QIKVRT_ADMIN_CREDENTIAL_SOURCE", "runtime"))
    parser.add_argument("--api-base", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    try:
        request = _load(args.request)
        token = os.environ.get(args.token_env, "")
        if not token:
            raise AdminEffectError(f"missing credential environment variable {args.token_env}")
        receipt = execute(request, token=token, api_base=args.api_base, dry_run=not args.execute, credential_source=args.credential_source)
    except (OSError, ValueError, json.JSONDecodeError, AdminEffectError) as exc:
        receipt = {"schema": RECEIPT_SCHEMA, "state": "HOLD", "verified": False, "error": str(exc), "credential_serialized": False}
        text = json.dumps(receipt, sort_keys=True, indent=2)
        if args.receipt:
            pathlib.Path(args.receipt).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 2
    text = json.dumps(receipt, sort_keys=True, indent=2)
    if args.receipt:
        pathlib.Path(args.receipt).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
