# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import pathlib
import subprocess
import unittest

from tools.qikvrt_fixpoint_dfs_observer import (
    ContractError,
    build_receipt,
    load_contract,
    render_markdown,
    validate_contract,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/fixpoints/QIKVRT_HARDWARE_MACHINE_LANGUAGE_FIXPOINT_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_fixpoint_dfs_observer.yml"


def snapshot(*, status="completed", conclusion="success", after_head=None):
    head, tree = "1" * 40, "2" * 40
    return {
        "repository": "Goldkelch/qik-vrt",
        "pull_request": 907,
        "head_ref": "agent/neutron-star-2d-variable-bitrate-mesh-v1",
        "base_sha": "3" * 40,
        "head_sha_before": head,
        "tree_sha_before": tree,
        "head_sha_after": after_head or head,
        "tree_sha_after": tree,
        "captured_at": "2026-08-27T16:30:00Z",
        "workflow_runs": [{
            "id": 20,
            "name": "QIKVRT neutron-star 2D Mesh",
            "event": "pull_request",
            "status": status,
            "conclusion": conclusion,
            "created_at": "2026-08-27T16:20:00Z",
            "jobs_total_reported": 1,
            "jobs": [{
                "id": 200,
                "name": "plan-and-verify",
                "status": status,
                "conclusion": conclusion,
                "steps": [
                    {"number": 1, "name": "Set up job", "status": "completed", "conclusion": "success"},
                    {"number": 2, "name": "Wide segmentation", "status": status, "conclusion": conclusion},
                ],
            }],
        }],
    }


class FixpointObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(CONTRACT)

    def test_exact_positions_and_digests(self) -> None:
        self.assertEqual(validate_contract(self.contract), ["hardware", "machine_language"])
        hardware, machine = self.contract["positions"]
        self.assertEqual(
            hardware["exact_text_lf"],
            "./Goldkelch/qik-vrt/*\n\nDoD\n\n*=<>.\n\nq.e.d.\nIngolf Lohmann\n\n*=<>.\n",
        )
        self.assertEqual(
            machine["exact_text_lf"],
            "./Goldkelch/qik-vrt/*\n\n*=<>.\n\nq.e.d.\nIngolf Lohmann\n",
        )
        for position in (hardware, machine):
            self.assertEqual(
                hashlib.sha256(position["exact_text_lf"].encode()).hexdigest(),
                position["sha256"],
            )

    def test_terminal_local_fixpoint_is_observe_not_pass(self) -> None:
        receipt = build_receipt(snapshot(), self.contract)
        self.assertEqual(receipt["state"], "OBSERVE")
        self.assertEqual(receipt["positions"]["order"], ["hardware", "machine_language"])
        self.assertFalse(receipt["claims"]["pass"])
        self.assertFalse(receipt["claims"]["final_pass"])
        self.assertFalse(receipt["claims"]["effect_ack_done"])

    def test_active_execution_continues(self) -> None:
        receipt = build_receipt(snapshot(status="in_progress", conclusion=None), self.contract)
        self.assertEqual(receipt["state"], "CONTINUE")
        self.assertTrue(receipt["execution"]["active"])

    def test_deepest_causal_failure_is_the_step(self) -> None:
        receipt = build_receipt(snapshot(conclusion="failure"), self.contract)
        self.assertEqual(receipt["state"], "HOLD")
        self.assertEqual(receipt["reason"], "FIRST_CAUSAL_ADVERSE_EXECUTION_NODE")
        self.assertEqual(receipt["execution"]["first_adverse"]["kind"], "step")
        self.assertEqual(receipt["execution"]["first_adverse"]["name"], "Wide segmentation")
        self.assertIn("First causal adverse node", render_markdown(receipt))

    def test_binding_drift_requires_reobservation(self) -> None:
        receipt = build_receipt(snapshot(after_head="4" * 40), self.contract)
        self.assertEqual(receipt["state"], "REOBSERVE")
        self.assertTrue(receipt["binding"]["binding_drift"])

    def test_input_permutation_does_not_change_receipt(self) -> None:
        value = snapshot()
        other = copy.deepcopy(value["workflow_runs"][0])
        other["id"], other["created_at"], other["jobs"][0]["id"] = 10, "2026-08-27T16:10:00Z", 100
        value["workflow_runs"].append(other)
        reversed_value = copy.deepcopy(value)
        reversed_value["workflow_runs"].reverse()
        self.assertEqual(
            build_receipt(value, self.contract)["receipt_sha256"],
            build_receipt(reversed_value, self.contract)["receipt_sha256"],
        )

    def test_incomplete_job_inventory_is_rejected(self) -> None:
        value = snapshot()
        value["workflow_runs"][0]["jobs_total_reported"] = 2
        with self.assertRaisesRegex(ContractError, "incomplete job inventory"):
            build_receipt(value, self.contract)

    def test_broadened_claim_is_rejected(self) -> None:
        bad = copy.deepcopy(self.contract)
        bad["claim_boundaries"]["physical_hardware_execution"] = True
        with self.assertRaisesRegex(ContractError, "claim boundary"):
            validate_contract(bad)

    def test_workflow_is_event_driven_with_reconciliation_not_polling(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", source)
        self.assertIn('cron: "*/5 * * * *"', source)
        self.assertIn("repository_dispatch:", source)
        self.assertIn('"--paginate",', source)
        self.assertIn('"--slurp",', source)
        self.assertIn("QIKVRT fixpoint positional DFS observation", source)
        self.assertNotIn("sleep ", source)
        self.assertNotIn("while :", source)
        self.assertNotIn("gh pr merge", source)

    def test_embedded_bash_blocks_are_syntax_valid(self) -> None:
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        blocks, index = [], 0
        while index < len(lines):
            if lines[index] == "        run: |":
                index += 1
                block = []
                while index < len(lines):
                    line = lines[index]
                    if line and len(line) - len(line.lstrip(" ")) < 10:
                        break
                    block.append(line[10:] if len(line) >= 10 else "")
                    index += 1
                blocks.append("\n".join(block) + "\n")
                continue
            index += 1
        self.assertGreaterEqual(len(blocks), 5)
        for ordinal, script in enumerate(blocks):
            completed = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, f"bash block {ordinal}: {completed.stderr}")


if __name__ == "__main__":
    unittest.main()
