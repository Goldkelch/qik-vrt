#!/usr/bin/env python3
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tail", ROOT / "tools/qikvrt_live_tail_stream.py")
tail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tail)


class LiveTailTests(unittest.TestCase):
    def test_only_events_after_cursor_are_emitted(self):
        body = """<!-- qikvrt-universal-terminal-live-surface-v1 -->
## Live event journal
- `2026-09-15T13:00:00Z` **OBSERVE** · `PR #1096 @ aaa` · opened · event `pull_request:1:1`
- `2026-09-15T13:01:00Z` **EFFECT** · `PR #1096 @ aaa` · CI → success (u) · event `workflow_run:2:1`
- `2026-09-15T13:02:00Z` **CLASSIFY** · `PR #1096 @ aaa` · gate → failure (u) · event `workflow_run:3:1`
"""
        items = tail.events(body)
        self.assertEqual([x["event"] for x in tail.unseen(items, "workflow_run:2:1")], ["workflow_run:3:1"])

    def test_missing_old_cursor_fails_closed(self):
        body = "- `2026-09-15T13:02:00Z` **OBSERVE** · `PR #1 @ a` · x · event `e:3:1`"
        with self.assertRaises(SystemExit) as cm:
            tail.unseen(tail.events(body), "e:1:1")
        self.assertEqual(str(cm.exception), "CURSOR_EVENT_NOT_IN_VISIBLE_JOURNAL")

    def test_cursor_is_atomic_and_reconstructible(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "cursor.json"
            expected = {"schema": "qikvrt_live_tail_cursor_v1", "last_event": "e:1:1"}
            tail.save_cursor(path, expected)
            self.assertEqual(tail.load_cursor(path), expected)

    def test_surface_selection_uses_marker(self):
        comments = [{"body": "other"}, {"body": tail.MARKER + "\n## Live event journal"}]
        self.assertIs(tail.find_surface(comments), comments[1])


if __name__ == "__main__":
    unittest.main()
