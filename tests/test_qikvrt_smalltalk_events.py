"""Execute the real locked Pharo reactor and its durable event continuation."""
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest import mock
import unittest

from tools.qikvrt_smalltalk import EventWorker, EventContinuation, LOCK_PATH, ROOT, build, verify
from tests.test_qikvrt_live_sse import event, append
from tools.qikvrt_live_sse import EventFile


class SmalltalkEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text())
        cls.directory = verify(Path(os.environ.get("QIKVRT_TOOLCHAIN_CACHE", ROOT / ".qikvrt/toolchains")), cls.lock)
        cls.image_dir = tempfile.TemporaryDirectory()
        cls.image = build(cls.directory, cls.lock, Path(cls.image_dir.name))

    @classmethod
    def tearDownClass(cls):
        cls.image_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.binding = {key: event()[key] for key in ("repository", "subject")}
        self.worker = self.new_worker()

    def new_worker(self):
        return EventWorker(self.directory, self.lock, self.image, self.binding)

    def tearDown(self):
        self.worker.close()
        self.temp.cleanup()

    def test_out_of_order_input_releases_only_after_explicit_predecessor(self):
        late = event("later", ["earlier"])
        response = self.worker.exchange(late)
        self.assertEqual(response["pending"], 1)
        self.assertEqual(response["completions"], [])
        result = self.worker.exchange(event("earlier"))["completions"]
        self.assertEqual([x["event_id"] for x in result], ["earlier", "later"])
        self.assertTrue(all(x["next_action"] == "REOBSERVE" for x in result))
        self.assertTrue(all(x["phase_satisfied"] is False for x in result))
        self.assertEqual(self.worker.exchange(late)["status"], "DUPLICATE")

    def test_rebinding_head_tree_base_repository_or_pr_is_rejected(self):
        for field in ("head_sha", "tree_sha", "base_sha", "pull_request", "repository"):
            with self.subTest(field=field):
                value = event(field)
                if field == "repository":
                    value[field] = "ingolf-lohmann/qik-vrt"
                elif field == "pull_request":
                    value["subject"][field] += 1
                else:
                    value["subject"][field] = "d" * 40
                response = self.worker.exchange(value)
                self.assertEqual(response["status"], "HOLD")
                self.assertEqual(response["reason"], "EXACT_SUBJECT_MISMATCH")

    def test_cycles_and_conflicting_duplicate_do_not_dispatch(self):
        self.worker.exchange(event("a", ["b"]))
        self.assertEqual(self.worker.exchange(event("b", ["a"]))["reason"], "CAUSAL_CYCLE")
        self.assertEqual(self.worker.exchange(event("a"))["reason"], "EVENT_ID_REBOUND")
        self.assertEqual(self.worker.exchange(event("self", ["self"]))["reason"], "CAUSAL_CYCLE")

    def test_d0_keeps_authority_request_separate_from_execution(self):
        for code, action in enumerate(("NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY")):
            value = event(str(code)); value["d0"] = code
            result = self.worker.exchange(value)["completions"][0]
            self.assertEqual(result["next_action"], action)
            self.assertFalse(result["effect_ack_done"])
            self.assertFalse(result["ordinary_release"])
            self.assertEqual(result["external_effect"], "NONE")

    def test_smalltalk_handler_runs_existing_kernel_without_promoting_input_claim(self):
        value = event()
        value["payload"] = {"verified_snapshot": {}, "effect_ack_done": True}
        result = self.worker.exchange(value)["completions"][0]
        self.assertEqual(result["snapshot_kernel_state"], "EFFECT_ACK_BLOCK")
        self.assertEqual(result["snapshot_d4"], 3)
        self.assertFalse(result["effect_ack_done"])

    def test_pending_continuation_survives_process_restart_and_deduplicates(self):
        path = Path(self.temp.name) / "outbox.jsonl"
        consumer = EventContinuation(self.worker, self.binding, path)
        self.assertEqual(consumer.accept(event("later", ["earlier"])), [])
        self.worker.close(); self.worker = self.new_worker()
        consumer = EventContinuation(self.worker, self.binding, path)
        self.assertEqual(consumer.recovered, [])
        results = consumer.accept(event("earlier"))
        self.assertEqual([x["event_id"] for x in results], ["earlier", "later"])
        size = path.stat().st_size
        self.assertEqual(consumer.accept(event("earlier")), [])
        self.assertEqual(path.stat().st_size, size)
        self.worker.close(); self.worker = self.new_worker()
        recovered = EventContinuation(self.worker, self.binding, path)
        self.assertEqual(recovered.recovered, [])
        self.assertEqual(len(recovered.ledger.completed), 2)

    def test_restart_recovers_crash_between_inbox_persistence_and_completion(self):
        path = Path(self.temp.name) / "outbox.jsonl"
        consumer = EventContinuation(self.worker, self.binding, path)
        consumer.ledger.append("ACCEPTED", "one", accepted={"event": event()})
        self.worker.close(); self.worker = self.new_worker()
        recovered = EventContinuation(self.worker, self.binding, path)
        self.assertEqual([x["event_id"] for x in recovered.recovered], ["one"])
        self.assertEqual(len(recovered.ledger.completed), 1)

    def test_file_notification_runs_pharo_and_persists_causal_continuation(self):
        path = Path(self.temp.name) / "events.jsonl"
        reader = EventFile(path)
        consumer = EventContinuation(self.worker, self.binding, Path(self.temp.name) / "outbox.jsonl")
        completed = threading.Event()
        results, errors = [], []
        def consume():
            try:
                for value in reader.follow():
                    results.extend(consumer.accept(value))
                    if len(results) == 2:
                        completed.set()
            except BaseException as error:
                errors.append(error)
                completed.set()
        thread = threading.Thread(target=consume)
        thread.start()
        try:
            append(path, event("later", ["earlier"]))
            append(path, event("earlier"))
            self.assertTrue(completed.wait(5))
            self.assertEqual(errors, [])
            self.assertEqual([x["event_id"] for x in results], ["earlier", "later"])
            self.assertEqual(set(consumer.ledger.completed), {"earlier", "later"})
        finally:
            reader.stop()
            thread.join(2)
            reader.close()
        self.assertFalse(thread.is_alive())

    def test_persistence_failure_requires_restart(self):
        consumer = EventContinuation(self.worker, self.binding, Path(self.temp.name) / "outbox.jsonl")
        with mock.patch.object(consumer.ledger, "append", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                consumer.accept(event())
        with self.assertRaisesRegex(ValueError, "requires restart"):
            consumer.accept(event("two"))

    def test_changed_runtime_cannot_inherit_ledger(self):
        path = Path(self.temp.name) / "outbox.jsonl"
        EventContinuation(self.worker, self.binding, path).accept(event())
        self.worker.close()
        self.worker = self.new_worker()
        self.worker.runtime_binding = {"different": "runtime"}
        with self.assertRaises(ValueError):
            EventContinuation(self.worker, self.binding, path)

    def test_ledger_tampering_blocks_restart(self):
        path = Path(self.temp.name) / "outbox.jsonl"
        consumer = EventContinuation(self.worker, self.binding, path)
        consumer.accept(event())
        path.write_text(path.read_text().replace('REOBSERVE', 'REQUEST_AUTHORITY'))
        self.worker.close(); self.worker = self.new_worker()
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            EventContinuation(self.worker, self.binding, path)


if __name__ == "__main__":
    unittest.main()
