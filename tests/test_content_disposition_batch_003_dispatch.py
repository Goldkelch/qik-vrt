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
P = ROOT / "tools/qikvrt_content_disposition_batch_003_dispatch.py"
S = importlib.util.spec_from_file_location("batch003_dispatch", P)
m = importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatch = load(m.DISPATCH)
        cls.package = load(m.WORK_PACKAGE)
        cls.work = load(m.WORK_UNIT)
        cls.queue = load(m.QUEUE)
        cls.corpus = load(m.CORPUS)
        cls.envelope = load(m.PROOF_ENVELOPE)
        cls.progress = load(m.AI_PROGRESS)
        cls.live_index = load(m.LIVE_INDEX)

    def test_positive(self):
        result = m.verify()
        self.assertEqual(
            result["state"],
            "BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT",
        )
        self.assertEqual(result["batch_id"], "CONTENT-DISPOSITION-BATCH-003")
        self.assertEqual(result["active_subject"], m.FIRST_SUBJECT_ID)
        self.assertEqual(result["active_subject_count"], 6)
        self.assertEqual(result["open_subject_count"], 7)
        self.assertFalse(result["claim_extraction_complete"])
        for key in (
            "zenodo_mutation_authorized",
            "pass",
            "final_pass",
            "effect_ack_done",
        ):
            self.assertIs(result[key], False)

    def test_exact_dispatch_partition_and_priority(self):
        m.validate_queue(self.queue)
        m.validate_corpus(self.corpus)
        m.validate_dispatch(self.dispatch, self.package, self.work)
        rows = self.dispatch["batch"]["subjects"]
        self.assertEqual(
            tuple(row["subject_id"] for row in rows),
            m.ACTIVE_SUBJECT_IDS,
        )
        self.assertEqual(rows[0]["queue_priority"], 2)
        self.assertTrue(
            all(row["queue_priority"] == 3 for row in rows[1:])
        )
        self.assertEqual(
            tuple(self.dispatch["outside_active_batch"]["subject_ids"]),
            m.OUTSIDE_SUBJECT_IDS,
        )

    def test_public_source_boundary_is_fail_closed(self):
        m.validate_public_sources(self.envelope)
        files = {
            row["name"]: row
            for row in self.package["public_source_files"]
        }
        receipt = files[m.PUBLIC_RECEIPT["name"]]
        index = files[m.PUBLIC_INDEX["name"]]
        self.assertEqual(
            receipt["state"],
            "LOCAL_EXACT_PUBLIC_BYTES_AVAILABLE",
        )
        self.assertEqual(
            index["state"],
            "PUBLIC_FREEZE_RECOVERY_REQUIRED_BEFORE_EXTRACTION",
        )
        self.assertTrue(
            receipt["current_repository_binding"]["repository_byte_match"]
        )
        self.assertFalse(
            index["current_repository_binding"][
                "current_repository_byte_match"
            ]
        )
        self.assertNotEqual(
            m.sha256_bytes(m.LIVE_INDEX.read_bytes()),
            m.PUBLIC_INDEX["sha256"],
        )

    def test_live_index_accepts_only_verified_append_only_growth(self):
        m.validate_live_index(self.live_index)
        rows = self.live_index["equality_receipts"]
        self.assertGreaterEqual(len(rows), m.LIVE_INDEX_BASE_ENTRY_COUNT)
        self.assertEqual(
            m.sha256_bytes(
                m.canonical_json_bytes(
                    rows[:m.LIVE_INDEX_BASE_ENTRY_COUNT]
                )
            ),
            m.LIVE_INDEX_BASE_PREFIX_SHA256,
        )

    def test_live_index_prefix_mutation_blocks(self):
        bad = copy.deepcopy(self.live_index)
        bad["equality_receipts"][0]["authority"]["main"] = "0" * 40
        with self.assertRaises(m.E):
            m.validate_live_index(bad)

    def test_live_index_prefix_reordering_blocks(self):
        bad = copy.deepcopy(self.live_index)
        bad["equality_receipts"][0], bad["equality_receipts"][1] = (
            bad["equality_receipts"][1],
            bad["equality_receipts"][0],
        )
        with self.assertRaises(m.E):
            m.validate_live_index(bad)

    def test_live_index_receipt_identity_tamper_blocks(self):
        bad = copy.deepcopy(self.live_index)
        bad["equality_receipts"][-1]["file_sha256"] = "0" * 64
        with self.assertRaises(m.E):
            m.validate_live_index(bad)

    def test_projection_has_active_owner_without_progress_inflation(self):
        progress, status = m.expected_projection()
        corpus = progress["scopes"][
            "qikvrt-zenodo-canonical-union-2026-07-28-v1"
        ]
        self.assertEqual(progress["state"], "WORKING")
        self.assertEqual(progress["percent"], 63)
        self.assertEqual(progress["next_action"], m.NEXT_EFFECT)
        self.assertIn(m.FIRST_SUBJECT_ID, progress["current_action"])
        self.assertEqual(corpus["counts"]["dispositioned_subjects"], 12)
        self.assertEqual(corpus["counts"]["open_subjects"], 7)
        self.assertEqual(corpus["active_batch"]["state"], "DISPATCHED")
        self.assertEqual(
            corpus["batch_003"]["state"],
            "DISPATCHED_FIRST_SUBJECT_ACTIVE",
        )
        self.assertFalse(corpus["batch_003"]["claim_extraction_complete"])
        self.assertIn("Batch 003 dispatched with six subjects", status)
        self.assertIn(m.NEXT_EFFECT, status)

    def test_ai_progress_and_human_status_are_byte_current(self):
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

    def test_wrong_first_subject_blocks(self):
        bad = copy.deepcopy(self.dispatch)
        bad["batch"]["subjects"][0]["subject_id"] = (
            "SUBJECT-172dd9bc2738fa43"
        )
        with self.assertRaises(m.E):
            m.validate_dispatch(bad, self.package, self.work)

    def test_false_completion_blocks(self):
        for key in (
            "all_content_claims_dispositioned",
            "batch_003_terminal",
            "first_subject_claim_extraction_complete",
            "pass",
            "final_pass",
            "effect_ack_done",
            "zenodo_mutation_authorized",
        ):
            bad = copy.deepcopy(self.dispatch)
            bad["completion_claims"][key] = True
            with self.assertRaises(m.E, msg=key):
                m.validate_dispatch(bad, self.package, self.work)

    def test_live_index_substitution_blocks(self):
        bad = copy.deepcopy(self.package)
        row = next(
            item
            for item in bad["public_source_files"]
            if item["name"] == m.PUBLIC_INDEX["name"]
        )
        row["current_repository_binding"][
            "current_repository_byte_match"
        ] = True
        with self.assertRaises(m.E):
            m.validate_work_package(bad)

    def test_projection_release_inflation_blocks(self):
        progress, _ = m.expected_projection()
        bad = copy.deepcopy(progress)
        bad["claims"]["PASS"] = True
        with self.assertRaises(m.E):
            m.validate_progress(bad)
        bad = copy.deepcopy(progress)
        bad["scopes"][
            "qikvrt-zenodo-canonical-union-2026-07-28-v1"
        ]["claims"]["PASS"] = True
        with self.assertRaises(m.E):
            m.validate_progress(bad)

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
            "BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
