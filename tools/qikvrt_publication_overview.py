#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically keep the human and machine publication indexes complete."""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys
from typing import Any, Sequence

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MACHINE_INDEX = pathlib.Path("docs/publications/index.json")
HUMAN_INDEX = pathlib.Path("docs/publications/index.html")
PUBLICATIONS_DIRECTORY = pathlib.Path("docs/publications")
EXPECTED_SCHEMA = "qikvrt_publication_overview_v1"
DRIFT_SIGNATURE = "publication overview drift:"
COLLECTION_PATTERN = re.compile(
    r'(?P<open><div class="collection-list">\n)'
    r'(?P<body>.*?)'
    r'(?P<close>      </div>)',
    re.DOTALL,
)
DATE_PREFIX = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-")
PUBLICATION_ID = re.compile(r"^Publication ID:\s*`(?P<value>[^`]+)`\s*$", re.MULTILINE)
INDEX_STATE = re.compile(
    r"^Publication Index State:\s*`(?P<value>[^`]+)`\s*$",
    re.MULTILINE,
)
HEADING = re.compile(r"^(?P<level>#{1,2})\s+(?P<value>\S.*)$", re.MULTILINE)
VALID_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class PublicationOverviewBlock(RuntimeError):
    """A fail-closed publication overview error."""


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PublicationOverviewBlock(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationOverviewBlock(f"{path} must contain one JSON object")
    if value.get("schema") != EXPECTED_SCHEMA:
        raise PublicationOverviewBlock(f"unsupported publication index schema in {path}")
    bundles = value.get("publication_bundles")
    if not isinstance(bundles, list) or not all(isinstance(item, dict) for item in bundles):
        raise PublicationOverviewBlock("publication_bundles must be a list of objects")
    return value


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PublicationOverviewBlock(f"cannot read {path}: {exc}") from exc


def _heading_values(text: str) -> tuple[str, str | None]:
    h1: str | None = None
    h2: str | None = None
    for match in HEADING.finditer(text):
        value = match.group("value").strip()
        if match.group("level") == "#" and h1 is None:
            h1 = value
        elif match.group("level") == "##" and h2 is None:
            h2 = value
        if h1 is not None and h2 is not None:
            break
    if h1 is None:
        raise PublicationOverviewBlock("publication README has no H1 title")
    return h1, h2


def _derive_identifier(text: str, directory_name: str) -> str:
    match = PUBLICATION_ID.search(text)
    value = match.group("value").strip() if match else directory_name
    value = value.lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9._-]+", "-", value).strip("-._")
    if not VALID_IDENTIFIER.fullmatch(value):
        raise PublicationOverviewBlock(f"cannot derive a safe publication id from {directory_name}")
    return value


def _derive_state(text: str) -> str:
    explicit = INDEX_STATE.search(text)
    if explicit:
        value = explicit.group("value").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
            raise PublicationOverviewBlock("Publication Index State is not a safe identifier")
        return value
    lower = text.casefold()
    if "human physics review" in lower or "human-physics-review" in lower:
        return "repository_candidate_human_physics_review_pending"
    if "human acoustic review" in lower or "menschliche verbatim-prüfung offen" in lower:
        return "repository_candidate_human_acoustic_review_pending"
    if "open_candidate" in lower or "physikalische korrespondenz" in lower:
        return "repository_candidate_open_correspondence"
    return "repository_candidate"


def _date_label(directory_name: str) -> str:
    match = DATE_PREFIX.match(directory_name)
    if not match:
        return "Neu"
    return f"{match.group('day')}.{match.group('month')}."


def _metadata(root: pathlib.Path, readme: pathlib.Path) -> dict[str, str]:
    text = _read_text(readme)
    title, subtitle = _heading_values(text)
    relative = readme.relative_to(root).as_posix()
    directory_name = readme.parent.name
    return {
        "id": _derive_identifier(text, directory_name),
        "title": title,
        "subtitle": subtitle or "Repository-Bündel mit expliziten Evidenzgrenzen",
        "path": relative,
        "state": _derive_state(text),
        "date_label": _date_label(directory_name),
    }


def _local_readmes(root: pathlib.Path) -> list[pathlib.Path]:
    directory = root / PUBLICATIONS_DIRECTORY
    if not directory.is_dir():
        raise PublicationOverviewBlock(f"publication directory is absent: {directory}")
    result = sorted(path for path in directory.glob("*/README.md") if path.is_file())
    if not result:
        raise PublicationOverviewBlock("no local publication README files were found")
    return result


