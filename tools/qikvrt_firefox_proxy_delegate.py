#!/usr/bin/env python3
"""QIK-VRT bounded Firefox proxy delegation bridge.

The bridge opens an allowlisted HTTPS target in Firefox and then stops at the
human-authentication boundary. It deliberately has no parameter for secret
values and performs no repository mutation itself.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ALLOWED_HOSTS = {"github.com"}
ACTION = "OWNER_AUTHENTICATED_BROWSER_STEP"


def validate_target(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("target must use https")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("target host is not allowlisted")
    if parsed.username or parsed.password:
        raise ValueError("credentials must not be embedded in target URL")
    return url


def resolve_firefox() -> str:
    explicit = os.environ.get("QIKVRT_FIREFOX_BIN", "").strip()
    if explicit:
        return explicit
    for name in ("firefox", "firefox-esr"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("Firefox executable not found")


def build_record(url: str, owner: str, repository: str, launched: bool) -> dict[str, object]:
    return {
        "schema": "qikvrt_firefox_proxy_delegation_v1",
        "action": ACTION,
        "target_url": url,
        "expected_owner": owner,
        "repository": repository,
        "launched": launched,
        "secret_serialized": False,
        "effect_executed": False,
        "next_boundary": "HUMAN_AUTHENTICATION_OR_SECRET_ENTRY",
        "post_boundary_requirement": "AUTHORITATIVE_REOBSERVATION",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-owner", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        target = validate_target(args.url)
    except ValueError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 4

    launched = False
    if not args.dry_run:
        try:
            firefox = resolve_firefox()
        except FileNotFoundError as exc:
            print(f"HOLD: {exc}", file=sys.stderr)
            return 3
        subprocess.Popen(
            [firefox, "--new-tab", target],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        launched = True

    record = build_record(target, args.expected_owner, args.repository, launched)
    if args.json:
        print(json.dumps(record, sort_keys=True))
    else:
        print("FIREFOX_PROXY_DELEGATION=" + ("LAUNCHED" if launched else "DRY_RUN"))
        print("NEXT_BOUNDARY=HUMAN_AUTHENTICATION_OR_SECRET_ENTRY")
        print("SECRET_SERIALIZED=false")
        print("EFFECT_EXECUTED=false")
        print("POST_BOUNDARY_REQUIREMENT=AUTHORITATIVE_REOBSERVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
