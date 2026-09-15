# QIKVRT Self-Contained GitHub Repository with REST/TCP-IP API V1

Created: 2026-06-26 05:43:26 CEST

This repository is a self-contained QIK-VRT repository root. It includes:

```text
GitHub-compatible REST/TCP-IP API shim
GitHub Actions workflow_dispatch / repository_dispatch workflow
OpenAPI contract
Handler implementation
Client implementation
Unit and TCP/IP E2E tests
CI workflow
Metagrammar test inventory
Audit and uploadability gates
```

## Owner decision: synchronous REST and compiled relations

On 2026-09-15, Product Owner Ingolf Lohmann directed that every Repository Node
provide a fixed, freely available REST interface connecting proved relations
to Motorola 68000 assembly execution. Cognitively variable processing remains
in the other implementation languages. The human-facing work cycle is
**input, processing, output**, with useful results at a measured, acceptable
response time. This is an architectural requirement; node availability and
performance require their own implementation evidence.

### Stable interface on every Node

Every participating Repository Node MUST expose the same versioned REST
contract for its supported registered kernels. The specification, discovery
and interoperability contract MUST be publicly documented and freely available.
Existing authentication, repository scope and effect authorization remain part
of the interface. Architecture availability does not relicense implementation
code; explicit repository and component license texts still govern reuse.

The existing [OpenAPI contract](../api/qikvrt_github_api.openapi.yaml) is the
single transport authority. Its MC68000 V1 paths and schemas are documented in
[MC68000 REST self-consumption](M68000_REST_SELF_CONSUMPTION_V1.md). Preserve
their meaning across Nodes. Incompatible register domains, result meanings or
execution contracts require a new version. Reuse the existing adapter,
registered kernels, clients and Node onboarding path when extending coverage.

A bounded evaluation MUST return its computed result and exact request binding
in the same request/response cycle. Receipt readback belongs to the client's
completed processing cycle. A dispatch acknowledgement, queued job or recurring
watch does not complete the requested computation. On missing evidence,
unavailable execution or exhausted bounds, return the precise failure or open
gate within the declared response budget. Continue safe, already authorized
work without requiring repeated human prompts; stop at an actual authority or
external-effect boundary and preserve the exact unfinished obligation.

### Division of execution

| Responsibility | Execution contract |
|---|---|
| Proved, stable executable relation | Compile its verified finite projection to registered MC68000 bytes; load once and reuse within the proved input domain. |
| Portable runtime and machine connection | Reuse the strict C90 core and the Cloud Transputer's existing machine and wire adapters. |
| Cognitively variable processing | Use Python, Smalltalk and the other appropriate languages for modeling, interpretation and orchestration through the same interface. |
| REST and receipts | Preserve version, kernel identity, input/output domains, source binding, authentication and result readback across language boundaries. |

The [compiled-kernel registry](../runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json)
binds reusable programs. Each kernel needs its formal source, assumptions,
executable projection, compiler identity, machine-byte digest and ABI. Reusing
a proved kernel avoids reinterpreting its higher-level rule on every call;
current input/evidence binding must still be checked. Changed proof, projection,
compiler, ABI or bytes invalidate dependent validation and require a new exact
binding. A model's formal consequences do not establish physical correspondence
outside its evidence scope.

Keep the Spark plan ABI, the Cloud Transputer D0 boundary ABI and its D4 effect
ABI distinct. A returned plan is a computation result; an effect described by
that plan needs its own authorized execution and post-effect observation.

### Per-Node acceptance and remaining work

Each Node MUST record its exact repository commit/tree, endpoint and contract
version, supported kernel and machine-byte identities, actual backend, and
request-to-result/readback conformance. Node enrollment or a predecessor's
receipt alone does not establish acceptance. Extend the existing known-Node
acceptance path; no foreign repository write is implied by this decision.

Speed is an acceptance property of the complete input-to-output path. Record
cold/warm end-to-end latency (including p50/p95/p99), throughput, input size,
concurrency, measurement method and target hardware/emulator identity, with
equivalent work and unchanged correctness gates. Record numerical latency and
throughput budgets for the applicable Node/use case before accepting it; no
such universal budget is fixed by this decision. Separate kernel execution
time from HTTP, source verification, hashing and receipt costs. Report actual
native or emulated execution and measured results without inferring a physical
speedup from instruction count or an interpreter result.

At this decision's input revision `2ceefffddded6a2c8173dea69550e75fffc1cd01`,
the REST increment supports one registered Spark kernel through a bounded
opcode interpreter. The continuous REST-to-C90/MC68000 backend connection,
additional kernel coverage, per-Node adoption and performance acceptance remain
open. The existing implementation carriers are
[REST #1091](https://github.com/Goldkelch/qik-vrt/pull/1091) and
[Cloud Transputer #1079](https://github.com/Goldkelch/qik-vrt/pull/1079);
each retains its own exact-subject evidence.

Decision and contribution provenance:
[work unit](../state/work_units/QIKVRT_SYNCHRONOUS_NODE_REST_ARCHITECTURE_V1.json).

## Local TCP/IP API

```bash
make run-api
```

Health:

```bash
curl http://127.0.0.1:8766/health
```

## Tests

```bash
make test
```

## GitHub REST API enablement

After upload to GitHub, the repository can be triggered through GitHub REST:

```text
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/dispatches
```

## Boundaries

```text
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
LIVE_GITHUB_ACTIONS_RUN = SUCCESS (run 29764193906)
GITHUB_PAGES_BUILD_AND_DEPLOY = SUCCESS (run 29764192834)
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_THIRD_PARTY_REPRODUCTION = OPEN
```

These hosted results establish the named GitHub effects only. They do not
establish non-bypassability in every integration, production hardening,
external adoption, or empirical validation of claims outside the executable
software boundary.
