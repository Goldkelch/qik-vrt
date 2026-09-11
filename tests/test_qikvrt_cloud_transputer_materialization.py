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
        cls.probe = (ROOT/'src/cloud_transputer/m68k_contract_probe.c').read_text()

    def test_d0_boundary_is_exact_four_state_machine(self):
        self.assertEqual(self.policy['boundary_contract']['decision_codes'], {
            'NOOP':0, 'HOLD':1, 'REOBSERVE':2, 'REQUEST_AUTHORITY':3})
        self.assertEqual(self.policy['boundary_contract']['d0_width_bits'], 2)
        self.assertEqual(self.policy['boundary_contract']['d0_mask'], 3)

    def test_0124_is_binary_weight_composition_not_five_state_d0(self):
        boundary = self.policy['boundary_contract']
        self.assertEqual(boundary['binary_weights'], [1,2,4])
        self.assertIn('3 = 1 + 2', boundary['composition_rule'])
        self.assertIn('weight 4', boundary['composition_rule'])
        self.assertEqual(self.policy['logic_0124_source_status'], 'RECOVERED_FROM_OWNER_MATERIAL')

    def test_effect_ack_is_separate_protocol_state_register(self):
        self.assertEqual(self.policy['effect_ack_protocol']['state_codes'], {
            'EFFECT_NACK':0, 'EFFECT_ACK_CONTINUE':1, 'EFFECT_ACK_ISOLATE':2,
            'EFFECT_ACK_BLOCK':3, 'EFFECT_ACK_DONE':4})
        self.assertEqual(self.policy['effect_ack_protocol']['register'], 'D4')
        self.assertEqual(self.policy['effect_ack_protocol']['ordinary_release'], 'EFFECT_ACK_DONE only')
        self.assertEqual(self.policy['boundary_contract']['register_binding']['D0'],
                         'low two bits are the invariant QIK-VRT/TEMDD boundary decision')
        self.assertEqual(self.policy['boundary_contract']['register_binding']['D4'], 'effect-ack protocol state')

    def test_mc68000_probe_enforces_boundary_split(self):
        for token in ('D0_BOUNDARY_CODES=0,1,2,3','D0_BINARY_WEIGHTS=1,2',
                      'D0_COMPOSITION_3=1+2','NEXT_ORTHOGONAL_WEIGHT=4',
                      'EFFECT_ACK_CODES=0,1,2,3,4','EFFECT_ACK_REGISTER=D4'):
            self.assertIn(token, self.probe)
        self.assertIn('d0_valid', self.probe)
        self.assertIn('d0_valid(4)', self.probe)

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

if __name__ == '__main__':
    unittest.main()
