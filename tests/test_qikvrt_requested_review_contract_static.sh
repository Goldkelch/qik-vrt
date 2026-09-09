#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# Shared local/CI static bindings for the requested-review contract.

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

grep -F 'pull_request_target:' .github/workflows/qikvrt_requested_review_executor.yml
# The executor uses a folded compound job condition: preserve the trusted-main
# binding while proving that neither its technical review COMMENT nor any
# github-actions[bot] issue-comment receipt can feed back into a fresh
# observation.
grep -F "github.ref == 'refs/heads/main'" .github/workflows/qikvrt_requested_review_executor.yml
grep -F "github.event.review.user.login == 'github-actions[bot]'" .github/workflows/qikvrt_requested_review_executor.yml
grep -F "github.event.review.state == 'commented'" .github/workflows/qikvrt_requested_review_executor.yml
grep -F "startsWith(github.event.review.body, '<!-- qikvrt-mesh-review:v1 ')" .github/workflows/qikvrt_requested_review_executor.yml
grep -F "github.event_name == 'issue_comment'" .github/workflows/qikvrt_requested_review_executor.yml
grep -F "github.event.comment.user.login == 'github-actions[bot]'" .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'qikvrt-universal-terminal-live-surface-v1' tools/qikvrt_requested_review_executor.py
grep -F 'qikvrt-ruleset-apply:' tools/qikvrt_requested_review_executor.py
grep -F 'qikvrt-ruleset-authority:' tools/qikvrt_requested_review_executor.py
grep -F 'converted_to_draft' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'review_request_removed' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'labeled' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'REQUESTED_HEAD:' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'inputs.head ||' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'GITHUB_EVENT_PATH' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'event_payload_sha256' .github/workflows/qikvrt_requested_review_executor.yml
grep -F -- '--event-context-file /tmp/qikvrt-review-event-context.json' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'issue_comment:' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'review_requested' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'select_review_subject' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'WORKFLOW_DISPATCH_HEAD_MISSING' tools/qikvrt_requested_review_executor.py
grep -F 'REVIEW_INTAKE_SCHEMA' tools/qikvrt_requested_review_executor.py
grep -F 'GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE' tools/qikvrt_requested_review_executor.py
grep -F 'qikvrt-mesh-review-selection-' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'EVENT_WORKFLOW_EVENT' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'schedule:' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F '*/5 * * * *' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'BOUNDED_SCHEDULE_ROTATION' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'pulls?state=open' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'schedule:' .github/workflows/qikvrt_autonomous_pr_head_continuation.yml
! grep -F 'qikvrt_requested_review_executor.yml/dispatches' .github/workflows/qikvrt_autonomous_pr_head_continuation.yml
! grep -F 'QIKVRT requested review executor' .github/workflows/qikvrt_autonomous_pr_head_continuation.yml
grep -F 'workflow_run:' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'refs/heads/qikvrt/mesh-review-ledger-v1' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'qikvrt/mesh-review-ledger-v1' .github/workflows/qikvrt_ci.yml
grep -F 'def _git_scope' tools/qikvrt_requested_review_executor.py
grep -F '"--no-ext-diff", "--no-textconv", "--no-renames"' tools/qikvrt_requested_review_executor.py
grep -F 'REQUIRED_GATE_PATHS_JSON' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'post-ledger-cas' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'post-review-comment' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'post-status' .github/workflows/qikvrt_requested_review_executor.yml
grep -F -- '-f commit_id="$EXPECTED_HEAD" -f event=COMMENT' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'if-no-files-found: error' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'include-hidden-files: true' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'latest_status_matches_projection' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'HOLD_UNVERIFIED' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'independent Code-Owner approval: **not implied**' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'event=APPROVE' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'event=REQUEST_CHANGES' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F '<<EOF' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'git push' .github/workflows/qikvrt_requested_review_executor.yml
! grep -F 'gh pr merge' .github/workflows/qikvrt_requested_review_executor.yml
grep -F 'permissions: {}' .github/workflows/qikvrt_code_owner_review_observer.yml
grep -F 'QIKVRT requested review executor' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'QIKVRT required code-owner review' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'select_required_review_targets' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'plan-native-account-review:' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'QIKVRT_GOLDKELCH_REVIEW_TOKEN' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'DELEGATED_ACCOUNT_TOKEN_IDENTITY_MISMATCH' tools/qikvrt_native_account_review.py
grep -F 'OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1' policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json
tr '\n' ' ' < docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md \
  | grep -F 'delegated platform-account action'
grep -F 'qikvrt-required-code-owner-selection-' .github/workflows/qikvrt_required_review_gate.yml
! grep -F 'schedule:' .github/workflows/qikvrt_required_review_gate.yml
! grep -F '*/5 * * * *' .github/workflows/qikvrt_required_review_gate.yml
! grep -F 'pulls?state=open' .github/workflows/qikvrt_required_review_gate.yml
grep -F 'INELIGIBLE_EVENT_TARGET' .github/workflows/qikvrt_code_owner_review_observer.yml
! grep -F 'BLOCK: pull request is not based on main' .github/workflows/qikvrt_code_owner_review_observer.yml
grep -F 'require_code_owner_review' tools/qikvrt_required_review_gate.py
grep -F 'dismiss_stale_reviews_on_push' tools/qikvrt_required_review_gate.py
grep -F 'require_last_push_approval' tools/qikvrt_required_review_gate.py
grep -F 'QIKVRT requested review execution' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'QIKVRT required code-owner review' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'statuses?per_page=100' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'mesh_review_status_projection' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'require_unchanged_mesh_review_status' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'require_unchanged_promotion_marker' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F 'HEAD^1' .github/workflows/qikvrt_expected_head_promotion.yml
! grep -F 'pulls/${PR_NUMBER}/merge' .github/workflows/qikvrt_expected_head_promotion.yml
grep -F "tools/qikvrt_requested_review_executor.py','verify'" .github/workflows/qikvrt_expected_head_promotion.yml
grep -F "'--expected-diff',str(diff_path)" .github/workflows/qikvrt_expected_head_promotion.yml
