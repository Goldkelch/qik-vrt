#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Structural regression tests for the formalization-v2 release protocol."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_formalization_v2_zenodo.yml"
MARKER = ROOT / "release/formalization-v2-request.json"
MANIFEST = ROOT / "release/formalization-v2-zenodo.json"
CLIENT = ROOT / "tools/qikvrt_formalization_v2_zenodo.py"
SHARED_CLIENT = ROOT / "tools/qikvrt_zenodo_actions.py"
CLIENT_TEST = ROOT / "tests/test_formalization_v2_zenodo.py"
ARCHIVE = ROOT / "release/formalization-v2/QIKVRT_Formalization_v2.0-alpha.1.zip"
EFFECT = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0/release_authorization/EFFECT_ACK_DONE.json"
)
MAKEFILE = ROOT / "Makefile"
INSPECTION_WORKFLOW = ROOT / ".github/workflows/qikvrt_formalization_v2_inspect.yml"
INSPECTION_MARKER = ROOT / "release/formalization-v2-inspection-request.json"
AUTOMATION_BRANCH = "automation/formalization-v2-publish-20260723-v2"
FEATURE_BRANCH = "agent/manuscript-formalization-v2-alpha"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embedded_python(workflow: str, step_name: str) -> str:
    start = workflow.index(f"      - name: {step_name}")
    next_step = workflow.find("\n      - name:", start + 1)
    block = workflow[start:] if next_step < 0 else workflow[start:next_step]
    match = re.search(
        r"python -I -S -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", block, re.S
    )
    if match is None:
        raise AssertionError(f"workflow step has no isolated embedded Python: {step_name}")
    lines = match.group(1).splitlines()
    indentation = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip()
    )
    return "\n".join(
        line[indentation:] if line.strip() else "" for line in lines
    )


