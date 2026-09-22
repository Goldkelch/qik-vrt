# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finite model/fixture conformance, not a communication-effect witness."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

from tools import qikvrt_binding_acceptance as core

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = b'non-production binding fixture\x00\r\n'
PROFILE = core._Profile('fixture.json', hashlib.sha256(FIXTURE).hexdigest())
ALL_TRUE = (True,) * 7
ALL_FALSE = (False,) * 7


def wire(byte_id='VERIFIED', flags=ALL_FALSE, status='OPEN', profile=PROFILE):
    return (f'artifact {profile.filename} sha256 {profile.digest} EXACT_FILE_BYTES\r\n'
            f'acceptance {byte_id} ' + ' '.join('true' if x else 'false' for x in flags)
            + f' {status}\r\n').encode('ascii')


def assessed(flags):
    return dict(zip(core.PREDICATES, flags))


class BindingAcceptanceTests(unittest.TestCase):
    def check(self, raw, artifact=FIXTURE, evidence=None):
        return core._validate(raw, artifact, evidence, PROFILE)

    def test_all_768_isolated_state_cases(self):
        cases = coherent = accepted = 0
        for bid, flags, status in itertools.product(
                core.BYTE_IDS, itertools.product((False, True), repeat=7), ('OPEN', 'ACCEPTED')):
            cases += 1
            want = 'ACCEPTED' if bid == 'VERIFIED' and all(flags) else 'OPEN'
            got = core.expected_status(bid, flags)
            self.assertEqual(got, want, (bid, flags, status))
            coherent += status == got
            accepted += status == got == 'ACCEPTED'
        self.assertEqual((cases, coherent, accepted), (768, 384, 1))

    def test_all_128_evidence_bound_vectors_and_inverse_status(self):
        accepted = 0
        for flags in itertools.product((False, True), repeat=7):
            status = core.expected_status('VERIFIED', flags)
            result = self.check(wire(flags=flags, status=status), evidence=assessed(flags))
            self.assertEqual(result.outcome, 'VALID')
            self.assertEqual(result.accepted, all(flags))
            self.assertFalse(result.external_effect_executed)
            accepted += result.accepted
            opposite = 'OPEN' if status == 'ACCEPTED' else 'ACCEPTED'
            result = self.check(wire(flags=flags, status=opposite), evidence=assessed(flags))
            self.assertEqual(result.outcome, 'SEMANTIC_REJECT')
            self.assertFalse(result.accepted)
        self.assertEqual(accepted, 1)

    def test_each_missing_false_or_unknown_predicate_blocks_acceptance(self):
        for name in core.PREDICATES:
            for value in (False, None, 'missing'):
                ev = assessed(ALL_TRUE)
                if value == 'missing':
                    del ev[name]
                else:
                    ev[name] = value
                result = self.check(wire(flags=ALL_TRUE, status='ACCEPTED'), evidence=ev)
                self.assertEqual(result.outcome, 'SEMANTIC_REJECT', (name, value))
                self.assertFalse(result.accepted)

    def test_hash_pass_with_no_evidence_does_not_open_gate(self):
        result = self.check(wire(flags=ALL_TRUE, status='ACCEPTED'))
        self.assertEqual(result.observed_byte_id, 'VERIFIED')
        self.assertEqual(result.outcome, 'SEMANTIC_REJECT')
        self.assertFalse(result.accepted)

    def test_valid_open_can_report_application_subject_unestablished(self):
        flags = (True, True, True, True, False, True, True)
        result = self.check(wire(flags=flags), evidence=assessed(flags))
        self.assertEqual(result.outcome, 'VALID')
        self.assertEqual(result.acceptance_status, 'OPEN')
        self.assertFalse(result.accepted)

    def test_unknown_evidence_projects_to_false(self):
        for ev in (None, {}, {key: None for key in core.PREDICATES}, assessed(ALL_FALSE)):
            result = self.check(wire(), evidence=ev)
            self.assertEqual(result.outcome, 'VALID')
            self.assertFalse(result.accepted)

    def test_no_contradiction_flag_is_not_true_by_default(self):
        flags = ALL_FALSE[:-1] + (True,)
        self.assertEqual(self.check(wire(flags=flags)).outcome, 'SEMANTIC_REJECT')
        self.assertEqual(self.check(wire(flags=flags), evidence={core.PREDICATES[-1]: True}).outcome, 'VALID')

    def test_evidence_rejects_truthy_strings_integers_and_extra_keys(self):
        for bad in ('true', 'false', 1, 0, [], {}):
            ev = assessed(ALL_TRUE)
            ev[core.PREDICATES[0]] = bad
            result = self.check(wire(flags=ALL_TRUE, status='ACCEPTED'), evidence=ev)
            self.assertEqual(result.outcome, 'SEMANTIC_REJECT')
        self.assertEqual(self.check(wire(), evidence={'unexpected': True}).outcome, 'SEMANTIC_REJECT')

    def test_mismatch_and_missing_bytes_take_priority_over_semantics(self):
        for artifact, observed in ((None, 'UNKNOWN'), (FIXTURE[:-1] + b'X', 'NOT_VERIFIED')):
            for bid in core.BYTE_IDS:
                result = self.check(wire(bid, ALL_FALSE, 'ACCEPTED'), artifact)
                self.assertEqual(result.outcome, 'BINDING_REJECT')
                self.assertEqual(result.observed_byte_id, observed)
                self.assertFalse(result.accepted)

    def test_actual_match_rejects_inconsistent_declared_identity(self):
        for bid in ('NOT_VERIFIED', 'UNKNOWN'):
            for status in ('OPEN', 'ACCEPTED'):
                result = self.check(wire(bid, ALL_TRUE, status), evidence=assessed(ALL_TRUE))
                self.assertEqual(result.outcome, 'BINDING_REJECT')
                self.assertEqual(result.reason, 'byte-id-assertion-mismatch')

    def test_canonical_example_is_syntax_not_byte_or_effect_evidence(self):
        raw = wire(flags=ALL_FALSE[:-1] + (True,), profile=core._PROFILE)
        parsed = core.parse(raw)
        self.assertEqual(parsed.status, 'OPEN')
        result = core.validate(raw, None)
        self.assertEqual(result.outcome, 'BINDING_REJECT')
        self.assertEqual(result.observed_byte_id, 'UNKNOWN')
        self.assertFalse(result.accepted)

    def test_production_profile_cannot_accept_fixture_binding(self):
        result = core.validate(wire(flags=ALL_TRUE, status='ACCEPTED'), FIXTURE, evidence=assessed(ALL_TRUE))
        self.assertEqual(result.outcome, 'ABNF_REJECT')
        result = core.validate(wire(profile=core._PROFILE), FIXTURE)
        self.assertEqual(result.outcome, 'BINDING_REJECT')

    def test_all_fixed_literals_are_case_sensitive(self):
        raw = wire()
        for before, after in ((b'artifact', b'ARTIFACT'), (b'acceptance', b'ACCEPTANCE'),
                              (b'fixture.json', b'Fixture.json'), (b'sha256', b'SHA256'),
                              (b'EXACT_FILE_BYTES', b'exact_file_bytes'), (b'VERIFIED', b'verified'),
                              (b'false', b'False'), (b'OPEN', b'open')):
            self.assertEqual(self.check(raw.replace(before, after, 1)).outcome, 'ABNF_REJECT')

    def test_exact_literal_and_boolean_count_failures(self):
        raw = wire()
        for before, after in ((b'fixture.json', b'other.json'), (b'sha256', b'sha512'),
                              (PROFILE.digest.encode(), b'0' * 64), (b'EXACT_FILE_BYTES', b'FILE_NAME_ONLY'),
                              (b'VERIFIED', b'HASH_OK'), (b'false', b'no'), (b'OPEN', b'APPROVED'),
                              (b' false OPEN', b' OPEN'), (b' OPEN', b' false OPEN')):
            self.assertEqual(self.check(raw.replace(before, after, 1)).outcome, 'ABNF_REJECT')

    def test_octet_framing_rejects_normalization_and_trailing_data(self):
        raw = wire()
        variants = (raw.replace(b'\r\n', b'\n'), raw[:-2], raw + b'\r\n', raw + b'junk',
                    raw.replace(b' ', b'\t', 1), raw.replace(b' ', b'  ', 1), b' ' + raw,
                    b'\xef\xbb\xbf' + raw, raw.replace(b' ', b'\xc2\xa0', 1), raw + b'\0')
        for value in variants:
            self.assertEqual(self.check(value).outcome, 'ABNF_REJECT')

    def test_syntax_has_priority_over_missing_binding(self):
        self.assertEqual(self.check(b'invalid', None).outcome, 'ABNF_REJECT')

    def test_parser_limits_and_strict_boolean_model(self):
        for raw in ('not-bytes', None, b'x' * (core.MAX_RECORD_BYTES + 1)):
            self.assertEqual(self.check(raw).outcome, 'ABNF_REJECT')
        for flags in ([True] * 7, (1,) * 7, ('true',) * 7, (True,) * 6):
            with self.assertRaises(ValueError):
                core.expected_status('VERIFIED', flags)
        self.assertEqual(self.check(wire(), bytearray(FIXTURE)).outcome, 'BINDING_REJECT')

    def test_cli_missing_artifact_cannot_validate_verified_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / 'record.txt'
            record.write_bytes(wire(flags=ALL_TRUE, status='ACCEPTED', profile=core._PROFILE))
            output = io.StringIO()
            with redirect_stdout(output):
                status = core.main(['--record', str(record), '--artifact', str(root / 'missing')])
            self.assertEqual(status, 1)
            result = json.loads(output.getvalue())
            self.assertEqual(result['outcome'], 'BINDING_REJECT')
            self.assertFalse(result['accepted'])

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'platform lacks no-follow flag')
    def test_cli_read_guard_rejects_symlinks_directories_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').write_bytes(b'abc')
            (root / 'link').symlink_to(root / 'real')
            for path, limit in ((root / 'link', 10), (root, 10), (root / 'real', 2)):
                with self.assertRaises(OSError):
                    core._read_regular(path, limit)
            self.assertEqual(core._read_regular(root / 'real', 3), b'abc')

    def test_spec_literals_and_order_remain_in_sync(self):
        text = (ROOT / 'state/autonomy/BINDING_ACCEPTANCE_SAFETY_INVARIANT_V1.md').read_text()
        grammar = text.split('```abnf\n', 1)[1].split('```', 1)[0]
        parts = re.search(r'digest\s*=\s*%s"([0-9a-f]+)"\s+%s"([0-9a-f]+)"', grammar)
        self.assertIsNotNone(parts)
        self.assertEqual(parts[1] + parts[2], core.DIGEST)
        self.assertIn('%s"' + core.FILENAME + '"', grammar)
        self.assertIn('%s"artifact"', grammar)
        self.assertIn('%s"acceptance"', grammar)
        self.assertIn('7(SP boolean)', grammar)
        self.assertEqual(grammar.count('CRLF'), 2)
        for index, name in enumerate(core.PREDICATES, 1):
            self.assertIn(f'{index}. {name}', text)
        self.assertIn('BINDING_REJECT first', text)
        self.assertIn('VALID with status OPEN', text)

    def test_reference_is_wired_to_existing_repository_test_target(self):
        text = (ROOT / 'Makefile').read_text()
        target = text.split('repository-writer-contract:\n', 1)[1].split('\n\n', 1)[0]
        self.assertIn('tests.test_qikvrt_binding_acceptance', target)
        self.assertIn('tests.test_qikvrt_pr_integrity_byte_carrier', target)


if __name__ == '__main__':
    unittest.main()
