# Issue #94 deterministic fallback

This implementation introduces a bounded, idempotent work-unit planner for blocked repository-native issue processing.

## Invocation

```sh
python3 tools/issue_agent_work_units.py --issue 79
```

The command persists canonical state under `evidence/issues/79/work-units/`, writes SHA-256 binding for the state, and emits `STATUS.work-units.json` as the aggregate handoff.

When semantic model inference is unavailable, the planner still completes deterministic discovery, inventory, and source-hash binding, then stops at the exact semantic cursor with `EFFECT_ACK_CONTINUE`. Completed units are not repeated on resume.

## Dispatcher integration

The existing issue-processing workflow already calls `scripts/issue_agent/finalize.py` after the semantic inference attempt. `finalize.py` now invokes the work-unit planner automatically whenever inference is unavailable or unsuccessful.

On successful fallback execution:

- `STATUS.work-units.json` is parsed;
- the aggregate work-unit state is promoted to canonical `STATUS.json`;
- `fallback_mode` is recorded as `deterministic_work_units`;
- `automatic_merge` remains false until every mandatory work unit is complete;
- the issue branch receives deterministic evidence through the existing commit and PR path.

If the planner or canonical promotion fails, `finalize.py` writes a precise fail-closed blocker and exits unsuccessfully. A broken fallback therefore cannot be hidden behind a successful pipeline status.

PR #88 remains the liveness and redispatch mechanism. Auto-finish remains forbidden until every mandatory work unit is `DONE` and the original Issue #79 gates are satisfied.

## Autonomy boundary

After this PR is merged, the repository can autonomously:

1. receive or redispatch an issue transaction;
2. attempt semantic inference;
3. fall back to deterministic work units on failure;
4. checkpoint granular state and a resume cursor;
5. commit materialized issue evidence through the existing issue branch;
6. resume completed work without restarting from zero;
7. remain fail-closed at the first genuinely semantic or external blocker.

Full scientific autonomy still depends on completing semantic claim extraction/classification, binding the native Lean build adapter, authenticated Authority/Mirror synchronization, and all Issue #79 completion gates.

## Fail-closed rules

- Extracted claims are not verified claims.
- Lean source is not proof without a native kernel receipt.
- Empirical claims are not promoted by model-internal proofs.
- Missing model inference is scoped to semantic work units.
- No `DONE`, `FINAL_PASS`, or `EFFECT_ACK_DONE` is emitted while any mandatory unit is incomplete.

Refs #79, #83, #88, #94.
