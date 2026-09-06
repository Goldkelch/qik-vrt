#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""One-shot trusted-main materializer for requested-review root-cause repair.

This program edits only the exact known executor contracts and writes focused
regression tests. The bridge executes the copy from trusted main, not candidate
bytes. It performs no GitHub API writes and makes no approval/effect claims.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if __file__ != "/tmp/qikvrt_review_root_fix.py" else Path.cwd()


def replace_exact(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, observed {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    core = ROOT / "tools/qikvrt_requested_review_executor.py"
    workflow = ROOT / ".github/workflows/qikvrt_requested_review_executor.yml"

    replace_exact(
        core,
        '    "detail",\n    "evidence_fingerprint",\n',
        '    "detail",\n'
        '    # Trusted-main tip is observation progress, not immutable candidate identity.\n'
        '    "current_main_sha",\n'
        '    "current_main_tree_sha",\n'
        '    "evidence_fingerprint",\n',
        "CORE_PROGRESS_PROJECTION_ANCHOR",
    )

    replace_exact(
        workflow,
        "      - name: Select exactly one durable recursive review work unit\n"
        "        if: steps.active.outputs.active == 'true' && steps.ledger.outputs.persisted == 'true'\n"
        "        id: queue\n"
        "        shell: bash\n",
        "      - name: Select exactly one durable recursive review work unit\n"
        "        if: steps.active.outputs.active == 'true' && steps.ledger.outputs.persisted == 'true'\n"
        "        id: queue\n"
        "        env:\n"
        "          SUBJECT_PR_NUMBER: ${{ steps.select.outputs.pr }}\n"
        "          SUBJECT_HEAD_SHA: ${{ steps.decision.outputs.head }}\n"
        "        shell: bash\n",
        "QUEUE_STEP_ANCHOR",
    )

    replace_exact(
        workflow,
        "              intent=parsed(queue_path)\n"
        "              if not isinstance(intent,dict):\n"
        "                  raise SystemExit(f'RECURSIVE_QUEUE_INTENT_INVALID_{queue_path}')\n"
        "              receipt_path=intent.get('receipt_path')\n",
        "              intent=parsed(queue_path)\n"
        "              if not isinstance(intent,dict):\n"
        "                  raise SystemExit(f'RECURSIVE_QUEUE_INTENT_INVALID_{queue_path}')\n"
        "              # Queue order is transport order, never causal subject routing.\n"
        "              if (\n"
        "                  intent.get('repository') != repo\n"
        "                  or str(intent.get('pr_number')) != os.environ['SUBJECT_PR_NUMBER']\n"
        "                  or intent.get('head_sha') != os.environ['SUBJECT_HEAD_SHA']\n"
        "              ):\n"
        "                  continue\n"
        "              receipt_path=intent.get('receipt_path')\n",
        "QUEUE_SUBJECT_FILTER_ANCHOR",
    )

    replace_exact(
        workflow,
        "              'tree_sha':commit.get('tree',{}).get('sha') == os.environ['EXPECTED_TREE'],\n"
        "              'base_sha':pr.get('base',{}).get('sha') == os.environ['EXPECTED_BASE'],\n"
        "              'workflow_event':run.get('event') == 'workflow_dispatch',\n",
        "              'tree_sha':commit.get('tree',{}).get('sha') == os.environ['EXPECTED_TREE'],\n"
        "              # GitHub pr.base.sha is a moving branch tip, not transport identity.\n"
        "              # Fresh base drift is classified by the child review.\n"
        "              'base_ref':pr.get('base',{}).get('ref') == 'main',\n"
        "              'workflow_event':run.get('event') == 'workflow_dispatch',\n",
        "TRANSPORT_BASE_IDENTITY_ANCHOR",
    )

    test = ROOT / "tests/test_qikvrt_review_control_plane_root_fix.py"
    test.write_text(
        '''# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0\n'''
        '''import copy\n'''
        '''import importlib.util\n'''
        '''import pathlib\n'''
        '''import sys\n'''
        '''import unittest\n\n'''
        '''ROOT = pathlib.Path(__file__).resolve().parents[1]\n'''
        '''SPEC = importlib.util.spec_from_file_location("qikvrt_requested_review_executor_root_fix", ROOT / "tools/qikvrt_requested_review_executor.py")\n'''
        '''assert SPEC and SPEC.loader\n'''
        '''MODULE = importlib.util.module_from_spec(SPEC)\n'''
        '''sys.modules[SPEC.name] = MODULE\n'''
        '''SPEC.loader.exec_module(MODULE)\n\n'''
        '''class RequestedReviewControlPlaneRootFixTests(unittest.TestCase):\n'''
        '''    def test_main_tip_is_progress_not_historical_identity(self):\n'''
        '''        receipt = {\n'''
        '''            "repository":"example/qik-vrt", "pr_number":1016, "base_ref":"main",\n'''
        '''            "base_sha":"a"*40, "base_tree_sha":"b"*40, "head_sha":"c"*40,\n'''
        '''            "tree_sha":"d"*40, "scope_sha256":"e"*64, "diff_sha256":"f"*64,\n'''
        '''            "current_main_sha":"1"*40, "current_main_tree_sha":"2"*40,\n'''
        '''            "state":"APPROVE", "mesh_disposition":"APPROVE", "first_blocker":None,\n'''
        '''            "detail":"old", "evidence_fingerprint":"3"*64, "receipt_payload_sha256":"4"*64,\n'''
        '''        }\n'''
        '''        successor = copy.deepcopy(receipt)\n'''
        '''        successor.update(current_main_sha="5"*40, current_main_tree_sha="6"*40,\n'''
        '''                         state="COMMENT_WITH_BLOCKER", mesh_disposition="COMMENT_WITH_BLOCKER",\n'''
        '''                         first_blocker="BASE_DRIFT", detail="main advanced",\n'''
        '''                         evidence_fingerprint="7"*64, receipt_payload_sha256="8"*64)\n'''
        '''        self.assertEqual(MODULE._historical_receipt_binding(receipt), MODULE._historical_receipt_binding(successor))\n\n'''
        '''    def test_recursive_queue_is_subject_scoped(self):\n'''
        '''        text=(ROOT/".github/workflows/qikvrt_requested_review_executor.yml").read_text()\n'''
        '''        self.assertIn("SUBJECT_PR_NUMBER: ${{ steps.select.outputs.pr }}", text)\n'''
        '''        self.assertIn("SUBJECT_HEAD_SHA: ${{ steps.decision.outputs.head }}", text)\n'''
        '''        self.assertIn("str(intent.get('pr_number')) != os.environ['SUBJECT_PR_NUMBER']", text)\n'''
        '''        self.assertIn("intent.get('head_sha') != os.environ['SUBJECT_HEAD_SHA']", text)\n\n'''
        '''    def test_transport_does_not_bind_moving_base_tip(self):\n'''
        '''        text=(ROOT/".github/workflows/qikvrt_requested_review_executor.yml").read_text()\n'''
        '''        self.assertNotIn("'base_sha':pr.get('base',{}).get('sha') == os.environ['EXPECTED_BASE']", text)\n'''
        '''        self.assertIn("'base_ref':pr.get('base',{}).get('ref') == 'main'", text)\n'''
        '''        self.assertIn("'full_causal_binding'", text)\n\n'''
        '''if __name__ == "__main__":\n'''
        '''    unittest.main()\n''',
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
