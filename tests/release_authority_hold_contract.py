#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Shared assertions for retired release workflows."""

from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile
import textwrap
from unittest import mock

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

CARRIER_WORKFLOWS = (
    "publish_ontology_difference_article_zenodo_v3.yml",
    "qikvrt_canonical_temporal_memory_zenodo_publish.yml",
    "qikvrt_effect_ack_finalize.yml",
    "qikvrt_formalization_v2_alpha3_publish.yml",
    "qikvrt_formalization_v2_inspect.yml",
    "qikvrt_formalization_v2_inventory.yml",
    "qikvrt_formalization_v2_zenodo.yml",
    "qikvrt_formalization_v2_zenodo_finalize.yml",
    "qikvrt_round_trip_zenodo_publish.yml",
    "qikvrt_status_report_finalize.yml",
    "qikvrt_status_report_reserve.yml",
    "qikvrt_survival_connectability_zenodo_publish.yml",
    "qikvrt_vrtcore_h3_e1_recovery.yml",
    "qikvrt_zenodo_reserve.yml",
)

FALSE_CLAIMS = {
    "physical_atari_boot": False,
    "physical_atari_execution": False,
    "merge": False,
    "approval": False,
    "pass": False,
    "final_pass": False,
    "publication": False,
    "release": False,
    "deployment": False,
    "authority_mirror_synchronization": False,
    "effect_ack_done": False,
}


def _hold_python(text: str) -> str:
    match = re.search(
        r"python3 -B - <<'PY'\n(?P<body>.*?)\n\s*PY(?:\n|$)", text, re.S
    )
    if match is None:
        raise AssertionError("Authority HOLD workflow has no embedded receipt builder")
    return textwrap.dedent(match.group("body"))


def assert_authority_hold_workflow(testcase, name: str) -> None:
    path = WORKFLOWS / name
    text = path.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    testcase.assertEqual(workflow.get("on"), {"workflow_dispatch": ""})
    testcase.assertEqual(workflow.get("permissions"), {"contents": "read"})
    testcase.assertEqual(set(workflow.get("jobs", {})), {"authority-hold"})
    job = workflow["jobs"]["authority-hold"]
    testcase.assertEqual(
        job.get("if"),
        "github.ref == 'refs/heads/main' && github.workflow_sha == github.sha",
    )
    testcase.assertEqual(job.get("permissions"), {"contents": "read"})
    testcase.assertIn("ref: ${{ github.workflow_sha }}", text)
    testcase.assertIn("persist-credentials: false", text)
    testcase.assertIn("qikvrt_release_authority_hold_v1", text)
    testcase.assertIn("PROTECTED_RELEASE_AUTHORITY_NOT_EXTERNALLY_VERIFIED", text)
    testcase.assertIn("if-no-files-found: error", text)
    testcase.assertNotIn("push:", text.split("permissions:", 1)[0])
    testcase.assertNotIn("pull_request", text.split("permissions:", 1)[0])
    testcase.assertNotIn("workflow_run", text.split("permissions:", 1)[0])
    for forbidden in (
        "secrets.",
        "ZENODO_ACCESS_TOKEN",
        "contents: write",
        "actions: write",
        "issues: write",
        "pull-requests: write",
        "packages: write",
        "qikvrt_zenodo_actions.py",
        "git push",
        "gh release",
        "/git/tags",
        "/git/refs",
    ):
        testcase.assertNotIn(forbidden, text)
    for action in re.findall(r"uses:\s*([^\s]+)", text):
        testcase.assertRegex(action, r"@[0-9a-f]{40}$")

    with tempfile.TemporaryDirectory(prefix="qikvrt-release-hold-") as raw:
        receipt_path = pathlib.Path(raw) / "receipt.json"
        environment = {
            "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
            "GITHUB_WORKFLOW_SHA": "a" * 40,
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "RECEIPT": os.fspath(receipt_path),
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            exec(compile(_hold_python(text), f"{path}:hold", "exec"), {})
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    testcase.assertEqual(
        set(receipt),
        {
            "schema",
            "repository",
            "evaluator_sha",
            "run_id",
            "run_attempt",
            "d0",
            "state",
            "reason",
            "productive_effect",
            "completion_claims",
        },
    )
    testcase.assertEqual(receipt["d0"], 3)
    testcase.assertEqual(receipt["state"], "REQUEST_AUTHORITY")
    testcase.assertEqual(
        receipt["reason"], "PROTECTED_RELEASE_AUTHORITY_NOT_EXTERNALLY_VERIFIED"
    )
    testcase.assertIs(receipt["productive_effect"], False)
    testcase.assertEqual(receipt["completion_claims"], FALSE_CLAIMS)
