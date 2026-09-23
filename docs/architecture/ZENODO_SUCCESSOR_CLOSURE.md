# Zenodo successor closure

A semantic repository successor must never remain silently coupled to a predecessor Zenodo candidate.

```text
SOURCE_CHANGED
→ MATERIALIZE_FRESH_CANDIDATE
→ CHECK_EXACT_SOURCE_IDENTITIES
→ AWAIT_EXACT_CANDIDATE_OWNER_AUTHORIZATION
→ PUBLISH
→ FRESH_PUBLIC_RECORD_AND_FILE_READBACK
→ PERSIST_RECEIPT
→ PUBLICATION_EFFECT_ACK_DONE
```

Candidate materialization is automatic for same-repository pull requests. Main fails closed if a registered target reaches Main without a current public receipt for the same exact source bytes. Once a current candidate-specific authorization and publish request exist, publication, public readback and receipt persistence are automatic.

The human authorization boundary remains explicit. Automation must not manufacture an owner authorization or transfer a predecessor authorization to changed bytes.

For every registered source file `p`:

```text
candidate.git_blob(p)
= publish_request.git_blob(p)
= public_receipt.git_blob(p)
= current_repository.git_blob(p)
```

Any mismatch is non-terminal and machine-visible. New publication families must be registered in `policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json`.

## Bot-successor recovery invariant

GitHub deliberately suppresses recursive ordinary workflow execution after a
workflow pushes with `GITHUB_TOKEN`. Therefore a workflow-generated successor
must never rely on a new ordinary `pull_request` run to verify itself.

The deterministic integrity/publication projection performs candidate
materialization and integrity regeneration in one commit. If that commit
creates a new PR head, the same admitted run immediately emits the trusted
`qikvrt_autonomous_exact_head_verify` repository-dispatch for the exact new
SHA. The default-branch verifier then executes the full repository gates against
that successor.

A second independent recovery edge remains active: zero-job
`action_required` observations for the projection or successor-closure guard
are classified by trusted-main automation and dispatch the same exact-head
REOBSERVE path. Thus a workflow-created head cannot become a silent terminal
state merely because GitHub suppresses recursive PR workflow admission.

Publication-receipt persistence applies the same rule: after a successful
Zenodo effect and persisted fresh public readback, a non-main PR successor is
immediately rebound and dispatched for exact-head repository verification.

These recovery edges do not create or transfer owner authorization and do not
turn a pending or failed publication into `EFFECT_ACK_DONE`.

## Mesh enforcement

The successor-freshness and public-effect guard runs on every repository node that carries the registry. Only the Authority node may execute the production Zenodo mutation. Mirror nodes independently enforce the same source/candidate/public-receipt identity and therefore cannot silently treat an Authority predecessor receipt as current after local semantic drift.
