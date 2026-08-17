#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression tests for the fail-closed terminal effect evidence basis."""
from __future__ import annotations

import hashlib
import json
import pathlib
import unittest

from tools.qikvrt_terminal_effect_basis import COMPLETION_CLAIMS, evaluate

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/TERMINAL_EFFECT_EVIDENCE_BASIS_V1.json"
WORK_UNIT = ROOT / "state/work_units/TERMINAL_EFFECT_EVIDENCE_BASIS_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_terminal_effect_basis.yml"

H1, T1, H2, T2, H3, T3 = ("1" * 40, "2" * 40, "3" * 40, "4" * 40, "5" * 40, "6" * 40)
SCOPE, PUB, REL = "7" * 64, "8" * 64, "9" * 64
META, SBOM, PROV, ROLLBACK = "a" * 64, "b" * 64, "c" * 64, "d" * 64
AM, AP, AR, AD, RECEIPT, CLOSURE = ("e" * 64, "f" * 64, "0" * 64, "1" * 64, "2" * 64, "3" * 64)


def gate(name: str, head: str = H2, tree: str = T2) -> dict[str, object]:
    return {"name": name, "applicable": True, "head_sha": head, "tree_sha": tree,
            "status": "completed", "conclusion": "success", "job_count": 1}


def auth(digest: str, artifact: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "authorized": True, "repository": "Goldkelch/qik-vrt",
        "candidate_head": H2, "candidate_tree": T2, "scope_sha256": SCOPE,
        "authorization_sha256": digest, "force": False,
    }
    if artifact is not None:
        value["artifact_sha256"] = artifact
    return value


def effect(kind: str, artifact: str, authorization: str) -> dict[str, object]:
    return {
        "verified": True, "request_head": H2, "request_tree": T2,
        "artifact_sha256": artifact, "authorization_sha256": authorization,
        "effect_id": f"effect/{kind}/v1", "target": f"target/{kind}",
        "transport_ack": True, "effect_ack": True, "live_readback": True,
        "receipt_sha256": RECEIPT,
    }


def evidence() -> dict[str, object]:
    return {
        "repository": "Goldkelch/qik-vrt",
        "binding": {
            "authority_head": H1, "authority_tree": T1, "base_head": H1,
            "base_tree": T1, "candidate_head": H2, "candidate_tree": T2,
            "scope_sha256": SCOPE,
        },
        "integrity": {
            "verified": True, "head_sha": H2, "tree_sha": T2,
            "materialization_state": "TREE_IDENTICAL_TRUSTED_CARRIER",
            "scope_clear": True, "provenance_clear": True,
        },
        "gates": [gate("QIKVRT CI"), gate("QIKVRT evidence materialization")],
        "writer": {"competing": False, "lease_clear": True},
        "review": {
            "mergeable": True, "draft": False, "ruleset_satisfied": True,
            "required_reviews_satisfied": True,
        },
        "artifacts": {
            "publication": {
                "artifact_sha256": PUB, "metadata_sha256": META,
                "rights_cleared": True, "scientific_status_bound": True,
            },
            "release": {
                "artifact_sha256": REL, "version": "v1.0.0",
                "sbom_sha256": SBOM, "provenance_sha256": PROV,
            },
            "deployment": {
                "artifact_sha256": REL, "environment": "production",
                "rollback_plan_sha256": ROLLBACK,
            },
        },
        "authorizations": {
            "merge": auth(AM), "publication": auth(AP, PUB),
            "release": auth(AR, REL), "deployment": auth(AD, REL),
        },
        "receipts": {
            "merge": {
                "verified": True, "candidate_head": H2, "candidate_tree": T2,
                "result_head": H3, "result_tree": T3,
                "receipt_sha256": RECEIPT, "live_readback": True,
            },
            "publication": effect("publication", PUB, AP),
            "release": effect("release", REL, AR),
            "deployment": effect("deployment", REL, AD),
            "closure": {
                "verified": True, "authority_head": H3, "authority_tree": T3,
                "required_effect_ids": [
                    "effect/deployment/v1", "effect/publication/v1", "effect/release/v1"
                ],
                "receipt_sha256": CLOSURE, "live_readback": True,
            },
        },
        "post_promotion": {
            "verified": True, "authority_head": H3, "authority_tree": T3,
            "integrity_verified": True, "gates": [gate("QIKVRT CI", H3, T3)],
        },
        "pending_required_effects": 0,
    }


