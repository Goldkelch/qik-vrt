#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate a future mixed-license Zenodo contract without remote effects.

This module deliberately has no network, credential, Git-ref or Zenodo client
capability.  It validates a proposed v3 manifest, its exact upload bytes and a
complete file-to-right mapping, then emits a normalized validation receipt to
stdout.  The production publisher supports only v1/v2 and therefore rejects v3
before any authorization can be consumed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter
from collections.abc import Mapping
from typing import Any, NoReturn

MANIFEST_SCHEMA = "qikvrt_zenodo_publication_manifest_v3"
MAP_SCHEMA = "qikvrt_zenodo_file_license_map_v1"
RECEIPT_SCHEMA = "qikvrt_zenodo_mixed_license_contract_receipt_v1"
VALIDATE_STATE = "validate_only"
NO_EFFECT_CONFIRMATION = "NO_REMOTE_EFFECT"
TRANSPORT_STATE = "NATIVE_RDM_MULTI_RIGHTS_NOT_IMPLEMENTED"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PUBLICATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TOP_LEVEL_CFF_LICENSE = re.compile(
    r'''(?m)^(?:license|'license'|"license")\s*:\s*(?P<value>[^\r\n]*)$'''
)
NOTICE_CC_SPDX = re.compile(
    r"(?m)^SPDX-License-Identifier:\s*CC-BY-NC-ND-4\.0\s*$"
)

STANDARD_RIGHTS: dict[str, dict[str, str]] = {
    "cc-by-nc-nd-4.0": {
        "kind": "standard",
        "spdx_id": "CC-BY-NC-ND-4.0",
    },
    "apache-2.0": {
        "kind": "standard",
        "spdx_id": "Apache-2.0",
    },
}

POLYFORM_CUSTOM_RIGHT = {
    "id": "LicenseRef-PolyForm-Noncommercial-1.0.0",
    "kind": "custom",
    "title": "PolyForm Noncommercial License 1.0.0",
    "description": (
        "Noncommercial software use under PolyForm Noncommercial 1.0.0; "
        "commercial use requires a separate written agreement with the rights holder."
    ),
    "url": "https://polyformproject.org/licenses/noncommercial/1.0.0/",
}


class ContractError(ValueError):
    """A fail-closed local contract violation."""


def _fail(message: str) -> NoReturn:
    raise ContractError(message)


def _exact_keys(value: Any, expected: set[str], where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        _fail(f"{where} keys differ ({'; '.join(details)})")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"JSON contains duplicate object key: {key}")
        result[key] = value
    return result


def _load_json(path: pathlib.Path, maximum: int = 2_000_000) -> tuple[Any, bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")
    if not data or len(data) > maximum:
        _fail(f"{path} must contain between 1 and {maximum} bytes")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"{path} is not unique-key UTF-8 JSON: {exc}")
    return value, data


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _fail(f"value is not canonical JSON: {exc}")


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git identity


