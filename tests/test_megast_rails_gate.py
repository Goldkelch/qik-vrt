# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. AI-authored validation fixture.
#!/usr/bin/env python3
"""Control-flow regressions for the proposed Makefile-only repair.

The Ruby/cache executables below are test doubles, NOT Rails validation.
Uses only a temporary directory and never installs dependencies or changes refs.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RailsGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qikvrt-rails-gate-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Makefile').write_bytes((ROOT / 'Makefile').read_bytes())
        tools = self.root / 'tools'
        tools.mkdir()
        # Bootstrap double tests Make propagation only, never runtime admission.
        (tools / 'bootstrap-runtime.sh').write_text(
            '#!/bin/sh\nexit "${BOOTSTRAP_EXIT:-0}"\n')
        self.app = self.root / 'deploy/vercel-monitor'
        self.app.mkdir(parents=True)
        self.lock = self.app / 'Gemfile.lock'
        self.calls = self.root / 'calls.jsonl'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('BUNDLE_', 'MAKE'))}
        self.env['QIKVRT_GATE_CALLS'] = str(self.calls)
        self.python = self.root / 'cache-double'
        self.ruby = self.root / 'ruby-double'
        self.python.write_text('#!' + sys.executable + '\n' + '''import os,sys
assert sys.argv[1:] in (['-B', 'tools/qikvrt_tool_cache.py', 'verify'], ['-B', 'tests/test_megast_rails_gate.py'])
sys.exit(int(os.environ.get('CACHE_EXIT', '0')) if 'verify' in sys.argv else 0)
''')
        self.ruby.write_text('#!' + sys.executable + '\n' + '''import json,os,sys
from pathlib import Path
with open(os.environ['QIKVRT_GATE_CALLS'], 'a') as stream:
 stream.write(json.dumps({'argv':sys.argv[1:],'cwd':str(Path.cwd()),'frozen':os.environ.get('BUNDLE_FROZEN'),'gemfile':os.environ.get('BUNDLE_GEMFILE'),'without':os.environ.get('BUNDLE_WITHOUT'),'bundle_path':os.environ.get('BUNDLE_PATH')})+'\\n')
sys.exit(19 if os.environ.get('FAIL_SUITE') == sys.argv[-1] else 0)
''')
        self.python.chmod(0o700)
        self.ruby.chmod(0o700)

    def make(self, *args, ruby=None):
        return subprocess.run(['make', '--no-print-directory',
            'PYTHON=' + str(self.python), 'RUBY=' + str(ruby or self.ruby),
            *args], cwd=self.root, env=self.env, text=True, capture_output=True, timeout=15)

    def recorded(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def admitted_lock_fixture(self):
        # Only existence is used by Make. This is deliberately NOT a real dependency lock.
        self.lock.write_text('TEST-DOUBLE-NOT-A-DEPENDENCY-LOCK\n')

    def test_root_make_includes_both_suites(self):
        output = self.make('-n', 'test')
        self.assertEqual(0, output.returncode, output.stderr)
        for path in ('test/megast_test.rb', 'test/rails_smoke_test.rb'):
            self.assertEqual(1, output.stdout.count(path))
        self.assertEqual([], self.recorded())

    def test_missing_lock_fails_before_either_suite(self):
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertIn('BLOCK: reviewed Mega ST Rails Gemfile.lock', output.stderr)
        self.assertEqual([], self.recorded())
        self.assertFalse(self.lock.exists())

    def test_empty_lock_fails_before_either_suite(self):
        self.lock.touch()
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())

    def test_cache_failure_prevents_execution(self):
        self.admitted_lock_fixture()
        self.env['CACHE_EXIT'] = '17'
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())

    def test_success_requires_both_in_order_and_frozen_bundle(self):
        self.admitted_lock_fixture()
        self.env.update(BUNDLE_FROZEN='false', BUNDLE_WITHOUT='test', BUNDLE_GEMFILE='untrusted')
        before = self.lock.read_bytes()
        output = self.make('megast-rails-test')
        self.assertEqual(0, output.returncode, output.stderr)
        calls = self.recorded()
        self.assertEqual(['test/megast_test.rb', 'test/rails_smoke_test.rb'], [call['argv'][-1] for call in calls])
        for call in calls:
            self.assertEqual('-rbundler/setup', call['argv'][0])
            self.assertEqual(str(self.app), call['cwd'])
            self.assertEqual('true', call['frozen'])
            self.assertEqual('Gemfile', call['gemfile'])
            self.assertEqual('', call['without'])
            self.assertEqual(str(self.root / '.qikvrt/toolchains/rails/bundle'), call['bundle_path'])
        self.assertEqual(before, self.lock.read_bytes())

    def test_core_failure_is_not_masked(self):
        self.admitted_lock_fixture()
        self.env['FAIL_SUITE'] = 'test/megast_test.rb'
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual(['test/megast_test.rb'], [call['argv'][-1] for call in self.recorded()])

    def test_smoke_failure_is_not_masked(self):
        self.admitted_lock_fixture()
        self.env['FAIL_SUITE'] = 'test/rails_smoke_test.rb'
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual(2, len(self.recorded()))

    def test_missing_bootstrap_runtime_cannot_skip(self):
        self.admitted_lock_fixture()
        self.env['BOOTSTRAP_EXIT'] = '20'
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())

    def test_bootstrap_integrity_block_cannot_skip(self):
        self.admitted_lock_fixture()
        self.env['BOOTSTRAP_EXIT'] = '1'
        output = self.make('megast-rails-test')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())

    def test_missing_ruby_is_not_a_skip(self):
        self.admitted_lock_fixture()
        output = self.make('megast-rails-test', ruby=self.root / 'absent-ruby')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())


class RailsCacheContractTests(unittest.TestCase):
    """Exercise the actual bootstrap functions on isolated non-executable fixtures."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qikvrt-rails-cache-contract-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'archives'
        self.destination = self.root / 'verified'
        self.source.mkdir()
        self.lock = self.root / 'Gemfile.lock'
        import hashlib
        self.data = b'isolated archive fixture, not a Ruby gem'
        digest = hashlib.sha256(self.data).hexdigest()
        self.lock.write_text('CHECKSUMS\n  fixture (1.0) sha256=' + digest + '\n')
        self.archive = self.source / 'fixture-1.0.gem'
        self.archive.write_bytes(self.data)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        (self.bundle / 'fixture.rb').write_text('# isolated byte-readback fixture\n')
        self.receipt = self.root / 'runtime' / 'environment.json'
        script = (ROOT / 'tools/bootstrap-runtime.sh').read_text()
        self.functions = script[script.index('rails_verify_archives() {'):script.index('check_rails_profile() {')]

    def run_function(self, function, *args):
        import shlex
        env = dict(os.environ, RAILS_LOCK=str(self.lock), RAILS_BUNDLE=str(self.bundle),
                   RAILS_RECEIPT=str(self.receipt))
        code = self.functions + '\n' + shlex.join([function, *map(str, args)]) + '\n'
        return subprocess.run(['sh'], input=code, env=env, capture_output=True, text=True, timeout=15)

    def test_verified_archive_copied_exactly(self):
        result = self.run_function('rails_verify_archives', self.source, self.destination)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.data, (self.destination / self.archive.name).read_bytes())

    def test_changed_archive_blocks_before_copy(self):
        self.archive.write_bytes(b'corrupt')
        result = self.run_function('rails_verify_archives', self.source, self.destination)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((self.destination / self.archive.name).exists())

    def test_unlisted_archive_is_not_a_cache_miss(self):
        self.archive.rename(self.source / 'unlisted-1.0.gem')
        self.assertNotEqual(0, self.run_function('rails_verify_archives', self.source, self.destination).returncode)

    def test_symlink_archive_is_blocked(self):
        original = self.root / 'outside.gem'
        self.archive.rename(original)
        self.archive.symlink_to(original)
        self.assertNotEqual(0, self.run_function('rails_verify_archives', self.source, self.destination).returncode)

    def test_receipt_roundtrip_and_tamper_rejection(self):
        self.assertEqual(0, self.run_function('rails_runtime_receipt', 'write').returncode)
        self.assertEqual(0, self.run_function('rails_runtime_receipt', 'verify').returncode)
        (self.bundle / 'fixture.rb').write_text('# changed\n')
        self.assertNotEqual(0, self.run_function('rails_runtime_receipt', 'verify').returncode)

    def test_added_installed_file_is_blocked(self):
        self.assertEqual(0, self.run_function('rails_runtime_receipt', 'write').returncode)
        (self.bundle / 'extra.rb').write_text('# extra\n')
        self.assertNotEqual(0, self.run_function('rails_runtime_receipt', 'verify').returncode)

    def test_linked_installed_file_is_blocked(self):
        (self.bundle / 'linked.rb').symlink_to(self.bundle / 'fixture.rb')
        self.assertNotEqual(0, self.run_function('rails_runtime_receipt', 'write').returncode)

    def test_lock_drift_invalidates_installed_receipt(self):
        self.assertEqual(0, self.run_function('rails_runtime_receipt', 'write').returncode)
        self.lock.write_text('changed lock\n')
        self.assertNotEqual(0, self.run_function('rails_runtime_receipt', 'verify').returncode)


