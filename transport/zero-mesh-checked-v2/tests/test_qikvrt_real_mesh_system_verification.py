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
import shutil
import contextlib
import io
from unittest import mock

from tools import qikvrt_real_mesh as mesh
from tools import qikvrt_real_mesh_system_verification as sysverify

SOURCE_HEAD = "a" * 40
SOURCE_TREE = "b" * 40


_FIXTURE: dict | None = None
_FIXTURE_DIR: pathlib.Path | None = None


def _minimal_receipt(*, overrides: dict | None = None) -> dict:
    """Real loopback execution with explicit synthetic source IDs for tests only."""
    global _FIXTURE, _FIXTURE_DIR
    if _FIXTURE is None:
        tmp = tempfile.TemporaryDirectory(prefix="qikvrt-mesh-fixture-")
        unittest.addModuleCleanup(tmp.cleanup)
        _FIXTURE_DIR = pathlib.Path(tmp.name)
        _FIXTURE = mesh.run_demo(_FIXTURE_DIR, source_head=SOURCE_HEAD, source_tree=SOURCE_TREE)
    base = copy.deepcopy(_FIXTURE)
    if overrides:
        base.update(overrides)
    _rehash(base)
    return base


def _rehash(receipt: dict) -> None:
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = mesh.canonical_sha256(receipt)


def _verify(receipt: object, contract: dict, **kwargs) -> list[str]:
    _minimal_receipt()
    defaults = dict(expected_head=SOURCE_HEAD, expected_tree=SOURCE_TREE,
                    ledger_dir=_FIXTURE_DIR / "ledgers")
    defaults.update(kwargs)
    return sysverify.verify_receipt(receipt, contract, **defaults)


class VerifyReceiptPureContractTests(unittest.TestCase):
    """Pure-contract tests: verify_receipt against the declared specification."""

    def setUp(self) -> None:
        self.contract = sysverify.load_contract()

    def test_conformant_receipt_has_no_findings(self) -> None:
        r = _minimal_receipt()
        findings = _verify(r, self.contract)
        self.assertEqual(findings, [])

    def test_wrong_schema_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"schema": "wrong_schema"})
        findings = _verify(r, self.contract)
        self.assertTrue(any("schema" in f for f in findings), findings)

    def test_wrong_mesh_id_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"mesh_id": "WRONG_MESH"})
        findings = _verify(r, self.contract)
        self.assertTrue(any("mesh_id" in f for f in findings), findings)

    def test_insufficient_pair_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"pair_count": 1})
        findings = _verify(r, self.contract)
        self.assertTrue(any("pair_count" in f for f in findings), findings)

    def test_insufficient_node_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"node_process_count": 2})
        findings = _verify(r, self.contract)
        self.assertTrue(any("node_process_count" in f for f in findings), findings)

    def test_non_redundant_path_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"redundant_path_observed": False})
        findings = _verify(r, self.contract)
        self.assertTrue(any("redundant" in f for f in findings), findings)

    def test_wrong_network_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"network_scope": "PUBLIC_INTERNET"})
        findings = _verify(r, self.contract)
        self.assertTrue(any("network_scope" in f for f in findings), findings)

    def test_restart_replay_failure_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["restart_replay"]["same_terminal_receipt"] = False
        findings = _verify(r, self.contract)
        self.assertTrue(any("same_terminal_receipt" in f for f in findings), findings)

    def test_false_general_effect_ack_done_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["general_effect_ack_done"] = True
        findings = _verify(r, self.contract)
        self.assertTrue(
            any("general_effect_ack_done" in f for f in findings), findings
        )

    def test_false_pass_claim_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["PASS"] = True
        findings = _verify(r, self.contract)
        self.assertTrue(any("PASS" in f for f in findings), findings)

    def test_wrong_effect_ack_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"effect_ack_scope": "GENERAL"})
        findings = _verify(r, self.contract)
        self.assertTrue(any("effect_ack_scope" in f for f in findings), findings)

    def test_missing_routes_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"routes": []})
        findings = _verify(r, self.contract)
        self.assertTrue(any("route" in f or "path" in f for f in findings), findings)

    def test_receipt_sha256_mismatch_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["receipt_sha256"] = "0" * 64
        findings = _verify(r, self.contract)
        self.assertTrue(any("sha256" in f for f in findings), findings)

    def test_receipt_sha256_match_is_not_a_finding(self) -> None:
        r = _minimal_receipt()
        _rehash(r)
        findings = _verify(r, self.contract)
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
            expected_head=SOURCE_HEAD, expected_tree=SOURCE_TREE,
            ledger_dir=_FIXTURE_DIR / "ledgers",
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
                expected_head=SOURCE_HEAD, expected_tree=SOURCE_TREE,
                ledger_dir=workdir / "ledgers",
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


