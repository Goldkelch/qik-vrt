"""Generate deterministic SHA-256 rows for all distributable source files."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    ".gitignore", "CITATION.cff", "FORMALIZATION_BOUNDARY.md", "LICENSE-CODE",
    "README.md", "QIKVRTFormalization.lean", "lakefile.toml", "lean-toolchain",
    "manifest.json", "package-lock.json", "package.json", "pyproject.toml",
    "requirements-dev.txt",
}
ROOT_DIRS = {
    ".github", "QIKVRTFormalization", "claims", "python", "scripts", "source",
    "tests", "validator",
}


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if len(rel.parts) == 1:
        return rel.name in ROOT_FILES
    if rel.parts[0] not in ROOT_DIRS:
        return False
    return "__pycache__" not in rel.parts and not rel.name.endswith((".pyc", ".profraw"))


def main() -> int:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and included(p))
    rows = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} checksums written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

