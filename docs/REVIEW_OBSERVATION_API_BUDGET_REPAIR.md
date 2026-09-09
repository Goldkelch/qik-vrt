# Review observation API-budget repair

TEMDD successor binding for the exact-head review-control-plane repair.

## Exact predecessor

- PR: `#1044`
- head: `98f9e2a776a199c0eb9e48120cecfcb5f992537b`
- tree: `177336eef9798ea5854d621937d6cd35e0b913fb`
- trusted main observed by the reproduced failing executor: `b4b0038bcaa8788098ffa529bd5d5b651dd0459c`
- reproduced run: `34136833479`
- first causal blocker: `INVALID_REVIEW_SNAPSHOT`
- platform detail: GitHub installation API rate limit / HTTP 403 before receipt derivation.

## Repair contract

The next implementation must reduce exact-subject observation API demand without weakening authority:

1. Reuse immutable fields from the exact `pull_request_target.review_requested` payload when they are already bound to the selected expected head.
2. Collapse identical repository reads within one bounded observation.
3. Retain only the minimum authoritative delta reads required for current-main identity, required gates, discussion/review state, and active-writer exclusion.
4. Fail closed if any required authoritative fact remains unavailable.
5. Event/cached data never establishes independent Code-Owner approval, merge, PASS, FINAL_PASS, publication, or `EFFECT_ACK_DONE`.
6. Regression coverage must demonstrate reduced API-call demand while preserving exact-head and fail-closed semantics.

This file records the repair subject only. It does not claim that the repair has been implemented or verified.
