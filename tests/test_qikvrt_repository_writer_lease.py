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

    def test_general_pr_integrity_writer_shares_exact_target_lease_and_is_atomic(self):
        path = Path('.github/workflows/qikvrt_pr18_integrity_repair.yml')
        text = path.read_text(encoding='utf-8')
        self.assertIn(
            'group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}',
            text,
        )
        self.assertIn('cancel-in-progress: false', text)
        self.assertIn("github.event_name == 'pull_request'", text)
        self.assertIn(
            'github.event.pull_request.head.repo.full_name == github.repository',
            text,
        )
        self.assertIn("github.actor != 'dependabot[bot]'", text)
        self.assertIn('EXPECTED_HEAD: ${{ github.event.pull_request.head.sha }}', text)
        self.assertIn('TARGET_REF: ${{ github.head_ref }}', text)
        self.assertNotIn('infra/live-status-default-branch', text)
        self.assertNotIn('git push --force', text)
        self.assertIn(
            'HOLD_UNVERIFIED: pull-request head differs before integrity repair',
            text,
        )
        self.assertIn(
            'HOLD_UNVERIFIED: pull-request head advanced before integrity persistence',
            text,
        )
        self.assertIn(
            'HOLD_UNVERIFIED: pull-request head advanced during local integrity commit',
            text,
        )
        self.assertIn(
            'HOLD_UNVERIFIED: pull-request integrity persistence readback mismatch',
            text,
        )
        commit = text.index(
            '      - name: Commit only the deterministic integrity trio with exact-head CAS'
        )
        commit_block = text[commit:]
        for integrity_path in (
            'REPOSITORY_FILE_MANIFEST.json',
            'REPOSITORY_FILE_MANIFEST.json.sha256',
            'SHA256SUMS.txt',
        ):
            self.assertIn(integrity_path, commit_block)
        self.assertNotIn('formalization/QIKVRT_Formalization_v2.0', commit_block)
        self.assertNotIn('docs/publications/', commit_block)
        self.assertIn('git push origin "HEAD:refs/heads/$TARGET_REF"', commit_block)

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


if __name__ == '__main__':
    unittest.main()
