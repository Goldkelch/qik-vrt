from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'qikvrt_trusted_exact_subject_p2.yml'


class TrustedExactSubjectP2ContractTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')

    def test_dispatch_requires_pr_and_expected_head(self):
        self.assertIn('pr:', self.text)
        self.assertIn('expected_head:', self.text)
        self.assertIn('required: true', self.text)

    def test_exact_pr_head_is_independently_read_back(self):
        self.assertIn('pulls/$PR_NUMBER', self.text)
        self.assertIn("--jq '.head.sha'", self.text)
        self.assertIn('observed', self.text)
        self.assertIn('EXPECTED_HEAD', self.text)

    def test_checkout_and_execution_are_exact_head_bound(self):
        self.assertIn('ref: ${{ env.EXPECTED_HEAD }}', self.text)
        self.assertIn('git rev-parse --verify HEAD^{commit}', self.text)
        self.assertIn('python3 tools/qikvrt_integrity.py verify', self.text)
        self.assertIn('make test', self.text)

    def test_validation_carrier_has_no_write_authority(self):
        self.assertIn('contents: read', self.text)
        self.assertIn('pull-requests: read', self.text)
        self.assertNotIn('contents: write', self.text)
        self.assertNotIn('pull-requests: write', self.text)
        self.assertNotIn('git push', self.text)
        self.assertNotIn('gh pr review', self.text)


if __name__ == '__main__':
    unittest.main()
