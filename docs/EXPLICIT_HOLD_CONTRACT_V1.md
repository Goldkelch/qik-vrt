# QIK-VRT Explicit HOLD Contract V1

A HOLD is not permission to stop explaining. It is a typed transition with a
precise cause and a single continuation path.

Every new `HOLD` or `HOLD_UNVERIFIED` must bind:

1. a deterministic `reason_code` and human-readable reason;
2. the exact repository subject and immutable head identity;
3. concrete evidence references;
4. the responsible role and actor;
5. the exact retry event and predicate;
6. one executable or externally bounded next action;
7. the correct D0 class.

The following are not valid reasons: `UNSPECIFIED`, `UNKNOWN`, `WAIT`, `RETRY`
or a missing blocker. Missing, stale, zero-job or drifted evidence is `D0=2
REOBSERVE`. Missing authority is `D0=3 REQUEST_AUTHORITY`. `D0=1 HOLD` is
reserved for a presently active/adverse condition, finding, unresolved thread,
invalid receipt or compare-and-swap conflict.

Historical receipts are append-only and are not rewritten. New projections may
normalize a complete legacy blocker into the explicit structure, but they may
never transfer predecessor evidence to a changed subject.

This contract does not establish merge, publication, PASS, FINAL_PASS or
EFFECT_ACK_DONE.
