#!/usr/bin/env python3
"""Build the existing Firefox reference adapter with every locale and resource."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "browser/firefox/qikvrt-terminal"


def package(output: Path, source: Path = SOURCE) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    required = {"manifest.json", "options.js", manifest["options_ui"]["page"]}
    required.update(manifest["background"]["scripts"])
    for script in manifest["content_scripts"]:
        required.update(script.get("js", []))
        required.update(script.get("css", []))
    files = {p.relative_to(source).as_posix(): p for p in source.rglob("*") if p.is_file()}
    missing = required - files.keys()
    if missing:
        raise ValueError(f"Missing Firefox resources: {sorted(missing)}")
    catalogs = sorted(source.glob("_locales/*/messages.json"))
    default = source / "_locales" / manifest["default_locale"] / "messages.json"
    if default not in catalogs:
        raise ValueError("Missing default locale")
    default_keys = set(json.loads(default.read_text(encoding="utf-8")))
    for path in catalogs:
        messages = json.loads(path.read_text(encoding="utf-8"))
        if set(messages) != default_keys or any(not v.get("message") for v in messages.values()):
            raise ValueError(f"Incomplete locale: {path.parent.name}")
    output = output.resolve()
    if output.is_relative_to(source.resolve()):
        raise ValueError("Package output must be outside the extension source")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    return {"path": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "files": len(files), "locales": len(catalogs), "signed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
