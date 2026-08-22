# QIK-VRT Zero-Bug Continuous Invariant v1

`ZERO-BUG` is an operational repository state, not a claim that no unknown defect can exist.

An exact observed head is in `ZERO_KNOWN_DETERMINISTIC_BUGS` only when every hard invariant in `policy/ZERO_BUG_CONTINUOUS_V1.json` is freshly evidenced on that exact head/tree and no known deterministic repository or workflow defect remains.

After every mutation the state is unconditionally reset to `HOLD_UNVERIFIED`. Previous gates, reviews and receipts do not transfer. The new head/tree must be reobserved and all applicable gates must be fresh.

Continuous agility and self-revision remain permitted under `PERFECT_OPTIMUM_V1`: later is not better; a candidate must preserve invariants, avoid metric regression and demonstrate strict bound progress. Arbitrary unregistered source self-modification remains `HOLD`.

The repair discipline is:

`OBSERVE_EXACT_HEAD_TREE -> IDENTIFY_FIRST_DETERMINISTIC_DEFECT -> SELECT_SMALLEST_REGISTERED_REPAIR -> VERIFY_SOURCE_HEAD_BEFORE_WRITE -> SERIALIZE_ONE_PRODUCTIVE_WRITER -> APPLY_MINIMAL_EFFECT -> REOBSERVE_NEW_HEAD_TREE -> REQUIRE_ALL_FRESH_GATES -> RETAIN_OR_HOLD`

This preserves `CAUSALITY != SEQUENCE`, `MUTATION != VERIFICATION`, and `REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`.
