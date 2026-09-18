# TEMDD persistent native-event producer v1

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

## Bounded obligation

PR #1103 gains a durable producer and replay transport for `/api/temdd/events`.
This is not T15/T16, language closure, a GitHub review, deployment acceptance,
Main integration, or QIKVRT_DOD. Persistence never implies any of those claims.
The existing Effect-Ack backend remains unchanged and is composed, not replaced.

The finite kernel is `Runtime.append` -> exact checkout check -> `Ledger.append`
-> validation -> SQLite transaction COMMIT -> exact durable readback -> event
notification. No repository polling, scheduler, retry job, model call, review or
promotion exists in this kernel. HTTP/SSE and Unix socket listeners are outer
I/O adapters; socket readiness, not a timed GitHub query, wakes observers.
Timeouts bound transport writes and subprocess I/O, not repository transitions.
The pre-existing container process supervisor remains an outer-layer concern.

## Reuse decision

The unchanged `qikvrt_effect_ack_http_terminal.Handler`, existing TEMDD workflow,
`make test`, and repository integrity generator are reused. The existing
`tools/qikvrt_real_mesh.py` has versioned node-hop/terminal receipt schemas for
bounded multi-pair message delivery, not this browser cursor contract. This
store is a separate exact-subject observation projection with durable native-ID
transactions; it does not replace that mesh ledger or relabel its receipts as
TEMDD proof. Upstream native callbacks retain their own authentication boundary.

## Run and connect a native producer

Requirements: Linux/Unix, Python 3.10+, Git, a clean committed checkout, and a
persistent owner-controlled state directory. Node.js is also required for the
browser regression test, not for the producer runtime.

```sh
python3 -B src/qikvrt_temdd_event_ledger.py serve \
  --root "$PWD" --host 127.0.0.1 --port 8771 \
  --state-dir /var/lib/qikvrt/state --repository Goldkelch/qik-vrt --pr 1103
```

The container entrypoint invokes this service. `/AI` serves the observer and
`/api/temdd/subject` reads the exact deployed checkout and ledger epoch. Startup
appends one actual local `transputer` OBSERVE event after both listeners bind;
its payload records the process and bound HTTP address. This proves neither a
running Firefox nor a current remote PR state.

An already authenticated repository/transputer callback submits its native
observation synchronously, with no polling and no browser write capability:

```sh
python3 -B src/qikvrt_temdd_event_ledger.py append \
  --state-dir /var/lib/qikvrt/state < native-event.json
```

`native-event.json` must have exactly these fields (head/tree are placeholders;
replace them with the actual native observation, never copy old evidence):

```json
{
  "schema": "qikvrt_temdd_native_event_v1",
  "kind": "READBACK",
  "subject": {
    "repository": "Goldkelch/qik-vrt",
    "pr": 1103,
    "head": "<exact observed 40-hex commit>",
    "tree": "<exact observed 40-hex tree>"
  },
  "provenance": {
    "source": "repository",
    "native_event_id": "<stable ID of this native delivery>"
  },
  "observed_at": "<actual UTC observation timestamp ending in Z>",
  "message": "<native observation summary>",
  "payload": {"receipt": "<native observation receipt>"}
}
```

Kinds: OBSERVE, CLASSIFY, ACTION, EFFECT, READBACK, SUCCESSOR, HOLD. Producer
sources: repository or transputer. One append accepts at most 65,536 canonical
UTF-8 bytes. Identical redelivery returns the same persisted record; reusing a
native ID with different content or subject fails closed. Payload SHA-256 and
whole-ledger-record SHA-256 are recomputed, not supplied by the caller.

Success is `PERSISTED` with the committed record, `authority_effect:false` and
`dod:false`. Errors return HOLD/nonzero. This is a ledger persistence receipt,
not proof that an arbitrary assertion inside a payload is true.

## Trust boundary and persistence

Ingress is `<state-dir>/temdd/ingress.sock`, mode 0600, inside a 0700 directory.
One process exclusively owns the store; a second owner fails closed. Browser
POST requests to `/api/temdd/*` are rejected. TEMDD HTTP reads require loopback
Host and same Origin. The local operating-system owner is trusted to authenticate
its upstream callback. Source labels and hashes are NOT webhook authentication,
digital signatures, or protection against a malicious state-directory owner.
This change does not install a GitHub webhook subscription or remote relay.

`events.sqlite3` uses WAL plus synchronous FULL and durable COMMIT before any
notification. Sequence IDs are persistent `ledger-epoch:sequence`; restart does
not reset them. A new/erased ledger has a different epoch. Filesystem/device
power-loss durability still depends on the deployment storage honoring sync.
The state directory must be mounted persistently for container replacement.

## Replay, subject mutation and fail-closed observer

`Last-Event-ID` takes precedence over the original `?after=` URL on native SSE
reconnect. Unknown, foreign-epoch, wrong-subject and future cursors are rejected,
never silently reset. Empty cursor means replay this subject from its beginning.
Replay is ordered and batched; the readback/subscribe race is closed. Observer
slots are bounded and released on disconnect even with no new native event.
No heartbeat fabricates repository events. Client disconnect does not stop or
modify repository execution.

Subject = repository + PR + exact commit + exact tree. Every ingress/readback
checks the deployed checkout; tracked mutation stops the producer fail-closed
until explicit restart. Old rows are retained for history but cannot replay into
a different subject. Browser cursor keys also include subject and ledger epoch.
The browser rejects a mismatched subject, malformed/non-monotonic event and any
`dod:true`. Transport errors show HOLD while leaving native SSE reconnection
available. A subject handshake is control data, not persisted repository proof.

A deployed checkout is not a fresh observation of the remote PR head. This
producer makes no freshness assertion about GitHub absent a native authenticated
upstream observation. No old test result, review or ledger row becomes evidence
for a successor merely because the implementation or content is similar.

## Validation and canonical integrity

`make temdd-event-ledger-test` runs fresh Git fixtures, real Unix ingress and
HTTP/SSE sockets, restart/replay, concurrent append, storage/crash-point failure,
wrong-subject/cursor rejection, JavaScript consumer and legacy Effect-Ack tests.
It is admitted into `make test`. The TEMDD workflow checks out the literal PR
head, runs this suite and existing language checks, and records head/tree.
A focused suite PASS is not full P2 or language conformance closure.

The workflow also uses the repository's own integrity generator to export a
strict three-file candidate (`REPOSITORY_FILE_MANIFEST.json`, its `.sha256`,
`SHA256SUMS.txt`) with parent head/tree, allowlist and hashes. It never adopts or
pushes that worktree. A later consumer must reobserve the branch, require the
identical parent, verify the allowlist/hashes, adopt non-force, and then rerun
all applicable validation on that new head/tree. Worktree verification is not
committed-integrity verification; every adoption resets P2+.

Runtime/Firefox deployment, upstream repository relay authentication, full P2,
T15/T16 and the remaining language obligations require their own fresh evidence.
