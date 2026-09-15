"""Real file notifications and SSE resume, without a polling test double."""
import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from tools.qikvrt_live_sse import EventFile, EventHub, Handler, ThreadingHTTPServer


def event(event_id="one", predecessors=()):
    return {"schema": "qikvrt_live_event_v1", "event_id": event_id,
            "observed_at": "2026-09-15T00:00:00Z", "repository": "Goldkelch/qik-vrt",
            "subject": {"kind": "pull_request", "pull_request": 1079,
                        "head_sha": "a" * 40, "tree_sha": "b" * 40, "base_sha": "c" * 40},
            "phase": "P2", "verb": "READBACK", "causal_state": "REOBSERVE", "d0": 2,
            "source": {"type": "workflow_run", "id": event_id},
            "predecessor_event_ids": list(predecessors), "productive_effect": False,
            "effect_ack": "PENDING", "payload": {}}


def append(path, value):
    with path.open("a") as stream:
        stream.write(json.dumps(value) + "\n")


class EventIngressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_idle_does_not_rescan_and_create_wakes_once(self):
        reader = EventFile(self.path)
        initial, received = threading.Event(), threading.Event()
        output = []
        original = reader.read_new
        def read():
            result = original()
            initial.set()
            return result
        def consume():
            for value in reader.follow():
                output.append(value)
                received.set()
        with mock.patch.object(reader, "read_new", side_effect=read) as calls:
            thread = threading.Thread(target=consume)
            thread.start()
            try:
                self.assertTrue(initial.wait(2))
                self.assertFalse(received.wait(0.1))
                self.assertEqual(calls.call_count, 1)
                append(self.path, event())
                self.assertTrue(received.wait(2))
                self.assertEqual(output, [event()])
            finally:
                reader.stop()
                thread.join(2)
                reader.close()
        self.assertFalse(thread.is_alive())

    def test_partial_record_is_not_consumed(self):
        raw = json.dumps(event()).encode() + b"\n"
        self.path.write_bytes(raw[:-2])
        reader = EventFile(self.path)
        try:
            self.assertEqual(reader.read_new(), [])
            with self.path.open("ab") as stream:
                stream.write(raw[-2:])
            self.assertEqual(reader.read_new(), [event()])
            self.assertEqual(reader.read_new(), [])
        finally:
            reader.close()

    def test_truncation_and_replacement_stop_the_reader(self):
        for mode in ("truncate", "replace"):
            with self.subTest(mode=mode):
                self.path.write_text(json.dumps(event()) + "\n")
                reader = EventFile(self.path)
                try:
                    reader.read_new()
                    if mode == "replace":
                        self.path.unlink()
                    self.path.write_text("")
                    with self.assertRaises(ValueError):
                        reader.read_new()
                finally:
                    reader.close()

    def test_duplicate_json_keys_and_oversized_record_fail_closed(self):
        for raw in ('{"schema":"x","schema":"y"}\n', 'x' * 65537):
            self.path.write_text(raw)
            reader = EventFile(self.path)
            try:
                with self.assertRaises(ValueError):
                    reader.read_new()
            finally:
                reader.close()

    def test_sse_resume_skips_exact_cursor_and_unknown_cursor_conflicts(self):
        append(self.path, event("one"))
        append(self.path, event("two"))
        hub = EventHub(self.path)
        class BoundHandler(Handler):
            pass
        BoundHandler.hub = hub
        server = ThreadingHTTPServer(("127.0.0.1", 0), BoundHandler)
        connection = http.client.HTTPConnection(*server.server_address, timeout=2)
        try:
            for cursor, status in (("absent", 409), ("one", 200)):
                thread = threading.Thread(target=server.handle_request)
                thread.start()
                connection.request("GET", "/events", headers={"Last-Event-ID": cursor})
                response = connection.getresponse()
                self.assertEqual(response.status, status)
                if status == 200:
                    self.assertEqual(response.fp.readline(), b"id: two\n")
                else:
                    response.read()
                response.close()
                connection.close()
                thread.join(2)
        finally:
            hub.stop()
            hub.reader.close()
            connection.close()
            server.server_close()

    def test_duplicate_id_is_deduplicated_but_rebinding_rejected(self):
        hub = EventHub(self.path)
        try:
            hub.add(event())
            hub.add(event())
            self.assertEqual(len(hub.events), 1)
            other = copy.deepcopy(event())
            other["payload"] = {"changed": True}
            with self.assertRaises(ValueError):
                hub.add(other)
        finally:
            hub.reader.close()


if __name__ == "__main__":
    unittest.main()
