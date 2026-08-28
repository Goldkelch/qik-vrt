<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT deterministic terminal, Mesh and hardware — technical disclosure dossier V1

**Inventor attribution:** Ingolf Lohmann  
**Status:** technical disclosure for counsel review. It is not a patent
application, a novelty opinion, a freedom-to-operate opinion, a legal opinion,
or a statement that a patent will be granted.

This dossier binds a bounded technical embodiment currently materialized in
this repository. It is deliberately narrower than any claim that a digital
system eliminates uncertainty in the physical world, proves a general
performance factor, or replaces a general-purpose cognitive model.

## 1. Technical problem

A distributed terminal has to make the same finite input mean the same thing
at every participant, while avoiding silent retry, duplicate effect execution,
topology drift and ambiguous admission. Common failure modes are:

- a transport retry is mistaken for a new request after a process restart;
- an HTTP request contains duplicate or differently interpreted binding
  headers;
- two endpoints hash different serializations of the same apparent JSON;
- a fan-out reads a changing registry while it is dispatching; or
- a partial, reordered or non-binary hardware frame is treated as complete.

The disclosed solution makes the finite decision path explicit and
fail-closed. It does **not** make an assertion about the reliability of an
unobserved sensor, ADC/DAC conversion, physical interconnect, external service
or human input. Those conditions are represented by explicit `CONTINUE`,
`HOLD`, or `BLOCK` outcomes instead of an implicit accepting branch.

## 2. Bounded technical embodiment

The disclosed embodiment has four coupled, independently testable parts.

| ID | Component | Deterministic mechanism | Exact reference embodiment | Evidence boundary |
| --- | --- | --- | --- | --- |
| T1 | Event-driven terminal peer | One explicit HTTP `POST` Prepare or Commit edge; no cron, periodic scan or blind retry in the terminal control path | `src/qikvrt_effect_ack_http_terminal.py`, `policy/QIKVRT_HTTP_TERMINAL_PEER_V2.json` | Loopback reference only; remote/public deployment is open. |
| T2 | Durable idempotent receipt | A single private node directory holds a hash-linked `RECORD → PREPARED → COMMITTED` ledger. The same idempotency key and exact fingerprint replays the original receipt; a changed fingerprint is blocked. | `src/qikvrt_effect_ack_http_terminal.py`, `tests/test_qikvrt_effect_ack_http_terminal.py` | HTTP requests are sessionless; the ledger is deliberately retained state for crash recovery and replay prevention. |
| T3 | Frozen quadratic Mesh epoch | The Authority freezes a canonical, bounded active-node projection before dispatch. It orders nodes by `(repository, guid)`, emits `N*N` row-major lane identifiers, hashes the epoch, then reobserves it before the finite fan-out. | `.github/workflows/qikvrt_authority_review_report_fanout.yml`, `docs/architecture/QIKVRT_AUTHORITY_REVIEW_REPORT_FANOUT_EPOCH_V1.md` | Repository-dispatch acceptance is not target delivery, an effect acknowledgement, merge, or external effect. |
| T4 | Hardware codec and gate | A finite VHDL serializer/deserializer uses row-major lanes and LSB-first bits; a four-outcome gate is total and fail-closed. | `hardware/vhdl/qikvrt_mesh_quadratic_codec.vhd`, `hardware/vhdl/qikvrt_deterministic_admission_gate.vhd` | RTL source and self-checking testbenches exist; locked synthesis, timing, bitstream and board observation remain open. |

### 2.1 Sessionless HTTP and explicit retained state

The terminal peer is **state-independent at the HTTP request/session layer**:
each V2 request contains all routing and binding fields needed for its local
decision. It is not a claim that the complete endpoint has no state. Exact
restart replay and duplicate-effect prevention require the explicit node-local
ledger in T2. This is a technical distinction, not a rhetorical one:

```text
stateless HTTP request != stateless daemon != stateless external system
```

The V2 peer accepts a closed `qikvrt_terminal_input_v2` domain and serializes
it with `QIKVRT_CLOSED_JSON_V2`: UTF-8, Unicode-scalar key ordering, fixed
control-character escaping, compact separators, no floating point, bounded
safe integers, and typed media only. It rejects duplicate binding/framing
headers, malformed state paths, competing state-directory owners, noncanonical
Base64, unterminated ledger entries and conflicting idempotency reuse.

`browser/firefox/qikvrt-terminal/` is a non-polling **V1** Firefox reference
client. A V2 Firefox peer on every terminal, TLS/mTLS authentication,
remote/public deployment and external-effect execution are not demonstrated by
this dossier.

### 2.2 Frozen finite Mesh epoch and `N*N` topology

For a frozen active-node set of cardinality `N`, the Authority materializes
one canonical epoch before any delivery attempt:

```text
ordered_nodes = sort(active_nodes, key=(repository, guid))
lane(r, c)    = qikvrt-mesh-lane-v1/<r>/<c>/<source-guid>/<target-guid>
lane_index    = r*N + c
lane_count    = N*N
```

