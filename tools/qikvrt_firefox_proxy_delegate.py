#!/usr/bin/env python3
"""QIK-VRT bounded Firefox proxy delegation bridge.

The bridge opens an allowlisted HTTPS target in Firefox. It never accepts secret
values. For the narrowly authorized review effect it can bind an existing exact
PR/head/tree APPROVE disposition into the URL consumed by the QIK-VRT Firefox
extension; the extension must reobserve owner identity and exact repository
state before submitting through the already-authenticated GitHub session.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

ALLOWED_HOSTS = {"github.com"}
ACTION = "OWNER_AUTHENTICATED_BROWSER_STEP"
REVIEW_EFFECT = "OWNER_AUTHENTICATED_EXACT_REVIEW_APPROVE"


def validate_target(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("target must use https")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("target host is not allowlisted")
    if parsed.username or parsed.password:
        raise ValueError("credentials must not be embedded in target URL")
    return url


def bind_review_effect(url: str, *, owner: str, repository: str, pr: int, head: str, tree: str) -> str:
    validate_target(url)
    if repository != "Goldkelch/qik-vrt" or owner != "Goldkelch":
        raise ValueError("review effect is bound to Goldkelch/qik-vrt and owner Goldkelch")
    expected_path = f"/Goldkelch/qik-vrt/pull/{pr}/files"
    parsed = urlparse(url)
    if parsed.path.rstrip("/") != expected_path:
        raise ValueError("review effect target must be the exact PR files page")
    if len(head) != 40 or len(tree) != 40:
        raise ValueError("review effect requires full 40-hex head and tree bindings")
    try:
        int(head, 16); int(tree, 16)
    except ValueError as exc:
        raise ValueError("head and tree must be hexadecimal") from exc
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({
        "qikvrt_effect": "review_approve",
        "qikvrt_owner": owner,
        "qikvrt_repo": repository,
        "qikvrt_pr": str(pr),
        "qikvrt_head": head,
        "qikvrt_tree": tree,
    })
    return urlunparse(parsed._replace(query=urlencode(query)))


def resolve_firefox() -> str:
    explicit = os.environ.get("QIKVRT_FIREFOX_BIN", "").strip()
    if explicit:
        return explicit
    for name in ("firefox", "firefox-esr"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("Firefox executable not found")


def build_record(url: str, owner: str, repository: str, launched: bool, effect: str | None = None) -> dict[str, object]:
    review = effect == "review_approve"
    return {
        "schema": "qikvrt_firefox_proxy_delegation_v1",
        "action": REVIEW_EFFECT if review else ACTION,
        "target_url": url,
        "expected_owner": owner,
        "repository": repository,
        "launched": launched,
        "secret_serialized": False,
        "effect_executed": False,
        "next_boundary": "OWNER_AUTHENTICATED_SESSION" if review else "HUMAN_AUTHENTICATION_OR_SECRET_ENTRY",
        "post_boundary_requirement": "AUTHORITATIVE_REOBSERVATION",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-owner", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--effect", choices=["review_approve"])
    parser.add_argument("--pr", type=int)
    parser.add_argument("--head")
    parser.add_argument("--tree")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        target = validate_target(args.url)
        if args.effect == "review_approve":
            if not (args.pr and args.head and args.tree):
                raise ValueError("review_approve requires --pr, --head and --tree")
            target = bind_review_effect(
                target,
                owner=args.expected_owner,
                repository=args.repository,
                pr=args.pr,
                head=args.head,
                tree=args.tree,
            )
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

    record = build_record(target, args.expected_owner, args.repository, launched, args.effect)
    if args.json:
        print(json.dumps(record, sort_keys=True))
    else:
        print("FIREFOX_PROXY_DELEGATION=" + ("LAUNCHED" if launched else "DRY_RUN"))
        print("NEXT_BOUNDARY=" + str(record["next_boundary"]))
        print("SECRET_SERIALIZED=false")
        print("EFFECT_EXECUTED=false")
        print("POST_BOUNDARY_REQUIREMENT=AUTHORITATIVE_REOBSERVATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
