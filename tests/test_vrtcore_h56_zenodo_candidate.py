# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed contracts for the H5/H6 Zenodo-v2 descendants."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_vrtcore_zenodo_candidate.py"
HEAD = "c5d4a3b5ae10cf72845b1839c6075cdd2711f315"
TREE = "6f909892ed1c33ada25010c50d06420278dc55b1"
RUN_ID = 30747218720
JOB_ID = 91494748519
LOG_SHA256 = "1ce2d54109d65210a6ea92d49912af185322e2dc76239e99bc439c8a04a79a3b"
PROFILES = {
    "h5": ("docs/publications/2026-08-02-vrtcore-smg-h5", "release/vrtcore-smg-h5-zenodo-v2", "qikvrt-vrtcore-smg-h5-v1", 18, 32),
    "h6": ("docs/publications/2026-08-02-vrtcore-virtual-sphere-h6", "release/vrtcore-virtual-sphere-h6-zenodo-v2", "qikvrt-vrtcore-virtual-sphere-h6-v1", 15, 55),
}
GENERATED = {
    "BOUNDARY_TEST_REPORT.json", "CHANGE_NOTICE.md", "CLAIM_MATRIX_V2.json",
    "KERNEL_RECEIPT.json", "MACHINE_PROOF_BUNDLE.json",
    "PREPUBLICATION_RETURN_RECEIPT.json", "ZENODO_FILESET.md",
    "ZENODO_LICENSE_NOTICE.md", "ZENODO_METADATA.json", "ZENODO_SHA256SUMS",
}

def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

