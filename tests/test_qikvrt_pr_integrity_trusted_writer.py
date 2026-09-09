from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/qikvrt_pr_integrity_trusted_writer.yml'


class TrustedPrIntegrityWriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding='utf-8')

    def test_uses_trusted_pull_request_target_boundary(self) -> None:
        self.assertIn('pull_request_target:', self.text)
        self.assertIn('ref: ${{ github.event.pull_request.base.sha }}', self.text)
        self.assertIn('persist-credentials: false', self.text)

    def test_pr_code_is_not_the_privileged_generator(self) -> None:
        self.assertIn('cp trusted/tools/qikvrt_integrity.py subject/tools/qikvrt_integrity.py', self.text)
        self.assertIn('cp trusted/tools/qikvrt_subprocess.py subject/tools/qikvrt_subprocess.py', self.text)
        self.assertIn('python3 -B tools/qikvrt_integrity.py generate', self.text)
        self.assertIn('python3 -B tools/qikvrt_integrity.py verify', self.text)

    def test_only_integrity_files_can_be_persisted(self) -> None:
        self.assertIn('REPOSITORY_FILE_MANIFEST\\.json', self.text)
        self.assertIn('REPOSITORY_FILE_MANIFEST\\.json\\.sha256', self.text)
        self.assertIn('SHA256SUMS\\.txt', self.text)
        self.assertIn('git add REPOSITORY_FILE_MANIFEST.json REPOSITORY_FILE_MANIFEST.json.sha256 SHA256SUMS.txt', self.text)

    def test_exact_head_drift_is_fail_closed(self) -> None:
        self.assertIn('remote_head=', self.text)
        self.assertIn('local_head=', self.text)
        self.assertIn('HOLD: PR head drifted before trusted integrity persistence', self.text)

    def test_no_polling_or_force_push(self) -> None:
        self.assertNotIn('schedule:', self.text)
        self.assertNotIn('--force', self.text)
        self.assertNotIn('sleep ', self.text)


if __name__ == '__main__':
    unittest.main()
