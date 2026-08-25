# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_terminal_assignment_backpressure",
    ROOT / "tools/qikvrt_terminal_assignment_backpressure.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TerminalAssignmentBackpressureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = "a" * 40
        self.policy = {
            "schema": "qikvrt_terminal_assignment_backpressure_v1",
            "repository": "Goldkelch/qik-vrt",
            "carrier_pr": 885,
            "states": list(MODULE.STATES),
            "anchor_assignment": {"display_id": "A56", "comment_id": 5415958931},
        }
        self.carrier = {
            "number": 885,
            "state": "open",
            "draft": False,
            "opt_in": False,
            "base_sha": self.base,
            "base_tree": "b" * 40,
            "head_sha": "c" * 40,
            "head_tree": "d" * 40,
        }
        self.comments = [
            {
                "id": 5415804598,
                "body": "<!-- qikvrt-terminal-repair-assignment:A51 -->\nfirst\n",
            },
            {
                "id": 5415832471,
                "body": "<!-- qikvrt-terminal-repair-assignment:A51 -->\nsecond\n",
            },
            {
                "id": 5415958931,
                "body": "<!-- qikvrt-terminal-repair-assignment:A56 -->\nbackpressure\n",
            },
        ]

    def observe(self, pulls=()):
        return MODULE.observe(
            policy=self.policy,
            comments=self.comments,
            pulls=pulls,
            carrier=self.carrier,
            source_run_id=123,
            source_run_attempt=1,
        )

    def test_canonical_identity_uses_comment_and_subject_digest(self) -> None:
        first = self.observe()["assignment"]
        second = self.observe()["assignment"]
        self.assertEqual(first["identity"], second["identity"])
        self.assertEqual(len(first["identity"]), 64)
        self.assertEqual(first["comment_id"], 5415958931)

    def test_legacy_duplicate_display_id_is_explicit(self) -> None:
        value = self.observe()
        self.assertEqual(len(value["legacy_display_id_collisions"]), 1)
        self.assertEqual(value["legacy_display_id_collisions"][0]["display_id"], "A51")

    def test_ineligible_carrier_requires_trusted_bootstrap(self) -> None:
        value = self.observe()
        self.assertEqual(value["state"], "AUTHORITY_REQUIRED")
        self.assertEqual(value["first_blocker"], "TRUSTED_MAIN_BOOTSTRAP_REQUIRED")
        self.assertTrue(value["next_assignment_allowed"])

    def test_exact_opt_in_draft_candidate_materializes_assignment(self) -> None:
        pull = {
            "number": 889,
            "state": "open",
            "draft": True,
            "body": (
                "<!-- qikvrt-terminal-repair-candidate:assignment=A56 "
                "comment=5415958931 -->\n"
                "<!-- qikvrt-autonomous-self-heal:enabled -->\n"
            ),
            "base": {"ref": "main", "sha": self.base},
            "head": {
                "ref": "automation/self-heal-a56",
                "sha": "e" * 40,
                "repo": {"full_name": "Goldkelch/qik-vrt"},
            },
        }
        value = self.observe([pull])
        self.assertEqual(value["state"], "MATERIALIZED")
        self.assertIsNone(value["first_blocker"])
        self.assertEqual(value["candidates"][0]["pull_request"], 889)

    def test_non_draft_or_wrong_base_candidate_is_rejected(self) -> None:
        pull = {
            "number": 889,
            "state": "open",
            "draft": False,
            "body": (
                "<!-- qikvrt-terminal-repair-candidate:assignment=A56 "
                "comment=5415958931 -->\n"
                "<!-- qikvrt-autonomous-self-heal:enabled -->\n"
            ),
            "base": {"ref": "main", "sha": "f" * 40},
            "head": {
                "ref": "automation/self-heal-a56",
                "sha": "e" * 40,
                "repo": {"full_name": "Goldkelch/qik-vrt"},
            },
        }
        self.assertEqual(self.observe([pull])["state"], "AUTHORITY_REQUIRED")

    def test_multiple_bound_candidates_fail_closed(self) -> None:
        def pull(number: int, sha: str):
            return {
                "number": number,
                "state": "open",
                "draft": True,
                "body": (
                    "<!-- qikvrt-terminal-repair-candidate:assignment=A56 "
                    "comment=5415958931 -->\n"
                    "<!-- qikvrt-autonomous-self-heal:enabled -->\n"
                ),
                "base": {"ref": "main", "sha": self.base},
                "head": {
                    "ref": f"automation/self-heal-a56-{number}",
                    "sha": sha,
                    "repo": {"full_name": "Goldkelch/qik-vrt"},
                },
            }

        value = self.observe([pull(889, "e" * 40), pull(890, "f" * 40)])
        self.assertEqual(value["state"], "AUTHORITY_REQUIRED")
        self.assertEqual(value["first_blocker"], "MULTIPLE_BOUND_REPAIR_CANDIDATES")

    def test_noop_is_reconciled_with_assignment_state(self) -> None:
        observation = self.observe()
        value = MODULE.reconcile({"state": "NOOP"}, observation)
        self.assertEqual(value["state"], "AUTHORITY_REQUIRED")
        self.assertEqual(value["failure_class"], "TRUSTED_MAIN_BOOTSTRAP_REQUIRED")


if __name__ == "__main__":
    unittest.main()
