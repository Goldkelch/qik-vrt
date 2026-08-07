# SPDX-License-Identifier: CC-BY-NC-ND-4.0
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy" / "IO_EVIDENCE_PUBLICATION_ROUNDTRIP_V1.json"
DOC_PATH = ROOT / "docs" / "IO_EVIDENCE_PUBLICATION_ROUNDTRIP.md"
TOOL_PATH = ROOT / "tools" / "qikvrt_io_roundtrip.py"


class IOEvidencePublicationRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.doc = DOC_PATH.read_text(encoding="utf-8")

    def test_universal_io_scope_and_persistence_contract(self) -> None:
        scope = self.policy["scope"]
        self.assertIn("MODEL_INPUT", scope["modalities"])
        self.assertIn("MODEL_OUTPUT", scope["modalities"])
        self.assertIn("TOOL_INPUT", scope["modalities"])
        self.assertIn("TOOL_OUTPUT", scope["modalities"])
        self.assertIn("INGRESS", scope["directions"])
        self.assertIn("EGRESS", scope["directions"])
        event = self.policy["event_record"]
        self.assertTrue(event["append_only"])
        self.assertIn("payload_sha256", event["required_fields"])
        self.assertIn("provenance", event["required_fields"])
        self.assertIn("epistemic_class", event["required_fields"])

    def test_knowledge_granularity_and_dedup_are_explicit(self) -> None:
        granularity = self.policy["knowledge_granularity"]
        self.assertIn("independently", granularity["unit"].lower())
        self.assertIn("content-address", granularity["deduplication"].lower())
        self.assertIn("not a truth predicate", granularity["novelty"].lower())

    def test_machine_proof_does_not_overclaim_nature(self) -> None:
        proof = self.policy["machine_proof_gate"]
        self.assertTrue(proof["required_for_formal_claims"])
        self.assertTrue(proof["fail_closed"])
        self.assertTrue(proof["no_placeholder_proofs"])
        self.assertIn("does not by itself prove physical correspondence", proof["model_relative_boundary"])

    def test_zenodo_and_conditional_ietf_routing(self) -> None:
        router = self.policy["publication_router"]
        self.assertIn("MACHINE_VERIFICATION_COMPLETE", router["zenodo"]["eligible_when"])
        self.assertIn("EXACT_BYTES_FROZEN", router["zenodo"]["eligible_when"])
        self.assertIn("INTEROPERABILITY_OR_PROTOCOL_RELEVANCE_TRUE", router["ietf"]["eligible_when"])
        self.assertTrue(router["not_every_event_is_publication"])
        self.assertTrue(router["zenodo"]["receipt_required"])
        self.assertTrue(router["ietf"]["receipt_required"])

    def test_no_manual_copy_step_and_external_effects_fail_closed(self) -> None:
        automation = self.policy["automation"]
        self.assertFalse(automation["human_manual_copy_step_required"])
        self.assertFalse(automation["chat_memory_required"])
        self.assertIn("PERSIST", automation["pipeline"])
        self.assertIn("PROVE_WHEN_FORMAL", automation["pipeline"])
        self.assertIn("ROUTE_ZENODO", automation["pipeline"])
        self.assertIn("ROUTE_IETF_IF_RELEVANT", automation["pipeline"])
        self.assertIn("AUTHORIZATION", automation["external_effect_steps"])
        self.assertIn("CREDENTIAL", automation["external_effect_steps"])

    def test_contract_does_not_claim_end_to_end_completion(self) -> None:
        claims = self.policy["release_claims"]
        self.assertFalse(claims["IMPLEMENTATION_COMPLETE"])
        self.assertFalse(claims["PASS"])
        self.assertFalse(claims["FINAL_PASS"])
        self.assertFalse(claims["EFFECT_ACK_DONE"])
        self.assertIn("No chat response", self.doc)

    def test_verify_command_returns_continue_not_pass(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-B", str(TOOL_PATH), "verify"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        value = json.loads(proc.stdout)
        self.assertEqual(value["state"], "CONTINUE")
        self.assertNotEqual(value["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
