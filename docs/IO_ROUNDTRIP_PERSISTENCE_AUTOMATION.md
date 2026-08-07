<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# I/O round-trip persistence automation

## Status

This document specifies the review candidate that implements the Product Owner
requirement recorded in
`state/authorization/delegations/OWNER_IO_ROUNDTRIP_PERSISTENCE_AUTOMATION_V1.json`.

It does **not** claim merge, deployment, Zenodo publication, IETF submission,
`PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Contract

A conforming client treats every application-visible input, output, and relevant
tool artifact as one event in an auditable work unit:

```text
INPUT
→ CAPTURE
→ NORMALIZE
→ HASH/BIND
→ PROVENANCE
→ REPOSITORY PERSISTENCE
→ CLASSIFY
→ VERIFY
→ PUBLICATION DISPOSITION
→ PRE-EFFECT GATES
→ AUTHORIZED EXTERNAL EFFECT
→ RECEIPT
→ REOBSERVE
→ REPOSITORY PERSISTENCE
```

Repository truth begins only after the event has been materially written, bound
to exact bytes or to an explicitly bounded observable projection, checked, and
closed by a receipt. A chat statement, static `/AI` page read, URI, filename,
model output, or workflow label is not proof that this happened.

## Reused authorities

The implementation deliberately composes existing repository components.

| Concern | Existing authority |
|---|---|
| Append-only interaction chain | `tools/qikvrt_interaction_archive.py` |
| Opaque bytes, idempotency, EFFECT_ACK receipts | `src/qikvrt_api_handler.py` |
| Repository file integrity | `tools/qikvrt_integrity.py` |
| Runtime readiness | `tools/ai_runtime_bootloader.py` |
| Zenodo machine-proof gates | `tools/qikvrt_zenodo_machine_proof.py` |
| Exact-byte audio request path | `.github/workflows/qikvrt_audio_request.yml` |

`tools/qikvrt_io_roundtrip.py` is an orchestrator. It is not a second archive,
a second integrity authority, or a new publication engine.

## Metadata-only capture

The executable v1 controller accepts only `METADATA_ONLY`. For each event it
persists:

- event identity, role, time, purpose, provenance, and epistemic class;
- the byte count and SHA-256 of the application-visible content;
- the declared normalization and observation scope;
- a minimized semantic projection;
- external URIs with retrieval and evidence status;
- an append-only event hash linked to the preceding event.

It does not persist the raw transcript. This is data minimization, not a claim
that provider-internal transport frames or hidden model state were observed.
When exact transport bytes are unavailable, the request must say so and bind
the observable application projection instead.

A separately authorized encrypted transcript can use
`tools/qikvrt_interaction_archive.py append`; opaque binary payloads use
`src/qikvrt_api_handler.py ingest`. Neither route promotes payload semantics to
fact merely because the bytes were stored.

## Capture request

Requests live below `requests/io/` and conform to
`schemas/qikvrt_io_roundtrip_capture_request_v1.schema.json`.

```bash
python3 -B tools/qikvrt_io_roundtrip.py capture \
  --repository-root . \
  --request requests/io/<REQUEST_ID>.json \
  --confirm PERSIST_QIKVRT_IO_METADATA
```

The controller materializes:

```text
state/interaction_archive/io-roundtrip/events/<EVENT_ID>.json
state/io_roundtrip/dispositions/<REQUEST_ID>.json
evidence/receipts/io-roundtrip-<REQUEST_ID>.json
state/work_units/<WORK_UNIT_ID>.json
```

A repeated identical invocation is a verified no-op. A reused event or output
identity with different content blocks.

Verification is read-only:

```bash
python3 -B tools/qikvrt_io_roundtrip.py verify \
  --repository-root . \
  --request requests/io/<REQUEST_ID>.json
```

## Publication disposition

Every candidate claim is separately classified. The controller permits only
fail-closed states:

- `HOLD`
- `BLOCK`
- `NOT_APPLICABLE`
- `CANDIDATE_PENDING_PROOF`

For Zenodo, the exact candidate, rights, provenance, scientific status, machine
proof bundle, return receipt, single-use authorization, credentials, upload
receipt, public redownload, and repository reobservation remain mandatory.

For IETF, a concrete protocol or interoperability delta must first exist.
Musical, biographical, symbolic, or general contextual references are not
Internet-standardization subjects. Submission still requires exact draft
binding, rights/provenance review, separate authorization, and a reobserved
Datatracker receipt.

## Host integration boundary

The repository cannot observe an opaque chat host by itself. Fully automatic
end-to-end behavior therefore requires each conforming client or adapter to
invoke the controller before user return, commit the resulting files on an
authorized review branch, and reobserve integrity and exact-head CI.

Until such a hook is active for a particular host, that host boundary remains
`OPEN_EXTERNAL_INTEGRATION_BOUNDARY`. The repository must record that concrete
gap; it must not report that every I/O byte was automatically captured.

## Verification

Focused contract:

```bash
python3 -B -m unittest -v tests.test_qikvrt_io_roundtrip
python3 -B -m py_compile \
  tools/qikvrt_io_roundtrip.py \
  tests/test_qikvrt_io_roundtrip.py
```

Repository-native acceptance additionally requires regenerated integrity
authorities and terminal-green exact-head workflows. Local tests do not replace
those gates.