def _safe_file(root: pathlib.Path, raw: Any, where: str) -> pathlib.Path:
    if not isinstance(raw, str) or not raw:
        _fail(f"{where} must be a non-empty repository-relative path")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts or ".git" in {
        part.casefold() for part in relative.parts
    }:
        _fail(f"{where} is not a safe repository-relative path")
    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            _fail(f"{where} must not traverse a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        _fail(f"{where} cannot resolve to a repository file: {exc}")
    if not resolved.is_file():
        _fail(f"{where} must resolve to a regular file")
    return resolved


def _identity(path: pathlib.Path, raw_path: str, name: str) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        sha256 = hashlib.sha256()
        git_sha = hashlib.sha1()  # noqa: S324 - Git object identity
        git_sha.update(f"blob {size}\0".encode("ascii"))
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                sha256.update(chunk)
                git_sha.update(chunk)
    except OSError as exc:
        _fail(f"cannot hash {raw_path}: {exc}")
    return {
        "path": raw_path,
        "name": name,
        "bytes": size,
        "sha256": sha256.hexdigest(),
        "git_blob_sha": git_sha.hexdigest(),
    }


def _validate_identity(
    value: Any,
    root: pathlib.Path,
    where: str,
) -> dict[str, Any]:
    item = _exact_keys(
        value,
        {"path", "name", "bytes", "sha256", "git_blob_sha"},
        where,
    )
    raw_path = item["path"]
    name = item["name"]
    if not isinstance(raw_path, str) or not raw_path:
        _fail(f"{where}.path must be a non-empty string")
    if (
        not isinstance(name, str)
        or not name
        or pathlib.PurePosixPath(name).name != name
        or name in {".", ".."}
    ):
        _fail(f"{where}.name must be a safe upload basename")
    if pathlib.PurePosixPath(raw_path).name != name:
        _fail(f"{where}.name must equal the basename of {where}.path")
    if (
        not isinstance(item["bytes"], int)
        or isinstance(item["bytes"], bool)
        or item["bytes"] < 0
    ):
        _fail(f"{where}.bytes must be a non-negative integer")
    if not isinstance(item["sha256"], str) or HEX64.fullmatch(item["sha256"]) is None:
        _fail(f"{where}.sha256 must be lowercase SHA-256")
    if (
        not isinstance(item["git_blob_sha"], str)
        or HEX40.fullmatch(item["git_blob_sha"]) is None
    ):
        _fail(f"{where}.git_blob_sha must be lowercase Git SHA-1")
    path = _safe_file(root, raw_path, f"{where}.path")
    observed = _identity(path, raw_path, name)
    if dict(item) != observed:
        _fail(f"{where} differs from the observed file bytes")
    return observed


def _validate_artifact_license(value: Any, where: str) -> None:
    license_value = _exact_keys(
        value,
        {"classification", "copyright", "license", "license_text_ref", "rights_holder"},
        where,
    )
    if license_value["classification"] != "machine_readable_license_policy":
        _fail(f"{where}.classification differs")
    if license_value["license"] != "CC-BY-NC-ND-4.0":
        _fail(f"{where}.license must equal CC-BY-NC-ND-4.0")
    if license_value["license_text_ref"] != "LICENSES/CC-BY-NC-ND-4.0.txt":
        _fail(f"{where}.license_text_ref differs")
    for key in ("copyright", "rights_holder"):
        if not isinstance(license_value[key], str) or not license_value[key].strip():
            _fail(f"{where}.{key} must be non-empty")
    if license_value["rights_holder"] != "Ingolf Lohmann":
        _fail(f"{where}.rights_holder differs")


def _validate_standard_right(value: Mapping[str, Any], where: str) -> dict[str, Any]:
    right = _exact_keys(value, {"id", "kind", "spdx_id"}, where)
    expected = STANDARD_RIGHTS.get(right["id"])
    if expected is None or dict(right) != {"id": right["id"], **expected}:
        _fail(f"{where} is not an approved standard-right mapping")
    return dict(right)


def _validate_custom_right(
    value: Mapping[str, Any],
    files_by_path: Mapping[str, Mapping[str, Any]],
    root: pathlib.Path,
    where: str,
) -> dict[str, Any]:
    right = _exact_keys(
        value,
        {"id", "kind", "title", "description", "url", "license_text"},
        where,
    )
    expected = dict(POLYFORM_CUSTOM_RIGHT)
    for key, expected_value in expected.items():
        if right.get(key) != expected_value:
            _fail(f"{where}.{key} differs from the approved custom-right definition")
    license_text = _validate_identity(
        right["license_text"], root, f"{where}.license_text"
    )
    if files_by_path.get(license_text["path"]) != license_text:
        _fail(f"{where}.license_text must be an exact upload artifact")
    return {**expected, "license_text": license_text}


def _metadata_projection(rights: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    projected: list[dict[str, str]] = []
    for right in rights:
        if right["kind"] == "standard":
            projected.append({"id": str(right["id"])})
        else:
            projected.append(
                {
                    "title": str(right["title"]),
                    "description": str(right["description"]),
                    "link": str(right["url"]),
                }
            )
    return projected


def _validate_citation_cff(
    files: list[Mapping[str, Any]],
    root: pathlib.Path,
    rights: list[Mapping[str, Any]],
) -> None:
    for item in files:
        if item["name"].casefold() != "citation.cff":
            continue
        path = _safe_file(root, item["path"], "CITATION.cff")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _fail(f"CITATION.cff must be UTF-8 text: {exc}")
        matches = list(TOP_LEVEL_CFF_LICENSE.finditer(text))
        if len(matches) > 1:
            _fail("CITATION.cff contains duplicate top-level license fields")
        if len(rights) > 1 and matches:
            _fail(
                "mixed-license candidates must omit top-level CITATION.cff license; "
                "CFF license arrays express alternatives, not per-file assignments"
            )
        if not matches:
            continue
        right = rights[0]
        raw_value = matches[0].group("value").strip()
        if right["kind"] != "standard":
            _fail("CITATION.cff license must not represent a custom LicenseRef right")
        if not raw_value or raw_value.startswith(("[", "-", "{", "|", ">")):
            _fail("CITATION.cff license must be one unambiguous SPDX scalar")
        if raw_value[0:1] in {"'", '"'}:
            quote = raw_value[0]
            if len(raw_value) < 2 or raw_value[-1] != quote:
                _fail("CITATION.cff license scalar has unmatched quotes")
            raw_value = raw_value[1:-1]
        if "LicenseRef-" in raw_value:
            _fail("CITATION.cff license must not use LicenseRef-* values")
        if raw_value != right["spdx_id"]:
            _fail("CITATION.cff license differs from the sole assigned SPDX right")


def _validate_license_notice(path: pathlib.Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"LICENSE_NOTICE.md must be UTF-8 text: {exc}")
    if NOTICE_CC_SPDX.search(text) is None:
        _fail("LICENSE_NOTICE.md must declare SPDX CC-BY-NC-ND-4.0")


def validate_manifest(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    """Validate one v3 contract and return a normalized no-effect receipt."""
    root = root.resolve(strict=True)
    manifest_path = path if path.is_absolute() else root / path
    try:
        manifest_path = manifest_path.resolve(strict=True)
        manifest_relative = manifest_path.relative_to(root).as_posix()
    except (OSError, ValueError) as exc:
        _fail(f"manifest must be a file inside the repository root: {exc}")
    manifest, manifest_raw = _load_json(manifest_path)
    value = _exact_keys(
        manifest,
        {
            "_license",
            "schema",
            "state",
            "confirm",
            "transport",
            "repository",
            "publication_id",
            "metadata",
            "files",
            "license_notice",
            "file_license_map",
        },
        "manifest",
    )
    _validate_artifact_license(value["_license"], "manifest._license")
    if value["schema"] != MANIFEST_SCHEMA:
        _fail("unsupported mixed-license manifest schema")
    if value["state"] != VALIDATE_STATE:
        _fail("v3 mixed-license manifest state must equal validate_only")
    if value["confirm"] != NO_EFFECT_CONFIRMATION:
        _fail("v3 mixed-license manifest must explicitly forbid remote effects")
    if value["transport"] != TRANSPORT_STATE:
        _fail("v3 transport state differs from the fail-closed contract")
    if (
        not isinstance(value["repository"], str)
        or SAFE_REPOSITORY.fullmatch(value["repository"]) is None
    ):
        _fail("manifest.repository must be an owner/repository identity")
    publication_id = value["publication_id"]
    if (
        not isinstance(publication_id, str)
        or SAFE_PUBLICATION_ID.fullmatch(publication_id) is None
    ):
        _fail("manifest.publication_id is unsafe")

    raw_files = value["files"]
    if not isinstance(raw_files, list) or not 2 <= len(raw_files) <= 100:
        _fail("manifest.files must contain between 2 and 100 entries")
    files = [
        _validate_identity(item, root, f"manifest.files[{index}]")
        for index, item in enumerate(raw_files)
    ]
    if len({item["path"] for item in files}) != len(files):
        _fail("manifest.files contains duplicate repository paths")
    if len({item["name"] for item in files}) != len(files):
        _fail("manifest.files contains duplicate upload names")
    files_by_path = {item["path"]: item for item in files}

    notice = _validate_identity(value["license_notice"], root, "manifest.license_notice")
    if notice["name"] != "LICENSE_NOTICE.md" or files_by_path.get(notice["path"]) != notice:
        _fail("manifest.license_notice must be the exact LICENSE_NOTICE.md upload")
    _validate_license_notice(
        _safe_file(root, notice["path"], "manifest.license_notice.path")
    )
    map_identity = _validate_identity(
        value["file_license_map"], root, "manifest.file_license_map"
    )
    if (
        map_identity["name"] != "FILE_LICENSE_MAP.json"
        or files_by_path.get(map_identity["path"]) != map_identity
    ):
        _fail("manifest.file_license_map must be the exact FILE_LICENSE_MAP.json upload")

    license_map, _map_raw = _load_json(
        _safe_file(root, map_identity["path"], "manifest.file_license_map.path")
    )
    map_value = _exact_keys(
        license_map,
        {"_license", "schema", "publication_id", "rights", "assignments"},
        "file license map",
    )
    _validate_artifact_license(map_value["_license"], "file license map._license")
    if map_value["schema"] != MAP_SCHEMA:
        _fail("unsupported file-license-map schema")
    if map_value["publication_id"] != publication_id:
        _fail("file license map publication_id differs from the manifest")

    raw_rights = map_value["rights"]
    if not isinstance(raw_rights, list) or not raw_rights:
        _fail("file license map rights must be a non-empty array")
    rights: list[dict[str, Any]] = []
    for index, raw_right in enumerate(raw_rights):
        if not isinstance(raw_right, dict):
            _fail(f"file license map rights[{index}] must be an object")
        if raw_right.get("kind") == "standard":
            rights.append(_validate_standard_right(raw_right, f"file license map rights[{index}]"))
        elif raw_right.get("kind") == "custom":
            rights.append(
                _validate_custom_right(
                    raw_right,
                    files_by_path,
                    root,
                    f"file license map rights[{index}]",
                )
            )
        else:
            _fail(f"file license map rights[{index}].kind is unsupported")
    right_ids = [str(right["id"]) for right in rights]
    if len(set(right_ids)) != len(right_ids):
        _fail("file license map rights contains duplicate ids")

    raw_assignments = map_value["assignments"]
    if not isinstance(raw_assignments, list):
        _fail("file license map assignments must be an array")
    assignments: list[dict[str, str]] = []
    for index, raw_assignment in enumerate(raw_assignments):
        assignment = _exact_keys(
            raw_assignment,
            {"path", "name", "right_id"},
            f"file license map assignments[{index}]",
        )
        normalized = {key: assignment[key] for key in ("path", "name", "right_id")}
        if not all(isinstance(item, str) and item for item in normalized.values()):
            _fail(f"file license map assignments[{index}] fields must be non-empty strings")
        assignments.append(normalized)
    if len({item["path"] for item in assignments}) != len(assignments):
        _fail("file license map assignments contains duplicate repository paths")
    if len({item["name"] for item in assignments}) != len(assignments):
        _fail("file license map assignments contains duplicate upload names")
    expected_pairs = {(item["path"], item["name"]) for item in files}
    observed_pairs = {(item["path"], item["name"]) for item in assignments}
    if observed_pairs != expected_pairs or len(assignments) != len(files):
        _fail("file license map must assign every upload exactly once with no extras")
    undefined = sorted({item["right_id"] for item in assignments} - set(right_ids))
    if undefined:
        _fail("file license map uses undefined rights: " + ",".join(undefined))
    counts = Counter(item["right_id"] for item in assignments)
    unused = sorted(set(right_ids) - set(counts))
    if unused:
        _fail("file license map declares unused rights: " + ",".join(unused))
    assignments_by_path = {item["path"]: item for item in assignments}
    for control, label in (
        (notice, "LICENSE_NOTICE.md"),
        (map_identity, "FILE_LICENSE_MAP.json"),
    ):
        if assignments_by_path[control["path"]]["right_id"] != "cc-by-nc-nd-4.0":
            _fail(f"{label} must be assigned to cc-by-nc-nd-4.0")
    for right in rights:
        if right["kind"] != "custom":
            continue
        text_path = right["license_text"]["path"]
        assignment = next(item for item in assignments if item["path"] == text_path)
        if assignment["right_id"] != right["id"]:
            _fail("custom license text must be assigned to its own custom right")

    metadata = value["metadata"]
    if not isinstance(metadata, dict) or not metadata:
        _fail("manifest.metadata must be a non-empty JSON object")
    if "license" in metadata:
        _fail("v3 mixed-license metadata forbids the singular legacy license field")
    if "rights" not in metadata:
        _fail("v3 mixed-license metadata requires rights")
    projection = _metadata_projection(rights)
    if metadata["rights"] != projection:
        _fail("manifest.metadata.rights differs from the exact file-license-map projection")

    mixed_rights = len(counts) > 1
    _validate_citation_cff(files, root, rights)
    manifest_identity = {
        "path": manifest_relative,
        "bytes": len(manifest_raw),
        "sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "git_blob_sha": _git_blob_sha(manifest_raw),
    }
    return {
        "schema": RECEIPT_SCHEMA,
        "state": "VALIDATED_NO_REMOTE_EFFECT",
        "repository": value["repository"],
        "publication_id": publication_id,
        "manifest": manifest_identity,
        "metadata_sha256": hashlib.sha256(_canonical_json(metadata)).hexdigest(),
        "file_license_map": map_identity,
        "license_notice": notice,
        "upload_count": len(files),
        "rights": [
            {"id": right_id, "file_count": counts[right_id]}
            for right_id in right_ids
        ],
        "mixed_rights": mixed_rights,
        "transport": TRANSPORT_STATE,
        "effect_permitted": False,
        "legacy_publisher": "UNSUPPORTED_SCHEMA_FAIL_CLOSED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a mixed-license Zenodo v3 contract without remote effects"
    )
    parser.add_argument("--manifest", required=True, help="repository-relative v3 manifest")
    args = parser.parse_args(argv)
    root = pathlib.Path.cwd().resolve()
    try:
        receipt = validate_manifest(pathlib.Path(args.manifest), root)
    except ContractError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
