# Standard Terminal Pattern — Continuation Addendum

This addendum makes the continuation semantics normative for every component that adopts the Standard Terminal Pattern.

A terminal loop MUST NOT terminate merely because observation, CI, materialization, or review preparation is successful. After every stable observation it MUST invoke the universal continuation selector.

Selector outcomes:

- `CONTINUE`: execute the uniquely determined bounded action through a capable adapter, then test, reobserve, persist, and reenter;
- `REOBSERVE`: refresh stale bindings before any action;
- `REQUEST_AUTHORITY`: persist the exact missing authority boundary;
- `HOLD`: persist the deterministic blocker or ambiguity;
- `NOOP`: persist an evidence-bound fixpoint.

If the observing component lacks capability to execute `CONTINUE`, it MUST route the bound action to a capable executor. Capability absence is not permission to degrade silently to monitor-only behavior.

The addendum preserves the standing boundaries: observation is not execution; candidate success is not canonical state; bot review disposition is not independent review authority; transport acknowledgement is not effect acknowledgement; virtualized execution is not physical hardware execution.
