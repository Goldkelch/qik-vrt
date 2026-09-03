# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import pathlib
import tempfile
import unittest

from tools.qikvrt_requested_review_executor import (
    _canonical_sha256,
    _pretty_json_bytes,
    build_diff_transport,
    review_queue_ack,
    review_queue_intent,
)
from tools.qikvrt_requested_review_stale_work_unit_reaper import (
    RecursiveQueueEvidenceError,
    classify_queue_work_unit,
    classify_run,
    load_unacknowledged_queue,
)


HEAD = "a" * 40
TREE = "d" * 40
MAIN = "b" * 40
FP = "c" * 64
PREDECESSOR = "e" * 64
REPOSITORY = "Goldkelch/qik-vrt"


def run(event="workflow_dispatch", status="pending", head=HEAD):
    return {
        "id": 17,
        "event": event,
        "status": status,
        "display_title": f"QIKVRT requested review pr=922 head={head} fp={FP}",
    }


def pr(head=HEAD, base=MAIN, state="open"):
    return {
        "number": 922,
        "state": state,
        "head": {"sha": head},
        "base": {"sha": base},
    }


def write_bytes(root, relative, value):
    path = root.joinpath(*pathlib.PurePosixPath(relative).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def materialize_queue(root, *, acknowledged=False):
    diff = (
        b"diff --git a/example.txt b/example.txt\n"
        b"new file mode 100644\n"
        b"index 0000000..1111111\n"
        b"--- /dev/null\n"
        b"+++ b/example.txt\n"
        b"@@ -0,0 +1 @@\n"
        b"+queue\n"
    )
    receipt_path = f"state/mesh/reviews/pr-922/{HEAD}/{FP}.json"
    diff_base = f"state/mesh/reviews/pr-922/{HEAD}/{FP}.diff"
    transport = build_diff_transport(diff, diff_base)
    receipt = {
        "repository": REPOSITORY,
        "pr_number": 922,
        "head_sha": HEAD,
        "tree_sha": TREE,
        "base_sha": MAIN,
        "state": "COMMENT_WITH_BLOCKER",
        "evidence_fingerprint": FP,
        "ledger_path": receipt_path,
        "ledger_diff_path": transport["manifest_path"],
        "diff_transport": transport,
        "diff_sha256": transport["sha256"],
        "diff_bytes": len(diff),
    }
    receipt["receipt_payload_sha256"] = _canonical_sha256(receipt)
    write_bytes(root, receipt_path, _pretty_json_bytes(receipt))
    write_bytes(
        root,
        transport["manifest_path"],
        _pretty_json_bytes(transport),
    )
    for packet in transport["packets"]:
        start = packet["offset"]
        stop = start + packet["bytes"]
        write_bytes(root, packet["path"], diff[start:stop])

    queue_path, intent = review_queue_intent(receipt, PREDECESSOR)
    write_bytes(root, queue_path, _pretty_json_bytes(intent))
    if acknowledged:
        ack_path, ack = review_queue_ack(
            REPOSITORY,
            922,
            HEAD,
            intent["successor_fingerprint"],
            "f" * 64,
        )
        write_bytes(root, ack_path, _pretty_json_bytes(ack))
    return intent


class RequestedReviewStaleWorkUnitReaperTests(unittest.TestCase):
    def test_stale_head_recursive_child_is_cancelled(self):
        value = classify_run(run(), pr(head="d" * 40), MAIN)
        self.assertTrue(value["cancel"])
        self.assertEqual(value["first_blocker"], "STALE_HEAD")
        self.assertEqual(
            value["next_action"],
            "CANCEL_STALE_RECURSIVE_TRANSPORT_ONLY",
        )

    def test_base_drift_recursive_child_is_cancelled(self):
        value = classify_run(run(), pr(base="e" * 40), MAIN)
        self.assertTrue(value["cancel"])
        self.assertEqual(value["first_blocker"], "BASE_DRIFT")
        self.assertEqual(
            value["next_action"],
            "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        )

    def test_current_recursive_child_is_kept(self):
        value = classify_run(run(), pr(), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["state"], "KEEP")

    def test_in_progress_child_is_not_cancelled(self):
        value = classify_run(run(status="in_progress"), pr(head="d" * 40), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["state"], "KEEP")

    def test_native_pr_observation_is_never_cancelled(self):
        value = classify_run(run(event="pull_request_target"), pr(base="e" * 40), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["state"], "KEEP")

    def test_unbound_title_fails_closed_without_cancellation(self):
        candidate = run()
        candidate["display_title"] = "unbound"
        value = classify_run(candidate, pr(), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(
            value["first_blocker"],
            "RECURSIVE_WORK_UNIT_TITLE_UNBOUND",
        )

    def test_local_queue_scan_reassembles_exact_durable_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            intent = materialize_queue(root)
            values = load_unacknowledged_queue(root, REPOSITORY)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["intent"], intent)
        self.assertEqual(values[0]["expected_status_state"], "failure")

    def test_acknowledged_queue_intent_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            materialize_queue(root, acknowledged=True)
            values = load_unacknowledged_queue(root, REPOSITORY)
        self.assertEqual(values, [])

    def test_noncanonical_queue_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            intent = materialize_queue(root)
            queue_path = root / (
                f"state/mesh/review-queue/pr-922/{HEAD}/"
                f"{intent['successor_fingerprint']}.json"
            )
            queue_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(RecursiveQueueEvidenceError):
                load_unacknowledged_queue(root, REPOSITORY)

    def queue_unit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            materialize_queue(root)
            return load_unacknowledged_queue(root, REPOSITORY)[0]

    def test_live_unprojected_queue_unit_dispatches_exactly_once(self):
        value = classify_queue_work_unit(
            self.queue_unit(),
            pr(),
            MAIN,
            [],
            [],
        )
        self.assertTrue(value["dispatch"])
        self.assertEqual(value["state"], "REOBSERVE")
        self.assertEqual(value["d0"], 2)

    def test_any_active_requested_review_writer_holds_dispatch(self):
        active = {
            "id": 99,
            "status": "in_progress",
            "event": "workflow_dispatch",
            "display_title": (
                f"QIKVRT requested review pr=922 head={HEAD} fp={FP}"
            ),
        }
        value = classify_queue_work_unit(
            self.queue_unit(),
            pr(),
            MAIN,
            [],
            [active],
        )
        self.assertFalse(value["dispatch"])
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["d0"], 1)
        self.assertEqual(
            value["first_blocker"],
            "REQUESTED_REVIEW_WRITER_ACTIVE",
        )

    def test_latest_exact_status_projection_prevents_redispatch(self):
        work_unit = self.queue_unit()
        fingerprint = work_unit["intent"]["successor_fingerprint"]
        statuses = [
            {
                "id": 1,
                "context": "QIKVRT requested review execution",
                "state": "failure",
                "description": f"Bound review receipt fp={fingerprint}",
                "created_at": "2026-09-03T00:00:00Z",
                "updated_at": "2026-09-03T00:00:00Z",
            }
        ]
        value = classify_queue_work_unit(
            work_unit,
            pr(),
            MAIN,
            statuses,
            [],
        )
        self.assertFalse(value["dispatch"])
        self.assertEqual(value["state"], "ALREADY_PROJECTED")
        self.assertEqual(value["next_action"], "AWAIT_DURABLE_QUEUE_ACK")

    def test_queue_unit_with_base_drift_is_not_dispatched(self):
        value = classify_queue_work_unit(
            self.queue_unit(),
            pr(base="f" * 40),
            MAIN,
            [],
            [],
        )
        self.assertFalse(value["dispatch"])
        self.assertEqual(value["first_blocker"], "BASE_DRIFT")


class RequestedReviewStaleWorkUnitReaperWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = pathlib.Path(
            ".github/workflows/"
            "qikvrt_requested_review_stale_work_unit_reaper.yml"
        ).read_text(encoding="utf-8")

    def test_recovery_is_event_driven_and_uses_local_ledger_checkout(self):
        self.assertIn('workflows:\n      - "QIKVRT requested review executor"', self.text)
        self.assertIn("ref: qikvrt/mesh-review-ledger-v1", self.text)
        self.assertIn(
            "Check out durable Mesh review queue without blob API hydration",
            self.text,
        )
        self.assertNotIn("schedule:", self.text)

    def test_installation_quota_exhaustion_is_persisted_as_hold(self):
        self.assertIn(
            "TRUSTED_MAIN_RECURSIVE_REVIEW_QUEUE_",
            self.text,
        )
        self.assertIn(
            "GITHUB_INSTALLATION_API_RATE_LIMIT_EXHAUSTED",
            self.text,
        )
        self.assertIn(
            "QIKVRT_GITHUB_INSTALLATION_RATE_LIMIT_BACKOFF_SECONDS",
            self.text,
        )
        self.assertIn('"state": "HOLD"', self.text)
        self.assertIn('"d0": 1', self.text)

    def test_only_one_exact_executor_transport_is_dispatched(self):
        self.assertIn(
            "qikvrt_requested_review_executor.yml/dispatches",
            self.text,
        )
        self.assertIn("inputs[fingerprint]", self.text)
        self.assertIn("REOBSERVE_TRANSPORT_WITHOUT_REDISPATCH", self.text)
        self.assertNotIn("repos/{repo}/git/blobs/", self.text)

    def test_permissions_reuse_existing_write_scope(self):
        self.assertEqual(self.text.count("actions: write"), 1)
        self.assertIn("statuses: read", self.text)
        self.assertNotIn("statuses: write", self.text)


if __name__ == "__main__":
    unittest.main()
