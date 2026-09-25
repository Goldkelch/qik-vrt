import copy
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

from tools.qikvrt_output_contract import (  # noqa: E402
    ARTICLE_BYTES,
    ARTICLE_PATH,
    ARTICLE_SHA256,
    BINDING_KEY,
    OutputContractError,
    bind_output,
    canonical_article_identity,
    load_policy,
    validate_output,
)


class UniversalProofThoughtSchemaTests(unittest.TestCase):
    def base(self):
        return bind_output(
            {"schema": "example_payload_v1", "value": 1},
            node_id="test-node",
            repository="Goldkelch/qik-vrt",
            subject={"head": "0" * 40, "tree": "1" * 40},
            claim_kind="FORMAL_THEOREM",
            statement="bounded example theorem output",
            assumptions=[],
            definitions=["example definition"],
            dependencies=[],
            exclusions=["physical correspondence"],
            evidence_refs=["lean:test"],
            epistemic_state="FORMAL",
            effect_state="NONE",
            transport_ack=False,
            effect_ack_done=False,
            new_difference="FORMAL_RESULT_MATERIALIZED",
        )

    def test_article_identity_is_exact(self):
        raw = ARTICLE_PATH.read_bytes()
        self.assertEqual(len(raw), ARTICLE_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ARTICLE_SHA256)
        self.assertEqual(canonical_article_identity()["sha256"], ARTICLE_SHA256)

    def test_policy_is_mandatory_and_binds_article(self):
        policy = load_policy()
        self.assertEqual(policy["status"], "MANDATORY_FAIL_CLOSED")
        self.assertTrue(policy["applies_to"]["current_and_future_node_outputs"])
        self.assertTrue(policy["persistence"]["every_node_run_must_persist_binding_in_its_receipt_or_ledger"])
        self.assertFalse(policy["invariants"]["predecessor_evidence_transfer"])
        self.assertEqual(policy["canonical_article"]["sha256"], ARTICLE_SHA256)

    def test_valid_bound_output_passes(self):
        value = self.base()
        self.assertEqual(validate_output(value), value)
        self.assertIn(BINDING_KEY, value)

    def test_missing_binding_fails_closed(self):
        with self.assertRaises(OutputContractError):
            validate_output({"schema": "unbound"})

    def test_article_rebinding_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["article_binding"]["sha256"] = "0" * 64
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_predecessor_transfer_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["scope"]["predecessor_evidence_transfer"] = True
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_transport_ack_cannot_become_effect_ack(self):
        value = self.base()
        value[BINDING_KEY]["effect_status"]["transport_ack_is_effect_ack"] = True
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_unscoped_done_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["effect_status"]["effect_ack_done"] = True
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_mesh_runtime_is_wired_to_output_contract(self):
        text = (ROOT / "tools/qikvrt_real_mesh.py").read_text(encoding="utf-8")
        self.assertIn("from tools.qikvrt_output_contract import", text)
        self.assertIn("bind_output(", text)
        self.assertIn("validate_output(", text)

    def test_ai_context_requires_policy_and_article(self):
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        order = context["required_read_order"]
        self.assertIn("policy/QIKVRT_UNIVERSAL_PROOF_THOUGHT_SCHEMA_V1.json", order)
        self.assertIn("docs/QIKVRT_UNIVERSAL_PROOF_AND_THOUGHT_SCHEMA_DE.md", order)
        ai = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn("QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1", ai)
        self.assertIn("every node-generated output", ai)


if __name__ == "__main__":
    unittest.main()
