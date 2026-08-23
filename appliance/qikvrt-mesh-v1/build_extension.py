#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Build a deterministic QIK-VRT Firefox appliance XPI.

The source extension remains untouched. The appliance adds one bounded startup
probe which exercises discovery, prepare, exact-bound commit and backend
reobservation against the loopback Effect-Ack service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ALLOWED_SUFFIXES = {".css", ".html", ".js", ".json"}
EXTENSION_ID = "qikvrt-ai-terminal@goldkelch.local"


def _json_no_duplicates(text: str) -> dict[str, object]:
    def hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=hook)
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build(source: Path, bootstrap: Path, output: Path, digest_file: Path | None) -> str:
    if not source.is_dir() or source.is_symlink():
        raise ValueError("extension source must be a real directory")
    manifest_path = source / "manifest.json"
    manifest = _json_no_duplicates(manifest_path.read_text(encoding="utf-8"))
    settings = manifest.get("browser_specific_settings")
    if not isinstance(settings, dict) or not isinstance(settings.get("gecko"), dict):
        raise ValueError("Firefox gecko identity is missing")
    if settings["gecko"].get("id") != EXTENSION_ID:
        raise ValueError("unexpected Firefox extension id")
    background = manifest.get("background")
    if not isinstance(background, dict) or not isinstance(background.get("scripts"), list):
        raise ValueError("Firefox background script list is missing")
    scripts = [str(item) for item in background["scripts"]]
    if "background.js" not in scripts:
        raise ValueError("canonical background.js is missing")
    if "appliance_bootstrap.js" not in scripts:
        scripts.append("appliance_bootstrap.js")
    background["scripts"] = scripts
    manifest["background"] = background
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    bootstrap_bytes = bootstrap.read_bytes()
    if not bootstrap_bytes or bootstrap.is_symlink():
        raise ValueError("bounded appliance bootstrap is unavailable")

    members: dict[str, bytes] = {
        "manifest.json": manifest_bytes,
        "appliance_bootstrap.js": bootstrap_bytes,
    }
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.is_symlink() or path.name == "manifest.json":
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        relative = path.relative_to(source).as_posix()
        if relative.startswith("../") or relative.startswith("/"):
            raise ValueError("extension path escaped source root")
        members[relative] = path.read_bytes()

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(members):
            archive.writestr(
                _zip_info(name),
                members[name],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    if digest_file is not None:
        digest_file.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--bootstrap", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha256-file", type=Path)
    args = parser.parse_args()
    print(build(args.source, args.bootstrap, args.output, args.sha256_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
