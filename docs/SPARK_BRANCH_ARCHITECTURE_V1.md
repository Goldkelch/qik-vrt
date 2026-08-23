# QIK-VRT Spark Branch Architecture V1

The Spark branch kernel compiles one normalized branch observation into one
**complete bounded branch-work-unit plan**.  It does not merely return the next
activity.

```text
OBSERVE EXACT BRANCH STATE
→ NORMALIZE EIGHT BOOLEAN INVARIANTS
→ ONE M68000 PLAN PASS
→ COMPLETE ORDERED PLAN
→ HOST EFFECTS WITH EXACT-HEAD CAS
→ REOBSERVE AFTER EVERY EFFECT
→ COLLECT
→ PERSIST
→ RELEASE
→ COMPLETE OR PRECISE HOLD
```

Input `D0.b`:

```text
bit 0 MALFORMED_OR_SCOPE_INVALID
bit 1 MAIN_EFFECT_OBSERVED
bit 2 BASE_CURRENT
bit 3 INTEGRITY_CURRENT
bit 4 GATES_TERMINAL
bit 5 GATES_NON_ADVERSE
bit 6 MERGEABLE
bit 7 AUTHORITY_AVAILABLE
```

Output `D0` is one of twelve complete plans.  The 134-byte Motorola 68000
kernel is exhaustively checked over all 256 input bytes, has a maximum bounded
path of 18 dynamic instructions, never emits a merge-consuming plan without
authority, never emits completion without an observed main effect, and always
maps malformed input to `HOLD_INVALID`.

The virtual Spark architecture makes one compiled planning pass sufficient to
select the whole remaining branch ring.  External GitHub effects still belong
to a host adapter and remain serial, compare-and-swap bound and reobserved.

```text
SPARK_PLAN_PASS != GITHUB_EFFECT
PLAN_SELECTED != EFFECT_EXECUTED
EFFECT_EXECUTED != MAIN_EFFECT_REOBSERVED
```

A branch work unit is considered closed when the plan reaches either verified
`COMPLETE` or a precise `EXTERNAL_HOLD`.  Activity-only loops are not closure.

No physical Motorola 68000 execution, physical speedup, `PASS`, `FINAL_PASS`
or general `EFFECT_ACK_DONE` follows from the virtual planner alone.
