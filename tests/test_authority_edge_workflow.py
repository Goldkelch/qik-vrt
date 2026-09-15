from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / '.github/workflows/qikvrt_authority_edge_request.yml'


class AuthorityEdgeWorkflowTest(unittest.TestCase):
    def test_producer_never_requires_admin_credential(self):
        text = PRODUCER.read_text(encoding='utf-8')
        self.assertNotIn('QIKVRT_GITHUB_ADMIN_TOKEN', text)
        self.assertNotIn('ADMIN_TOKEN', text)

    def test_producer_is_exact_head_bound_and_unprivileged(self):
        text = PRODUCER.read_text(encoding='utf-8')
        self.assertIn('github.event.pull_request.head.sha', text)
        self.assertIn('Goldkelch/qik-vrt', text)
        self.assertIn('github-actions[bot]', text)
        self.assertIn('dependabot[bot]', text)
        permissions = text.split('jobs:', 1)[0]
        self.assertIn('actions: read', permissions)
        self.assertIn('contents: read', permissions)
        self.assertNotIn('write', permissions)


if __name__ == '__main__':
    unittest.main()
