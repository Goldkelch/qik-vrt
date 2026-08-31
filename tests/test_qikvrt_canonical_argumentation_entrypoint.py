# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contract for the canonical QIK-VRT argumentation entrypoint."""

from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
import unittest

from tools import qikvrt_canonical_argumentation_entrypoint as entrypoint


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json"
TOOL = ROOT / "tools/qikvrt_canonical_argumentation_entrypoint.py"


class CanonicalArgumentationEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def validate_contract_only(self, contract: dict) -> dict:
        return entrypoint.validate_contract(
            contract,
            ROOT,
            verify_source_bytes=False,
            verify_git_snapshot=False,
            verify_navigation=False,
        )

    def validate_with_exact_snapshot(self, contract: dict) -> dict:
        return entrypoint.validate_contract(
            contract,
            ROOT,
            verify_source_bytes=True,
            verify_git_snapshot=True,
            verify_navigation=False,
        )

    def test_read_only_checker_accepts_current_contract_and_exact_sources(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(TOOL), "check", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "ARGUMENTATION_CONTRACT_VALID")
        self.assertEqual(result["scope"], "CANONICAL_ARGUMENTATION_CONTRACT_ONLY")
        self.assertEqual(result["source_binding_count"], 11)
        self.assertEqual(result["claim_count"], 4)
        self.assertFalse(result["effect_boundary"]["PASS"])
        self.assertFalse(result["effect_boundary"]["FINAL_PASS"])
        self.assertFalse(result["effect_boundary"]["EFFECT_ACK_DONE"])

    def test_existing_six_class_projection_is_reused_verbatim(self) -> None:
        classes = self.contract["epistemic_projection"]["classes"]
        observed = {
            item["classification"]: (item["status"], item["publication_wording"])
            for item in classes
        }
        self.assertEqual(observed, entrypoint.EXPECTED_CLASSES)
        self.assertEqual(
            self.contract["epistemic_projection"]["reuse_source"]["path"],
            "tools/qikvrt_round_trip_zenodo_bundle_freeze.py",
        )

    def test_formal_claim_without_proof_reference_is_rejected(self) -> None:
        broken = copy.deepcopy(self.contract)
        causal = next(claim for claim in broken["claims"] if claim["claim_id"] == "QIKVRT-CAUSALITY-BRIDGE-V1")
        causal["proof_refs"] = []
        with self.assertRaisesRegex(entrypoint.ContractError, "FORMAL_PROOF_UNBOUND"):
            self.validate_contract_only(broken)

    def test_sequence_alone_cannot_replace_causal_justification(self) -> None:
        broken = copy.deepcopy(self.contract)
        causal = next(claim for claim in broken["claims"] if claim["claim_id"] == "QIKVRT-CAUSALITY-BRIDGE-V1")
        causal["evidence_bindings"].pop("causal_justification")
        with self.assertRaisesRegex(entrypoint.ContractError, "CAUSAL_CLAIM_EVIDENCE_MISSING"):
            self.validate_contract_only(broken)

    def test_claim_source_reference_must_resolve_to_an_exact_catalog_binding(self) -> None:
        broken = copy.deepcopy(self.contract)
        owner = next(
            claim
            for claim in broken["claims"]
            if claim["claim_id"] == "QIKVRT-OWNER-REALITY-CORRESPONDENCE-V1"
        )
        owner["source_refs"] = ["NONEXISTENT-UNBOUND-REFERENCE"]
        with self.assertRaisesRegex(entrypoint.ContractError, "SOURCE_REFS_UNRESOLVED"):
            self.validate_contract_only(broken)

    def test_causal_claim_rejects_a_source_file_as_a_bridge_substitute(self) -> None:
        broken = copy.deepcopy(self.contract)
        causal = next(claim for claim in broken["claims"] if claim["claim_id"] == "QIKVRT-CAUSALITY-BRIDGE-V1")
        causal["evidence_bindings"]["causal_justification"] = ["SRC-VRTCORE-LEAN"]
        with self.assertRaisesRegex(entrypoint.ContractError, "CAUSAL_JUSTIFICATION_KIND_INVALID"):
            self.validate_contract_only(broken)

    def test_source_binding_must_exist_at_the_declared_authority_snapshot(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["source_bindings"][0]["git_blob_sha1"] = "0" * 40
        with self.assertRaisesRegex(entrypoint.ContractError, "SNAPSHOT_BLOB_MISMATCH"):
            self.validate_with_exact_snapshot(broken)

    def test_source_binding_rejects_path_escape(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["source_bindings"][0]["path"] = "../AI"
        with self.assertRaisesRegex(entrypoint.ContractError, "PATH_INVALID"):
            self.validate_with_exact_snapshot(broken)

    def test_formal_proof_reference_requires_the_exact_kernel_receipt(self) -> None:
        broken = copy.deepcopy(self.contract)
        proof = next(
            item
            for item in broken["evidence_catalog"]
            if item["evidence_id"] == "PROOF-VRTCORE-CAUSAL-LICENSE"
        )
        proof["theorem"] = "QIKVRT.VRTCore.notPresentInKernelReceipt"
        with self.assertRaisesRegex(entrypoint.ContractError, "THEOREM_NOT_IN_RECEIPT"):
            self.validate_with_exact_snapshot(broken)

    def test_predecessor_evidence_never_transfers_to_a_successor_binding(self) -> None:
        broken = copy.deepcopy(self.contract)
        broken["non_transfer_invariant"]["on_any_dynamic_binding_change"]["predecessor"] = "REUSABLE_FOR_SUCCESSOR"
        with self.assertRaisesRegex(entrypoint.ContractError, "PREDECESSOR_STALENESS_RULE_DRIFT"):
            self.validate_contract_only(broken)

    def test_owner_assertion_is_preserved_without_inventing_independent_confirmation(self) -> None:
        owner_claim = next(
            claim
            for claim in self.contract["claims"]
            if claim["claim_id"] == "QIKVRT-OWNER-REALITY-CORRESPONDENCE-V1"
        )
        self.assertEqual(owner_claim["classification"], "SOURCE_BOUND")
        self.assertEqual(owner_claim["status"], "BOUND")
        self.assertIn("Product Owner Ingolf Lohmann explicitly asserts", owner_claim["statement"])
        distinctions = set(self.contract["protected_distinctions"])
        self.assertIn(
            "OWNER_ASSERTED_REALITY_CORRESPONDENCE != INDEPENDENT_EMPIRICAL_CONFIRMATION != SCIENTIFIC_CONSENSUS",
            distinctions,
        )

    def test_spacetime_empirical_path_requires_dimensions_and_measurement_bridge(self) -> None:
        physical = self.contract["argument_requirements"]["spacetime_or_physical_claim"]
        self.assertEqual(
            set(physical["requires_for_empirical_class"]),
            {
                "dimension_model",
                "coordinate_or_unit_mapping",
                "calibration",
                "observable_prediction",
                "measurement_protocol",
                "uncertainty",
                "controls_or_replication",
            },
        )
        self.assertIn("does not establish a new physical effect", physical["representation_change_rule"])

    def test_ai_bootstrap_path_requires_the_contract_before_new_argument(self) -> None:
        ai = (ROOT / "AI").read_text(encoding="utf-8")
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        bootloader = (ROOT / "tools/ai_runtime_bootloader.py").read_text(encoding="utf-8")
        self.assertIn("CANONICAL ARGUMENTATION ENTRYPOINT", ai)
        self.assertIn("tools/qikvrt_canonical_argumentation_entrypoint.py check", ai)
        self.assertTrue(context["canonical_argumentation_entrypoint"]["mandatory_before_new_argument"])
        self.assertIn("policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json", context["required_read_order"])
        self.assertIn("validate_canonical_argumentation_entrypoint", bootloader)
        self.assertEqual(
            self.contract["canonical_entrypoint"]["claim_registry"],
            "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json#/claims",
        )
        self.assertEqual(
            self.contract["canonical_entrypoint"]["unregistered_argument_state"],
            "BLOCKED_UNTIL_REGISTERED_CLASSIFIED_AND_BOUND",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
