import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

M = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools/qikvrt_distribution_readback.py'))
HEAD, TREE = 'a' * 40, 'b' * 40

class DistributionReadbackTests(unittest.TestCase):
    def fixture(self, root):
        for name in M['REQUIRED']:
            (root / name).write_bytes(('fixture:' + name).encode())
        return M['create'](root, HEAD, TREE)

    def test_complete_bytes_verify_without_done_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.fixture(root)
            M['verify_local'](root, manifest, HEAD, TREE)
            self.assertFalse(manifest['full_product_done'])
            self.assertFalse(manifest['linux_distribution_done'])
            self.assertIn('  ' + M['MANIFEST'] + '\n', (root / (M['MANIFEST'] + '.sha256')).read_text())

    def test_sha_file_without_iso_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            (root / M['REQUIRED'][0]).unlink()
            with self.assertRaisesRegex(ValueError, 'complete ISO'):
                M['create'](root, HEAD, TREE)

    def test_modified_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); manifest = self.fixture(root)
            (root / M['REQUIRED'][0]).write_bytes(b'not the bound ISO')
            with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
                M['verify_local'](root, manifest, HEAD, TREE)

    def test_head_or_tree_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = self.fixture(Path(d))
            for head, tree in [('c'*40, TREE), (HEAD, 'c'*40)]:
                with self.assertRaisesRegex(ValueError, 'subject mismatch'):
                    M['validate'](manifest, head, tree)

    def test_path_traversal_and_zero_byte_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = self.fixture(Path(d))
            bad = copy.deepcopy(manifest)
            bad['assets']['../escape'] = {'bytes': 1, 'sha256': 'a'*64}
            with self.assertRaisesRegex(ValueError, 'unsafe asset'):
                M['validate'](bad, HEAD, TREE)
            bad = copy.deepcopy(manifest)
            bad['assets'][M['REQUIRED'][0]]['bytes'] = 0
            with self.assertRaisesRegex(ValueError, 'byte count'):
                M['validate'](bad, HEAD, TREE)

    def test_http_is_not_accepted_as_https(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'HTTPS'):
                M['download']('http://example.invalid/iso', Path(d)/'iso', 'a'*64)

    def test_wrong_download_bytes_leave_no_accepted_file(self):
        class Response(io.BytesIO):
            status = 200
        with tempfile.TemporaryDirectory() as d, patch('urllib.request.build_opener') as make:
            make.return_value.open.return_value = Response(b'wrong')
            target = Path(d)/'iso'
            with self.assertRaisesRegex(ValueError, 'digest/size mismatch'):
                M['download']('https://example.invalid/iso', target, hashlib.sha256(b'right').hexdigest(), 5)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(d).iterdir()), [])
            request = make.return_value.open.call_args.args[0]
            self.assertNotIn('Authorization', request.headers)

    def test_all_payloads_are_requested_on_public_readback(self):
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d)/'src', Path(d)/'dst'; source.mkdir()
            manifest = self.fixture(source)
            seen = []
            def fake_download(url, path, expected_hash, expected_bytes=None):
                name = url.rsplit('/', 1)[-1]; data = (source/name).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)
                if expected_bytes is not None: self.assertEqual(len(data), expected_bytes)
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); seen.append(name)
                return {'url': url, 'http_status': 200, 'bytes': len(data), 'sha256': expected_hash}
            with patch.dict(M['readback'].__globals__, download=fake_download):
                result = M['readback']('https://example.invalid/release', target, M['digest'](source/M['MANIFEST']), HEAD, TREE)
            self.assertTrue(set(M['REQUIRED']) <= set(seen))
            self.assertFalse(result['full_product_done'])
            self.assertFalse(result['linux_distribution_done'])

    def test_split_release_readback_requests_parts_then_verifies_original_files(self):
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d)/'src', Path(d)/'dst'; source.mkdir()
            self.fixture(source)
            manifest = M['create'](source, HEAD, TREE, part_bytes=17)
            M['verify_local'](source, manifest, HEAD, TREE)
            seen = []
            def fetch(url, path, expected_hash, expected_bytes=None):
                name = url.rsplit('/', 1)[-1]; data = (source/name).read_bytes(); seen.append(name)
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected_hash)
                if expected_bytes is not None: self.assertEqual(len(data), expected_bytes)
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
                return {'url': url, 'http_status': 200, 'bytes': len(data), 'sha256': expected_hash}
            with patch.dict(M['readback'].__globals__, download=fetch):
                result = M['readback']('https://example.invalid/release', target, M['digest'](source/M['MANIFEST']), HEAD, TREE)
            self.assertEqual(set(seen)-{M['MANIFEST']}, set(M['transport_names'](manifest['assets'])))
            for name in M['REQUIRED']:
                self.assertEqual((target/name).read_bytes(), (source/name).read_bytes())
                self.assertNotIn(name, seen)
            self.assertTrue(result['artifact_bytes_verified']); self.assertFalse(result['full_product_done'])
            # A valid original file cannot mask a damaged part before publication.
            part = next(iter(manifest['assets'].values()))['parts'][0]
            (source/part['name']).write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'part integrity mismatch'):
                M['verify_local'](source, manifest, HEAD, TREE)

    def test_sender_cannot_raise_receiver_default_without_explicit_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            manifest = M['create'](root, HEAD, TREE, part_bytes=4096*1024**2)
            with self.assertRaisesRegex(ValueError, 'receiver limit'):
                M['validate'](manifest, HEAD, TREE)
            M['validate'](manifest, HEAD, TREE, max_part_bytes=4096*1024**2)

if __name__ == '__main__':
    unittest.main()
