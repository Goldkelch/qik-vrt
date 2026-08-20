import copy
import json
import unittest
from pathlib import Path

from tools.qikvrt_metagrammar import MetagrammarError, bind_digest, canonical_sha256, validate


H40 = "a" * 40
T40 = "b" * 40
ROOT = Path(__file__).resolve().parents[1]


def envelope():
    return {
        "meta": {
            "schema": "qikvrt_metagrammar_envelope_v1",
            "version": "1.0",
            "kind": "OBSERVE",
            "rid": "test-rid-1",
            "timestamp": "2026-08-17T15:34:05Z",
        },
        "binding": {
            "repository": "Goldkelch/qik-vrt",
            "ref": "refs/heads/main",
            "head": H40,
            "tree": T40,
            "predecessor_rid": None,
        },
        "intent": {
            "verb": "OBSERVE",
            "object": "exact-head state",
            "constraints": ["read-only"],
        },
        "authority": {
            "status": "BOUND",
            "source": "product-owner",
            "authorization_id": "po-test",
            "scope": ["OBSERVE"],
        },
        "evidence": [
            {"type": "HEAD", "value": H40, "sha256": None},
            {"type": "TREE", "value": T40, "sha256": None},
        ],
        "state": {
            "classification": "OBSERVE",
            "blocker": None,
            "next_action": "REOBSERVE",
        },
        "effect": {
            "state": "NONE",
            "productive": False,
            "effect_id": None,
            "effect_ack": {"status": "NONE", "receipt": None},
        },
        "proof": {"canonical_sha256": "0" * 64, "signature": None},
    }


class MetagrammarTests(unittest.TestCase):
    def test_digest_binding_is_deterministic_and_valid(self):
        one = bind_digest(envelope())
        two = bind_digest(copy.deepcopy(envelope()))
        self.assertEqual(one["proof"]["canonical_sha256"], two["proof"]["canonical_sha256"])
        self.assertEqual(one["proof"]["canonical_sha256"], canonical_sha256(one))
        validate(one)

    def test_tampering_breaks_digest(self):
        value = bind_digest(envelope())
        value["state"]["classification"] = "CHANGED"
        with self.assertRaisesRegex(MetagrammarError, "canonical digest mismatch"):
            validate(value)

    def test_unbound_authority_fails_closed(self):
        value = envelope()
        value["authority"]["status"] = "MISSING"
        value["state"]["next_action"] = "EXECUTE"
        value["effect"]["productive"] = True
        value["effect"]["state"] = "EXECUTED"
        value = bind_digest(value)
        with self.assertRaises(MetagrammarError):
            validate(value)

    def test_missing_authority_allows_bounded_hold(self):
        value = envelope()
        value["meta"]["kind"] = "HOLD"
        value["authority"]["status"] = "MISSING"
        value["authority"]["authorization_id"] = None
        value["state"]["classification"] = "MISSING_AUTHORITY"
        value["state"]["blocker"] = "authorization not bound"
        value["state"]["next_action"] = "HOLD"
        value = bind_digest(value)
        validate(value)

    def test_effect_ack_cannot_outrun_observed_effect(self):
        value = envelope()
        value["effect"]["state"] = "OBSERVED"
        value["effect"]["effect_ack"] = {"status": "ACKNOWLEDGED", "receipt": "r1"}
        value = bind_digest(value)
        with self.assertRaisesRegex(MetagrammarError, "cannot outrun"):
            validate(value)

    def test_acknowledged_effect_requires_receipt(self):
        value = envelope()
        value["meta"]["kind"] = "ACK"
        value["effect"]["state"] = "ACKNOWLEDGED"
        value["effect"]["effect_id"] = "effect-1"
        value["effect"]["effect_ack"] = {"status": "ACKNOWLEDGED", "receipt": None}
        value = bind_digest(value)
        with self.assertRaisesRegex(MetagrammarError, "requires receipt"):
            validate(value)

    def test_exact_head_and_tree_are_mandatory(self):
        value = envelope()
        value["binding"]["head"] = "deadbeef"
        value = bind_digest(value)
        with self.assertRaisesRegex(MetagrammarError, "head must"):
            validate(value)

    def test_top_level_shape_is_closed(self):
        value = envelope()
        value["implicit_authorization"] = True
        value = bind_digest(value)
        with self.assertRaisesRegex(MetagrammarError, "canonical eight sections"):
            validate(value)

    def test_contiguous_output_contract_is_machine_bound(self):
        state = json.loads((ROOT / "state" / "autonomy" / "METAGRAMMAR_OF_UNDERSTANDING_V1.json").read_text(encoding="utf-8"))
        contract = state["contiguous_output_contract"]
        self.assertEqual(contract["semantic_unit"], "ATOMIC_DELIVERY_OBJECT")
        self.assertEqual(contract["default_delivery_mode"], "CONTIGUOUS")
        self.assertIn("HARD_TRANSPORT_OR_RUNTIME_LIMIT", contract["interrupt_only_for"])
        self.assertIn("EXPLICIT_USER_REQUEST", contract["interrupt_only_for"])
        self.assertFalse(contract["forced_continuation"]["repeat_completed_introduction"])
        self.assertIn("SEMANTIC_CONTEXT", contract["forced_continuation"]["must_preserve"])
        self.assertEqual(contract["public_distribution"]["transport"], "HTTPS")
        self.assertTrue(contract["public_distribution"]["anonymous_read"])
        self.assertIn("RAW_GITHUB_CONTENT", contract["public_distribution"]["interfaces"])
        self.assertEqual(
            contract["public_distribution"]["role_local_adoption"],
            "REOBSERVE_EXACT_AUTHORITY_BINDING_BEFORE_CONSUMPTION",
        )


if __name__ == "__main__":
    unittest.main()
