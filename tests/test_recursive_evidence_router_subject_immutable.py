import dataclasses
import unittest

from src.qikvrt.recursive_evidence_router import Subject


class SubjectImmutabilityTest(unittest.TestCase):
    def test_subject_is_frozen(self):
        subject = Subject("A", "h", "t")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            subject.head = "other"


if __name__ == "__main__":
    unittest.main()
