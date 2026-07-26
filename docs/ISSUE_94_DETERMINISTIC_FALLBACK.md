# Issue #94 deterministic fallback

This implementation introduces a bounded, idempotent work-unit planner for blocked repository-native issue processing.

## Invocation

```sh
python3 tools/issue_agent_work_units.py --issue 79
```

The command persists canonical state under `evidence/issues/79/work-units/`, writes SHA-256 binding for the state, and emits `STATUS.work-units.json` as the aggregate handoff.

When semantic model inference is unavailable, the planner still completes deterministic discovery, inventory, and source-hash binding, then stops at the exact semantic cursor with `EFFECT_ACK_CONTINUE`. Completed units are not repeated on resume.

## Integration boundary

The existing issue-processing dispatcher should invoke this script before or as a fallback to monolithic model inference. PR #88 remains the liveness/redispatch mechanism. Auto-finish remains forbidden until every mandatory work unit is `DONE` and the original Issue #79 gates are satisfied.

The planner intentionally writes `STATUS.work-units.json` rather than overwriting the historical coarse `STATUS.json` in this first migration step. Promotion to the canonical aggregate status requires repository tests and review on the exact PR head.

## Fail-closed rules

- Extracted claims are not verified claims.
- Lean source is not proof without a native kernel receipt.
- Empirical claims are not promoted by model-internal proofs.
- Missing model inference is scoped to semantic work units.
- No `DONE`, `FINAL_PASS`, or `EFFECT_ACK_DONE` is emitted while any mandatory unit is incomplete.

Refs #79, #83, #88, #94.
