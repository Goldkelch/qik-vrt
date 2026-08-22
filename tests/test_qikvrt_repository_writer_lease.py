from pathlib import Path
import unittest


class RepositoryWriterLeaseTests(unittest.TestCase):
    def test_observed_writers_share_target_ref_lease(self):
        paths = [
            Path('.github/workflows/qikvrt_batch04_integrity.yml'),
            Path('.github/workflows/qikvrt_batch003_remaining_disposition.yml'),
        ]
        expected = 'group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}'
        for path in paths:
            text = path.read_text(encoding='utf-8')
            self.assertIn(expected, text, str(path))
            self.assertIn('cancel-in-progress: false', text, str(path))

    def test_batch003_has_pre_and_post_commit_drift_guards(self):
        text = Path('.github/workflows/qikvrt_batch003_remaining_disposition.yml').read_text(encoding='utf-8')
        self.assertIn('Bind exact source head before materialization', text)
        self.assertIn('target ref advanced before Batch-003 evidence persistence', text)
        self.assertIn('target ref advanced after local Batch-003 commit; refusing push', text)


if __name__ == '__main__':
    unittest.main()
