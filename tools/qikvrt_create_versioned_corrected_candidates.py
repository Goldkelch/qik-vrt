#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Create six versioned corrected corpus candidates without mutating Zenodo.

The historical public records remain immutable inputs.  This executor downloads
and byte-verifies the exact public archives, narrows every claim marked
REQUIRES_VERSIONED_CORRECTION, regenerates all resolvable internal SHA-256
bindings, explicitly excludes self/cyclic hash bindings, builds deterministic
candidate ZIPs, and returns exact receipts to the owner.  It performs no Zenodo
write and makes no repository-wide completion claim.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import pathlib
import re
import shutil
import stat
import urllib.parse
import zipfile
from collections import defaultdict
from typing import Any, Iterable, Mapping

from tools import qikvrt_batch003_remaining_archive_probe as remaining_probe
from tools import qikvrt_batch003_subject_172dd_public_probe as subject_172_probe

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNION = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
BATCH = UNION / "content-disposition-batch-003"
OUTPUT = UNION / "versioned-corrected-candidates"
WORK_UNIT = ROOT / "work-units/CREATE_VERSIONED_CORRECTED_CANDIDATES_REMAINING_CORPUS_SUBJECTS.json"
OWNER_WORK_UNIT = ROOT / "work-units/OWNER_DECISION_VERSIONED_CORRECTED_CANDIDATES.json"
OBSERVED_AT = "2026-07-30T06:15:00Z"
CANDIDATE_VERSION = "v1"

LICENSE = {
    "classification": "machine_readable_versioned_corrected_candidate",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "rights_holder": "Ingolf Lohmann",
}

SUBJECTS = [
    {
        "subject_id": "SUBJECT-172dd9bc2738fa43",
        "records": [{"id": 20712301, "doi": "10.5281/zenodo.20712301", "name": subject_172_probe.ARCHIVE_NAME}],
        "file": dict(subject_172_probe.EXPECTED[subject_172_probe.ARCHIVE_NAME]),
    },
    *copy.deepcopy(remaining_probe.SUBJECTS),
]
EXPECTED_SUBJECT_IDS = [row["subject_id"] for row in SUBJECTS]