class AdversarialWitnessTests(unittest.TestCase):
    def setUp(self):
        self.receipt = _minimal_receipt()
        self.contract = sysverify.load_contract()

    def test_native_counterexamples_are_rejected_even_after_rehash(self):
        cases = {
            "missing_receipt_hash": lambda r: r.pop("receipt_sha256"),
            "missing_source_head": lambda r: r.pop("source_head"),
            "malformed_source_tree": lambda r: r.update(source_tree="not-a-tree"),
            "missing_topology": lambda r: r.pop("topology"),
            "duplicate_route": lambda r: r["routes"].__setitem__(1, copy.deepcopy(r["routes"][0])),
            "missing_hop_readbacks": lambda r: r["routes"][0]["observation"].update(node_observations=[]),
            "blocked_ack": lambda r: r["routes"][0]["bounded_effect_ack"].update(state="EFFECT_ACK_BLOCK", ordinary_release=False),
            "unobserved_restart": lambda r: r["restart_replay"].update(observed=False),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                r = copy.deepcopy(self.receipt); mutate(r)
                if name != "missing_receipt_hash":
                    _rehash(r)
                self.assertTrue(_verify(r,self.contract))

    def test_independent_expected_subject_is_mandatory(self):
        for kwargs in ({"expected_head":None}, {"expected_tree":None},
                       {"expected_head":"c"*40}, {"expected_tree":"d"*40},
                       {"expected_head":SOURCE_HEAD.upper()}, {"ledger_dir":None}):
            with self.subTest(kwargs=kwargs):
                self.assertTrue(_verify(self.receipt,self.contract,**kwargs))
        self.assertTrue(sysverify.verify_receipt(self.receipt,self.contract))

    def test_top_level_relabel_does_not_transfer_predecessor_evidence(self):
        r = self.receipt
        r["source_head"] = "c"*40
        _rehash(r)
        self.assertTrue(_verify(r,self.contract,expected_head="c"*40))
        # Even rehashed origin envelopes cannot rewrite independently read hop ledgers.
        for route in r["routes"]:
            route["message"]["payload"]["input_binding"]["source_head"] = "c"*40
            route["message"]["payload_sha256"] = mesh.canonical_sha256(route["message"]["payload"])
            route["observation"]["payload_sha256"] = route["message"]["payload_sha256"]
        _rehash(r)
        self.assertTrue(_verify(r,self.contract,expected_head="c"*40))

    def test_malformed_shapes_fail_closed_without_traceback(self):
        for value in (None, [], "receipt", 7, True):
            self.assertTrue(_verify(value,self.contract))
        for key in ("topology", "routes", "restart_replay", "completion_claims", "pair_count", "node_process_count"):
            for value in (None, "bad", [], True):
                with self.subTest(key=key,value=value):
                    r=copy.deepcopy(self.receipt);r[key]=value;_rehash(r)
                    self.assertTrue(_verify(r,self.contract))
        for key in ("message", "observation", "bounded_effect_ack"):
            r=copy.deepcopy(self.receipt);r["routes"][0][key]=None;_rehash(r)
            self.assertTrue(_verify(r,self.contract))

    def test_inconsistent_witness_fields_cannot_be_hidden_by_rehash(self):
        cases = [
            lambda r:r.update(node_process_count=5),
            lambda r:r.update(pair_count=3),
            lambda r:r.update(topology_sha256="sha256:"+"0"*64),
            lambda r:r.update(pair_states=[]),
            lambda r:r["topology"]["nodes"][0].update(host="8.8.8.8"),
            lambda r:r["routes"][0]["observation"].update(complete_route_reobserved=False),
            lambda r:r["routes"][0]["observation"].update(hop_receipt_sha256s=[]),
            lambda r:r["routes"][0]["observation"]["node_observations"][0].update(ledger_record_count=True),
            lambda r:r["routes"][0]["observation"]["node_observations"][0].update(ledger_record_count=999),
            lambda r:r["routes"][0]["observation"]["node_observations"][0].update(ledger_tip_sha256="sha256:"+"0"*64),
            lambda r:r["routes"][0]["observation"]["node_observations"][0].update(root_tree_sha="c"*40),
            lambda r:r["routes"][0]["bounded_effect_ack"]["responsibility_protocol"].update(protocol_hash="sha256:"+"0"*64),
            lambda r:r["restart_replay"].update(record_count_after=3),
            lambda r:r["restart_replay"].update(terminal_sha256_after="sha256:"+"0"*64),
            lambda r:r["restart_replay"].update(processes_before={}),
            lambda r:r["restart_replay"].update(processes_after=r["restart_replay"]["processes_before"]),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(index=index):
                r=copy.deepcopy(self.receipt);mutate(r);_rehash(r)
                self.assertTrue(_verify(r,self.contract))

    def test_forged_protocol_with_valid_intrinsic_hash_still_needs_hop_binding(self):
        from src.qikvrt_effect_ack import ResponsibilityProtocol,compute_protocol_hash
        from dataclasses import replace
        raw=self.receipt["routes"][0]["bounded_effect_ack"]["responsibility_protocol"]
        p=ResponsibilityProtocol.from_dict(raw)
        p=replace(p,input_id="other-subject")
        p=replace(p,protocol_hash=compute_protocol_hash(p))
        self.receipt["routes"][0]["bounded_effect_ack"]["responsibility_protocol"]=p.to_dict()
        _rehash(self.receipt)
        self.assertTrue(_verify(self.receipt,self.contract))

    def test_missing_symlink_and_tampered_ledger_are_rejected_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=pathlib.Path(tmp)/"ledgers"
            self.assertTrue(_verify(self.receipt,self.contract,ledger_dir=dest))
            self.assertFalse(dest.exists())
            for kind in ("missing","symlink","truncated","hash","duplicate_key"):
                with self.subTest(kind=kind):
                    if dest.exists():shutil.rmtree(dest)
                    shutil.copytree(_FIXTURE_DIR/"ledgers",dest)
                    path=sorted(dest.glob("*.jsonl"))[0];raw=path.read_bytes()
                    if kind=="missing":path.unlink()
                    elif kind=="symlink":path.unlink();path.symlink_to(_FIXTURE_DIR/"ledgers"/path.name)
                    elif kind=="truncated":path.write_bytes(raw[:-1])
                    elif kind=="hash":path.write_bytes(raw.replace(b'ACCEPTED',b'REJECTED',1))
                    else:path.write_bytes(raw.replace(b'{',b'{"schema":"duplicate",',1))
                    self.assertTrue(_verify(self.receipt,self.contract,ledger_dir=dest))

    def test_rehashed_ledger_cannot_launder_premature_transport_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=pathlib.Path(tmp)/"ledgers";shutil.copytree(_FIXTURE_DIR/"ledgers",dest)
            nid=self.receipt["routes"][0]["message"]["route"][0]
            path=dest/f"{nid}.jsonl"
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            rows[1]["response"]["ordinary_release"]=True
            previous=None
            for row in rows:
                row["previous_record_sha256"]=previous;row.pop("record_sha256")
                row["record_sha256"]=mesh.canonical_sha256(row);previous=row["record_sha256"]
            path.write_text("".join(json.dumps(row)+"\n" for row in rows))
            for route in self.receipt["routes"]:
                for obs in route["observation"]["node_observations"]:
                    if obs["node_id"]==nid:obs["ledger_tip_sha256"]=rows[obs["ledger_record_count"]-1]["record_sha256"]
            _rehash(self.receipt)
            self.assertTrue(_verify(self.receipt,self.contract,ledger_dir=dest))

    def test_audit_cannot_launder_invalid_receipt_with_empty_findings(self):
        self.receipt.pop("receipt_sha256")
        a=sysverify.build_audit_receipt(receipt_path=None,receipt=self.receipt,
            contract=self.contract, findings=[],reflexive_standard=sysverify.load_reflexive_standard(),
            expected_head=SOURCE_HEAD,expected_tree=SOURCE_TREE,ledger_dir=_FIXTURE_DIR/"ledgers")
        self.assertEqual(a["status"],"BLOCK")
        self.assertFalse(a["bounded_loopback_effect_ack_scope_confirmed"])
        self.assertFalse(a["live_platform_and_repository_mesh_verified"])

    def test_cli_requires_independent_bindings_and_rejects_duplicate_json(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                sysverify.parse_args(["verify","--receipt","x.json"])
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/"receipt.json"
            path.write_text('{"schema":"one","schema":"two"}')
            with contextlib.redirect_stderr(io.StringIO()):
                result=sysverify.main(["verify","--receipt",str(path),"--expected-head",SOURCE_HEAD,
                    "--expected-tree",SOURCE_TREE,"--ledger-dir",str(_FIXTURE_DIR/"ledgers")])
            self.assertEqual(result,2)

    def test_complete_hidden_receipt_and_ledger_exports_are_explicit(self):
        for name, directory in (
            ("qikvrt_real_mesh.yml", ".qikvrt/real-mesh"),
            ("qikvrt_real_mesh_system_verification.yml", ".qikvrt/real-mesh-sysverify"),
        ):
            with self.subTest(workflow=name):
                text=(sysverify.ROOT/".github/workflows"/name).read_text()
                upload=text.split("uses: actions/upload-artifact@",1)[1]
                self.assertIn("include-hidden-files: true",upload)
                self.assertIn("path: "+directory+"\n",upload)
                self.assertIn("if-no-files-found: error",upload)
                self.assertNotIn("path: .qikvrt\n",upload)
                self.assertIn("--ledger-dir",text)


    def test_cli_run_does_not_accept_arbitrary_source_labels(self):
        with mock.patch.object(sysverify.subprocess,"check_output",return_value="c"*40+"\n"+"d"*40+"\n"), \
             mock.patch.object(sysverify,"run_and_verify") as run, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sysverify.main(["run","--source-head",SOURCE_HEAD,"--source-tree",SOURCE_TREE]),2)
            run.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
