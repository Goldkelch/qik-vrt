#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import unittest

from tools import qikvrt_zenodo_machine_proof as proof_gate


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "docs/publications/2026-08-01-scientific-fact-growth-mesh"
RELEASE = ROOT / "release/scientific-fact-growth-mesh-2026-08-01"


class ScientificFactGrowthReleaseTests(unittest.TestCase):
    def test_generated_release_is_at_deterministic_fixpoint(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "tools/qikvrt_prepare_scientific_fact_growth_release.py",
                "--check",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("STATE=current", result.stdout)

    def test_machine_proof_validates_the_exact_upload_set(self) -> None:
        bundle_path = PUBLICATION / "MACHINE_PROOF_BUNDLE.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        upload_paths = [
            *(item["path"] for item in bundle["candidate"]["files"]),
            *(item["path"] for item in bundle["artifacts"]),
            bundle_path.relative_to(ROOT).as_posix(),
        ]
        receipt = proof_gate.validate_bundle(
            ROOT,
            bundle_path,
            upload_paths=upload_paths,
        )
        self.assertEqual(receipt["claim_count"], 30)
        self.assertTrue(receipt["machine_proof_complete"])

    def test_external_effect_candidate_is_fail_closed(self) -> None:
        candidate = json.loads(
            (RELEASE / "ZENODO_DEPOSITION_CANDIDATE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(candidate["state"], "AWAITING_EXACT_OWNER_AUTHORIZATION")
        self.assertFalse(
            candidate["external_effects"]["zenodo_production_upload_performed"]
        )
        self.assertFalse(
            candidate["external_effects"]["ietf_datatracker_submission_performed"]
        )
        metadata_hash = hashlib.sha256(
            json.dumps(
                candidate["metadata"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(candidate["canonical_metadata_sha256"], metadata_hash)
        self.assertFalse(candidate["completion_claims"]["pass"])
        self.assertFalse(candidate["completion_claims"]["final_pass"])
        self.assertFalse(candidate["completion_claims"]["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
