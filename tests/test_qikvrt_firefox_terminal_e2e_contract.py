import json
import unittest
from pathlib import Path


class FirefoxTerminalE2EContract(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path('policy/MLP_FIREFOX_EFFECT_ACK_E2E_V1.json').read_text())
        self.options = Path('browser/firefox/qikvrt-terminal/options.js').read_text()
        self.harness = Path('tools/qikvrt_firefox_terminal_e2e.py').read_text()
        self.manifest = json.loads(Path('browser/firefox/qikvrt-terminal/manifest.json').read_text())
        self.background = Path('browser/firefox/qikvrt-terminal/background.js').read_text()

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

    def test_firefox_system_context_is_enabled_at_geckodriver_boundary(self):
        self.assertIn('--allow-system-access', self.harness)
        self.assertNotIn('"args": ["-headless", "-remote-allow-system-access"]', self.harness)
        self.assertIn('moz/context', self.harness)

    def test_loopback_permission_is_valid_but_runtime_port_remains_exact(self):
        hosts = self.manifest['host_permissions']
        self.assertIn('http://127.0.0.1/*', hosts)
        self.assertNotIn('http://127.0.0.1:8771/*', hosts)
        self.assertNotIn('<all_urls>', hosts)
        self.assertNotIn('http://*/*', hosts)
        csp = self.manifest['content_security_policy']['extension_pages']
        self.assertIn('http://127.0.0.1:8771', csp)
        self.assertIn('const E2E_BACKEND = "http://127.0.0.1:8771";', self.options)
        self.assertIn('const E2E_HOST_PERMISSION = "http://127.0.0.1/*";', self.options)
        self.assertIn('origins: [E2E_HOST_PERMISSION]', self.options)
        self.assertNotIn('origins: [`${E2E_BACKEND}/*`]', self.options)
        self.assertIn('const DEFAULT_BACKEND = "http://127.0.0.1:8771";', self.background)
        self.assertIn('new Set(["http://127.0.0.1:8771", "http://localhost:8771"])', self.background)

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