class RuntimeByteAuthorityTests(unittest.TestCase):
    """Test generic byte-authority enforcement in the existing cache validator."""
    def setUp(self):
        import hashlib
        import importlib.util
        spec = importlib.util.spec_from_file_location('tested_tool_cache', ROOT / 'tools/qikvrt_tool_cache.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(prefix='qikvrt-byte-authority-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module.ROOT = self.root
        (self.root / 'lock').write_text('source bytes\n')
        self.entry = {'version': '1', 'profiles': ['fixture'], 'cache_class': 'ecosystem-cache',
            'provider': 'isolated test', 'cache_locations': ['fixture-cache'],
            'authority_files': ['lock'], 'verification': ['fixture hash'], 'trusted_save': False,
            'sha256_authorities': {'lock': hashlib.sha256((self.root / 'lock').read_bytes()).hexdigest()}}
        self.registry = {'components': {'fixture': self.entry}, 'cache_classes': ['ecosystem-cache']}
        self.locked = {'fixture': {'versions': ['1']}}

    def validate(self):
        return self.module.validate_registry(self.locked, self.registry)

    def test_exact_bytes_admitted(self):
        self.assertEqual('fixture', self.validate()[0]['component'])

    def test_byte_drift_is_blocked(self):
        (self.root / 'lock').write_text('different bytes\n')
        with self.assertRaises(self.module.ContractError):
            self.validate()

    def test_undeclared_byte_authority_is_blocked(self):
        self.entry['sha256_authorities']['other'] = '0' * 64
        with self.assertRaises(self.module.ContractError):
            self.validate()

    def test_malformed_digest_is_blocked(self):
        self.entry['sha256_authorities']['lock'] = 'not a digest'
        with self.assertRaises(self.module.ContractError):
            self.validate()

    def test_legacy_contract_without_optional_hash_unchanged(self):
        self.entry.pop('sha256_authorities')
        self.assertEqual('fixture', self.validate()[0]['component'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
