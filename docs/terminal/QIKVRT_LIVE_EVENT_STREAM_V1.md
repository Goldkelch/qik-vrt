# QIK-VRT Live Event Stream V1

## Goal

Expose repository-native QIK-VRT receipts as a persistent append-only event stream suitable for `tail -f`, Server-Sent Events (SSE), WebSocket relays, or other event-bus consumers.

This transport is observational. It does not create scientific truth, transfer predecessor evidence, merge, publish, or assert EFFECT_ACK_DONE.

## Canonical event envelope

Each emitted line/event MUST bind its exact subject:

```json
{
  "schema": "qikvrt_live_event_v1",
  "event_id": "<stable id>",
  "observed_at": "<RFC3339 UTC>",
  "repository": "Goldkelch/qik-vrt",
  "subject": {
    "kind": "pull_request|trusted_main|external_delivery",
    "pull_request": 966,
    "head_sha": "<exact sha>",
    "base_sha": "<exact sha or null>"
  },
  "phase": "P0|P1|P2|P3|P4|P5|P6|P7|EXTERNAL",
  "verb": "OBSERVE|CLASSIFY|D0|ACTION|EFFECT|READBACK|SUCCESSOR|HOLD|EXTERNAL",
  "causal_state": "NOOP|HOLD|REOBSERVE|REQUEST_AUTHORITY|EFFECT",
  "d0": 0,
  "source": {"type":"workflow_run|status|review|commit|external_readback","id":"..."},
  "predecessor_event_ids": [],
  "productive_effect": false,
  "effect_ack": "NOT_REQUIRED|PENDING|DONE",
  "payload": {}
}
```

## Ordering

Events are append-only. Consumers MUST NOT infer causal order from timestamps alone. `predecessor_event_ids`, exact subject binding, and `policy/QIKVRT_EXECUTION_PRECEDENCE_V1.json` define causality. Unknown relation is `HOLD_UNVERIFIED`.

## Repository producer

Trusted workflows emit one JSON line per normalized transition to `state/live/QIKVRT_LIVE_EVENTS.jsonl` or to an external event sink. The repository remains authoritative for event construction.

## Transport adapters

A consumer MAY expose the same normalized events through:

- `tail -f state/live/QIKVRT_LIVE_EVENTS.jsonl` for a checked-out repository;
- SSE using `Content-Type: text/event-stream`, one event envelope per `data:` frame;
- WebSocket frames containing exactly one event envelope;
- an append-only message bus/topic.

Transport ACK is not effect ACK.

## SSE mapping

```text
id: <event_id>
event: qikvrt
data: <single-line JSON envelope>

```

The SSE relay MUST support resume using `Last-Event-ID` and MUST NOT manufacture events that are absent from repository-native receipts.

## Event-only observatory adapter

`docs/mesh-observatory/index.html` consumes the existing relay at same-origin
`/events`. Serve the HTML through the existing HTTP surface and proxy this path
to `tools/qikvrt_live_sse.py`; a GitHub blob view is not a running endpoint.
No browser credentials, arbitrary query-supplied event endpoint, new broker,
GitHub schedule, or new receipt producer is introduced.

The Linux relay registers an inotify watch on the journal's parent directory
**before** its initial read. Thereafter only file notifications permit a journal
scan; atomic replacement is included. A transport keepalive timeout writes only
an SSE comment, never a file scan or a GitHub request. Unsupported notification
backends and invalidated/overflowed watches fail closed; the former
`--poll-seconds` option is removed rather than retained as a hidden fallback.
The journal parent must already exist. Deployment must provision permissions,
watch/connection limits, and the existing trusted producer-to-journal delivery.
The relay does not pull repository changes itself.

Two named control frames extend the transport, **not** the native event schema:

```text
event: qikvrt-ready
data: {"schema":"qikvrt_stream_boundary_v1","last_event_id":"<id or null>"}

event: qikvrt-gap
data: {"reason":"CURSOR_NOT_FOUND","effect_ack":"PENDING"}
```

`qikvrt-ready` is sent once after initial replay and after a notification batch,
not on idle heartbeats. Its cursor is a transport position, not proof of causal
completeness or a new repository receipt. An absent resume cursor, malformed
complete JSONL record, conflicting event ID, or notification gap stops replay.
An unfinished final line is withheld until completed. The client closes on a
gap; it never silently treats lost history as a continuous causal chain.

The existing materializer also emits `subject.kind=repository` for non-Main
subjects. These receipts are admitted only as repository-scoped invalidation
hints; they do not become PR-bound evidence. PR hints are filtered to the
observatory's existing subjects; other repositories are ignored. Matching
IDs deduplicate replay; conflicting IDs and exhausted bounded dedupe storage
hold rather than discard safety information.

After bootstrap/reconnect replay, a relevant event batch, or an explicit user
readback, the consumer performs one coalesced readback batch. It reads Main and
PR pointers, resolves their literal commit/tree objects, then rereads pointers.
Head/base drift, invalid bindings, failed reads, deadlines, disconnects, and
superseding events reject the in-flight result. This is a bounded observation
window, not a transaction across GitHub endpoints and not P2-P7 evidence.
Readback errors do not schedule retries. A later native event or explicit user
action may request another readback; transport reconnection itself does not
query GitHub until replay reaches its boundary.

The 60-second timer now **expires only local readback freshness**. It never
fetches GitHub, renews evidence, reconnects, or promotes a predicate. Old values
remain visibly STALE/HISTORICAL. `EFFECT_ACK_DONE = OPEN` is never modified by
this adapter, including when a transported payload says `effect_ack=DONE`.
Head/tree/base mutation emits an explicit P2+ reset/no-transfer notice.

## Repair validation and exact-head admission

Focused regressions, in addition to the repository's existing required gates:

```sh
node --test tests/test_mesh_observatory.cjs
python3 -B tests/test_qikvrt_live_sse.py -v
make test
```

Use the repository's admitted toolchain/cache profile (including Node 24.x and
Python 3.12.13) for P2. The standalone regressions use only standard libraries;
the relay/notification tests require Linux. The two focused suites must be run
explicitly; an existing `make test` success alone does not cover these new tests.
Regenerate and verify the canonical integrity trio before freezing the final
candidate. Any resulting mutation resets P2+ again. Local auxiliary tests under
other interpreter versions do not establish repository-native P2 success.
Neither predecessor validation nor predecessor native approval transfers to the
changed head/tree. Obtain validation, native review, and post-review reobservation
on the final exact subject; keep ruleset enforcement and promotion separate.

## Completion boundary

A live stream is operational only after an independently running transport endpoint has been deployed and a client readback demonstrates that a repository event is received without a human/chat polling action. Merely committing this contract does not establish that endpoint.

The deployment receipt must additionally bind the served HTML and relay bytes,
producer event ID, exact repository subject and browser readback; demonstrate
idle/no-GitHub-read behavior, disconnect/expiry HOLD, and resume or explicit gap
handling. A synthetic local SSE test is not that production receipt.
