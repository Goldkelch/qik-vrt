from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_trusted_exact_subject_p2.yml'

class BootstrapCarrierTests(unittest.TestCase):
    def test_read_only_exact_subject_execution(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('expected_head:', text)
        self.assertIn('pulls/$PR_NUMBER', text)
        self.assertIn('ref: ${{ env.EXPECTED_HEAD }}', text)
        self.assertIn('make test', text)
        self.assertNotIn('git push', text)
        self.assertNotIn('contents: write', text)

if __name__ == '__main__':
    unittest.main()
