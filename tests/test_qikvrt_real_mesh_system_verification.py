#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Tests for the reflexive real-mesh system verification tool."""
from __future__ import annotations

import copy
import json
import pathlib
import socket
import tempfile
import unittest

from tools import qikvrt_real_mesh as mesh
from tools import qikvrt_real_mesh_system_verification as sysverify

SOURCE_HEAD = "a" * 40
SOURCE_TREE = "b" * 40


def _minimal_receipt(*, overrides: dict | None = None) -> dict:
    """Build a minimal conformant execution receipt for contract testing."""
    base: dict = {
        "schema": "qikvrt_real_mesh_execution_receipt_v1",
        "mesh_id": mesh.MESH_ID,
        "source_head": SOURCE_HEAD,
        "source_tree": SOURCE_TREE,
        "pair_count": 2,
        "node_process_count": 4,
        "network_scope": mesh.NETWORK_SCOPE,
        "event_model": "SOCKET_EVENT_DRIVEN_NO_DOMAIN_POLLING",
        "redundant_path_observed": True,
        "routes": [
            {
                "observation": {
                    "path": [
                        "node-1",
                        "node-2",
                        "node-3",
                    ]
                },
                "bounded_effect_ack": {"state": "DONE"},
            },
            {
                "observation": {
                    "path": [
                        "node-3",
                        "node-4",
                        "node-1",
                    ]
                },
                "bounded_effect_ack": {"state": "DONE"},
            },
        ],
        "restart_replay": {
            "node_id": "node-1",
            "same_terminal_receipt": True,
            "ledger_record_count_unchanged": True,
            "observed": True,
        },
        "completion_claims": {
            "real_multi_pair_mesh_runtime_executed": True,
            "independent_tcp_node_processes_observed": True,
            "multi_hop_delivery_reobserved": True,
            "acknowledgement_return_path_observed": True,
            "append_only_restart_persistence_observed": True,
            "bounded_loopback_effect_ack_done": True,
            "general_effect_ack_done": False,
            "general_internet_reachability": False,
            "production_deployment": False,
            "physical_hardware_execution": False,
            "authority_mirror_synchronization": False,
            "authority_mirror_equality_claimed": False,
            "merge": False,
            "PASS": False,
            "FINAL_PASS": False,
        },
        "effect_ack_scope": mesh.EFFECT_ACK_SCOPE,
        "external_effect": "NONE",
        "receipt_created_utc": "2026-08-24T21:00:00.000000Z",
    }
    if overrides:
        base.update(overrides)
    return base


class VerifyReceiptPureContractTests(unittest.TestCase):
    """Pure-contract tests: verify_receipt against the declared specification."""

    def setUp(self) -> None:
        self.contract = sysverify.load_contract()

    def test_conformant_receipt_has_no_findings(self) -> None:
        r = _minimal_receipt()
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertEqual(findings, [])

    def test_wrong_schema_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"schema": "wrong_schema"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("schema" in f for f in findings), findings)

    def test_wrong_mesh_id_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"mesh_id": "WRONG_MESH"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("mesh_id" in f for f in findings), findings)

    def test_insufficient_pair_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"pair_count": 1})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("pair_count" in f for f in findings), findings)

    def test_insufficient_node_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"node_process_count": 2})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("node_process_count" in f for f in findings), findings)

    def test_non_redundant_path_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"redundant_path_observed": False})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("redundant" in f for f in findings), findings)

    def test_wrong_network_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"network_scope": "PUBLIC_INTERNET"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("network_scope" in f for f in findings), findings)

    def test_restart_replay_failure_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["restart_replay"]["same_terminal_receipt"] = False
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("same_terminal_receipt" in f for f in findings), findings)

    def test_false_general_effect_ack_done_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["general_effect_ack_done"] = True
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(
            any("general_effect_ack_done" in f for f in findings), findings
        )

    def test_false_pass_claim_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["PASS"] = True
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("PASS" in f for f in findings), findings)

    def test_wrong_effect_ack_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"effect_ack_scope": "GENERAL"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("effect_ack_scope" in f for f in findings), findings)

    def test_missing_routes_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"routes": []})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("route" in f or "path" in f for f in findings), findings)

    def test_receipt_sha256_mismatch_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["receipt_sha256"] = "0" * 64
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("sha256" in f for f in findings), findings)

    def test_receipt_sha256_match_is_not_a_finding(self) -> None:
        r = _minimal_receipt()
        r["receipt_sha256"] = sysverify.canonical_sha256(r)
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertEqual(findings, [])


