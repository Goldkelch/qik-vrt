#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI ChatGPT.
"""Materialize the first Roundtrip entry and the owner-supplied self-declaration."""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATHS = ("README.md", "AI", "AGENTS.md", "next/README.md", "next/AI")
START = b"<!-- qikvrt-roundtrip-first:v1 -->\n"
END = b"<!-- /qikvrt-roundtrip-first:v1 -->\n\n"
DECLARATION_PATH = "docs/WENN_BEOBACHTUNG_ALS_HANDELN_AUSGEGEBEN_WIRD.md"
DECLARATION_BLOB = "a1ac6efca03171328851c1daadf45b58964d26a2"
DECLARATION_START = b"<!-- qikvrt-self-declaration:v1 -->\n"
DECLARATION_END = b"<!-- /qikvrt-self-declaration:v1 -->\n\n"
MAIN_ANCHOR = b'<main id="main">\n'
NAV_ANCHOR = b'    <nav class="navlinks" aria-label="Hauptnavigation">\n'
NAV_LINK = '      <a href="#selbsterklaerung">Selbsterklärung</a>\n'.encode("utf-8")


def prefix(relative: str) -> bytes:
    link = "../" if relative.startswith("next/") else ""
    return (START + (
        "## Zuerst: ausfuehrbarer Roundtrip-Beweis / Start here\n\n"
        f"Read [{link}ROUNDTRIP.md]({link}ROUNDTRIP.md) first. "
        f"The executable entrypoint is [{link}roundtrip.py]({link}roundtrip.py).\n"
        "From the repository root, with the locked target toolchain available:\n\n"
        "```sh\n"
        "python3 -B roundtrip.py --repository Goldkelch/qik-vrt --output-dir ../roundtrip-evidence\n"
        "```\n\n"
        "Use this checkout's actual owner/repository for a Mirror or fork. "
        "Choose a new output directory for every execution. "
        "The runner calls the existing exact-HEAD/TREE suite: C90, bus, store, "
        "restart, byte-preserving source recovery and rebuild. "
        "Runner presence is not execution evidence. The prime-search experiment "
        "has a separate, currently missing original-artifact binding; it is not "
        "replaced by this suite. Existing instructions follow unchanged.\n\n"
    ).encode("utf-8") + END)


def materialize(root: Path, *, check: bool) -> list[str]:
    pending = []
    for relative in PATHS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"ENTRYPOINT_MISSING_OR_UNSAFE: {relative}")
        raw = path.read_bytes()
        block = prefix(relative)
        if raw.startswith(block):
            continue
        if START in raw or END in raw:
            raise ValueError(f"CONFLICTING_ENTRYPOINT_PREFIX: {relative}")
        pending.append((path, block + raw))
    if check and pending:
        raise ValueError("ROUNDTRIP_NOT_FIRST: " + ", ".join(str(p.relative_to(root)) for p, _ in pending))
    if not check:
        for path, raw in pending:
            path.write_bytes(raw)
    return [str(path.relative_to(root)) for path, _ in pending]


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def declaration_source(root: Path) -> bytes:
    path = root / DECLARATION_PATH
    if not path.is_file() or path.is_symlink():
        raise ValueError("SELF_DECLARATION_SOURCE_MISSING_OR_UNSAFE")
    raw = path.read_bytes()
    if git_blob(raw) != DECLARATION_BLOB:
        raise ValueError("SELF_DECLARATION_SOURCE_BLOB_MISMATCH")
    raw.decode("utf-8", errors="strict")
    return raw


def declaration_prefix(relative: str, source: bytes) -> bytes:
    link = ("../" if relative.startswith("next/") else "") + DECLARATION_PATH
    label = "## Selbsterklärung für natürliche und künstliche kognitive Systeme\n\n"
    if relative == "README.md":
        body = label.encode("utf-8") + source + b"\n"
    else:
        body = (label + "[Wenn Beobachtung als Handeln ausgegeben wird]"
                f"({link}) — Ingolf Lohmann · September 2026.\n\n"
                "Vollständiger Text einschließlich der Ergänzung "
                "„Die gefährlichste Form des Scheiterns“.\n\n").encode("utf-8")
    return DECLARATION_START + body + DECLARATION_END


