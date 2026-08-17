# Terminal Effect Evidence Basis

## Status

This candidate defines a fail-closed, machine-readable basis for deciding when
merge, publication, release, deployment, `PASS`, `FINAL_PASS`, and
`EFFECT_ACK_DONE` may later be asserted. It performs none of those effects and
sets every completion claim to `false`.

## Why a separate basis is required

A source change, a green workflow, an uploaded artifact, a transport
acknowledgement, and a confirmed external effect are different events. The basis
keeps them different and binds every transition to the newly resolved exact
repository head, tree, scope, authorization, artifact, target, and receipt.

The evaluator rejects predecessor-head gate evidence, `action_required`,
zero-job runs, unclear materialization provenance, review/ruleset gaps,
competing writers, stale leases, and unbound authorizations. A
tree-identical trusted carrier is accepted only when its materialized tree and
provenance have already been verified.

## Evaluation

```bash
python3 -B tools/qikvrt_terminal_effect_basis.py evaluate \
  --evidence path/to/evidence.json
```

The output has two deliberately separate surfaces:

- `readiness`: whether the exact evidence basis for a later transition is
  present;
- `completion_claims`: always false in this evaluator.

`ALL_BASES_READY` therefore means only that a supplied evidence packet satisfies
the basis contract. It does not mean that any effect has happened and does not
authorize the controller to perform one.

## Readiness chain

`PASS_basis_ready` requires an exact candidate binding, trusted integrity
materialization or carrier provenance, terminal-success applicable workflows
with at least one executed job each, and a clear single-writer/lease state.

`merge_basis_ready` additionally requires a non-draft mergeable pull request,
satisfied ruleset and required-review evidence, and an exact force-disabled
merge authorization.

Publication and release bases each require immutable artifact digests and their
own exact authorization. Publication also binds metadata, rights, and scientific
status. Release binds version, SBOM, and provenance. Deployment requires the
same immutable artifact as the release, an environment, a rollback-plan digest,
and a separate deployment authorization.

`FINAL_PASS_basis_ready` additionally requires verified receipts for merge and
all three requested external-effect classes, live readback, a newly resolved
post-promotion Authority head and tree, post-promotion integrity, and fresh
executed exact-head gates.

`EFFECT_ACK_DONE_basis_ready` additionally requires zero pending required
effects and a closure receipt whose effect set, Authority binding, digest, and
live readback are exact.

## Non-promotion rules

The following implications are forbidden:

```text
BASIS_READY        != EFFECT_DONE
WORKFLOW_SUCCESS   != EXTERNAL_EFFECT
TRANSPORT_ACK      != EFFECT_ACK
PREDECESSOR_GREEN  != CURRENT_HEAD_GREEN
BOT_REVIEW         != INDEPENDENT_HUMAN_REVIEW
```

Actual merge, publication, release, deployment, `PASS`, `FINAL_PASS`, and
`EFFECT_ACK_DONE` remain separate, exact-evidence-bound transitions.
