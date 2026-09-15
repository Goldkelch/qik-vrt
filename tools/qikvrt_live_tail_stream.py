#!/usr/bin/env python3
"""Consume the repository-native Universal Terminal journal as an append-only stream.

The producer is qikvrt_live_status_watch.yml.  This client never invents events:
it reads the marker comment, advances a persistent cursor by event identity and
prints only unseen journal records.  With --follow it waits for repository-native
journal mutations using conditional HTTP reads rather than repainting snapshots.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MARKER = "<!-- qikvrt-universal-terminal-live-surface-v1 -->"
EVENT_RE = re.compile(r"^- `(?P<time>[^`]+)` \*\*(?P<verb>[^*]+)\*\* · `(?P<subject>[^`]+)` · (?P<detail>.*?) · event `(?P<event>[^`]+)`$")


def api(url: str, token: str, etag: str | None = None):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "qikvrt-live-tail-v1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if etag:
        headers["If-None-Match"] = etag
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get("ETag"), json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, etag, None
        raise


def load_cursor(path: Path) -> dict:
    if not path.exists():
        return {"schema": "qikvrt_live_tail_cursor_v1", "last_event": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "qikvrt_live_tail_cursor_v1":
        raise SystemExit("CURSOR_SCHEMA_INVALID")
    return data


def save_cursor(path: Path, cursor: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cursor, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def find_surface(comments: list[dict]) -> dict | None:
    surfaces = [c for c in comments if MARKER in (c.get("body") or "")]
    return surfaces[-1] if surfaces else None


def events(body: str) -> list[dict]:
    out = []
    for line in body.splitlines():
        m = EVENT_RE.match(line.strip())
        if m:
            out.append(m.groupdict())
    return out


def unseen(items: list[dict], last_event: str | None) -> list[dict]:
    if last_event is None:
        return items
    for i, item in enumerate(items):
        if item["event"] == last_event:
            return items[i + 1 :]
    # The producer intentionally bounds the visible journal.  Losing the cursor
    # from that window must fail closed rather than replaying unrelated history.
    raise SystemExit("CURSOR_EVENT_NOT_IN_VISIBLE_JOURNAL")


def emit(item: dict, jsonl: bool) -> None:
    if jsonl:
        print(json.dumps(item, sort_keys=True), flush=True)
    else:
        print(f'{item["time"]}  {item["verb"]:<9}  {item["subject"]}  {item["detail"]}  [{item["event"]}]', flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"))
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--cursor", type=Path, default=Path(".qikvrt/live-tail-cursor.json"))
    p.add_argument("--follow", action="store_true")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--jsonl", action="store_true")
    args = p.parse_args()
    if args.interval < 1.0:
        raise SystemExit("INTERVAL_MINIMUM_ONE_SECOND")

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    url = f"https://api.github.com/repos/{args.repo}/issues/{args.pr}/comments?per_page=100"
    cursor = load_cursor(args.cursor)
    etag = None

    while True:
        status, etag, payload = api(url, token, etag)
        if status != 304:
            surface = find_surface(payload)
            if surface is None:
                raise SystemExit("LIVE_SURFACE_NOT_FOUND")
            fresh = unseen(events(surface.get("body") or ""), cursor.get("last_event"))
            for item in fresh:
                emit(item, args.jsonl)
                cursor = {
                    "schema": "qikvrt_live_tail_cursor_v1",
                    "repository": args.repo,
                    "pull_request": args.pr,
                    "last_event": item["event"],
                    "last_subject": item["subject"],
                    "observed_at": item["time"],
                }
                save_cursor(args.cursor, cursor)
        if not args.follow:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
