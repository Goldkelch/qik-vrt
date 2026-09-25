import copy
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

from tools import qikvrt_authority_mirror_mesh_instance as authority_mirror_mesh
from tools import qikvrt_mesh_node_receipt as mesh_node_receipt
from tools import qikvrt_workflow_executor as workflow_executor

from tools.qikvrt_output_contract import (  # noqa: E402
    ARTICLE_GIT_BLOB_SHA1,
    ARTICLE_PATH,
    ORIGIN_PROOF_GIT_BLOB_SHA1,
    ORIGIN_PROOF_PATH,
    BINDING_KEY,
    OutputContractError,
    bind_output,
    canonical_article_identity,
    canonical_origin_proof_identity,
    canonical_knowledge_artifacts_identity,
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

    def test_article_and_origin_proof_identities_are_exact(self):
        self.assertTrue(ARTICLE_PATH.is_file())
        self.assertTrue(ORIGIN_PROOF_PATH.is_file())
        self.assertEqual(
            canonical_article_identity()["git_blob_sha1"],
            ARTICLE_GIT_BLOB_SHA1,
        )
        self.assertEqual(
            canonical_origin_proof_identity()["git_blob_sha1"],
            ORIGIN_PROOF_GIT_BLOB_SHA1,
        )

    def test_policy_is_mandatory_and_binds_article(self):
        policy = load_policy()
        self.assertEqual(policy["status"], "MANDATORY_FAIL_CLOSED")
        self.assertTrue(policy["applies_to"]["current_and_future_node_outputs"])
        self.assertTrue(policy["persistence"]["every_node_run_must_persist_binding_in_its_receipt_or_ledger"])
        self.assertFalse(policy["invariants"]["predecessor_evidence_transfer"])
        self.assertEqual(
            policy["canonical_article"]["git_blob_sha1"],
            ARTICLE_GIT_BLOB_SHA1,
        )
        self.assertEqual(
            policy["ontological_origin_proof"]["document_git_blob_sha1"],
            ORIGIN_PROOF_GIT_BLOB_SHA1,
        )
        self.assertTrue(
            policy["persistence"]["every_node_must_bind_ontological_origin_proof"]
        )
        self.assertTrue(
            policy["persistence"]["every_node_must_bind_required_knowledge_artifacts"]
        )
        self.assertEqual(
            policy["required_knowledge_artifacts"]["manifest_git_blob_sha1"],
            canonical_knowledge_artifacts_identity()["git_blob_sha1"],
        )

    def test_valid_bound_output_passes(self):
        value = self.base()
        self.assertEqual(validate_output(value), value)
        self.assertIn(BINDING_KEY, value)

    def test_missing_binding_fails_closed(self):
        with self.assertRaises(OutputContractError):
            validate_output({"schema": "unbound"})

    def test_article_rebinding_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["article_binding"]["git_blob_sha1"] = "0" * 40
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_origin_proof_rebinding_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["ontological_origin_proof_binding"][
            "git_blob_sha1"
        ] = "0" * 40
        with self.assertRaises(OutputContractError):
            validate_output(value)

    def test_required_knowledge_rebinding_fails_closed(self):
        value = self.base()
        value[BINDING_KEY]["knowledge_artifacts_binding"]["git_blob_sha1"] = "0" * 40
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
        self.assertIn("docs/ONTOLOGICAL_ORIGIN_OF_DIFFERENCE_DE.md", order)
        self.assertIn(
            "state/mesh/QIKVRT_REQUIRED_KNOWLEDGE_ARTIFACTS_20260925_V1.json",
            order,
        )
        self.assertIn(
            "docs/publications/2026-09-25-leibniz-qikvrt/PROSA_VOM_UNTERSCHIED_ZU_QIKVRT_DE.md",
            order,
        )
        self.assertIn(
            "docs/publications/2026-09-25-leibniz-qikvrt/SCIENTIFIC_ARTICLE_LEIBNIZ_QIKVRT_DE.md",
            order,
        )
        ai = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn("QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1", ai)
        self.assertIn("every node-generated output", ai)

    def test_authority_mirror_terminal_projection_is_bound(self):
        observation = {
            "schema": authority_mirror_mesh.INPUT_SCHEMA,
            "observation_id": "proof-schema-test-observation",
            "observed_at": "2026-09-25T06:00:00Z",
            "authority": {
                "repository": "Goldkelch/qik-vrt",
                "role": "AUTHORITY",
                "ref_name": "main",
                "head_sha": "1" * 40,
                "root_tree_sha": "2" * 40,
                "inventory": {"open_issues": 0, "open_pull_requests": 0, "branches": 1},
                "integrity": None,
            },
            "mirror": {
                "repository": "ingolf-lohmann/qik-vrt",
                "role": "MIRROR",
                "ref_name": "main",
                "head_sha": "3" * 40,
                "root_tree_sha": "4" * 40,
                "inventory": {"open_issues": 0, "open_pull_requests": 0, "branches": 1},
                "integrity": None,
            },
        }
        instance = authority_mirror_mesh.build_mesh_instance(observation)
        projection = authority_mirror_mesh.terminal_projection(instance, "FULL")
        validate_output(projection)
        self.assertIn(BINDING_KEY, projection)
        self.assertFalse(
            projection[BINDING_KEY]["scope"]["predecessor_evidence_transfer"]
        )

    def test_future_node_receipt_requires_bound_wrapper(self):
        bound = mesh_node_receipt.build_bound_node_receipt(
            "example/node", "main", ROOT
        )
        validate_output(bound)
        validation = mesh_node_receipt.validate_bound_node_receipt(
            bound, "example/node", "main", ROOT
        )
        validate_output(validation)
        legacy_unbound = workflow_executor.build_node_receipt(
            "example/node", "main", ROOT
        )
        with self.assertRaises(mesh_node_receipt.NodeReceiptContractError):
            mesh_node_receipt.validate_bound_node_receipt(
                legacy_unbound, "example/node", "main", ROOT
            )

    def test_output_carrier_registry_is_closed_for_current_declared_carriers(self):
        registry = json.loads(
            (ROOT / "state/mesh/QIKVRT_NODE_OUTPUT_CARRIER_REGISTRY_V1.json")
            .read_text(encoding="utf-8")
        )
        self.assertTrue(registry["coverage_complete_for_declared_current_carriers"])
        self.assertTrue(registry["future_carriers_require_registration_before_admission"])
        self.assertGreaterEqual(len(registry["carriers"]), 4)
        for carrier in registry["carriers"]:
            self.assertEqual(carrier["policy_id"], "QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1")
            self.assertEqual(carrier["enforcement"], "FAIL_CLOSED")
            self.assertTrue(carrier["article_binding_required"])
            self.assertTrue(carrier["ontological_origin_proof_binding_required"])
            self.assertTrue(carrier["required_knowledge_artifacts_binding_required"])


if __name__ == "__main__":
    unittest.main()
