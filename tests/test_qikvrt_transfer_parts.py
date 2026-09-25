# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Real byte splitting/reassembly, interrupted delivery and finite size boundaries."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import qikvrt_transfer_parts as parts


class TransferPartsTests(unittest.TestCase):
    def test_2048_mib_default_and_larger_smaller_profiles_have_finite_limits(self):
        self.assertEqual(parts.DEFAULT_PART_BYTES, 2048 * 1024**2)
        total = 3 * 1024**3 + 17
        for limit in (64 * parts.MIB, parts.DEFAULT_PART_BYTES, 4096 * parts.MIB):
            entry = {'bytes': total, 'sha256': 'a'*64}
            if total > limit:
                entry['parts'] = [{'name': parts.part_name('image', entry, limit, index+1),
                                  'offset': offset, 'bytes': min(limit, total-offset), 'sha256': 'b'*64}
                                 for index, offset in enumerate(range(0, total, limit))]
            parts.validate_file('image', entry, limit)
        for limit in (0, -1, True, parts.MAX_PART_BYTES+1):
            with self.assertRaises(ValueError): parts.part_size(limit)
        with self.assertRaises(ValueError):
            parts.validate_file('image', {'bytes': parts.DEFAULT_PART_BYTES+1, 'sha256': 'a'*64})

    def test_exact_edges_and_repacking_for_changed_line_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'image'; out = root/'out'; out.mkdir()
            for size in (1, 6, 7, 8, 14, 15, 257):
                source.write_bytes(bytes(i % 251 for i in range(size)))
                for limit in (7, 11, 37):
                    with self.subTest(size=size, limit=limit):
                        entry = parts.describe(source, limit)
                        parts.validate_file('image', entry, limit)
                        self.assertEqual(parts.describe(source, limit), entry)
                        target = out/'image'; target.unlink(missing_ok=True)
                        if size > limit:
                            parts.assemble(target, entry, root, limit)
                            self.assertEqual(target.read_bytes(), source.read_bytes())
                        else:
                            self.assertNotIn('parts', entry)

    def test_missing_reordered_duplicate_corrupt_and_wrong_total_never_publish(self):
        for failure in ('missing', 'reordered', 'duplicate', 'corrupt', 'total', 'offset', 'truncated'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); source = root/'image'; source.write_bytes(b'0123456789abcdefghijk')
                entry = parts.describe(source, 7); target_dir = root/'out'; target_dir.mkdir()
                target = target_dir/'image'
                if failure == 'missing': (root/entry['parts'][1]['name']).unlink()
                elif failure == 'reordered': entry['parts'].reverse()
                elif failure == 'duplicate': entry['parts'][1] = copy.deepcopy(entry['parts'][0])
                elif failure == 'corrupt': (root/entry['parts'][1]['name']).write_bytes(b'xxxxxxx')
                elif failure == 'truncated': (root/entry['parts'][1]['name']).write_bytes(b'x')
                elif failure == 'offset': entry['parts'][1]['offset'] += 1
                elif failure == 'total':
                    # Each part remains valid; only the expected whole hash changes.
                    entry['sha256'] = entry['sha256'][:16] + '0'*48
                with self.assertRaises(ValueError): parts.assemble(target, entry, root, 7)
                self.assertEqual(list(target_dir.iterdir()), [])

    def test_interrupted_transfer_resumes_only_verified_parts_and_fresh_readback_refetches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'src'; target = root/'dst'; source.mkdir(); target.mkdir()
            path = source/'image'; path.write_bytes(b'0123456789abcdefghijk')
            entry = parts.describe(path, 7); calls = []
            def fetch(url, destination, digest, size):
                name = url.rsplit('/', 1)[-1]; calls.append(name)
                if len(calls) == 2: raise ConnectionError('finite interrupted-line fixture')
                data = (source/name).read_bytes()
                self.assertEqual(len(data), size); self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                destination.write_bytes(data)
                return {'http_status': 200, 'sha256': digest}
            with self.assertRaises(ConnectionError):
                parts.receive_file('https://example.invalid', 'image', entry, target, fetch, 7)
            self.assertFalse((target/'image').exists())
            receipt = parts.receive_file('https://example.invalid', 'image', entry, target, fetch, 7)
            self.assertEqual(receipt[0]['state'], 'VERIFIED_CACHE')
            self.assertEqual(calls.count(entry['parts'][0]['name']), 1)
            self.assertEqual((target/'image').read_bytes(), path.read_bytes())
            before = len(calls)
            parts.receive_file('https://example.invalid', 'image', entry, target, fetch, 7, fresh=True)
            self.assertEqual(len(calls)-before, len(entry['parts']))

    def test_bad_existing_output_and_symlink_part_are_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'image'; source.write_bytes(b'0123456789')
            entry = parts.describe(source, 7); out = root/'out'; out.mkdir(); target = out/'image'
            target.write_bytes(b'preserve')
            with self.assertRaises(ValueError): parts.assemble(target, entry, root, 7)
            self.assertEqual(target.read_bytes(), b'preserve')
            target.unlink(); part = root/entry['parts'][0]['name']; part.unlink(); part.symlink_to(source)
            with self.assertRaises(ValueError): parts.assemble(target, entry, root, 7)
            self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
