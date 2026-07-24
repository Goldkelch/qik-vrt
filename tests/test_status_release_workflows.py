#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed static contract tests for the inert status-report workflows."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESERVE = ROOT / ".github/workflows/qikvrt_status_report_reserve.yml"
FINALIZE = ROOT / ".github/workflows/qikvrt_status_report_finalize.yml"
MARKER = ROOT / "release/status-clarification-request.json"
SCHEMA = ROOT / "policy/qikvrt-status-report-release-request.schema.json"
DOC = ROOT / "docs/STATUS_REPORT_RELEASE_AUTOMATION.md"
ZERO40 = "0" * 40
ZERO64 = "0" * 64
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
UPLOAD_ARTIFACT_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"


class StatusReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reserve = RESERVE.read_text(encoding="utf-8")
        cls.finalize = FINALIZE.read_text(encoding="utf-8")
        cls.marker_raw = MARKER.read_bytes()
        cls.marker = json.loads(cls.marker_raw)
        cls.schema_raw = SCHEMA.read_bytes()
        cls.schema = json.loads(cls.schema_raw)

    def test_initial_marker_is_canonically_inert(self) -> None:
        marker = self.marker
        self.assertEqual(marker["action"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(marker["release"]["expected_source_tree"], ZERO40)
        self.assertEqual(
            marker["release"]["expected_source_commits"],
            {"Goldkelch/qik-vrt": ZERO40, "ingolf-lohmann/qik-vrt": ZERO40},
        )
        for key in (
            "client_sha256",
            "reservation_manifest_sha256",
            "final_template_manifest_sha256",
            "final_manifest_sha256",
            "reservation_evidence_sha256",
        ):
            self.assertEqual(marker["zenodo"][key], ZERO64, key)
        self.assertIsNone(marker["zenodo"]["report_doi"])
        projection = dict(marker)
        projection.pop("authorization_payload_sha256")
        canonical = json.dumps(
            projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(
            marker["authorization_payload_sha256"],
            hashlib.sha256(canonical).hexdigest(),
        )
        self.assertEqual(
            marker["schema_sha256"], hashlib.sha256(self.schema_raw).hexdigest()
        )

    def test_schema_closes_three_manifest_contract(self) -> None:
        self.assertFalse(self.schema["additionalProperties"])
        zenodo = self.schema["properties"]["zenodo"]
        self.assertFalse(zenodo["additionalProperties"])
        required = set(zenodo["required"])
        self.assertTrue(
            {
                "reservation_manifest_path",
                "reservation_manifest_sha256",
                "final_template_manifest_path",
                "final_template_manifest_sha256",
                "final_manifest_path",
                "final_manifest_sha256",
            }
            <= required
        )
        self.assertEqual(
            zenodo["properties"]["reservation_manifest_path"]["const"],
            "release/status-clarification-zenodo-reservation-manifest.json",
        )
        self.assertEqual(
            zenodo["properties"]["final_template_manifest_path"]["const"],
            "release/status-clarification-zenodo-template.json",
        )
        self.assertEqual(
            zenodo["properties"]["final_manifest_path"]["const"],
            "release/status-clarification-zenodo.json",
        )
        reserve = self.schema["allOf"][1]["then"]["properties"]
        finalize = self.schema["allOf"][2]["then"]["properties"]
        for active in (reserve, finalize):
            commits = active["release"]["properties"]["expected_source_commits"][
                "properties"
            ]
            self.assertEqual(
                commits["Goldkelch/qik-vrt"]["$ref"],
                "#/$defs/nonzeroGitSha1",
            )
            self.assertEqual(
                commits["ingolf-lohmann/qik-vrt"]["$ref"],
                "#/$defs/nonzeroGitSha1",
            )
            self.assertEqual(
                active["release"]["properties"]["expected_source_tree"]["$ref"],
                "#/$defs/nonzeroGitSha1",
            )
        for key in (
            "client_sha256",
            "reservation_manifest_sha256",
            "final_template_manifest_sha256",
        ):
            self.assertEqual(
                reserve["zenodo"]["properties"][key]["$ref"],
                "#/$defs/nonzeroSha256",
            )
        for key in (
            "client_sha256",
            "reservation_manifest_sha256",
            "final_template_manifest_sha256",
            "final_manifest_sha256",
            "reservation_evidence_sha256",
        ):
            self.assertEqual(
                finalize["zenodo"]["properties"][key]["$ref"],
                "#/$defs/nonzeroSha256",
            )

    def test_only_exact_push_refs_and_marker_path_trigger(self) -> None:
        self.assertIn(
            "automation/status-clarification-reserve-20260722", self.reserve
        )
        self.assertIn(
            "automation/status-clarification-finalize-20260722", self.finalize
        )
        reserve_trigger = self.reserve.split("permissions:", 1)[0]
        finalize_trigger = self.finalize.split("permissions:", 1)[0]
        self.assertNotIn(
            "automation/status-clarification-finalize-20260722", reserve_trigger
        )
        self.assertNotIn(
            "automation/status-clarification-reserve-20260722", finalize_trigger
        )
        self.assertNotIn("workflow_dispatch:", self.reserve + self.finalize)
        self.assertNotIn("pull_request:", self.reserve + self.finalize)
        for workflow in (self.reserve, self.finalize):
            self.assertIn("release/status-clarification-request.json", workflow)
            self.assertIn('require(os.environ["EVENT_NAME"], "push"', workflow)
            self.assertIn('require(os.environ["EVENT_FORCED"], "false"', workflow)
            self.assertIn("marker-only authorization commit", workflow)
            self.assertIn("HEAD^", workflow)

    def test_actions_are_immutable_sha_pinned(self) -> None:
        combined = self.reserve + self.finalize
        uses = re.findall(r"^\s*uses:\s*([^\s#]+)", combined, flags=re.MULTILINE)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")
        self.assertIn("actions/checkout@" + CHECKOUT_SHA, combined)
        self.assertIn("actions/setup-python@" + SETUP_PYTHON_SHA, combined)
        self.assertIn("actions/upload-artifact@" + UPLOAD_ARTIFACT_SHA, combined)

    def test_reserve_and_finalize_use_schema2_cli(self) -> None:
        self.assertIn(
            "--reservation-manifest release/status-clarification-zenodo-reservation-manifest.json",
            self.reserve,
        )
        self.assertIn(
            "--final-template-manifest release/status-clarification-zenodo-template.json",
            self.reserve,
        )
        self.assertNotIn("--final-manifest", self.reserve)
        for option in (
            "--reservation-manifest release/status-clarification-zenodo-reservation-manifest.json",
            "--final-template-manifest release/status-clarification-zenodo-template.json",
            "--final-manifest release/status-clarification-zenodo.json",
        ):
            self.assertIn(option, self.finalize)
        self.assertNotRegex(self.reserve + self.finalize, r"(?m)^\s+--manifest\s")

    def test_repository_effect_partition_is_explicit(self) -> None:
        self.assertIn("github.repository == 'Goldkelch/qik-vrt'", self.reserve)
        self.assertNotIn("secrets.ZENODO_ACCESS_TOKEN", self.finalize.split("zenodo:", 1)[0])
        self.assertIn("github.repository == 'Goldkelch/qik-vrt'", self.finalize)
        self.assertIn("github.repository == 'ingolf-lohmann/qik-vrt'", self.finalize)
        self.assertEqual(self.reserve.count("secrets.ZENODO_ACCESS_TOKEN"), 2)
        self.assertEqual(self.finalize.count("secrets.ZENODO_ACCESS_TOKEN"), 2)
        self.assertIn("permissions:\n      contents: write", self.finalize)
        self.assertIn('"object": source', self.finalize)
        self.assertNotIn('"object": os.environ["GITHUB_SHA"]', self.finalize)

    def test_state_and_cross_repository_barriers_are_fail_closed(self) -> None:
        combined = self.reserve + self.finalize
        self.assertGreaterEqual(
            combined.count('encoded = "".join('),
            3,
        )
        self.assertNotIn(
            'base64.b64decode(content["content"], validate=True)', combined
        )
        for workflow in (self.reserve, self.finalize):
            self.assertIn('get_ref_path = "/git/ref/" + encoded_ref', workflow)
            self.assertIn('update_ref_path = "/git/refs/" + encoded_ref', workflow)
            self.assertIn('api("PATCH", update_ref_path', workflow)
        self.assertIn(
            "release-state/status-clarification/zenodo-reservation-attempt.json",
            self.reserve,
        )
        self.assertIn(
            "a prior one-shot intent has no persisted reservation", self.reserve
        )
        self.assertIn(
            'ref(repository, "main") != expected',
            self.reserve,
        )
        self.assertIn(
            'state_headers["Authorization"] = f"Bearer {os.environ[\'GH_API_TOKEN\']}"',
            self.reserve,
        )
        self.assertNotIn(
            "/contents/{state_path}?ref={state_ref}\",\n              headers=headers",
            self.reserve,
        )
        self.assertIn(
            'tag_is_exact("ingolf-lohmann/qik-vrt")',
            self.finalize,
        )
        self.assertIn(
            "mirror annotated tag was not observable within ten minutes",
            self.finalize,
        )
        self.assertIn(
            'content = api(\n              "Goldkelch/qik-vrt"',
            self.finalize,
        )
        self.assertGreaterEqual(self.finalize.count("validate_final_transition("), 1)

    def test_old_records_and_newversion_are_fail_closed(self) -> None:
        combined = self.reserve + self.finalize + DOC.read_text(encoding="utf-8")
        for identifier in ("21498772", "21498773", "21498774", "21488115"):
            self.assertIn(identifier, combined)
        self.assertIn("newversion", combined)
        self.assertIn("No GitHub Release object", self.marker["release"]["tag_message"])

    def test_all_embedded_python_is_syntactically_valid(self) -> None:
        snippets: list[str] = []
        for workflow in (self.reserve, self.finalize):
            lines = workflow.splitlines()
            index = 0
            while index < len(lines):
                if lines[index].strip() != "python -B - <<'PY'":
                    index += 1
                    continue
                start = index + 1
                index = start
                while index < len(lines) and lines[index].strip() != "PY":
                    index += 1
                self.assertLess(index, len(lines), "unterminated Python heredoc")
                snippets.append(textwrap.dedent("\n".join(lines[start:index])))
                index += 1
        self.assertGreaterEqual(len(snippets), 8)
        for number, snippet in enumerate(snippets, start=1):
            compile(snippet, f"workflow-heredoc-{number}", "exec")


if __name__ == "__main__":
    unittest.main()
