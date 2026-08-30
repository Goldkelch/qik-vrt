#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Unit tests for the pure durable continuation-ledger core."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "qikvrt_continuation_ledger.py"
CONTRACT_PATH = ROOT / "state" / "autonomy" / "CONTINUATION_LEDGER_CONTRACT_V1.json"
SCHEMA_PATH = ROOT / "schemas" / "qikvrt_continuation_ledger_entry_v1.schema.json"

SPEC = importlib.util.spec_from_file_location("qikvrt_continuation_ledger", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


HEAD = "a" * 40
TREE = "b" * 40
BASE = "c" * 40
WORKFLOW_BLOB = "d" * 40
SOURCE_SHA = "e" * 64


def subject() -> dict[str, str]:
    return {
        "repository": "Goldkelch/qik-vrt",
        "kind": "PULL_REQUEST",
        "identifier": "917",
    }


def binding(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "ref": "refs/pull/917/head",
        "head_sha": HEAD,
        "tree_sha": TREE,
        "base_sha": BASE,
        "workflow_path": ".github/workflows/qikvrt_reflexive_repository_watchdog.yml",
        "workflow_blob_sha": WORKFLOW_BLOB,
        "workflow_run_id": 33316138453,
        "workflow_run_attempt": 1,
        "job_id": 99269836945,
        "review_id": None,
        "receipt_sha256": SOURCE_SHA,
        "source_event": "workflow_run.completed",
    }
    value.update(changes)
    return value


def source(**changes: object) -> dict[str, str]:
    value = {
        "uri": "https://github.com/Goldkelch/qik-vrt/actions/runs/33316138453",
        "sha256": SOURCE_SHA,
    }
    value.update(changes)
    return value


def semantic(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "workflow_conclusion": "action_required",
        "jobs": [{"id": 99269836945, "status": "completed", "conclusion": "action_required"}],
        "human_review_sha256": "f" * 64,
    }
    value.update(changes)
    return value


def live(**changes: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "subject": subject(),
        "binding": binding(),
        "semantic_input": semantic(),
        "first_blocker": "ACTION_ADMISSION_REQUIRES_REOBSERVATION",
        "next_action": "REOBSERVE_EXACT_JOB_BEARING_ADMISSION_RECEIPT",
        "wake_predicates": [
            "EXACT_HEAD_TREE_OR_RUN_BINDING_CHANGED",
            "JOB_BEARING_ADMISSION_RECEIPT_CHANGED",
        ],
        "immutable_source": source(),
        "observation": {"observed_at": "2026-08-30T14:11:21Z"},
    }
    arguments.update(changes)
    return MODULE.build_live_record(**arguments)


class ContinuationLedgerTests(unittest.TestCase):
    def test_contract_and_schema_define_indefinite_logical_liveness(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "qikvrt_continuation_ledger_contract_v1")
        self.assertEqual(contract["logical_liveness"], MODULE.LIVENESS)
        self.assertFalse(contract["enabled"])
        self.assertEqual(
            contract["activation_status"],
            "DRAFT_ONLY_REQUIRES_DEDICATED_SINGLE_WRITER_AND_EXACT_READBACK",
        )
        self.assertTrue(contract["ledger"]["append_only"])
        self.assertEqual(contract["ledger"]["write_protocol"], "FAST_FORWARD_COMPARE_AND_SWAP_ONLY")
        self.assertFalse(contract["boundaries"]["logical_continuation_changes_writer_queue_liveness_or_effect_token_ttl"])
        self.assertEqual(schema["properties"]["schema"]["const"], MODULE.RECORD_SCHEMA)
        self.assertEqual(
            set(contract["states"]["evidenced_outcomes"]), MODULE.OUTCOME_STATES
        )

    def test_temporal_and_self_generated_metadata_do_not_change_identity(self) -> None:
        first = live(
            semantic_input=semantic(
                updated_at="2026-08-30T14:10:00Z",
                self_generated_status_update={"id": 1, "body": "still blocked"},
                nested={"observed_at": "2026-08-30T14:10:00Z", "value": "causal"},
            ),
            observation={"observed_at": "2026-08-30T14:10:00Z"},
        )
        second = live(
            semantic_input=semantic(
                updated_at="2031-01-01T00:00:00Z",
                self_generated_status_update={"id": 999, "body": "same semantic state"},
                nested={"observed_at": "2031-01-01T00:00:00Z", "value": "causal"},
            ),
            observation={"observed_at": "2031-01-01T00:00:00Z"},
        )
        self.assertEqual(first["continuation_key"], second["continuation_key"])
        self.assertEqual(first["record_id"], second["record_id"])
        self.assertNotIn("updated_at", first["semantic_input"])
        self.assertNotIn("self_generated_status_update", first["semantic_input"])
        self.assertNotIn("observed_at", first["semantic_input"]["nested"])

    def test_material_human_or_exact_binding_change_creates_a_new_key(self) -> None:
        initial = live()
        changed_review = live(semantic_input=semantic(human_review_sha256="1" * 64))
        changed_head = live(
            binding=binding(head_sha="1" * 40, tree_sha="2" * 40)
        )
        self.assertNotEqual(initial["continuation_key"], changed_review["continuation_key"])
        self.assertNotEqual(initial["continuation_key"], changed_head["continuation_key"])

    def test_nonterminal_block_is_indefinitely_live(self) -> None:
        record = live(
            semantic_input=semantic(workflow_conclusion="cancelled"),
            first_blocker="WATCHDOG_LIFECYCLE_CANCELLATION",
            next_action="REOBSERVE_NON_CANCELLING_TERMINAL_RECEIPT",
        )
        self.assertEqual(record["state"], "LIVE")
        self.assertEqual(record["liveness"], MODULE.LIVENESS)
        self.assertIsNone(record["outcome"])
        self.assertFalse(record["completion_claims"]["PASS"])
        self.assertFalse(record["completion_claims"]["EFFECT_ACK_DONE"])

    def test_rebind_stales_predecessor_and_keeps_successor_live(self) -> None:
        previous = live()
        stale, successor = MODULE.rebind_record(
            previous,
            binding=binding(head_sha="1" * 40, tree_sha="2" * 40),
            semantic_input=semantic(workflow_conclusion="success"),
            first_blocker="CURRENT_HEAD_REQUIRES_FRESH_GATE_RECEIPT",
            next_action="REOBSERVE_REPLACEMENT_EXACT_HEAD",
            wake_predicates=["JOB_BEARING_ADMISSION_RECEIPT_CHANGED"],
            immutable_source=source(sha256="2" * 64),
        )
        self.assertEqual(stale["state"], "REBOUND")
        self.assertEqual(
            stale["outcome"]["replacement_continuation_key"], successor["continuation_key"]
        )
        self.assertEqual(successor["state"], "LIVE")
        self.assertEqual(successor["predecessor_continuation_key"], previous["continuation_key"])
        self.assertNotEqual(previous["continuation_key"], successor["continuation_key"])

    def test_postcondition_and_external_hold_require_direct_evidence(self) -> None:
        previous = live()
        postcondition = MODULE.build_outcome_record(
            previous,
            state="POSTCONDITION_OBSERVED",
            immutable_source=source(sha256="3" * 64),
            postcondition="EXACT_CURRENT_HEAD_JOB_BEARING_RECEIPT_REOBSERVED",
        )
        self.assertEqual(postcondition["state"], "POSTCONDITION_OBSERVED")
        self.assertEqual(postcondition["predecessor_record_id"], previous["record_id"])
        held = MODULE.build_outcome_record(
            previous,
            state="EXTERNAL_HOLD",
            immutable_source=source(sha256="4" * 64),
            external_authority="GitHub Actions admission control",
            external_reason="WORKFLOW_AWAITING_APPROVAL",
        )
        self.assertEqual(held["outcome"]["authority"], "GitHub Actions admission control")
        with self.assertRaises(MODULE.ContinuationLedgerError):
            MODULE.build_outcome_record(
                previous,
                state="EXTERNAL_HOLD",
                immutable_source=source(sha256="5" * 64),
                external_authority="GitHub Actions admission control",
            )

    def test_append_plan_is_fast_forward_only_and_deduplicates_exact_bytes(self) -> None:
        record = live()
        bytes_value = MODULE.canonical_json_bytes(record)
        path = MODULE.ledger_path(record)
        initialize = MODULE.plan_append(
            ledger_head=None,
            path=path,
            existing_record_bytes=None,
            record_bytes=bytes_value,
        )
        self.assertEqual(initialize["action"], "INITIALIZE_ORPHAN_ROOT")
        self.assertFalse(initialize["force"])
        append = MODULE.plan_append(
            ledger_head="9" * 40,
            path=path,
            existing_record_bytes=None,
            record_bytes=bytes_value,
        )
        self.assertEqual(append["action"], "APPEND_FAST_FORWARD")
        duplicate = MODULE.plan_append(
            ledger_head="9" * 40,
            path=path,
            existing_record_bytes=bytes_value,
            record_bytes=bytes_value,
        )
        self.assertEqual(duplicate["action"], "NOOP_IDENTICAL_RECORD")
        collision = MODULE.plan_append(
            ledger_head="9" * 40,
            path=path,
            existing_record_bytes=b"different bytes\n",
            record_bytes=bytes_value,
        )
        self.assertEqual(collision["action"], "HOLD")
        self.assertEqual(collision["first_blocker"], "APPEND_ONLY_LEDGER_PATH_COLLISION")

    def test_invalid_exact_binding_and_volatile_record_input_fail_closed(self) -> None:
        with self.assertRaises(MODULE.ContinuationLedgerError):
            live(binding=binding(head_sha="a" * 40, tree_sha=None))
        record = live()
        record["semantic_input"]["updated_at"] = "2031-01-01T00:00:00Z"
        with self.assertRaises(MODULE.ContinuationLedgerError):
            MODULE.validate_record(record)


if __name__ == "__main__":
    unittest.main()
