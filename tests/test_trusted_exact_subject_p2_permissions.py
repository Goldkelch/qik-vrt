from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_trusted_exact_subject_p2.yml'

class ExactSubjectPermissionTests(unittest.TestCase):
    def test_carrier_cannot_mutate_repository_or_review(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('contents: read', text)
        self.assertIn('pull-requests: read', text)
        for forbidden in ('contents: write', 'pull-requests: write', 'statuses: write', 'git push', 'gh pr review'):
            self.assertNotIn(forbidden, text)

if __name__ == '__main__':
    unittest.main()
