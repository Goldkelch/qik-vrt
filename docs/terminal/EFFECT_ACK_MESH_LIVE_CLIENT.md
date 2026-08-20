# QIK-VRT Effect-Acknowledgement Mesh Live Client

## Purpose

The live client translates public repository activity into a bounded, causal,
evidence-referenced Effect Acknowledgement projection. It is a read-only view
of Authority, Mirror, pull-request transactions, exact-head workflow evidence,
independent review disposition, promotion, and effect boundaries.

It does not introduce a second protocol. The five canonical states remain:

- `EFFECT_NACK`
- `EFFECT_ACK_CONTINUE`
- `EFFECT_ACK_DONE`
- `EFFECT_ACK_ISOLATE`
- `EFFECT_ACK_BLOCK`

Repository-specific display states such as `PROGRESS`, `BLOCK`, `STALL`, and `COMPLETION_CANDIDATE` are profile mappings. STALL is not a sixth canonical state.

## Live effect chain

Every observed pull-request transaction is projected onto the same ordered set
of causal requirements:

```text
REQUEST
→ SOURCE_RECEIPT
→ AUTHORIZATION_RECEIPT
→ CANDIDATE_TREE
→ UNPRIVILEGED_EXECUTION
→ EVIDENCE_BUNDLE
→ INDEPENDENT_REVIEW
→ PROMOTION
→ AUTHORITY_EFFECT
→ MIRROR_EFFECT
→ PAIR_ACKNOWLEDGEMENT
```

The displayed bars are discrete evidence indicators for these stages. They are
not a percentage estimate and they do not count commits, comments, retries, or
workflow volume as progress.

```text
ACTIVITY != EFFECT
TRANSPORT_ACK != EFFECT_ACK
CAUSALITY != SEQUENCE
DETECTED_REPAIR != EFFECTIVE_REPAIR
IDENTITY != EQUALITY
```

## Causal fingerprint and stall

The client creates a canonical JSON projection containing only effect-relevant
bindings:

- Authority and Mirror main heads and trees;
- each transaction's base, head, observed tree, state, review disposition,
  stage statuses, deterministic blocker, and next effect.

Run IDs, timestamps, duplicate retries, and activity counts are excluded from
the causal fingerprint. The projection is SHA-256 bound.

Three consecutive observations with the same causal fingerprint produce:

```text
profile_state = STALL
retry_policy.mode = STOP_ON_STALL
```

The automatic observer then stops. A user may explicitly reobserve, but an
unchanged result remains a stall rather than manufactured progress.

## Public data boundary

The browser adapter uses only fixed public `GET` requests with
`credentials: "omit"` against:

- `Goldkelch/qik-vrt`;
- `ingolf-lohmann/qik-vrt`.

It reads public main commits, open pull requests, pull-request workflow runs,
and submitted reviews. It accepts no repository URL, credential, token,
command, or arbitrary endpoint from the user. It performs no workflow dispatch,
review, merge, branch update, repository write, release, deployment, or
publication.

The observer is rate-budgeted. It uses a 60-second base interval, progressive
backoff, a maximum of eight full observations per hour, and a twelve-second
request timeout. Public GitHub rate-limit or transport failures are observation
barriers. They do not establish a source defect.

## Review boundary

A bot-authored comment containing a substantive approval recommendation is not
an independent review approval. The client counts only the latest submitted
review disposition from a non-bot reviewer other than the pull-request author.
It does not infer Code Owner status from a username or comment.

## Completion boundary

The public view never derives `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` from
GitHub activity alone. Snapshot completion claims are fixed to `false`.

Even when every observable technical gate is non-adverse, completion still
requires independently bound evidence for authorization, review authority,
Authority effect, Mirror effect, and pair acknowledgement. Tree equality is
reported as evidence for the observed heads; it is not used to erase required
role-local identity.

## Files

- `docs/terminal/live/index.html` — accessible live visualization;
- `docs/assets/js/qikvrt-effect-ack-live-core.js` — pure causal classifier,
  fingerprinting, snapshot, and delta logic;
- `docs/assets/js/qikvrt-effect-ack-live.js` — fixed-endpoint browser adapter
  and renderer;
- `docs/assets/css/qikvrt-effect-ack-live.css` — responsive progress display;
- `docs/terminal/QIKVRT_EFFECT_ACK_MESH_LIVE_SNAPSHOT_V1.schema.json` —
  machine-readable snapshot contract;
- `tests/test_qikvrt_effect_ack_live_client.py` — security, schema, stall,
  review-authority, and causal-delta regression tests.

## Nonclaims

This client is a public observation and visualization component. It does not
claim repository-wide completion, protocol-wide conformance, external effect,
scientific establishment, deployment, publication, `PASS`, `FINAL_PASS`, or
`EFFECT_ACK_DONE`.