def _validate_bundles(bundles: list[dict[str, Any]]) -> None:
    paths: set[str] = set()
    identifiers: set[str] = set()
    for item in bundles:
        path = item.get("path")
        identifier = item.get("id")
        if not isinstance(path, str) or not path:
            raise PublicationOverviewBlock("publication bundle path is missing")
        if not isinstance(identifier, str) or not VALID_IDENTIFIER.fullmatch(identifier):
            raise PublicationOverviewBlock(f"invalid publication bundle id for {path}")
        if path in paths:
            raise PublicationOverviewBlock(f"duplicate publication bundle path: {path}")
        if identifier in identifiers:
            raise PublicationOverviewBlock(f"duplicate publication bundle id: {identifier}")
        paths.add(path)
        identifiers.add(identifier)


def _row(repository: str, item: dict[str, str]) -> str:
    path = item["path"]
    href = f"https://github.com/{repository}/blob/main/{path}"
    return (
        f'        <a class="collection-row" href="{html.escape(href, quote=True)}">'
        f'<time>{html.escape(item["date_label"])}</time><span>'
        f'<strong>{html.escape(item["title"])}</strong>'
        f'<small>{html.escape(item["subtitle"])}</small></span>'
        f'<b>Öffnen →</b></a>'
    )


def build_outputs(root: pathlib.Path) -> tuple[bytes, str, dict[str, Any]]:
    machine_path = root / MACHINE_INDEX
    human_path = root / HUMAN_INDEX
    index = _load_json(machine_path)
    html_text = _read_text(human_path)
    bundles = index["publication_bundles"]
    _validate_bundles(bundles)

    existing_paths = {str(item["path"]) for item in bundles}
    existing_ids = {str(item["id"]) for item in bundles}
    discovered = [_metadata(root, path) for path in _local_readmes(root)]
    missing_json: list[dict[str, str]] = []
    for item in discovered:
        if item["path"] in existing_paths:
            continue
        if item["id"] in existing_ids:
            raise PublicationOverviewBlock(
                f"new publication id collides with an existing bundle: {item['id']}"
            )
        entry = {key: item[key] for key in ("id", "title", "path", "state")}
        bundles.append(entry)
        existing_paths.add(item["path"])
        existing_ids.add(item["id"])
        missing_json.append(item)

    repository = index.get("repository")
    if not isinstance(repository, str) or "/" not in repository:
        raise PublicationOverviewBlock("publication index repository is invalid")
    collection = COLLECTION_PATTERN.search(html_text)
    if collection is None:
        raise PublicationOverviewBlock("human publication index has no collection-list block")

    missing_html = [item for item in discovered if item["path"] not in html_text]
    if missing_html:
        body = collection.group("body")
        if body and not body.endswith("\n"):
            body += "\n"
        body += "\n".join(_row(repository, item) for item in missing_html) + "\n"
        html_text = (
            html_text[: collection.start()]
            + collection.group("open")
            + body
            + collection.group("close")
            + html_text[collection.end() :]
        )

    _validate_bundles(bundles)
    indexed_paths = {str(item["path"]) for item in bundles}
    local_paths = {item["path"] for item in discovered}
    uncovered_json = sorted(local_paths - indexed_paths)
    uncovered_html = sorted(path for path in local_paths if path not in html_text)
    if uncovered_json or uncovered_html:
        raise PublicationOverviewBlock(
            f"coverage remains incomplete: json={uncovered_json}, html={uncovered_html}"
        )

    machine_bytes = (
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")
    detail = {
        "missing_machine_entries": [item["path"] for item in missing_json],
        "missing_human_entries": [item["path"] for item in missing_html],
        "local_bundle_count": len(local_paths),
        "indexed_bundle_count": len(indexed_paths),
    }
    return machine_bytes, html_text, detail


def execute(root: pathlib.Path, materialize: bool) -> dict[str, Any]:
    machine_path = root / MACHINE_INDEX
    human_path = root / HUMAN_INDEX
    expected_machine, expected_human, detail = build_outputs(root)
    current_machine = machine_path.read_bytes()
    current_human = human_path.read_text(encoding="utf-8")
    changed_paths: list[str] = []
    if current_machine != expected_machine:
        changed_paths.append(MACHINE_INDEX.as_posix())
    if current_human != expected_human:
        changed_paths.append(HUMAN_INDEX.as_posix())
    if changed_paths and materialize:
        machine_path.write_bytes(expected_machine)
        human_path.write_text(expected_human, encoding="utf-8")
        verify_machine, verify_human, _ = build_outputs(root)
        if verify_machine != expected_machine or verify_human != expected_human:
            raise PublicationOverviewBlock("materialization is not idempotent")
    return {
        "schema": "qikvrt_publication_overview_result_v1",
        "state": "MATERIALIZED" if changed_paths and materialize else (
            "DRIFT" if changed_paths else "CURRENT"
        ),
        "changed_paths": changed_paths,
        "detail": detail,
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "materialize"))
    parser.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        result = execute(root, args.command == "materialize")
    except (OSError, ValueError, json.JSONDecodeError, PublicationOverviewBlock) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if result["state"] == "DRIFT":
        print(f"{DRIFT_SIGNATURE} {rendered}", file=sys.stderr)
        return 2
    print(rendered if args.json else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
