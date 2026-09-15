from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'policy' / 'QIKVRT_TERMINAL_MONITOR_STREAM_V1.json'


class TerminalMonitorStreamE2E(unittest.TestCase):
    def test_terminal_stream_contract_exists(self):
        self.assertTrue(CONTRACT.exists(), 'continuous terminal monitor contract is missing')

    def test_stream_forbids_prompt_driven_and_polling_continuation(self):
        text = CONTRACT.read_text(encoding='utf-8')
        self.assertIn('repository_event', text)
        self.assertIn('visible_append_without_user_prompt', text)
        self.assertIn('effect_ack_done', text)
        self.assertIn('prompt_required', text)
        self.assertIn('false', text.lower())
        self.assertIn('repository_core_polling', text)

    def test_stream_requires_multiple_consecutive_appends(self):
        text = CONTRACT.read_text(encoding='utf-8')
        self.assertIn('multiple_consecutive_transitions', text)
        self.assertIn('append_only', text)
        self.assertIn('serialized_transputer_stream', text)


if __name__ == '__main__':
    unittest.main()
