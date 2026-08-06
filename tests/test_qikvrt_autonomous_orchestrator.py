# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_orchestrator",
    ROOT / "tools/qikvrt_autonomous_orchestrator.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def delegation_fixture() -> dict:
    return {
        "schema": "qikvrt_owner_autonomous_repository_continuation_v2",
        "authorization_scope": {"state": "ACTIVE"},
        "allowed_without_reinteraction": [
            "read_only_repository_and_public_evidence_observation",
            "reviewable_successor_creation",
            "semantic_fingerprint_bound_branch_creation",
            "draft_pull_request_creation_for_allowlisted_repository_internal_repairs",
            "expected_head_bound_promotion_when_all_declared_conditions_hold",
            "append_only_receipt_status_and_work_unit_projection_creation",
        ],
        "not_authorized": [
            "zenodo_create_upload_metadata_mutation_or_publication",
            "ietf_datatracker_submission_resubmission_or_metadata_mutation",
            "github_release_or_tag_creation",
            "force_push_or_history_rewrite",
            "unconditional_automatic_merge_or_unbound_promotion",
        ],
        "promotion_policy": {
            "unconditional_automatic_merge": "FORBIDDEN",
            "expected_head_bound_promotion": "ALLOWED_ONLY_IF",
            "conditions": list(MODULE.PROMOTION_CONDITIONS),
            "requires_existing_repository_bound_promotion_contract": True,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


class AutonomousOrchestratorTests(unittest.TestCase):
    def test_repository_contract_queue_and_promotion_contract_are_valid(self) -> None:
        contract = load("state/autonomy/AUTONOMOUS_ORCHESTRATOR_V2.json")
        queue = load("state/autonomy/WORK_QUEUE_V2.json")
        promotion = load(
            "state/authorization/promotions/AUTONOMOUS_WORK_UNIT_PROMOTION_V2.json"
        )
        delegation = delegation_fixture()
        MODULE.validate_delegation(delegation)
        MODULE.validate_contract(contract, delegation)
        MODULE.validate_promotion_contract(promotion)
        index = MODULE.validate_queue(queue, contract)
        self.assertEqual(len(index), 8)
        self.assertEqual(
            MODULE.select_work_unit(queue, contract)["id"],
            "AUT-QCE-FINALIZE-20260806",
        )

    def test_no_waiting_boundary_is_automatically_selected(self) -> None:
        contract = load("state/autonomy/AUTONOMOUS_ORCHESTRATOR_V2.json")
        queue = load("state/autonomy/WORK_QUEUE_V2.json")
        for unit in queue["work_units"]:
            if unit["state"] == "READY":
                unit["state"] = "DONE"
        self.assertIsNone(MODULE.select_work_unit(queue, contract))
        waiting = {
            unit["state"] for unit in queue["work_units"] if unit["state"].startswith("WAITING_")
        }
        self.assertEqual(
            waiting,
            {
                "WAITING_HUMAN",
                "WAITING_CONFIGURATION",
                "WAITING_EMPIRICAL",
                "WAITING_EXTERNAL_AUTH",
            },
        )

    def test_dependency_order_is_strict_and_deterministic(self) -> None:
        contract = load("state/autonomy/AUTONOMOUS_ORCHESTRATOR_V2.json")
        queue = load("state/autonomy/WORK_QUEUE_V2.json")
        qce = next(unit for unit in queue["work_units"] if unit["id"] == "AUT-QCE-FINALIZE-20260806")
        audio = next(unit for unit in queue["work_units"] if unit["id"] == "AUT-AUDIO-INGEST-20260806")
        qce["state"] = "DONE"
        selected = MODULE.select_work_unit(queue, contract)
        self.assertEqual(selected["id"], audio["id"])
        audio["state"] = "DONE"
        selected = MODULE.select_work_unit(queue, contract)
        self.assertEqual(selected["id"], "AUT-ONTOLOGY-UNIFIED-PROGRAM-20260806")

    def test_dependency_cycle_is_rejected(self) -> None:
        index = {
            "AUT-A": {"dependencies": ["AUT-B"]},
            "AUT-B": {"dependencies": ["AUT-A"]},
        }
        with self.assertRaises(MODULE.OrchestratorBlock):
            MODULE.validate_acyclic(index)

    def test_candidate_branch_binds_work_unit_and_base(self) -> None:
        branch = MODULE.candidate_branch("AUT-QCE-FINALIZE-20260806", "a" * 40)
        self.assertEqual(
            branch,
            "automation/orchestrator-qce-finalize-20260806-aaaaaaaa",
        )
        self.assertNotEqual(
            branch,
            MODULE.candidate_branch("AUT-QCE-FINALIZE-20260806", "b" * 40),
        )

    def test_path_allowlist_is_fail_closed(self) -> None:
        patterns = [
            "docs/publications/example/**",
            "state/autonomy/WORK_QUEUE_V2.json",
        ]
        self.assertTrue(MODULE.path_allowed("docs/publications/example/README.md", patterns))
        self.assertTrue(MODULE.path_allowed("state/autonomy/WORK_QUEUE_V2.json", patterns))
        self.assertFalse(MODULE.path_allowed(".github/workflows/foreign.yml", patterns))
        self.assertFalse(MODULE.path_allowed("../outside", patterns))

    def test_zip_path_traversal_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("../escape.txt", b"no")
            with self.assertRaises(MODULE.OrchestratorBlock):
                MODULE.safe_extract_zip(
                    archive,
                    root / "out",
                    maximum_members=10,
                    maximum_bytes=1000,
                )

    def test_qce_receipt_never_promotes_physical_correspondence(self) -> None:
        receipt = {
            "schema": "qikvrt-qce-kernel-receipt/1.0",
            "state": "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
            "source_binding": {
                "repository": "Goldkelch/qik-vrt",
                "commit": "a" * 40,
                "tree": "b" * 40,
            },
            "workflow_binding": {"run_id": "1", "run_attempt": "1"},
            "kernel_execution": {
                "accepted_theorems": 36,
                "axiom_audit_directives": 36,
                "named_theorems": 36,
                "project_axioms": 0,
                "sorry_or_admit": 0,
                "unsafe_declarations": 0,
            },
            "formal_scope": {
                "finite_model_contract_kernel_accepted": True,
                "physical_closure": False,
                "physical_correspondence_established": False,
            },
        }
        verification = {
            "result": "FORMAL_MODEL_VERIFIED",
            "physical_correspondence": "OPEN_CANDIDATE",
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        }
        MODULE.verify_qce_receipt(
            receipt,
            verification,
            source_head="a" * 40,
            source_tree="b" * 40,
            run_id=1,
            run_attempt=1,
        )
        receipt["formal_scope"]["physical_correspondence_established"] = True
        with self.assertRaises(MODULE.OrchestratorBlock):
            MODULE.verify_qce_receipt(
                receipt,
                verification,
                source_head="a" * 40,
                source_tree="b" * 40,
                run_id=1,
                run_attempt=1,
            )

    def test_audio_normalization_requires_pending_human_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            plain = output_dir / "sample.transcript.txt"
            structured = output_dir / "sample.transcript.json"
            provenance = output_dir / "sample.provenance.json"
            observation = output_dir / "normalization-observation.json"
            receipt = input_dir / "chunk-materialization-receipt.json"
            plain.write_text("rohe ASR", encoding="utf-8")
            structured.write_text(
                json.dumps(
                    {
                        "text": "rohe ASR",
                        "segments": [{"index": 0, "text": "rohe ASR"}],
                    }
                ),
                encoding="utf-8",
            )
            provenance.write_text(
                json.dumps({"input": {"sha256": "d" * 64}}), encoding="utf-8"
            )
            receipt.write_text(
                json.dumps(
                    {
                        "schema": "qikvrt_audio_chunk_materialization_receipt_v1",
                        "repository": "Goldkelch/qik-vrt",
                        "audio_id": "a08",
                        "carrier_sha": "c" * 40,
                        "original": {"sha256": "o" * 64},
                        "derivative": {"sha256": "d" * 64},
                    }
                ),
                encoding="utf-8",
            )
            outputs = []
            for path in (plain, structured, provenance):
                outputs.append(
                    {
                        "filename": path.name,
                        "bytes": path.stat().st_size,
                        "sha256": MODULE.sha256_file(path),
                    }
                )
            observation.write_text(
                json.dumps(
                    {
                        "schema": "qikvrt_audio_normalization_observation_v1",
                        "repository": "Goldkelch/qik-vrt",
                        "audio_id": "a08",
                        "carrier_sha": "c" * 40,
                        "run_id": 7,
                        "original_sha256": "o" * 64,
                        "derivative_sha256": "d" * 64,
                        "automatic_asr": "COMPLETE",
                        "human_acoustic_review": "PENDING",
                        "verbatim_verified": False,
                        "zenodo_mutation": False,
                        "outputs": outputs,
                    }
                ),
                encoding="utf-8",
            )
            expected = {
                "audio_id": "a08",
                "semantic_label": "test",
                "original_sha256": "o" * 64,
                "derivative_sha256": "d" * 64,
            }
            result = MODULE.validate_audio_artifact(
                root,
                expected,
                repository="Goldkelch/qik-vrt",
                run_id=7,
                carrier_sha="c" * 40,
            )
            self.assertFalse(result["verbatim_verified"])
            value = json.loads(observation.read_text())
            value["verbatim_verified"] = True
            observation.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(MODULE.OrchestratorBlock):
                MODULE.validate_audio_artifact(
                    root,
                    expected,
                    repository="Goldkelch/qik-vrt",
                    run_id=7,
                    carrier_sha="c" * 40,
                )

    def test_true_completion_claim_is_rejected(self) -> None:
        with self.assertRaises(MODULE.OrchestratorBlock):
            MODULE.require_false_claims(
                {"PASS": True, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
                "fixture",
            )


if __name__ == "__main__":
    unittest.main()
