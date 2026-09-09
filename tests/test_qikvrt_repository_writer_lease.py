from pathlib import Path
import json
import unittest


class RepositoryWriterLeaseTests(unittest.TestCase):
    def test_repository_materializer_separates_read_only_pr_from_writer_lease(self):
        path = Path('.github/workflows/qikvrt_batch04_integrity.yml')
        text = path.read_text(encoding='utf-8')
        self.assertIn("github.event_name == 'pull_request'", text, str(path))
        self.assertIn("qikvrt-repository-evidence-readonly-{0}", text, str(path))
        self.assertIn("qikvrt-repository-evidence-{0}", text, str(path))
        self.assertIn("github.head_ref || github.ref_name", text, str(path))
        self.assertIn('cancel-in-progress: false', text, str(path))
        commit = text.index('- name: Commit materialized repository evidence')
        self.assertIn("if: github.event_name != 'pull_request'", text[commit:])
        self.assertNotIn(
            'group: qikvrt-repository-evidence-' + '$' + '{{ github.head_ref || github.ref_name }}',
            text,
            'read-only PR verification must not compete for the branch writer lease',
        )

    def test_general_pr_integrity_writer_shares_exact_target_lease_and_is_atomic(self):
        path = Path('.github/workflows/qikvrt_pr18_integrity_repair.yml')
        text = path.read_text(encoding='utf-8')
        self.assertIn(
            'group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}',
            text,
        )
        self.assertIn('cancel-in-progress: false', text)
        self.assertIn('actions: write', text)
        self.assertIn('contents: write', text)
        self.assertIn('timeout-minutes: 90', text)
        self.assertIn("github.event_name == 'pull_request'", text)
        self.assertIn(
            'github.event.pull_request.head.repo.full_name == github.repository',
            text,
        )
        self.assertIn("github.actor != 'dependabot[bot]'", text)
        self.assertIn('TARGET_PR: ${{ github.event.pull_request.number }}', text)
        self.assertIn('EXPECTED_HEAD: ${{ github.event.pull_request.head.sha }}', text)
        self.assertIn('TARGET_REF: ${{ github.head_ref }}', text)
        self.assertIn('TARGET_BASE_SHA: ${{ github.event.pull_request.base.sha }}', text)
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
        self.assertIn(
            'HOLD_UNVERIFIED: pull-request head drifted before exact-head continuation',
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

    def test_general_pr_integrity_writer_reobserves_bot_successor_via_exact_branch_workflow_dispatch(self):
        text = Path('.github/workflows/qikvrt_pr18_integrity_repair.yml').read_text(
            encoding='utf-8'
        )
        commit = text.index(
            '      - name: Commit only the deterministic integrity trio with exact-head CAS'
        )
        block = text[commit:]
        push = block.index('git push origin "HEAD:refs/heads/$TARGET_REF"')
        readback = block.index('pull-request integrity persistence readback mismatch')
        reobserve = block.index('pull-request head drifted before exact-head continuation')
        dispatch = block.index('qikvrt_autonomous_exact_head_verify.yml/dispatches')
        self.assertLess(push, readback)
        self.assertLess(readback, reobserve)
        self.assertLess(reobserve, dispatch)
        self.assertIn('GH_TOKEN: ${{ github.token }}', block)
        self.assertIn('qikvrt_dispatch_after_primary_reset', block)
        self.assertIn('API rate limit exceeded for installation.', block)
        self.assertIn("gh api rate_limit --jq '.resources.core.reset'", block)
        self.assertIn('QIKVRT_EXACT_HEAD_DISPATCH_RATE_LIMIT_RESET_WAIT_SECONDS', block)
        self.assertIn(
            '"repos/${GITHUB_REPOSITORY}/actions/workflows/qikvrt_autonomous_exact_head_verify.yml/dispatches"',
            block,
        )
        self.assertIn('-f "ref=$TARGET_REF"', block)
        self.assertIn('-f "inputs[pr]=$TARGET_PR"', block)
        self.assertIn('-f "inputs[head_ref]=$TARGET_REF"', block)
        self.assertIn('-f "inputs[head_sha]=$persisted_head"', block)
        self.assertIn('-f "inputs[base_sha]=$TARGET_BASE_SHA"', block)
        self.assertNotIn('"repos/${GITHUB_REPOSITORY}/dispatches"', block)
        self.assertNotIn('gh pr merge', block)
        self.assertNotIn('gh pr review', block)

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