The `epoch_sha256` binds the exact Authority main head/tree, Registry blob,
quadratic-codec policy bytes, ordered active-node projection, finite cardinality
and every row-major lane ID. A pre-dispatch reobservation checks those bytes
again. Registry or Authority drift, an invalid epoch, a duplicate identity or a
cardinality outside the reviewed finite bound yields `HOLD_UNVERIFIED` before a
dispatch.

Per-target delivery idempotency is the SHA-256 of canonical JSON binding the
epoch digest, exact source head, target repository/GUID/index/self-lane and
event type. It therefore distinguishes a different topology, source revision
or target without using a randomized identifier as a decision rule.

### 2.3 Canonical finite wire frame

For `WORD_BITS` bits per lane, the serializer maps a payload bit as:

```text
wire_bit_index = (row*N + column)*WORD_BITS + bit
wire_order     = row-major lanes, then least-significant bit first
payload_bits   = N*N*WORD_BITS
```

The protected reference frame is, in LSB-first order:

```text
SYNC_8 | SEQUENCE_16 | PAYLOAD_(N*N*WORD_BITS) | CRC16_CCITT_16
```

The receiver releases a payload only when every received frame bit is binary,
the sync and expected sequence match exactly, and the locally recomputed
CRC-16/CCITT equals the received tag. A short frame is `CONTINUE`; bad sync,
sequence, insertion/reorder or tag becomes `HOLD`; automatic resynchronization
is disabled. CRC-16 is an error-detection tag in this embodiment, not a claim
of cryptographic authenticity or physical fault-free transport.

### 2.4 Deterministic admission

The VHDL admission gate has this total precedence table:

| Condition, in order | Output encoding | Meaning |
| --- | --- | --- |
| `frame_complete_i != '1'` | `00` | `CONTINUE` |
| otherwise, `ambiguity_present_i != '0'` | `01` | `HOLD` |
| otherwise, `canonical_equal_i == '1'` | `10` | `ACCEPT` |
| otherwise | `11` | `BLOCK` |

Any non-binary `std_logic` value is handled by one of the non-accepting
branches. Sampling, random selection and implicit ambiguity resolution are
absent from this bounded decision path. This is a property of the specified
logic and its inputs; it is not a proof that a physical interface cannot
experience metastability or noise.

## 3. Candidate claim groups for patent counsel

These are technical claim-development inputs, not proposed legal claims and
not an assertion of novelty or inventive step. Counsel must decide whether the
groups should be combined, separated, narrowed, or omitted after a documented
search and jurisdiction-specific review.

1. **Terminal-peer apparatus.** A pair of HTTP peer daemons that bind a
   closed canonical terminal envelope and duplicate-sensitive headers to a
   single idempotency key, then retain a private, hash-linked lifecycle ledger
   so an exact restart retry returns the prior local receipt while a different
   fingerprint under the same key is rejected.
2. **Frozen Mesh fan-out method.** Generating a finite canonical epoch from an
   ordered active-node projection; deriving exactly `N*N` row-major lane IDs;
   reobserving the bound registry/main bytes before dispatch; and deriving a
   target-specific idempotency binding from epoch, exact source revision and
   lane identity.
3. **Codec and gate apparatus.** A finite `N*N*WORD_BITS` serializer and
   inverse deserializer with protected wire framing, alongside the exact
   `CONTINUE → HOLD → ACCEPT → BLOCK` precedence circuit.
4. **Cross-layer combination.** A terminal peer whose durable receipt is
   bound to a frozen Mesh epoch and whose finite hardware endpoint rejects
   non-canonical or ambiguous frames before admission.

The technical effects to be tested for an appropriately narrowed claim are
reproducible byte serialization, deterministic fan-out identity, fail-closed
admission and restart-safe duplicate handling. They are not a claim of a
general intelligence metric, LLM-token throughput, analog-noise elimination,
universal safety, standardization, patent grant or freedom to operate.

## 4. Evidence matrix

The machine-readable evidence index is
[`state/patent/QIKVRT_DETERMINISTIC_MESH_EVIDENCE_MATRIX_V1.json`](../../state/patent/QIKVRT_DETERMINISTIC_MESH_EVIDENCE_MATRIX_V1.json).
It binds each technical proposition to source, test or testbench and records
whether the corresponding physical observation is still open.

