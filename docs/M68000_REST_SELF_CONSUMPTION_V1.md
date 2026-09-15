<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# MC68000 REST self-consumption V1

The Mesh uses its existing authenticated REST adapter to execute its registered
Spark plan kernel and retrieve the resulting receipt. This is the first local
consumer of the constant machine execution interface. The ordinary Spark CLI
uses REST by default. The explicitly selected pure reference ring remains a
verification model. A failed REST call never falls back to a host decision.

## Reused implementation

| Layer | Existing component and V1 behavior |
|---|---|
| REST transport | `src/qikvrt_github_api_shim.py`: existing bearer expiry, repository scope, rate limit, strict JSON, bounded transport, TLS boundary |
| Machine program | Registered `lean_spark_branch_plan_v1`, 134 immutable MC68000 bytes; no submitted programs |
| Virtual execution | Existing Spark opcode interpreter executes BTST, BNE/BEQ, MOVEQ and RTS; 64-instruction budget |
| Local consumer | `tools/qikvrt_spark_branch_work_unit.py`: encode observation, POST, validate GET readback, decode returned plan |
| Persistence | Consumer output embeds the complete request and receipt; the existing circular Spark workflow preserves it as an artifact |

A new small runtime module is necessary to own the immutable program load and
receipt cache across HTTP requests. It does not duplicate the existing CPU
interpreter, transport, credential policy, high-level planning rule or workflow.
Only Python standard-library components and Git are added to the execution path;
there is no new package, emulator download or toolchain dependency.

## Constant interface

The additive API contract is in `api/qikvrt_github_api.openapi.yaml`.
Paths belong to the local adapter; GitHub itself does not implement them.

| Method | Path | Meaning |
|---|---|---|
| GET | `/qik-vrt/mesh/v1/m68000/kernels` | Loaded kernel and exact runtime binding |
| POST | `/qik-vrt/mesh/v1/m68000/executions` | Execute one normalized observation byte |
| GET | `/qik-vrt/mesh/v1/m68000/executions/{request_sha256}` | Read the retained exact-request receipt |

All three require the existing scoped, unexpired bearer credential. V1 loads
the kernel once at server startup. Request bindings include repository, HEAD,
tree, checkout cleanliness, source-file SHA-256 values and their aggregate
digest. Dirty source bytes are explicitly identified; they are never presented
as the committed tree. Source and HEAD are reobserved before and after execution
and before readback. A changed binding returns 409; restart and reobserve.

JSON hashes use UTF-8, sorted object keys, compact separators, no non-finite
numbers, and one final LF. `request_sha256` hashes the complete request;
`receipt_sha256` hashes the receipt without that one digest field. The client
checks both, exact request equality, output domain, execution boundary and
canonical equality of POST and GET. It never follows a redirect or polls.

The service retains at most 256 receipts by default, evicting the oldest entry.
Identical retained requests return the same receipt without reexecution.
Readback after eviction or process restart returns 404. The consumer must save
its verified embedded receipt when durable evidence is required. A retained
receipt does not establish a new execution time or fresh GitHub observation.

## Start and consume locally

Use the existing credential setup for the adapter: `QIKVRT_API_TOKEN` in its
canonical `b64url:` representation, a future `QIKVRT_API_TOKEN_EXPIRES_UTC`,
`QIKVRT_API_PRINCIPAL`, and `QIKVRT_ALLOWED_REPOSITORY=Goldkelch/qik-vrt`.
Keep credential material out of files, shell history, receipts and logs.

From the checkout root, with these variables already configured:

```sh
QIKVRT_M68000_ENABLED=1 python3 -B src/qikvrt_github_api_shim.py
```

In a second process with the same credential and repository scope:

```sh
python3 -B tools/qikvrt_spark_branch_work_unit.py \
  --observation /path/outside-checkout/observation.json --json \
  > /path/outside-checkout/verified-plan.json
```

The default origin is `http://127.0.0.1:8766`. For an already authorized remote
adapter, set `--m68000-api-url` or `QIKVRT_M68000_API_URL`; non-loopback requires
HTTPS. The remote runtime must match the client's expected source binding.
The existing server opt-in and TLS certificate requirements remain applicable.
Do not expose the service through the Cloud Transputer deployment implicitly.

The observation object contains exactly eight booleans:
`malformed_or_scope_invalid`, `main_effect_observed`, `base_current`,
`integrity_current`, `gates_terminal`, `gates_non_adverse`, `mergeable`,
`authority_available`. These are caller observations, not newly verified
GitHub facts. The kernel selects a bounded plan; the authorized host adapter
must freshly establish the preconditions before any proposed effect.

## Hardware depth and evidence boundary

This increment executes genuine registered MC68000 machine bytes through a
bounded instruction interpreter. It does not emulate a complete MC68000 machine,
its bus, MMU, supervisor state, interrupts or peripherals. REST framing,
authentication and receipt handling run on the host. It does not establish
native physical execution or a speedup.

The Spark plan ABI returns code 0..11 in D0. It is distinct from the Cloud
Transputer's four operational states in D0 and five effect states in D4.
A returned merge plan does not execute a merge. HTTP 200, a green workflow,
native review approval and EFFECT_ACK_DONE remain separate evidence states.
Every execution receipt here is `EFFECT_ACK_CONTINUE`, with
`ordinary_release=false`, `host_effects_executed=false` and no native approval
or DONE claim. No evidence from PR #1081 or a predecessor head is inherited.

Subsequent implementation should reuse the Cloud Transputer's existing C90
wire encoding and reverse receipt, Smalltalk event handling and QEMU integration.
Each newly exposed kernel needs its own register domain, bounded execution,
return mapping and actual Mesh consumer. Full machine execution and remote
effects need their own verified backend and effect readback. Preserve V1's
request meaning; incompatible register or backend contracts require a new
version, not reinterpretation of an existing kernel ID.

Performance must be measured over equivalent work. Loading immutable bytes once
and exact-request reuse remove repeated kernel setup, while REST, source
reobservation and hashing add costs. No end-to-end speedup follows automatically.

## Verification

`tests.test_qikvrt_m68000_rest` executes all 256 flag bytes over real authenticated
HTTP with GET readback against the independent reference oracle. Negative
controls cover stale head/tree/runtime/kernel bindings, wrong repository,
missing authentication, duplicate JSON fields, register coercion, unauthorized
program fields, receipt tampering, bounded retention, replay and instruction
loops. Existing handler security and API-client tests remain required.
