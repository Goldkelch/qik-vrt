import json
import unittest
from pathlib import Path


class FirefoxTerminalE2EContract(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path('policy/MLP_FIREFOX_EFFECT_ACK_E2E_V1.json').read_text())
        self.options = Path('browser/firefox/qikvrt-terminal/options.js').read_text()
        self.harness = Path('tools/qikvrt_firefox_terminal_e2e.py').read_text()

    def test_exact_predecessor_and_tcpip_binding(self):
        self.assertEqual(self.policy['source']['pr'], 748)
        self.assertEqual(self.policy['source']['head'], 'e48f50a0419bea9bbdcca47a7673356d372f7400')
        self.assertEqual(self.policy['source']['tcpip_head'], 'a71484ba02f6ebe9169af5a291244e99468caec3')

    def test_extension_executes_actual_prepare_and_commit(self):
        self.assertIn('DISCOVER_EFFECT_ACK', self.options)
        self.assertIn('PREPARE_EFFECT', self.options)
        self.assertIn('COMMIT_EFFECT', self.options)
        self.assertIn('E2E_DONE:', self.options)
        self.assertIn('moz/addon/install', self.harness)

    def test_effect_ack_scope_stays_bounded(self):
        b = self.policy['boundaries']
        self.assertTrue(b['loopback_backend_only'])
        self.assertEqual(b['external_effect'], 'NONE')
        self.assertFalse(b['repository_write_effect'])
        self.assertFalse(b['publication_effect'])
        self.assertFalse(b['physical_megast_execution'])
        self.assertEqual(b['effect_ack_done_scope'], 'BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY')


if __name__ == '__main__':
    unittest.main()
