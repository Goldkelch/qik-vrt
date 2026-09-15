# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic receipt and actual local Linux/SSE regression tests."""
import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("qikvrt_live_sse", Path(__file__).resolve().parents[1] / "tools/qikvrt_live_sse.py")
sse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sse)


def receipt(eid, **overrides):
    return dict(schema="qikvrt_live_event_v1", event_id=eid,
                observed_at="2026-09-15T13:00:00Z", repository="Goldkelch/qik-vrt",
                subject={"kind": "trusted_main", "head_sha": "a" * 40},
                phase="P6", verb="READBACK", causal_state="HOLD",
                source={"type": "workflow_run", "id": "1"},
                productive_effect=False, effect_ack="PENDING", payload={}, **overrides)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "events.jsonl"

    def write(self, *events):
        self.path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")

    def connect(self, cursor=None):
        handler = type("TestHandler", (sse.Handler,), {"events_path": self.path})
        server = sse.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def close_server():
            server.shutdown()
            server.server_close()
            thread.join(2)
        self.addCleanup(close_server)
        conn = http.client.HTTPConnection(*server.server_address, timeout=2)
        self.addCleanup(conn.close)
        conn.request("GET", "/events", headers={"Last-Event-ID": cursor} if cursor else {})
        response = conn.getresponse()
        self.addCleanup(response.close)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "text/event-stream")
        return response

    def frame(self, response):
        lines = []
        while True:
            line = response.readline().decode()
            if line == "\n" or line == "":
                return "".join(lines)
            lines.append(line)

    def test_resume_deduplicates_and_preserves_order(self):
        self.write(receipt("a"), receipt("a"), receipt("b"))
        self.assertEqual([e["event_id"] for e in sse.iter_events(self.path, "a")], ["b"])
        self.assertEqual(list(sse.iter_events(self.path, "b")), [])

    def test_unknown_or_missing_cursor_is_gap(self):
        self.write(receipt("a"))
        with self.assertRaisesRegex(sse.ReplayGap, "CURSOR_NOT_FOUND"):
            list(sse.iter_events(self.path, "lost"))
        self.path.unlink()
        with self.assertRaisesRegex(sse.ReplayGap, "JOURNAL_MISSING"):
            list(sse.iter_events(self.path, "a"))

    def test_partial_tail_is_not_delivered(self):
        self.write(receipt("a"))
        with self.path.open("a") as fh:
            fh.write(json.dumps(receipt("b")))
        self.assertEqual(list(sse.iter_events(self.path, "a")), [])
        with self.path.open("a") as fh:
            fh.write("\n")
        self.assertEqual([e["event_id"] for e in sse.iter_events(self.path, "a")], ["b"])

    def test_malformed_complete_record_cannot_release_partial_replay(self):
        self.write(receipt("a"))
        with self.path.open("a") as fh:
            fh.write("{bad}\n")
        with self.assertRaisesRegex(sse.ReplayGap, "INVALID_JSONL"):
            next(sse.iter_events(self.path))

    def test_conflicting_id_and_sse_injection_fail_closed(self):
        changed = receipt("a")
        changed["verb"] = "HOLD"
        self.write(receipt("a"), changed)
        with self.assertRaisesRegex(sse.ReplayGap, "EVENT_ID_CONFLICT"):
            list(sse.iter_events(self.path))
        self.assertFalse(sse.valid_event(receipt("bad\nid: forged")))
        self.assertFalse(sse.valid_event([]))

    def test_notification_catches_creation_and_atomic_replace(self):
        watcher = sse.JournalWatch(self.path)
        self.addCleanup(watcher.close)
        self.write(receipt("a"))
        self.assertTrue(watcher.wait(1))
        self.assertFalse(watcher.wait(0))
        replacement = self.path.with_suffix(".new")
        replacement.write_text(json.dumps(receipt("b")) + "\n")
        replacement.replace(self.path)
        self.assertTrue(watcher.wait(1))

    def test_unrelated_file_is_not_journal_invalidation(self):
        watcher = sse.JournalWatch(self.path)
        self.addCleanup(watcher.close)
        (self.path.parent / "unrelated").write_text("change")
        self.assertFalse(watcher.wait(1))

    def test_no_notification_backend_has_no_polling_fallback(self):
        with patch.object(sse.sys, "platform", "unsupported"):
            with self.assertRaisesRegex(OSError, "BACKEND_UNAVAILABLE"):
                sse.JournalWatch(self.path)
        source = Path(SPEC.origin).read_text()
        self.assertNotIn("time.sleep", source)
        self.assertNotIn("poll_seconds", source)

    def test_real_sse_bootstrap_append_and_boundaries(self):
        self.write(receipt("a"))
        response = self.connect()
        self.assertIn("id: a\nevent: qikvrt", self.frame(response))
        self.assertIn('"last_event_id":"a"', self.frame(response))
        with self.path.open("a") as fh:
            fh.write(json.dumps(receipt("b")) + "\n")
        self.assertIn("id: b\nevent: qikvrt", self.frame(response))
        self.assertIn('"last_event_id":"b"', self.frame(response))

    def test_real_sse_resume_and_gap(self):
        self.write(receipt("a"), receipt("b"))
        response = self.connect("a")
        self.assertIn("id: b\n", self.frame(response))
        self.assertIn("qikvrt-ready", self.frame(response))
        lost = self.connect("missing")
        frame = self.frame(lost)
        self.assertIn("event: qikvrt-gap", frame)
        self.assertIn("CURSOR_NOT_FOUND", frame)
        self.assertNotIn("id:", frame)

    def test_idle_keepalives_never_rescan_journal(self):
        self.write(receipt("a"))
        # Timeout the transport only; deterministic, with no sleep in this test.
        with patch.object(sse.JournalWatch, "wait", side_effect=[False, False, sse.ReplayGap("end")]), \
             patch.object(sse, "iter_events", wraps=sse.iter_events) as scan:
            response = self.connect()
            self.frame(response)
            self.frame(response)
            self.assertEqual(self.frame(response), ": keepalive\n")
            self.assertEqual(self.frame(response), ": keepalive\n")
            self.assertIn("qikvrt-gap", self.frame(response))
            self.assertEqual(scan.call_count, 1)


if __name__ == "__main__":
    unittest.main()
