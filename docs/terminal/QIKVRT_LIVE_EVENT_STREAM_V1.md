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

## Completion boundary

A live stream is operational only after an independently running transport endpoint has been deployed and a client readback demonstrates that a repository event is received without a human/chat polling action. Merely committing this contract does not establish that endpoint.
