#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import tempfile
import unittest
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/qikvrt_mesh_html.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_mesh_html", MODULE_PATH)
assert SPEC and SPEC.loader
mesh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mesh)

ARTIFACT = ROOT / "QIK_VRT_MESH.html"
WORKFLOW = ROOT / ".github/workflows/qikvrt_feature_request.yml"
SCHEMA = ROOT / "policy/QIKVRT_FEATURE_REQUEST_V1.schema.json"
HEAD = "1" * 40


class MeshHtmlTests(unittest.TestCase):
    def test_committed_artifact_is_deterministic_generator_output(self) -> None:
        self.assertEqual(ARTIFACT.read_bytes(), mesh.artifact_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            generated = pathlib.Path(tmp) / "QIK_VRT_MESH.html"
            mesh.write_artifact(generated)
            self.assertEqual(generated.read_bytes(), ARTIFACT.read_bytes())

    def test_single_file_is_offline_embedded_svg_and_bounded(self) -> None:
        raw = ARTIFACT.read_bytes()
        text = raw.decode("utf-8")
        self.assertLess(len(raw), 10 * 1024 * 1024)
        self.assertTrue(unicodedata.is_normalized("NFC", text))
        self.assertIn("<svg", text)
        self.assertIn("<style>", text)
        self.assertIn("<script>", text)
        for forbidden in (
            r"https?://",
            r"<script[^>]+src=",
            r"<link[^>]+href=",
            r"\bfetch\s*\(",
            r"\bXMLHttpRequest\b",
            r"\bWebSocket\s*\(",
            r"\bEventSource\s*\(",
        ):
            self.assertIsNone(re.search(forbidden, text, flags=re.IGNORECASE), forbidden)

    def test_all_requested_surface_capabilities_are_materialized(self) -> None:
        text = ARTIFACT.read_text(encoding="utf-8")
        for value in mesh.VIEWS + mesh.TIME_MODES + mesh.ANIMATIONS:
            self.assertIn(value, text)
        for value in (
            "fpsHistory", "historyLine", "profileFrames", "warningList",
            "function migrate", "function downgrade", "function stable",
            "normalize('NFC')", "function selfTests", "property-based samples=128",
            "localStorage", "future_projection", "PREDECESSOR_EVIDENCE_TRANSFER = FALSE",
            "REFERENCE_LINK ≠ EVIDENCE_TRANSFER ≠ EFFECT_ACK",
        ):
            self.assertIn(value, text)

    def test_repository_dispatch_original_shape_is_accepted_and_subject_bound(self) -> None:
        request = json.loads(json.dumps(mesh.CANONICAL_REQUEST))
        request["subject_sha"] = HEAD
        event = {"action": mesh.EVENT_TYPE, "client_payload": request}
        selected = mesh.request_from_event(event, "repository_dispatch", HEAD)
        self.assertEqual(selected["artifact"], mesh.ARTIFACT)
        self.assertEqual(selected["subject_sha"], HEAD)

    def test_repository_dispatch_rejects_wrong_event_and_subject_drift(self) -> None:
        request = json.loads(json.dumps(mesh.CANONICAL_REQUEST))
        with self.assertRaises(ValueError):
            mesh.request_from_event({"action": "other", "client_payload": request}, "repository_dispatch", HEAD)
        request["subject_sha"] = "2" * 40
        with self.assertRaises(ValueError):
            mesh.request_from_event({"action": mesh.EVENT_TYPE, "client_payload": request}, "repository_dispatch", HEAD)

    def test_unknown_request_fields_fail_closed(self) -> None:
        request = json.loads(json.dumps(mesh.CANONICAL_REQUEST))
        request["request"]["network"] = True
        with self.assertRaises(ValueError):
            mesh.validate_feature_request(request)

    def test_workflow_dispatch_supports_default_and_encoded_request(self) -> None:
        event = {"inputs": {"task": mesh.TASK, "request_json_b64": "", "subject_sha": ""}}
        selected = mesh.request_from_event(event, "workflow_dispatch", HEAD)
        self.assertEqual(selected, mesh.CANONICAL_REQUEST)

    def test_workflow_is_read_only_and_executes_build_test_receipt(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "types: [qikvrt_feature_request]",
            "options: [build_qik_vrt_mesh_html]",
            "contents: read",
            "actions: read",
            "persist-credentials: false",
            "validate-event",
            "generate --output dist/QIK_VRT_MESH.html",
            "cmp -- QIK_VRT_MESH.html dist/QIK_VRT_MESH.html",
            "tests.test_qikvrt_mesh_html",
            "QIK_VRT_MESH.receipt.json",
            "actions/upload-artifact@",
        ):
            self.assertIn(required, text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("git push", text)

    def test_schema_binds_real_repository_dispatch_contract(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["event_type"]["const"], mesh.EVENT_TYPE)
        payload = schema["properties"]["client_payload"]
        self.assertFalse(payload["additionalProperties"])
        self.assertEqual(payload["properties"]["artifact"]["const"], mesh.ARTIFACT)
        request = payload["properties"]["request"]
        self.assertEqual(request["properties"]["views"]["const"], mesh.VIEWS)
        self.assertEqual(request["properties"]["time_modes"]["const"], mesh.TIME_MODES)
        self.assertEqual(request["properties"]["animations"]["const"], mesh.ANIMATIONS)

    def test_receipt_does_not_claim_repository_or_effect_ack_completion(self) -> None:
        request = json.loads(json.dumps(mesh.CANONICAL_REQUEST))
        with tempfile.TemporaryDirectory() as tmp:
            artifact = pathlib.Path(tmp) / mesh.ARTIFACT
            mesh.write_artifact(artifact)
            receipt = mesh.build_receipt(request, HEAD, "3" * 40, artifact)
        self.assertFalse(receipt["repository_mutation"])
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["transport_ack_is_effect_ack"])
        self.assertFalse(receipt["predecessor_evidence_transfer"])
        self.assertEqual(receipt["effect_scope"], "deterministic-build-test-artifact-only")


if __name__ == "__main__":
    unittest.main()
