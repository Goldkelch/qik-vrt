#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import re
import sys
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "state/autonomy/PUBLICATION_CANDIDATE_READINESS_OBSERVER_CONTRACT_V1.json"
WORKFLOW_PATH = ROOT / ".github/workflows/qikvrt_publication_candidate_readiness.yml"
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_publication_candidate_readiness",
    ROOT / "tools/qikvrt_publication_candidate_readiness.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


MAIN = "a" * 40
MAIN_TREE = "b" * 40
HEAD = "c" * 40
HEAD_TREE = "d" * 40
PREDECESSOR = "e" * 40
BLOB = "f" * 40


def contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def run(number: int, name: str, *, conclusion: str = "success", job_conclusion: str = "success") -> dict[str, object]:
    return {
        "id": number,
        "name": name,
        "run_number": number,
        "event": "pull_request",
        "head_sha": HEAD,
        "head_branch": "agent/current-main-successor",
        "status": "completed",
        "conclusion": conclusion,
        "jobs": [
            {
                "id": number * 10,
                "name": "verify",
                "status": "completed",
                "conclusion": job_conclusion,
            }
        ],
    }


def snapshot() -> dict[str, object]:
    value = contract()
    all_gates = value["workflow_gates"]["required"] + value["workflow_gates"]["conditionally_not_applicable"]
    inventory = {item["path"]: BLOB for item in all_gates}
    files = [
        {"path": "docs/publications/current.md", "sha": "1" * 40},
        {"path": "state/current.json", "sha": "2" * 40},
    ]
    scope_sha = MODULE.digest(files)
    inventory_sha = MODULE.digest(inventory)
    return {
        "schema": MODULE.SNAPSHOT_SCHEMA,
        "repository": "example/qik-vrt",
        "authority": {"main_head_sha": MAIN, "main_tree_sha": MAIN_TREE},
        "candidate": {
            "number": 42,
            "state": "open",
            "base_ref": "main",
            "base_sha": MAIN,
            "head_ref": "agent/current-main-successor",
            "head_sha": HEAD,
            "head_tree_sha": HEAD_TREE,
            "changed_file_count": len(files),
            "changed_files": files,
            "draft": False,
            "mergeable": True,
        },
        "reobservation": {
            "main_head_sha": MAIN,
            "base_sha": MAIN,
            "head_sha": HEAD,
            "head_tree_sha": HEAD_TREE,
            "scope_sha256": scope_sha,
            "workflow_blob_inventory_sha256": inventory_sha,
            "contract_blob_sha": BLOB,
        },
        "contract_blob_sha": BLOB,
        "workflow_inventories": {"base": inventory, "head": inventory},
        "workflow_runs": [run(index, gate["name"]) for index, gate in enumerate(value["workflow_gates"]["required"], start=1)],
        "reviews": [],
        "review_comment_count": 0,
        "competing_writers": [],
        "external_inputs": {
            target["target"]: {"present": True, "blob_sha": BLOB, "sha256": "3" * 64}
            for target in value["external_boundaries"]
        },
    }


