import pathlib
import unittest


class ContinueReceiptTest(unittest.TestCase):
    def test_artifact_contains_revalidation_and_dashboard_receipts(self):
        workflow = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        required = (
            "registry/NODEMESH_REVALIDATION.json",
            "evidence/seed_node_revalidation/LATEST.json",
            "evidence/seed_node_revalidation/runs/${{ env.QIKVRT_RUN_ID }}.json",
            "evidence/seed_dashboard/LATEST.json",
            "evidence/seed_dashboard/runs/${{ env.QIKVRT_RUN_ID }}.json",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertIn(path, workflow)


if __name__ == "__main__":
    unittest.main()
