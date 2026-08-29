#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Plan or apply the exact QIK-VRT main-ruleset projection."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/GITHUB_MAIN_RULESET_V1.json"
SCHEMA = "qikvrt_github_main_ruleset_reconciliation_v1"


class RulesetBlock(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_policy(path: pathlib.Path = POLICY_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_github_main_ruleset_v1":
        raise RulesetBlock("ruleset policy schema mismatch")
    if value.get("repository") != "Goldkelch/qik-vrt":
        raise RulesetBlock("ruleset policy repository mismatch")
    if value.get("ruleset_id") != 19344903:
        raise RulesetBlock("ruleset policy id mismatch")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RulesetBlock(f"{label} must be an object")
    return value


def _rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise RulesetBlock("rules must be a list")
    result = []
    for raw in value:
        item = json.loads(json.dumps(dict(_mapping(raw, "rule"))))
        rule_type = item.get("type")
        if not isinstance(rule_type, str) or not rule_type:
            raise RulesetBlock("rule type is missing")
        parameters = item.get("parameters")
        if isinstance(parameters, dict):
            checks = parameters.get("required_status_checks")
            if isinstance(checks, list):
                parameters["required_status_checks"] = sorted(
                    checks,
                    key=lambda check: (
                        str(check.get("context", "")),
                        int(check.get("integration_id") or 0),
                    ),
                )
            reviewers = parameters.get("required_reviewers")
            if isinstance(reviewers, list):
                parameters["required_reviewers"] = sorted(
                    reviewers, key=lambda reviewer: json.dumps(reviewer, sort_keys=True)
                )
        result.append(item)
    return sorted(result, key=lambda item: item["type"])


def normalize(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": value.get("name"),
        "target": value.get("target"),
        "enforcement": value.get("enforcement"),
        "conditions": value.get("conditions"),
        "bypass_actors": value.get("bypass_actors") or [],
        "rules": _rules(value.get("rules")),
    }


def desired_payload(policy: Mapping[str, Any]) -> dict[str, Any]:
    return normalize(policy)


def evaluate(current: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    if current.get("id") != policy.get("ruleset_id"):
        raise RulesetBlock("observed ruleset id mismatch")
    if current.get("source") != policy.get("repository"):
        raise RulesetBlock("observed ruleset source mismatch")
    before = normalize(current)
    desired = desired_payload(policy)
    changed = sorted(
        key for key in desired if before.get(key) != desired.get(key)
    )
    return {
        "schema": SCHEMA,
        "repository": policy["repository"],
        "ruleset_id": policy["ruleset_id"],
        "state": "CURRENT" if not changed else "DRIFT",
        "changed_fields": changed,
        "pre_state_sha256": digest(before),
        "desired_state_sha256": digest(desired),
        "mutation": "NONE",
        "effect_observed": False,
    }


def _request(
    method: str,
    url: str,
    token: str,
    *,
    payload: Mapping[str, Any] | None = None,
    etag: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if etag:
        headers["If-Match"] = etag
    data = canonical_bytes(payload) if payload is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
            response_etag = response.headers.get("ETag")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RulesetBlock(f"GitHub ruleset API HTTP {exc.code}: {detail}") from exc
    if not isinstance(value, dict):
        raise RulesetBlock("GitHub ruleset API returned a non-object")
    return value, response_etag


def reconcile(token: str, policy: Mapping[str, Any]) -> dict[str, Any]:
    repository = policy["repository"]
    ruleset_id = policy["ruleset_id"]
    url = f"https://api.github.com/repos/{repository}/rulesets/{ruleset_id}"
    initial, initial_etag = _request("GET", url, token)
    plan = evaluate(initial, policy)
    if plan["state"] == "CURRENT":
        return plan

    reobserved, reobserved_etag = _request("GET", url, token)
    if digest(normalize(reobserved)) != plan["pre_state_sha256"]:
        raise RulesetBlock("ruleset drifted after planning; refusing mutation")
    conditional_etag = reobserved_etag or initial_etag
    if not conditional_etag:
        raise RulesetBlock("ruleset response omitted ETag; conditional update unavailable")
    _request(
        "PUT",
        url,
        token,
        payload=desired_payload(policy),
        etag=conditional_etag,
    )
    observed, _etag = _request("GET", url, token)
    final = evaluate(observed, policy)
    if final["state"] != "CURRENT":
        raise RulesetBlock("ruleset update was not confirmed by exact readback")
    return {
        **final,
        "pre_state_sha256": plan["pre_state_sha256"],
        "mutation": "PUT",
        "effect_observed": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=pathlib.Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args(argv)
    policy = load_policy()
    try:
        if args.apply:
            token = os.environ.get("QIKVRT_RULESET_ADMIN_TOKEN", "")
            if not token:
                raise RulesetBlock("QIKVRT_RULESET_ADMIN_TOKEN is unavailable")
            result = reconcile(token, policy)
        else:
            if args.snapshot is None:
                raise RulesetBlock("--snapshot is required without --apply")
            current = json.loads(args.snapshot.read_text(encoding="utf-8"))
            result = evaluate(_mapping(current, "ruleset snapshot"), policy)
    except (OSError, ValueError, json.JSONDecodeError, RulesetBlock) as exc:
        result = {
            "schema": SCHEMA,
            "repository": policy["repository"],
            "ruleset_id": policy["ruleset_id"],
            "state": "HOLD",
            "first_blocker": str(exc),
            "mutation": "NONE",
            "effect_observed": False,
        }
        exit_code = 2
    else:
        exit_code = 0 if result["state"] == "CURRENT" else 10
    raw = canonical_bytes(result)
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_bytes(raw)
    sys.stdout.buffer.write(raw)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
