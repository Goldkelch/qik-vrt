import unittest

from src.qikvrt.recursive_evidence_router import Subject


class ExternalInterfaceCompatibilityTest(unittest.TestCase):
    def test_subject_node_identifier_is_not_restricted_to_local_repository(self):
        subject = Subject("https://neighbor.example/.well-known/effect-ack-Readback", "h", "t")
        self.assertTrue(subject.node.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