class TerminalEffectEvidenceBasisTests(unittest.TestCase):
    def test_contract_has_all_bases_and_false_claims(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            set(contract["readiness"]),
            {"PASS_basis_ready", "merge_basis_ready", "publication_basis_ready",
             "release_basis_ready", "deployment_basis_ready",
             "FINAL_PASS_basis_ready", "EFFECT_ACK_DONE_basis_ready"},
        )
        self.assertEqual(contract["completion_claims"], COMPLETION_CLAIMS)
        self.assertFalse(contract["negative_controls"]["transport_ack_is_effect_ack"])

    def test_work_unit_binds_scope_base_and_non_effect_boundary(self) -> None:
        unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertEqual(unit["authority_base"]["head_sha"], "836a068d42b30f4df496caf4d712dbe8da45c043")
        self.assertEqual(unit["authority_base"]["tree_sha"], "f2f97a535842eb9558e29c3e60db3260941d8c56")
        self.assertEqual(unit["completion_claims"], COMPLETION_CLAIMS)
        paths = unit["scope"]["paths"]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(
            unit["scope"]["path_set_sha256"],
            hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest(),
        )
        self.assertFalse(unit["effect_boundary"]["external_effect_authority_created"])

    def test_workflow_is_pinned_exact_head_and_read_only(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "permissions:\n  contents: read",
            "github.event.pull_request.head.sha || github.sha",
            "persist-credentials: false",
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "tests.test_qikvrt_terminal_effect_basis",
        ):
            self.assertIn(marker, workflow)
        for forbidden in ("contents: write", "pull-requests: write", "deployments: write",
                          "git push", "gh pr merge"):
            self.assertNotIn(forbidden, workflow)

    def test_missing_evidence_is_fail_closed(self) -> None:
        result = evaluate({})
        self.assertFalse(any(result["readiness"].values()))
        self.assertEqual(result["completion_claims"], COMPLETION_CLAIMS)

    def test_predecessor_head_gate_is_rejected(self) -> None:
        value = evidence()
        value["gates"] = [gate("QIKVRT CI", H1, T1)]
        result = evaluate(value)
        self.assertFalse(result["readiness"]["PASS_basis_ready"])
        self.assertTrue(any("head mismatch" in b for b in result["blockers"]["PASS_basis_ready"]))

    def test_action_required_and_zero_job_are_rejected(self) -> None:
        value = evidence()
        bad = gate("QIKVRT CI")
        bad.update({"conclusion": "action_required", "job_count": 0})
        value["gates"] = [bad]
        blockers = evaluate(value)["blockers"]["PASS_basis_ready"]
        self.assertTrue(any("not success" in b for b in blockers))
        self.assertTrue(any("zero-job" in b for b in blockers))

    def test_pass_basis_does_not_claim_pass(self) -> None:
        value = evidence()
        value["review"]["draft"] = True
        result = evaluate(value)
        self.assertTrue(result["readiness"]["PASS_basis_ready"])
        self.assertFalse(result["readiness"]["merge_basis_ready"])
        self.assertFalse(any(result["completion_claims"].values()))

    def test_full_basis_still_performs_no_effect(self) -> None:
        result = evaluate(evidence())
        self.assertEqual(result["classification"], "ALL_BASES_READY")
        self.assertTrue(all(result["readiness"].values()))
        self.assertFalse(any(result["completion_claims"].values()))

    def test_transport_ack_does_not_substitute_for_effect_ack(self) -> None:
        value = evidence()
        value["receipts"]["publication"]["effect_ack"] = False
        result = evaluate(value)
        self.assertTrue(result["readiness"]["publication_basis_ready"])
        self.assertFalse(result["readiness"]["FINAL_PASS_basis_ready"])
        self.assertFalse(result["semantic_boundaries"]["transport_ack_is_effect_ack"])

    def test_deployment_must_equal_release_artifact(self) -> None:
        value = evidence()
        value["artifacts"]["deployment"]["artifact_sha256"] = PUB
        value["authorizations"]["deployment"]["artifact_sha256"] = PUB
        value["receipts"]["deployment"]["artifact_sha256"] = PUB
        result = evaluate(value)
        self.assertFalse(result["readiness"]["deployment_basis_ready"])
        self.assertFalse(result["readiness"]["FINAL_PASS_basis_ready"])


if __name__ == "__main__":
    unittest.main()
