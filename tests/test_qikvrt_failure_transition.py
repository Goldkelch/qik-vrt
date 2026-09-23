# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.qikvrt_failure_transition import resolve_failure

ROOT = Path(__file__).resolve().parents[1]


class FailureTransitionTests(unittest.TestCase):
    def test_smallest_internal_capability_wins(self):
        result = resolve_failure(
            cause="READ_PATH_UNAVAILABLE",
            capabilities=[
                {
                    "id": "REPEAT_SAME_READ",
                    "transition": "RETRY",
                    "rank": 20,
                    "admissible": False,
                },
                {
                    "id": "FETCH_GIT_BLOB",
                    "transition": "USE_GIT_BLOB_READBACK",
                    "rank": 10,
                    "admissible": True,
                },
                {
                    "id": "DOWNLOAD_ARCHIVE",
                    "transition": "USE_ARCHIVE",
                    "rank": 30,
                    "admissible": True,
                },
            ],
        )
        self.assertEqual(result["state"], "INTERNAL_TRANSITION_REQUIRED")
        self.assertEqual(result["selected_capability"]["id"], "FETCH_GIT_BLOB")
        self.assertFalse(result["identical_retry_permitted"])
        self.assertFalse(result["deadlock"])

    def test_external_transition_suppresses_identical_retry(self):
        result = resolve_failure(
            cause="ADMIN_AUTHORITY_UNAVAILABLE",
            external_effect={
                "credential": "QIKVRT_RULESET_ADMIN_TOKEN",
                "minimum_permission": "Administration: write",
            },
            wake_condition="QIKVRT_RULESET_ADMIN_TOKEN_AVAILABLE_AND_AUTHORIZED",
        )
        self.assertEqual(result["state"], "EXTERNAL_TRANSITION_REQUIRED")
        self.assertTrue(result["deadlock"])
        self.assertFalse(result["retry_permitted"])
        self.assertFalse(result["identical_retry_permitted"])

    def test_no_transition_fails_closed(self):
        result = resolve_failure(cause="UNCLASSIFIED_FIRST_BLOCKER")
        self.assertEqual(result["state"], "FAIL_CLOSED")
        self.assertIsNone(result["next_action"])

    def test_bootstrap_binds_rule(self):
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        for path in (
            "docs/CAUSE_CAPABILITY_EFFECT_READBACK.md",
            "policy/CAUSE_CAPABILITY_EFFECT_READBACK_V1.json",
            "state/transition/CAUSE_CAPABILITY_EFFECT_READBACK_ADOPTION_V1.json",
        ):
            self.assertIn(path, context["required_read_order"])
        ai = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn("qikvrt-cause-capability-effect-readback:v1", ai)


if __name__ == "__main__":
    unittest.main()
