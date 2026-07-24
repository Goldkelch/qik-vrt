#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Preserve CI test side effects, restore the committed tree, and verify integrity.

The repository integrity manifest describes persistent repository content. A CI test
run may legitimately create disposable audit output or modify explicitly mutable
runtime-state records. Those effects must not silently contaminate the subsequent
integrity check. This helper therefore:

1. rejects modifications to immutable tracked repository content;
2. records SHA-256 receipts for mutable tracked changes and untracked outputs;
3. restores mutable tracked files from Git;
4. removes preserved untracked outputs from the disposable CI checkout; and
5. leaves ignored runtime/cache paths untouched.

The helper is invoked only when ``CI=true`` by the Makefile. Local untracked work is
never removed by ``make test``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_integrity as integrity  # noqa: E402


class SanitationError(RuntimeError):
    """A test changed immutable content or produced an unsafe filesystem object."""


@dataclass(frozen=True)
class Receipt:
    path: str
    state: str
    classification: str
    bytes: int | None
    sha256: str | None


def _git(root: pathlib.Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise SanitationError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def _nul_paths(payload: bytes) -> list[str]:
    return sorted(
        {
            os.fsdecode(item)
            for item in payload.split(b"\0")
            if item
        }
    )


def _safe_relative(raw: str) -> pathlib.PurePosixPath:
    if not raw or "\\" in raw or any(ord(character) < 32 for character in raw):
        raise SanitationError(f"unsafe repository path: {raw!r}")
    value = pathlib.PurePosixPath(raw)
    if value.is_absolute() or ".." in value.parts or "." in value.parts:
        raise SanitationError(f"unsafe repository path: {raw!r}")
    return value


def _sha256_file(path: pathlib.Path) -> tuple[int, str]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise SanitationError(f"CI output is not a regular file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _copy_receipt(
    root: pathlib.Path,
    evidence_root: pathlib.Path,
    relative: str,
    state: str,
) -> Receipt:
    safe = _safe_relative(relative)
    source = root.joinpath(*safe.parts)
    classification, _immutable, _reason = integrity.classification(relative)
    if not source.exists():
        return Receipt(relative, state, classification, None, None)
    if source.is_symlink():
        raise SanitationError(f"CI output must not be a symlink: {relative}")
    size, digest = _sha256_file(source)
    target = evidence_root / "files" / state / pathlib.Path(*safe.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return Receipt(relative, state, classification, size, digest)


def _remove_empty_parents(path: pathlib.Path, root: pathlib.Path) -> None:
    parent = path.parent
    while parent != root and parent.is_relative_to(root):
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def _restore_mutable_tracked(root: pathlib.Path, paths: Iterable[str]) -> None:
    values = list(paths)
    if values:
        _git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", *values)


def sanitize(
    root: pathlib.Path = ROOT,
    evidence_root: pathlib.Path | None = None,
) -> dict[str, object]:
    root = root.resolve(strict=True)
    evidence_root = evidence_root or (
        root / ".qikvrt" / "evidence" / "ci-post-test"
    )
    evidence_root.mkdir(parents=True, exist_ok=True)

    tracked = set(
        _nul_paths(_git(root, "diff", "--name-only", "-z", "--"))
        + _nul_paths(_git(root, "diff", "--cached", "--name-only", "-z", "--"))
        + _nul_paths(_git(root, "ls-files", "-z", "--deleted", "--", "."))
    )
    untracked = _nul_paths(
        _git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", ".")
    )

    immutable_changes: list[str] = []
    mutable_changes: list[str] = []
    receipts: list[Receipt] = []

    for relative in sorted(tracked):
        _classification, immutable, _reason = integrity.classification(relative)
        if immutable:
            immutable_changes.append(relative)
        else:
            mutable_changes.append(relative)
            receipts.append(
                _copy_receipt(root, evidence_root, relative, "mutable-tracked")
            )

    if immutable_changes:
        report = {
            "schema": "qikvrt_ci_post_test_v1",
            "status": "BLOCK",
            "reason": "immutable_tracked_content_changed",
            "immutableTrackedChanges": immutable_changes,
        }
        (evidence_root / "REPORT.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise SanitationError(
            "tests changed immutable tracked repository content: "
            + ", ".join(immutable_changes)
        )

    for relative in untracked:
        receipts.append(_copy_receipt(root, evidence_root, relative, "untracked"))

    _restore_mutable_tracked(root, mutable_changes)

    for relative in untracked:
        safe = _safe_relative(relative)
        target = root.joinpath(*safe.parts)
        if target.is_symlink():
            raise SanitationError(f"CI output must not be a symlink: {relative}")
        if target.exists():
            target.unlink()
            _remove_empty_parents(target, root)

    remaining_tracked = sorted(
        set(
            _nul_paths(_git(root, "diff", "--name-only", "-z", "--"))
            + _nul_paths(_git(root, "diff", "--cached", "--name-only", "-z", "--"))
            + _nul_paths(_git(root, "ls-files", "-z", "--deleted", "--", "."))
        )
    )
    remaining_untracked = _nul_paths(
        _git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", ".")
    )
    if remaining_tracked or remaining_untracked:
        raise SanitationError(
            f"post-test checkout is not clean; tracked={remaining_tracked}, "
            f"untracked={remaining_untracked}"
        )

    report = {
        "schema": "qikvrt_ci_post_test_v1",
        "status": "PASS",
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "runId": os.environ.get("GITHUB_RUN_ID", ""),
        "recordedUnix": int(time.time()),
        "mutableTrackedRestored": mutable_changes,
        "untrackedOutputsPreservedAndRemoved": untracked,
        "receipts": [receipt.__dict__ for receipt in receipts],
    }
    (evidence_root / "REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--evidence-root", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        report = sanitize(args.root, args.evidence_root)
    except (OSError, SanitationError, ValueError) as exc:
        print(f"BLOCK CI_POST_TEST_SANITATION: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS CI post-test sanitation: "
        f"restored {len(report['mutableTrackedRestored'])} mutable tracked paths; "
        f"preserved and removed {len(report['untrackedOutputsPreservedAndRemoved'])} "
        "untracked outputs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
