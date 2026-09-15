from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SSE = ROOT / 'tools' / 'qikvrt_live_sse.py'
MATERIALIZER = ROOT / '.github' / 'workflows' / 'qikvrt_batch04_integrity.yml'
SUCCESSOR = ROOT / '.github' / 'workflows' / 'qikvrt_pr_successor_persistence.yml'


class ProgressDeadlockGate(unittest.TestCase):
    def test_live_stream_does_not_poll_for_progress(self):
        text = SSE.read_text(encoding='utf-8')
        self.assertNotIn('time.sleep(', text)
        self.assertNotIn('--poll-seconds', text)
        self.assertNotIn('poll_seconds', text)

    def test_live_stream_is_append_driven(self):
        text = SSE.read_text(encoding='utf-8')
        self.assertIn('follow_events', text)
        self.assertIn('Last-Event-ID', text)
        self.assertIn('seek(', text)
        self.assertIn('readline()', text)

    def test_no_prompt_or_manual_dispatch_is_terminal_progress_clock(self):
        contract = (ROOT / 'policy' / 'QIKVRT_TERMINAL_MONITOR_STREAM_V1.json').read_text(encoding='utf-8')
        self.assertIn('"prompt_required": false', contract)
        self.assertIn('"repository_core_polling": false', contract)
        self.assertIn('"silent_termination_while_work_remains": false', contract)

    def test_stale_materializers_cannot_queue_ahead_of_current_head(self):
        text = MATERIALIZER.read_text(encoding='utf-8')
        self.assertIn('cancel-in-progress: true', text)

    def test_stale_successor_writers_cannot_queue_ahead_of_current_head(self):
        text = SUCCESSOR.read_text(encoding='utf-8')
        self.assertIn('cancel-in-progress: true', text)


if __name__ == '__main__':
    unittest.main()
