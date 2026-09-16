import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_seed_dashboard_publish.yml"


class SeedDashboardContinueSemanticsTest(unittest.TestCase):
    def test_revalidation_continue_does_not_abort_dashboard_materialization(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        revalidate = text.index("sh tools/qikvrt_seed_node_revalidation.sh")
        capture = text.index("revalidation_rc=$?", revalidate)
        case = text.index('case "$revalidation_rc" in', capture)
        accepted = text.index("0|10) ;;", case)
        publish = text.index("sh tools/qikvrt_seed_dashboard_publish.sh", accepted)
        self.assertLess(revalidate, capture)
        self.assertLess(capture, accepted)
        self.assertLess(accepted, publish)

    def test_unexpected_revalidation_error_remains_fail_closed(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('*) exit "$revalidation_rc" ;;', text)

    def test_continue_is_not_relabelled_as_effect(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("CONTINUE represented in dashboard evidence", text)
        self.assertNotIn("EFFECT_ACK_DONE=true", text)


if __name__ == "__main__":
    unittest.main()
