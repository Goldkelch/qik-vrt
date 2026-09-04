# QIK-VRT Metatransistor Horizon refresh contract

## Observable failure being repaired

The deployed page could show current data after a manual browser refresh, but it did not update itself. A manually refreshed HTML document is not an event-driven monitor.

## Connection sequence

Exactly one snapshot is read when the browser connects:

```text
GET /api/state
-> bind stream_cursor
-> render latest exact projection
-> EventSource /api/gate-stream?cursor=<stream_cursor>
```

After that point, repository state is not fetched periodically. GitHub `workflow_run` events are serialized by the trusted repository workflow, transported with GitHub OIDC, appended to a Redis stream, and projected to the browser through Server-Sent Events. EventSource reconnect uses `Last-Event-ID`; the transport heartbeat is only connection liveness and never a repository-state observation.

```text
repository event
-> OBSERVE
-> CLASSIFY
-> D0 exact subject
-> ACTION
-> TRANSPORT EFFECT
-> READBACK
-> SUCCESSOR
-> SSE projection
```

`/api/gates` returns HTTP 410 and cannot be used as a polling fallback.

## Recursive Metatransistor projection

The inner Authority projects one master monitor and exactly eight immediate Mirror-Authority nodes. Each Mirror-Authority immediately defines eight child lanes of its own, producing the visible `8 × 8` ring. The same rule recurses by base-8 node path. Through logical depth nine the topology contains `153391689` nodes; the browser materializes only the bounded visible levels needed for inspection.

Each transition is canonical UTF-8 JSON with SHA-256 bindings. The complete payload is manifested into every child lane. Derealisation accepts exactly the eight expected slots and verifies each child state and payload digest before reconstructing the parent payload.

## Terminal input

`POST /api/terminal-event` accepts only bounded data or the signed fixed-point ALU model. It performs no arbitrary code execution and no repository write. The input is serialized into eight Mirror-Authorities, read back through an exact first-level derealisation receipt, appended to the same event stream, and shown without a page refresh.

The existing loopback Universal Terminal remains the separate Prepare → Commit → Readback adapter for explicitly authorized local effects.

## Depth-nine dead end

Eight exact gate-local `HOLD` states plus the carrier position produce computation depth nine. While an issue, pull request, or branch carrier remains, the aggregate state is not terminal `HOLD`; it is `CUT_CANDIDATE_REQUIRES_EXACT_RECEIPT`. Destructive retirement is permitted only after authoritative repository receipts, exact-current carrier readback, no active writer, no successor, and an unprotected non-default branch are all bound.

The monitor itself never closes a pull request, closes an issue, deletes a branch, merges, approves, deploys, publishes, or asserts `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
