# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Execute the workflow's routing code against a strict, read-only API double.

Regression for requested-review run 34440301270: a fully projected exact
receipt must not enumerate unrelated ledger history before native review.
The doubles provide sealed fixture evidence; the existing review-core tests
remain responsible for the complete receipt and diff-transport contracts.
"""
from __future__ import annotations

import ast
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest
from unittest.mock import patch
import urllib.parse

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/qikvrt_requested_review_executor.yml"
QUEUE_STEP = "Select exactly one durable recursive review work unit"
REOBSERVE_STEP = "Reobserve successor transport and literal subject binding"
QUEUE_ROOT = "state/mesh/review-queue"
ACK_ROOT = "state/mesh/review-queue-acks"


def step_source(name: str) -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    start = source.index("      - name: " + name + "\n")
    end = source.find("\n      - name: ", start + 1)
    return source[start:] if end < 0 else source[start:end]


def step_code(name: str):
    source = step_source(name)
    script = source.split("          python3 -B - <<'PY'\n", 1)[1].split("\n          PY", 1)[0]
    tree = ast.parse(textwrap.dedent(script))
    # Isolate workflow routing, not a reimplementation of its routing logic.
    # Only the already separately tested review-core dependencies are doubled.
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom)
        and node.module == "tools.qikvrt_requested_review_executor"
    )]
    return compile(tree, str(WORKFLOW) + "::" + name, "exec")


def pretty(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class QueueFixture:
    repo = "Goldkelch/qik-vrt"
    number = 1069
    head = "a" * 40
    tree = "b" * 40
    base = "c" * 40
    ledger = "d" * 40
    predecessor = "e" * 64
    fingerprint = "f" * 64

    def __init__(self):
        self.queue_path = f"{QUEUE_ROOT}/pr-{self.number}/{self.head}/{self.fingerprint}.json"
        self.ack_path = f"{ACK_ROOT}/pr-{self.number}/{self.head}/{self.fingerprint}.json"
        self.receipt_path = f"state/mesh/reviews/pr-{self.number}/{self.head}/{self.fingerprint}.json"
        self.diff_path = self.receipt_path + ".diff.json"
        self.packet_path = self.receipt_path + ".packet-0"
        self.diff = b"diff --git a/example b/example\n"
        receipt = {
            "repository": self.repo, "pr_number": self.number,
            "head_sha": self.head, "tree_sha": self.tree, "base_sha": self.base,
            "evidence_fingerprint": self.fingerprint, "state": "APPROVE",
            "diff_sha256": hashlib.sha256(self.diff).hexdigest(),
            "diff_bytes": len(self.diff),
        }
        receipt["receipt_payload_sha256"] = canonical_sha(receipt)
        self.expected_intent = {
            "repository": self.repo, "pr_number": self.number,
            "head_sha": self.head, "tree_sha": self.tree, "base_sha": self.base,
            "predecessor_fingerprint": self.predecessor,
            "successor_fingerprint": self.fingerprint,
            "receipt_path": self.receipt_path, "diff_path": self.diff_path,
        }
        self.files = {
            self.queue_path: pretty(self.expected_intent),
            self.receipt_path: pretty(receipt),
            self.diff_path: pretty({"packets": [{"path": self.packet_path}]}),
            self.packet_path: self.diff,
        }
        self.calls: list[str] = []
        self.failures: dict[str, int] = {}
        self.projected = False
        self.pr_head = self.head
        self.ref_name = "refs/heads/qikvrt/mesh-review-ledger-v1"
        self.env = {
            "REPOSITORY": self.repo, "SUBJECT_PR_NUMBER": str(self.number),
            "SUBJECT_HEAD_SHA": self.head,
            "SUBJECT_PREDECESSOR_FINGERPRINT": self.predecessor,
            "SUCCESSOR_FINGERPRINT": self.fingerprint,
            "SUCCESSOR_QUEUE_PATH": self.queue_path,
        }

    def response(self, endpoint: str):
        self.calls.append(endpoint)
        prefix = f"repos/{self.repo}/"
        if endpoint == prefix + "git/ref/heads/qikvrt/mesh-review-ledger-v1":
            return {"ref": self.ref_name, "object": {"sha": self.ledger}}, 200
        if endpoint.startswith(prefix + "contents/"):
            parts = urllib.parse.urlsplit(endpoint)
            if urllib.parse.parse_qs(parts.query) != {"ref": [self.ledger]}:
                raise AssertionError("content read is not bound to the immutable ledger commit")
            path = urllib.parse.unquote(parts.path[len(prefix + "contents/"):])
            allowed = {self.queue_path, self.receipt_path, self.diff_path, self.packet_path, self.ack_path}
            if path not in allowed:
                raise AssertionError("unrelated queue/evidence read: " + path)
            if path in self.failures:
                return None, self.failures[path]
            if path not in self.files:
                return None, 404
            return {"sha": hashlib.sha256(self.files[path]).hexdigest()}, 200
        if endpoint.startswith(prefix + "git/blobs/"):
            sha = endpoint.rsplit("/", 1)[1]
            for payload in self.files.values():
                if hashlib.sha256(payload).hexdigest() == sha:
                    return {"content": base64.b64encode(payload).decode()}, 200
            raise AssertionError("unknown blob")
        if endpoint == prefix + f"pulls/{self.number}":
            return {"state": "open", "head": {"sha": self.pr_head}}, 200
        if endpoint == prefix + f"commits/{self.head}/statuses?per_page=100":
            return [], 200
        # In particular, global tree/commit inventory requests are forbidden.
        raise AssertionError("out-of-scope API request: " + endpoint)

    def run(self, command, **kwargs):
        if len(command) != 3 or command[:2] != ["gh", "api"]:
            raise AssertionError("only exact read-only gh api requests are allowed")
        value, status = self.response(command[2])
        return subprocess.CompletedProcess(
            command, 0 if status == 200 else 1,
            json.dumps(value) if status == 200 else "",
            "" if status == 200 else f"gh: fixture error (HTTP {status})",
        )

    def check_output(self, command, **kwargs):
        result = self.run(command, **kwargs)
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command, stderr=result.stderr)
        return result.stdout

    def execute(self):
        namespace = {
            "REVIEW_QUEUE_ROOT": QUEUE_ROOT, "REVIEW_QUEUE_ACK_ROOT": ACK_ROOT,
            "_canonical_sha256": canonical_sha, "_pretty_json_bytes": pretty,
            "review_queue_intent": lambda receipt, predecessor: (self.queue_path, copy.deepcopy(self.expected_intent)),
            "reassemble_diff_transport": lambda manifest, packets: b"".join(packets),
            "latest_status_matches_projection": lambda *args: self.projected,
        }
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                Path(".qikvrt/mesh-review").mkdir(parents=True)
                environment = dict(self.env, GITHUB_OUTPUT=str(Path(directory) / "output"))
                with patch.dict(os.environ, environment), \
                     patch.object(subprocess, "run", self.run), \
                     patch.object(subprocess, "check_output", self.check_output), \
                     contextlib.redirect_stdout(io.StringIO()):
                    exec(step_code(QUEUE_STEP), namespace)
                return json.loads(Path(".qikvrt/mesh-review/queue-selection.json").read_text())
            finally:
                os.chdir(previous)


class QueueSubjectScopeTests(unittest.TestCase):
    def test_queue_guard_requires_a_needed_durable_successor(self):
        source = step_source(QUEUE_STEP)
        condition = re.search(r"^        if: (.+)$", source, re.M).group(1)
        for name in ("persisted", "successor_needed", "successor_evidence_persisted"):
            self.assertIn(f"steps.ledger.outputs.{name} == 'true'", condition)
        self.assertNotIn("||", condition)

    def test_only_explicit_edge_is_read_even_with_unrelated_history(self):
        fixture = QueueFixture()
        for number in range(1000):
            fixture.files[f"{QUEUE_ROOT}/pr-{number}/{'0' * 40}/{'0' * 64}.json"] = b"invalid unrelated history"
        report = fixture.execute()
        self.assertEqual(report["state"], "WORK_UNIT")
        self.assertEqual(report["selected"]["queue_path"], fixture.queue_path)
        self.assertEqual(len(fixture.calls), 12)
        self.assertFalse(any("/git/trees/" in call for call in fixture.calls))
        self.assertFalse(any(report["completion_claims"].values()))

    def test_invalid_subject_binding_stops_before_any_api_call(self):
        invalid = {
            "SUBJECT_PR_NUMBER": "01069",
            "SUBJECT_HEAD_SHA": "main",
            "SUBJECT_PREDECESSOR_FINGERPRINT": "not-a-digest",
            "SUCCESSOR_FINGERPRINT": "not-a-digest",
            "SUCCESSOR_QUEUE_PATH": f"{QUEUE_ROOT}/pr-1071/other.json",
        }
        for key, value in invalid.items():
            with self.subTest(key=key):
                fixture = QueueFixture()
                fixture.env[key] = value
                with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_SUCCESSOR_NOT_BOUND"):
                    fixture.execute()
                self.assertEqual(fixture.calls, [])

    def test_a_self_edge_is_not_a_successor(self):
        fixture = QueueFixture()
        fixture.env["SUBJECT_PREDECESSOR_FINGERPRINT"] = fixture.fingerprint
        with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_SUCCESSOR_NOT_BOUND"):
            fixture.execute()
        self.assertEqual(fixture.calls, [])

    def test_payload_subject_drift_fails_before_reading_receipt(self):
        for key, value in (("pr_number", 1071), ("head_sha", "0" * 40),
                           ("predecessor_fingerprint", "0" * 64), ("successor_fingerprint", "0" * 64)):
            with self.subTest(key=key):
                fixture = QueueFixture()
                intent = copy.deepcopy(fixture.expected_intent)
                intent[key] = value
                fixture.files[fixture.queue_path] = pretty(intent)
                with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_SUBJECT_MISMATCH"):
                    fixture.execute()
                self.assertEqual(len(fixture.calls), 3)

    def test_missing_required_intent_is_not_an_empty_success(self):
        fixture = QueueFixture()
        del fixture.files[fixture.queue_path]
        with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_API_READ_FAILED.*HTTP 404"):
            fixture.execute()

    def test_invalid_ledger_ref_fails_closed(self):
        fixture = QueueFixture()
        fixture.ref_name = "refs/heads/main"
        with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_LEDGER_REF_INVALID"):
            fixture.execute()
        self.assertEqual(len(fixture.calls), 1)

    def test_ack_rate_limit_is_not_treated_as_absence(self):
        fixture = QueueFixture()
        fixture.failures[fixture.ack_path] = 403
        with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_API_READ_FAILED.*HTTP 403"):
            fixture.execute()

    def test_null_or_malformed_ack_is_not_treated_as_absence(self):
        for payload in (b"null", b"{broken-json"):
            with self.subTest(payload=payload):
                fixture = QueueFixture()
                fixture.files[fixture.ack_path] = payload
                with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_ACK_INVALID"):
                    fixture.execute()

    def test_acknowledged_exact_edge_is_deduplicated(self):
        fixture = QueueFixture()
        fixture.files[fixture.ack_path] = pretty({
            "repository": fixture.repo, "pr_number": fixture.number,
            "head_sha": fixture.head, "predecessor_fingerprint": fixture.fingerprint,
        })
        report = fixture.execute()
        self.assertEqual(report["state"], "EMPTY")
        self.assertFalse(any("/pulls/" in call for call in fixture.calls))

    def test_receipt_digest_validation_is_not_weakened(self):
        fixture = QueueFixture()
        receipt = json.loads(fixture.files[fixture.receipt_path])
        receipt["state"] = "WAIT"
        fixture.files[fixture.receipt_path] = pretty(receipt)
        with self.assertRaisesRegex(SystemExit, "RECURSIVE_QUEUE_BINDING_INVALID"):
            fixture.execute()

    def test_current_head_movement_prevents_dispatch_selection(self):
        fixture = QueueFixture()
        fixture.pr_head = "0" * 40
        self.assertEqual(fixture.execute()["state"], "EMPTY")


class SuccessorCausalDecisionTests(unittest.TestCase):
    def execute(self, ledger_safe: bool, causal_binding: bool):
        fixture = QueueFixture()
        environment = {
            "REPOSITORY": fixture.repo, "PR_NUMBER": str(fixture.number),
            "EXPECTED_HEAD": fixture.head, "EXPECTED_TREE": fixture.tree,
            "EXPECTED_BASE": fixture.base, "SUCCESSOR_FINGERPRINT": fixture.fingerprint,
            "SUCCESSOR_RUN_ID": "123",
        }
        def output(command, **kwargs):
            endpoint = command[2]
            if endpoint.endswith(f"/pulls/{fixture.number}"):
                return json.dumps({"head": {"sha": fixture.head}, "base": {"ref": "main"}})
            if endpoint.endswith(f"/git/commits/{fixture.head}"):
                return json.dumps({"tree": {"sha": fixture.tree}})
            if endpoint.endswith("/actions/runs/123"):
                return json.dumps({
                    "id": 123, "status": "queued", "event": "workflow_dispatch",
                    "workflow_id": 456, "path": ".github/workflows/qikvrt_requested_review_executor.yml",
                    "repository": {"full_name": fixture.repo}, "head_branch": "main",
                    "display_title": f"QIKVRT requested review pr={fixture.number} head={fixture.head} fp={fixture.fingerprint}",
                })
            if endpoint.endswith("/actions/workflows/qikvrt_requested_review_executor.yml"):
                return json.dumps({"id": 456})
            raise AssertionError("unexpected API read: " + endpoint)
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                root = Path(".qikvrt/mesh-review")
                causal_path = root / "reobservations/post-successor-dispatch/verification.json"
                causal_path.parent.mkdir(parents=True)
                causal_path.write_bytes(pretty({"ledger_safe": ledger_safe, "checks": {"causal_binding": causal_binding}}))
                error = None
                with patch.dict(os.environ, environment), \
                     patch.object(subprocess, "check_output", output), \
                     contextlib.redirect_stdout(io.StringIO()):
                    try:
                        exec(step_code(REOBSERVE_STEP), {})
                    except SystemExit as exc:
                        error = str(exc)
                report = json.loads((root / "successor-dispatch-reobservation.json").read_text())
                return report, error
            finally:
                os.chdir(previous)

    def test_failed_late_causal_check_must_change_the_decision(self):
        for ledger_safe, causal_binding in ((False, True), (True, False), (False, False)):
            with self.subTest(ledger_safe=ledger_safe, causal_binding=causal_binding):
                report, error = self.execute(ledger_safe, causal_binding)
                self.assertFalse(report["checks"]["full_causal_binding"])
                self.assertFalse(report["transport_ack_observed"])
                self.assertEqual(error, "PROGRESS_SUCCESSOR_REOBSERVATION_FAILED")

    def test_successful_transport_does_not_claim_effect_completion(self):
        report, error = self.execute(True, True)
        self.assertIsNone(error)
        self.assertTrue(report["transport_ack_observed"])
        self.assertEqual(report["effect_ack"], "PENDING_CHILD_REOBSERVATION")
        self.assertFalse(any(report["completion_claims"].values()))


if __name__ == "__main__":
    unittest.main()
