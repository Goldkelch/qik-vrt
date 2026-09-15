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
 stream.write(json.dumps({'argv':sys.argv[1:],'cwd':str(Path.cwd()),'frozen':os.environ.get('BUNDLE_FROZEN'),'gemfile':os.environ.get('BUNDLE_GEMFILE'),'without':os.environ.get('BUNDLE_WITHOUT')})+'\\n')
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

    def test_missing_ruby_is_not_a_skip(self):
        self.admitted_lock_fixture()
        output = self.make('megast-rails-test', ruby=self.root / 'absent-ruby')
        self.assertNotEqual(0, output.returncode)
        self.assertEqual([], self.recorded())

if __name__ == '__main__':
    unittest.main(verbosity=2)
