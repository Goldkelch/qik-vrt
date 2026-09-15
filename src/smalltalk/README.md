# QIK-VRT Smalltalk core

`QikvrtEffectAck.st` is an independently executable Pharo Smalltalk implementation
of the C90 verified-snapshot kernel. Python remains the rich evidence/protocol
adapter; C90 remains the dependency-minimal kernel. Existing Python functionality
and tests are retained.

The 19 Boolean fields and five decisions share the existing C90 test-mask order.
All 2,621,440 combinations are compared byte-for-byte with the compiled C90
kernel, whose existing suite independently checks 7,864,387 assertions. The
Smalltalk test also rejects malformed snapshots and restores a freshly built
image before testing. These counts refer to the stated domains, not to millions
of independent end-to-end boot tests.

Another 23 representable boundary cases compare the rich Python engine with
the C90/Smalltalk results. Projection into the verified snapshot preserves
Python's reception rule: without a transport acknowledgement, a raw identifier
string is not an available effect-checkable input identity. This is a scoped
adapter check, not a claim that every Python protocol feature was ported.

```
python3 -B tools/qikvrt_smalltalk.py install
make smalltalk-test
python3 -B tools/qikvrt_smalltalk.py build --output /tmp/qikvrt-smalltalk-image
```

Source is stored in Git as standard Smalltalk file-in text. The generated image
is a derivative, not an editable source of authority. Each build begins with the
locked upstream image and records the exact source, image and lock hashes. The
Linux x86_64 VM and image archives are bound in `pharo-13.lock.json`; a changed
upstream URL response fails closed. Rollback deletes only an incomplete new
installation and never replaces a verified cache. A successful restore does not
approve, publish, deploy or complete the broader project.

The C enum and the Transputer D4 encoding are deliberately different:

| State | C90 enum | D4 wire |
| --- | ---: | ---: |
| EFFECT_NACK | 0 | 0 |
| EFFECT_ACK_CONTINUE | 1 | 1 |
| EFFECT_ACK_DONE | 2 | 4 |
| EFFECT_ACK_ISOLATE | 3 | 2 |
| EFFECT_ACK_BLOCK | 4 | 3 |

Use `wireCodeFor:` at the transport boundary; never send a C enum as D4 directly.

Upstream: [Pharo download](https://pharo.org/download),
[Pharo source](https://github.com/pharo-project/pharo),
[VM source](https://github.com/pharo-project/pharo-vm).
The upstream licenses are retained under `runtime/toolchains/pharo-*-LICENSE.txt`.

## Event-driven continuation

`QikvrtEventReactor.st` adds a persistent, source-built Smalltalk event handler.
The existing Python launcher transports bounded JSONL records over blocking
pipes; Smalltalk owns predecessor scheduling and runs the existing snapshot
kernel when a snapshot is provided. Linux inotify wakes the incremental file
reader on append. Neither idle path issues status requests or uses a polling
timer. The SSE projection uses the same notification reader and supports exact
`Last-Event-ID` replay; an unknown cursor returns HTTP 409.

Start an explicitly bound local consumer:

```sh
python3 -B tools/qikvrt_smalltalk.py events \
  --binding /absolute/path/binding.json \
  --events /absolute/path/events.jsonl \
  --ledger /absolute/path/continuations.jsonl
```

The binding JSON contains `repository` and `subject`. The subject must include
`kind`, exact 40-character `head_sha`, `tree_sha`, and `base_sha`; a
`pull_request` subject also requires its positive integer `pull_request` number.
Every event must carry that identical subject and repository. Obtain these
identities from authoritative Git observations; do not fill missing identities
from a predecessor or assume that a current branch name identifies old events.
Existing live-status events without this complete binding remain observational
and cannot enter this consumer without separately verified source enrichment.
The input is a trusted local append-only producer channel, not a public webhook.

Input records use `qikvrt_live_event_v1`. An event with absent predecessors waits
until those explicit event IDs arrive. Duplicate identical records do not rerun
completed work; changed content under an existing ID, cycles and subject drift
fail closed. D0 selects NOOP, HOLD, REOBSERVE or REQUEST_AUTHORITY. These are
local continuation proposals. A delivered predecessor does not satisfy its
P0–P7 gate. Snapshot results likewise cannot establish external completion.

The existing fsynced, hash-linked Mesh ledger stores ACCEPTED inputs and
COMPLETED local outputs. Restart reconstructs Smalltalk from that history,
including pending work and a crash between accepted input and completed output.
The ledger is bound to repository subject, source hashes and locked runtime;
a changed runtime requires an explicit new ledger or reviewed migration.
A file lease excludes concurrent CLI writers. Persistence failure requires
restart. Stdout is a projection: downstream consumers must deduplicate by event
ID and recover from the durable outbox if a crash occurs after persistence but
before stdout delivery. External exactly-once execution is not claimed.

Bounds: 64 KiB per input record, 10,000 records per journal, at most 64 explicit
predecessors per event. Rollover is explicit. Source replacement, truncation,
notification loss, malformed JSON and conflicting IDs stop processing. The
reader does not authenticate another process with write access or detect every
in-place alteration of an already consumed source prefix. Linux notifications
are required; there is no polling fallback. SSE has no timed keepalive; idle
client/proxy lifetime must be managed by its hosting layer.

`make smalltalk-test` runs real Pharo continuation, restart and failure tests in
addition to the exhaustive kernel comparison. `make test` includes notification
and SSE tests without requiring a Pharo installation. The integrated test
appends out-of-order events and verifies notification → Pharo → durable outbox.
This first integration does not activate trusted Main, execute GitHub actions,
submit reviews, deliver QR payloads or emit general `EFFECT_ACK_DONE`.
