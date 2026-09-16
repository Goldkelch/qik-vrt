from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_trusted_exact_subject_p2.yml'

class ExactSubjectBootstrapContract(unittest.TestCase):
    def test_p2_has_binary_executed_result(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('BLOCK: exact subject mismatch', text)
        self.assertIn('P2_EXECUTED', text)
        self.assertIn('result=PASS', text)
        self.assertNotIn('exit 0 # noop', text.lower())

if __name__ == '__main__':
    unittest.main()
