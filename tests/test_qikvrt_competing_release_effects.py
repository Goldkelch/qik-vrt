#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Isolation regressions for release-capable and retired workflows."""

from __future__ import annotations

import pathlib
import unittest

from tests.release_authority_hold_contract import (
    CARRIER_WORKFLOWS,
    assert_authority_hold_workflow,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


class CompetingReleaseEffectIsolationTests(unittest.TestCase):
    def test_repository_mesh_tag_is_marker_and_exact_subject_bound(self) -> None:
        text = workflow("qikvrt_repository_mesh_sync_tag.yml")
        trigger = text.split("permissions:", 1)[0]
        self.assertIn("automation/repository-mesh-sync-tag-20260724", trigger)
        self.assertNotIn("workflow_dispatch", trigger)
        self.assertIn("authorization commit must change only the marker", text)
        reciprocal_gate = text.index("for target, commit in zip(REPOSITORIES")
        tag_effect = text.index("api(repository, 'POST', '/git/tags'")
        self.assertLess(reciprocal_gate, tag_effect)

    def test_global_completion_has_no_repository_release_effect(self) -> None:
        text = workflow("qikvrt_global_completion.yml")
        trigger = text.split("permissions:", 1)[0]
        self.assertIn("agent/global-completion-v1", trigger)
        self.assertNotIn("refs/heads/main", text)
        for forbidden in (
            "gh pr merge",
            "gh release",
            "refs/tags/",
            "git push --tags",
            '"/git/tags"',
            '"/git/refs"',
        ):
            self.assertNotIn(forbidden, text)

    def test_all_candidate_controlled_zenodo_carriers_are_holds(self) -> None:
        for name in CARRIER_WORKFLOWS:
            with self.subTest(workflow=name):
                assert_authority_hold_workflow(self, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
