import unittest

from tools.qikvrt_repository_dod_census import classify_branch, explicit_pr_disposition


class DodCensusTests(unittest.TestCase):
    def test_explicit_pr_disposition_is_exact_marker_only(self):
        self.assertEqual(
            explicit_pr_disposition("<!-- qikvrt-dod-pr-disposition:REJECT_WITH_EVIDENCE -->"),
            "REJECT_WITH_EVIDENCE",
        )
        self.assertIsNone(explicit_pr_disposition("REJECT_WITH_EVIDENCE"))

    def test_current_candidate_branch_is_regarded_without_claiming_merge(self):
        subject = "a" * 40
        row = classify_branch("integration/final", subject, subject, "b" * 40)
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "PRODUCTIVE_CURRENT_CANDIDATE")

    def test_default_main_is_regarded(self):
        row = classify_branch("main", "a" * 40, "b" * 40, "a" * 40)
        self.assertTrue(row["regarded"])
        self.assertEqual(row["disposition"], "MERGED")


if __name__ == "__main__":
    unittest.main()