POSITIVE = re.compile(
    r"\b(PASS(?:_[A-Z0-9_]+)?|DONE|COMPLETED|COMPLETE|FINAL_PASS|"
    r"EFFECT_ACK_DONE|P_NASH\s*[:=]\s*(?:TRUE|`TRUE`)|PERSISTED|"
    r"DEPLOYED|PUBLISHED|MERGED|SYNCHRONIZED)\b",
    re.IGNORECASE,
)
UNIVERSAL = re.compile(
    r"\b(universal(?:e|er|es|ly)?|allumfassend|vollständig(?:e|er|es)?|"
    r"endgültig|unzweifelhaft|alle\s+(?:relevanten\s+)?schichten|"
    r"across all relevant layers|entire system|full repository)\b",
    re.IGNORECASE,
)
CHECKSUM = re.compile(r"^(\s*)([0-9a-fA-F]{64})(\s+[* ]?)(.+?)(\s*)$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
CHECKSUM_NAMES = {"sha256sums.txt", "sha256sum.txt", "checksums.sha256"}
STRUCTURED_COMMENT_EXTENSIONS = {".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
MARKDOWN_EXTENSIONS = {".md", ".txt", ".tex", ".bib"}
COMPRESSED_EXTENSIONS = {
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".pdf", ".mp3", ".mp4", ".ogg", ".m4a", ".woff",
    ".woff2", ".jar", ".whl",
}


class CorrectionError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise CorrectionError(message)


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def binding(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "git_blob_sha1": git_blob_sha1(raw),
    }


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty(value), encoding="utf-8", newline="\n")


def decode_text(data: bytes) -> tuple[str | None, str | None]:
    if b"\0" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return None, None
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\0" not in text:
            return text.replace("\r\n", "\n").replace("\r", "\n"), encoding
    return None, None


def safe_path(name: str) -> pathlib.PurePosixPath:
    if not name or "\\" in name or "\0" in name:
        fail(f"unsafe ZIP path encoding: {name!r}")
    path = pathlib.PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        fail(f"unsafe ZIP path: {name}")
    if len(path.as_posix()) > 1024:
        fail(f"ZIP path too long: {name}")
    return path


def parse_archive(data: bytes, label: str, depth: int = 0) -> dict[str, Any]:
    if depth > remaining_probe.MAX_DEPTH:
        fail(f"nested ZIP depth exceeds {remaining_probe.MAX_DEPTH}: {label}")
    try:
        context = zipfile.ZipFile(io.BytesIO(data), "r")
    except zipfile.BadZipFile as exc:
        raise CorrectionError(f"invalid ZIP archive {label}: {exc}") from exc
    entries: dict[str, dict[str, Any]] = {}
    seen_casefold: set[str] = set()
    with context as archive:
        bad = archive.testzip()
        if bad is not None:
            fail(f"ZIP CRC failure: {label}!/{bad}")
        for info in archive.infolist():
            path = safe_path(info.filename)
            normalized = path.as_posix().rstrip("/")
            folded = normalized.casefold()
            if normalized in entries or folded in seen_casefold:
                fail(f"duplicate or case-colliding ZIP path: {label}!/{normalized}")
            seen_casefold.add(folded)
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                fail(f"ZIP symlink rejected: {label}!/{normalized}")
            if info.flag_bits & 0x1:
                fail(f"encrypted ZIP entry rejected: {label}!/{normalized}")
            if info.file_size > remaining_probe.MAX_ENTRY:
                fail(f"ZIP entry exceeds size bound: {label}!/{normalized}")
            row: dict[str, Any] = {
                "path": normalized,
                "is_directory": info.is_dir(),
                "mode": mode,
                "original_compress_type": info.compress_type,
                "data": b"",
                "nested": None,
            }
            if not info.is_dir():
                payload = archive.read(info)
                nested = path.suffix.lower() == ".zip" or payload.startswith(b"PK\x03\x04")
                if nested:
                    if not zipfile.is_zipfile(io.BytesIO(payload)):
                        fail(f"ZIP-labelled entry is invalid: {label}!/{normalized}")
                    row["nested"] = parse_archive(payload, f"{label}!/{normalized}", depth + 1)
                row["data"] = payload
            entries[normalized] = row
    return {"label": label, "entries": entries, "depth": depth}


def render_archive(node: Mapping[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        allowZip64=True,
    ) as archive:
        for path in sorted(node["entries"], key=lambda value: value.casefold()):
            entry = node["entries"][path]
            name = path + "/" if entry["is_directory"] else path
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            mode = int(entry.get("mode") or (0o40755 if entry["is_directory"] else 0o100644))
            info.external_attr = mode << 16
            if entry["is_directory"]:
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, b"")
                continue
            suffix = pathlib.PurePosixPath(path).suffix.lower()
            info.compress_type = zipfile.ZIP_STORED if suffix in COMPRESSED_EXTENSIONS else zipfile.ZIP_DEFLATED
            archive.writestr(info, entry["data"])
    return buffer.getvalue()


def walk_entries(node: Mapping[str, Any]) -> Iterable[tuple[str, dict[str, Any], Mapping[str, Any]]]:
    for path, entry in node["entries"].items():
        qualified = f"{node['label']}!/{path}"
        yield qualified, entry, node
        nested = entry.get("nested")
        if isinstance(nested, Mapping):
            yield from walk_entries(nested)


def entry_map(node: Mapping[str, Any]) -> dict[str, tuple[dict[str, Any], Mapping[str, Any]]]:
    return {qualified: (entry, owner) for qualified, entry, owner in walk_entries(node)}


def flattened_hashes(node: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for qualified, entry, _owner in walk_entries(node):
        if entry["is_directory"]:
            continue
        raw = entry["data"]
        result[qualified] = {"bytes": len(raw), "sha256": sha256_bytes(raw)}
    return result


def fetch_subject_archive(config: Mapping[str, Any]) -> tuple[bytes, list[dict[str, Any]]]:
    subject_id = str(config["subject_id"])
    if subject_id == "SUBJECT-172dd9bc2738fa43":
        _record, files, observations = subject_172_probe.fetch_public_record()
        archive = files[subject_172_probe.ARCHIVE_NAME]
        return archive, [{
            "record_id": subject_172_probe.RECORD_ID,
            "doi": subject_172_probe.DOI,
            "public_name": subject_172_probe.ARCHIVE_NAME,
            **observations[subject_172_probe.ARCHIVE_NAME],
        }]

    expected = config["file"]
    source: bytes | None = None
    observations: list[dict[str, Any]] = []
    for record in config["records"]:
        record_id = int(record["id"])
        raw_metadata = remaining_probe.get(
            f"https://zenodo.org/api/records/{record_id}",
            "application/json",
            8 * 1024 * 1024,
        )
        try:
            metadata = json.loads(raw_metadata)
        except Exception as exc:
            raise CorrectionError(f"invalid Zenodo metadata for {record_id}: {exc}") from exc
        if int(metadata.get("id") or 0) != record_id:
            fail(f"Zenodo record identity drift: {record_id}")
        rows = remaining_probe.files(metadata)
        by_name = {str(row.get("key") or row.get("filename") or row.get("name")): row for row in rows}
        if set(by_name) != {record["name"]}:
            fail(f"Zenodo public file-set drift for {record_id}: {sorted(by_name)}")
        row = by_name[record["name"]]
        if row.get("size") is not None and int(row["size"]) != int(expected["bytes"]):
            fail(f"Zenodo metadata size drift: {record_id}")
        checksum = str(row.get("checksum") or "").removeprefix("md5:")
        if checksum and checksum != expected["md5"]:
            fail(f"Zenodo metadata MD5 drift: {record_id}")
        links = row.get("links") if isinstance(row.get("links"), Mapping) else {}
        url = links.get("content") or links.get("download") or links.get("self")
        if not isinstance(url, str):
            quoted = urllib.parse.quote(str(record["name"]), safe="")
            url = f"https://zenodo.org/api/records/{record_id}/files/{quoted}/content"
        payload = remaining_probe.get(url, "application/octet-stream, */*;q=0.1", remaining_probe.MAX_PUBLIC)
        observed = {
            "bytes": len(payload),
            "md5": md5_bytes(payload),
            "sha256": sha256_bytes(payload),
            "git_blob_sha1": git_blob_sha1(payload),
        }
        for key in ("bytes", "md5", "sha256"):
            if observed[key] != expected[key]:
                fail(f"exact public byte mismatch for {record_id}: {key}")
        if source is None:
            source = payload
        elif payload != source:
            fail(f"subject payload records are not byte-identical: {subject_id}")
        observations.append({
            "record_id": record_id,
            "doi": record["doi"],
            "public_name": record["name"],
            **observed,
        })
    if source is None:
        fail(f"no public source archive recovered: {subject_id}")
    return source, observations


def pointer_tokens(pointer: str) -> list[str]:
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        fail(f"invalid JSON pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def pointer_parent(value: Any, pointer: str) -> tuple[Any, str]:
    tokens = pointer_tokens(pointer)
    if not tokens:
        fail("root JSON pointer cannot be replaced in-place")
    current = value
    for token in tokens[:-1]:
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            fail(f"JSON pointer traverses scalar: {pointer}")
    return current, tokens[-1]


def pointer_get(value: Any, pointer: str) -> Any:
    current = value
    for token in pointer_tokens(pointer):
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def pointer_set(value: Any, pointer: str, replacement: Any) -> None:
    parent, token = pointer_parent(value, pointer)
    if isinstance(parent, list):
        parent[int(token)] = replacement
    else:
        parent[token] = replacement


def sibling_pointer(pointer: str, sibling: str) -> str:
    tokens = pointer_tokens(pointer)
    if not tokens:
        fail("root pointer has no sibling")
    tokens[-1] = sibling
    escaped = [token.replace("~", "~0").replace("/", "~1") for token in tokens]
    return "/" + "/".join(escaped)


def replacement_for(value: Any) -> Any:
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        return "OPEN_NOT_INDEPENDENTLY_REVALIDATED"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None
    if value is None:
        return None
    return "OPEN_NOT_INDEPENDENTLY_REVALIDATED"


def line_marker(path: pathlib.PurePosixPath) -> str:
    message = "QIK-VRT CORRECTION: OPEN_NOT_INDEPENDENTLY_REVALIDATED; historical wording is retained in the owner changeset only."
    suffix = path.suffix.lower()
    if suffix in MARKDOWN_EXTENSIONS:
        return f"> **{message}**"
    if suffix in STRUCTURED_COMMENT_EXTENSIONS or suffix in {".py", ".ps1", ".sh", ".rb"}:
        return f"# {message}"
    if suffix in {".xml", ".html", ".htm"}:
        return f"<!-- {message} -->"
    if suffix in {".bat", ".cmd"}:
        return f"REM {message}"
    if suffix in {".c", ".h", ".cc", ".cpp", ".hpp", ".js", ".ts", ".css", ".java"}:
        return f"/* {message} */"
    return message


def claim_source(claim: Mapping[str, Any]) -> tuple[str, str, Any]:
    refs = claim.get("source_refs")
    if not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], Mapping):
        fail(f"claim does not have exactly one source reference: {claim.get('claim_id')}")
    ref = refs[0]
    qualified = ref.get("qualified_path")
    locator = ref.get("locator")
    if not isinstance(qualified, str) or not isinstance(locator, Mapping):
        fail(f"invalid claim source reference: {claim.get('claim_id')}")
    return qualified, str(locator.get("type")), locator.get("value")


def apply_claim_corrections(root: dict[str, Any], claims: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    mapping = entry_map(root)
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for claim in claims:
        qualified, _kind, _locator = claim_source(claim)
        grouped[qualified].append(claim)
    changes: list[dict[str, Any]] = []
    for qualified in sorted(grouped):
        if qualified not in mapping:
            fail(f"claim source file is absent from exact archive: {qualified}")
        entry, _owner = mapping[qualified]
        if entry["is_directory"] or entry.get("nested") is not None:
            fail(f"claim source is not a leaf text file: {qualified}")
        text, encoding = decode_text(entry["data"])
        if text is None:
            fail(f"claim source is not decodable text: {qualified}")
        path = pathlib.PurePosixPath(qualified.rsplit("!/", 1)[1])
        rows = grouped[qualified]
        if path.suffix.lower() == ".json":
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise CorrectionError(f"invalid JSON correction source {qualified}: {exc}") from exc
            changed = False
            seen: set[str] = set()
            for claim in sorted(rows, key=lambda row: str(claim_source(row)[2])):
                _q, kind, locator = claim_source(claim)
                if kind != "json" or not isinstance(locator, str):
                    fail(f"mixed JSON/line correction source: {claim.get('claim_id')}")
                if claim.get("status") == "CONTRADICTED_BY_RECURSIVE_BYTE_AUDIT":
                    changes.append({
                        "claim_id": claim["claim_id"],
                        "qualified_path": qualified,
                        "locator": {"type": kind, "value": locator},
                        "repair": "REGENERATE_OR_EXCLUDE_HASH_BINDING",
                        "historical_statement": claim.get("statement"),
                    })
                    continue
                if locator in seen:
                    continue
                seen.add(locator)
                original = pointer_get(value, locator)
                replacement = replacement_for(original)
                pointer_set(value, locator, replacement)
                changed = True
                changes.append({
                    "claim_id": claim["claim_id"],
                    "qualified_path": qualified,
                    "locator": {"type": kind, "value": locator},
                    "repair": "NARROW_POSITIVE_STATUS_TO_OPEN_NOT_REVALIDATED",
                    "historical_value": original,
                    "candidate_value": replacement,
                    "historical_statement": claim.get("statement"),
                })
            if changed:
                entry["data"] = pretty(value).encode("utf-8")
            continue

        lines = text.splitlines()
        by_line: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
        for claim in rows:
            _q, kind, locator = claim_source(claim)
            if kind != "line" or not isinstance(locator, int):
                fail(f"mixed line/JSON correction source: {claim.get('claim_id')}")
            if claim.get("status") == "CONTRADICTED_BY_RECURSIVE_BYTE_AUDIT":
                changes.append({
                    "claim_id": claim["claim_id"],
                    "qualified_path": qualified,
                    "locator": {"type": kind, "value": locator},
                    "repair": "REGENERATE_OR_EXCLUDE_HASH_BINDING",
                    "historical_statement": claim.get("statement"),
                })
                continue
            by_line[locator].append(claim)
        for line_number in sorted(by_line, reverse=True):
            if line_number < 1 or line_number > len(lines):
                fail(f"line locator outside source: {qualified}:{line_number}")
            original = lines[line_number - 1]
            lines[line_number - 1] = line_marker(path)
            for claim in by_line[line_number]:
                changes.append({
                    "claim_id": claim["claim_id"],
                    "qualified_path": qualified,
                    "locator": {"type": "line", "value": line_number},
                    "repair": "REPLACE_UNBOUND_WORDING_WITH_EXPLICIT_OPEN_BOUNDARY",
                    "historical_line": original,
                    "candidate_line": lines[line_number - 1],
                    "historical_statement": claim.get("statement"),
                })
        if by_line:
            trailing = "\n" if text.endswith("\n") else ""
            entry["data"] = ("\n".join(lines) + trailing).encode("utf-8")
    return changes


def resolve_target(entries: Mapping[str, Any], source: str, raw_target: str) -> str | None:
    value = raw_target.replace("\\", "/").strip().lstrip("./")
    source_parent = pathlib.PurePosixPath(source).parent
    candidates = [
        (source_parent / pathlib.PurePosixPath(value)).as_posix(),
        pathlib.PurePosixPath(value).as_posix(),
    ]
    for candidate in dict.fromkeys(candidates):
        if candidate in entries and not entries[candidate]["is_directory"]:
            return candidate
    return None


def json_binding_edges(value: Any, source: str, entries: Mapping[str, Any], pointer: str = "") -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str) and SHA256.fullmatch(value["sha256"]):
            target = resolve_target(entries, source, value["path"])
            if target is None:
                fail(f"unresolved manifest target: {source} -> {value['path']}")
            edges.append({
                "kind": "json",
                "source": source,
                "target": target,
                "pointer": f"{pointer}/sha256" or "/sha256",
                "path_value": value["path"],
            })
        for key in sorted(value):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            edges.extend(json_binding_edges(value[key], source, entries, f"{pointer}/{escaped}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            edges.extend(json_binding_edges(item, source, entries, f"{pointer}/{index}"))
    return edges


def collect_binding_documents(node: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    entries = node["entries"]
    documents: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for path in sorted(entries):
        entry = entries[path]
        if entry["is_directory"] or entry.get("nested") is not None or remaining_probe.third(pathlib.PurePosixPath(path)):
            continue
        suffix = pathlib.PurePosixPath(path).suffix.lower()
        name = pathlib.PurePosixPath(path).name.lower()
        if suffix == ".json":
            text, _encoding = decode_text(entry["data"])
            if text is None:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            local_edges = json_binding_edges(value, path, entries)
            if local_edges:
                documents[path] = {"kind": "json", "value": value, "edges": local_edges}
                edges.extend(local_edges)
        elif name in CHECKSUM_NAMES or suffix == ".sha256":
            text, _encoding = decode_text(entry["data"])
            if text is None:
                continue
            lines = text.splitlines()
            local_edges = []
            for index, line in enumerate(lines):
                match = CHECKSUM.match(line)
                if not match:
                    continue
                target = resolve_target(entries, path, match.group(4))
                if target is None:
                    fail(f"unresolved checksum target: {path} -> {match.group(4)}")
                local_edges.append({
                    "kind": "checksum",
                    "source": path,
                    "target": target,
                    "line_index": index,
                    "path_value": match.group(4),
                    "spacing": match.group(3),
                })
            if local_edges:
                documents[path] = {"kind": "checksum", "lines": lines, "edges": local_edges}
                edges.extend(local_edges)
    return documents, edges


def strongly_connected_components(graph: Mapping[str, set[str]]) -> tuple[dict[str, int], dict[int, list[str]]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    components: dict[int, list[str]] = {}
    component_of: dict[str, int] = {}

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, set())):
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component_id = len(components)
            members: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component_of[member] = component_id
                members.append(member)
                if member == node:
                    break
            components[component_id] = sorted(members)

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return component_of, components


def regenerate_bindings(node: dict[str, Any]) -> dict[str, Any]:
    for path in sorted(node["entries"]):
        entry = node["entries"][path]
        nested = entry.get("nested")
        if isinstance(nested, dict):
            regenerate_bindings(nested)
            entry["data"] = render_archive(nested)

    documents, edges = collect_binding_documents(node)
    graph = {source: set() for source in documents}
    for edge in edges:
        if edge["target"] in documents:
            graph[edge["source"]].add(edge["target"])
    component_of, components = strongly_connected_components(graph)
    excluded: list[dict[str, Any]] = []
    active: list[dict[str, Any]] = []
    for edge in edges:
        source_component = component_of.get(edge["source"])
        target_component = component_of.get(edge["target"])
        same_cycle = (
            edge["source"] == edge["target"]
            or (
                source_component is not None
                and source_component == target_component
                and len(components[source_component]) > 1
            )
        )
        edge["excluded"] = same_cycle
        (excluded if same_cycle else active).append(edge)

    rendered: set[str] = set()
    visiting: set[str] = set()

    def render_document(path: str) -> None:
        if path in rendered:
            return
        if path in visiting:
            fail(f"unexcluded hash dependency cycle: {node['label']}!/{path}")
        visiting.add(path)
        document = documents[path]
        for edge in document["edges"]:
            if not edge["excluded"] and edge["target"] in documents:
                render_document(edge["target"])
        if document["kind"] == "json":
            value = document["value"]
            for edge in document["edges"]:
                pointer = edge["pointer"]
                if edge["excluded"]:
                    pointer_set(value, pointer, None)
                    pointer_set(value, sibling_pointer(pointer, "sha256_binding_status"), "SELF_OR_CYCLIC_BINDING_EXCLUDED")
                else:
                    target_data = node["entries"][edge["target"]]["data"]
                    pointer_set(value, pointer, sha256_bytes(target_data))
                    pointer_set(value, sibling_pointer(pointer, "sha256_binding_status"), "REGENERATED_FROM_EXACT_CANDIDATE_BYTES")
                    try:
                        pointer_set(value, sibling_pointer(pointer, "size"), len(target_data))
                    except (KeyError, IndexError, ValueError, TypeError):
                        pass
            node["entries"][path]["data"] = pretty(value).encode("utf-8")
        else:
            lines = list(document["lines"])
            for edge in document["edges"]:
                index = int(edge["line_index"])
                if edge["excluded"]:
                    lines[index] = f"# QIKVRT_CORRECTION SELF_OR_CYCLIC_HASH_BINDING_EXCLUDED {edge['path_value']}"
                else:
                    target_data = node["entries"][edge["target"]]["data"]
                    lines[index] = f"{sha256_bytes(target_data)}  {edge['path_value']}"
            node["entries"][path]["data"] = ("\n".join(lines) + "\n").encode("utf-8")
        visiting.remove(path)
        rendered.add(path)

    for path in sorted(documents):
        render_document(path)

    verify_documents, verify_edges = collect_binding_documents(node)
    mismatches = []
    for edge in verify_edges:
        target_data = node["entries"][edge["target"]]["data"]
        if edge["kind"] == "json":
            observed = pointer_get(verify_documents[edge["source"]]["value"], edge["pointer"])
        else:
            line = verify_documents[edge["source"]]["lines"][edge["line_index"]]
            match = CHECKSUM.match(line)
            observed = match.group(2).lower() if match else None
        expected = sha256_bytes(target_data)
        if observed != expected:
            mismatches.append({"source": edge["source"], "target": edge["target"], "observed": observed, "expected": expected})
    if mismatches:
        fail(f"active regenerated hash bindings mismatch in {node['label']}: {mismatches[:3]}")
    return {
        "archive_label": node["label"],
        "active_binding_count": len(verify_edges),
        "excluded_self_or_cyclic_binding_count": len(excluded),
        "active_binding_mismatch_count": 0,
        "excluded_bindings": [
            {"source": edge["source"], "target": edge["target"], "kind": edge["kind"]}
            for edge in excluded
        ],
    }


def add_correction_notice(
    root: dict[str, Any],
    subject_id: str,
    source_observations: list[dict[str, Any]],
    decision: Mapping[str, Any],
    changes: list[dict[str, Any]],
    binding_reports: list[dict[str, Any]],
) -> None:
    path = "QIKVRT_RETROSPECTIVE_CORRECTION_NOTICE_v1.json"
    if path in root["entries"]:
        fail(f"correction notice path collision: {subject_id}")
    notice = {
        "_license": LICENSE,
        "schema": "qikvrt_retrospective_correction_notice_v1",
        "subject_id": subject_id,
        "candidate_version": CANDIDATE_VERSION,
        "source_records": source_observations,
        "historical_public_bytes_mutated": False,
        "correction_basis": {
            "state": decision["state"],
            "correction_claim_count": decision["correction_claim_count"],
            "historical_internal_hash_mismatch_count": decision.get("internal_hash_mismatch_count", decision.get("manifest_hash_mismatch_count", 0)),
        },
        "candidate_repairs": {
            "claim_change_count": len(changes),
            "all_required_claim_ids_accounted_for": True,
            "active_internal_hash_binding_mismatches": 0,
            "self_or_cyclic_hash_bindings_explicitly_excluded": sum(row["excluded_self_or_cyclic_binding_count"] for row in binding_reports),
        },
        "owner_boundary": {
            "owner_decision_required": True,
            "accepted": False,
            "rejected": False,
            "zenodo_mutation_authorized": False,
        },
        "completion_claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "proof_corpus_published_on_zenodo": False,
            "zenodo_mutation_authorized": False,
        },
    }
    root["entries"][path] = {
        "path": path,
        "is_directory": False,
        "mode": 0o100644,
        "original_compress_type": zipfile.ZIP_DEFLATED,
        "data": pretty(notice).encode("utf-8"),
        "nested": None,
    }


def collect_binding_reports(node: Mapping[str, Any]) -> list[dict[str, Any]]:
    reports = []
    documents, edges = collect_binding_documents(node)
    reports.append({
        "archive_label": node["label"],
        "active_binding_count": len(edges),
        "active_binding_mismatch_count": 0,
    })
    for entry in node["entries"].values():
        nested = entry.get("nested")
        if isinstance(nested, Mapping):
            reports.extend(collect_binding_reports(nested))
    return reports


def correction_claims(subject_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    subject_root = BATCH / "subject-dispositions" / subject_id
    decision_value = read_json(subject_root / "CONTENT_CHANGE_DECISION.json")
    decision = decision_value["decision"]
    matrix = read_json(subject_root / "CLAIM_MATRIX.json")
    claims = [
        row for row in matrix["claims"]
        if row.get("publication_language_status") == "REQUIRES_VERSIONED_CORRECTION"
    ]
    expected_ids = list(decision["correction_claim_ids"])
    observed_ids = [row["claim_id"] for row in claims]
    if observed_ids != expected_ids:
        fail(f"correction claim ID drift: {subject_id}")
    if len(claims) != int(decision["correction_claim_count"]):
        fail(f"correction claim count drift: {subject_id}")
    return decision, claims


def materialize_subject(config: Mapping[str, Any]) -> dict[str, Any]:
    subject_id = str(config["subject_id"])
    decision, claims = correction_claims(subject_id)
    if decision.get("required") is not True or decision.get("state") != "VERSIONED_CORRECTION_REQUIRED":
        fail(f"subject is not authorized for correction: {subject_id}")
    source_archive, observations = fetch_subject_archive(config)
    expected = config["file"]
    if len(source_archive) != int(expected["bytes"]) or sha256_bytes(source_archive) != expected["sha256"]:
        fail(f"source archive identity mismatch after recovery: {subject_id}")

    root = parse_archive(source_archive, str(config["records"][0]["name"]))
    before = flattened_hashes(root)
    changes = apply_claim_corrections(root, claims)
    applied_ids = [row["claim_id"] for row in changes]
    if sorted(applied_ids) != sorted(decision["correction_claim_ids"]):
        missing = sorted(set(decision["correction_claim_ids"]) - set(applied_ids))
        extra = sorted(set(applied_ids) - set(decision["correction_claim_ids"]))
        fail(f"correction claim application drift {subject_id}: missing={missing[:5]} extra={extra[:5]}")

    binding_reports: list[dict[str, Any]] = []
    def regenerate_recursive(node: dict[str, Any]) -> None:
        for entry in node["entries"].values():
            nested = entry.get("nested")
            if isinstance(nested, dict):
                regenerate_recursive(nested)
                entry["data"] = render_archive(nested)
        report = regenerate_bindings(node)
        binding_reports.append(report)
    regenerate_recursive(root)
    add_correction_notice(root, subject_id, observations, decision, changes, binding_reports)
    candidate_archive = render_archive(root)

    candidate_root = parse_archive(candidate_archive, f"{subject_id}-corrected-{CANDIDATE_VERSION}.zip")
    verification_reports = []
    def verify_recursive(node: dict[str, Any]) -> None:
        for entry in node["entries"].values():
            nested = entry.get("nested")
            if isinstance(nested, dict):
                verify_recursive(nested)
        documents, edges = collect_binding_documents(node)
        mismatches = []
        for edge in edges:
            target_data = node["entries"][edge["target"]]["data"]
            expected_hash = sha256_bytes(target_data)
            if edge["kind"] == "json":
                observed_hash = pointer_get(documents[edge["source"]]["value"], edge["pointer"])
            else:
                line = documents[edge["source"]]["lines"][edge["line_index"]]
                match = CHECKSUM.match(line)
                observed_hash = match.group(2).lower() if match else None
            if observed_hash != expected_hash:
                mismatches.append({"source": edge["source"], "target": edge["target"]})
        if mismatches:
            fail(f"corrected candidate binding mismatch {node['label']}: {mismatches[:3]}")
        verification_reports.append({"archive_label": node["label"], "active_binding_count": len(edges), "mismatch_count": 0})
    verify_recursive(candidate_root)

    after = flattened_hashes(candidate_root)
    changed_paths = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            changed_paths.append({"qualified_path": path, "before": before.get(path), "after": after.get(path)})

    subject_output = OUTPUT / subject_id
    subject_output.mkdir(parents=True, exist_ok=True)
    candidate_name = f"{subject_id}__versioned-corrected-candidate-{CANDIDATE_VERSION}.zip"
    candidate_path = subject_output / candidate_name
    candidate_path.write_bytes(candidate_archive)
    changeset = {
        "_license": LICENSE,
        "schema": "qikvrt_versioned_corrected_candidate_changeset_v1",
        "subject_id": subject_id,
        "candidate_version": CANDIDATE_VERSION,
        "source_archive": {
            "bytes": len(source_archive),
            "sha256": sha256_bytes(source_archive),
            "git_blob_sha1": git_blob_sha1(source_archive),
        },
        "correction_claim_count": len(claims),
        "applied_claim_ids": sorted(applied_ids),
        "claim_repairs": sorted(changes, key=lambda row: row["claim_id"]),
        "changed_file_count": len(changed_paths),
        "changed_files": changed_paths,
        "binding_regeneration": binding_reports,
        "candidate_verification": verification_reports,
        "boundaries": {
            "historical_public_bytes_mutated": False,
            "owner_decision_required": True,
            "zenodo_mutation_authorized": False,
        },
    }
    changeset_path = subject_output / "CANDIDATE_CHANGESET.json"
    write_json(changeset_path, changeset)
    receipt = {
        "_license": LICENSE,
        "schema": "qikvrt_versioned_corrected_candidate_receipt_v1",
        "subject_id": subject_id,
        "candidate_version": CANDIDATE_VERSION,
        "observed_at": OBSERVED_AT,
        "state": "VERSIONED_CORRECTED_CANDIDATE_READY_FOR_OWNER_DECISION",
        "source_records": observations,
        "source_public_archive": {
            "bytes": len(source_archive),
            "md5": md5_bytes(source_archive),
            "sha256": sha256_bytes(source_archive),
            "git_blob_sha1": git_blob_sha1(source_archive),
        },
        "candidate_archive": binding(candidate_path),
        "changeset": binding(changeset_path),
        "verification": {
            "correction_claims_required": len(claims),
            "correction_claims_applied": len(applied_ids),
            "changed_file_count": len(changed_paths),
            "active_internal_hash_binding_mismatches": 0,
            "historical_public_bytes_rewritten": False,
        },
        "owner_decision": {
            "required": True,
            "accepted": False,
            "rejected": False,
        },
        "completion_claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "candidate_promoted": False,
            "proof_corpus_published_on_zenodo": False,
            "zenodo_mutation_authorized": False,
        },
        "next_deterministic_effect": "OWNER_ACCEPT_OR_REJECT_VERSIONED_CORRECTED_CANDIDATE",
    }
    receipt_path = subject_output / "CANDIDATE_RECEIPT.json"
    write_json(receipt_path, receipt)
    review_path = subject_output / "OWNER_REVIEW.md"
    review_path.write_text(
        "\n".join([
            f"# Owner review — {subject_id}",
            "",
            f"Candidate: `{candidate_path.relative_to(ROOT).as_posix()}`",
            f"Candidate SHA-256: `{receipt['candidate_archive']['sha256']}`",
            f"Correction claims applied: `{len(applied_ids)}`",
            f"Changed archive paths: `{len(changed_paths)}`",
            "Active internal hash mismatches: `0`",
            "",
            "Historical Zenodo bytes remain unchanged. No upload or mutation is authorized.",
            "",
            "Required owner disposition: `ACCEPT` or `REJECT` for this exact candidate SHA-256.",
            "",
        ]),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "subject_id": subject_id,
        "candidate_archive": receipt["candidate_archive"],
        "candidate_receipt": binding(receipt_path),
        "candidate_changeset": binding(changeset_path),
        "owner_review": binding(review_path),
        "correction_claim_count": len(applied_ids),
        "changed_file_count": len(changed_paths),
        "state": receipt["state"],
    }


def materialize() -> dict[str, Any]:
    work_unit = read_json(WORK_UNIT)
    if work_unit.get("state") not in {"READY", "RETURNED_TO_OWNER"}:
        fail(f"correction work unit is not executable: {work_unit.get('state')}")
    if work_unit.get("subject_ids") != EXPECTED_SUBJECT_IDS:
        fail("correction work-unit subject order drift")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    candidates = [materialize_subject(config) for config in SUBJECTS]
    owner_package = {
        "_license": {**LICENSE, "classification": "machine_readable_owner_return_package"},
        "schema": "qikvrt_versioned_corrected_candidates_owner_return_v1",
        "work_unit_id": work_unit["work_unit_id"],
        "observed_at": OBSERVED_AT,
        "state": "RETURNED_TO_OWNER_WAITING_EXPLICIT_DECISIONS",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "owner_decision_contract": {
            "required_per_subject": True,
            "allowed_values": ["ACCEPT", "REJECT"],
            "decision_must_bind_exact_candidate_sha256": True,
            "accepted_subject_ids": [],
            "rejected_subject_ids": [],
        },
        "boundaries": {
            "historical_zenodo_records_mutated": False,
            "candidate_promotion_authorized": False,
            "zenodo_mutation_authorized": False,
        },
        "completion_claims": {
            "all_six_candidates_created": True,
            "all_six_candidates_returned_to_owner": True,
            "all_six_candidates_owner_accepted": False,
            "repository_wide_pass": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "proof_corpus_published_on_zenodo": False,
            "zenodo_mutation_authorized": False,
        },
        "next_deterministic_effect": "OWNER_ACCEPT_OR_REJECT_VERSIONED_CORRECTED_CANDIDATES",
    }
    owner_package_path = OUTPUT / "OWNER_RETURN_PACKAGE.json"
    write_json(owner_package_path, owner_package)
    owner_markdown = [
        "# Versioned corrected candidates — owner return package",
        "",
        "Six exact candidates have been generated from byte-verified historical public archives.",
        "Historical Zenodo records were not modified and no Zenodo mutation is authorized.",
        "",
        "| Subject | Candidate SHA-256 | Claims corrected | Changed paths | Decision |",
        "|---|---|---:|---:|---|",
    ]
    for candidate in candidates:
        owner_markdown.append(
            f"| `{candidate['subject_id']}` | `{candidate['candidate_archive']['sha256']}` | "
            f"{candidate['correction_claim_count']} | {candidate['changed_file_count']} | `ACCEPT` / `REJECT` |"
        )
    owner_markdown.extend([
        "",
        "Each decision must bind the exact candidate SHA-256 shown above.",
        "No candidate is promoted, published, synchronized or deployed by this return package.",
        "",
    ])
    (OUTPUT / "OWNER_RETURN_PACKAGE.md").write_text("\n".join(owner_markdown), encoding="utf-8", newline="\n")

    updated = copy.deepcopy(work_unit)
    updated["state"] = "RETURNED_TO_OWNER"
    updated["returned_at"] = OBSERVED_AT
    updated["candidate_count"] = len(candidates)
    updated["owner_return_package"] = binding(owner_package_path)
    updated["candidate_receipts"] = [candidate["candidate_receipt"] for candidate in candidates]
    updated["next_deterministic_effect"] = "OWNER_ACCEPT_OR_REJECT_VERSIONED_CORRECTED_CANDIDATES"
    write_json(WORK_UNIT, updated)
    owner_work_unit = {
        "_license": {**LICENSE, "classification": "machine_readable_work_unit"},
        "schema": "qikvrt_work_unit_v1",
        "work_unit_id": "OWNER-DECISION-VERSIONED-CORRECTED-CANDIDATES-20260730",
        "operation": "OWNER_ACCEPT_OR_REJECT_VERSIONED_CORRECTED_CANDIDATES",
        "state": "WAITING_OWNER_DECISION",
        "owner_return_package": binding(owner_package_path),
        "requirements": [
            "bind every decision to the exact candidate SHA-256",
            "accept or reject each subject candidate explicitly",
            "do not mutate Zenodo before all accepted candidates are separately authorized",
        ],
        "completion_claims": {
            "all_owner_decisions_received": False,
            "candidate_promotion_authorized": False,
            "zenodo_mutation_authorized": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
        "next_deterministic_effect": "WAIT_FOR_OWNER_DECISIONS",
    }
    write_json(OWNER_WORK_UNIT, owner_work_unit)
    return owner_package


def check() -> dict[str, Any]:
    package_path = OUTPUT / "OWNER_RETURN_PACKAGE.json"
    if not package_path.is_file():
        fail("owner return package is missing")
    package = read_json(package_path)
    if package.get("state") != "RETURNED_TO_OWNER_WAITING_EXPLICIT_DECISIONS":
        fail("owner return package state drift")
    if package.get("candidate_count") != 6:
        fail("owner return candidate count drift")
    if [row.get("subject_id") for row in package.get("candidates", [])] != EXPECTED_SUBJECT_IDS:
        fail("owner return subject order drift")
    for candidate in package["candidates"]:
        subject_id = candidate["subject_id"]
        receipt_path = ROOT / candidate["candidate_receipt"]["path"]
        changeset_path = ROOT / candidate["candidate_changeset"]["path"]
        archive_path = ROOT / candidate["candidate_archive"]["path"]
        for path, expected in (
            (receipt_path, candidate["candidate_receipt"]),
            (changeset_path, candidate["candidate_changeset"]),
            (archive_path, candidate["candidate_archive"]),
        ):
            if not path.is_file() or binding(path) != expected:
                fail(f"candidate binding drift: {subject_id}:{path}")
        receipt = read_json(receipt_path)
        changeset = read_json(changeset_path)
        decision, _claims = correction_claims(subject_id)
        if receipt["state"] != "VERSIONED_CORRECTED_CANDIDATE_READY_FOR_OWNER_DECISION":
            fail(f"candidate state drift: {subject_id}")
        if receipt["verification"]["correction_claims_applied"] != decision["correction_claim_count"]:
            fail(f"candidate correction count drift: {subject_id}")
        if sorted(changeset["applied_claim_ids"]) != sorted(decision["correction_claim_ids"]):
            fail(f"candidate claim binding drift: {subject_id}")
        candidate_root = parse_archive(archive_path.read_bytes(), archive_path.name)
        notice = candidate_root["entries"].get("QIKVRT_RETROSPECTIVE_CORRECTION_NOTICE_v1.json")
        if not notice or notice["is_directory"]:
            fail(f"candidate correction notice missing: {subject_id}")
        notice_value = json.loads(notice["data"].decode("utf-8"))
        if notice_value["owner_boundary"]["zenodo_mutation_authorized"] is not False:
            fail(f"candidate mutation boundary inflated: {subject_id}")
    work_unit = read_json(WORK_UNIT)
    if work_unit.get("state") != "RETURNED_TO_OWNER":
        fail("correction work unit was not returned to owner")
    owner_work = read_json(OWNER_WORK_UNIT)
    if owner_work.get("state") != "WAITING_OWNER_DECISION":
        fail("owner decision work unit state drift")
    return {
        "candidate_count": 6,
        "subject_ids": EXPECTED_SUBJECT_IDS,
        "state": package["state"],
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = materialize() if args.materialize else check()
    print(pretty(result), end="")
    print("PASS=false")
    print("FINAL_PASS=false")
    print("EFFECT_ACK_DONE=false")
    print("ZENODO_MUTATION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CorrectionError as exc:
        print(f"BLOCK: {exc}")
        raise SystemExit(2)
