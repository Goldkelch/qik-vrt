# MONITOR_ONLY_STALL repair

`MONITOR_ONLY_STALL` is the repository-wide failure class in which a component observes a stable state and reports it, but does not invoke the next-action selector even though the next bounded action is uniquely determined, authorized and supported by current evidence.

Repair pattern:

`OBSERVE -> BIND -> SELECT -> CONTINUE|NOOP|HOLD|REQUEST_AUTHORITY -> TEST -> REOBSERVE -> PERSIST -> REENTER`

This pattern is intentionally independent of any single PR or workflow. Components that cannot execute the selected action must persist the exact boundary and route the work to a capable executor rather than silently degrade to observation-only behavior.

## Required coverage

The class applies to repository monitors, terminal/watchdog loops, self-healing loops, review orchestration, integrity materialization, stacked-successor recovery, issue-agent work units, TEMDD/compiler pipelines, publication preparation and Authority/Mirror role-local coordination.

## Safety

Continuation is fail-closed. It never fabricates an owner action, independent review identity, external effect, successful deployment, publication, merge, PASS, FINAL_PASS or EFFECT_ACK_DONE. A real boundary becomes `HOLD` or `REQUEST_AUTHORITY`; a proved fixpoint becomes `NOOP`; stale evidence becomes `REOBSERVE`.
