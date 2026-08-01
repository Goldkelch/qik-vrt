#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "tools/qikvrt_content_disposition_batch_002_terminal.py"
CURRENT_P = ROOT / "tools/qikvrt_content_disposition_batch_003_dispatch.py"
BASE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
OUT = BASE / "content-disposition-batch-002/terminal-disposition"
HANDOFF_RECEIPT = ROOT / "receipts/anticipation/0003-post-promotion-current-main-handoff.json"
HANDOFF_WORK_UNIT = "CURRENT_MAIN_CHILD_PORT_OF_AUTHORITY_PR289"
HANDOFF_NEXT_EFFECT = "MATERIALIZE_AND_VERIFY_CURRENT_MAIN_CHILD_PORT_OF_AUTHORITY_PR289_ON_EXACT_HEAD"

spec = importlib.util.spec_from_file_location("b2", P)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)
current_spec = importlib.util.spec_from_file_location("current_status", CURRENT_P)
current = importlib.util.module_from_spec(current_spec)
assert current_spec.loader is not None
current_spec.loader.exec_module(current)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = load(OUT / "CONTENT_DISPOSITION_BATCH_002_RECEIPT.json")
        cls.queue = load(BASE / "CONTENT_CLAIM_DISPOSITION_QUEUE.json")
        cls.index = load(BASE / "CONTENT_CLAIM_DISPOSITION_INDEX.json")
        cls.union_receipt = load(BASE / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json")
        cls.progress = load(ROOT / "AI_PROGRESS.json")

    @staticmethod
    def current_projection_contract():
        stage = current.projection_stage()
        if stage == current.STAGE_FINAL_CORPUS:
            advanced = current._advanced_module(stage)
            if HANDOFF_RECEIPT.is_file():
                return {
                    "next_effect": HANDOFF_NEXT_EFFECT,
                    "tool": advanced.TOOL_REL,
                    "open_subjects": 0,
                    "batch_state": "TERMINALLY_DISPOSITIONED",
                    "bar": None,
                    "status_marker": HANDOFF_WORK_UNIT,
                }
            return {
                "next_effect": advanced.NEXT_EFFECT,
                "tool": advanced.TOOL_REL,
                "open_subjects": 0,
                "batch_state": "TERMINALLY_DISPOSITIONED",
                "bar": "[███████████████████] 100%",
                "status_marker": "All 19 canonical claim subjects terminally classified",
            }
        if stage == current.STAGE_SECOND_SUBJECT:
            advanced = current._advanced_module(stage)
            return {
                "next_effect": advanced.NEXT_EFFECT,
                "tool": advanced.TOOL_REL,
                "open_subjects": 5,
                "batch_state": "SECOND_SUBJECT_TERMINAL_CORRECTION_REQUIRED_NEXT_SUBJECT_READY",
                "bar": "[██████████████░░░░░] 74%",
                "status_marker": "5715/5715 assertion nodes classified",
            }
        if stage == current.STAGE_FIRST_SUBJECT:
            advanced = current._advanced_module(stage)
            return {
                "next_effect": advanced.NEXT_EFFECT,
                "tool": advanced.TOOL_REL,
                "open_subjects": 6,
                "batch_state": "FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY",
                "bar": "[█████████████░░░░░░] 68%",
                "status_marker": "39/39 claims terminally classified",
            }
        return {
            "next_effect": current.NEXT_EFFECT,
            "tool": current.TOOL_REL,
            "open_subjects": 7,
            "batch_state": "DISPATCHED_FIRST_SUBJECT_ACTIVE",
            "bar": "[████████████░░░░░░░] 63%",
            "status_marker": "Batch 003 dispatched with six subjects",
        }

    def test_epistemic_classification_boundaries(self):
        self.assertEqual(m.classify("Diese Frage bleibt offen."), "OPEN")
        self.assertEqual(m.classify("Jede Veröffentlichung muss geprüft werden."), "NORMATIVE")
        self.assertEqual(m.classify("Dies ist eine ontologische Interpretation."), "INTERPRETATIVE")
        self.assertEqual(m.classify("Der SHA-256-Redownload wurde verifiziert."), "EMPIRICALLY_EVIDENCED")
        self.assertEqual(m.classify("Das Dokument enthält sieben Dateien."), "SOURCE_BOUND")
        self.assertNotEqual(m.classify("Satz", "KERNEL_PROVED", "", []), "FORMAL_PROVED")
        self.assertEqual(m.classify("Satz", "KERNEL_PROVED", "", ["Theorem.x"]), "FORMAL_PROVED")
        self.assertTrue(m.OVERCLAIM.search("Damit ist alles vollständig bewiesen."))

    def test_terminal_receipt_remains_truth_bounded(self):
        receipt = self.receipt
        self.assertEqual(receipt["batch_id"], m.BATCH_ID)
        self.assertEqual(receipt["state"], "TERMINALLY_DISPOSITIONED")
        self.assertEqual(receipt["subject_count"], 6)
        self.assertEqual(receipt["claim_count"], 1489)
        self.assertEqual(receipt["content_change_required_count"], 1)
        self.assertEqual(receipt["observed_at"], m.OBSERVED_AT)
        self.assertEqual([row["subject_id"] for row in receipt["subjects"]], m.SUBJECT_IDS)
        for key in ("all_content_claims_dispositioned", "proof_corpus_published_on_zenodo", "pass", "final_pass", "effect_ack_done"):
            self.assertIs(receipt["completion_claims"][key], False, key)
        m.validate_terminal_receipt(receipt, self.index)

    def test_terminal_receipt_tamper_is_rejected(self):
        bad = copy.deepcopy(self.receipt)
        bad["validation"]["all_public_files_byte_reverified"] = False
        with self.assertRaises(m.E):
            m.validate_terminal_receipt(bad, self.index)
        bad = copy.deepcopy(self.receipt)
        bad["subjects"][0]["claim_matrix_sha256"] = "0" * 64
        with self.assertRaises(m.E):
            m.validate_terminal_receipt(bad, self.index)

    def test_historical_queue_index_and_union_are_one_projection(self):
        next_effect = "CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002"
        self.assertEqual(self.receipt["next_deterministic_effect"], next_effect)
        self.assertEqual(self.queue["next_deterministic_effect"], next_effect)
        self.assertEqual(self.index["next_deterministic_effect"], next_effect)
        self.assertEqual(self.union_receipt["next_deterministic_effect"], next_effect)
        self.assertEqual(self.queue["state"], "BATCH_002_CORRECTION_REQUIRED_BATCH_003_READY")

    def test_batch_counts_and_partition_remain_exact(self):
        complete = [row for row in self.index["claim_subjects"] if row["claim_disposition_complete"]]
        pending = [row for row in self.index["claim_subjects"] if not row["claim_disposition_complete"]]
        self.assertEqual((len(complete), len(pending)), (12, 7))
        self.assertEqual(sum(row["claim_count"] for row in complete), 1747)
        active = self.queue["active_batch"]
        self.assertEqual(
            (active["batch_id"], active["state"], active["subject_count"], self.queue["remaining_subject_count"]),
            ("CONTENT-DISPOSITION-BATCH-003", "READY", 6, 1),
        )

    def test_historical_projection_is_idempotent(self):
        args = (
            copy.deepcopy(self.queue),
            copy.deepcopy(self.index),
            copy.deepcopy(self.union_receipt),
            copy.deepcopy(self.receipt["subjects"]),
            self.receipt["claim_count"],
            self.receipt["content_change_required_count"],
        )
        first = m.project_status(*args)
        second = m.project_status(
            copy.deepcopy(first[0]),
            copy.deepcopy(first[1]),
            copy.deepcopy(first[2]),
            copy.deepcopy(self.receipt["subjects"]),
            self.receipt["claim_count"],
            self.receipt["content_change_required_count"],
        )
        self.assertEqual(first, second)
        self.assertEqual(first, (self.queue, self.index, self.union_receipt))

    def test_later_evidence_is_not_injected_into_historical_projection(self):
        future = copy.deepcopy(self.union_receipt)
        future["completion_claims"]["mirror_synchronized"] = True
        with self.assertRaises(m.E):
            m.project_status(
                copy.deepcopy(self.queue),
                copy.deepcopy(self.index),
                future,
                copy.deepcopy(self.receipt["subjects"]),
                self.receipt["claim_count"],
                self.receipt["content_change_required_count"],
            )

    def test_final_corpus_precedence_is_explicit(self):
        if current.FINAL_CORPUS_RECEIPT.is_file():
            self.assertEqual(current.projection_stage(), current.STAGE_FINAL_CORPUS)
            self.assertTrue(current._advanced_module().__name__.endswith("qikvrt_content_disposition_batch_003_remaining_archives"))

    def test_current_dispatch_supersedes_only_root_status(self):
        contract = self.current_projection_contract()
        result = current.verify()
        self.assertEqual(result["next_deterministic_effect"], contract["next_effect"])
        self.assertEqual(self.progress["projection_owner"]["tool"], contract["tool"])
        self.assertEqual(self.progress["next_action"], contract["next_effect"])
        corpus = self.progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
        self.assertEqual(corpus["counts"]["open_subjects"], contract["open_subjects"])
        self.assertEqual(corpus["batch_002"]["state"], "TERMINALLY_DISPOSITIONED")
        self.assertEqual(corpus["batch_002"]["post_acceptance"]["state"], current.POST_ACCEPTANCE_STATE)
        self.assertEqual(corpus["batch_003"]["state"], contract["batch_state"])
        self.assertEqual(self.queue["next_deterministic_effect"], "CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002")

    def test_schema_and_policy_contract_remain_compatible(self):
        schema = load(ROOT / "schemas/human_machine_progress.schema.json")
        durable = schema["$defs"]["durableSnapshotV3"]
        policy = load(ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
        self.assertTrue(set(policy["mandatory_fields"]).issubset(durable["required"]))
        self.assertEqual(durable["properties"]["schema"]["const"], self.progress["schema"])
        self.assertIn(self.progress["state"], durable["properties"]["state"]["enum"])
        self.assertEqual(policy["tracked_snapshot"]["ownerless_state"], "IDLE")

    def test_human_projection_is_current_and_fail_closed(self):
        contract = self.current_projection_contract()
        status = (ROOT / "AI_STATUS.md").read_text(encoding="utf-8")
        expected, rendered = current.expected_projection()
        self.assertEqual(self.progress, expected)
        self.assertEqual(status, rendered)
        if contract["bar"] is not None:
            self.assertIn(contract["bar"], status)
        self.assertIn(contract["status_marker"], status)
        self.assertIn(contract["next_effect"], status)
        if HANDOFF_RECEIPT.is_file():
            self.assertIn("VERIFIED POST-PROMOTION BINDING", status)
            self.assertIn("6836f28622173e45b1330f41a294bbd46f36fec2", status)
            self.assertIn("638717de71071f1fe420ce5ddfd8521638356672", status)
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            self.assertIs(self.progress["claims"][key], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