def declaration_html(source: bytes) -> bytes:
    # The supplied Markdown uses only headings and prose. Escape every source
    # byte before inserting HTML; no raw HTML, scripting or remote dependency.
    blocks = []
    for block in source.decode("utf-8").strip().split("\n\n"):
        heading = re.fullmatch(r"(#{1,3}) ([^\n]+)", block)
        if heading:
            level = len(heading[1])
            attr = ' id="self-declaration-title"' if not blocks else ""
            blocks.append(f"<h{level}{attr}>{html.escape(heading[2])}</h{level}>")
        elif block:
            blocks.append("<p>" + html.escape(block).replace("\n", "<br>\n") + "</p>")
    body = ('<section id="selbsterklaerung" class="section" lang="de" '
            'aria-labelledby="self-declaration-title">\n'
            '<div class="wrap" style="max-width: 76ch; overflow-wrap: anywhere;">\n'
            '<p class="eyebrow">Selbsterklärung für natürliche und künstliche kognitive Systeme</p>\n'
            + "\n".join(blocks) + "\n</div>\n</section>\n")
    return DECLARATION_START + body.encode("utf-8") + DECLARATION_END


def insert_declaration(raw: bytes, anchor: bytes, block: bytes, relative: str) -> bytes:
    if raw.count(anchor) != 1:
        raise ValueError(f"SELF_DECLARATION_ANCHOR_CONFLICT: {relative}")
    before, rest = raw.split(anchor, 1)
    if DECLARATION_START in before or DECLARATION_END in before:
        raise ValueError(f"SELF_DECLARATION_PREFIX_CONFLICT: {relative}")
    if DECLARATION_START in rest or DECLARATION_END in rest:
        if (not rest.startswith(DECLARATION_START)
                or rest.count(DECLARATION_START) != 1 or rest.count(DECLARATION_END) != 1):
            raise ValueError(f"SELF_DECLARATION_PREFIX_CONFLICT: {relative}")
        rest = rest.split(DECLARATION_END, 1)[1]
    return before + anchor + block + rest


def materialize_declaration(root: Path, *, check: bool) -> list[str]:
    source = declaration_source(root)
    pending = []
    for relative in (*PATHS, "docs/index.html"):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"SELF_DECLARATION_TARGET_MISSING_OR_UNSAFE: {relative}")
        raw = path.read_bytes()
        if relative == "docs/index.html":
            updated = insert_declaration(raw, MAIN_ANCHOR, declaration_html(source), relative)
            if updated.count(NAV_ANCHOR) != 1 or updated.count(NAV_LINK) > 1:
                raise ValueError("SELF_DECLARATION_NAV_CONFLICT")
            if NAV_LINK in updated:
                if NAV_ANCHOR + NAV_LINK not in updated:
                    raise ValueError("SELF_DECLARATION_NAV_CONFLICT")
            else:
                updated = updated.replace(NAV_ANCHOR, NAV_ANCHOR + NAV_LINK, 1)
        else:
            if not raw.startswith(prefix(relative)):
                raise ValueError(f"ROUNDTRIP_NOT_FIRST: {relative}")
            updated = insert_declaration(raw, prefix(relative), declaration_prefix(relative, source), relative)
        if updated != raw:
            pending.append((path, updated))
    if check and pending:
        raise ValueError("SELF_DECLARATION_NOT_CURRENT: " + ", ".join(str(p.relative_to(root)) for p, _ in pending))
    if not check:
        for path, raw in pending:
            path.write_bytes(raw)
    return [str(path.relative_to(root)) for path, _ in pending]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changed = materialize(ROOT, check=args.check)
        changed += materialize_declaration(ROOT, check=args.check)
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    print("ENTRYPOINT_CHECK_PASS" if args.check else "ENTRYPOINTS_MATERIALIZED: " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
