# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contracts for the Round Trip Zenodo bundle freeze."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_round_trip_zenodo_bundle_freeze.py"
RELEASE = ROOT / "release/round-trip-canonical-publication-zenodo-v1"
WORK_UNIT = ROOT / "state/work_units/ROUND_TRIP_ZENODO_BUNDLE_FREEZE_V1.json"


class RoundTripZenodoBundleFreezeTests(unittest.TestCase):
    def load(self, path: pathlib.Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_existing_v2_machinery_is_reused_without_parallel_publisher(self) -> None:
        text = TOOL.read_text(encoding="utf-8")
        self.assertIn("qikvrt_zenodo_machine_proof", text)
        self.assertIn("qikvrt_zenodo_publish", text)
        self.assertNotIn("urllib.request", text)
        self.assertNotIn("requests.", text)
        self.assertFalse((ROOT / "tools/qikvrt_round_trip_zenodo_publish.py").exists())

    def test_frozen_primary_files_and_effect_boundary(self) -> None:
        work = self.load(WORK_UNIT)
        receipt = self.load(RELEASE / "BUNDLE_FREEZE_RECEIPT.json")
        self.assertEqual(
            [item["sha256"] for item in receipt["primary_files"]],
            [
                "dc58e50161b22826152dd251db836f06f85235a470e0253aeefa1b0a380787fe",
                "e5fd9c53a0bf6c84471d9b26d0c3c06019977aa6b2367913006fa9560a3c948f",
            ],
        )
        self.assertEqual(work["source_base"]["authority_commit"], "12842e8df99553260774d53517522b2b5539c8a8")
        self.assertEqual(work["source_base"]["mirror_commit"], "c52b324914978dc5d6d80251260ce55f396909f7")
        self.assertTrue(all(value is False for value in receipt["effect_boundary"].values()))
        self.assertEqual(receipt["completion_claims"], {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False})

    def test_retrospective_and_formal_inventories_are_complete_for_scope(self) -> None:
        retrospective = self.load(RELEASE / "RETROSPECTIVE_SOURCE_CONSTITUENTS.json")
        formal = self.load(RELEASE / "PROMOTED_FORMAL_SOURCE_BINDINGS.json")
        receipts = self.load(RELEASE / "PROMOTED_FORMAL_KERNEL_RECEIPTS.json")
        claims = self.load(RELEASE / "CLAIM_MATRIX.json")
        self.assertEqual(retrospective["constituent_count"], 34)
        self.assertEqual(retrospective["claim_matrix_count"], 19)
        self.assertEqual(retrospective["subject_receipt_count"], 7)
        self.assertEqual(retrospective["content_change_decision_count"], 6)
        self.assertEqual((retrospective["claims"], retrospective["explicit_open_claims"]), (70439, 1262))
        self.assertEqual(len(formal["bindings"]), 6)
        self.assertEqual(sum(len(item["theorems"]) for item in formal["bindings"]), 99)
        self.assertEqual(len(receipts["receipts"]), 6)
        self.assertTrue(all(item["project_axioms"] == [] for item in receipts["receipts"]))
        self.assertEqual(claims["claim_count"], 12)
        self.assertEqual(sum(c["classification"] == "FORMAL_PROVED" for c in claims["claims"]), 6)
        self.assertEqual(sum(c["classification"] == "OPEN" for c in claims["claims"]), 2)

    def test_metadata_target_and_fileset_are_fail_closed(self) -> None:
        metadata = self.load(RELEASE / "ZENODO_METADATA.json")
        target = self.load(RELEASE / "ZENODO_TARGET_RECORD.json")
        receipt = self.load(RELEASE / "BUNDLE_FREEZE_RECEIPT.json")
        self.assertEqual(metadata["creators"], [{"name": "Lohmann, Ingolf"}])
        self.assertEqual(metadata["license"], "cc-by-nc-nd-4.0")
        self.assertEqual(metadata["language"], "deu")
        self.assertEqual((metadata["upload_type"], metadata["publication_type"]), ("publication", "workingpaper"))
        self.assertEqual(target["mode"], "CREATE_NEW_RECORD")
        self.assertTrue(target["prereserve_doi"])
        self.assertTrue(all(value is False for value in target["effect_boundary"].values()))
        entries = receipt["upload_fileset"]["entries"]
        self.assertEqual(len(entries), 54)
        self.assertEqual([e["name"] for e in entries], sorted(e["name"] for e in entries))
        self.assertEqual(len({e["name"] for e in entries}), 54)
        for forbidden in ("OWNER_ZENODO_AUTHORIZATION.json", "publish-request.json", "zenodo-publication.json"):
            self.assertFalse((RELEASE / forbidden).exists())

    @unittest.skipUnless(
        (ROOT / "tools/qikvrt_zenodo_machine_proof.py").exists()
        and (ROOT / "tools/qikvrt_zenodo_publish.py").exists(),
        "full repository authorities are not present in an overlay-only test",
    )
    def test_full_repository_checker(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--check", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["scope"], "LOCAL_EXACT_BUNDLE_FREEZE_CANDIDATE_ONLY")
        self.assertFalse(result["effect_boundary"]["zenodo_effect_executed"])
        self.assertFalse(result["effect_boundary"]["PASS"])


if __name__ == "__main__":
    unittest.main()
