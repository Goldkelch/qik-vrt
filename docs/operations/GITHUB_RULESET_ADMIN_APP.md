# Scoped GitHub App route for main-ruleset reconciliation

The selected implementation is the source in this same Git tree, not an older
issue recipe. `QIKVRT autonomous ruleset effect loop` is the sole ruleset writer.
Its native ingress is completion of `QIKVRT required code-owner review`;
selection reobserves the exact upstream workflow, artifact, PR head and Main.
The removed standalone reconciler and removed dispatch bridge are not endpoints
that can be invoked. This contract is not evidence of configuration or effect.

## One repository, one narrow permission

Install a dedicated GitHub App only on `Goldkelch/qik-vrt`. Grant repository
**Administration: read/write** and implicit metadata read, without contents,
issues, pull-request, status, Actions, organization or other-repository access.
The job's ordinary `GH_TOKEN` is `${{ github.token }}`. Only the scoped effect
step receives the minted token as `QIKVRT_RULESET_ADMIN_TOKEN`.

The exact selected implementation consumes:

- Repository variable: `QIKVRT_RULESET_APP_ID` (the App ID; action input `app-id`).
- Actions secret: `QIKVRT_RULESET_APP_PRIVATE_KEY`.
- Minted token: `steps.app-token.outputs.token`; never a stored admin fallback.

Do not configure a legacy `QIKVRT_RULESET_ADMIN_TOKEN` secret to fix ordinary
reads. No credential value belongs in Git, issues, PRs, artifacts or chat.
Source validation checks these names against the actual workflow. Historical
issue recipes remain provenance and must not override this selected contract.

The mint action requests only `permission-administration: write`, explicitly
scoped to the current repository owner and `qik-vrt`. The App token is not a
Goldkelch user-review credential and cannot substitute for that identity.

## Missing authority and technical failures

Missing App configuration is `REQUEST_AUTHORITY`. A failed configuration check,
failed token mint, rejected permission, API failure, ETag conflict or mismatching
readback is failing `HOLD`. Neither condition falls through to a broad or
long-lived credential, becomes a green closure, or permits repeated PUTs.
The precise missing capability is preserved independently of Owner consent.
Another general authorization message does not create an App installation.

The surviving native writer performs: ordinary-token exact-subject observation;
scoped token mint; authenticated ruleset GET; canonical-policy comparison;
a single conditional PUT only on drift; authenticated exact GET readback.
A transport response alone is not the readback. A durable current-receipt marker
never suppresses a fresh ruleset read. The writer does not submit or impersonate
a native review, dispatch the review gate to itself, merge or publish.

## Bootstrap and operational closure

The ordinary-read bootstrap must work without the administrative secret.
Candidate verification proves implementation scope only. Repair closure is a
separate post-promotion predicate: native adoption in exact Main history,
unchanged exact Main before/after observation, actual current ruleset readback,
and newly executed nonempty regression probes on that Main.

`policy/REPAIR_EFFECTIVENESS_CLOSURE_V1.json` registers these failure classes.
`make repair-effectiveness-contract` runs candidate-local regressions, including
mutated-bootstrap and configuration-recipe counterexamples. The existing
`QIKVRT zero-bug continuous invariant` workflow has a separate Main-only
`repair-effectiveness` job. It never requires a candidate to be deployed before
its own merge. There is no second polling or dispatch controller and no pending
pre-merge status that creates a self-blocking promotion dependency.

An unmerged repair remains VERIFIED_NOT_EFFECTIVE. A missing/failed probe,
zero tests, stale head, unverifiable adoption or non-current ruleset cannot
produce a closed receipt. A workflow failure preserves the structured receipt
when available; it is not hidden by an unconditional success conclusion.
The receipt is written outside the immutable source checkout. Manual issue
closure, PR closure and narrative reports are not operational closure evidence.

Ruleset administration and review are two separate capabilities. The delegated
native-review contract remains in
`docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md`; its activation and selected
user credential must be verified by the signer itself. Their presence is not
inferred from this document or from an empty review inventory.

A repair is only effective once the exact-Main receipt actually exists. This
contract cannot grant credentials, undo an external effect, certify future
immunity, or establish publication, PASS, FINAL_PASS or EFFECT_ACK_DONE.
