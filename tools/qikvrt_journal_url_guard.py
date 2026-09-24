#!/usr/bin/env python3
"""Guard stable QIK-VRT Journal URLs and immutable historical versions."""
from __future__ import annotations
import argparse, subprocess, sys

JOURNAL = "docs/journal/"
VERSIONS = "/versions/"

def out(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)

def tree_paths(ref: str) -> set[str]:
    raw = out("ls-tree", "-r", "--name-only", ref)
    return {p for p in raw.splitlines() if p.startswith(JOURNAL)}

def blob(ref: str, path: str) -> str | None:
    try:
        return out("rev-parse", f"{ref}:{path}").strip()
    except subprocess.CalledProcessError:
        return None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ns = ap.parse_args()

    base_paths = tree_paths(ns.base)
    head_paths = tree_paths(ns.head)
    errors: list[str] = []

    # Published journal URLs must not disappear.
    for path in sorted(base_paths):
        if path.endswith("/index.html") and path not in head_paths:
            errors.append(f"published URL removed: {path}")

    # Historical version bytes are immutable once they are on the base.
    for path in sorted(base_paths):
        if VERSIONS in path:
            if path not in head_paths:
                errors.append(f"archived version removed: {path}")
            elif blob(ns.base, path) != blob(ns.head, path):
                errors.append(f"archived version modified: {path}")

    if errors:
        print("\n".join("BLOCK: " + e for e in errors), file=sys.stderr)
        return 2
    print("PASS: journal permalinks preserved; archived versions unchanged")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