| Evidence ID | Proposition | Bound evidence | Current classification |
| --- | --- | --- | --- |
| `QTM-HTTP-001` | V2 request/session handling is closed-domain and duplicate-sensitive. | V2 daemon, policy/schema and HTTP-terminal negative tests. | Reference implementation/test evidence; no remote deployment claim. |
| `QTM-EPOCH-001` | Fan-out freezes and reobserves one finite epoch with exactly `N*N` lanes. | Authority fan-out workflow and epoch static tests. | Workflow-source/static-contract evidence; no target-delivery claim. |
| `QTM-CODEC-001` | Serialization/deserialization follows the declared finite mapping and protected frame. | Python reference codec, VHDL codec and codec tests/testbench. | Reference/source evidence; hardware execution remains open. |
| `QTM-GATE-001` | The four-outcome gate is total and does not admit non-exact inputs. | VHDL gate and its self-checking testbench. | RTL/source evidence; locked GHDL execution remains open. |
| `QTM-FPGA-001` | The `2 x 2`, 8-bit embodiment has a specified iCE40UP5K target and reproducibility checklist. | FPGA top, constraints and prototype requirements. | Prototype preparation only; synthesis, bitstream and board observation are open. |

## 5. Prototype reproducibility and physical evidence plan

The intended initial target is the Lattice `iCE40UP5K-B-EVN` / `iCE40UP5K`
`SG48` board. The exact hardware requirements and open fields are in
`hardware/fpga/ice40up5k_breakout/PROTOTYPE_REQUIREMENTS.json`.

Before a physical claim, one reproducible run must preserve all of the
following, in this order:

1. Pin the exact OSS CAD Suite/GHDL/Yosys/nextpnr/icepack/iceprog toolchain:
   archive URL and SHA-256, license, cache path, executable path/digest,
   version output and self-test. Do not use an unpinned `PATH` tool.
2. Run the self-checking VHDL analysis, elaboration and testbenches for the
   codec, admission gate and reset-bound top. The current wrapper
   `make vhdl-admission-gate-test` blocks until its GHDL toolchain binding
   exists; it must not be replaced by a source-only success statement.
3. Synthesize the exact RTL and constraints for `up5k/sg48`, preserve the
   synthesis report, place-and-route/timing report and all input digests.
4. Preserve the generated bitstream SHA-256, programmer command/readback and
   observed board I/O/LED record, including the clock source and reset
   polarity.
5. Perform fault-injection observations for incomplete, bad sync, replay,
   reorder/insertion and CRC mismatch. An `ACCEPT` observation is valid only
   for the exact complete frame and gate truth-table combination.
6. If performance is claimed, bind a fixed workload, dataset, clock,
   measurement method, power boundary, baseline, raw logs and independent
   reproduction procedure. Raw serial-frame rate is not receipt rate or
   cognitive-workload throughput.

Until these receipts are present, the correct physical state is
`SOURCE_IS_SYNTHESIS_ORIENTED; PHYSICAL_EXECUTION_OPEN`.

## 6. Prior-art and filing preparation plan

The bound plan is
[`state/patent/QIKVRT_DETERMINISTIC_MESH_PRIOR_ART_SEARCH_V1.json`](../../state/patent/QIKVRT_DETERMINISTIC_MESH_PRIOR_ART_SEARCH_V1.json).
It treats the present record only as a preliminary search log, not a novelty
opinion. The plan requires a search across patent and non-patent literature,
synonyms, classifications, families, citations and public-disclosure timeline.

For each result, the future claim chart must compare every candidate claim
element—not merely a shared term—to the cited disclosure. It must retain:

- exact database/query/classification/date, result count and exported record;
- publication, priority and family information where available;
- cited passages/drawings, relevance category and reviewer attribution;
- a claim-element-by-element mapping and unresolved differences; and
- a separate chronology of this project's public disclosures, inventor and
  applicant review, intended jurisdictions, confidentiality and filing route.

Official public search entry points include [WIPO patent
information](https://www.wipo.int/en/web/patents), [WIPO
IPC/PATENTSCOPE information](https://www.wipo.int/en/web/classification-ipc),
[EPO Espacenet](https://www.epo.org/en/searching-for-patents/technical/espacenet)
and [USPTO Patent Public Search](https://www.uspto.gov/patents/search).
These sources support research; none turns this dossier into a legal result.

Before an application or any further potentially enabling public disclosure,
qualified patent counsel must review the complete disclosure chronology,
inventor/applicant chain, target jurisdictions, technical-claim framing,
prior-art results and the distinction between patentability and freedom to
operate. A PCT route, if selected, is not a "world patent", and filing,
publication and grant remain separate external events.

## 7. Explicit open boundaries

The following are **not** established by this dossier:

- legal novelty, inventive step, technical character in a given jurisdiction,
  eligibility, enablement, ownership, freedom to operate, application filing,
  grant or enforceability;
- IETF standard or consensus, browser V2 runtime interoperability, TLS/mTLS
  peer authentication, public Internet deployment or a protected external
  effect;
- locked HDL analysis, synthesis, timing closure, bitstream generation,
  fabrication, board execution, physical fault model or analog-noise result;
- a comparison of deterministic internal decisions with LLM tokens, an
  intelligence claim, or a universal performance/power factor; and
- `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE`.

The dossier is therefore suitable as a precise technical input to a prototype
and counsel review. It is not evidence that either process has already reached
its terminal legal or physical state.
