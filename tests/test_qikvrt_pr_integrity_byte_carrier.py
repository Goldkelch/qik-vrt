# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exercise the materializer's real inline carrier code against temporary Git repos.

Local files/ZIPs test the boundary; only a native artifact download proves GitHub
persistence. These tests neither dispatch workflows nor mutate a remote ref.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
import warnings
import zipfile

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_batch04_integrity.yml'
PATHS = ('REPOSITORY_FILE_MANIFEST.json', 'REPOSITORY_FILE_MANIFEST.json.sha256', 'SHA256SUMS.txt')


def inline(marker: str) -> str:
    source = WORKFLOW.read_text(encoding='utf-8')
    opening = "          python3 -B - <<'" + marker + "'\n"
    return textwrap.dedent(source.split(opening, 1)[1].split('\n          ' + marker + '\n', 1)[0])


class IntegrityByteCarrierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        for name in PATHS:
            (self.root / name).write_bytes(b'original\n')
        (self.root / 'ordinary.txt').write_text('unchanged\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.tree = self.git('rev-parse', 'HEAD^{tree}').strip()
        self.target = self.base / 'carrier'
        self.archive = self.base / 'readback.zip'
        self.env = dict(os.environ, CARRIER_DIRECTORY=str(self.target),
                        EXPECTED_HEAD=self.head, CARRIER_REPOSITORY='Goldkelch/qik-vrt',
                        CARRIER_PR='1160', CARRIER_RUN_ID='123', CARRIER_RUN_ATTEMPT='1',
                        CARRIER_GATES='success', CARRIER_ARCHIVE=str(self.archive),
                        CARRIER_ARTIFACT_ID='456')
        for name in PATHS:
            (self.root / name).write_bytes(('regenerated ' + name + '\n').encode())

    def git(self, *args: str) -> str:
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.PIPE)

    def run_inline(self, marker: str, **overrides: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, '-B', '-c', inline(marker)], cwd=self.root,
                              env=dict(self.env, **overrides), capture_output=True, text=True,
                              timeout=20, check=False)

    def capture(self, **overrides: str) -> dict:
        result = self.run_inline('PY_CARRIER', **overrides)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.target / 'CARRIER.json').read_text(encoding='utf-8'))

    def zip_carrier(self) -> None:
        with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.target.iterdir()):
                archive.write(path, path.name)

    def test_exact_source_and_bytes_are_bound_without_commit(self) -> None:
        before = self.git('status', '--porcelain=v1')
        value = self.capture()
        self.assertEqual(value['source']['head_sha'], self.head)
        self.assertEqual(value['source']['tree_sha'], self.tree)
        self.assertEqual(value['source']['run_id'], 123)
        self.assertTrue(value['trio_covers_tracked_delta'])
        self.assertEqual(value['other_modified_paths'], [])
        self.assertTrue(all(flag is False for flag in value['claims'].values()))
        for entry in value['files']:
            raw = (self.root / entry['path']).read_bytes()
            self.assertEqual(raw, (self.target / entry['path']).read_bytes())
            self.assertEqual(entry['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(entry['git_blob_sha1'], hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
            self.assertEqual(entry['source_blob_sha1'], self.git('rev-parse', self.head + ':' + entry['path']).strip())
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.head)
        self.assertEqual(self.git('status', '--porcelain=v1'), before)

    def test_head_drift_blocks_before_carrier_creation(self) -> None:
        result = self.run_inline('PY_CARRIER', EXPECTED_HEAD='0' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HEAD drift', result.stderr)
        self.assertFalse(self.target.exists())

    def test_missing_source_tree_member_blocks(self) -> None:
        self.git('rm', '--cached', PATHS[0])
        self.git('commit', '-qm', 'remove source member')
        result = self.run_inline('PY_CARRIER', EXPECTED_HEAD=self.git('rev-parse', 'HEAD').strip())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('source path', result.stderr)

    def test_symlink_payload_blocks(self) -> None:
        path = self.root / PATHS[0]
        path.unlink()
        path.symlink_to(self.root / 'ordinary.txt')
        result = self.run_inline('PY_CARRIER')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_directory_payload_blocks(self) -> None:
        path = self.root / PATHS[0]
        path.unlink()
        path.mkdir()
        self.assertNotEqual(self.run_inline('PY_CARRIER').returncode, 0)

    def test_output_inside_checkout_blocks(self) -> None:
        result = self.run_inline('PY_CARRIER', CARRIER_DIRECTORY=str(self.root / 'output'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('outside the checkout', result.stderr)

    def test_existing_carrier_is_never_overwritten(self) -> None:
        self.capture()
        before = (self.target / 'CARRIER.json').read_bytes()
        self.assertNotEqual(self.run_inline('PY_CARRIER').returncode, 0)
        self.assertEqual((self.target / 'CARRIER.json').read_bytes(), before)

    def test_other_delta_is_disclosed_not_silently_claimed_covered(self) -> None:
        (self.root / 'ordinary.txt').write_text('changed\n', encoding='utf-8')
        value = self.capture()
        self.assertEqual(value['other_modified_paths'], ['ordinary.txt'])
        self.assertFalse(value['trio_covers_tracked_delta'])

    def test_failed_gate_remains_failed_in_carrier(self) -> None:
        value = self.capture(CARRIER_GATES='failure')
        self.assertEqual(value['repository_gates_outcome'], 'failure')
        self.assertFalse(value['claims']['fresh_successor_gates_pass'])

    def test_invalid_identity_or_unknown_gate_blocks(self) -> None:
        for overrides in ({'CARRIER_PR': '0'}, {'CARRIER_RUN_ID': 'unknown'},
                          {'CARRIER_REPOSITORY': 'not-a-repository'}, {'CARRIER_GATES': 'unknown'}):
            with self.subTest(overrides=overrides):
                self.assertNotEqual(self.run_inline('PY_CARRIER', **overrides).returncode, 0)
                self.assertFalse(self.target.exists())

    def test_identical_archive_readback_has_bounded_state(self) -> None:
        self.capture()
        self.zip_carrier()
        result = self.run_inline('PY_CARRIER_READBACK')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['state'], 'BYTE_CARRIER_READBACK_VERIFIED')
        self.assertFalse(value['repository_successor_persisted'])
        self.assertFalse(value['effect_ack_done'])

    def test_changed_same_length_archive_bytes_block(self) -> None:
        self.capture()
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for path in sorted(self.target.iterdir()):
                raw = path.read_bytes()
                if path.name == PATHS[0]:
                    raw = bytes([raw[0] ^ 1]) + raw[1:]
                archive.writestr(path.name, raw)
        result = self.run_inline('PY_CARRIER_READBACK')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('persisted artifact bytes differ', result.stderr)

    def test_missing_or_duplicate_archive_member_blocks(self) -> None:
        self.capture()
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.write(self.target / 'CARRIER.json', 'CARRIER.json')
        self.assertNotEqual(self.run_inline('PY_CARRIER_READBACK').returncode, 0)
        self.zip_carrier()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.archive, 'a') as archive:
                archive.writestr('CARRIER.json', b'{}')
        self.assertNotEqual(self.run_inline('PY_CARRIER_READBACK').returncode, 0)

    def repository_fixture(self):
        manifest = self.capture()
        self.git('add', *PATHS)
        self.git('commit', '-qm', 'integrity successor')
        remote = self.base / 'remote'
        remote.mkdir()
        for entry in manifest['files']:
            raw = (self.target / entry['path']).read_bytes()
            response = {'encoding': 'base64', 'sha': entry['git_blob_sha1'],
                        'size': len(raw), 'content': base64.b64encode(raw).decode()}
            (remote / (entry['path'] + '.json')).write_text(json.dumps(response), encoding='utf-8')
        return remote, dict(REPOSITORY_READBACK=str(remote), GITHUB_REPOSITORY='Goldkelch/qik-vrt',
                            GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1',
                            PERSISTED_HEAD=self.git('rev-parse', 'HEAD').strip(),
                            PERSISTED_TREE=self.git('rev-parse', 'HEAD^{tree}').strip())

    def test_repository_readback_binds_direct_successor_and_actual_bytes(self) -> None:
        remote, env = self.repository_fixture()
        result = self.run_inline('PY_REPOSITORY_READBACK', **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads((remote / 'RECEIPT.json').read_text())
        self.assertEqual(value['successor_head'], env['PERSISTED_HEAD'])
        self.assertEqual(value['source']['head_sha'], self.head)
        self.assertFalse(value['fresh_successor_gates_pass'])
        self.assertFalse(value['effect_ack_done'])

    def test_repository_readback_rejects_wrong_source_run(self) -> None:
        remote, env = self.repository_fixture()
        env['GITHUB_RUN_ID'] = '124'
        result = self.run_inline('PY_REPOSITORY_READBACK', **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('carrier source binding differs', result.stderr)
        self.assertFalse((remote / 'RECEIPT.json').exists())

    def test_repository_readback_rejects_same_length_different_bytes(self) -> None:
        remote, env = self.repository_fixture()
        path = remote / (PATHS[0] + '.json')
        value = json.loads(path.read_text())
        raw = base64.b64decode(value['content'])
        value['content'] = base64.b64encode(bytes([raw[0] ^ 1]) + raw[1:]).decode()
        path.write_text(json.dumps(value))
        result = self.run_inline('PY_REPOSITORY_READBACK', **env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('repository byte readback differs', result.stderr)
        self.assertFalse((remote / 'RECEIPT.json').exists())

    def test_workflow_retains_writer_and_gate_boundaries(self) -> None:
        source = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("if: github.event_name != 'pull_request'", source)
        self.assertIn("steps.regenerated_integrity.outcome == 'success'", source)
        self.assertIn("steps.byte_carrier.outcome == 'success'", source)
        self.assertIn("steps.upload_byte_carrier.outcome == 'success'", source)
        self.assertIn('make test', source)
        self.assertIn('          overwrite: false', source)
        self.assertNotIn('continue-on-error:', source)
        self.assertIn('  actions: read', source)
        self.assertNotIn('  actions: write', source)
        compile(inline('PY_CARRIER'), 'carrier', 'exec')
        compile(inline('PY_CARRIER_READBACK'), 'readback', 'exec')
        compile(inline('PY_REPOSITORY_READBACK'), 'repository-readback', 'exec')
        self.assertIn('      - mesh/effect-evidence-invariant-v1', source)
        self.assertIn("github.event_name == 'push' && github.ref_name == 'mesh/effect-evidence-invariant-v1'", source)
        self.assertIn('qikvrt_autonomous_exact_head_verify', source)
        self.assertNotIn('gh run rerun', source)


if __name__ == '__main__':
    unittest.main()
