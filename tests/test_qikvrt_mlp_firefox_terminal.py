import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import qikvrt_mlp_firefox_terminal as m


class FirefoxTerminalTests(unittest.TestCase):
    def test_policy_is_terminal_not_monitor_and_binds_proven_tcpip(self):
        p=json.loads(Path('policy/MLP_FIREFOX_TERMINAL_V1.json').read_text())
        self.assertEqual(p['terminal']['mode'], 'INTERACTIVE_TERMINAL')
        self.assertFalse(p['terminal']['monitor_only'])
        self.assertTrue(p['terminal']['protected_effects_require_effect_ack'])
        self.assertFalse(p['os_portability']['all_historical_and_future_operating_systems_guaranteed'])
        self.assertEqual(p['source']['tcpip_head'], 'a71484ba02f6ebe9169af5a291244e99468caec3')
        self.assertEqual(p['source']['tcpip_tree'], 'b45556a6c4ea2d9946c73264c1ed47d4f3128a76')
        self.assertTrue(p['source']['guest_tcp_ip_roundtrip_observed'])

    def test_stage_makes_exact_mlp_prg(self):
        source=Path('MLP.TOS/MLP.TOS')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), m.MLP_SHA256)
        with tempfile.TemporaryDirectory() as td:
            out=m.stage(source, Path(td))
            target=Path(out['desktop_program'])
            self.assertEqual(target.name, 'MLP.PRG')
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertFalse(out['executed'])

    def test_launch_requires_exact_frame_and_does_not_invent_ack(self):
        with tempfile.TemporaryDirectory() as td:
            frame=Path(td)/'MLP.OPEN'
            frame.write_bytes(b'bad')
            with self.assertRaises(SystemExit):
                m.validate_frame(frame)

    def test_dry_run_separates_requested_execution_observation_ack(self):
        with tempfile.TemporaryDirectory() as td:
            frame=Path(td)/'MLP.OPEN'
            payload=bytes.fromhex('7203740170034e75')
            with mock.patch.object(m, 'FRAME_SHA256', hashlib.sha256(payload).hexdigest()), \
                 mock.patch.object(m, 'firefox_binary', return_value='firefox'):
                frame.write_bytes(payload)
                out=m.launch(frame, m.DEFAULT_URL, None, True)
                self.assertTrue(out['requested'])
                self.assertFalse(out['executed'])
                self.assertFalse(out['browser_execution_observed'])
                self.assertFalse(out['effect_ack_done'])
                self.assertFalse(out['monitor_only'])


if __name__ == '__main__':
    unittest.main()
