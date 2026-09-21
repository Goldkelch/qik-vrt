# Alternating Exact-Subject Code-Owner Review

## Purpose

This note names and persists the repository mechanism needed to keep review progress continuous without confusing automated observation with native human authority.

The operating pattern is an **alternating two-node review path**:

```text
Node A creates or mutates an exact subject
  -> Node B reviews that exact HEAD/TREE
  -> any mutation creates a successor and invalidates subject-bound review evidence
  -> Node B may create or mutate the next subject
  -> Node A reviews that exact successor
  -> repeat
```

The goal is high review sampling rate with fail-closed evidence semantics, not self-approval.

## Invariants

1. **Exact subject.** Every technical receipt and review decision binds the exact `HEAD ∧ TREE`.
2. **No predecessor transfer.** A mutation creates a successor; predecessor review/test evidence is historical only until the successor is freshly validated.
3. **Independent native review.** The author identity of a pull request must not supply its own native approval or request-changes decision. The peer node/identity performs that review.
4. **Observer is not authority.** Review observers, requested-review executors, comments and status checks may discover, schedule and verify work, but do not synthesize a native Code-Owner review.
5. **Alternate the writer/reviewer roles.** When practical, the node that reviewed the current subject becomes the writer for the next successor and the other node becomes reviewer. This avoids a permanently idle review side and preserves throughput.
6. **Parallelize technical evidence, serialize authority.** Technical validation lanes may execute concurrently. Native review applies only after the exact candidate is known and must be re-established after mutation.
7. **Fail closed.** Missing, stale, ambiguous or unbound review evidence is not approval.
8. **Repository integration is separate from product DONE.** Review or merge does not establish deployment, public reachability, fresh public readback or EFFECT_ACK_DONE.

## Repository control-plane contract

For each reviewable pull request, the repository should materialize a review work unit containing at least:

```text
repository
pull_request
head
tree
base
author_identity
required_reviewer_identity
review_fingerprint
technical_gate_state
native_review_state
successor_of
predecessor_evidence_transfer=false
```

The scheduler should select a reviewer identity different from the PR author. If the current connected identity is the author, a failed self-review attempt is a routing signal, not a reason to retry the same identity. Route the work unit to the peer review node.

A native review is accepted only when its observed commit matches the current exact subject. A later push immediately makes that review historical for the new subject and schedules fresh technical validation plus peer review.

## Current witness: PR #1137

At the time this mechanism was identified, PR #1137 was:

```text
HEAD = 74e716e21a7607abb61b7263d6bbe5bbbf9525f2
TREE = 938d7907061f076b0d31e97b635effedca02a25c
AUTHOR = ingolf-lohmann
REQUESTED_REVIEWER = Goldkelch
```

The exact-subject proof lanes were successful, while the native review ledger remained empty. An attempted `REQUEST_CHANGES` operation through the author identity was rejected by GitHub as self-review. This is the concrete routing witness for the two-node rule: **the review must execute through the peer identity, not be simulated by the author-side executor.**

The technical review also found a fail-closed reporting defect in the 16-case comparator: selected malformed-input or argument-parse failures can terminate a rerun while leaving an older PASS report at the output path. That defect must be repaired on a successor and freshly validated; predecessor evidence does not transfer.

## Minimal transition algorithm

```text
on reviewable exact subject S:
    bind S = HEAD ∧ TREE
    require fresh technical admission/execution evidence for S

    reviewer := peer(author(S))
    dispatch review(S, reviewer)

    if native review is missing:
        HOLD_REVIEW
    elif review requests changes:
        create/await repaired successor S'
        invalidate subject-bound evidence from S
        validate S'
        dispatch review(S', peer(author(S')))
    elif review approves:
        continue only to the next independently required integration gate

    never map observer success, dispatch success, queue state,
    self-review failure, or predecessor approval to native approval
```

## Integration boundary

For the present stack, review of #1137 does not by itself establish integration into #1103, reconciliation with #1124, protected Main integration, deployment, public readback, or DONE. Each resulting mutation creates a new exact subject requiring the corresponding fresh evidence.

This contract is deliberately small: it defines **who reviews which immutable subject and how the roles alternate**. It does not grant either node authority to manufacture human approval.
