import json
from pathlib import Path
import unittest

from tools.qikvrt_hold_contract import (
    HoldContractError,
    validate_document,
    validate_hold_reason,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "QIKVRT_EXPLICIT_HOLD_V1.json"


def explicit_hold(reason_code="COMPETING_WRITER_ACTIVE", d0=1):
    return {
        "state": "HOLD",
        "verification_state": "HOLD_UNVERIFIED",
        "hold_reason": {
            "reason_code": reason_code,
            "reason": "The named condition is active on the exact subject.",
            "subject": {
                "repository": "Goldkelch/qik-vrt",
                "kind": "pull_request",
                "number": 974,
                "head_sha": "e40ec6174546c685b42af0d2cdbc175bbbba4c8a",
            },
            "evidence_refs": ["actions/run/33783865625"],
            "owner": {"role": "EXACT_SUBJECT_OBSERVER", "actor": "github-actions[bot]"},
            "retry_condition": {
                "event": "workflow_run.completed",
                "predicate": "the writer lease is terminal and the exact head is unchanged",
            },
            "next_action": "REOBSERVE_EXACT_SUBJECT_AFTER_WRITER_TERMINAL",
            "d0": d0,
        },
        "completion_claims": {
            "MERGE": False,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


class ExplicitHoldContractTests(unittest.TestCase):
    def test_policy_is_machine_readable(self):
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(value["policy_id"], "QIKVRT-EXPLICIT-HOLD-V1")
        self.assertTrue(value["scope"]["historical_predecessor_receipts_are_immutable"])
        self.assertFalse(value["scope"]["predecessor_evidence_transfer"])

    def test_explicit_hold_passes(self):
        result = validate_document(explicit_hold())
        self.assertEqual(result[0]["hold_reason"]["reason_code"], "COMPETING_WRITER_ACTIVE")

    def test_bare_hold_is_forbidden(self):
        with self.assertRaisesRegex(HoldContractError, "no explicit hold_reason"):
            validate_document({"state": "HOLD"})

    def test_unspecified_reason_is_forbidden(self):
        value = explicit_hold()
        value["hold_reason"]["reason_code"] = "UNSPECIFIED"
        with self.assertRaisesRegex(HoldContractError, "not explicit"):
            validate_document(value)

    def test_generic_wait_is_not_a_next_action(self):
        value = explicit_hold()
        value["hold_reason"]["next_action"] = "WAIT"
        with self.assertRaisesRegex(HoldContractError, "not deterministic"):
            validate_document(value)

    def test_zero_job_is_reobserve_not_hold(self):
        value = explicit_hold("ZERO_EXECUTED_JOB_GATE", 1)
        with self.assertRaisesRegex(HoldContractError, "must be D0=2"):
            validate_document(value)
        value["hold_reason"]["d0"] = 2
        validate_document(value)

    def test_evidence_drift_is_reobserve_not_hold(self):
        value = explicit_hold("CAUSAL_REVIEW_EVIDENCE_DRIFT", 2)
        validate_document(value)

    def test_missing_authority_is_request_authority(self):
        value = explicit_hold("INDEPENDENT_CODE_OWNER_AUTHORITY_NOT_OBSERVED", 1)
        with self.assertRaisesRegex(HoldContractError, "must be D0=3"):
            validate_document(value)
        value["hold_reason"]["d0"] = 3
        validate_document(value)

    def test_complete_legacy_receipt_is_accepted_without_rewrite(self):
        value = {
            "state": "WAIT",
            "verification_state": "HOLD_UNVERIFIED",
            "repository": "Goldkelch/qik-vrt",
            "pr_number": 974,
            "head_sha": "e40ec6174546c685b42af0d2cdbc175bbbba4c8a",
            "first_blocker": "COMPETING_WRITER_ACTIVE",
            "detail": "1 productive repository writer is active",
            "derived_action": {
                "d0": 1,
                "next_action": "REOBSERVE_EXACT_SUBJECT_AFTER_WRITER_TERMINAL",
            },
            "ledger_path": "state/mesh/reviews/pr-974/example.json",
        }
        validate_document(value)

    def test_legacy_hold_with_null_blocker_is_forbidden(self):
        value = {
            "verification_state": "HOLD_UNVERIFIED",
            "repository": "Goldkelch/qik-vrt",
            "pr_number": 974,
            "head_sha": "e40ec6174546c685b42af0d2cdbc175bbbba4c8a",
            "first_blocker": None,
            "detail": None,
            "derived_action": {"d0": 3, "next_action": "REQUEST_AUTHORITY"},
        }
        with self.assertRaises(HoldContractError):
            validate_document(value)

    def test_hold_completion_claims_remain_false_in_example(self):
        claims = explicit_hold()["completion_claims"]
        self.assertFalse(any(claims.values()))


if __name__ == "__main__":
    unittest.main()
