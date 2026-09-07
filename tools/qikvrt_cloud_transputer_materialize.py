#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Apply the cloud-transputer toolchain delta before integrity generation."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DELTA = ROOT / "deploy/universal-terminal/toolchain-delta.json"
LOCK = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
REGISTRY = ROOT / "runtime/toolchains/CACHE_REGISTRY.json"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    if delta.get("schema") != "qikvrt_cloud_transputer_toolchain_delta_v1":
        raise SystemExit("BLOCK: unexpected cloud transputer toolchain delta schema")

    raw = LOCK.read_text(encoding="utf-8")
    lines = raw.splitlines()
    rows: dict[str, list[str]] = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        rows.setdefault(fields[0], fields)

    changed = False
    for row in delta["lock_rows"]:
        current = rows.get(row[0])
        if current is not None and current != row:
            raise SystemExit(f"BLOCK: conflicting existing toolchain component {row[0]}")
        if current is None:
            lines.append("\t".join(row))
            rows[row[0]] = row
            changed = True
    if changed:
        LOCK.write_text("\n".join(lines) + "\n", encoding="utf-8")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    components = registry["components"]
    for name, value in delta["registry_components"].items():
        current = components.get(name)
        if current is not None and current != value:
            raise SystemExit(f"BLOCK: conflicting existing cache registry component {name}")
        if current is None:
            components[name] = value
            changed = True
    if changed:
        REGISTRY.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    run(sys.executable, "tools/qikvrt_tool_cache.py", "render")
    run(sys.executable, "tools/qikvrt_tool_cache.py", "verify")
    run(sys.executable, "tools/qikvrt_integrity.py", "generate")
    run(sys.executable, "tools/qikvrt_integrity.py", "verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
