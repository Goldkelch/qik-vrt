# QIK-VRT Metatransistor Horizon contract

## Purpose

Horizon is the event-driven outward reflection of QIK-VRT Mesh nodes. The
Authority node provides the master monitor. Every registered node serializes its
internal transition as an exact terminal frame; monitor-capable nodes expose the
frame, and full-terminal nodes additionally accept an explicitly submitted
Effect-Ack input through their own loopback Universal Terminal.

The implementation framework identifier is **KubiKAva**. The development model
is **Tested Event Model Driven Development**: event schemas, classifiers,
transport, readback, lossless frame reconstruction, depth handling, and claim
boundaries are executable tests rather than prose-only conventions.

## No polling

The browser performs exactly one `/api/state` snapshot read when it connects.
That atomic Redis snapshot includes the latest projection and the exact stream
cursor. The browser then opens one Server-Sent Events connection using that
cursor. New repository transitions arrive only from the Redis stream.

`EventSource` reconnect uses `Last-Event-ID`. Redis `XREAD BLOCK` waits for a new
append. The 15-second SSE comment is transport liveness only: it does not read,
classify, or infer repository state. `/api/gates` returns HTTP 410 and cannot be
used as a timer endpoint.

## Repository event path

Each of the eight bound workflows produces `requested`, `in_progress`, or
`completed` `workflow_run` events. The projector itself executes from trusted
`main`, never from candidate bytes:

```text
workflow_run event
-> OBSERVE exact event envelope
-> CLASSIFY gate state
-> D0 exact head SHA
-> serialize node/subject transition
-> ACTION: OIDC-authenticated Vercel ingress
-> transport receipt
-> READBACK receipt fields
-> SUCCESSOR: next event or Last-Event-ID reconnect
```

A successful workflow is rendered as `READY`, not as repository-wide `PASS`.
An adverse terminal workflow is rendered as gate-level `HOLD`; that gate display
does not by itself authorize a repository carrier mutation.

## Metatransistor and computation depth

The inner node is the Authority. Eight gate elements form the observable ring.
The ninth depth position is the carrier-disposition boundary.

The exact carrier is depth position one. Every gate classified `HOLD` adds one
observable depth tooth. A complete vector with all eight gates on `HOLD`
therefore reaches the owner-defined computation depth nine in one exact
projection. An active productive writer or an observed repository-native
successor resets the dead-end depth to zero.

At depth nine, the projection becomes `CUT_CANDIDATE`. It becomes
`CUT_ELIGIBLE` only when every gate is backed by an authoritative
repository-receipt fingerprint and the carrier readback proves an unchanged,
unprotected, non-default branch. The monitor never cuts automatically. The
executable cut order is:

```text
read exact subject/carrier
-> persist cut receipt
-> close exact PR as not planned when open
-> close only an exclusive issue carrier when open
-> delete only the unchanged unprotected non-default branch
-> read back absence of all selected carriers
```

Head drift requires a fresh exact-subject projection. An active writer or a
successor prevents dead-end classification and resets the depth.

## Node reflection and lossless Mirror manifestation

Every node event binds node identity, repository role, exact subject, sequence,
causal provenance, and frame hash. A serialized Metatransistor frame contains:

```text
node_id
sequence
previous_hash
payload
lossless=true
predecessor_evidence_transfer=false
frame_hash
```

Mirror manifestation must reproduce the exact payload and frame hash before it
can be treated as the same transition. Derealization is permitted only after an
exact readback. Transport acknowledgement is not effect acknowledgement.

## Full-terminal nodes

The page enables input only for registry entries advertising a full-terminal
capability. It accepts only a loopback endpoint (`127.0.0.1` or `localhost`) and
runs the existing two-phase flow:

```text
Prepare exact terminal input
-> receive short-lived single-use token and record hash
-> Commit the byte-equivalent payload
-> read /terminal/state
```

The Horizon wrapper extends the loopback CORS allowlist only to the canonical
GitHub, GitHub Pages, and Horizon origins. The adapter remains loopback-only and
records `external_effect=NONE`.

## Activation and effect boundary

The `workflow_run` projector becomes effective only when this workflow exists on
the repository default branch, and the Vercel runtime requires a configured
Redis-compatible `REDIS_URL`. Repository source presence is therefore separate
from Trusted-Main promotion, Vercel deployment, alias promotion, live event
receipt, and browser readback.

Nothing in this monitor or local terminal claims approval, merge, publication,
empirical confirmation, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.