class AuditReceiptStructureTests(unittest.TestCase):
    """Verify that the audit receipt structure is well-formed."""

    def setUp(self) -> None:
        self.contract = sysverify.load_contract()
        self.reflexive_standard = sysverify.load_reflexive_standard()

    def _audit(self, findings: list[str]) -> dict:
        r = _minimal_receipt()
        return sysverify.build_audit_receipt(
            receipt_path="/tmp/test_receipt.json",
            receipt=r,
            contract=self.contract,
            findings=findings,
            reflexive_standard=self.reflexive_standard,
        )

    def test_conformant_receipt_produces_pass_status(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["finding_count"], 0)

    def test_findings_produce_block_status(self) -> None:
        audit = self._audit(["some finding"])
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["finding_count"], 1)

    def test_audit_schema_is_correct(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["schema"], sysverify.AUDIT_SCHEMA)

    def test_audit_has_sha256(self) -> None:
        audit = self._audit([])
        self.assertIn("audit_sha256", audit)
        sha = audit["audit_sha256"]
        self.assertIsInstance(sha, str)
        self.assertTrue(sha.startswith("sha256:"), sha)
        self.assertEqual(len(sha), 71)  # "sha256:" (7) + 64 hex chars

    def test_general_effect_ack_done_always_false_in_audit(self) -> None:
        audit = self._audit([])
        self.assertIs(audit["general_effect_ack_done"], False)

    def test_external_effect_always_none_in_audit(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["external_effect"], "NONE")

    def test_transport_ack_is_not_effect_ack_in_audit(self) -> None:
        audit = self._audit([])
        self.assertIs(audit["transport_ack_is_effect_ack"], False)


class ContractAndStandardLoadTests(unittest.TestCase):
    """Verify that the declared artefacts are loadable and structurally valid."""

    def test_load_contract_succeeds(self) -> None:
        contract = sysverify.load_contract()
        self.assertEqual(contract["schema"], "qikvrt_real_mesh_contract_v1")
        self.assertEqual(contract["mesh_id"], "QIKVRT_REAL_MULTI_PAIR_MESH_V1")

    def test_load_reflexive_standard_succeeds(self) -> None:
        std = sysverify.load_reflexive_standard()
        self.assertIn("id", std)
        self.assertIn("status", std)
        self.assertIn("mandatory_correction_layers", std)
        self.assertIn("TESTS", std["mandatory_correction_layers"])

    def test_contract_minimum_topology_is_present(self) -> None:
        contract = sysverify.load_contract()
        topo = contract["minimum_topology"]
        self.assertGreaterEqual(topo["pair_count"], 2)
        self.assertGreaterEqual(topo["node_process_count"], 4)
        self.assertTrue(topo["redundant_routes_required"])

    def test_contract_effect_boundary_forbids_general_effect_ack(self) -> None:
        contract = sysverify.load_contract()
        self.assertFalse(contract["effect_boundary"]["general_effect_ack_done"])

    def test_contract_transport_scope_is_loopback_only(self) -> None:
        contract = sysverify.load_contract()
        self.assertEqual(
            contract["transport"]["network_scope"],
            "LOOPBACK_TCP_ONLY",
        )


class ReflexiveNetworkSystemTest(unittest.TestCase):
    """End-to-end system test: execute real TCP mesh, verify, audit."""

    def test_real_tcp_mesh_passes_all_contract_checks(self) -> None:
        """Execute four real TCP node processes and verify the receipt reflexively."""
        with tempfile.TemporaryDirectory(prefix="qikvrt-sysverify-") as tmp:
            workdir = pathlib.Path(tmp)
            receipt, contract, findings = sysverify.run_and_verify(
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
                workdir=workdir,
            )
        self.assertEqual(
            findings,
            [],
            f"Reflexive verification found {len(findings)} finding(s): {findings}",
        )
        self.assertEqual(receipt["pair_count"], 2)
        self.assertEqual(receipt["node_process_count"], 4)
        self.assertIs(receipt["completion_claims"]["general_effect_ack_done"], False)
        self.assertIs(receipt["completion_claims"]["PASS"], False)
        self.assertEqual(receipt["external_effect"], "NONE")

    def test_audit_receipt_is_well_formed_after_real_execution(self) -> None:
        """The audit receipt produced after real execution must be self-consistent."""
        contract = sysverify.load_contract()
        reflexive_standard = sysverify.load_reflexive_standard()

        with tempfile.TemporaryDirectory(prefix="qikvrt-sysverify-") as tmp:
            workdir = pathlib.Path(tmp)
            receipt, _contract, findings = sysverify.run_and_verify(
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
                workdir=workdir,
            )

        audit = sysverify.build_audit_receipt(
            receipt_path=None,
            receipt=receipt,
            contract=contract,
            findings=findings,
            reflexive_standard=reflexive_standard,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["finding_count"], 0)
        self.assertIs(audit["general_effect_ack_done"], False)
        self.assertEqual(audit["external_effect"], "NONE")
        self.assertTrue(audit["bounded_loopback_effect_ack_scope_confirmed"])
        # Verify the audit's own SHA-256
        stored = audit["audit_sha256"]
        body = {k: v for k, v in audit.items() if k != "audit_sha256"}
        self.assertEqual(stored, sysverify.canonical_sha256(body))


if __name__ == "__main__":
    import unittest

    unittest.main()
