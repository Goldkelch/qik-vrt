import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MegaSTTcpIpProofContract(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.p = json.loads(Path('policy/MLP_TOS_MEGAST_TCPIP_ROUNDTRIP_V1.json').read_text())

    def test_source_is_exactly_bound(self):
        self.assertEqual(self.p['source']['pr'], 744)
        self.assertEqual(self.p['source']['head'], '8141a304c1f25f548b0094c0bc4b61f6ae5c2989')
        self.assertEqual(self.p['source']['tree'], '2caca35947cd4824834dd646e1c3a76b96d00c89')
        self.assertEqual(self.p['source']['mlp_tos_sha256'], '5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e')

    def test_host_network_is_insufficient(self):
        self.assertTrue(self.p['boundaries']['host_network_is_not_guest_network'])
        self.assertIn('GitHub runner has network access', self.p['insufficient_evidence'])
        self.assertIn('host-side curl or socket succeeds', self.p['insufficient_evidence'])

    def test_roundtrip_requires_guest_response_observation(self):
        chain = self.p['required_observation_chain']
        self.assertIn('guest initiates TCP connection to a controlled endpoint', chain)
        self.assertIn('controlled endpoint observes connection and exact nonce-bearing payload', chain)
        self.assertIn('guest observes the returned response', chain)
        self.assertEqual(self.p['result_states']['tcp_connect_without_response'], 'TRANSPORT_ACK_ONLY')
        self.assertEqual(self.p['result_states']['nonce_response_observed_by_guest'], 'GUEST_TCP_IP_ROUNDTRIP_OBSERVED')

    def test_claim_boundaries_remain_fail_closed(self):
        self.assertFalse(self.p['boundaries']['effect_ack_done'])
        self.assertFalse(self.p['boundaries']['physical_megast_execution'])
        self.assertTrue(self.p['boundaries']['controlled_local_tcp_endpoint_is_sufficient'])

    def test_qiknet_prg_builder_wraps_position_independent_text(self):
        text = bytes.fromhex('4e714e75')
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            text_path = tmp_path / 'qiknet.text'
            output_path = tmp_path / 'QIKNET.PRG'
            text_path.write_bytes(text)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(self.root / 'tools' / 'build_qiknet_prg.py'),
                    '--text',
                    str(text_path),
                    '--output',
                    str(output_path),
                ],
                check=True,
                cwd=self.root,
                capture_output=True,
                text=True,
            )
            image = output_path.read_bytes()
        self.assertEqual(completed.stdout, 'QIKNET.PRG bytes=32 text=4\n')
        self.assertEqual(len(image), 28 + len(text))
        header = struct.unpack('>HIIIIIIH', image[:28])
        self.assertEqual(header, (0x601A, len(text), 0, 0, 0, 0, 0, 1))
        self.assertEqual(image[28:], text)


if __name__ == '__main__':
    unittest.main()