class PublicationCandidateReadinessTests(unittest.TestCase):
    def test_repository_candidate_is_advisory_and_external_boundaries_stay_separate(self) -> None:
        result = MODULE.evaluate(snapshot())
        self.assertEqual(result["state"], "PROMOTE_REPOSITORY_CANDIDATE")
        self.assertIsNone(result["first_blocker"])
        self.assertEqual(result["external_boundaries"]["ZENODO"]["state"], "NOT_AUTHORIZED")
        self.assertEqual(result["external_boundaries"]["ARXIV"]["effect_evidence"], "NOT_OBSERVED_BY_READ_ONLY_OBSERVER")
        self.assertFalse(result["completion_claims"]["EXTERNAL_EFFECT"])

    def test_competing_writer_is_before_draft_or_workflow_followups(self) -> None:
        value = snapshot()
        value["candidate"]["draft"] = True
        value["competing_writers"] = [{"number": 43, "overlap_paths": ["state/current.json"]}]
        result = MODULE.evaluate(value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_OVERLAP")

    def test_declared_branch_gated_skip_is_not_applicable(self) -> None:
        value = snapshot()
        value["workflow_runs"].append(run(100, "QIKVRT Batch-003 subject 172dd public archive probe", conclusion="skipped", job_conclusion="skipped"))
        result = MODULE.evaluate(value)
        gate = next(item for item in result["workflows"]["gates"] if item["name"] == "QIKVRT Batch-003 subject 172dd public archive probe")
        self.assertEqual(gate["state"], "NOT_APPLICABLE")
        self.assertEqual(result["state"], "PROMOTE_REPOSITORY_CANDIDATE")

    def test_unclassified_exact_head_workflow_fails_closed(self) -> None:
        value = snapshot()
        value["workflow_runs"].append(run(100, "unclassified exact-head workflow"))
        result = MODULE.evaluate(value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "UNDECLARED_EXACT_HEAD_WORKFLOW")

    def test_stale_run_is_discarded_and_cannot_satisfy_a_gate(self) -> None:
        value = snapshot()
        required_name = contract()["workflow_gates"]["required"][1]["name"]
        value["workflow_runs"] = [item for item in value["workflow_runs"] if item["name"] != required_name]
        stale = run(200, required_name)
        stale["head_sha"] = PREDECESSOR
        value["workflow_runs"].append(stale)
        result = MODULE.evaluate(value)
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_MISSING")
        self.assertEqual(result["workflows"]["stale_runs_discarded"], 1)

    def test_scope_workflow_and_contract_drift_invalidate_receipt(self) -> None:
        for field, expected in (("scope_sha256", "SCOPE_DRIFT"), ("workflow_blob_inventory_sha256", "WORKFLOW_BLOB_DRIFT"), ("contract_blob_sha", "CONTRACT_BLOB_DRIFT")):
            with self.subTest(field=field):
                value = snapshot()
                value["reobservation"][field] = "0" * (64 if field != "contract_blob_sha" else 40)
                result = MODULE.evaluate(value)
                self.assertEqual(result["first_blocker"], expected)

    def test_declared_predecessor_scope_is_visible_without_lifecycle_mutation(self) -> None:
        value = snapshot()
        value["declared_predecessor"] = {
            "number": 41,
            "declared_head_sha": PREDECESSOR,
            "observed_head_sha": PREDECESSOR,
            "state": "open",
            "changed_paths": ["docs/publications/current.md"],
        }
        result = MODULE.evaluate(value)
        self.assertEqual(result["supersession"]["state"], "CURRENT_MAIN_SUCCESSOR_SCOPE_COVERED")
        self.assertEqual(result["supersession"]["lifecycle_followup"], "PREDECESSOR_STILL_OPEN")

    def test_contract_paths_match_exact_workflow_names(self) -> None:
        value = contract()
        for group in ("required", "conditionally_not_applicable"):
            for gate in value["workflow_gates"][group]:
                workflow = ROOT / gate["path"]
                self.assertTrue(workflow.is_file(), gate["path"])
                self.assertIn(f"name: {gate['name']}", workflow.read_text(encoding="utf-8"))

    def test_workflow_stays_artifact_only_and_read_only(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertIn("qikvrt-publication-candidate-readiness-", workflow)
        self.assertIn("github.event.pull_request.head.sha || 'main'", workflow)
        for forbidden in ("actions: write", "pull-requests: write", "gh pr merge", "/merge", "/dispatches", "zenodo.org", "arxiv.org", "datatracker.ietf.org"):
            self.assertNotIn(forbidden, workflow)

    def test_workflow_embedded_python_is_syntactically_valid(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        blocks = re.findall(r"python3 - <<'PY'\n(.*?)\n          PY", workflow, flags=re.DOTALL)
        self.assertEqual(len(blocks), 2)
        for index, block in enumerate(blocks, start=1):
            compile(textwrap.dedent(block), f"publication-readiness-workflow-{index}.py", "exec")


if __name__ == "__main__":
    unittest.main()
