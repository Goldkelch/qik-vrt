#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate deterministic, complete cache coverage for the declared QIK-VRT runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
REGISTRY_PATH = ROOT / "runtime/toolchains/CACHE_REGISTRY.json"
COVERAGE_PATH = ROOT / "runtime/toolchains/CACHE_COVERAGE.json"

REQUIRED_COMPONENT_FIELDS = {
    "version",
    "profiles",
    "cache_class",
    "provider",
    "cache_locations",
    "authority_files",
    "verification",
    "trusted_save",
}
FORBIDDEN_CACHE_TOKENS = {
    "gh_token",
    "github_token",
    "credential",
    "cookie",
    ".ssh",
    "private_key",
    "auth login",
}


class ContractError(RuntimeError):
    """Raised when the runtime cache contract is incomplete or inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_lock() -> dict[str, dict[str, list[str]]]:
    if not LOCK_PATH.is_file():
        raise ContractError(f"missing toolchain lock: {LOCK_PATH.relative_to(ROOT)}")
    records: dict[str, dict[str, set[str]]] = {}
    for line_number, raw in enumerate(
        LOCK_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 7:
            raise ContractError(
                f"invalid lock row {line_number}: expected 7 tab-separated fields"
            )
        component, version, platform, _archive, _archive_hash, _license, purpose = fields
        if not component or not version or not platform or not purpose:
            raise ContractError(f"invalid empty field in lock row {line_number}")
        record = records.setdefault(
            component,
            {"versions": set(), "platforms": set(), "purposes": set()},
        )
        record["versions"].add(version)
        record["platforms"].add(platform)
        record["purposes"].add(purpose)

    normalized: dict[str, dict[str, list[str]]] = {}
    for component, record in records.items():
        versions = sorted(record["versions"])
        if len(versions) != 1:
            raise ContractError(f"{component}: multiple versions in lock: {versions}")
        normalized[component] = {
            "versions": versions,
            "platforms": sorted(record["platforms"]),
            "purposes": sorted(record["purposes"]),
        }
    if not normalized:
        raise ContractError("toolchain lock declares no components")
    return normalized


def read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise ContractError(f"missing cache registry: {REGISTRY_PATH.relative_to(ROOT)}")
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid cache registry JSON: {exc}") from exc
    if registry.get("schema") != "qikvrt-tool-cache-registry/1.0":
        raise ContractError("unsupported cache registry schema")
    if registry.get("lock_authority") != str(LOCK_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry lock_authority does not identify TOOLCHAIN.lock.tsv"
        )
    if registry.get("coverage_authority") != str(COVERAGE_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry coverage_authority does not identify CACHE_COVERAGE.json"
        )
    if not isinstance(registry.get("components"), dict):
        raise ContractError("cache registry components must be an object")
    return registry


def validate_registry(
    locked: dict[str, dict[str, list[str]]],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: dict[str, Any] = registry["components"]
    locked_names = set(locked)
    registry_names = set(entries)
    missing = sorted(locked_names - registry_names)
    extra = sorted(registry_names - locked_names)
    if missing:
        raise ContractError(
            f"cache registry misses locked components: {', '.join(missing)}"
        )
    if extra:
        raise ContractError(
            f"cache registry has undeclared components: {', '.join(extra)}"
        )

    allowed_classes = set(registry.get("cache_classes", []))
    if not allowed_classes:
        raise ContractError("cache registry defines no cache classes")

    coverage: list[dict[str, Any]] = []
    for component in sorted(locked):
        entry = entries[component]
        if not isinstance(entry, dict):
            raise ContractError(f"{component}: registry entry must be an object")
        absent_fields = sorted(REQUIRED_COMPONENT_FIELDS - set(entry))
        if absent_fields:
            raise ContractError(
                f"{component}: missing fields: {', '.join(absent_fields)}"
            )
        expected_version = locked[component]["versions"][0]
        if entry["version"] != expected_version:
            raise ContractError(
                f"{component}: registry version {entry['version']!r} "
                f"!= lock {expected_version!r}"
            )
        if entry["cache_class"] not in allowed_classes:
            raise ContractError(
                f"{component}: unsupported cache class {entry['cache_class']!r}"
            )
        for list_field in (
            "profiles",
            "cache_locations",
            "authority_files",
            "verification",
        ):
            value = entry[list_field]
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ContractError(
                    f"{component}: {list_field} must be a non-empty string list"
                )
        if not isinstance(entry["provider"], str) or not entry["provider"].strip():
            raise ContractError(f"{component}: provider must be non-empty")
        if not isinstance(entry["trusted_save"], bool):
            raise ContractError(f"{component}: trusted_save must be boolean")

        for authority in entry["authority_files"]:
            authority_path = ROOT / authority
            if not authority_path.is_file():
                raise ContractError(
                    f"{component}: missing authority file: {authority}"
                )

        joined_locations = "\n".join(entry["cache_locations"]).lower()
        forbidden = sorted(
            token for token in FORBIDDEN_CACHE_TOKENS if token in joined_locations
        )
        if forbidden:
            raise ContractError(
                f"{component}: credential-bearing cache location token(s): "
                f"{', '.join(forbidden)}"
            )

        coverage.append(
            {
                "cache_class": entry["cache_class"],
                "component": component,
                "provider": entry["provider"],
                "version": expected_version,
            }
        )
    return coverage


def build_coverage() -> dict[str, Any]:
    locked = read_lock()
    registry = read_registry()
    components = validate_registry(locked, registry)
    lock_bytes = LOCK_PATH.read_bytes()
    registry_bytes = REGISTRY_PATH.read_bytes()
    total = len(locked)
    covered = len(components)
    if covered != total:
        raise ContractError(f"cache coverage is incomplete: {covered}/{total}")
    return {
        "schema": "qikvrt-tool-cache-coverage/1.0",
        "status": "PASS",
        "coverage_basis": (
            "unique components in runtime/toolchains/TOOLCHAIN.lock.tsv"
        ),
        "coverage_percent": 100,
        "declared_components": total,
        "covered_components": covered,
        "lock_sha256": sha256_bytes(lock_bytes),
        "registry_sha256": sha256_bytes(registry_bytes),
        "components": components,
        "rules": {
            "all_declared_tools_have_cache_strategy": True,
            "new_tool_must_extend_lock_and_registry_before_use": True,
            "credentials_forbidden_in_cache": True,
            "cold_and_warm_cache_semantics_equal": True,
            "cache_never_replaces_required_checks": True,
        },
    }


def render() -> None:
    document = build_coverage()
    COVERAGE_PATH.write_text(canonical_json(document), encoding="utf-8")
    print(
        f"PASS: rendered {document['covered_components']}/"
        f"{document['declared_components']} tool-cache coverage"
    )


def verify() -> None:
    expected = canonical_json(build_coverage())
    if not COVERAGE_PATH.is_file():
        raise ContractError(
            f"missing coverage authority: {COVERAGE_PATH.relative_to(ROOT)}"
        )
    actual = COVERAGE_PATH.read_text(encoding="utf-8")
    if actual != expected:
        raise ContractError(
            "CACHE_COVERAGE.json is stale; run "
            "'python3 tools/qikvrt_tool_cache.py render'"
        )
    document = json.loads(actual)
    print(
        f"PASS: {document['covered_components']}/"
        f"{document['declared_components']} declared tools have cache strategies "
        f"({document['coverage_percent']}%)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "verify"))
    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            render()
        else:
            verify()
    except ContractError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
