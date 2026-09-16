import pathlib
import unittest


class FailClosedBoundaryTest(unittest.TestCase):
    def test_only_documented_success_and_continue_codes_are_admitted(self):
        text = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("0|10) ;;", text)
        self.assertNotIn("0|1|10) ;;", text)
        self.assertIn('*) exit "$revalidation_rc" ;;', text)


if __name__ == "__main__":
    unittest.main()