class FormalizationV2ReleaseWorkflowTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.marker = json.loads(MARKER.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_trigger_is_one_inert_marker_on_one_authority_branch(self) -> None:
        trigger = self.workflow.split("permissions:", 1)[0]
        self.assertIn(f"      - {AUTOMATION_BRANCH}\n", trigger)
        self.assertIn("      - release/formalization-v2-request.json\n", trigger)
        self.assertNotIn(FEATURE_BRANCH, trigger)
        self.assertNotIn("workflow_dispatch", self.workflow)
        self.assertNotIn("repository_dispatch", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s*pull_request(?:_target)?:")
        self.assertIn("github.repository == 'Goldkelch/qik-vrt'", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)

    def test_candidate_marker_is_closed_and_inert(self) -> None:
        self.assertEqual(
            set(self.marker),
            {"schema", "request_id", "state", "confirm", "candidate", "bindings"},
        )
        self.assertEqual(
            self.marker["schema"],
            "qikvrt_formalization_v2_publication_request_v1",
        )
        self.assertEqual(
            self.marker["request_id"], "2026-07-23-formalization-v2.0-alpha.1"
        )
        self.assertEqual(self.marker["state"], "inactive")
        self.assertEqual(self.marker["confirm"], "NOT_AUTHORIZED")
        candidate = self.marker["candidate"]
        self.assertEqual(candidate["authority_repository"], "Goldkelch/qik-vrt")
        self.assertEqual(candidate["mirror_repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(candidate["feature_branch"], FEATURE_BRANCH)
        for key in ("candidate_commit", "candidate_tree", "mirror_commit", "mirror_tree"):
            self.assertEqual(candidate[key], "0" * 40)
        self.assertEqual(
            set(self.marker["bindings"]),
            {
                "effect_ack_sha256",
                "manifest_sha256",
                "client_sha256",
                "shared_client_sha256",
                "client_test_sha256",
                "workflow_sha256",
                "archive_sha256",
            },
        )
        for value in self.marker["bindings"].values():
            self.assertEqual(value, "0" * 64)

    def test_inert_marker_executes_without_network_and_cannot_authorize(self) -> None:
        source = embedded_python(
            self.workflow, "Validate inert or marker-only publication request"
        )
        with tempfile.TemporaryDirectory(prefix="qikvrt-inert-marker-output-") as raw:
            output = pathlib.Path(raw) / "github-output"
            environment = {
                "GITHUB_REPOSITORY": "Goldkelch/qik-vrt",
                "GITHUB_SHA": "a" * 40,
                "GITHUB_OUTPUT": os.fspath(output),
                "GH_API_TOKEN": "offline-unused-token",
                "EVENT_AFTER": "a" * 40,
                "EVENT_BEFORE": "0" * 40,
                "EVENT_FORCED": "false",
                "EVENT_REF": "refs/heads/" + AUTOMATION_BRANCH,
            }
            with mock.patch.dict(os.environ, environment, clear=False), mock.patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("inactive marker attempted network access"),
            ), mock.patch("pathlib.Path.cwd", return_value=ROOT), mock.patch(
                "os.getcwd", return_value=os.fspath(ROOT)
            ):
                previous = pathlib.Path.cwd()
                os.chdir(ROOT)
                try:
                    with self.assertRaises(SystemExit) as stopped:
                        exec(compile(source, "<formalization-v2-marker>", "exec"), {})
                finally:
                    os.chdir(previous)
            self.assertEqual(stopped.exception.code, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "authorized=false\n")

    def test_finalize_protocol_binds_parent_diff_bases_mirror_and_all_mutators(self) -> None:
        required = (
            'state != "finalize"',
            'PUBLISH_ZENODO_FORMALIZATION_V2_ALPHA_1',
            'changes != ["M\\t" + MARKER_PATH]',
            'git("show", "-s", "--format=%P", "HEAD^").split() != [AUTHORITY_CANDIDATE_PARENT]',
            'candidate["candidate_tree"] != candidate["mirror_tree"]',
            'd037a44d2893b9ea094d7cad55954223eb90a186',
            '7aaee4e1b182e18c9f0e927685f31d3c1190031a',
            'ed4f61fb4f09043eb8683932a1fed5222ad524f7',
            'c9a7bcabebd66768f2f728d8b35a9317c5ea7323',
            'fetch-depth: 4',
            'git checkout --detach "${{ steps.marker.outputs.candidate_commit }}"',
            'EVENT_BEFORE',
            'EVENT_FORCED',
        )
        for text in required:
            self.assertIn(text, self.workflow)
        paths = {
            "effect_ack_sha256": EFFECT,
            "manifest_sha256": MANIFEST,
            "client_sha256": CLIENT,
            "shared_client_sha256": SHARED_CLIENT,
            "client_test_sha256": CLIENT_TEST,
            "workflow_sha256": WORKFLOW,
            "archive_sha256": ARCHIVE,
        }
        for key, path in paths.items():
            self.assertIn(f'"{key}": "{path.relative_to(ROOT).as_posix()}"', self.workflow)
        self.assertGreaterEqual(self.workflow.count("remote_head("), 3)
        self.assertIn("authority feature branch moved before effect", self.workflow)
        self.assertIn("mirror feature branch moved before effect", self.workflow)

    def test_effect_ack_and_truthful_partial_scope_are_hard_gates(self) -> None:
        for value in (
            "ICH AKZEPTIERE",
            "NATURAL_PERSON",
            "Ingolf Lohmann",
            "partial formalization with explicit boundaries",
            "publish a new version of formalization concept 10.5281/zenodo.21488115",
            "EFFECT_ACK_DONE",
        ):
            self.assertIn(value, self.workflow)
        self.assertIn('software.get("source_record_id") != 21498774', self.workflow)
        self.assertIn('software.get("concept_record_id") != 21488115', self.workflow)
        self.assertIn('software.get("metadata", {}).get("version") != "2.0.0-alpha.1"', self.workflow)

    def test_secret_boundary_is_isolated_and_followed_by_anonymous_verification(self) -> None:
        self.assertEqual(self.workflow.count("secrets.ZENODO_ACCESS_TOKEN"), 2)
        self.assertNotIn("access_token=", self.workflow.lower())
        publish = self.workflow.index(
            "Publish the exact new Zenodo version through the isolated client"
        )
        anonymous = self.workflow.index(
            "Independently verify anonymous public Zenodo metadata and bytes"
        )
        reject = self.workflow.index(
            "Reject secret-bearing or incomplete publication evidence"
        )
        recheck = self.workflow.index(
            "Revalidate candidate bytes and both remote branch heads before effect"
        )
        self.assertLess(recheck, publish)
        self.assertLess(publish, anonymous)
        self.assertLess(anonymous, reject)
        anonymous_block = self.workflow[anonymous:reject]
        self.assertNotIn("ZENODO_ACCESS_TOKEN", anonymous_block)
        self.assertNotIn("from tools", anonymous_block)
        self.assertIn('"anonymous": True', anonymous_block)
        self.assertIn("source_latest_verified", anonymous_block)
        self.assertIn("hashlib.sha256(raw).hexdigest()", anonymous_block)
        publish_block = self.workflow[publish:anonymous]
        self.assertIn("python -I -S -B -", publish_block)
        self.assertIn("runpy.run_path", publish_block)

    def test_actions_are_immutable_and_workflow_never_writes_repository_refs(self) -> None:
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", self.workflow)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"@(?:[0-9a-f]{40}|[0-9a-f]{64})$")
        for forbidden in ("git push", "gh pr", "gh release", "contents: write"):
            self.assertNotIn(forbidden, self.workflow)

    def test_draft_inspection_is_inert_read_only_and_hash_bound(self) -> None:
        inspection = INSPECTION_WORKFLOW.read_text(encoding="utf-8")
        marker = json.loads(INSPECTION_MARKER.read_text(encoding="utf-8"))
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertTrue(all(value == "0" * 64 for value in marker["bindings"].values()))
        self.assertIn("automation/formalization-v2-inspect-20260723", inspection)
        self.assertIn("release/formalization-v2-inspection-request.json", inspection)
        self.assertIn("INSPECT_ZENODO_FORMALIZATION_V2_DRAFT_READ_ONLY", inspection)
        self.assertIn('["M\\t" + MARKER]', inspection)
        self.assertIn('method="GET"', inspection)
        for method in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"'):
            self.assertNotIn(method, inspection)
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", inspection)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"@(?:[0-9a-f]{40}|[0-9a-f]{64})$")

    def test_release_tests_are_part_of_root_test_and_candidate_workflow(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        for module in (
            "tests.test_formalization_v2_release_workflow",
            "tests.test_formalization_v2_zenodo",
        ):
            self.assertIn(module, makefile)
            self.assertIn(module, self.workflow)
        self.assertIn("tools/qikvrt_formalization_v2_zenodo.py", makefile)

    def test_manifest_continues_only_live_latest_concept_version(self) -> None:
        software = self.manifest["software"]
        self.assertEqual(software["source_record_id"], 21498774)
        self.assertEqual(software["concept_record_id"], 21488115)
        self.assertEqual(software["metadata"]["version"], "2.0.0-alpha.1")
        archive = next(
            item
            for item in software["files"]
            if item["name"] == "QIKVRT_Formalization_v2.0-alpha.1.zip"
        )
        self.assertEqual(archive["sha256"], sha256(ARCHIVE))
        self.assertEqual(
            archive["sha256"],
            "7cfa6851256bc5bdd9f5cb18ed7760d732dac2544a9f3a5ca514abade3a7825b",
        )


if __name__ == "__main__":
    unittest.main()
