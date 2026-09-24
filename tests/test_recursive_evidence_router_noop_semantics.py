import unittest

from src.qikvrt.recursive_evidence_router import NoAdmissibleRoute, RecursiveEvidenceRouter, Subject


class NoopSemanticsTest(unittest.TestCase):
    def test_unreachable_requested_information_is_a_blocker_not_success(self):
        a = Subject("A", "ha", "ta")
        z = Subject("Z", "hz", "tz")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter().traverse(a, z, "required", reobserve=lambda e: e, validate=lambda e: True)


if __name__ == "__main__":
    unittest.main()
