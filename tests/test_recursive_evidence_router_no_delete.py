import unittest

from src.qikvrt.recursive_evidence_router import RecursiveEvidenceRouter


class NoEvidenceDeletionApiTest(unittest.TestCase):
    def test_router_has_no_evidence_deletion_operation(self):
        router = RecursiveEvidenceRouter()
        self.assertFalse(hasattr(router, "delete"))
        self.assertFalse(hasattr(router, "remove"))
        self.assertTrue(hasattr(router, "learn"))


if __name__ == "__main__":
    unittest.main()
