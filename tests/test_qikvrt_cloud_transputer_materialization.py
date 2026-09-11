# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CloudTransputerMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT/'policy/QIKVRT_CLOUD_TRANSPUTER_V1.json').read_text())
        cls.dockerfile = (ROOT/'deploy/universal-terminal/Dockerfile').read_text()
        cls.compose = (ROOT/'deploy/universal-terminal/compose.yaml').read_text()
        cls.service = (ROOT/'deploy/universal-terminal/service-entrypoint.sh').read_text()

    def test_exact_five_state_d0_mapping(self):
        self.assertEqual(self.policy['protocol_contract']['decision_codes'], {
            'EFFECT_NACK':0, 'EFFECT_ACK_CONTINUE':1, 'EFFECT_ACK_ISOLATE':2,
            'EFFECT_ACK_BLOCK':3, 'EFFECT_ACK_DONE':4})

    def test_mc68000_contract_and_overlay(self):
        self.assertEqual(self.policy['architecture'], 'MC68000')
        self.assertEqual(self.policy['overlay_model']['banks'], 4)
        self.assertTrue(self.policy['overlay_model']['fence_required'])
        self.assertTrue(self.policy['overlay_model']['instruction_prefetch_flush'])

    def test_ip_bootstrap_contract(self):
        value=self.policy['ip_bootstrap']
        self.assertEqual(value['subnet'], '10.73.0.0/24')
        self.assertEqual(value['discovery_port'], 7331)
        self.assertEqual(value['route'], ['discover','offer','request','data','done'])
        self.assertEqual(value['checksum'], 'FNV1A32')

    def test_image_contains_required_runtime_planes(self):
        for token in ('firefox-esr','novnc','openssh-server','postgresql','snmpd','bind9',
                      'gcc-m68k-linux-gnu','qemu-user','qikvrt-m68k-selftest'):
            self.assertIn(token, self.dockerfile)

    def test_compose_materializes_fixed_mesh(self):
        for token in ('10.73.0.0/24','10.73.0.2','10.73.0.3','10.73.0.4','10.73.0.6',
                      'qikvrt-universal-terminal','qikvrt-sqld','qikvrt-mirror','qikvrt-mc68000',
                      'qikvrt-smtpd','qikvrt-dnsd','qikvrt-snmpd','qikvrt-sshd'):
            self.assertIn(token, self.compose)

    def test_personal_posix_is_fail_closed_when_required(self):
        self.assertIn('QIKVRT_REQUIRE_PERSONAL_POSIX', self.service)
        self.assertIn('PERSONAL_POSIX_UNBOUND', self.service)
        self.assertIn('m68k-linux-gnu-gcc', self.service)
        self.assertIn('qemu-m68k', self.service)

    def test_0124_term_is_not_invented(self):
        self.assertEqual(self.policy['logic_0124_source_status'], 'NOT_RECOVERED_VERBATIM')

if __name__ == '__main__':
    unittest.main()