class H56ZenodoCandidateTests(unittest.TestCase):
    def test_one_parameterized_pipeline_and_deterministic_envelopes(self) -> None:
        text = TOOL.read_text(encoding="utf-8")
        self.assertIn('choices=("relational", "h5", "h6")', text)
        self.assertFalse((ROOT / "tools/qikvrt_h5_zenodo_candidate.py").exists())
        self.assertFalse((ROOT / "tools/qikvrt_h6_zenodo_candidate.py").exists())
        for name, (source_rel, envelope_rel, _pid, _count, _theorems) in PROFILES.items():
            source, envelope = ROOT / source_rel, ROOT / envelope_rel
            self.assertEqual({p.name for p in envelope.iterdir() if p.is_file()}, GENERATED)
            self.assertFalse(GENERATED & {p.name for p in source.iterdir() if p.is_file()})
            run = subprocess.run(
                [sys.executable, "-B", str(TOOL), "return", "--profile", name, "--check"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("PASS verified", run.stdout)

    def test_projection_kernel_and_boundary_are_exact_head_bound(self) -> None:
        for _name, (source_rel, envelope_rel, pid, count, theorems) in PROFILES.items():
            source, envelope = ROOT / source_rel, ROOT / envelope_rel
            original, projection = load(source / "CLAIM_MATRIX.json"), load(envelope / "CLAIM_MATRIX_V2.json")
            self.assertEqual(projection["publication_id"], pid)
            self.assertEqual(projection["claim_count"], count)
            source_ids = {c["id"] for c in original["claims"]}
            projected_ids = {c["claim_id"] for c in projection["claims"]}
            self.assertEqual(source_ids, set(projection["source_projection_map"]))
            self.assertEqual(
                projected_ids,
                {item for items in projection["source_projection_map"].values() for item in items},
            )
            self.assertTrue(projection["completion_claims"]["source_to_projection_complete"])
            mapped = projection["source_projection_map"]
            split_id = "H5-C04" if pid.endswith("h5-v1") else "H6-C07"
            self.assertEqual(len(mapped[split_id]), 2)
            self.assertTrue(all(
                len(targets) == 1
                for source_id, targets in mapped.items()
                if source_id != split_id
            ))
            flattened = [target for targets in mapped.values() for target in targets]
            self.assertEqual(len(flattened), len(set(flattened)))
            ci = projection["exact_head_ci"]
            self.assertEqual((ci["expected_head"], ci["expected_tree"], ci["state"]), (HEAD, TREE, "SUCCESS"))
            self.assertEqual(ci["terminal_evidence"]["run_id"], RUN_ID)
            self.assertEqual(ci["terminal_evidence"]["decoded_log_sha256"], LOG_SHA256)
            formal = [c for c in projection["claims"] if c["source_kind"] == "formal-proved"]
            self.assertEqual(len(formal), 6)
            self.assertTrue(all(c["classification"] == "FORMAL_PROVED" and c["status"] == "PROVED" for c in formal))
            self.assertTrue(all(c["proof_refs"] for c in formal))
            kernel = load(envelope / "KERNEL_RECEIPT.json")
            self.assertEqual(kernel["state"], "KERNEL_VERIFIED")
            self.assertEqual(kernel["theorem_count"], theorems)
            self.assertEqual(kernel["workflow"]["expected_sha"], HEAD)
            self.assertTrue(kernel["workflow"]["exact_head_bound"])
            self.assertEqual(kernel["workflow"]["run_id"], RUN_ID)
            self.assertEqual(kernel["workflow"]["job_id"], JOB_ID)
            self.assertEqual(kernel["workflow"]["decoded_log"]["sha256"], LOG_SHA256)
            self.assertEqual(kernel["workflow"]["evidence_role"], "HOSTED_AUTOMATED_EXACT_HEAD_REEXECUTION_ONLY")
            self.assertNotIn("reviewer", kernel["workflow"])
            self.assertNotIn("organization", kernel["workflow"])
            self.assertEqual(kernel["workflow"]["poppler_step_conclusion"], "success")
            self.assertEqual(kernel["workflow"]["observed_profile_result"]["theorems"], f"{theorems}/{theorems}")
            self.assertFalse(kernel["epistemic_boundary"]["ci_log_used_as_formal_proof_source"])
            report = load(envelope / "BOUNDARY_TEST_REPORT.json")
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["source_binding"]["commit"], HEAD)
            self.assertEqual(report["source_binding"]["tree"], TREE)
            self.assertEqual(report["boundaries"]["physical_closure"], "OPEN")
            self.assertEqual(report["boundaries"]["physical_big_bang_identity"], "NOT_CLAIMED")
            self.assertEqual(report["boundaries"]["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertEqual(report["boundaries"]["automated_exact_head_reexecution"], "GITHUB_ACTIONS_SUCCESS")
            self.assertEqual(report["boundaries"]["independent_external_reproduction"], "OPEN")
            self.assertNotIn("independent_exact_head_reproduction", report["boundaries"])
            self.assertEqual(report["boundaries"]["github_source_commit_already_observed"], HEAD)
            self.assertFalse(report["boundaries"]["github_mutation_by_envelope_materialization"])
            self.assertFalse(report["boundaries"]["zenodo_mutation_by_envelope_materialization"])

    def test_v2_bundle_return_fileset_and_mixed_license(self) -> None:
        sys.path.insert(0, str(ROOT / "tools"))
        import qikvrt_zenodo_machine_proof as proof
        for _name, (_source_rel, envelope_rel, _pid, _count, _theorems) in PROFILES.items():
            envelope = ROOT / envelope_rel
            receipt = load(envelope / "PREPUBLICATION_RETURN_RECEIPT.json")
            self.assertEqual(receipt["schema"], "qikvrt_prepublication_return_receipt_v2")
            self.assertFalse(receipt["content_changed"])
            self.assertEqual(receipt["changed_claim_ids"], [])
            self.assertEqual(receipt["return"]["returned_at"], "2026-08-02T12:09:04Z")
            self.assertEqual(
                receipt["return"]["return_channel"],
                "GitHub draft PR #323 exact-head source candidate at " + HEAD,
            )
            bundle_path, bundle = envelope / "MACHINE_PROOF_BUNDLE.json", load(envelope / "MACHINE_PROOF_BUNDLE.json")
            uploads = [*(x["path"] for x in bundle["candidate"]["files"]), *(x["path"] for x in bundle["artifacts"]), bundle_path.relative_to(ROOT).as_posix()]
            result = proof.validate_bundle(ROOT, bundle_path, upload_paths=uploads)
            self.assertTrue(result["machine_proof_complete"])
            formal = [c for c in bundle["claims"] if c["classification"] == "FORMAL_PROVED"]
            self.assertEqual(len(formal), 6)
            self.assertTrue(all(c["proof_refs"] for c in formal))
            open_claims = [c for c in bundle["claims"] if c["classification"] == "OPEN"]
            self.assertTrue(open_claims)
            metadata = load(envelope / "ZENODO_METADATA.json")
            self.assertEqual(metadata["license"], "other-open")
            citation = (ROOT / _source_rel / "CITATION.cff").read_text(encoding="utf-8")
            citation_version = re.search(r'^version:\s*"([^"]+)"$', citation, re.MULTILINE)
            citation_type = re.search(r'^type:\s*([A-Za-z0-9_-]+)$', citation, re.MULTILINE)
            self.assertIsNotNone(citation_version)
            self.assertIsNotNone(citation_type)
            self.assertEqual(metadata["version"], citation_version.group(1))
            if citation_type.group(1) == "software":
                self.assertEqual(metadata["upload_type"], "software")
                self.assertNotIn("publication_type", metadata)
            else:
                self.assertEqual(metadata["upload_type"], "publication")
                self.assertEqual(metadata["publication_type"], "workingpaper")
            self.assertIn("not independent review", metadata["notes"])
            license_text = (envelope / "ZENODO_LICENSE_NOTICE.md").read_text(encoding="utf-8")
            self.assertIn("PolyForm-Noncommercial-1.0.0", license_text)
            self.assertIn("CC-BY-NC-ND-4.0", license_text)
            self.assertIn("MACHINE_PROOF_BUNDLE.json", (envelope / "ZENODO_FILESET.md").read_text(encoding="utf-8"))
            change_notice = (envelope / "CHANGE_NOTICE.md").read_text(encoding="utf-8")
            self.assertIn("content_changed=false", change_notice)
            if _pid.endswith("h5-v1"):
                self.assertIn("H5-C04-RESIDUAL", change_notice)
                self.assertIn("SOURCE_BOUND", change_notice)
            else:
                self.assertIn("H6-C07-RESIDUAL", change_notice)
                self.assertIn("`OPEN`", change_notice)

    def test_real_reference_fragments_and_conservative_projection(self) -> None:
        expected_empirical = {
            "h5": {"SRC-ATLAS-2012", "SRC-CMS-2012", "SRC-LIGO-GW150914"},
            "h6": {"SRC-H6-RECEIPT"},
        }
        expected_source_bound = {
            "h5": {"SRC-CERN-SM", "SRC-DONOGHUE-1994"},
            "h6": {
                "qikvrt-h6-virtual-sphere-manifest/1.0",
                "MANIFEST.json",
                "qikvrt-h6-virtual-sphere-local-kernel-receipt/1.0",
            },
        }
        for name, (_source_rel, envelope_rel, _pid, _count, _theorems) in PROFILES.items():
            projection = load(ROOT / envelope_rel / "CLAIM_MATRIX_V2.json")
            by_id = {claim["claim_id"]: claim for claim in projection["claims"]}
            empirical_id = "H5-C07" if name == "h5" else "H6-C07"
            source_id = "H5-C08" if name == "h5" else "H6-C08"
            self.assertEqual(set(by_id[empirical_id]["sources"]), expected_empirical[name])
            self.assertEqual(set(by_id[source_id]["sources"]), expected_source_bound[name])
        h5 = load(ROOT / PROFILES["h5"][1] / "CLAIM_MATRIX_V2.json")
        h5_c04 = next(c for c in h5["claims"] if c["claim_id"] == "H5-C04")
        self.assertEqual(h5_c04["projection_relation"], "CONSERVATIVE_SUBCLAIM_OF_SOURCE")
        self.assertIn("ten bridge witnesses", h5_c04["statement"])
        self.assertNotIn("all twelve", h5_c04["statement"])
        self.assertEqual(
            h5["source_projection_map"]["H5-C04"],
            ["H5-C04", "H5-C04-RESIDUAL"],
        )
        h5_residual = next(c for c in h5["claims"] if c["claim_id"] == "H5-C04-RESIDUAL")
        self.assertEqual(h5_residual["classification"], "SOURCE_BOUND")
        self.assertIn("planckNormalForm", h5_residual["statement"])
        self.assertEqual(h5_residual["projection_relation"], "EXPLICIT_RESIDUAL_OF_SOURCE")
        h6 = load(ROOT / PROFILES["h6"][1] / "CLAIM_MATRIX_V2.json")
        h6_c07 = next(c for c in h6["claims"] if c["claim_id"] == "H6-C07")
        self.assertEqual(h6_c07["projection_relation"], "CONSERVATIVE_SUBCLAIM_OF_SOURCE")
        self.assertIn("receipt-bound H6 local execution", h6_c07["statement"])
        self.assertNotIn("Finite computers", h6_c07["statement"])
        self.assertEqual(
            h6["source_projection_map"]["H6-C07"],
            ["H6-C07", "H6-C07-RESIDUAL"],
        )
        h6_residual = next(c for c in h6["claims"] if c["claim_id"] == "H6-C07-RESIDUAL")
        self.assertEqual((h6_residual["classification"], h6_residual["status"]), ("OPEN", "OPEN"))
        self.assertIn("remains open", h6_residual["statement"])
        h6_o03 = next(c for c in h6["claims"] if c["claim_id"] == "H6-O03")
        self.assertEqual((h6_o03["classification"], h6_o03["status"]), ("OPEN", "OPEN"))

    def test_no_authorization_publish_request_workflow_or_effect_receipt(self) -> None:
        forbidden = {"OWNER_ZENODO_AUTHORIZATION.json", "publish-request.json", "zenodo-publication.json"}
        for _name, (_source_rel, envelope_rel, _pid, _count, _theorems) in PROFILES.items():
            envelope = ROOT / envelope_rel
            self.assertTrue(all(not (envelope / name).exists() for name in forbidden))
        self.assertEqual(list(ROOT.glob(".github/workflows/*h56*zenodo*")), [])

    def test_future_authorization_inputs_are_exact(self) -> None:
        for _name, (_source_rel, envelope_rel, pid, _count, _theorems) in PROFILES.items():
            envelope = ROOT / envelope_rel
            ret = hashlib.sha256((envelope / "PREPUBLICATION_RETURN_RECEIPT.json").read_bytes()).hexdigest()
            metadata = load(envelope / "ZENODO_METADATA.json")
            meta = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            machine = hashlib.sha256((envelope / "MACHINE_PROOF_BUNDLE.json").read_bytes()).hexdigest()
            line = f"AUTHORIZE_EXACT_UPLOAD authorization_id=<FRESH_ID> publication_id={pid} return_sha256={ret} metadata_sha256={meta} machine_proof_sha256={machine}"
            self.assertIn("<FRESH_ID>", line)
            self.assertFalse((envelope / "OWNER_ZENODO_AUTHORIZATION.json").exists())

if __name__ == "__main__":
    unittest.main()
