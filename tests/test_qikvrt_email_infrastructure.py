#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/qikvrt_email_infrastructure.py"
spec = importlib.util.spec_from_file_location("qikvrt_email_infrastructure", MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load email infrastructure module")
mail = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mail
spec.loader.exec_module(mail)


class EmailInfrastructureTest(unittest.TestCase):
    def test_historical_lineage_and_cloud_inventory(self) -> None:
        report = mail.validate_contract()
        self.assertEqual(report["historical_anchor"], "KARLSRUHE_CSNET_1984")
        self.assertEqual(report["layer_count"], 18)
        self.assertGreaterEqual(report["standard_count"], 24)
        self.assertGreaterEqual(report["cloud_variant_count"], 16)
        policy = json.loads(
            (ROOT / "policy/QIKVRT_EMAIL_INFRASTRUCTURE_V1.json").read_text(
                encoding="utf-8"
            )
        )
        anchor = policy["historical_anchor"]
        self.assertIn("KARLSRUHE", anchor["id"])
        self.assertIn("BBN", anchor["origin"])
        self.assertIn("EMAIL_EXISTED_IN_GERMANY_BEFORE", anchor["scope_guard"])

    def test_event_driven_and_truth_boundaries(self) -> None:
        policy = json.loads(
            (ROOT / "policy/QIKVRT_EMAIL_INFRASTRUCTURE_V1.json").read_text(
                encoding="utf-8"
            )
        )
        event = policy["event_model"]
        self.assertEqual(event["normal_operation"], "EVENT_DRIVEN_ONLY")
        self.assertEqual(event["polling"], "FORBIDDEN_AS_REGULAR_DOMAIN_WORK_MODE")
        self.assertTrue(event["append_only_receipts"])
        invariants = set(policy["invariants"])
        required_fragments = (
            "RFC5321_ENVELOPE",
            "SMTP_250",
            "MAILBOX_STORED",
            "RENDERED != HUMAN_READ",
            "READ_RECEIPT != EFFECT_ACK",
            "WEBHOOK_NOTIFICATION",
            "NATURAL_PERSON_AUTHENTICATION",
            "M68000_ROUTE_DECISION != NETWORK_EFFECT",
        )
        for fragment in required_fragments:
            self.assertTrue(any(fragment in item for item in invariants), fragment)

    def test_compiled_bytes_and_exhaustive_equivalence(self) -> None:
        persisted = bytes.fromhex(
            (ROOT / "runtime/m68000/qikvrt_email_route_select.hex")
            .read_text(encoding="utf-8")
            .strip()
        )
        self.assertEqual(mail.compile_kernel(), persisted)
        receipt = mail.verify_exhaustive()
        self.assertEqual(receipt["input_pairs_verified"], 65536)
        self.assertTrue(receipt["d3_preserved"])
        self.assertFalse(receipt["physical_m68000_execution_observed"])
        self.assertFalse(receipt["network_effect"])

    def test_route_cases_and_privacy(self) -> None:
        cases = {
            0x1F: mail.COMPLETE,
            0x1E: mail.HOLD,
            0x3F: mail.REOBSERVE,
            0x5F: mail.REQUEST_AUTHORITY,
            0xDF: mail.COMPLETE,
            0x1D: mail.REOBSERVE,
        }
        for flags, expected in cases.items():
            actual = mail.execute(mail.MACHINE, flags, 0xA5)
            self.assertEqual(actual[0], expected)
            self.assertEqual(actual[3], 0xA5)
        receipt = mail.route_receipt(0x1F, 0xA5, "<private@example.test>")
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("private@example.test", encoded)
        self.assertFalse(receipt["message_content_persisted"])
        self.assertFalse(receipt["credential_accessed"])
        self.assertFalse(receipt["mail_sent_or_received"])
        self.assertFalse(receipt["effect_ack_done"])

    def test_workflow_is_event_driven_and_effect_free(self) -> None:
        workflow = (
            ROOT / ".github/workflows/qikvrt_email_infrastructure.yml"
        ).read_text(encoding="utf-8")
        self.assertNotRegex(workflow, r"(?m)^  schedule:")
        self.assertIn("external_effect=NONE", workflow)
        self.assertIn("python3 -B tools/qikvrt_email_infrastructure.py verify", workflow)
        self.assertIn("python3 -B -m unittest", workflow)


if __name__ == "__main__":
    unittest.main()
