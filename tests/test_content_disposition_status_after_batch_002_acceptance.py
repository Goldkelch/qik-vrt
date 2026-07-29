#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / (
    "tools/"
    "qikvrt_content_disposition_status_after_batch_002_acceptance_compat.py"
)
S = importlib.util.spec_from_file_location("post_acceptance_status", P)
m = importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.post = load(m.POST)
        cls.owner = load(m.OWNER_ACCEPTANCE)
        cls.equality = load(m.EQUALITY_RECEIPT)
        cls.progress = load(m.AI_PROGRESS)
        cls.queue = load(m.QUEUE)
        cls.index = load(m.INDEX)
        cls.union = load(m.UNION_RECEIPT)

    def test_positive(self):
        result = m.verify()
        self.assertEqual(
            result["state"],
            "BATCH_002_ACCEPTANCE_STATUS_PROJECTION_CURRENT",
        )
        self.assertEqual(
            result["next_deterministic_effect"],
            "EXECUTE_CONTENT_DISPOSITION_BATCH_003",
        )
        self.assertTrue(
            result["batch_002_correction_and_owner_return_complete"]
        )
        self.assertEqual(result["open_subject_count"], 7)
        for key in ("pass", "final_pass", "effect_ack_done"):
            self.assertIs(result[key], False)

    def test_exact_owner_acceptance_binding(self):
        m.validate_owner_acceptance(self.owner)
        evidence = self.post["evidence"]["owner_acceptance"]
        self.assertEqual(evidence["git_blob_sha1"], m.OWNER_BLOB)
        self.assertEqual(evidence["sha256"], m.OWNER_SHA256)
        self.assertEqual(evidence["comment_id"], 5122279522)
        self.assertEqual(evidence["decision"], "ACCEPT")

    def test_exact_promotion_and_reciprocal_binding(self):
        m.validate_equality_receipt(self.equality)
        evidence = self.post["evidence"]
        self.assertEqual(
            evidence["promotion_chain"]["authority"]["promotion_pull_request"],
            209,
        )
        self.assertEqual(
            evidence["promotion_chain"]["mirror"]["promotion_pull_request"],
            100,
        )
        self.assertEqual(
            evidence["reciprocal_receipt"]["authority"]["pull_request"],
            213,
        )
        self.assertEqual(
            evidence["reciprocal_receipt"]["mirror"]["pull_request"],
            101,
        )
        self.assertEqual(
            evidence["reciprocal_receipt"]["git_blob_sha1"],
            m.EQUALITY_BLOB,
        )

    def test_seven_open_subjects_are_preserved(self):
        open_ids = m.validate_historical_files(
            self.queue,
            self.index,
            self.union,
        )
        self.assertEqual(open_ids, m.OPEN_SUBJECT_IDS)
        corpus = self.post["preserved_corpus"]
        self.assertEqual(corpus["subject_count"], 19)
        self.assertEqual(corpus["dispositioned_subject_count"], 12)
        self.assertEqual(corpus["open_subject_count"], 7)
        self.assertEqual(tuple(corpus["open_subject_ids"]), m.OPEN_SUBJECT_IDS)
        self.assertEqual(corpus["active_batch"]["subject_count"], 6)
        self.assertEqual(corpus["queued_after_active"], 1)

    def test_batch_002_is_complete_only_for_the_bounded_correction_chain(self):
        corpus = self.progress["scopes"][
            "qikvrt-zenodo-canonical-union-2026-07-28-v1"
        ]
        batch = corpus["batch_002"]
        later = batch["post_acceptance"]
        self.assertEqual(batch["state"], "TERMINALLY_DISPOSITIONED")
        self.assertEqual(
            batch["evidence"],
            {
                "path": m.TERMINAL_RECEIPT_REL,
                "sha256": m.TERMINAL_RECEIPT_SHA256,
            },
        )
        self.assertEqual(later["state"], m.POST_ACCEPTANCE_STATE)
        for key in (
            "owner_return_complete",
            "owner_acceptance_recorded",
            "content_correction_review_complete",
            "authority_promotion_complete",
            "mirror_promotion_complete",
            "reciprocal_equality_receipt_complete",
        ):
            self.assertIs(later[key], True, key)
        self.assertEqual(
            corpus["next_action"],
            "EXECUTE_CONTENT_DISPOSITION_BATCH_003",
        )
        self.assertEqual(corpus["counts"]["open_subjects"], 7)
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            self.assertIs(corpus["claims"][key], False)

    def test_historical_terminal_projection_is_not_rewritten(self):
        _, _, _, receipt, _ = m.historical_projection()
        historical_next = (
            "CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002"
        )
        self.assertEqual(receipt["next_deterministic_effect"], historical_next)
        self.assertEqual(self.queue["next_deterministic_effect"], historical_next)
        self.assertEqual(self.index["next_deterministic_effect"], historical_next)
        self.assertEqual(self.union["next_deterministic_effect"], historical_next)
        self.assertTrue(
            self.post["base_projection"]["terminal_projection_preserved"]
        )

    def test_owner_tamper_blocks(self):
        bad = copy.deepcopy(self.owner)
        bad["decision"] = "REJECT"
        with self.assertRaises(m.E):
            m.validate_owner_acceptance(bad)

    def test_reciprocal_claim_inflation_blocks(self):
        bad = copy.deepcopy(self.equality)
        bad["claims"]["final_pass"] = True
        with self.assertRaises(m.E):
            m.validate_equality_receipt(bad)

    def test_open_subject_or_next_action_tamper_blocks(self):
        bad = copy.deepcopy(self.post)
        bad["preserved_corpus"]["open_subject_ids"] = list(m.OPEN_SUBJECT_IDS[:-1])
        with self.assertRaises(m.E):
            m.validate_post_projection(bad, m.OPEN_SUBJECT_IDS)
        bad = copy.deepcopy(self.post)
        bad["projection"]["next_deterministic_effect"] = (
            "BUILD_RETROSPECTIVE_PROOF_CORPUS"
        )
        with self.assertRaises(m.E):
            m.validate_post_projection(bad, m.OPEN_SUBJECT_IDS)

    def test_false_completion_and_zenodo_authorization_block(self):
        for key in (
            "all_content_claims_dispositioned",
            "proof_corpus_published_on_zenodo",
            "zenodo_mutation_authorized",
            "pass",
            "final_pass",
            "effect_ack_done",
        ):
            bad = copy.deepcopy(self.post)
            bad["completion_claims"][key] = True
            with self.assertRaises(m.E, msg=key):
                m.validate_post_projection(bad, m.OPEN_SUBJECT_IDS)

    def test_ai_progress_and_human_projection_are_byte_current(self):
        expected, status = m.expected_projection()
        self.assertEqual(self.progress, expected)
        self.assertEqual(
            m.AI_PROGRESS.read_text(encoding="utf-8"),
            m.pretty(expected),
        )
        self.assertEqual(
            m.AI_STATUS.read_text(encoding="utf-8"),
            status,
        )
        self.assertIn("✓ Owner decision `ACCEPT` recorded", status)
        self.assertIn("`EXECUTE_CONTENT_DISPOSITION_BATCH_003`", status)
        self.assertNotIn("- □ Required corrected Batch-002 candidate", status)

    def test_schema_compatibility_and_projection_owner(self):
        schema = load(ROOT / "schemas/human_machine_progress.schema.json")
        durable = schema["$defs"]["durableSnapshotV3"]
        self.assertEqual(
            durable["properties"]["schema"]["const"],
            self.progress["schema"],
        )
        self.assertTrue(set(durable["required"]).issubset(self.progress))
        self.assertEqual(
            self.progress["projection_owner"]["tool"],
            m.TOOL_REL,
        )
        effects = self.progress["repository_effects"]
        self.assertTrue(
            all(
                value == "NOT_EVALUATED"
                for key, value in effects.items()
                if key != "scope"
            )
        )

    def test_check_mode_works_without_historical_git_objects(self):
        with tempfile.TemporaryDirectory() as empty_objects:
            environment = dict(os.environ)
            environment.update({
                "GIT_OBJECT_DIRECTORY": empty_objects,
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_TERMINAL_PROMPT": "0",
            })
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(P),
                    "--check-status-projection",
                ],
                cwd=ROOT,
                env=environment,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            "BATCH_002_ACCEPTANCE_STATUS_PROJECTION_CURRENT",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
