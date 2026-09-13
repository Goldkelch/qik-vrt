# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/MESH_SELF_EXPLANATION_V1.json"
DISCLOSURE = ROOT / ".well-known/qik-vrt-self-disclosure.json"
AI_CONTEXT = ROOT / "AI_CONTEXT.json"
AI = ROOT / "AI"
HUMAN_CONTRACT = ROOT / "docs/MESH_SELF_EXPLANATION_AND_DELIVERY.md"


class MeshSelfExplanationScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.disclosure = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
        cls.ai_context = json.loads(AI_CONTEXT.read_text(encoding="utf-8"))
        cls.ai = AI.read_text(encoding="utf-8")
        cls.human_contract = HUMAN_CONTRACT.read_text(encoding="utf-8")

    def test_scope_is_exclusively_the_owner_qik_vrt_temdd_mesh(self) -> None:
        project_name = "QIK-VRT Tested Event Model Driven Development Mesh Repository"
        scope = self.policy["project_scope"]
        self.assertEqual(scope["name"], project_name)
        self.assertEqual(scope["owner"], "Ingolf Lohmann")
        self.assertEqual(scope["authority_repository"], "Goldkelch/qik-vrt")
        self.assertEqual(scope["mirror_repository"], "ingolf-lohmann/qik-vrt")
        self.assertIs(scope["applies_exclusively_to_this_qik_vrt_temdd_mesh"], True)
        self.assertIs(scope["generic_mesh_repository_applicability_claimed"], False)
        self.assertEqual(scope["external_mesh_repositories"], "OUT_OF_SCOPE")
        self.assertNotIn("every QIK-VRT Mesh repository", self.policy["purpose"])

        binding = self.disclosure["bindings"]["mesh_self_explanation"]
        self.assertEqual(binding["project_name"], project_name)
        self.assertIs(binding["exclusive_project_scope"], True)
        self.assertIs(binding["generic_mesh_repository_applicability_claimed"], False)

        self.assertEqual(self.ai_context["project"]["name"], project_name)
        self.assertIs(self.ai_context["project"]["scope"]["exclusive_to_this_project"], True)
        self.assertIs(
            self.ai_context["project"]["scope"]["generic_mesh_repository_applicability_claimed"],
            False,
        )
        self.assertNotIn("Every QIK-VRT repository", self.ai_context["entrypoint_rule"])

        self.assertIn("SELF-EXPLANATION SCOPE", self.ai)
        self.assertIn(
            "applies exclusively to Ingolf Lohmann's QIK-VRT Tested Event Model Driven Development Mesh Repository",
            self.ai,
        )
        self.assertIn(
            "applies **exclusively to Ingolf Lohmann's QIK-VRT Tested Event Model Driven Development Mesh Repository**",
            self.human_contract,
        )

    def test_internal_mesh_extension_does_not_generalize_scope(self) -> None:
        interoperability = self.policy["mesh_interoperability"]
        self.assertEqual(interoperability["scope"], "INTERNAL_QIK_VRT_TEMDD_MESH_ONLY")
        self.assertIs(interoperability["external_mesh_repositories_are_out_of_scope"], True)
        self.assertIn("Internal downstream Mesh elements", self.ai)
        self.assertIn("does not extend this contract to unrelated Mesh repositories", self.ai)
        self.assertIn("does not extend the contract to arbitrary external Mesh repositories", self.human_contract)


if __name__ == "__main__":
    unittest.main()
