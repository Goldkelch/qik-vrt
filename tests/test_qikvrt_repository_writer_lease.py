from pathlib import Path
import json
import unittest


class RepositoryWriterLeaseTests(unittest.TestCase):
    def test_repository_materializer_keeps_exact_target_writer_lease(self):
        path = Path('.github/workflows/qikvrt_batch04_integrity.yml')
        text = path.read_text(encoding='utf-8')
        expected = 'group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}'
        self.assertIn(expected, text, str(path))
        self.assertIn('cancel-in-progress: false', text, str(path))

    def test_batch003_separates_read_only_pr_run_from_non_pr_writer_lease(self):
        path = Path('.github/workflows/qikvrt_batch003_remaining_disposition.yml')
        text = path.read_text(encoding='utf-8')
        self.assertIn("github.event_name == 'pull_request'", text, str(path))
        self.assertIn("'batch003-remaining-readonly'", text, str(path))
        self.assertIn("'repository-evidence'", text, str(path))
        self.assertIn('${{ github.head_ref || github.ref_name }}', text, str(path))
        self.assertIn('cancel-in-progress: false', text, str(path))
        self.assertGreaterEqual(
            text.count("if: github.event_name != 'pull_request'"),
            3,
            'integrity, complete gates, and persistence must remain non-PR writer-only',
        )

    def test_batch003_has_pre_and_post_commit_drift_guards(self):
        text = Path('.github/workflows/qikvrt_batch003_remaining_disposition.yml').read_text(encoding='utf-8')
        self.assertIn('Bind exact source head before materialization', text)
        self.assertIn('target ref advanced before Batch-003 evidence persistence', text)
        self.assertIn('target ref advanced after local Batch-003 commit; refusing push', text)

    def test_issue_writer_shares_nonpreemptive_branch_lease(self):
        path = Path('.github/workflows/issue-autonomous-processing.yml')
        text = path.read_text(encoding='utf-8')
        self.assertIn(
            'group: qikvrt-repository-evidence-issue-agent/${{ github.event.issue.number || inputs.issue_number }}',
            text,
        )
        self.assertIn('cancel-in-progress: false', text)
        self.assertNotIn('git push --force', text)
        self.assertIn('issue branch advanced before history-preserving persistence', text)

    def test_zero_bug_writer_inventory_includes_issue_producer(self):
        policy = json.loads(
            Path('policy/ZERO_BUG_CONTINUOUS_V1.json').read_text(encoding='utf-8')
        )
        self.assertIn(
            'Autonomous issue processing',
            policy['audit_surface']['writer_workflows'],
        )

    def test_read_only_promotion_observer_never_occupies_review_writer_lease(self):
        promotion_name = 'QIK-VRT expected-head promotion executor'
        promotion_path = Path('.github/workflows/qikvrt_expected_head_promotion.yml')
        promotion = promotion_path.read_text(encoding='utf-8')
        permissions = promotion.split('permissions:', 1)[1].split('concurrency:', 1)[0]
        self.assertIn('actions: read', permissions)
        self.assertIn('contents: read', permissions)
        self.assertIn('pull-requests: read', permissions)
        self.assertIn('statuses: read', permissions)
        self.assertNotIn(': write', permissions)

        inventories = (
            (Path('.github/workflows/qikvrt_requested_review_executor.yml'), 'WRITER_WORKFLOWS_JSON:'),
            (Path('.github/workflows/qikvrt_required_review_gate.yml'), 'WRITER_WORKFLOWS_JSON:'),
            (promotion_path, 'MESH_REVIEW_WRITER_WORKFLOWS_JSON:'),
        )
        for path, key in inventories:
            text = path.read_text(encoding='utf-8')
            lines = text.splitlines()
            matched = 0
            for index, line in enumerate(lines):
                if line.strip() != key:
                    continue
                matched += 1
                self.assertLess(index + 1, len(lines), str(path))
                raw = lines[index + 1].strip()
                values = json.loads(raw)
                self.assertIsInstance(values, list, str(path))
                self.assertNotIn(promotion_name, values, str(path))
            self.assertGreater(matched, 0, f'{key} absent from {path}')


if __name__ == '__main__':
    unittest.main()
