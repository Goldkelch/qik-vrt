import pathlib
import unittest


class DashboardTriStateContractTest(unittest.TestCase):
    def test_dashboard_publish_is_reached_for_zero_and_continue_only(self):
        workflow = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("0|10) ;;", workflow)
        self.assertIn('*) exit "$revalidation_rc" ;;', workflow)
        self.assertIn("sh tools/qikvrt_seed_dashboard_publish.sh", workflow)


if __name__ == "__main__":
    unittest.main()
