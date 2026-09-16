from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_trusted_exact_subject_p2.yml'

class ExactSubjectIdentityTests(unittest.TestCase):
    def test_identity_is_bound_before_checkout(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        bind = text.index('Bind exact current PR subject')
        checkout = text.index('Check out exact candidate head')
        execute = text.index('Execute fresh exact-head P2')
        self.assertLess(bind, checkout)
        self.assertLess(checkout, execute)

if __name__ == '__main__':
    unittest.main()
