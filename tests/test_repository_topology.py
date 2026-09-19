#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Repository-shape regression tests for the canonical thin-waist topology."""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "policy/REPOSITORY_TOPOLOGY.json").read_text(encoding="utf-8"))


def tracked_paths() -> list[str]:
    raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--", "."]
    )
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


class RepositoryTopologyTests(unittest.TestCase):
    def test_root_is_a_bounded_front_door(self) -> None:
        roots = {path.split("/", 1)[0] for path in tracked_paths()}
        self.assertLessEqual(len(roots), POLICY["root_entry_budget"])
        offenders = sorted(
            item for item in roots
            if re.fullmatch(r"QIKVRT_V45_[0-9]+_.*[.]cmd", item)
        )
        self.assertEqual(offenders, [])

    def test_canonical_surfaces_exist(self) -> None:
        for paths in POLICY["canonical_surfaces"].values():
            for relative in paths:
                self.assertTrue((ROOT / relative).exists(), relative)

    def test_v45_launchers_are_archived_not_duplicated(self) -> None:
        archived = sorted((ROOT / "legacy/v45").glob("QIKVRT_V45_*.cmd"))
        self.assertEqual(len(archived), 14)
        for path in archived:
            self.assertFalse((ROOT / path.name).exists())


if __name__ == "__main__":
    unittest.main()
