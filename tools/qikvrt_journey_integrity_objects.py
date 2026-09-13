#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Record exact-head journey integrity and public-site Git blobs; never mutate a Git ref."""
from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
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
DELIVERY_REQUEST_PATH = "state/delivery/requests/JOURNEY_47_HOMEPAGE_TO_PAGES_V1.json"
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



class RenderedPage(HTMLParser):
    """Read actual HTML text nodes, not the renderer's inventory alone."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, raw: bytes):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = {}
        self.buttons = []
        self.sections = []
        self.scripts = []
        self.styles = []
        self.feed(raw.decode("utf-8", errors="strict"))
        self.close()
        if self.stack:
            raise ValueError("HOLD: unclosed rendered HTML")

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": []}
        ident = node["attrs"].get("id")
        if ident:
            if ident in self.ids:
                raise ValueError("HOLD: duplicate rendered element id")
            self.ids[ident] = node
        if tag == "script":
            self.scripts.append(node)
        if tag == "style":
            self.styles.append(node)
        if tag == "button" and "data-lang" in node["attrs"]:
            self.buttons.append(node)
        if tag == "section" and "data-edition" in node["attrs"]:
            self.sections.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1]["tag"] != tag:
            raise ValueError("HOLD: malformed rendered HTML")
        node = self.stack.pop()
        if self.stack:
            self.stack[-1]["text"].append("".join(node["text"]))


def content_binding(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob_sha1": blob_id(raw)}


def rendered_delivery_manifest(root: Path, raw: bytes, *, head: str, tree: str) -> dict:
    """Bind candidate HTML and its DOM text; no HTTP or authority claim."""
    if any(len(v) != 40 or any(c not in "0123456789abcdef" for c in v) for v in (head, tree)):
        raise ValueError("HOLD: delivery subject must be exact head/tree")
    repository_root = root.parent.parent
    request_raw = (root / "REQUEST.json").read_bytes()
    delivery_raw = (repository_root / DELIVERY_REQUEST_PATH).read_bytes()
    delivery_request = json.loads(delivery_raw)
    if delivery_request.get("source_request") != {"path": "docs/reise/REQUEST.json", **content_binding(request_raw)}:
        raise ValueError("HOLD: delivery request source binding mismatch")
    report, editions, codes = journey_site.inspect(root)
    if report["available_count"] != 47 or not report["all_47_texts_present"]:
        raise ValueError("HOLD: delivery requires all 47 source-bound editions")
    dom = RenderedPage(raw)
    if len(dom.scripts) != 2 or "".join(dom.scripts[1]["text"]) != journey_site.JS or dom.scripts[1]["attrs"]:
        raise ValueError("HOLD: rendered chooser script mismatch")
    if len(dom.styles) != 1 or "".join(dom.styles[0]["text"]) != journey_site.CSS:
        raise ValueError("HOLD: rendered style mismatch")
    payload = json.loads("".join(dom.ids["edition-data"]["text"]))
    if payload.get("editions") != editions:
        raise ValueError("HOLD: rendered edition payload differs from source")
    wanted = ["de", "en"] + [c for c in codes if c not in ("de", "en")]
    if [b["attrs"]["data-lang"] for b in dom.buttons] != wanted or any("disabled" in b["attrs"] for b in dom.buttons):
        raise ValueError("HOLD: rendered language chooser differs from frozen scope")
    if [s["attrs"]["data-edition"] for s in dom.sections] != list(editions):
        raise ValueError("HOLD: rendered edition sections differ from source")
    if any(s["attrs"].get("lang") != s["attrs"]["data-edition"] for s in dom.sections):
        raise ValueError("HOLD: rendered section language mismatch")
    for button in dom.buttons:
        code = button["attrs"]["data-lang"]
        if not "".join(button["text"]).startswith(journey_site.NATIVE[code]):
            raise ValueError("HOLD: rendered native language name mismatch")
    for ident, expected in (("page-title", editions["de"][0]), ("page-subtitle", editions["de"][2])):
        if "".join(dom.ids[ident]["text"]) != expected:
            raise ValueError("HOLD: rendered title/subtitle differs from source")
    page = raw.decode("utf-8")
    if page.count('href="' + journey_site.MEDIA + '"') != 1:
        raise ValueError("HOLD: rendered opening media URL mismatch")
    rows = []
    for code in codes:
        values = editions[code]
        text_path = "source.de.txt" if code == "de" else "translations/" + code + ".txt"
        text_raw = journey_site.regular(root, text_path)
        if payload["raw_editions"].get(code) != text_raw.decode("utf-8"):
            raise ValueError("HOLD: rendered download differs from exact text")
        rendered = values[:3]
        for i, value in enumerate(values[3:], 3):
            node = dom.ids.get(f"{code}-p{i:04}")
            if node is None:
                raise ValueError("HOLD: rendered source block missing")
            actual = "⸻" if node["tag"] == "hr" else "".join(node["text"])
            if actual != value:
                raise ValueError("HOLD: rendered source block differs")
            rendered.append(actual)
        encoded = json.dumps(rendered, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        rows.append({"edition": code, "fragment": "#lang=" + code,
                     "text_path": "docs/reise/" + text_path, "text": content_binding(text_raw),
                     "rendered_blocks": len(rendered), "rendered_blocks_sha256": hashlib.sha256(encoded).hexdigest()})
    return {
        "schema": "qikvrt_journey_delivery_manifest_v1",
        "obligation_id": "JOURNEY_47_HOMEPAGE_TO_PAGES_V1",
        "repository": REPOSITORY, "pull_request": PR_NUMBER,
        "subject": {"head": head, "tree": tree, "role": "CANDIDATE"},
        "target_url": "https://goldkelch.github.io/qik-vrt/reise/",
        "homepage": {"path": PUBLIC_PATH, **content_binding(raw)},
        "request": {"path": "docs/reise/REQUEST.json", **content_binding(request_raw)},
        "delivery_request": {"path": DELIVERY_REQUEST_PATH, **content_binding(delivery_raw)},
        "delivery_ledger": {"path": "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json", **content_binding((repository_root / "state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json").read_bytes())},
        "language_scope": {"path": "docs/reise/WIKIPEDIA_47_LANGUAGE_SOURCE.json", **content_binding((root / "WIKIPEDIA_47_LANGUAGE_SOURCE.json").read_bytes())},
        "language_chooser": {"edition_order": wanted, "native_names": journey_site.NATIVE,
                             "script_sha256": hashlib.sha256(journey_site.JS.encode()).hexdigest(),
                             "style_sha256": hashlib.sha256(journey_site.CSS.encode()).hexdigest()},
        "editions": rows,
        "render_check": "HTML_TEXT_NODES_AND_DOWNLOAD_BYTES_MATCH_SOURCE_BOUND_EDITIONS",
        "browser_check": "REQUIRED_SEPARATELY_ON_DESKTOP_AND_MOBILE_VIEWPORTS",
        "main_binding": "REGENERATE_AND_VERIFY_AFTER_P6_ON_EXACT_TRUSTED_MAIN",
        "public_http_readback": "NOT_OBSERVED",
        "delivery_state": "CANDIDATE_BOUND_DELIVERY_PENDING",
        "predecessor_evidence_transfer": False, "native_review": False,
        "main_promotion": False, "public_delivery": False, "EFFECT_ACK_DONE": False,
    }


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
    delivery = rendered_delivery_manifest(Path("docs/reise"), site_raw, head=expected, tree=source_tree)
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
        "delivery_manifest": delivery,
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
