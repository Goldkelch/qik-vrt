#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Record exact-head journey integrity and public-site Git blobs; never mutate a Git ref."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

from tools import qikvrt_journey_site as journey_site

REPOSITORY = "Goldkelch/qik-vrt"
BRANCH = "publication/self-explanation-47-homepage-v1"
PR_NUMBER = 1080
PUBLIC_PATH = "docs/reise/index.html"
ALLOWED = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def git_paths(*args: str) -> list[str]:
    raw = subprocess.check_output(["git", *args, "-z"])
    return [part.decode("utf-8") for part in raw.split(b"\0") if part]


def blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def validate_delta(changed: list[str], untracked: list[str]) -> None:
    if untracked or set(changed) - set(ALLOWED):
        raise ValueError("HOLD: integrity delta contains non-allowlisted paths")


def verify_blob(raw: bytes, created: dict, observed: dict) -> str:
    expected = blob_id(raw)
    if created.get("sha") != expected or observed.get("sha") != expected:
        raise ValueError("HOLD: Git blob identity mismatch")
    if observed.get("encoding") != "base64" or observed.get("size") != len(raw):
        raise ValueError("HOLD: Git blob encoding/size mismatch")
    content = observed.get("content")
    if not isinstance(content, str):
        raise ValueError("HOLD: missing Git blob readback bytes")
    decoded = base64.b64decode("".join(content.split()), validate=True)
    if decoded != raw:
        raise ValueError("HOLD: Git blob readback bytes differ")
    return expected


def validate_subject(pr: dict, ref: dict, expected: str) -> None:
    head = pr.get("head", {})
    if (
        pr.get("number") != PR_NUMBER
        or pr.get("state") != "open"
        or pr.get("merged") is not False
        or head.get("repo", {}).get("full_name") != REPOSITORY
        or head.get("ref") != BRANCH
        or head.get("sha") != expected
        or pr.get("base", {}).get("ref") != "main"
        or ref.get("object", {}).get("type") != "commit"
        or ref.get("object", {}).get("sha") != expected
    ):
        raise ValueError("HOLD: exact live journey subject changed or is inadmissible")


def public_site_bytes(root: Path = Path("docs/reise")) -> bytes:
    page, report = journey_site.render(root)
    if not report.get("all_47_texts_present") or report.get("available_count") != 47:
        raise ValueError("HOLD: public site requires exact 47/47 structural coverage")
    preview_robots = '<meta name="robots" content="noindex,nofollow">'
    preview_notice = (
        '<strong>Unveröffentlichte Lesevorschau / Unpublished reading preview.</strong> '
        '47 von 47 geplanten Sprachausgaben liegen als Volltext vor. Fehlende Übersetzungen sind nicht auswählbar. '
        'Diese Vorschau ist kein Nachweis einer veröffentlichten 47-Sprachen-Homepage.'
    )
    public_notice = (
        '<strong>47-Sprachen-Leseausgabe / 47-language reading edition.</strong> '
        'Alle 47 festgelegten Sprachausgaben liegen als Volltext vor. Der deutsche Text ist die vom Autor bereitgestellte '
        'Referenz; die Übersetzungen sind ausdrücklich ungeprüfte KI-Arbeitsfassungen und keine unabhängige sprachliche Bestätigung.'
    )
    if page.count(preview_robots) != 1 or page.count(preview_notice) != 1:
        raise ValueError("HOLD: public render markers changed; explicit rebind required")
    page = page.replace(preview_robots, '<meta name="robots" content="index,follow">', 1)
    page = page.replace(preview_notice, public_notice, 1)
    if "Unveröffentlichte Lesevorschau" in page or "Unpublished reading preview" in page or "noindex,nofollow" in page:
        raise ValueError("HOLD: preview-only marker leaked into public site")
    raw = page.encode("utf-8")
    committed = root / "index.html"
    if committed.exists():
        if committed.is_symlink() or committed.read_bytes() != raw:
            raise ValueError("HOLD: committed public homepage differs from deterministic exact-source render")
    return raw


def api(method: str, endpoint: str, payload: dict | None = None) -> dict:
    token = os.environ["GH_TOKEN"]
    if not token:
        raise ValueError("HOLD: missing GitHub capability")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{endpoint}",
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def observe(expected: str) -> str:
    validate_subject(
        api("GET", f"pulls/{PR_NUMBER}"),
        api("GET", f"git/ref/heads/{BRANCH}"),
        expected,
    )
    main = api("GET", "git/ref/heads/main")["object"]["sha"]
    subprocess.run(["git", "merge-base", "--is-ancestor", main, expected], check=True)
    return main


def store_readback(raw: bytes) -> dict:
    created = api("POST", "git/blobs", {"encoding": "base64", "content": base64.b64encode(raw).decode("ascii")})
    sha = blob_id(raw)
    observed = api("GET", f"git/blobs/{sha}")
    verify_blob(raw, created, observed)
    return {"git_blob_sha1": sha, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> None:
    expected = os.environ["EXPECTED_HEAD"]
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("HOLD: wrong repository")
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("HOLD: checkout is not the literal expected head")
    source_tree = git("rev-parse", "HEAD^{tree}")
    source_main = observe(expected)
    subprocess.run(["git", "diff", "--cached", "--exit-code"], check=True)
    changed = git_paths("diff", "--name-only")
    untracked = git_paths("ls-files", "--others", "--exclude-standard")
    validate_delta(changed, untracked)
    files = {}
    if changed:
        for name in ALLOWED:
            path = Path(name)
            if path.is_symlink() or not path.is_file():
                raise ValueError("HOLD: integrity output is not a regular file")
            files[name] = store_readback(path.read_bytes())
    site_raw = public_site_bytes()
    site = store_readback(site_raw)
    if observe(expected) != source_main:
        raise ValueError("HOLD: Main changed during object materialization")
    if git("rev-parse", "HEAD") != expected:
        raise ValueError("HOLD: local subject mutated")
    receipt = {
        "schema": "qikvrt_journey_integrity_objects_v2",
        "repository": REPOSITORY,
        "pull_request": PR_NUMBER,
        "source_head": expected,
        "source_tree": source_tree,
        "source_main": source_main,
        "state": "PUBLIC_SITE_AND_INTEGRITY_GIT_OBJECTS_READ_BACK_CANDIDATE_ONLY",
        "changed_paths": sorted(changed),
        "files": files,
        "public_site_candidate": {"path": PUBLIC_PATH, **site},
        "all_47_texts_present": True,
        "linguistic_accuracy_certified": False,
        "ref_mutation": False,
        "predecessor_validation_transfer": False,
        "native_review": False,
        "public_delivery": False,
        "EFFECT_ACK_DONE": False,
    }
    output = Path(os.environ["RUNNER_TEMP"]) / "qikvrt-journey-integrity-objects.json"
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
