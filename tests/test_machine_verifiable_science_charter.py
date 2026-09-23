#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations
import hashlib, json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
CHARTER=ROOT/"docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md"; POLICY=ROOT/"policy/QIKVRT_MACHINE_VERIFIABLE_SCIENCE_CHARTER_V1.json"; STATE=ROOT/"state/charter/CHARTER_ADOPTION_V1.json"
CONTEXT=ROOT/"AI_CONTEXT.json"; AI=ROOT/"AI"; README=ROOT/"README.md"
ZENODO=ROOT/"release/machine-verifiable-science/zenodo-publication.json"
EXPECTED_BYTES=10127; EXPECTED_SHA256="7fb4e5c369b079e93ce409e9ca4f6830476a1b6dbd42543273d85164e111a631"; EXPECTED_GIT_BLOB="d6533d9be451f8ac922ef7c11cbf04900fa3066f"; EXPECTED_DOI="10.5281/zenodo.21515074"
ADAPTERS=["AGENTS.md","CLAUDE.md",".github/copilot-instructions.md",".github/instructions/qikvrt-ai-entry.instructions.md",".cursor/rules/qikvrt-ai-entry.mdc",".clinerules",".roo/rules/qikvrt-ai-entry.md",".kiro/steering/qikvrt-ai-entry.md",".amazonq/rules/qikvrt-ai-entry.md",".continue/rules/qikvrt-ai-entry.md",".windsurf/rules/qikvrt-ai-entry.md"]
def git_blob_sha1(data: bytes)->str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii")+data,usedforsecurity=False).hexdigest()
class CharterAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=CHARTER.read_bytes(); cls.policy=json.loads(POLICY.read_text()); cls.state=json.loads(STATE.read_text()); cls.context=json.loads(CONTEXT.read_text()); cls.ai=AI.read_text(); cls.readme=README.read_text()
    def test_identity(self):
        self.assertEqual(len(self.raw),EXPECTED_BYTES); self.assertEqual(hashlib.sha256(self.raw).hexdigest(),EXPECTED_SHA256); self.assertEqual(git_blob_sha1(self.raw),EXPECTED_GIT_BLOB)
    def test_binding(self):
        self.assertEqual(self.policy["canonical_charter"]["sha256"],EXPECTED_SHA256); self.assertEqual(self.policy["public_archive"]["doi"],EXPECTED_DOI); self.assertFalse(self.policy["effect_boundary"]["effect_ack_done_implied"])
        for p in ("docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md","policy/QIKVRT_MACHINE_VERIFIABLE_SCIENCE_CHARTER_V1.json","state/charter/CHARTER_ADOPTION_V1.json"): self.assertIn(p,self.context["required_read_order"]); self.assertIn(p,self.ai)
        self.assertIn("qikvrt-machine-verifiable-science-charter-binding:v1",self.readme)
    def test_mesh_transitivity(self):
        for p in ADAPTERS: self.assertIn("required_read_order",(ROOT/p).read_text(),p)
        self.assertTrue(self.state["mesh"]["current_and_future_conforming_nodes_bound"]); self.assertFalse(self.state["mesh"]["historical_snapshots_rewritten"])
    def test_zenodo_exact(self):
        z=json.loads(ZENODO.read_text()); self.assertEqual(z["state"],"published"); self.assertEqual(z["doi"],EXPECTED_DOI); self.assertEqual(z["record_id"],21515074)
        f=z["files"][0]; self.assertEqual(f["path"],"docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md"); self.assertEqual(f["size"],EXPECTED_BYTES); self.assertEqual(f["sha256"],EXPECTED_SHA256); self.assertEqual(f["git_blob_sha"],EXPECTED_GIT_BLOB)
if __name__=="__main__": unittest.main()
