# QIK-VRT Zero-Bug Continuous Invariant v1

`ZERO-BUG` is an operational repository state, not a claim that no unknown defect can exist.

An exact observed head is in `ZERO_KNOWN_DETERMINISTIC_BUGS` only when every hard invariant in `policy/ZERO_BUG_CONTINUOUS_V1.json` is freshly evidenced on that exact head/tree and no known deterministic repository or workflow defect remains.

After every mutation the state is unconditionally reset to `HOLD_UNVERIFIED`. Previous gates, reviews and receipts do not transfer. The new head/tree must be reobserved and all applicable gates must be fresh.

Continuous agility and self-revision remain permitted under `PERFECT_OPTIMUM_V1`: later is not better; a candidate must preserve invariants, avoid metric regression and demonstrate strict bound progress. Arbitrary unregistered source self-modification remains `HOLD`.

The repair discipline is:

`OBSERVE_EXACT_HEAD_TREE -> IDENTIFY_FIRST_DETERMINISTIC_DEFECT -> SELECT_SMALLEST_REGISTERED_REPAIR -> VERIFY_SOURCE_HEAD_BEFORE_WRITE -> SERIALIZE_ONE_PRODUCTIVE_WRITER -> APPLY_MINIMAL_EFFECT -> REOBSERVE_NEW_HEAD_TREE -> REQUIRE_ALL_FRESH_GATES -> RETAIN_OR_HOLD`

This preserves `CAUSALITY != SEQUENCE`, `MUTATION != VERIFICATION`, and `REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`.

## Mandatory Mesh base algorithm: correct failure, then correct cause

Product Owner Ingolf Lohmann's September 8, 2026 directive is normative in
`policy/ZERO_BUG_CONTINUOUS_V1.json#base_algorithm`:

1. Correct the concrete error or blocker with the smallest authorized effect,
   then reobserve the actual result. A successful command is insufficient.
2. Identify and correct the causal mechanism. Symptom correction alone leaves
   the work unit open.
3. Reproduce the defect with a discriminating regression and verify the same
   test against the corrected exact subject.
4. Reobserve the original user-requested operation, not only the repair test.

Every discovered cause, prerequisite blocker and repair failure is another work
unit under this same algorithm. The end condition is a complete, freshly bound
inventory with no open known work units or descendants in the declared scope.
It is not universal bug freedom, promotion, publication or EFFECT_ACK_DONE.

Recursion is a finite event-driven dependency worklist, not a new endless
polling loop or unbounded agent spawning. At most one productive writer owns
an exact subject. A held dependency does not stop independent eligible work.
Cycles, missing children and the 4096-unit per-call budget boundary retain
HOLD; they never mean the backlog was discharged. Order comes from explicit
causal links, not timestamps, PR numbers or array order.

## Executable enforcement and reuse

The existing `tools/qikvrt_autonomous_self_heal.py:repair_handler` now performs
`probe -> one allowlisted repair -> probe` even after a nonzero exit or repair
timeout. The receipt preserves command return codes and SHA-256 hashes of
observation output. A successful local reprobe becomes
`SYMPTOM_CORRECTED_CAUSE_OPEN`, never `REPAIRED`. A failed command with a partial
successful effect remains `HOLD_REPAIR_INCOMPLETE`; it is not blindly repeated.
A missing post-effect observation is unknown. Local workspace results still
require exact committed-subject readback and original-flow validation.

The existing controller loads the mandatory basis policy before executing
registered handlers, invokes the reducer below, and carries unresolved cause
obligations in its result. The existing pre-effect wrapper retains that result;
no new signer, workflow scheduler, generic shell executor or writer authority
is introduced. Existing output artifacts/work-unit ledgers are the persistence
carriers. Before a subsequent event can close a repair, its client must retain
and reconcile those receipts. Without supplied history the controller reports
`UNKNOWN_NOT_CLEARED`; a clean later probe does not discharge earlier causes.

`tools/qikvrt_zero_bug.py:recursive_debugging_plan` validates the complete
four-stage causal receipt chain and every explicit child relation. The existing
zero-bug evaluator rejects an explicitly supplied open or invalid repair
inventory even if its local command markers are all green. Without an inventory
its old local-audit state remains local only and recursive completion is false.

Read-only evaluation of retained authoritative evidence:

```sh
python3 -B tools/qikvrt_zero_bug.py --repair-inventory exact-inventory.json
python3 -B tools/qikvrt_autonomous_self_heal.py check --repair-inventory exact-inventory.json
```

The inventory schema is `qikvrt_recursive_debugging_inventory_v1`. It contains
`subject` (`repository`, `base_sha`, `head_sha`, `tree_sha`), `scope`,
`inventory_receipt_id`, literal boolean `inventory_complete`, and `work_units`.
Each unit has a unique `id`, `original_scope`, `observation_receipt_id`, explicit
`blocked_by` and `causes` arrays, and a `receipts` object.

The receipt keys are `symptom`, `cause`, `regression`, `original_flow`. Each
success binds the current exact `subject`, a distinct `id`, and `after` equal
to the preceding receipt ID (the observation ID for `symptom`). Symptom and
cause readbacks also bind `effect_receipt_id`; cause identifies `mechanism`.
Regression carries a `test_id` and a `red` reproduction with the same test ID,
an identified subject/receipt and `status=failure`. The historical red subject
is not current green validation. Original-flow readback binds the unit's exact
`original_scope`. Every current-subject mutation invalidates downstream receipt
bindings; prior bytes remain historical evidence, not reusable validation.

This reducer validates supplied evidence relations. It does not authenticate
arbitrary JSON or itself make GitHub/external reads. Its callers must obtain
receipts from the existing authoritative observers. A plan is not permission
to run arbitrary input as code. Unknown credentials and capabilities remain
explicit open obligations; existing authority paths must be investigated, not
substituted or weakened. P0-P7, exact-account signing, ruleset controls and
external publication readbacks remain separate mandatory boundaries.

## Regression and attribution

The added tests cover false success after exit zero, failed-write partial
effects, timeouts, missing readback, symptom-only closure, unknown inventory,
parent/child obligations, cycles, missing links, input permutation, exact-subject
drift, red/green identity and original-flow scope. Local tests of the reducer
are not proof that every Mesh instance has adopted or executed the policy.

The normative two-stage debugging directive is Ingolf Lohmann's contribution.
The implementation, tests and explanatory integration are artificial-cognitive
work produced by ChatGPT under that directive; acceptance does not change that
origin. Repository review, promotion and runtime adoption remain separately
read-back-bound.
