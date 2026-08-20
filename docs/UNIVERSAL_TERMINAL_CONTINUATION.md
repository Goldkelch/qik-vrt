# Universal Terminal Continuation Pattern

The universal terminal is not a monitor with notifications attached. It is a bounded causal control loop.

`OBSERVE -> BIND -> UNDERSTAND -> SELECT -> EXECUTE -> TEST -> REOBSERVE -> PERSIST -> REENTER`

A stable green observation is not itself a stop condition. If context, authority, meaning and evidence uniquely determine a bounded repository-native next action, the terminal must continue. Stopping at observation in that state is `MONITOR_ONLY_STALL`.

The only legitimate terminal states are:

- `NOOP`: an evidence-bound fixpoint has been established;
- `HOLD`: a deterministic blocker, ambiguity, missing evidence, missing authority, stale binding, or forbidden external effect exists;
- `REQUEST_AUTHORITY`: the next action is known but authority is genuinely absent;
- continuation: perform the uniquely determined bounded action and reobserve.

This rule applies generically to repository monitors, self-heal loops, requested-review orchestration, integrity materialization, issue work units, compiler/TEMDD pipelines, publication preparation, and Authority/Mirror role-local workflows.

## Causal-epistemic binding

Every continuation decision binds four things together before execution:

1. context — exact repository, role, base, head, tree and semantic scope;
2. authority — who or what is allowed to cause the next transition;
3. meaning — what that transition denotes and what it does not denote;
4. evidence — the exact observations supporting the transition.

No layer may infer execution from sequence, candidate success from canonical effect, transport acknowledgement from effect acknowledgement, or bot disposition from independent review authority.

## Acceleration rule

Previously proved bounded transitions may be compressed into tested macro-transitions. This is optimization by verified equivalence, not by deleting causal distinctions. A terminal may therefore reduce operational path length while preserving every required semantic and authority boundary.

## TEMDD integration

Tested Event Model Driven Development uses this pattern recursively:

`event model -> semantic validation -> lowering -> execution request -> observation -> acknowledgement boundary -> next event`

A verified intermediate state feeds the next admissible event automatically. CI success without continuation is not completion; it is evidence for the next selector invocation.
