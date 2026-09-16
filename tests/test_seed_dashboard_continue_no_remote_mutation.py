import pathlib
import unittest


class ReadOnlyBoundaryTest(unittest.TestCase):
    def test_workflow_remains_contents_read_only(self):
        text = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("persist-credentials: false", text)


if __name__ == "__main__":
    unittest.main()
