# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed configuration/cache tests; synthetic data, no personal enrollment."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from tools import qikvrt_sso_gateway as sso


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qikvrt-sso-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.settings = {
            'schema': 'qikvrt_sso_gateway_v1', 'issuer': 'https://issuer.example/realm',
            'client_id': 'synthetic-terminal', 'origin': 'https://localhost:8443',
            'listen_port': 8443, 'novnc_port': 6080,
        }
        for key, value in {
            'client_secret_file': b'not-a-production-client-secret',
            'cookie_secret_file': os.urandom(32),
            'allowed_emails_file': b'fixture@example.invalid\n',
            'tls_cert_file': b'SYNTHETIC_PLACEHOLDER_NOT_A_CERTIFICATE',
            'tls_key_file': b'SYNTHETIC_PLACEHOLDER_NOT_A_KEY',
        }.items():
            path = self.root / key
            path.write_bytes(value); path.chmod(0o600)
            self.settings[key] = str(path)

    def test_generated_configuration_has_no_authority_or_secret_forwarding(self):
        config = tomllib.loads(sso.configuration(self.settings))
        self.assertEqual(config['upstreams'], ['http://127.0.0.1:6080/'])
        self.assertEqual(config['http_address'], '')
        self.assertEqual(config['https_address'], '127.0.0.1:8443')
        self.assertEqual(config['code_challenge_method'], 'S256')
        self.assertFalse(config['insecure_oidc_skip_nonce'])
        self.assertFalse(config['pass_access_token'])
        self.assertFalse(config['pass_authorization_header'])
        self.assertTrue(config['cookie_secure'])
        self.assertNotIn('not-a-production-client-secret', sso.configuration(self.settings))

    def test_unknown_field_cannot_disable_authentication(self):
        for key, value in [('skip_auth_routes', ['.*']), ('cookie_secure', False),
                           ('ssl_insecure_skip_verify', True), ('upstreams', ['http://evil.invalid'])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                sso.validate({**self.settings, key: value})

    def test_malformed_or_external_origins_rejected(self):
        for origin in ['http://localhost:8443', 'https://attacker.invalid:8443',
                       'https://localhost:8443@evil.invalid', 'https://localhost:8443/?rd=x',
                       'https://localhost:8443/#fragment', 'https://localhost:8443\\@evil',
                       'https://localhost:9443', 'https://localhost:8443\n']:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                sso.validate({**self.settings, 'origin': origin})

    def test_insecure_or_credential_bearing_issuers_rejected(self):
        for issuer in ['http://issuer.example', 'https://user:pass@issuer.example',
                       'https://issuer.example?secret=value', 'https://issuer.example#fragment']:
            with self.subTest(issuer=issuer), self.assertRaises(ValueError):
                sso.validate({**self.settings, 'issuer': issuer})

    def test_ports_are_explicit_distinct_unprivileged_integers(self):
        for port in [True, 0, 443, 65536, 8443, '6080']:
            with self.subTest(port=port), self.assertRaises(ValueError):
                sso.validate({**self.settings, 'novnc_port': port})

    def test_wildcards_empty_lists_and_control_characters_rejected(self):
        path = Path(self.settings['allowed_emails_file'])
        for data in ['*\n', '*@example.invalid\n', '', 'fixture@example.invalid,other@example.invalid\n',
                     'fixture@example.invalid\n\n', 'fixture@example.invalid\nfixture@example.invalid\n']:
            path.write_text(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                sso.validate(self.settings)

    def test_secret_permissions_and_symlinks_rejected(self):
        path = Path(self.settings['client_secret_file'])
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'OWNER_ONLY'):
            sso.validate(self.settings)
        path.chmod(0o600)
        link = self.root / 'linked-secret'; link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'SYMLINK'):
            sso.validate({**self.settings, 'client_secret_file': str(link)})
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'OWNER_ONLY'):
            sso.validate(self.settings)
        self.root.chmod(0o700)

    def test_cookie_secret_must_be_raw_32_bytes(self):
        Path(self.settings['cookie_secret_file']).write_bytes(b'base64-looking-but-too-short')
        with self.assertRaisesRegex(ValueError, '32_RAW'):
            sso.validate(self.settings)

    def test_duplicate_settings_and_repository_auth_state_rejected(self):
        path = self.root / 'settings.json'; path.write_text('{"issuer":"a","issuer":"b"}')
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
            sso.load_settings(path)
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_REPOSITORY'):
            sso.private_file(str(sso.ROOT / 'test-secret'), 'test')

    def test_process_environment_cannot_override_hardened_config(self):
        with patch.dict(os.environ, {'OAUTH2_PROXY_SKIP_AUTH_ROUTES': '.*',
                                     'OAUTH2_PROXY_COOKIE_SECURE': 'false'}):
            self.assertFalse(any(key.startswith('OAUTH2_PROXY_') for key in sso.clean_environment()))

    def archive(self, kind=tarfile.REGTYPE):
        path = self.root / 'fixture.tar.gz'; member = 'fixture/oauth2-proxy'; raw = b'fixture-binary'
        with tarfile.open(path, 'w:gz') as archive:
            info = tarfile.TarInfo(member); info.type = kind
            info.size = len(raw) if kind == tarfile.REGTYPE else 0
            info.linkname = '/outside-cache'
            archive.addfile(info, io.BytesIO(raw) if info.size else None)
        (self.root / 'oauth2-proxy').write_bytes(raw)
        return {'binary_member': member, 'archive': {'name': path.name, 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}

    def test_changed_binary_archive_and_link_members_are_rejected(self):
        lock = self.archive()
        self.assertEqual(sso.verify(self.root, lock), self.root / 'oauth2-proxy')
        (self.root / 'oauth2-proxy').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'BINARY_ABSENT_OR_CHANGED'):
            sso.verify(self.root, lock)
        lock = self.archive()
        (self.root / 'fixture.tar.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'ABSENT_OR_CHANGED'):
            sso.verify(self.root, lock)
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            lock = self.archive(kind)
            with self.assertRaisesRegex(ValueError, 'REGULAR_BINARY'):
                sso.verify(self.root, lock)

    def test_invalid_tls_material_prevents_process_launch(self):
        with patch.object(sso.subprocess, 'Popen') as launch:
            with self.assertRaises(OSError):
                sso.run_gateway(Path('/unused-binary'), self.settings)
            launch.assert_not_called()

    @unittest.skipUnless(os.environ.get('QIKVRT_SSO_NATIVE_TEST') == '1', 'requires explicitly installed locked proxy')
    def test_actual_proxy_accepts_generated_configuration(self):
        # Upstream --config-test parses/validates options without loading TLS or
        # contacting an IdP. This is intentionally NOT a successful SSO receipt.
        lock = json.loads(sso.LOCK.read_text())
        binary = sso.verify(sso.ROOT / '.qikvrt/toolchains/sso', lock)
        config = self.root / 'proxy.cfg'; config.write_text(sso.configuration(self.settings)); config.chmod(0o600)
        result = subprocess.run([str(binary), '--config', str(config), '--config-test'],
                                capture_output=True, text=True, timeout=30, env=sso.clean_environment())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('configuration is valid', result.stdout)


if __name__ == '__main__':
    unittest.main()
