#!/usr/bin/env python3
"""Boundary regression tests for universal-ontology claim closure."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formalization/QIKVRT_Formalization_v2.0"
MATRIX = FORMAL / "universal_ontology/CLAIM_MATRIX.json"
WORLD = FORMAL / "universal_ontology/WORLD_FORMULA_CLAIM_MATRIX.json"
SCOPE = FORMAL / "universal_ontology/SOURCE_SCOPE.json"
CORE = FORMAL / "QIKVRTUniversalOntology/Core.lean"
AUDIT = FORMAL / "QIKVRTUniversalOntology/AxiomAudit.lean"
EXTENDED_AUDIT = FORMAL / "QIKVRTUniversalOntology/ExtendedAxiomAudit.lean"
STANDING = ROOT / "state/authorization/delegations/OWNER_WORLD_FORMULA_FORMALIZATION_AND_PUBLICATION_DELEGATION_V1.json"
WORK = ROOT / "state/work_units/UNIFIED_ONTOLOGY_KERNEL_PROGRAM_V2.json"
IETF = ROOT / "external/ietf/UNIVERSAL_ONTOLOGY_FORMALIZATION_DISPOSITION_2026-08-06.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_universal_ontology_formalization.yml"


class UniversalOntologyClaimClosureTests(unittest.TestCase):
    def load(self, path: pathlib.Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def audited_constants(path: pathlib.Path) -> set[str]:
        return {
            line.strip().removeprefix("#print axioms ")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }

    def test_formal_claims_have_unique_kernel_constants(self):
        matrices = [self.load(MATRIX), self.load(WORLD)]
        formal = [
            claim
            for matrix in matrices
            for claim in matrix["claims"]
            if claim["kind"] == "FORMAL_THEOREM"
        ]
        constants = [claim["proof_constant"] for claim in formal]
        self.assertEqual(len(constants), 32)
        self.assertEqual(len(constants), len(set(constants)))
        self.assertEqual(set(constants), self.audited_constants(AUDIT))

    def test_extended_audit_separates_support_tranches_from_core_receipt(self):
        core = self.audited_constants(AUDIT)
        extended = self.audited_constants(EXTENDED_AUDIT)
        extra = extended - core
        self.assertEqual(len(core), 32)
        self.assertEqual(len(extended), 71)
        self.assertEqual(len(extra), 39)
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.QuantumFoundations.") for name in extra),
            9,
        )
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.HardwareWitness.") for name in extra),
            22,
        )
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.DecisionSufficiency.") for name in extra),
            8,
        )

    def test_nonformal_claims_are_not_proof_inflated(self):
        matrix = self.load(MATRIX)
        for claim in matrix["claims"]:
            if claim["kind"] != "FORMAL_THEOREM":
                self.assertNotIn("proof_constant", claim, claim["claim_id"])
        self.assertEqual(matrix["physical_correspondence"], "OPEN_CANDIDATE")
        self.assertEqual(
            matrix["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )

    def test_lean_has_no_escape_hatches(self):
        for path in (CORE, AUDIT, EXTENDED_AUDIT):
            text = path.read_text(encoding="utf-8")
            code = "\n".join(
                line for line in text.splitlines()
                if not line.lstrip().startswith(("--", "/-", "*", "-/"))
            )
            self.assertIsNone(re.search(r"\b(?:sorry|admit|axiom)\b", code), path)

    def test_source_scope_binds_authority_baseline(self):
        scope = self.load(SCOPE)
        self.assertEqual(scope["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(scope["source_commit"], "df66a3d9ea7dee7889028cc5a93f0ac34424b4b2")
        paths = {item["path"] for item in scope["sources"]}
        self.assertIn("GLOBAL_CLAIM_INVENTORY.json", paths)
        self.assertIn("docs/publications/index.json", paths)
        self.assertIn(
            "external/ietf/draft-lohmann-qikvrt-effect-ack-03.PUBLICATION_RECEIPT.json",
            paths,
        )

    def test_standing_authorization_is_hard_gated(self):
        value = self.load(STANDING)
        self.assertEqual(value["schema"], "qikvrt-owner-delegation/1.0")
        self.assertEqual(value["authorizing_owner"], "Ingolf Lohmann")
        permissions = value["autonomous_permissions"]
        self.assertIs(permissions["test_and_ci_execution"], True)
        self.assertEqual(
            permissions["credentialed_zenodo_write"],
            "AUTHORIZED_IN_PRINCIPLE_BUT_REQUIRES_AVAILABLE_VALID_CREDENTIALS_AND_PRE_EFFECT_GATES",
        )
        joined = "\n".join(value["hard_fail_closed_gates"])
        self.assertIn("No physical correspondence", joined)
        self.assertIn("No admitted, sorry, axiom-smuggled", joined)
        self.assertEqual(
            value["mandatory_status_separation"]["scientific_consensus"],
            "NOT_CLAIMED",
        )

    def test_work_program_remains_continue_until_effect_evidence(self):
        value = self.load(WORK)
        self.assertEqual(value["effect_state"], "EFFECT_ACK_CONTINUE")
        states = {item["id"]: item["state"] for item in value["work_units"]}
        self.assertEqual(states["UOK2-04"], "PENDING_EXACT_HEAD_CI")
        self.assertEqual(states["UOK2-10"], "NO_PROTOCOL_CHANGE_REQUIRED")
        self.assertEqual(value["physical_correspondence"], "OPEN_CANDIDATE")

    def test_ietf_delta_does_not_mutate_protocol(self):
        value = self.load(IETF)
        self.assertEqual(value["active_internet_draft"], "draft-lohmann-qikvrt-effect-ack-03")
        self.assertEqual(value["disposition"], "NO_PROTOCOL_CHANGE_REQUIRED")
        for field in (
            "wire_version_changed", "record_fields_changed",
            "state_machine_changed", "done_predicate_changed",
            "normative_interoperability_change",
        ):
            self.assertIs(value[field], False)
        self.assertIs(value["submission_performed_for_this_delta"], False)

    def test_workflow_binds_exact_pr_head_and_emits_receipt(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.pull_request.head.sha", text)
        self.assertIn("lake build QIKVRTUniversalOntology", text)
        self.assertIn("QIKVRTUniversalOntology/ExtendedAxiomAudit.lean", text)
        self.assertIn("make_universal_ontology_kernel_receipt.py", text)
        self.assertIn("UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT.json", text)
        self.assertIn("universal-ontology-extended-axioms.txt", text)


if __name__ == "__main__":
    unittest.main()
