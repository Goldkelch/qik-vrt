# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.qikvrt_requirement_delivery_gate import classify_obligation

MAIN = "a" * 40


def obligation():
    return {
        "id": "TEST",
        "required_main_paths": ["docs/result.md"],
        "delivery": {
            "effect_ack_required": True,
            "authoritative_readback": ["external_id", "timestamp"],
        },
    }


class RequirementDeliveryGateTests(unittest.TestCase):
    def test_missing_main_deliverable_can_never_be_done(self):
        with TemporaryDirectory() as temporary:
            result = classify_obligation(
                obligation(),
                repository_root=Path(temporary),
                main_sha=MAIN,
                main_reobservation=None,
                effect_receipt=None,
            )
        self.assertEqual(result["state"], "WAIT_MAIN")
        self.assertFalse(result["EFFECT_ACK_DONE"])

    def test_main_file_without_exact_reobservation_is_not_done(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/result.md").write_text("x", encoding="utf-8")
            result = classify_obligation(
                obligation(),
                repository_root=root,
                main_sha=MAIN,
                main_reobservation=None,
                effect_receipt=None,
            )
        self.assertEqual(result["state"], "WAIT_EXACT_MAIN_REOBSERVATION")

    def test_transport_or_unbound_effect_never_completes_requirement(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/result.md").write_text("x", encoding="utf-8")
            reobserved = {"main_sha": MAIN, "state": "REOBSERVED"}
            result = classify_obligation(
                obligation(),
                repository_root=root,
                main_sha=MAIN,
                main_reobservation=reobserved,
                effect_receipt={
                    "obligation_id": "TEST",
                    "main_sha": MAIN,
                    "state": "TRANSPORT_ACK",
                    "readback": {"external_id": "1", "timestamp": "now"},
                },
            )
        self.assertEqual(result["state"], "DELIVERY_REQUIRED")
        self.assertFalse(result["EFFECT_ACK_DONE"])

    def test_effect_from_predecessor_main_never_transfers(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/result.md").write_text("x", encoding="utf-8")
            result = classify_obligation(
                obligation(),
                repository_root=root,
                main_sha=MAIN,
                main_reobservation={"main_sha": MAIN, "state": "REOBSERVED"},
                effect_receipt={
                    "obligation_id": "TEST",
                    "main_sha": "b" * 40,
                    "state": "EFFECT_ACK_DONE",
                    "readback": {"external_id": "1", "timestamp": "now"},
                },
            )
        self.assertEqual(result["first_causal_blocker"], "EFFECT_ACK_BINDING_MISMATCH")

    def test_done_requires_main_reobservation_and_complete_readback(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/result.md").write_text("x", encoding="utf-8")
            result = classify_obligation(
                obligation(),
                repository_root=root,
                main_sha=MAIN,
                main_reobservation={"main_sha": MAIN, "state": "REOBSERVED"},
                effect_receipt={
                    "obligation_id": "TEST",
                    "main_sha": MAIN,
                    "state": "EFFECT_ACK_DONE",
                    "readback": {"external_id": "1", "timestamp": "now"},
                },
            )
        self.assertEqual(result["state"], "DONE")
        self.assertTrue(result["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main()
