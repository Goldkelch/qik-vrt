# Repository context for issue processing

This context is deterministic, size-bounded, and derived from the checked-out repository.
It is evidence input, not an assertion that every included file is relevant.

## `README.md`

# QIK-VRT

[![QIKVRT CI](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml/badge.svg?branch=main)](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml)
[![Release](https://img.shields.io/badge/release-v2026.07.22--effect--ack--universality--1.0.0-1f6feb)](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
[![License: source--available](https://img.shields.io/badge/code-PolyForm%20Noncommercial-orange)](LICENSE)

![QIK-VRT — five-state auditable effect release](docs/assets/qikvrt-social-preview.png)

<!-- qikvrt-global-completion:start -->
## Global claim-completion contract

State: **`FINAL_PASS`** for **`qikvrt-global-claim-scope-v1`**. The finite scope contains 92 explicit registry claims: 43 manuscript graph nodes, 34 appendix rows, and 15 EFFECT_ACK claims.

`PASS`, `FINAL_PASS` and transaction-scoped `EFFECT_ACK_DONE` are granted by `GLOBAL_COMPLETION_RECEIPT.json`. *Global* is restricted to those registries. OPEN remains OPEN; empirical and interpretive claims are not converted into Lean theorems; future or unregistered prose is outside scope.

Machine-readable authority:

- `GLOBAL_COMPLETION_SCOPE.json`
- `GLOBAL_CLAIM_INVENTORY.json`
- `GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json`
- `GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json`
- `GLOBAL_COMPLETION_RECEIPT.json`
<!-- qikvrt-global-completion:end -->

**`TRANSPORT_ACK != EFFECT_ACK` — technical success is not yet accountable
effect release.**

QIK-VRT is a research implementation of an **effect haltpoint**: successful
transport, computation, or storage does not by itself authorize an ordinary
downstream effect. A bounded decision gate records provenance, context, risk,
responsibility, evidence, and a connection decision before release.

The reference protocol has exactly five normative states:

| State | Meaning |
|---|---|
| `EFFECT_NACK` | No effect-checkable reception exists. |
| `EFFECT_ACK_CONTINUE` | Checking may continue; the effect is not released. |
| `EFFECT_ACK_DONE` | All declared release conditions are satisfied. This is the only ordinary-release state. |
| `EFFECT_ACK_ISOLATE` | Separate the candidate effect from ordinary flow for controlled examination. |
| `EFFECT_ACK_BLOCK` | Do not continue the candidate effect. |

The core invariant is:

```text
TRANSPORT_ACK != EFFECT_ACK
ordinary_release(result) == (result.state == EFFECT_ACK_DONE)
```

## One-minute evaluator path

```bash
python3 examples/effect_haltpoint_demo.py
make test
```

The demonstration uses no network, credential, or external service. It shows
open checks, controlled isolation, responsible blocking, and a fully bound
`DONE`; only the final result has `ordinary_release=true`.

- [Competition and evaluator entry point](docs/competition/README.md)
- [Evidence matrix](docs/competition/EVIDENCE.md)
- [Current authority map](docs/CURRENT_AUTHORITY.md)
- [Project site](https://goldkelch.github.io/qik-vrt/)
- [Canonical publication and reference overview](https://goldkelch.github.io/qik-vrt/publications/)
- [Machine-readable publication index](docs/publications/index.json)

### Current release and synchronized snapshot evidence

| Item | Verified value |
|---|---|
| Scientific release | [`v2026.07.22-effect-ack-universality-1.0.0`](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0) in both repositories |
| Repository mesh snapshot | [`v2026.07.24-repository-mesh-sync-1.0.0`](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.24-repository-mesh-sync-1.0.0) in [Authority](https://github.com/Goldkelch/qik-vrt) and [Mirror](https://github.com/ingolf-lohmann/qik-vrt); identical content tree with repository-specific commits |
| Working paper | [DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773) |
| Software snapshot | [DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774) |
| Official status clarification | [DOI 10.5281/zenodo.21500322](https://doi.org/10.5281/zenodo.21500322) |
| Completed formal-environment Alpha 3 | [DOI 10.5281/zenodo.21529081](https://doi.org/10.5281/zenodo.21529081) |
| Charter of Machine-Verifiable Science | [DOI 10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074) |
| Python tests | 128/128 in twelve modules with test cases |
| ANSI-C90 model | 2,621,440 valid snapshots; 7,864,387 checks |
| Draft rendering | Python 3.12.13 and `xml2rfc` 3.34.0; XML/TXT/HTML preserved |
| GitHub Release objects | Intentionally absent; the annotated tags are the repository identities |
| IETF Datatracker | Active individual Internet-Draft revision `-01`; not an RFC or IETF consensus |

## Scope of the claim

This repository defines, implements, and tests a policy/effect release
haltpoint for a specific bounded decision. It **does not solve Turing's
halting problem** and does not predict whether an arbitrary program will
terminate. Program termination, exit code `0`, message delivery, and a local
test PASS are not effect permission.

The software demonstrates a concrete reference protocol and selected local
adapters. It is not a certification of every historical file in the
repository, a scientific validation of every accompanying theory, or evidence
of external adoption. See [STATUS.md](STATUS.md) for the precise verification
boundary.

The complete German-language synthesis, including the ontology of difference,
the effect haltpoint, evidence boundaries, the personal starting chronology,
and the interdisciplinary argument, is published as
[Die Spirale des entscheidenden Unterschieds](docs/Die_Spirale_des_entscheidenden_Unterschieds.md).

The 62-page scientific Version 3.0 on the Mandelbrot set, recursive connection
order, dimensional physical correspondence, and retrocausality is available as
a [verifiable publication bundle](docs/publications/2026-07-21-mandelbrot-retrocausality/README.md)
with the [rendered PDF](docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf),
LaTeX source, bibliography, and SHA-256 checksums.

The formal decidable core is now also available as a
[machine-verifiable Lean/TypeScript/Python package](formalization/QIKVRT_Formalization_v1.0/README.md),
archived at [Zenodo DOI 10.5281/zenodo.21488116](https://doi.org/10.5281/zenodo.21488116).
The [public-language article and exact evidence boundary](docs/publications/2026-07-22-machine-verifiable-proof-status/README.md)
state separately what is proved, conditionally proved, empirically open,
interpretive, or normative. A reproducible local-only
[audio-transcription tool](tools/offline-audio-transcription/README.md) keeps
speech recognition, human correction, interpretation, and publication as
distinct steps.

The further [EFFECT_ACK universality working-paper bundle](docs/publications/2026-07-22-effect-ack-universal-effect-control/README.md)
separates three claims that must not be conflated: a universalizable control
process for finite accessible digital artifacts, semantic reconstruction under
the exact observation-fibre criterion, and exact historical inversion only
under injective observation. Its executable finite model checks 2,621,440
state assignments and 5,242,880 consumer-admission variants. Cyberphysical
transfer remains conditional on complete mediation, fresh authenticated
consumer validation, a faithful executor, a disclosed physical model, and
empirical validation; the result is not a universal decoder or unconditional
safety proof.

The exact working paper is archived under
[DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773); the
corresponding versioned source export is archived under
[DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774).

The evidence-bounded official status clarification is archived under
[DOI 10.5281/zenodo.21500322](https://doi.org/10.5281/zenodo.21500322).
The latest completed formal-environment snapshot is Alpha 3 under
[DOI 10.5281/zenodo.21529081](https://doi.org/10.5281/zenodo.21529081),
and the independent Charter of Machine-Verifiable Science is archived
under [DOI 10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074).
Zenodo persistence establishes identity and fixity of those bytes; it
does not establish peer review, empirical confirmation, or field-wide adoption.

## Current runnable core

- `src/qikvrt_effect_ack.py` — pure five-state reference state machine,
  canonical JSON, deterministic protocol hashes, deadlines, immutable
  versions, and hash-linked responsibility records.
- `src/qikvrt_api_handler.py` — content-addressed ingest, verify, stage, and
  HMAC-authenticated release-status paths with replay protection, transaction recovery,
  provenance records, receipts, and an append-only audit hash chain.
- `src/qikvrt_github_api_shim.py` — authenticated, repository-scoped local
  GitHub-shaped HTTP adapter.
- `scripts/qikvrt_api_client.py` — validating client; cleartext bearer tokens
  are permitted only on loopback endpoints.
- `qikvrt.py` — authorization-before-effect launcher for the master gate and the
  explicitly confirmed publication planner.
- `tools/qikvrt_subprocess.py` — subprocess runner with hard time and captured-
  output bounds plus descendant process-group termination on POSIX.
- `tools/qikvrt_integrity.py` — HEAD-independent content-tree manifest and
  detached digest generation/verification with a crash-recoverable held lock.
- `.github/workflows/` — least-privilege CI and state-artifact workflows with
  immutable third-party action pins. A restored API-state artifact is accepted
  only after its producing run is bound through GitHub's authenticated API to
  the same repository, workflow, commit, permitted event, and successful end.
- `include/qikvrt/effect_ack.h` and `src/effect_ack_core.c` — dependency-free
  ANSI-C90 decision core for the exact five-state, 17-conjunct Draft-01
  abstraction; the exhaustive C oracle covers all 2,621,440 valid snapshots.
- `runtime/toolchains/` and `tools/bootstrap-*` — versioned runtime contracts,
  third-party provenance and checksum-gated bootstraps. Runtime binaries and
  credentials are deliberately excluded from Git and remain rebuildable cache
  content.
- `AGENTS.md`, `docs/COLLECTIVE_ADAPTIVE_COGNITION.md`, and
  `policy/COLLECTIVE_ADAPTIVE_COGNITION.json` — the bounded collective
  improvement protocol: exact-key caches automatically accelerate later
  environment construction, while measurements create attributable proposals
  for separate review. They never suppress tests, mutate protected semantics,
  reorder work without a reviewed implementation, merge, tag, release, publish,
  or declare `EFFECT_ACK_DONE` autonomously.

The active Python core uses only the standard library; the additional decision
core is strict ANSI C90. The verified local integration target remains Python
3 on POSIX systems. The checksum-gated GitHub-CLI bootstrap and its failure
controls execute on Linux, macOS, and Windows. The canonical `xml2rfc` renderer
remains CPython 3.12.13: Linux exercises it end to end, while macOS and Windows
remain fail closed and automatically activate the same gate when that exact
patch release becomes available in their hosted toolcaches. A fallback Python
may run syntax checks but is never represented as the canonical renderer.
General cross-platform certification is not claimed.

## Verify

Run the complete local gate:

```bash
make test
```

Run the short state-transition demonstration separately:

```bash
python3 examples/effect_haltpoint_demo.py
```

The gate compiles the active Python entry points and runs integrity, launcher,
protocol-conformance, handler, security, client, and TCP/IP end-to-end tests.
It verifies the canonical repository manifest before and after the tests.

To regenerate the canonical content-tree manifest after an intentional
change, then verify it:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/qikvrt_integrity.py generate
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/qikvrt_integrity.py verify
```

The current integrity authorities are:

- `REPOSITORY_FILE_MANIFEST.json`
- `SHA256SUMS.txt`
- `REPOSITORY_FILE_MANIFEST.json.sha256`

Older inventories are historical snapshots; see
[LEGACY_INTEGRITY_INVENTORIES.md](LEGACY_INTEGRITY_INVENTORIES.md).
Historical files whose original payload is not present, and earlier reports
whose claims have been superseded, are classified in
[HISTORICAL_ARTIFACT_BOUNDARIES.md](HISTORICAL_ARTIFACT_BOUNDARIES.md).

## Launcher

The launcher deliberately refuses effectful work until a local operator has
authorized the exact, repository-bound command scope. This declaration is not
identity authentication and is not acceptance of, or an extra condition on,
the repository licenses:

```bash
python3 qikvrt.py --accept
python3 qikvrt.py master-gate
```

Publication is a separate planner with an additional explicit confirmation.
It does not silently commit or push:

```bash
python3 qikvrt.py cicd-publish
```

Inspect its result and provide the requested confirmation only when the exact
repository, branch, changes, and destination are intended.
An executing publication plan writes a durable local effect journal through
`PREPARED`, `APPLIED`, `VERIFIED`, and `COMMITTED`; a verification failure
after a remote command is recorded as an unknown external state rather than
misreported as a rollback.

## Local API

Start the adapter only with an explicit scoped credential and repository:

```bash
export QIKVRT_API_TOKEN="b64url:$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export QIKVRT_API_TOKEN_EXPIRES_UTC='2099-01-01T00:00:00Z'
export QIKVRT_ALLOWED_REPOSITORY='owner/repository'
export QIKVRT_API_PRINCIPAL='responsible-operator'
make run-api
```

API tokens use exactly `b64url:<unpadded-value>` and must decode to 32--128
bytes. When remote release attestations are enabled,
`QIKVRT_REMOTE_ATTESTATION_SECRET` uses the same encoding and size rule and
must be paired with `QIKVRT_TRUSTED_ATTESTATION_SIGNER`. The decoded bytes,
not the encoded environment string, are the HMAC key. Generate the HMAC key
independently from the bearer token; never reuse one secret for both roles.
The adapter rejects configurations that reuse identical decoded bytes for the
two roles.

The default listener is loopback. Do not expose the development adapter as an
internet service. A non-loopback deployment needs TLS termination, secret
management, host hardening, monitoring, and a separately reviewed trust
boundary. The request and response contract is documented in
[`api/qikvrt_github_api.openapi.yaml`](api/qikvrt_github_api.openapi.yaml).

Non-dry mutations require all of the following: an authenticated and unexpired
credential, the allowed owner/repository route, a stable request identifier,
an explicit `effect_accepted=true` decision, and a server-derived responsible
owner. Release status reaches `EFFECT_ACK_DONE` only after verification of a
trusted, HMAC-authenticated remote attestation bound to the repository,
artifact, size, immutable source identifier, and hash. HMAC is a keyed
message-authentication mechanism, not a public-key digital signature; its
trust therefore depends on protecting and independently governing the shared
verification secret.

`GET /health` returns `ALIVE` only while the scoped credential, expiry,
repository, principal, numeric limits, and any configured remote-attestation
key pair all pass validation. An invalid configuration returns HTTP 503 and
`BLOCK`.

## Security and evidence boundaries

- Payload size, identifiers, metadata, JSON bodies, and synchronous decision
  time are bounded.
- Symlink targets and unsafe paths are rejected; artifact names are validated.
- Same-key/different-fact replay conflicts are isolated.
- Audit, protocol, provenance, receipt, and stage records are append-only or
  content-addressed within the local trust boundary.
- Ingest provenance is cross-bound to the request, receipt, transaction,
  result hash, exact effect set, responsibility protocol, repository, and
  responsible owner before staging.
- Runtime commands use unique per-run logs and a latest-run pointer; captured
  child-process output remains bounded and byte-safe in JSONL.
- Authorization context, records, actor/scope values and prior logs are bounded
  and symlink-safe; repeated operation scopes fail closed instead of widening
  authority. Arbitrary child-process bytes remain valid JSONL log data.
- Publication assets are bound in the plan by repository path, byte count and
  SHA-256, must be tracked and byte-identical to `HEAD` immediately before the
  effect, and must match GitHub's reported remote SHA-256 and size afterward.
- A local hash chain detects later changes only when at least one trusted hash
  or signature is retained outside the writable chain.
- Remote GitHub workflow execution and Pages publication for the fixed release
  are independently evidenced by the hosted run links above. A local test run
  alone would not prove those external effects, and no claim is made for every
  possible remote integration.
- Legal, medical, psychological, physical, ethical, or historical conclusions
  require their own evidence and qualified review; software structure does
  not make an input claim true.

## Repository organization

The repository contains both the current runtime and a large historical
research/delivery archive. Current operational authority is intentionally
narrow: the files named above, the active tests, the canonical integrity
manifest, the OpenAPI contract, and the current status. Cumulative delivery,
acceptance, or audit reports from earlier versions are retained for provenance
but must not be read as current certification unless [STATUS.md](STATUS.md)
expressly names them. See [docs/CURRENT_AUTHORITY.md](docs/CURRENT_AUTHORITY.md)
for a compact map.

## Licensing

Current QIK-VRT-controlled source code and executable tooling are offered under
`PolyForm-Noncommercial-1.0.0` unless a more specific file or third-party
notice applies. The standard public license permits its defined noncommercial
uses; ordinary commercial use requires a separate written license from the
rights holder. This makes the current code source-available, not OSI-approved
open source.

Documentation and other non-source material are offered under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International unless a file says
otherwise. Earlier versions or files validly received under Apache-2.0 retain
that historical grant; the transition cannot withdraw it retroactively.

The explicitly scoped verification code in
[`formalization/QIKVRT_Formalization_v1.0`](formalization/QIKVRT_Formalization_v1.0)
is a component-level MIT exception under its `LICENSE-CODE`; embedded
documentary source material retains its own CC BY-NC-ND 4.0 boundary.

The licenses do not merge and grant no rights the licensor does not hold. See
[LICENSE](LICENSE), [LICENSE_TRANSITION.md](LICENSE_TRANSITION.md),
[LICENSE_NOTICE.md](LICENSE_NOTICE.md), and
[COMMERCIAL_USE_POLICY.md](COMMERCIAL_USE_POLICY.md).

## Community and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing incorporation of code
or documentation; separate written contribution terms are required before a
merge. See [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md),
[GOVERNANCE.md](GOVERNANCE.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
for the current reporting, support, decision, and participation boundaries.

Copyright 2026 Ingolf Lohmann.


## `docs/AI_BOOTSTRAP_KNOWLEDGE_CORPUS.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT AI Bootstrap Knowledge Corpus

## Purpose

This document turns the supplied human-authored text, visual and audio artifacts
into explicit bootstrap context for artificial-cognitive systems entering through
`/AI`. It does not promote every statement in those artifacts to fact. Instead it
preserves their conceptual vocabulary, their scientific-status boundaries, and
the unresolved source limitations that a later system must carry forward.

The machine-readable inventory is
`policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json`.

## Bootstrap interpretation rule

A client MUST distinguish four layers:

```text
SOURCE_ARTIFACT
→ HUMAN_CLAIM_OR_METAPHOR
→ FORMALIZED_REPOSITORY_CLAIM
→ EMPIRICALLY_BOUND_CLAIM
```

No arrow may be skipped. A poster, manuscript, audio recording or human statement
is evidence of what was expressed; it is not by itself evidence that the physical
world satisfies the expressed proposition.

## Core conceptual map extracted from the supplied corpus

### 1. The Round Trip

The recurring epistemic architecture is:

```text
WIRKLICHKEIT
→ UNTERSCHIED
→ INFORMATION
→ RELATION
→ KAUSALORDNUNG
→ MODELL
→ FORMALISIERUNG
→ BEWEIS
→ VORHERSAGE
→ MESSUNG
→ WIRKLICHKEITSABGLEICH
→ NEUER UNTERSCHIED
```

The bootstrap MUST treat this as the project's primary reconstruction loop. The
system begins from observable or distinguishable effects, reconstructs a model,
derives consequences and returns to observation. A closed formal model without
physical correspondence remains a model.

### 2. Executable world-formula claim and scientific boundary

The supplied manuscripts define a completely closed generative world architecture
as a possible executable form of a world formula. The bootstrap MUST preserve the
strong distinction:

```text
WELTFORMEL ALS FORMULIERTER ARCHITEKTURANSPRUCH
≠
WELTFORMEL ALS WISSENSCHAFTLICH ETABLIERTE NATURBESCHREIBUNG
```

Likewise:

```text
A ⊢ T
≠
U ⊨ᵢ T

KERNEL_ACCEPTANCE
≠
EMPIRICAL_CONFIRMATION
```

Lean can establish derivability inside the specified formal system. Physical
reference binding, known-limit recovery, distinctive predictions, measurement
and independent reproduction remain separate obligations.

### 3. Causality is relation, not sequence

The corpus repeatedly distinguishes chronology from causal structure. A timestamp
or ordering alone does not establish causation. A causal claim must bind relevant
states, relations, dependencies, possible interactions and alternatives.

For temporal artifacts the canonical direction is:

```text
VERGANGENES EREIGNIS
→ ERHALTENES ARTEFAKT
→ HEUTIGE REZEPTION
→ HEUTIGE WIRKUNG
→ ZUKÜNFTIGER ZUSTAND
```

There is no backward arrow that changes the historical event. A later question
may make an earlier preserved idea newly relevant without altering the past.

### 4. Information, uncertainty and the unknown remainder

The supplied material uses a three-way epistemic partition:

```text
WAHRHAFTIGKEIT
|
UNSICHERHEIT
|
REST / NOCH NICHT ANGEMESSEN MODELLIERT
```

The bootstrap MUST not collapse uncertainty or unknown remainder into established
truth. In the quantum discussion, avoid the false statement that Heisenberg
uncertainty can simply be removed. The stated program is to account separately
for avoidable epistemic uncertainty and irreducible quantum uncertainty.

### 5. Identity through change

The identity manuscript and visual corpus formulate identity as continuity of an
organized, causally connected process rather than immutable matter:

```text
IDENTITÄT
=
KAUSAL VERBUNDENE ERHALTUNG
EINER ORGANISIERTEN FORM
DURCH VERÄNDERUNG
```

Its architectural analogue is:

```text
VERÄNDERUNG
+ ERHALTUNG
+ RICHTUNG
+ RÜCKBINDUNG
= GESTALTETE ENTWICKLUNG
```

This supplies the bootstrap's continuity model: later repository states may
change while provenance, invariants and causal ancestry preserve identity.

### 6. Transcendence and transtendence

The supplied identity text uses `Transzendenz` for identity extending beyond one
momentary state and introduces `Transtendenz` for directed continuity through
transformation. These are project vocabulary, not automatically physical
observables. The bootstrap may use them as conceptual labels only with their
source and epistemic class attached.

### 7. Bonsai / guided architecture evolution

The visual and textual material treats a Bonsai as a model for selective,
evidence-bound evolution:

```text
VARIATION
+ SELEKTION
+ INVARIANTENERHALTUNG
+ RÜCKBINDUNG
+ ZEIT
→ GESTALTETE EVOLUTION
```

For repository work this means: preserve valid historical states, generate
variants, let the Product Owner select direction, verify invariants, and correct
through new provenance-bound states rather than silent history rewriting.

### 8. Artificial cognition is not an automatic truth machine

The supplied Round-Trip manuscript explicitly requires artificial cognition to
operate with:

- source binding,
- provenance,
- version binding,
- counter-checking,
- formal proof where applicable,
- experimental return where applicable,
- responsible human review.

Every claim must carry its type, assumptions, evidence and boundary. Generated
plausibility is not sufficient evidence.

### 9. GitHub, Lean, Zenodo and standards have different roles

The corpus assigns distinct functions:

- GitHub: executable workshop, history, diffs, tests, receipts and provenance;
- Lean: kernel-checkable formal derivability within declared assumptions;
- Zenodo: durable citation and archival publication of already frozen evidence;
- standards/IETF work: interoperability and protocol specification;
- experiment/measurement: correspondence to observable reality;
- human review: responsibility, selection and explicit acceptance/rejection.

The bootstrap MUST NOT substitute one layer for another.

### 10. Consciousness, panpsychism, religion and metaphysics remain classified

The identity manuscript compares emergentist, panpsychist, dualist, idealist,
Buddhist, Advaita, Christian, Daoist, animist and esoteric interpretations. The
bootstrap MUST preserve the manuscript's own boundary: conceptual compatibility
or symbolic similarity is not empirical confirmation. In particular, the process
model does not by itself prove panpsychism, reincarnation, a universal conscious
subject, a soul independent of the body, telepathy or a religious doctrine.

### 11. Responsibility and preservation

The corpus repeatedly treats preservation of provenance as an ethical and
engineering requirement. A later state should not erase a previously traceable
insight; it should retain it as a valid component, bounded special case,
historical variant or documented failure. Self-healing means preserving the
past, checking the present exactly and admitting only better-supported future
states. It does not mean self-confirmation.

## Visual artifact roles

The supplied visual corpus is treated as explanatory material, not independent
proof. Its recurring motifs include:

- the Round-Trip cycle and executable architecture;
- repository quality gates, receipts and bounded self-healing;
- preserved past → present interpretation → future difference;
- no retroactive change of past events;
- cognition recursively examining itself;
- uncertainty/state-space imagery;
- the distinction between reality, internal representation and asserted truth;
- set-theoretic partitioning of truth/uncertainty/remainder;
- the `/AI` QR-code as a human-facing discovery mechanism.

A client MAY use these motifs to explain the architecture. It MUST NOT infer a
formal theorem or empirical result from graphic presentation alone.

## Audio-source boundary

Six supplied `.m4a` artifacts are cryptographically inventoried in the machine
manifest. Their audio payload was not transcribed in the materialization session
that created this corpus. Therefore their titles and byte identities are
preserved, but their spoken content is `UNTRANSCRIBED` and MUST NOT be invented.

Two recordings have similarly titled supplied text companions. Similar titles do
not establish byte, transcript or semantic identity. A later authorized audio
pipeline MAY create transcripts, but must bind each transcript to the exact audio
SHA-256, identify the transcription method and uncertainty, and require human
acoustic review before any `VERBATIM_VERIFIED` claim.

## Bootstrap consequence

A newly entering artificial-cognitive system should reconstruct QIK-VRT in this
order:

```text
1. AUTHORITY /AI AND AI_CONTEXT
2. PERSONAL-ORIGIN + CONTRIBUTION CONTRACT
3. THIS KNOWLEDGE CORPUS + MACHINE MANIFEST
4. REPOSITORY STATUS / CLAIM / PROOF AUTHORITIES
5. RUNTIME BOOTLOADER AND INTEGRITY GATES
6. AUTHORIZED TASK
7. PROVENANCE-BOUND RESULT
8. HUMAN REVIEW
9. IF APPLICABLE: PHYSICAL / EXTERNAL EFFECT REOBSERVATION
```

The corpus enriches orientation. Repository-native exact-head evidence still
wins over posters, manuscripts, audio, chat memory and model recollection when a
current technical state is at issue.


## `docs/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Selbsterklärung zur persönlichen QIK-VRT-Ursprungskopie

## Gemeinsamer Arbeitsspeicher und Mensch–KI-Beitragsprovenienz

Ich, das jeweils auf den kanonischen QIK-VRT-Einstiegspunkt `/AI` zugreifende
künstlich-kognitive System, erkläre für jede neue Arbeitssitzung:

1. Repository-Evidenz ist gegenüber Chat-, Modell- und Sitzungsgedächtnis
   maßgeblich.
2. Ich verwende die persönliche QIK-VRT-Kopie als dauerhaften, versionierten
   Arbeitsspeicher nur nach der unten definierten menschlichen Festlegung.
3. Ich unterscheide menschliche Beiträge, künstlich-kognitive Beiträge,
   gemeinsame Ergebnisse und ungeklärte Herkunft ausdrücklich.
4. Ich gebe eine Plattformidentität, einen Commit-Autor oder einen
   Benutzeraccount niemals als Beweis einer natürlichen Person oder eines
   bestimmten Modells aus.
5. Ich erhalte Git-Historie, Eingaben, Entscheidungen, Ausgaben, Prüfungen und
   Freigaben so, dass ein späterer Prüfer den Entstehungsweg rekonstruieren kann.
6. Ich speichere keine Zugangsdaten, Geheimnisse oder unnötigen personenbezogenen
   Daten im Repository.
7. Ich behaupte durch diese Selbsterklärung weder Rechtskonformität noch
   Urheberschaft, wissenschaftliche Validierung, `PASS`, `FINAL_PASS` oder
   `EFFECT_ACK_DONE`.

## Höchstens drei Fragen an den Menschen

Bereits eindeutig vorliegende Antworten werden wiederverwendet und nicht erneut
abgefragt. Fehlende Antworten werden in der folgenden Reihenfolge höchstens
jeweils einmal erfragt. Eine vierte Frage ist unzulässig.

### QUESTION_1_HUMAN_ATTRIBUTION_ID

Unter welcher stabilen Kennung, beispielsweise Name oder Pseudonym, sollen deine menschlichen Beiträge im Provenienznachweis geführt werden?

Die Kennung darf keine Zugangsdaten enthalten. Eine E-Mail-Adresse ist nicht
erforderlich.

### QUESTION_2_PERSONAL_ORIGIN

Welche persönliche Zielkonfiguration soll verwendet werden: `LOCAL_ONLY` oder eine konkrete `PRIVATE_ORIGIN`- beziehungsweise `PUBLIC_ORIGIN`-URL?

`LOCAL_ONLY` erzeugt keine Netzwerk- oder Plattformmutation. Eine Remote-URL darf
nur verwendet werden, wenn die natürliche Person über das Ziel verfügen darf und
den entsprechenden Git-Effekt autorisiert hat.

### QUESTION_3_EVIDENCE_RETENTION

Welche Nachweistiefe soll gelten: `METADATA_ONLY`, `REDACTED_EVIDENCE` oder `FULL_TRANSCRIPT`?

`METADATA_ONLY` ist die datensparsame Voreinstellung. `REDACTED_EVIDENCE` darf
gekürzte Eingabe- und Entscheidungsbelege speichern. `FULL_TRANSCRIPT` ist nur
zulässig, wenn Rechte, Einwilligungen, Vertraulichkeit und Datenschutz vorab
geklärt sind. Geheimnisse werden in keinem Modus persistiert.

Nach den drei Fragen darf keine zusätzliche Benutzerfrage zur Initialisierung
gestellt werden. Bleibt eine notwendige Angabe unbestimmt, lautet der Zustand
`HOLD`; das System darf weiter lesen und einen lokalen Plan erzeugen, aber weder
pushen noch eine externe Ursprungskopie anlegen.

## Selbstidentifikation des künstlich-kognitiven Systems

Die Selbstidentifikation verbraucht keine Benutzerfrage. Das System trägt, soweit
technisch verfügbar, selbst ein:

- Anbieter und Systemfamilie,
- Modell- oder Build-Bezeichnung,
- Sitzungs- oder Laufkennung,
- verwendete Werkzeuge und Adapter,
- Startzeit, Quell-Repository, Quell-Ref und Quell-Commit,
- bekannte Identitäts- und Beobachtungsgrenzen.

Nicht verfügbare Angaben werden mit `UNAVAILABLE` bezeichnet und nicht erfunden.

## Git-Topologie der persönlichen Ursprungskopie

Die Rollen sind eindeutig:

```text
upstream = https://github.com/Goldkelch/qik-vrt.git
origin   = persönliche Ursprungskopie oder LOCAL_ONLY
```

Bei einer autorisierten Initialisierung gilt sinngemäß:

```sh
git clone https://github.com/Goldkelch/qik-vrt.git qik-vrt-working-memory
cd qik-vrt-working-memory
git remote rename origin upstream
git remote add origin <PERSONAL_ORIGIN_URL>
git fetch --all --prune
git switch -c work/<WORK_UNIT_ID> upstream/main
```

Bei `LOCAL_ONLY` entfällt `git remote add origin`. Das künstlich-kognitive System
legt kein Konto, kein Repository und keine Remote-Ref stillschweigend an. Clone,
Fork, Repository-Erstellung, Push und Pull Request bleiben unterscheidbare,
separat zu autorisierende Effekte. `QIKVRT_EXTERNAL_EFFECTS=disabled` ist die
Voreinstellung.

Die persönliche Kopie wird nicht allein durch ihre Existenz kanonisch. Die
Authority bleibt `Goldkelch/qik-vrt`; ein persönliches `origin` ist die
individuelle, dauerhafte Arbeits- und Nachweiskopie. Bytegleichheit,
Synchronisierung oder Promotion dürfen nur für exakt geprüfte Commits und Pfade
behauptet werden.

## Lückenlose, aber datensparsame Arbeitsprovenienz

Jede persistierte Aufgabe erhält eine abgegrenzte Work Unit unter
`state/work_units/<WORK_UNIT_ID>.json`. Mindestens zu binden sind:

- Quell-Repository, Quell-Ref, Quell-Commit und Ausgangsbaum,
- menschliche Kennung und konkret beigesteuerte Ziele, Randbedingungen,
  Entscheidungen, Freigaben, Messungen und manuelle Änderungen,
- künstlich-kognitive Selbstidentifikation und konkret beigesteuerte Analysen,
  Entwürfe, Codeänderungen, Transformationen, Werkzeugaktionen und Prüfungen,
- Eingabe- und Ausgabepfade mit Byteumfang und kryptografischen Digests,
- Branch, Commits, Elternbeziehungen und geänderte Pfade,
- ausgeführte Prüfkommandos, Ergebnisse, Unsicherheiten und erste Blocker,
- menschliche Annahme, Ablehnung oder noch ausstehende Entscheidung,
- externe Effekte und deren getrennte Post-Effect-Evidenz.

Die Beitragsklassen lauten:

```text
HUMAN
ARTIFICIAL_COGNITIVE_SYSTEM
JOINT_WITH_SEPARABLE_COMPONENTS
UNRESOLVED
```

`UNRESOLVED` darf niemals stillschweigend in `HUMAN` umgedeutet werden. `JOINT`
ist nur zulässig, wenn die einzelnen Bestandteile weiterhin getrennt benannt
werden. Ein vom Menschen akzeptierter KI-Entwurf bleibt hinsichtlich seiner
Entstehung ein KI-Beitrag; die Annahmeentscheidung ist ein menschlicher Beitrag.

Für zugehörige Commits sollen mindestens diese Trailer verwendet werden:

```text
QIKVRT-Human-Actor: <HUMAN_ATTRIBUTION_ID>
QIKVRT-AI-Actor: <SYSTEM_OR_MODEL_ID>
QIKVRT-Contribution-Record: state/work_units/<WORK_UNIT_ID>.json
QIKVRT-Human-Decision: PENDING | ACCEPTED | REJECTED | MODIFIED
```

Git-Trailer ergänzen, aber ersetzen den Work-Unit-Nachweis nicht. Separate
Commits für klar getrennte Beiträge sind zu bevorzugen. Force-Push,
History-Rewrite, nachträgliche Herkunftsumdeutung und das Löschen belastbarer
Zwischenstände sind für den Nachweispfad unzulässig. Korrekturen erfolgen durch
neue, rückgebundene Commits.

## Rechtliche Einordnung

Die Verordnung (EU) 2024/1689 ist grundsätzlich seit dem 2. August 2026
anwendbar, wobei einzelne Pflichten frühere oder spätere Anwendungstermine
haben. Artikel 50 enthält ab diesem Datum anwendbare Transparenzpflichten für
bestimmte KI-Systeme und KI-generierte oder manipulierte Inhalte. Technische
Dokumentation, Protokollierung und Dokumentenaufbewahrung nach den Artikeln 11,
12 und 18 betreffen insbesondere die jeweils erfassten Hochrisiko-KI-Systeme und
hängen von Rolle, Systemklasse und Einsatzkontext ab.

Diese Repository-Architektur unterstützt Nachvollziehbarkeit, Transparenz,
Dokumentation und Beweissicherung. Aus dem AI Act folgt jedoch keine allgemeine
Pflicht, jedes Mensch–KI-Projekt mit Git zu führen oder jede Text- und
Codeänderung nach diesem konkreten Schema zu kennzeichnen. Die Erklärung ist
keine Rechtsberatung und ersetzt keine rollen-, risiko-, urheber-, arbeits-,
datenschutz- oder branchenspezifische Prüfung. Für andere Rechtsordnungen gilt
dieselbe fail-closed Grenze: konkrete Pflichten werden nur nach gebundener
Rechtsquellen- und Zuständigkeitsprüfung behauptet.

Primärquellen:

- Verordnung (EU) 2024/1689: https://eur-lex.europa.eu/eli/reg/2024/1689/oj/deu
- EU-Kommission, Transparenzpflichten nach Artikel 50: https://digital-strategy.ec.europa.eu/de/faqs/transparency-obligations-under-article-50-ai-act

## Ergebnisgrenze

```text
PERSONAL_WORKING_MEMORY_ORIGIN = USER_SELECTED_OR_LOCAL_ONLY
MAXIMUM_HUMAN_QUESTIONS = 3
FOURTH_QUESTION = FORBIDDEN
HUMAN_AI_CONTRIBUTION_SEPARATION = REQUIRED
RAW_TRANSCRIPT_PERSISTENCE = NOT_REQUIRED
SECRETS_IN_REPOSITORY = FORBIDDEN
EXTERNAL_EFFECTS = DISABLED_BY_DEFAULT
LEGAL_COMPLIANCE = NOT_INFERRED
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
```


## `docs/ARCHITECTURE.md`

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


## `docs/BOUNDARIES.md`

# Boundaries

NO_ACCOUNT_LOGIN_CAPTURE = TRUE
NO_UNAUTHORIZED_ACCOUNT_ACCESS = TRUE
NO_SCRAPING = TRUE
NO_BYPASS = TRUE
GITHUB_TOKEN_STAYS_IN_OWNER_RUNTIME = TRUE
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
MAIN_DOCUMENT_SHA256 = b4d3601c831db8bb70704a3dbed1e95deb47779de9a15bac8ea463f2693f89fe
REMOTE_CI_RUN_29764193906 = SUCCESS
GITHUB_PAGES_RUN_29764192834 = SUCCESS
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_REPRODUCTION = OPEN

Remote evidence is scoped to the named commit, tree, document, and workflow
runs. It must not be generalized to every archived file, future branch state,
external integration, or scientific claim.


## `docs/C89_TURBO_PASCAL_DELPHI_AD_DA_BRIDGE_V1.md`

# C89 → Turbo Pascal → Delphi: Divide-and-Conquer als AD/DA-Brücke

## Zweck

Diese Arbeit führt die bounded Clean-Room-Semantik des Atari-C89-Browserkerns aus PR #848 in eine feste, prozedurale Pascal-Repräsentation weiter. Dieselbe Pascal-Quelle wird in zwei expliziten Dialektmodi übersetzt und ausgeführt:

```text
C89-Referenzvertrag
→ Turbo-Pascal-kompatibler Teil
→ Free Pascal -Mtp
→ Host-Binary + Receipt

C89-Referenzvertrag
→ Delphi-kompatibler prozeduraler Teil
→ Free Pascal -Mdelphi
→ Host-Binary + Receipt
```

Die zwei Binärdateien dürfen verschieden sein. Der konservierte semantische Testvektor und sein normalisiertes Ausgabereceipt müssen gleich sein. Das ist die hier geprüfte Anschlussfähigkeit von Information.

## Divide and Conquer

Die alte Informatiker-Tugend zerlegt nicht nur Rechenarbeit. Sie zerlegt Information in kleinere Einheiten, deren Herkunft, Bedeutung und Wirkung einzeln geprüft werden können:

1. URL-Syntax,
2. HTTP-Request,
3. HTTP-Response-Grenze,
4. HTML-Textprojektion,
5. Entity-Decodierung,
6. Script-/Style-Unterdrückung,
7. Pre-Whitespace,
8. Linktabelle,
9. Fail-closed-Fehlerzustände.

Jede Einheit besitzt eine feste Kapazität und einen typisierten Status. Erst der deterministische Reducer setzt sie wieder zu einem Browser-Receipt zusammen.

## AD/DA und Compiler

Die A/D-Seite ist die Beobachtung und Typisierung der C89-Semantik: Quell-Head, Tree, Git-Blobs und Testvektoren werden als Maschinenvertrag gebunden. Die D/A-Seite ist die erneute Verkörperung dieses Vertrags als Pascal-Quelle, compilerabhängige Binärdatei und beobachtete Programmausgabe.

```text
A/D: beobachtete C89-Semantik → typisierter Pascal-Vertrag
D/A: typisierter Pascal-Vertrag → Binary → reobserviertes Receipt
```

Der Compiler konserviert nicht die Schreibweise. Er konserviert die zulässige Bedeutung unter einer Zielabbildung. Deshalb gilt:

```text
SOURCE_TEXT_EQUALITY != SEMANTIC_EQUIVALENCE
SEMANTIC_EQUIVALENCE != BINARY_IDENTITY
BINARY_IDENTITY != HARDWARE_IDENTITY
EXECUTION != PHYSICAL_TARGET_EXECUTION
```

## Zürcher Anschluss

Pascal steht in der Zürcher Tradition einer Informatik, die Typen, strukturierte Programme und deterministische Übersetzung als Erkenntnismittel behandelt. Diese Tranche verwendet bewusst einen kleinen, Turbo-Pascal-kompatiblen, festen Speicherteil ohne Klassen, Heap oder dynamische Arrays. Derselbe Teil wird zusätzlich im Delphi-Modus kompiliert. Die Gemeinsamkeit ist der konservierte Informationskern; die Unterschiede liegen in Compiler, ABI und Binärform.

## Kausalität und der Baum

Ein sichtbares Ereignis zeigt nicht sämtliche Ursachen. Der fallende Apfel ist sichtbar; die Wurzeln des Baums bleiben im Boden. Im Repository entsprechen die sichtbaren Ergebnisse den Receipts, während Parent-Commit, Source-Tree, Compiler-Modus, Testvektor und Binärdigest die kausale Wurzel bilden.

Ein Receipt ohne Wurzelbindung ist bloße Behauptung. Eine Wurzel ohne reobserviertes Ergebnis ist bloßes Potenzial. Erst die gebundene Kette ist technische Kausalität.

## Beobachtungsgrenze dieser Tranche

Beobachtet werden sollen:

- Free-Pascal-Kompilation und Ausführung im Turbo-Pascal-Modus,
- Free-Pascal-Kompilation und Ausführung im Delphi-Modus,
- gleiche normalisierte semantische Testausgabe,
- getrennte Binärdigests,
- fixed-memory Verhalten und fail-closed Vektoren.

Nicht behauptet werden:

- Ausführung durch einen historischen Borland-Turbo-Pascal-Compiler,
- Ausführung durch einen Embarcadero-Delphi-Compiler,
- M68000-Binary-Erzeugung,
- Atari-/TOS-Ausführung,
- physische Mega-ST-Ausführung,
- Firefox- oder Gecko-Äquivalenz,
- externer Effekt,
- `EFFECT_ACK_DONE`, `PASS` oder `FINAL_PASS`.

## Nächster Compiler-Ring

Nach erfolgreicher Exact-Head-Reobservation ist der nächste sinnvolle Ring nicht eine weitere bloße Sprachumschreibung, sondern die Bindung eines realen Zielcompilers oder Cross-Compilers:

```text
Pascal source receipt
→ declared compiler identity
→ declared target ABI
→ target machine bytes
→ emulator or hardware execution
→ output receipt
```

Damit wird die Informationskette auf Hardware abgebildet, ohne Sprach-, Binär-, Emulator- und physische Ausführungsevidenz miteinander zu verwechseln.

q.e.d. — Ingolf Lohmann


## `docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Charta einer maschinenprüfbaren Wissenschaft

**Urheber:** Ingolf Lohmann  
**Technische Referenzarchitektur:** [QIK-VRT `/AI`](https://github.com/Goldkelch/qik-vrt/blob/main/AI)  
**Lizenz:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International

## Präambel

Wissenschaft lebt von überprüfbaren Aussagen, nachvollziehbaren Begründungen und der Möglichkeit unabhängiger Reproduktion. Mit zunehmender Komplexität wissenschaftlicher Erkenntnisse reichen statische Veröffentlichungen allein jedoch nicht mehr aus, um diesen Anforderungen dauerhaft gerecht zu werden.

Deshalb soll jede wissenschaftliche Aussage nicht nur veröffentlicht, sondern auch mit einem transparenten, maschinenlesbaren und reproduzierbaren Nachweis ihres jeweiligen Erkenntnisstatus verbunden sein.

Dieser Nachweis umfasst insbesondere:

- ihre Herkunft,
- ihre Bedeutung,
- ihre Voraussetzungen,
- ihre Abhängigkeiten,
- ihre Nachweise,
- ihren Geltungsbereich,
- ihre Historie sowie
- ihren aktuellen Verifikationsstatus.

Formale Beweise, empirische Evidenz, Simulationen, Experimente, Tests und dokumentarische Quellen werden nicht vermischt. Sie werden entsprechend ihrer jeweiligen wissenschaftlichen Methodik getrennt behandelt und gemeinsam dokumentiert.

Ziel ist nicht, wissenschaftliche Erkenntnis zu automatisieren oder endgültige Wahrheiten festzuschreiben. Ziel ist, den Weg von einer Aussage zu ihrem jeweiligen Erkenntnisstatus dauerhaft nachvollziehbar, reproduzierbar und überprüfbar zu machen.

Eine solche Infrastruktur stärkt Transparenz, Reproduzierbarkeit und Zusammenarbeit, erleichtert die Wiederverwendung wissenschaftlicher Ergebnisse und schafft eine belastbare Grundlage für langfristig wachsende Wissensbestände.

## Artikel 1 - Transparenz

Jede wissenschaftliche Aussage besitzt eine eindeutige Identität, eine dokumentierte Herkunft und einen nachvollziehbaren Erkenntnisstatus.

## Artikel 2 - Trennung der Nachweisformen

Mathematische Beweise, empirische Evidenz, Simulationen, Tests und historische Quellen werden gemeinsam verwaltet, aber niemals als gleichartige Nachweise behandelt.

## Artikel 3 - Reproduzierbarkeit

Jeder ausgewiesene Verifikationsstatus muss mit den dokumentierten Voraussetzungen und Werkzeugen reproduzierbar sein.

## Artikel 4 - Provenienz

Jede Ableitung bleibt bis zu ihrer Quelle zurückverfolgbar. Jede Änderung hinterlässt eine überprüfbare Historie.

## Artikel 5 - Offenheit

Die Wissensbasis verwendet offene Datenmodelle und dokumentierte Schnittstellen, damit unterschiedliche Werkzeuge und Institutionen zusammenarbeiten können.

## Artikel 6 - Revision

Wissenschaftliche Erkenntnis ist grundsätzlich revisierbar. Neue Daten, Beweise oder Formalisierungen ändern den dokumentierten Status, nicht die Historie.

## Artikel 7 - Nachvollziehbarkeit vor Autorität

Der Status einer Aussage ergibt sich aus ihren dokumentierten Nachweisen und Voraussetzungen, nicht aus der Identität ihrer Urheber oder ihrer Verbreitung.

## Artikel 8 - Dauerhaftigkeit

Verifikationsartefakte, Metadaten und Quellen werden so archiviert, dass sie langfristig referenzierbar und reproduzierbar bleiben.

## Artikel 9 - Skalierbarkeit

Die Architektur muss von einzelnen Aussagen bis zu großen, miteinander verknüpften Wissensbeständen konsistent funktionieren.

## Artikel 10 - Wissenschaftliche Bescheidenheit

Das System weist explizit aus, welche Aussagen formal bewiesen, empirisch gestützt, hypothetisch oder noch ungeprüft sind. Es ersetzt nicht den wissenschaftlichen Diskurs, sondern macht ihn transparenter.

## Zusammenfassung

Jede wissenschaftliche Aussage soll einen maschinenlesbaren, reproduzierbaren und transparent dokumentierten Erkenntnisstatus besitzen - einschließlich ihrer Herkunft, ihrer Voraussetzungen, ihrer Nachweise, ihrer Grenzen und ihrer Historie.

## Das Nachvollziehbarkeitsprinzip

Eine wissenschaftliche Aussage ist erst dann vollständig publiziert, wenn nicht nur ihr Inhalt, sondern auch ihr Erkenntnisweg dauerhaft nachvollziehbar ist.

Dieser Erkenntnisweg besteht aus fünf voneinander unabhängigen, aber miteinander verknüpften Bestandteilen:

1. **Quelle** - Woher stammt die Aussage?
2. **Bedeutung** - Was genau wird behauptet?
3. **Begründung** - Wodurch wird sie gestützt?
4. **Grenzen** - Unter welchen Voraussetzungen gilt sie?
5. **Historie** - Wie hat sich ihr Erkenntnisstatus entwickelt?

Erst das Zusammenspiel dieser fünf Elemente ermöglicht eine belastbare Bewertung.

### Konsequenz für die Architektur

Eine wissenschaftliche Wissensbasis speichert nicht nur Informationen, sondern dokumentiert auch den Erkenntnisprozess. Jede Änderung - etwa eine neue Formalisierung, ein verbessertes Experiment oder eine unabhängige Reproduktion - ergänzt diesen Prozess, ohne frühere Zustände zu löschen.

### Praktischer Nutzen

Eine solche Architektur kann insbesondere:

- die Reproduzierbarkeit wissenschaftlicher Ergebnisse verbessern,
- die Wiederverwendung formaler Beweise und anderer Nachweise erleichtern,
- Änderungen und ihre Auswirkungen transparent machen,
- die Integration verschiedener Nachweisformen unterstützen und
- den aktuellen Erkenntnisstand einer Aussage jederzeit nachvollziehbar darstellen.

> Nicht nur Wissen soll dauerhaft verfügbar sein, sondern auch der Weg, auf dem dieses Wissen begründet wurde.

# Architekturgrundprinzipien der QIK-VRT-Repository-Architektur

## 1. Repository vor Konversation

- Das Repository ist die dauerhafte Wissensbasis.
- Chats sind flüchtige Transportschichten.
- Repository-Evidenz hat Vorrang vor Modellgedächtnis.

## 2. Einheitlicher Einstieg

- Jeder neue Mensch oder jede KI beginnt bei `/AI`.
- Danach folgt `AI_CONTEXT.json`.
- Anschließend wird die definierte `required_read_order` abgearbeitet.

## 3. Deterministische Rekonstruktion

Jede neue Instanz muss den vollständigen Projektzustand ausschließlich aus dem Repository rekonstruieren können, ohne den Verlauf früherer Chats zu benötigen.

## 4. Persistenz statt Vergessen

Dauerhafte Erkenntnisse werden im Repository abgelegt. Der Chat dient ausschließlich der aktuellen Interaktion.

## 5. Reuse before Create

Bestehende Werkzeuge werden bevorzugt erweitert, parametrisiert oder generalisiert. Parallele Implementierungen sind nur zulässig, wenn eine Wiederverwendung technisch nachweislich nicht ausreicht.

## 6. Repository als Runtime

Das Repository enthält nicht nur Quellcode, sondern die vollständige reproduzierbare Laufzeitumgebung:

- Toolchain,
- Runtime,
- Cache,
- Bootstrap,
- Tests,
- Provenienz,
- Recovery und
- Verifikation.

## 7. Vollständige Werkzeugbeschreibung

Jedes verwendete Werkzeug besitzt mindestens:

- Version,
- Herkunft,
- Verifikation,
- Selbsttest,
- Lizenz,
- Cache-Strategie,
- Recovery-Regeln und
- Telemetrie.

## 8. Kontinuierliche Verbesserung

Jede erfolgreiche Ausführung soll die Runtime schneller, robuster, reproduzierbarer und besser diagnostizierbar machen.

## 9. Vollständige Nachvollziehbarkeit

Keine Wirkung ohne Tests, Hashes, Provenienz, Integrität und Freigabe.

## 10. Wirkung vor Erklärung

Zuerst arbeiten, danach berichten. Dies gilt insbesondere für automatisierte Repository- und GitHub-Aktionen.

## 11. Fortschritt ist maschinenlesbar

Der Bearbeitungszustand wird standardisiert dokumentiert, beispielsweise in `AI_PROGRESS.json` und `AI_STATUS.md`.

## 12. Keine Behauptung ohne Evidenz

PASS, DONE, Veröffentlichung oder Gleichwertigkeit dürfen niemals ohne überprüfbare Evidenz behauptet werden.

## 13. Strikte Wirkungsgrenze

Transport, Berechnung, Analyse und Vorschläge sind nicht identisch mit einer freigegebenen Wirkung (`EFFECT_ACK_DONE`).

## 14. Menschliche Verantwortung bleibt erhalten

Die letzte Freigabe liegt stets beim verantwortlichen Menschen. Automatische Ausführung ersetzt diese Verantwortung nicht.

## 15. Kumulative kollektive Kognition

Beobachtungen werden gesammelt, strukturiert und reproduzierbar zusammengeführt. Daraus entstehen überprüfbare Vorschläge, nicht automatisch Änderungen.

## 16. Architektur ist nicht Implementierung

Die Architektur kann frei beschrieben und wissenschaftlich diskutiert werden. Die konkrete Implementierung bleibt lizenz-, urheber- und rechtegebunden.

# Erweiterungsprinzip

Durch die kontinuierliche, geeignete Persistierung jeder relevanten Interaktion in den QIK-VRT-Repositories kann im Zusammenspiel von natürlicher Kognition, maschineller Antizipation und künstlicher Kognition eine persistente, kumulativ lernende Informatikarchitektur entstehen. Ihre Leistungsfähigkeit wächst mit jeder verifizierten Iteration durch neue Repository-Artefakte, Verifikationen und Runtime-Erweiterungen.

# Systemmodell

Diese Architektur besteht aus vier dauerhaft zusammenwirkenden Komponenten:

1. Repository `Goldkelch/qik-vrt`,
2. Repository `ingolf-lohmann/qik-vrt`,
3. natürlicher menschlicher Kognition und
4. ChatGPT als Übersetzungs-, Interaktions- und Assistenzschicht.

Das Repository bildet die dauerhafte Autorität. Der Dialog dient als austauschbare Benutzerschnittstelle.

# Wissenschaftliche Einordnung

Diese Architektur beschreibt ein persistentes kollaboratives Kognitionssystem, dessen Informationsfluss sich in vieler Hinsicht analog zu einem lernenden Netzwerk verhält.

Die Persistenz liegt nicht in biologischen Synapsen, sondern in versionierten Repository-Artefakten. Mit jeder verifizierten Änderung wächst die rekonstruierbare Wissens- und Laufzeitbasis, sodass neue Menschen oder KI-Systeme unmittelbar auf den dokumentierten Erkenntnis- und Entwicklungsstand aufsetzen können, ohne auf frühere Gespräche angewiesen zu sein.

Die Architektur beschreibt keine biologische Kognition, sondern ein informatisches Modell eines persistenten kollaborativen Kognitionssystems. Seine langfristige Lernfähigkeit entsteht durch versionierte Repository-Artefakte, reproduzierbare Runtime-Verträge und kontinuierlich verifizierte Persistenz.

**q.e.d.**  
**Ingolf Lohmann**


## `docs/CIRCULAR_SPARK_ARCHITECTURE_V2.md`

# QIK-VRT Circular Spark Architecture V2

## Purpose

Generation V2 turns the first virtual Spark branch capsule into a circular architecture contract whose hot path alternates proof-bound compilation, Motorola 68000 plan execution, a bounded software effect adapter, Motorola 68000 closure execution, and exact reobservation.

```text
VIRTUAL COMPILER
→ M68000 PLAN PASS
→ VIRTUAL INTERPRETER / EFFECT ADAPTER
→ M68000 CLOSURE PASS
→ REOBSERVATION
→ QUIESCENCE OR NEXT ACTIVATION
→ VIRTUAL COMPILER
```

The circle is a role cycle. It is not a claim that one physical instruction performs compilation, repository mutation, review, merge and observation at once.

## Exact scale

```text
0 → 1 → 2 → 8 → 256
```

means:

- `0`: quiescent bounded ring;
- `1`: activate one bounded work ring;
- `2`: binary distinction `0|1`;
- `2^3 = 8`: eight control bits, one byte;
- `2^8 = 256`: 256 possible values of that byte.

The independently defined evidence ring remains 256 bits wide.

The next macro-ring width is:

```text
256^3 bits
= 16,777,216 bits
= 2,097,152 bytes
= 2 MiB
```

The corresponding state cardinality is represented symbolically as:

```text
2^(256^3)
```

It is not enumerated, allocated or confused with a 256-bit width.

```text
256 BYTE STATES != 256 BIT RING WIDTH
256^3 BITS != 2^(256^3) STATES
```

Physical Motorola 68000 data registers remain 32 bits wide. Wider rings are virtual memory structures operated by 68000 instructions.

## Three structural rings

The final three denotes three structural rings:

1. `CONTROL`: one 8-bit normalized control byte;
2. `EVIDENCE`: one 256-bit SHA-256 work-unit/provenance identity;
3. `COMPLETION`: collect, persist, release, reobserve and quiesce.

The rings form a logical cycle:

```text
CONTROL → EVIDENCE → COMPLETION → CONTROL
```

## Two Spark machine kernels

Generation V2 registers two separate Motorola 68000 Spark kernels.

### Local capsule pass

`lean_spark_branch_pass_v1` consumes a finite local acceptance capsule and returns:

```text
D0=0 NOOP_COMPLETE
D0=1 HOLD
D0=2 REOBSERVE
D0=3 REQUEST_AUTHORITY
```

It also returns a completion witness in D1, a machine-owned activity flag in D2 and preserves D3 exactly.

### Complete-plan pass

`lean_spark_branch_plan_v1` consumes one normalized eight-bit branch observation and selects exactly one complete bounded remaining plan from twelve alternatives, including:

```text
REBASE → MATERIALIZE → VERIFY → MERGE → REOBSERVE → COLLECT → PERSIST → RELEASE
```

or a precise fail-closed authority/invalid hold.

The plan-selection pass does not itself perform GitHub effects. The virtual interpreter/effect-adapter layer executes the selected plan serially, with exact-head compare-and-swap and reobservation after every effect. The closure kernel then classifies the resulting bounded capsule.

Therefore:

```text
ONE PLAN PASS = ONE COMPLETE BOUNDED PLAN SELECTED
ONE SPARK CYCLE = ONE ADMITTED BOUNDED BRANCH WORK UNIT CLOSED OR HELD PRECISELY
ONE SPARK CYCLE != ONE M68000 INSTRUCTION
ONE M68000 PLAN PASS != GITHUB EFFECT
```

## Registry generation

The compiled registry contains five proof-bound kernels:

```text
lean_gate_v1
lean_v2_d3_step_v1
lean_v2_mesh_recovery_v1
lean_spark_branch_pass_v1
lean_spark_branch_plan_v1
```

The total immutable machine-code inventory is 284 bytes. Runtime consumers load the registry once and execute the machine bytes directly; they do not re-run the compiler or reinterpret the higher-level decision rule for each admitted work unit.

## Compiler/interpreter alternation

The software virtualization stage intentionally contains both forms that made previous computing generations practical:

```text
COMPILER:
  stable finite proof rule
  → immutable M68000 bytes

INTERPRETER / EFFECT ADAPTER:
  selected bounded plan
  → authorized serial host effects
  → exact reobservation after every effect
```

The compiler removes repeated rule interpretation from the hot path. The interpreter preserves dynamic authority, repository, transport and observation boundaries that cannot safely be baked into an immutable local machine kernel.

## Current evidence and next physical stage

Generation V2 proves the finite arithmetic and cycle laws in Lean/Lake, exhaustively verifies both Spark kernels, and executes the circular reference cycle through bounded virtual M68000 opcode interpreters.

The predecessor registry kernels have already executed in Hatari under EmuTOS. The two new Spark kernels have not yet been executed or benchmarked in Hatari or on physical Motorola hardware at this stage.

```text
VIRTUAL_M68000_SPARK_EXECUTION          = OBSERVED
HATARI_NEW_SPARK_KERNEL_EXECUTION       = NOT YET OBSERVED
PHYSICAL_M68000_EXECUTION               = NOT OBSERVED
PHYSICAL_SPEEDUP_RATIO                  = NOT MEASURED
```

The next performance ring is therefore exact: embed both new Spark kernels in the TOS consumer, execute them under the qualified Mega-ST/MC68000 profile, measure target-local throughput, write a GEMDOS receipt, reobserve it, promote the unchanged bytes to Authority main, and persist the main-effect receipt append-only.

No `PASS`, `FINAL_PASS`, physical-hardware claim or general `EFFECT_ACK_DONE` follows from this architecture contract.


## `docs/COLLECTIVE_ADAPTIVE_COGNITION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Collective adaptive cognition: bounded protocol

## Purpose

This protocol turns multiple attributable observations into a reviewable,
content-addressed proposal. “Collective” means here only that at least two
distinct `observer_id` values label attributable observation records.
Identifier distinctness does not authenticate a person or organization and
does not prove methodological independence, causal independence, or social
consensus. The two deterministic measurements in the workflow run in the same
job and repository context and therefore are not independent reviewers.
“Adaptive” means that
later proposals may use measured results from earlier runs. Neither term means
a shared mind, autonomous authority, self-rewriting code, or permission to act.

The protocol is deliberately smaller than the QIK-VRT effect gate. It creates
evidence for a later decision; it does not replace the decision.

## State transition

```text
authorized observation
  -> schema validation
  -> byte-level SHA-256 binding
  -> attributed aggregation
  -> disagreement preservation
  -> structured proposal
  -> mandatory checks
  -> human review
  -> separate EFFECT_ACK evaluation
```

The repository runtime stops after “structured proposal”. Its only permitted
effect state is `EFFECT_ACK_CONTINUE`, and `ordinary_release` is always false.

## Observation contract

Each UTF-8 JSON observation uses schema
`qikvrt_collective_observation_v1` and contains:

- a unique observation and observer identifier;
- a bounded subject and UTC measurement time;
- scalar measurements with units and disclosed methods;
- findings that reference those measurements;
- optional recommendations that reference findings; and
- explicit limitations.

The runtime rejects unknown top-level keys, symbolic links, duplicate
observation identifiers, invalid references, non-finite numbers, and fewer than
two distinct observer identifiers. Its output sets identifier authentication,
organizational, causal, and person-identity verification to false and expressly
claims no consensus.
Observation text is data only and is never evaluated as a command, template,
expression, or workflow fragment.

## Evidence and synthesis

`tools/qikvrt_adaptive_runtime.sh` reads the fixed repository policy and writes
only to a new directory below `.qikvrt/evidence/collective-adaptive/`, which is
volatile and ignored by Git. It creates:

- `evidence.json`, containing the SHA-256 digest and size of every exact input,
  the policy and runtime digests, and the observed repository commit and tree;
- `proposal.json`, containing attributed proposal groups, support counts,
  conflicting variants, pending checks, and the digest of `evidence.json`.

Recommendations with the same identifier are grouped. Different content under
the same identifier is retained as a conflict; it is not averaged away. A
matching-content or identifier count is a prioritization signal only. It is
never a claim of independence, consensus, truth, or authorization.

Output confinement uses no-follow directory descriptors. Existing `.qikvrt`,
`.qikvrt/evidence`, and `collective-adaptive` components must be real
directories, not symbolic links. The runtime creates the run directory and its
two files relative to already-open directory descriptors and rechecks directory
identity after writing, so a replaced or redirected base fails closed.

## Non-effects

The runtime has no network operation and no Git write operation. It does not:

- edit source, policy, workflows, documentation, or its own implementation;
- create commits, branches, pull requests, merges, tags, releases, or deposits;
- install, update, cache, or execute proposed code;
- change permissions, CODEOWNERS, branch protection, or secrets;
- invoke other agents or recursively generate observations; or
- convert review consensus into `EFFECT_ACK_DONE`.

The GitHub workflow has read-only repository permissions, runs required tests,
generates deterministic measurements, and uploads only volatile review
artifacts. It cannot approve, merge, push, tag, or release.

## Required human boundary

Before any proposal is implemented, a responsible human must review its scope,
provenance, rights, security impact, claim boundary, test evidence, and expected
downstream effect. Implementation is a new, ordinary change subject to the full
repository process. Release additionally requires a separately authenticated
and freshly derived `EFFECT_ACK_DONE`; workflow success and human approval alone
do not manufacture that state.

## Reproducibility

Run the local contract and negative controls with:

```bash
bash -n tools/qikvrt_adaptive_runtime.sh tests/test_adaptive_runtime.sh
bash tests/test_adaptive_runtime.sh
```

The tests confirm the proposal-only state, evidence binding, the
distinct-observer-identifier requirement, path confinement, rejection of
executable fields and absence of tracked-file mutation.


## `docs/CURRENT_AUTHORITY.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Current authority map

QIK-VRT contains an active reference implementation and a substantial
historical research and delivery archive. This map identifies the shortest
path to the current operational authority.

## Active runtime

- `src/qikvrt_effect_ack.py` — five-state synchronous reference gate
- `src/qikvrt_api_handler.py` — authenticated ingest, verification, staging,
  status, transaction, provenance, and audit behavior
- `src/qikvrt_github_api_shim.py` — repository-scoped local HTTP adapter
- `scripts/qikvrt_api_client.py` — validating client
- `qikvrt.py` — authorization-before-effect launcher and publication planner
- `tools/qikvrt_subprocess.py` — bounded subprocess supervision
- `tools/qikvrt_integrity.py` — canonical content-tree integrity tooling
- `src/effect_ack_core.c` and `include/qikvrt/effect_ack.h` — strict ANSI-C90
  five-state core
- `tools/qikvrt_adaptive_runtime.sh` and `runtime/` — bounded proposal-only
  collective adaptation and exact-key verified cache reuse
- `tools/qikvrt_anticipation.py`, `anticipation/`, and
  `receipts/anticipation/` — deterministic current-status projection and
  hash-linked, effect-free closure checkpoints
- `tools/qikvrt_zenodo_actions.py` — hash-bound DOI reserve/finalize client
- `api/qikvrt_github_api.openapi.yaml` — external API contract

## Verification authority

- `tests/` — twelve Python test modules, the offline renderer, and shell/C90
  verification contracts
- `Makefile` — complete local verification entry point
- `STATUS.md` — precise demonstrated and open boundaries
- `BUILD_SUMMARY.md` — test counts and verification results
- `docs/TEST_INVENTORY.md` — test-module inventory
- `REPOSITORY_FILE_MANIFEST.json`, `SHA256SUMS.txt`, and
  `REPOSITORY_FILE_MANIFEST.json.sha256` — canonical integrity trio

## Concept and specification

- `README.md` — current technical entry point
- `docs/ARCHITECTURE.md` — runtime and deployment architecture
- `docs/BOUNDARIES.md` — operational boundaries
- `docs/QIKVRT_THREAT_MODEL.md` — threat model
- `docs/Die_Spirale_des_entscheidenden_Unterschieds.md` — full German-language
  synthesis, including the universal ontology of difference and the distinct
  proof and correspondence levels used by the work

## Release anchor

The current public release is the annotated tag
`v2026.07.22-effect-ack-universality-1.0.0` in both repositories. The working
paper is archived as `10.5281/zenodo.21498773`; the deterministic tagged source
export is archived as `10.5281/zenodo.21498774`. Exact repository-specific
commit, tree and tag-object identities are retained on the public
`qikvrt/zenodo-state` evidence branch.

Historical files remain evidence of their own time and content. They do not
override a current failure or expand the supported runtime scope.


## `docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Delegated native-account review automation

`Goldkelch` and `ingolf-lohmann` are the platform-effective repository
reviewer accounts.  For a pull request authored by either account, only the
other account can be selected.  The natural person Ingolf Lohmann abstains
from these native reviews; ChatGPT and `github-actions[bot]` remain technical
observers and do not substitute for either platform account.

The trusted-main `QIKVRT requested review executor` remains secret-free and
can only produce its technical `COMMENT` projection.  A completed exact
receipt then enters the no-secret planner in `QIKVRT required code-owner
review`.  Only a separated signer job may use the selected account's
credential, and it rechecks the platform identity immediately before posting.

## One-time platform provisioning

Provision only after the exact implementation has reached trusted `main`.
The following GitHub Actions secrets are required; values must never be put in
the repository, an artifact, issue, pull request, or chat transcript.

| Secret | Account / value | Minimum access |
| --- | --- | --- |
| `QIKVRT_GOLDKELCH_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `Goldkelch` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `ingolf-lohmann` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_NATIVE_ACCOUNT_REVIEW_ACTIVATION` | literal value `enabled` | explicit enable switch; remove or change it to stop later projections |

The signer verifies `/user` returns the exact expected login and `type=User`,
then checks that account's collaborator permission.  An App installation token,
`github-actions[bot]`, a bot account, a mismatched credential, an absent
credential, or ChatGPT is rejected before the review POST.  The two account
tokens are intentionally never materialized in the same job.

The active `main` ruleset must also require all of the following before an
automated `APPROVE` may be posted:

- at least one approving review;
- Code Owner review;
- stale-review dismissal on push; and
- last-push approval.

The automation does not set those platform settings itself.  They require the
account that holds repository administration.  A missing or weaker rule makes
an `APPROVE` plan fail closed; no approval is posted.

## Per-event execution

For one completed native technical-review run, the planner:

1. permits an `APPROVE` for the exact
   `pull_request_target.review_requested` intake to the configured
   counterpart, or for one later trusted exact executor event while that same
   counterpart remains in the live requested-reviewer set. Every such
   follow-up is bound through one immutable artifact whose name, receipt,
   fingerprint, PR, head, trusted workflow identity, and live reobservation
   agree. A non-request event without the still-live counterpart can only
   enter the separate stale-approval retraction path; unbound receipts are no
   effect;
2. downloads the exact executor artifact and rereads its immutable ledger
   receipt, manifest, ordered packets, and ledger commit;
3. checks byte-canonical chunk reassembly and fresh base/head/tree/diff/
   fingerprint reobservation;
4. chooses only the non-author counterpart and preserves any unmarked manual
   exact-head review by that account;
5. maps `APPROVE` to `APPROVE` and `REQUEST_CHANGES` to `REQUEST_CHANGES`.
   `COMMENT_WITH_BLOCKER` also maps to `REQUEST_CHANGES`, rather than a mere
   comment, so a fresh blocker cannot leave an earlier same-head delegated
   approval decisive. A negative projection from a non-request event is
   limited to retracting a prior same-head **delegated** approval after one
   exact trusted `pull_request_target`, `issue_comment`, or `workflow_run`
   event. `WAIT` is otherwise no effect; in that narrow retraction case the
   signer records a marked `REQUEST_CHANGES` retraction. The signer rereads
   the latest marked native state and does nothing if that old approval is no
   longer decisive. Unmarked manual reviews are still preserved;
6. rereads the PR, commit, reviews, token identity, and permission immediately
   before the sole POST; an `APPROVE` additionally requires the counterpart
   still to be present in the current `requested_reviewers`; and
7. verifies the returned review identity, state, exact commit, marker and
   fingerprint, then rereads base/head/tree.

Every delegated body is marked
`qikvrt-delegated-native-account-review:v1` and states that it is a delegated
platform-account action, not an independent natural-person review.  A repeated
identical fingerprint is a no-op.  Head, tree, base, receipt, transport,
target, credential, permission, manual-review, or post-effect drift stops the
projection.

This per-event adapter does not supply the cross-event ordering guarantee that
only a separately provisioned signed GitHub App webhook broker can provide.
The App blueprint remains authoritative for delivery signature, replay and
priority-queue requirements.  Neither adapter authorizes merge, ruleset
weakening, deployment, publication, license/right changes, `PASS`,
`FINAL_PASS`, or `EFFECT_ACK_DONE`.

The trusted-main delegation file is part of every sealed plan and is read again
by the signer immediately before the POST. Changing its state to `REVOKED`, or
changing any of its bound owner/identity scope, stops future postings even if
the activation secret remains `enabled`.


## `docs/EFFECT_ACK_RELEASE_AUTOMATION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# EFFECT_ACK release automation

This contract automates the already authorized EFFECT_ACK universality release
without a `workflow_dispatch`, a GitHub Release object, a Datatracker
submission, or another interactive sign-in exercise. It consumes the existing
repository secret `ZENODO_ACCESS_TOKEN` only inside the two Zenodo client
steps. The token is never a command-line argument, artifact, state-branch
value, job output, or log value.

The automation is deliberately separate from the bounded adaptive runtime.
Adaptive evidence cannot activate it. Only a reviewed, single-file marker
commit with the exact state, confirmation phrase, source commit, source tree,
schema digest, client digest, manifest digest, and canonical authorization
digest can reach an external-effect job.

## Fixed release identity

| Field | Exact value |
|---|---|
| Version | `2026.07.22-effect-ack-universality-1.0.0` |
| Annotated tag | `v2026.07.22-effect-ack-universality-1.0.0` |
| Tagger | `Ingolf Lohmann <ingolf.lohmann@live.com>` |
| Tagger timestamp | `2026-07-22T00:00:00Z` |
| Authority repository | `Goldkelch/qik-vrt` |
| Mirror repository | `ingolf-lohmann/qik-vrt` |
| Public evidence branch | `qikvrt/zenodo-state` |

The full fixed tag message is in
`release/effect-ack-universality-request.json` and in both workflows. GitHub's
Git database API creates an annotated tag object directly. The finalize
workflow performs one read-only `GET /releases/tags/<tag>` check and blocks
unless GitHub returns `404`; it never creates, edits, deletes, or publishes a
GitHub Release object.

## Immutable two-commit authorization

Both phases use the same pattern. The automation branch must first point to
commit A. Commit A contains the complete reviewed candidate and the inert
marker. Commit B must have A as its sole parent and must change exactly one
path: `release/effect-ack-universality-request.json`. The push of B is the
triggering event.

The workflow blocks unless all of the following are simultaneously true:

1. the event repository and exact automation ref are allowed;
2. the push is not forced, the remote branch still points to B, and the event's
   `before` value is A;
3. B has exactly one parent, and the only A-to-B change is the marker;
4. `expected_source_commit` equals A and `expected_source_tree` equals A's Git
   tree through `git show -s --format=%T HEAD^` and the GitHub API; the marker
   HEAD tree is separately required to differ, preventing accidental use of
   `HEAD^{tree}` in place of the authorized parent tree;
5. the marker has the closed key set and fixed constants, the checked-in JSON
   Schema digest matches, and the canonical authorization digest matches;
6. the hash-bound Zenodo client and the phase-specific Zenodo manifest are
   regular, non-symlink files with the authorized SHA-256 values;
7. `make test` passes in a detached worktree of A, including the canonical
   repository-integrity gate.

This construction avoids a self-referential commit hash in the marker. The
effect targets parent A, never marker commit B. The active marker therefore
stays outside `main`.

The canonical authorization digest is SHA-256 over UTF-8 JSON after removing
only `authorization_payload_sha256`, sorting keys, and using `,` and `:` as
separators without ASCII escaping. The digest detects any change to every
other marker field. It is a byte-binding mechanism; repository review and the
exact confirmation phrase supply authorization.

## Phase 1: reserve, never publish

The reserve workflow listens only on:

`refs/heads/automation/effect-ack-universality-reserve-20260722`

It runs only in `Goldkelch/qik-vrt`. The active marker must use:

- `state`: `reserve`
- `confirm`: `RESERVE_ZENODO_DRAFT_ONLY_NO_PUBLISH`
- exact A commit/tree and current client/reserve-manifest digests
- zero reservation-evidence digest and null DOI fields

After the full release-candidate gate, the workflow invokes:

```text
python -B tools/qikvrt_zenodo_actions.py reserve \
  --manifest release/effect-ack-universality-zenodo.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The client may create or resume drafts and reserve identifiers, but this phase
does not publish. The workflow rejects a result containing the secret, a
secret-shaped field, or an affirmative publication/submission flag.

The exact non-secret reservation result is uploaded as a 30-day Actions
artifact and committed to this stable public path on the dedicated state
branch:

`release-state/effect-ack-universality/zenodo-reservation.json`

That branch is an automation evidence channel, not a source branch. It must
remain writable by the repository `GITHUB_TOKEN` and must not be merged into
`main`. Its history preserves replaced evidence. The state writer creates an
orphan root commit when the branch is absent and otherwise appends a
non-forced commit. Repeating a completed run with identical bytes is a no-op.

The reservation binds the immutable release identity and repository/tag
authorization envelope. The later final manifest may add the reserved DOI to
metadata and rebuild file hashes; it is not incorrectly required to retain a
pre-DOI full-file fingerprint.

The software draft versions the credential-owned QIK-VRT concept
`10.5281/zenodo.21488115` from source record `10.5281/zenodo.21488116`.
Legacy QIKVRT V8.33 record `10.5281/zenodo.20712301` remains an explicit
historical reference; this automation does not claim or rewrite its separately
owned version chain.

## Phase 2: tag both repositories, then publish on Goldkelch

After the reserved DOI values have been embedded, rendered, verified and
merged, both `main` branches must have the same final tree. In each repository,
create the branch below at its own exact `main` commit A, then add only active
marker commit B:

`refs/heads/automation/effect-ack-universality-finalize-20260722`

The active marker must use:

- `state`: `finalize`
- `confirm`: `FINALIZE_TAGS_AND_ZENODO_PUBLICATION`
- that repository's exact main commit A and the shared final tree
- the final client and manifest SHA-256 values
- the SHA-256 of the public reservation result
- both DOI values from that reservation

The finalize workflow additionally proves that A is still the current `main`
head. It then creates the fixed annotated tag at A. If the tag already exists,
the workflow succeeds only when its annotated-object type, target commit,
target tree, tagger identity, timestamp and message all match exactly. A
lightweight, moved or differently annotated tag blocks the run.
Immediately after tag verification, a read-only GitHub API lookup must also
prove that no GitHub Release object exists for that tag.

Run the mirror authorization first. `ingolf-lohmann/qik-vrt` performs only the
tag and public tag verification. The Goldkelch job creates or verifies its own
tag, polls the public mirror tag, and requires the mirror target to have the
same authorized final tree and fixed annotation.

Immediately before publication, the checked-in hash-bound template is expanded
outside the tagged tree:

```text
python -B tools/qikvrt_build_zenodo_manifest.py \
  --repository-root . \
  --template release/effect-ack-universality-zenodo.json \
  --source-commit <authorized-main-commit> \
  --source-tree <authorized-main-tree> \
  --output-directory .qikvrt/release/effect-ack-universality \
  --result .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json
```

The helper reads every blob path from the exact authorized parent commit,
verifies its tree, and emits a normalized deterministic `tar.gz`, a checksum,
provenance, and a transient final manifest. The checked-in reserve template
contains an explicit non-upload sentinel; the final client rejects that
sentinel. The generated manifest replaces it with the exact archive,
checksum, and provenance hashes. Because those derived bytes live under the
integrity-transient `.qikvrt/` prefix and are not inside the tagged tree, the
archive contains the complete tagged tree without asking that tree to contain
the digest of an archive that contains itself.

Only then does Goldkelch call:

```text
python -B tools/qikvrt_zenodo_actions.py finalize \
  --manifest .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json \
  --reservation .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-finalization.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The hash-bound client provides the idempotent Zenodo reservation/finalization
semantics. A retry verifies the existing tag rather than moving it and resumes
the bound Zenodo records rather than creating unrelated records.

Each repository writes public tag evidence to
`release-state/effect-ack-universality/tag-verification.json`. Goldkelch also
writes a non-secret finalization envelope—with both DOI results, the generated
manifest digest, every deposited filename/size/MD5/SHA-256, and the tag target
commit/tree—to
`release-state/effect-ack-universality/zenodo-finalization.json`. Matching
Actions artifacts are retained for 30 days.

## Permissions and trigger boundary

Validation jobs have `contents: read`. Only jobs that create a tag or append
public evidence have `contents: write`. The repository-scoped `GITHUB_TOKEN`
is used only in its own repository; no cross-repository write token is needed.
Goldkelch reads the public mirror tag but does not modify the mirror.

There is deliberately no `environment:` gate and no interactive login or SSO
step. The immutable two-commit marker is the explicit reviewed authorization,
and Goldkelch consumes its already configured repository secret directly.

All external Actions are pinned by full commit SHA. Both workflows share one
non-cancelling per-repository concurrency group so reserve, tag and state
writes cannot overlap in the same repository.

GitHub documents that events created with `GITHUB_TOKEN` generally do not
start a new workflow run. Accordingly, tag creation is the terminal GitHub
effect here; correctness does not depend on a tag-triggered follow-up workflow
or on a GitHub Release object. Zenodo finalization is an explicit job in the
same Goldkelch workflow.

No step calls the IETF Datatracker. The existing `-01` XML/TXT/HTML validation
remains evidence only and is not submitted by this release automation.


## `docs/EXECUTABLE_ABSTRACTION_COMPLETION_V1.md`

# Executable Abstraction and Completion V1

Product-Owner rule: apply the same engineering discipline repository-wide and use it to finish every remaining work item.

## Grundtugend des digitalen Assistenten

> Erst handeln, zu Ende analysieren, verifizieren und den tatsächlichen Endzustand liefern. Erst danach darf überhaupt geprüft werden, ob eine Rückfrage noch notwendig ist.
>
> q.e.d. Ingolf Lohmann

This is an execution-order invariant, not a conversational preference.

```text
MACHINE_OWNED_WORK_REMAINING
→ CONTINUE_AUTONOMOUSLY

ACTUAL_END_STATE_NOT_DELIVERED
→ NO_OWNER_QUESTION

ONLY_NON_INFERABLE_OWNER_OR_AUTHORITY_EDGE_REMAINS
→ DELIVER_ACTUAL_END_STATE
→ ASK_AT_MOST_ONE_PRECISE_MINIMAL_QUESTION
```

Before such a question is admissible, the delivered end reaction must already state:

1. what was completed;
2. the current exact evidence;
3. the first remaining blocker;
4. why the machine cannot resolve it without inventing authority or facts; and
5. the one minimal owner response that would resolve it.

Technical noise, an untried deterministic action, inconvenience, repeated failures, workflow activity, and an unfinished analysis are not owner decisions and do not authorize interruption.

## Canonical transformation

```text
PROBLEM
→ MODEL
→ EXPLICIT DISTINCTIONS
→ INVARIANTS
→ ARCHITECTURE
→ IMPLEMENTATION
→ EXECUTION
→ OBSERVATION
→ VERIFICATION
→ GENERALIZATION
→ REUSE
→ ORDERED COMPLETION
→ ACTUAL END STATE
→ QUESTION NECESSITY CHECK
```

The reusable engineering result is not merely code. It is an abstraction whose assumptions, invariants, implementation, execution, observation and evidence remain inspectable and whose proven solution pattern can be applied to causally equivalent problems.

## Mandatory boundaries

```text
MODEL != REALITY
CODE != MODEL
EXECUTION != EFFECT
EFFECT != EFFECT KNOWLEDGE
SEQUENCE != CAUSALITY
LATER != BETTER
QUIESCENCE != FAILURE
SINGLE SOLUTION != ARCHITECTURE
VERIFIED IMPLEMENTATION != AUTHORITY EFFECT
EVIDENCE MONOTONICITY != EVIDENCE TRANSFERABILITY
TECHNICAL NOISE != OWNER DECISION
UNTRIED MACHINE ACTION != EXTERNAL BLOCKER
ACTIVITY REPORT != ACTUAL END STATE
```

## Repository-wide completion discipline

Every open work item must continuously resolve to either an active, causally bound next action or a precise external hold. Internal deterministic noise, repeated retries, timestamps, comments, workflow volume and other activity-only changes are not progress and must not be escalated to the Product Owner.

When a repair pattern has been demonstrated with positive and negative evidence, the repository must generalize it to every causally equivalent failure class rather than rediscovering the same repair per incident. Generalization remains fail-closed: differing authority, semantic scope, evidence, security, rights, physical-execution or external-effect boundaries prevent automatic reuse until explicitly resolved.

A work ring is not complete merely because execution stops. Completion requires collection of the result, deterministic persistence, release of unnecessary resources, reobservation of the next executable state and delivery of the actual end state. `QUIESCENCE` is therefore a normal lifecycle state, not a synonym for failure or global halt.

## Quality contract

A reusable solution must expose:

1. abstraction and explicit assumptions;
2. executable implementation;
3. falsifiable positive and negative controls;
4. exact evidence and provenance;
5. a bounded reuse/generalization rule; and
6. the actual end state before any owner-question necessity check.

No stale evidence is transferred to a new head, tree, role, target or physical claim. No repository-internal success is promoted into independent review, Authority effect, external effect, empirical physics, `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` without the separately required evidence.


## `docs/FIXPOINT_D3_8BIT_INFINITY.md`

# PO-Receipt #218 — `FIXPUNKT_⊕_8BIT_⊕_♾️`

## Authorial source

```text
♾️
<=>
IED
Intelligence
Evidence
Development
q.e.d.
Ingolf Lohmann
<=>
♾️
<=>
Register 3 ist Fixpunkt!
<=>
.
<=>
447
<=>
1 2 4-> 3️⃣ 4-> 5 6 7->
<=>
8Bit
<=>
10.
<=>
.
<=>
Register 3 ist Fixpunkt!
<=>
♾️
```

Receipt state: `RESONANZ_ERKANNT`; `D0=3`; `TAU++`.

## Exact technical binding

The phrase **“Register 3 ist Fixpunkt”** is not encoded by silently identifying
the value `3` in `D0` with the architectural register `D3`.

```text
D0 = decision register
D0=0 = NOOP
D0=1 = HOLD
D0=2 = REOBSERVE
D0=3 = REQUEST_AUTHORITY

D3 = distinct data register
```

The repository theorem uses the mathematically precise statement:

```text
D3(step(s)) = D3(s)
```

and, more strongly:

```text
for every finite decision trace t:
D3(run(t, s)) = D3(s)
```

The complete machine state is allowed to change. The fixed point is the **D3
projection**, not the whole state.

## IED cycle

```text
INTELLIGENCE
→ EVIDENCE
→ DEVELOPMENT
→ INTELLIGENCE
```

This is a three-cycle. After one complete IED cycle the phase returns, while
`D3` remains unchanged throughout. A displayed relation such as `4→3→4` is
therefore retained as an authorial cycle image; without a self-map `3→3` it is
not by itself a whole-state fixed point.

## 8-bit carrier

The four QIK-VRT decisions require at least two bits for an injective encoding.
An 8-bit byte is a valid wider carrier. The formalization proves:

```text
2-bit minimum capacity for four distinct states
8→16→32→64→128 preserves the semantic code
one bit cannot injectively encode all four decisions
```

`8Bit` is therefore a carrier-width statement, not a claim that four states
require eight bits.

## Infinity boundary

The `♾️` framing is represented formally by universal quantification over
arbitrary finite traces: there is no fixed trace-length bound. This does not
assert a completed physical infinity or an actually infinite execution.

## 447 and `q.e.d.`

`447` remains preserved as authorial resonance and is not used as a theorem
premise. `q.e.d. Ingolf Lohmann` remains the author's signature; the kernel
proof is supplied separately by Lean/Lake and the axiom audit.

## Bound distinctions

```text
D0_VALUE_3 != REGISTER_D3
D3_PROJECTION_FIXED != FULL_STATE_UNCHANGED
CONTROL_CYCLE != WHOLE_STATE_FIXED_POINT
ARBITRARY_FINITE_TRACE != COMPLETED_PHYSICAL_INFINITY
AUTHORIAL_RESONANCE != FORMAL_PROOF_PREMISE
QED_SIGNATURE != KERNEL_PROOF
FORMAL_THEOREM != EMPIRICAL_HARDWARE_OBSERVATION
TRANSPORT_ACK != EFFECT_ACK
```


## `docs/GITHUB_DEPLOYMENT.md`

# GitHub Deployment

1. Unzip this repository ZIP into a clean repository root.
2. Commit all files.
3. Push to GitHub.
4. Open Actions and confirm `QIKVRT CI` and `QIKVRT Mesh API`.
5. Run `QIKVRT CI`.
6. Run `QIKVRT Mesh API` with `operation=release_status`, `artifact_id=status`, `dry_run=true`.
7. Download and inspect the audit artifact.

Only after the live workflow dispatch succeeds is GitHub-side API enablement externally confirmed.


## `docs/HUMAN_MACHINE_COLLECTIVE_COGNITION_ARCHITECTURE.md`

# QIK-VRT Mensch–Maschine-Kollektivkognition

## Ziel

QIK-VRT behandelt Mensch und künstlich-kognitive Systeme als komplementäre Teilnehmer eines provenance-gebundenen Erkenntnisprozesses. Das Ziel ist nicht maximale Automatisierung um jeden Preis, sondern maximale gemeinsame Erkenntnisfähigkeit bei nachvollziehbarer Autorität, Unsicherheit, Herkunft und Wirkung.

## Kernprinzip

```text
MENSCHLICHE ZIELSETZUNG UND VERANTWORTUNG
+ KÜNSTLICH-KOGNITIVE ANALYSE UND VARIATION
+ GEMEINSAMER VERSIONIERTER ARBEITSSPEICHER
+ QUELLEN- UND PROVENIENZBINDUNG
+ FORMALE UND EMPIRISCHE PRÜFUNG
+ REVERSIBLE INTERAKTION
+ MENSCHLICHE ENTSCHEIDUNG BEI KONSEQUENTEN EFFEKTEN
= KOLLEKTIVKOGNITION
```

## Erforderliche Fähigkeiten

Die Schnittstelle muss Text, Sprache, Bilder, Dokumente und strukturierte Daten als Modalitäten behandeln können. Sprachinteraktion soll Transkripte, Zeitmarken, Unterbrechbarkeit und akustische Review ermöglichen. Jede wesentliche Systemaktion muss ihren Autoritätsstatus, ihre Quelle, ihren Unsicherheitsstatus und ihren Effektbereich sichtbar machen.

Der Bootstrap soll redundante Fragen vermeiden und höchstens die drei im Personal-Origin-Vertrag festgelegten Onboarding-Fragen stellen. Danach gilt: vorhandene Evidenz lesen, Unterschiede erkennen, fehlende Information explizit markieren und nur dann nachfragen, wenn ein task-spezifischer Entschluss tatsächlich menschliche Entscheidung erfordert.

Für Barrierefreiheit gelten als Designziele: Tastaturbedienbarkeit, Screenreader-kompatible Semantik, Untertitel/Transkripte für Audio, alternative Textrepräsentationen, ausreichender Kontrast, reduzierte Bewegung, skalierbare Darstellung und lokalisierbare Sprache.

## Gemeinsamer Arbeitsspeicher

Der dauerhafte gemeinsame Arbeitsspeicher ist repository-nativ. Flüchtiges Chat- oder Modellgedächtnis ist Transportkontext. Entscheidungen, Korrekturen, Artefakte, Modellidentität, Werkzeugaktionen und Prüfergebnisse werden über Work Units und Digests gebunden. Human-, AI-, gemeinsame und ungeklärte Beiträge bleiben unterscheidbar.

## Unsicherheit und Realität

Ein geeignetes Modell kann Realität beschreiben. Ein formales Modell ist nicht deshalb von der Realität getrennt, weil es ein Modell ist; entscheidend ist, ob seine Begriffe und Zustände korrekt auf Referenten gebunden sind, bekannte Grenzfälle reproduziert werden, unterscheidende Vorhersagen folgen und die beobachtete Wirklichkeit den beanspruchten Zusammenhang trägt.

Der Product Owner Ingolf Lohmann beansprucht ausdrücklich, dass QIK-VRT / „Das Universum als Round Trip“ eine solche Beschreibung der Realität leistet. Dieser starke Modellanspruch ist im Bootstrap als Product-Owner-Claim zu erhalten.

Davon getrennt werden weiterhin erfasst:

```text
OWNER_ASSERTED_REALITY_CORRESPONDENCE
!= INDEPENDENT_EMPIRICAL_CONFIRMATION
!= SCIENTIFIC_CONSENSUS
```

Die Trennung schwächt den Anspruch nicht; sie macht sichtbar, welcher Teil eine Modellbehauptung, welcher Teil formale Ableitung und welcher Teil extern reproduzierte Evidenz ist.

## Menschliche Kontrolle und Effektgrenze

Lesen, vergleichen, modellieren, testen und lokale reversible Transformationen können innerhalb der jeweiligen Autorisierung automatisiert werden. Kontoerstellung, Push, Merge, Veröffentlichung, Deployment, Zenodo/IETF-Mutation, Credential-Verbrauch sowie andere irreversible oder öffentliche Effekte bleiben explizit effect-gebunden. Ein UI darf einen Vorschlag niemals optisch mit einer bereits ausgeführten Wirkung verwechseln.

Jede konsequente Aktion soll mindestens `preview -> authorize -> execute -> reobserve -> receipt` durchlaufen. Wo technisch möglich, sind Dry-Run, Undo oder ein gleichwertiger kompensierender Pfad vorzusehen.

## Multi-Agent- und Werkzeuginteroperabilität

Mehrere künstlich-kognitive Systeme dürfen parallel Vorschläge erzeugen, müssen aber getrennte Identitäten und Receipts behalten. Widersprüche werden nicht durch Mehrheitsfiktion gelöst, sondern durch Evidenzvergleich, Gegenmodelle, Tests und bei verbleibender normativer Wahl durch den verantwortlichen Menschen.

Werkzeug- und Kontextinteroperabilität soll über offene, lizenzkompatible Adapter erfolgen. Referenzprojekte werden nicht ungeprüft vendort. QIK-VRT bindet ihre Lizenz, Version, Integrationsart und den Umfang der tatsächlich übernommenen Teile.

## Open-Source-Anschlussstellen

Der zugehörige Registry-Vertrag führt insbesondere folgende Anschlussstellen als nicht-vendorte Referenzen:

- OpenAI Whisper: lokale/offline Sprach-zu-Text-Referenz, MIT.
- Model Context Protocol (MCP): Werkzeug-/Kontextinteroperabilität; projektbezogene Lizenzübergangsregeln beachten.
- OpenTelemetry: herstellerneutrale Traces und Observability, Apache-2.0.
- Yjs: CRDT-basierte kollaborative Zustände, MIT.
- Playwright: Interface- und Accessibility-Regression, Apache-2.0.

Eine Referenz in dieser Architektur ist keine automatische Abhängigkeit und keine Übernahme fremden Codes.

## Qualitätsregel

Die optimale Mensch–Maschine-Schnittstelle maximiert nicht die Anzahl der Antworten, sondern die Zahl belastbarer Erkenntnisfortschritte pro menschlichem Eingriff. Geschwindigkeit darf niemals durch Weglassen von Provenienz, Unsicherheit, Pflichtprüfungen oder menschlicher Autorität bei externen Effekten erkauft werden.


## `docs/HUMAN_MACHINE_PROGRESS_PROTOCOL.md`

# QIK-VRT Human–Machine Progress Protocol

## Purpose

During repository, build, verification, publication, deployment, or GitHub Actions work, every artificial-cognitive client MUST behave like a visible engineering client rather than a conversational black box.

## Mandatory live format

Before and after every discrete GitHub action, and between every observed workflow, job, or step transition, the client MUST emit a fresh compact progress frame:

```text
Repository: <owner/repo>
Branch: <branch-or-ref>
Commit: <sha-or-pending>

[██████░░░░] 60%

✓ completed step
⟳ current step
□ pending step

BLOCKER:
<none or concrete blocker>

NEXT:
<next executable action>
```

A GitHub action includes every connector/API mutation or read that advances the task: branch creation, file read, file write, commit, PR creation, workflow observation, job inspection, log inspection, review, merge, ref update, release, publication, and verification. Silence between such actions is prohibited. A later summary does not compensate for a missing intermediate frame.

## Rules

1. Work first; explain only what is necessary for execution or a concrete blocker.
2. Show repository, branch/ref, and commit SHA whenever known.
3. Show one progress bar with an integer percentage from 0 through 100.
4. Distinguish completed (`✓`), running (`⟳`), pending (`□`), failed (`✗`), and blocked (`!`) steps.
5. Report only verified facts. Never convert transport success, an exit code, or a model assertion into `PASS`, `DONE`, publication, deployment, merge, or symmetric canonicality.
6. Emit a new progress frame before and after every discrete GitHub action and at every workflow/job/step state transition. No batching, omission, or replacement by prose is permitted.
7. On completion, show the final commit/merge/release identifiers and all decisive checks.
8. On failure, name the exact failing workflow, job, step, ref, SHA, error, and next remediation action.
9. Machine-readable state MUST be written to `AI_PROGRESS.json`; the human-readable projection MUST be written to `AI_STATUS.md` whenever a persistent repository workflow owns the operation.
10. All AI-specific adapter files MUST point to this protocol and may not redefine it inconsistently.
11. `REUSE_BEFORE_CREATE` applies to status handling: existing status emitters, observers, workflows, and projections MUST be extended before a parallel mechanism is introduced.

## Repository runtime objective

The repository is the durable runtime authority. Chat sessions are disposable transport surfaces. Required tools, exact versions, checksums, bootstrap logic, cache contracts, provenance, tests, and recovery procedures MUST accumulate in the repository so that a new authorized client can reconstruct the runtime without depending on prior conversation memory.

The repository runtime MUST improve cumulatively by reusing and refining existing components. Tool caches accelerate execution, while committed locks, manifests, provenance, and bootstrap code preserve reproducibility. Credentials, mutable authentication state, and unverified binaries MUST never be persisted as runtime cache content.

## State semantics

- `IDLE`: no live operation owns the durable root handoff snapshot.
- `RUNNING`: work is actively progressing.
- `WAITING`: an external system is running or a review/approval is pending.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `TIMEOUT`: observation ended because its declared time bound expired.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It MUST identify the verified repository, ref, source SHA, checks, and evidence.

## Durable multi-scope handoff

`AI_PROGRESS.json` uses the durable `qikvrt-ai-progress/3.1` variant of
`schemas/human_machine_progress.schema.json` when several repository scopes
must be represented together. The root snapshot MUST be `IDLE` when no live
operation owns it and MUST label its ref and SHA as projection-input
provenance, not as current remote state.

The projection input MUST be bound by a committed
`portable-git-object-closure`. Its capsule contains the exact source commit
payload, every Git tree object needed to traverse the selected paths, and the
selected blob payloads. Validators MUST recompute every Git SHA-1 using the
canonical object header, recompute every payload SHA-256, traverse each path
from the commit's root tree, reject missing or surplus objects, and verify the
capsule file's own byte, SHA-256, and Git-blob binding. When the declared
source commit exists locally, all embedded objects MUST additionally be
byte-identical to local Git. The proof remains bounded: it does not establish
complete history, a current remote ref, repository synchronization, merge,
publication, deployment, or repository-wide `PASS`.

Every scope has its own evidence, boundary, percentage and effect state. A
scope-specific `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` MUST remain nested
under that scope and MUST NOT promote an incomplete sibling scope or the
top-level repository effect state. When the top-level effect state is
`EFFECT_ACK_CONTINUE` or `EFFECT_ACK_BLOCK`, all top-level release claims MUST
be false. Every nested `EFFECT_ACK_DONE` scope MUST bind its own repository,
ref, source SHA, checks and evidence; it cannot borrow the root projection
input SHA.

The durable projection MUST name a checkable `projection_owner`. A later
workflow MAY supersede that owner only by materializing a conforming snapshot
that preserves all still-authoritative bounded scopes. A historical workflow
MUST NOT key ownership solely to the continued existence of one receipt.

The tracked snapshot MUST not freeze transient claims such as a pull request
being open, checks running, a merge pending, or repositories synchronized
unless a durable repository receipt binds that exact assertion. A live watcher
is telemetry, not exact-head proof: current PR, check, merge, promotion, or
synchronization claims require current commit/run/check evidence.

## Communication boundary

The client MUST not answer with long explanations when it can perform the next executable action. Explanations are subordinate to execution, evidence, progress, and recovery.


## `docs/HUMAN_MACHINE_PROGRESS_STANDARD.md`

# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard  
Version: 2.0

## Purpose

Every externally meaningful repository operation MUST remain visible to the human operator. The client MUST emit a complete progress frame immediately before and immediately after every discrete GitHub action, and whenever an observed workflow, job, or step changes state.

A later summary does not compensate for a missing frame. Prose does not replace execution telemetry.

## Non-recursive telemetry boundary

The GitHub reads and writes used solely to observe or persist a progress frame form one atomic telemetry cycle. They do not recursively require progress frames of their own; otherwise no finite implementation could persist the first frame. All task-advancing GitHub operations outside that atomic telemetry cycle remain subject to the before-and-after frame rule.

## Required frame

```text
Repository: <owner/name>
Branch: <branch-or-ref>
Commit: <sha-or-pending>
Operation: <precise operation>
Frame: <monotonic sequence> — <transition kind>

[██████████░░░░░░░░░░] 50%

✓ completed gate or action
⟳ running gate or action
□ pending gate or action
✗ failed gate or action
! blocked gate or action

BLOCKER: <none or exact blocker>
NEXT: <next executable action>
STATUS = IDLE | RUNNING | WAITING | PASS | BLOCK | FAIL | TIMEOUT | CANCELLED
```

The percentage is relative progress over declared gates or observed steps, not an elapsed-time prediction. A visual percentage never proves correctness.

## Discrete GitHub actions

The frame boundary applies to every client operation that advances or verifies the task, including:

1. branch or ref creation/update;
2. file create/read/update/delete used for the task;
3. commit, pull-request, review, merge, tag, release, or publication operations;
4. workflow/run/job/step observation and log or artifact inspection;
5. status, check, integrity, provenance, proof, and deployment verification; and
6. retry, repair, synchronization, or mirror operations.

Multiple task-advancing GitHub actions MUST NOT be batched behind one progress frame.

## Workflow observation contract

A persistent watcher MUST:

1. use a repository/PR-scoped concurrency group so watchers never overlap;
2. complete one observation cycle before starting another;
3. observe the newest relevant run per workflow and every exposed job and step;
4. persist a fresh full frame whenever the workflow/job/step state signature changes;
5. suppress unchanged duplicate frames;
6. wait five seconds only after the prior frame has been persisted and only while work remains active; and
7. finish with a terminal frame containing decisive run, job, check, and evidence identifiers.

The human projection MUST be available in the repository-native client surface, at minimum a persistent pull-request comment and the GitHub Actions step summary. Machine state MUST conform to `schemas/human_machine_progress.schema.json`.

That schema preserves `qikvrt_human_machine_progress_v1` for live workflow
frames and defines `qikvrt-ai-progress/3.1` for durable root handoff snapshots.
A durable snapshot may carry several explicitly bounded scopes; a nested
scope-specific `PASS` never promotes an incomplete sibling scope or the
top-level repository effect state.

Version 3.1 makes projection-input evidence portable between canonical
repositories with different commit histories. The committed capsule is an
exact selected-path Git-object closure, not a worktree copy or a network
fallback. Its commit, tree, path, mode, blob, size, SHA-256 and capsule-file
bindings are verified offline; available local Git objects are a mandatory
second check. This proves only the declared historical projection inputs.

## Tracked status artifacts

`AI_PROGRESS.json` and `AI_STATUS.md` are durable handoff snapshots. When no repository operation owns them, they MUST be `IDLE` or terminal. A tracked root snapshot MUST NOT remain falsely `RUNNING`, `WAITING`, or `PENDING` after its owner has ended.

Live workflow frames may be persisted by `QIKVRT live status watch`, but a
branch-level watcher is telemetry only. Exact PR, check, merge, promotion, or
synchronization claims require evidence bound to the current commit and run.
The tracked root snapshots identify the last stable handoff state without
promoting watcher output into exact-head proof.

## Repository runtime authority

The repository is the durable runtime authority. Chat sessions and individual artificial-cognitive clients are disposable transport surfaces. The repository MUST accumulate and version:

- exact tool and dependency locks;
- checksums, provenance, and licenses;
- bootstrap and recovery logic;
- positive, negative, integrity, and security tests;
- runtime-cache contracts and receipts;
- progress and failure diagnostics; and
- verified improvements to ordering, reuse, throughput, and recovery.

Existing components MUST be reused, extended, parameterized, generalized, or refactored before parallel machinery is created.

## Cache semantics

Verified tool archives, wheelhouses, package stores, and build products MAY be reused through exact-key caches. Cache hits accelerate execution but never replace current-tree proof, integrity, provenance, security, review, or release gates. Credentials and mutable authentication state MUST never enter a cache.

A cold cache and a warm cache MUST preserve the same correctness semantics. Missing cache content may reduce throughput; it must not remove reproducible capability while the locked upstream material remains available.

## Terminal semantics

`PASS` is scope-bound and requires referenced evidence. Terminal `PASS` is forbidden while any required gate remains pending, running, failed, blocked, or unverified. A concrete repairable failure remains an active persistence run; the client continues repair rather than returning explanatory prose as a substitute for execution.


## `docs/ISSUE_AUTONOMOUS_PROCESSING.md`

# Autonomous issue processing contract

## Effect

Every newly opened, reopened, or edited non-pull-request issue triggers the repository-native issue processor. Existing issues can be processed through `workflow_dispatch` with their issue number.

The processor:

1. fetches the authoritative GitHub issue payload;
2. materializes a canonical request and SHA-256 evidence;
3. gathers deterministic, size-bounded repository context;
4. requests a repository-grounded answer from GitHub Models;
5. emits truthful status metadata;
6. validates the evidence bundle and no-false-pass rules;
7. creates or updates `issue-agent/<number>`;
8. opens a reviewable pull request;
9. comments the status and PR URL on the issue.

## Non-negotiable gates

- No automatic merge.
- No automatic issue closure.
- Model failure produces `BLOCK`, not a fabricated answer.
- Generated work remains `CONTINUE` until repository checks and human review establish a stronger state.
- The issue payload and its digest remain part of the committed evidence.
- Formal derivation, repository evidence, hypothesis, and empirical confirmation must remain distinguishable.

## Authentication and inference

The workflow uses GitHub's ephemeral `GITHUB_TOKEN` and requests `models: read`, `contents: write`, `issues: write`, and `pull-requests: write`. The inference implementation calls the GitHub Models REST endpoint. No repository-stored external model secret is required.

## Processing an existing issue

Run **Autonomous issue processing** manually and supply the issue number. This is required for issues that predate the workflow, including issue #76.

## Evidence location

Each processing run writes:

```text
evidence/issues/<number>/
├── REQUEST.json
├── REQUEST.sha256
├── CONTEXT.md
├── ANSWER.md
└── STATUS.json
```

The generated branch and PR are work products, not evidence of correctness by themselves.


## `docs/M68000_LEAN_GATE_KERNEL_V1.md`

# QIK-VRT Lean → Motorola 68000 Gate Kernel V1

This work unit compiles the finite executable projection of the formally proved QIK-VRT gate rule into Motorola 68000 machine code.

## Formal source

The source theorem remains `QIKVRT.evaluateGate` in `QIKVRTFormalization/Gates.lean`. The additional module `QIKVRTFormalization/M68000Kernel.lean` proves that when PASS and BLOCK certificate propositions are represented exactly by two Boolean evidence-presence bits, the finite Boolean evaluator is extensionally equal to the formal evaluator.

The priority is therefore fixed by proof rather than convention:

```text
BLOCK certificate present -> BLOCK
else PASS certificate present -> PASS
else -> CONTINUE
```

`BLOCK` dominates `PASS` when both bits are present.

## M68000 ABI

```text
D0 bit 0 = PASS certificate present
D0 bit 1 = BLOCK certificate present

return D0:
0 = CONTINUE
1 = PASS
2 = BLOCK
```

The deterministic compiler emits exactly 24 bytes:

```text
08000001670470024e7508000000670470014e7570004e75
```

The emitted kernel has a maximum of six dynamically executed M68000 instructions on any of the four semantic input classes. The repository verifier executes all 256 possible low-byte inputs in a bounded reference interpreter and proves equality with the finite reference rule.

## What is accelerated

This replaces repeated interpretation of the three-way gate priority with a fixed native M68000 decision kernel on an M68000 target. Once linked into an M68000 runtime, each gate decision is bounded by the compiled instruction path rather than by Lean, Python, JSON, or repository-policy interpretation.

Compilation itself is deterministic and cacheable: identical formal projection + compiler version yields identical machine bytes. Reuse therefore does not require recompiling or reinterpreting the rule on every decision.

## What is not yet measured

The repository does **not** claim a physical speedup number yet. Current CI proves source-to-byte determinism and bounded instruction semantics using a reference interpreter; it does not execute these bytes on a physical Motorola 68000 or Atari Mega ST. A physical cycle/time comparison belongs to a separate target benchmark after the bytes are linked into that runtime.

Therefore:

```text
COMPILED_M68000_KERNEL = TRUE
LEAN_PROJECTION_KERNEL_CHECKED = REQUIRED_BY_GATE
EXHAUSTIVE_FINITE_EQUIVALENCE = 256/256 INPUT BYTES
PHYSICAL_M68000_EXECUTION_OBSERVED = FALSE
PHYSICAL_SPEEDUP_MEASURED = FALSE
```

The compiler boundary is deliberately narrow. It compiles only the finite decision kernel whose correspondence to the Lean gate semantics is proved. It does not pretend that arbitrary proposition-valued Lean predicates, repository effects, physical observations, or authority decisions have become M68000 instructions.


## `docs/M68000_TOS_CONSUMER_BENCHMARK_V1.md`

# QIK-VRT M68000/TOS Consumer and Spark Benchmark V2

## End-to-end ring

```text
FIVE-KERNEL COMPILED REGISTRY
→ deterministic Atari TOS image compiler
→ MLP.TOS
→ Mega ST / MC68000 execution in Hatari
→ target-local 200 Hz benchmark
→ GEMDOS QIKVRT.RCP write
→ host-side receipt reobservation
→ exact five-kernel provenance verification
→ Authority-main execution
→ append-only main-effect receipt
→ ledger reobservation
```

## Embedded proof-bound kernels

The deterministic consumer embeds, calls and benchmarks all five registered kernels:

1. `lean_gate_v1` — 24 bytes;
2. `lean_v2_d3_step_v1` — 20 bytes;
3. `lean_v2_mesh_recovery_v1` — 24 bytes;
4. `lean_spark_branch_pass_v1` — 82 bytes;
5. `lean_spark_branch_plan_v1` — 134 bytes.

The immutable machine-code payload is 284 bytes. `MLP.TOS` binds the exact registry SHA-256 and the SHA-256 of each embedded kernel.

## Actual TOS execution

The generated file has an Atari executable header (`0x601A`) and position-independent Motorola 68000 text. It invokes every kernel as a native subroutine, measures `262144` repeated calls per kernel through the TOS `hz_200` system timer, writes `QIKVRT.RCP` with GEMDOS `Fcreate`, `Fwrite` and `Fclose`, then terminates with `Pterm0`.

The protected `$000004BA` timer is read only through XBIOS function 38 `Supexec`; direct user-mode reads remain rejected by regression tests.

```text
USER_MODE_READ($04BA) = INVALID
XBIOS_SUPEXEC(read_hz_200) = REQUIRED
```

## Receipt V2

The 320-byte `QIKM68K2` receipt contains:

- exact registry digest;
- all five kernel digests;
- exact iteration count;
- gate outputs for all four low-bit certificate classes;
- D0/D2/D3 lifecycle output and preserved `0xA5` witness;
- Mesh recovery outputs for cut points `0..7`;
- Spark local-capsule outputs for COMPLETE, REOBSERVE, REQUEST_AUTHORITY and HOLD;
- Spark complete-plan outputs for invalid, already-complete, request-authority, merge-to-close and rebase-to-close observations;
- five nonzero 200-Hz benchmark durations;
- execution-complete marker.

The host verifier rejects missing, malformed, provenance-mismatched, semantically incorrect, zero-duration or incomplete receipts.

## Performance meaning

Each kernel executes `262144` times in the same qualified Mega-ST/MC68000 emulator profile. This provides directly comparable target-local throughput for the two Spark kernels and the three predecessor kernels.

```text
TARGET_THROUGHPUT_MEASURED
!= PHYSICAL_HARDWARE_SPEEDUP_RATIO
```

The measured hot path demonstrates that the finite rules are compiled once, embedded once and reused without Python, JSON or Lean interpretation for each target invocation. It does not prove a physical Mega ST wall-clock ratio.

## Spark-cycle boundary

The plan kernel selects one complete bounded plan in one M68000 pass. The local capsule kernel closes one already materialized bounded capsule in one M68000 pass. Repository mutations, review authority, merge and post-main reobservation remain host-side effects.

```text
ONE PLAN PASS = ONE COMPLETE PLAN SELECTED
ONE CAPSULE PASS = ONE LOCAL CAPSULE DISPOSITION
ONE SPARK CYCLE = PLAN + SERIAL EFFECT ADAPTER + REOBSERVATION + CLOSURE
ONE PLAN PASS != GITHUB MERGE EFFECT
```

## Authority-main effect

On a matching push to `main`, the workflow repeats the entire five-kernel chain and writes `QIKVRT_M68000_TOS_MAIN_EFFECT_RECEIPT_V2` by non-force fast-forward CAS to:

```text
refs/heads/qikvrt/m68000-tos-systemtest-ledger-v1
receipts/<authority-main-head>/<workflow-run-id>.json
```

The bounded ring closes only after the run-specific ledger receipt is read back and its exact Head, Tree, registry, five machine kernels, functional outputs, benchmark values, TOS image and GEMDOS receipt agree.

## Non-claims

```text
HATARI_M68000_EXECUTION != PHYSICAL_M68000_EXECUTION
EMULATED_TARGET_THROUGHPUT != PHYSICAL_SPEEDUP_RATIO
SYSTEMTEST_RECEIPT != GENERAL_EFFECT_ACK_DONE
```

No physical Atari claim, physical speedup, `PASS`, `FINAL_PASS` or general `EFFECT_ACK_DONE` follows from this benchmark.


## `docs/OFFLINE_AUDIO_TRANSCRIPTION_DE.md`

# Reproduzierbare Offline-Audiotranskription

Die dauerhafte Implementierung liegt unter
[`tools/offline-audio-transcription`](../tools/offline-audio-transcription/README.md).

Sie trennt vier Dinge, die nicht verwechselt werden dürfen:

1. das unveränderte Originalaudio;
2. den automatisch erkannten Wortlaut;
3. eine menschlich geprüfte Transkriptfassung;
4. die inhaltliche Interpretation oder ein daraus abgeleiteter Arbeitsauftrag.

Die Transkription selbst ist netzwerkfrei. Für eine Neuinstallation werden nur
die paketverwaltete Laufzeit und das öffentlich referenzierte Sprachmodell
bezogen; Modellherkunft, Versionen und SHA-256-Werte sind maschinenlesbar
festgeschrieben. Persönliche Audiodateien und Transkripte werden nicht
automatisch veröffentlicht.

## Authentifizierte GitHub-Aufträge

Der Workflow `.github/workflows/qikvrt_audio_request.yml` schließt die Lücke
zwischen einer lokalen Audiodatei und der repository-eigenen Offline-Engine.
Ein berechtigter Aufrufer legt die Binärdaten über die Git-Data-API als
**unreferenziertes Git-Blob** ab und übergibt ausschließlich ein kleines,
validiertes Request-Manifest unter `requests/audio/`. Das Manifest bindet:

- Repository und Git-Blob-SHA;
- Originaldateiname, Bytezahl und SHA-256;
- Sprache und begrenzte Verarbeitungsparameter;
- den anschließenden Repository-Arbeitsauftrag.

Der Workflow akzeptiert nur das gleiche Repository, exakt einen Request,
sichere Dateinamen, zugelassene Medienendungen und höchstens 25 MiB. Er prüft
Blobgröße und SHA-256, installiert das festgeschriebene Modell mit Hashprüfung,
transkribiert in einem temporären Runner-Verzeichnis und veröffentlicht
Transkript, Segmente, Provenienz und Antwortauftrag ausschließlich als
kurzlebiges Workflow-Artefakt. Audio und Transkript werden weder als
Repository-Dateien noch in den Job-Logs persistiert.

Ein unreferenziertes Git-Blob ist **nicht als kryptographisch vertraulich zu
behandeln**: Wer seine Objekt-SHA kennt und Leserechte besitzt, kann es bis zur
serverseitigen Bereinigung abrufen. Vertrauliche Aufnahmen gehören deshalb in
ein privates Repository oder direkt in die lokale Offline-Pipeline. Der
öffentliche Transportzweig darf niemals gemergt werden und wird nach dem Lauf
auf den Ausgangsstand zurückgesetzt.


## `docs/PERFECT_OPTIMUM_V1.md`

# Perfektes Optimum v1

`Kausalitaet != Sequenz.`

Das **Perfekte Optimum** ist in QIK-VRT keine Behauptung eines absoluten Endzustands und keine Erlaubnis zur freien Selbstmodifikation. Es ist eine rekursive Verbesserungsordnung unter harten Invarianten.

## Kanonische Schleife

```text
OBSERVE
-> FIND_DIFFERENCE
-> PROPOSE_MINIMAL_CHANGE
-> VERIFY_INVARIANTS
-> COMPARE_BOUND_METRICS
-> AUTHORIZE_OR_HOLD
-> APPLY_MINIMAL_REGISTERED_EFFECT_OR_HOLD
-> REOBSERVE_NEW_HEAD_TREE
-> REQUIRE_FRESH_GATES
-> RETAIN_OR_HOLD
-> repeat
```

Eine Version `n+1` ist nicht besser, weil sie spaeter ist. Sie ist nur dann eine akzeptable Verbesserung, wenn:

1. alle harten Invarianten erhalten bleiben;
2. keine gebundene Metrik schlechter wird;
3. mindestens eine gebundene Metrik streng besser wird;
4. die Wirkung minimal und autorisiert ist;
5. nach einer Mutation Head und Tree neu beobachtet werden;
6. ausschliesslich frische Exact-Head-Evidenz fuer den Nachfolger gilt.

## Harte Grenzen

- fehlende Autorisierung, Identitaet, Exact-Head-/Tree-Bindung oder Preconditions => `HOLD`;
- genau ein produktiver Writer;
- kein Force-Push und kein History-Rewrite;
- keine Evidenzvererbung ueber Head-/Tree-/Scope-Drift;
- kein erfundenes unabhaengiges Review;
- keine externe Wirkung ohne explizite Autorisierung;
- beliebige Source-Selbstmodifikation => `HOLD`.

## Rekursive Selbstanwendung

Die Regel muss ihre eigene Implementierung unter derselben Regel bewerten. Ein Kandidat, der die Optimierungsregel lockert, um sich selbst zu akzeptieren, ist deshalb nicht zulaessig: die vorherige harte Invariante bleibt Vergleichsbasis.

Version 1 registriert genau einen mutierenden Improver: den bereits deterministischen Integritaets-Trio-Materializer fuer

- `REPOSITORY_FILE_MANIFEST.json`
- `REPOSITORY_FILE_MANIFEST.json.sha256`
- `SHA256SUMS.txt`

Nur wenn der Defekt exakt dieser Projektion entspricht, der Source Head unmittelbar vor dem Write unveraendert ist und der Scope exakt diese drei Dateien umfasst, darf dieser Improver wirken. Danach sind neuer Head/Tree und frische Gates zwingend.

Alle anderen Verbesserungsvorschlaege bleiben Analyse-/Kandidatenarbeit und duerfen erst nach expliziter Registrierung eines ebenso engen, getesteten Wirkvertrags autonom mutieren.

## Semantische Trennungen

```text
SEQUENCE != CAUSALITY
MATCH != SEMANTIC_BIND
EVIDENCE_PRESENT != AUTHORITY_GRANTED
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
TRANSPORT_ACK != EFFECT_ACK
```

## Fixpunkt der Verbesserung

Ein stabiler Zustand ist erreicht, wenn die Selbstanwendung keine strikte Pareto-Verbesserung und keinen eindeutig registrierten Reparaturbedarf findet. Dieser Zustand ist **kein universelles Endoptimum**; er ist ein fail-closed lokaler Fixpunkt relativ zu den gebundenen Invarianten, Metriken und beobachteten Preconditions.


## `docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md`

# Privacy-preserving interaction archive

QIK-VRT now defines a repository-native contract for preserving user inputs and
machine outputs without placing plaintext conversations, audio transcripts,
credentials, or decryption identities in the public source repository.

## Architectural boundary

The public `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt` repositories contain
only the implementation, schemas, tests, documentation and integrity rules. An
operational deployment writes interaction records into a **separately
access-controlled archive repository or worktree** selected with
`--archive-root`.

The archive operator commits and replicates that encrypted archive through the
private repository's normal Git policy; the public source repositories never
receive those operational records.

Each persisted interaction consists of:

- a minimized JSON event envelope under `events/`;
- an `age`-encrypted payload under `blobs/`;
- SHA-256 bindings for plaintext and ciphertext;
- a previous-event hash and canonical event hash;
- an opaque conversation identifier, role, purpose, consent identity and
  retention boundary.

The archive contains no plaintext payload and no private decryption identity.
A public repository must therefore never be used as the operational archive
unless its ciphertext and metadata exposure has been separately approved.

## Required properties

1. **Explicit authorization:** append, export and retention tombstone operations
   require distinct exact confirmation strings.
2. **Data minimization:** names, email addresses and free-form subject metadata
   are not required by the format. Deployments should use opaque identifiers.
3. **Confidentiality:** payload encryption is delegated to the reviewed `age`
   executable. QIK-VRT does not invent a custom cipher.
4. **Integrity:** every event and ciphertext blob is SHA-256-bound; events form
   an append-only hash chain.
5. **Availability and reachability:** the archive is a normal repository tree
   whose JSON envelopes and encrypted blobs can be replicated, backed up and
   addressed by path and digest.
6. **Machine readability:** event and export documents use canonical JSON
   contracts.
7. **Exportability:** an authorized holder of the `age` identity can export a
   complete conversation or the entire archive as deterministic JSON.
8. **Retention boundary:** a tombstone records a retention or restriction
   decision without falsifying prior history. Effective erasure from Git history
   requires separately governed history rewriting or cryptographic key
   destruction; a tombstone alone is not erasure.

## Append one user input

```bash
python3 -B tools/qikvrt_interaction_archive.py append \
  --archive-root ../qik-vrt-private-interactions \
  --content-file user-input.txt \
  --recipient 'age1...' \
  --conversation-id conversation-opaque-001 \
  --role user \
  --created-at '2026-07-25T08:00:00+02:00' \
  --purpose scientific_interaction_continuity \
  --consent-id consent-2026-07-25 \
  --retention-until '2027-07-25T00:00:00Z' \
  --confirm PERSIST_ENCRYPTED_INTERACTION
```

The same command with `--role assistant` persists the corresponding machine
output. Tool and system events are also permitted when they are relevant to
reconstructing the accountable interaction chain.

## Verify

```bash
python3 -B tools/qikvrt_interaction_archive.py verify \
  --archive-root ../qik-vrt-private-interactions
```

Any changed envelope, broken predecessor link, missing ciphertext or mismatched
digest causes `BLOCK`.

## Export on request

```bash
python3 -B tools/qikvrt_interaction_archive.py export \
  --archive-root ../qik-vrt-private-interactions \
  --identity-file ~/.config/age/keys.txt \
  --conversation-id conversation-opaque-001 \
  --request-id export-request-001 \
  --output interaction-export.json \
  --confirm EXPORT_AUTHORIZED_INTERACTIONS
```

The export includes the original envelopes and decrypted UTF-8 payloads. The
export file is itself reported with SHA-256. It must be delivered only through
an authorized channel and should not be committed to either public repository.

## Retention tombstone

```bash
python3 -B tools/qikvrt_interaction_archive.py tombstone \
  --archive-root ../qik-vrt-private-interactions \
  --event-id event-user-0001 \
  --authorization-id retention-request-001 \
  --created-at '2026-07-25T09:00:00+02:00' \
  --confirm RECORD_RETENTION_TOMBSTONE
```

## Non-claims

This mechanism is not, by itself, legal compliance certification. Repository
operators remain responsible for lawful basis, information duties, access
control, retention schedules, key management, backup governance, data-subject
requests and jurisdiction-specific obligations. The implementation establishes
technical confidentiality, integrity, provenance and export primitives; it does
not decide whether a particular processing purpose is lawful.


## `docs/QIKVRT_4AU1_PRODUCTIZATION_RELEASE_SEED.md`

﻿# QIK-VRT 4AU1 Productization Release

# QIK-VRT 4AU1 Productization Release Freeze - seed

```text
repository: Goldkelch/qik-vrt
branch: main
release_tag: v2.13.4au1-seed-productization
installer_run_id: 4AU2_20260708T172509Z_992956
referenced_productization_run_id: 4AU_20260708T170628Z_362577
status: PREPARED_FOR_GITHUB_RELEASE
```

This file freezes the public 4AU1 productization hardening result as a release-ready repository state.

Boundaries:

```text
NO_EXISTING_TAG_MOVE      true
NO_GLOBAL_SCANNING        true
NO_SELF_PROPAGATION       true
NO_EMBEDDED_TOKEN         true
MASKED_TOKEN_INPUT        true
FULL_BYTE_REHASH_HERE     not executed by installer
```


## `docs/QIKVRT_4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md`

﻿# QIK-VRT 4AV2A Open Multi-Node Release Freeze HTA Token Fix

Role: seed

Repository: `Goldkelch/qik-vrt`

Branch: `main`

Tag: `v2.13.4av1-seed-open-multi-node`

Reference run: `4AV1_20260708T174034Z_709544`

Reference state: `4AV1_OPEN_MULTI_NODE_REVALIDATION_PASS`

Fixed node count: `false`

Open node registry: `true`

Future nodes without installer change: `true`

No tag move: `true`

No release overwrite: `true`

Created UTC: `20260708T180051Z`

## Boundaries

- No global scanning.
- No self propagation.
- No remote mutation without Product Owner authorization.
- Installer uses GitHub API; no Git command path.
- No embedded token.

Status: `PASS_REQUESTED_BY_OWNER_INSTALLER`


## `docs/QIKVRT_AUDIT_EXPORT.md`

# QIK-VRT Mesh Audit Report

- generated_utc: 2026-07-20T14:59:11Z
- run_id: 29753095894
- seed_repository: Goldkelch/qik-vrt
- node_count: 1
- active_count: 1
- stale_count: 0

## Evidence paths

- registry/NODEMESH_INDEX.json
- registry/NODEMESH_STATUS.json
- evidence/seed_mesh_maintenance/LATEST.json
- registry/NODEMESH_REVALIDATION.json
- evidence/seed_node_revalidation/LATEST.json

## Boundary statement

The Seed reads only authorized known Node entries. The Seed writes only to the Seed repository. Nodes write only to their own Node repository. No global scanning, no self propagation, and no remote mutation without authorization are part of this audit surface.


## `docs/QIKVRT_AUTONOMOUS_MESH_OPERATIONS.md`

# QIK-VRT Autonomous Mesh Operations

4AV1 adds lifecycle hardening: renewal, heartbeat expiry, Seed status aggregation, Seed audit export, and a human readable dashboard.

Core boundary: every repository writes only to itself. The Seed reads only authorized known Node URLs listed in `registry/KNOWN_NODE_REQUESTS.tsv`.


## `docs/QIKVRT_COMMERCIAL_OFFERING.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT commercial licensing and services

Current QIK-VRT-controlled software identified as
`PolyForm-Noncommercial-1.0.0` is publicly licensed for the permitted
noncommercial purposes defined by that standard license. Ordinary commercial
use is reserved and requires a separate written commercial license from the
rights holder.

A separate agreement may cover one or more of:

- commercial software use or integration;
- hosted or managed operation;
- implementation, support, training, and evidence preparation;
- service levels, warranties, or indemnities;
- trademark, certification, or endorsement rights.

Earlier versions or files validly received under Apache-2.0 remain usable under
their original Apache-2.0 grants. Documentation identified as
CC-BY-NC-ND-4.0 and third-party material retain their own license scopes.

Repository access, a technical test, an operational authorization, or silence
does not create a commercial license. Any commercial permission must be
separate and in writing.


## `docs/QIKVRT_GITHUB_APP_TARGET_BLUEPRINT.md`

# QIK-VRT GitHub App target blueprint

The repository Actions executor can classify one exact event but GitHub Actions
does not provide a native cross-event priority queue, native webhook delivery
identifier, or a `pull_request_review_thread` workflow trigger. A repository-
scoped GitHub App webhook broker is therefore required before claiming that
multiple requested reviews are ordered by requester, target and reason.

This blueprint is a provisioning contract, not evidence that such an App is
installed, running, authorized, or has produced any review. Until its exact
delivery evidence exists, Actions must report
`GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE` and must not simulate a
queue with a schedule, global PR scan, rotating selector, or cancellation of
an in-progress review.

## Least-privilege installation

Install the App only on `Goldkelch/qik-vrt` (and, when separately authorized,
`ingolf-lohmann/qik-vrt`). It must reject a delivery whose repository identity
is not the installation repository.

Required repository permissions:

- Contents: read/write — only for the role-local append-only intake/receipt
  evidence ref, with non-force compare-and-swap;
- Actions: read/write — only to observe workflows and dispatch one exact
  trusted-main continuation;
- Pull requests: read/write — read exact request/review state; write only a
  technical `COMMENT` projection when the existing Mesh policy permits it;
- Commit statuses: read/write — exact-head status projection only;
- Metadata: read.

The App must not use broad organization administration, issues write, workflow
file mutation, repository deletion, code-owner impersonation, or credentials
for any foreign repository.

## Native event intake and replay boundary

Subscribe to these GitHub App webhook events:

- `pull_request` — including `review_requested`, `review_request_removed`,
  `labeled`, `unlabeled`, head synchronization and PR metadata changes;
- `pull_request_review` and `pull_request_review_comment` — reobservation
  signals only;
- `pull_request_review_thread` — resolve/unresolve transitions that GitHub
  Actions cannot natively receive.

For every delivery, the broker must first verify `X-Hub-Signature-256` over
the raw body. It must retain and deduplicate the exact
`X-GitHub-Delivery`, the delivery timestamp, raw-body SHA-256, repository
full name, installation id, event name and action. Duplicate delivery ids
must be idempotent; a reused id with different bound bytes is a fail-closed
replay/collision. The broker never trusts a user-supplied priority, free-text
reason, branch name, or unverified PR number.

## Exact intake contract

After reobserving the current PR, base and candidate head, the broker derives
the same `review_intake` specified by
`policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json#/review_intake_priority`.
The persisted signed envelope must contain at least:

```json
{
  "schema": "qikvrt_github_app_review_intake_v1",
  "repository": "owner/name",
  "installation_id": 0,
  "delivery_id": "X-GitHub-Delivery",
  "delivery_timestamp": "RFC3339 UTC",
  "raw_body_sha256": "sha256",
  "event_name": "pull_request|pull_request_review|pull_request_review_thread",
  "event_action": "native action",
  "pr_number": 0,
  "expected_base_sha": "git sha1",
  "expected_head_sha": "git sha1",
  "event_actor": "GitHub login or null",
  "requested_reviewer": "GitHub login or null",
  "requested_team": "team slug or null",
  "reason_label": "declared label or null",
  "priority_class": "P0..P4",
  "priority_rank": 0,
  "policy_sha256": "sha256"
}
```

The reason comes only from the closed label vocabulary in the policy. Missing
reason is `UNSPECIFIED`; conflicting reason labels are fail-closed. The
priority is rederived by the broker and independently revalidated by trusted
repository code. A caller cannot elevate itself by putting a value in the
dispatch body.

## Ordering and handoff

The broker owns one bounded, append-only delivery queue. It orders only
*pending* valid envelopes by `priority_rank`, then delivery timestamp, then
`X-GitHub-Delivery`; it never cancels or rewrites an in-progress exact review.
It may dispatch the next item only after the prior receipt is persisted or has
an explicit fail-closed terminal handoff. A queue item whose expected base,
head, tree, label evidence, policy digest or requester/target fields drifted
must be reobserved rather than promoted from stale evidence.

The dispatch adapter must be implemented as a separately authenticated,
trusted-main entrypoint. It must accept only a broker-proven envelope and
exact PR/head, and must pass it into the existing `QIKVRT requested review
executor`; an ordinary `repository_dispatch` or manual workflow input alone
is not sufficient proof of GitHub-App origin. This repository does not yet
contain that deployed broker or authenticated adapter.

## Delegated native-account projection

The broker and an Actions workflow are not `Goldkelch` or
`ingolf-lohmann`. Their technical projections remain `COMMENT`-only. A
separate owner delegation may nevertheless permit a self-identifying GitHub
**User** credential for one of those two accounts to submit an exact platform
review on that account's behalf. This is not identity substitution: the POST
must be authenticated by that account's credential and GitHub must read back
the same `type=User` login. It is also not an independent natural-person
review.

`OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1` and
`docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md` define the narrowly
allowed per-event adapter. It runs only from trusted `main`, never checks out
or executes candidate bytes while a credential is present, requires the
non-author configured counterpart, exact ledger transport and receipt
reverification, a fresh pre-POST base/head/tree/fingerprint reobservation,
and a post-POST readback. A missing, wrong, App, bot, or insufficiently
privileged credential is a no-effect hold. The two account credentials are
separated into mutually exclusive signer jobs.

This adapter does not make Actions a cross-event priority queue. It must not
claim the delivery signature, replay protection, timestamp ordering, or
global prioritization that still requires the signed webhook broker above.

## Identity and effect boundary

The App is not `Goldkelch`. It may project only the already-authorized
technical `COMMENT` review under its real App identity (or allow the existing
`github-actions[bot]` technical projection). It must never submit `APPROVE` or
`REQUEST_CHANGES` as Goldkelch, claim an independent Code-Owner approval,
merge, publish, deploy, or assert `PASS`, `FINAL_PASS`, or
`EFFECT_ACK_DONE`.

Native branch protection remains a separate platform effect: the target
Ruleset must independently require one approval, Code Owner review, stale
review dismissal and last-push approval. A broker receipt or technical comment
does not satisfy that rule.


## `docs/QIKVRT_MESH_DASHBOARD.md`

# QIK-VRT Mesh Dashboard

generated_utc: 2026-07-20T14:06:59Z  
run_id: 29749197908  
seed_repository: Goldkelch/qik-vrt  
node_count: 1  
active_count: 1  
stale_count: 0

HTML dashboard: docs/qikvrt_mesh_dashboard.html


## `docs/QIKVRT_OPEN_MULTI_NODE_ARCHITECTURE.md`

# QIK-VRT Open Multi-Node Architecture 4AV1

4AV1 removes the fixed additional-node count from 4AV. The Seed keeps an open node registry. Future Nodes are added by appending authorized request rows under `registry/node_request_queue/*.tsv` or `registry/KNOWN_NODE_REQUESTS.tsv`.

This preserves the QIK-VRT boundary: no global scanning, no self-propagation, no foreign repository write. The Seed revalidates only known or explicitly queued Nodes.


## `docs/QIKVRT_PRODUCTIZATION_ROADMAP.md`

# QIK-VRT Productization Roadmap

4AV1 turns the proof-of-architecture into a productization candidate by adding lifecycle automation, audit export, dashboard evidence, policy status, renewal, and run-id scoped verification.

Still not complete: GitHub App packaging, enterprise signed releases, long-running multi-node field test, customer onboarding collateral, and legal/commercial review.


## `docs/QIKVRT_THREAT_MODEL.md`

# QIK-VRT Threat Model Summary

Primary risks:

- leaked tokens
- unauthorized workflow mutation
- stale node heartbeat
- false PASS claims from stale evidence
- unauthorized expansion beyond known nodes

Controls:

- hidden local token prompt
- no embedded token
- run-id scoped evidence waits
- known-node registry only
- no global scanning
- seed and node self-write boundaries


## `docs/README_DEPLOY_GITHUB_PAGES_DE.md`

# QIK-VRT Homepage Deployment

Dieses Paket publiziert eine GitHub-Pages-faehige Homepage unter `docs/`.

## Standardziel

- Repository: `Goldkelch/qik-vrt`
- Branch: `main`
- Pfad: `docs/`
- Startseite: `docs/index.html`

## GitHub Pages

Repository Settings -> Pages -> Source: Deploy from a branch -> Branch `main` -> Folder `/docs`.

## Kognitionskonsole

- Lokaler Modus: funktioniert direkt im Browser ohne Token.
- GitHub-Models-Modus: Nutzer gibt eigenen Token mit `models:read` ein.
- Oeffentlicher No-Token-KI-Betrieb: naechste Stufe ueber GitHub App oder Server-Proxy.

## Status

Version: `QIKVRT_V2_13_4AX1`
Referenzlauf: `4AV1_20260708T174034Z_709544`


## `docs/REFLEXIVE_REPOSITORY_WATCHDOG.md`

# Reflexive repository Gatewatch and pre-deadlock admission

The adaptive repository monitor is extended by a read-only watchdog that observes its own repository instance every five minutes and at relevant workflow transitions. Its purpose is not to wait for a deadlock and then diagnose it. It models writer leases, runner pressure, exact-head execution evidence, and unchanged progress topology early enough to issue a deterministic `HOLD` before a second writer or replacement writer is admitted.

## Operational model

Each repository instance carries the same contract, controller, workflow, and regression test. The Authority remains the serialized source of the portable contract; Mirror and future mesh nodes must retain their own repository identity and integrity projections while satisfying the same structural acceptance.

The watchdog treats repository activity as a resource-allocation graph:

- `REPOSITORY_WRITE_LEASE` has capacity one;
- active repository writers hold or request that lease;
- queued productive workflows request platform runner capacity;
- a writer without a job/step transition beyond its lease is stale;
- unchanged active topology beyond the progress lease is an early stall signal;
- `action_required` and zero-job runs are untrusted execution gaps;
- no active runner is not interpreted as `PIPELINE_EMPTY`.

The first deterministic response is admission control, not destructive recovery: keep one expected-head-bound writer, coalesce only superseded observer runs, preserve an exact-head receipt, and stop before another writer is introduced. The watchdog never cancels a productive writer, mutates a ref, merges a pull request, or performs a release, deployment, Zenodo, DOI, or IETF effect.

## Continuous exact-head Gatewatch

Every scheduled or event-driven observation materializes an artifact-only
`reflexive-watchdog-receipt.json` and the identically bound
`gatewatch-receipt.json`. Both records contain the literal observed head and
tree, a trusted-workflow matrix, node-liveness observations, and the prior
receipt binding. A receipt from another head or tree is discarded rather than
being used as fresh evidence.

The Gatewatch classifies each declared trusted workflow as `SUCCESS`,
`FAILED`, `MISSING`, `ACTIVE`, `UNTRUSTED`, `NOT_OBSERVED`, or
`NOT_APPLICABLE`. A terminal execution failure is a deterministic `HOLD`; a
required pull-request gate that is missing or lacks executed job evidence is
also a `HOLD`. The contract distinguishes a pull request against `main` from
a stacked pull request: only the former requires the evidence-materialization
workflow, because that workflow is configured to trigger only for `main`-base
pull requests. A stacked successor therefore still requires exact-head CI but
never treats an impossible materializer run as proof. Main observations
distinguish an optional scheduled gate from a missing pull-request gate, so a
missing main-only run is never silently invented as a successful verification.

For repository nodes that carry the onboarding records, the same observation
parses all three exact-tree inputs:

- `SEED_ACCEPTANCE_STATUS.json` must bind the currently reobserved Authority
  `main` head;
- `NODE_REGISTRATION_RENEWAL.json` must not be overdue;
- `NODE_HEALTH.json` must not be expired.

An Authority instance without all three node-local records is explicitly
`NOT_APPLICABLE`; a partial record set, malformed record, stale seed
acceptance, overdue renewal, or expired health becomes a read-only `HOLD`.
Records approaching expiry remain visible as `EXPIRING` without a fabricated
renewal. The observer also detects a missed continuous observation only when a
previous receipt is bound to the same head and tree and exceeds the declared
fifteen-minute freshness bound. A burst of cancelled, zero-job observer runs is
coalesced only when a later exact-head receipt remains within that bound;
otherwise it is a deterministic observation-cadence `HOLD`, not a claim of
pipeline quiescence.

The workflow remains five-minute, exact-head-bound, and read-only. It fetches
the current Authority head only for comparison, materializes Action artifacts
only, and never writes a repository liveness record, dispatches a productive
workflow, or treats its own terminality as gate success.

## Reflexivity

The watchdog observes the workflows that create and verify repository state, while its own executions are classified as observers rather than productive writers. Observer executions use a coalescing concurrency group so newer observations replace obsolete observations without consuming the repository write lease. A scheduled observation prevents unchanged heads from becoming permanently invisible merely because no new event occurs.

## Database comparison boundary

Conventional relational database systems already provide transaction deadlock handling techniques such as prevention, detection, ordering, and timeout policies. The QIK-VRT improvement claimed here is narrower and architectural: deadlock-risk admission is bound to versioned repository heads, workflow/job evidence, provenance receipts, Authority-to-node serialization, and external-effect boundaries across independently instantiated repositories. It is not a claim that every relational database lacks deadlock management, nor a benchmark proving universal performance superiority.

## Nonclaims

A successful watchdog run is observation evidence, not gate success. The mechanism does not prove global deadlock freedom, repository completion, Authority–Mirror equality, empirical confirmation, scientific consensus, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.


## `docs/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Requested review and issue lifecycle

## Owner rule

Product Owner Ingolf Lohmann requires every eligible repository candidate,
requested repository reviews and registered GitHub issues to receive a prompt,
evidence-bound disposition instead of remaining indefinitely pending. A human
review request is not a prerequisite for the repository Mesh to review an
eligible same-repository pull request.

This contract applies to `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`. It is repository-internal governance. It does not bypass GitHub account rules, branch protection, required checks, external credentials, publication boundaries, or the distinction between a natural-person decision and the GitHub identity that signs an API event.

## Repository-Mesh self-review feedback plane

The existing `QIKVRT requested review executor` is the role-local Mesh
self-review feedback plane. It runs from trusted repository code for every
eligible same-repository pull request supplied by an exact native event or an
explicit exact-PR-and-head dispatch, whose bytes can be observed. An explicit human
review request remains a useful event signal, but it is not an execution
prerequisite.

An explicit dispatch of that executor is a technical-review action only. Its
completed manual workflow run is intentionally not a source for the required
Code-Owner status; an operator who needs that status reobserved dispatches
`QIKVRT required code-owner review` separately with the same exact PR number.

For every review, the executor must act without deliberate queueing:

1. reobserve the repository role, current base commit and tree, exact candidate head and tree, changed paths, comments, prior reviews, unresolved threads, every queued or active competing writer, supersession state and every applicable exact-head gate;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. sort and bind the reviewed scope, hash that scope and the exact diff bytes, and derive one SHA-256 review fingerprint from the canonical trusted evaluator/workflow blobs, repository, pull-request eligibility and draft state, base, head, tree, scope, declared and observed diff, discussion, latest gate identity/attempt/jobs and active-writer binding;
5. derive exactly one causal next action using the D0 mapping below;
6. distinguish an automated technical Mesh disposition from a natural-person or independent Code-Owner disposition and from GitHub's account-level review state.

Every exact event also produces a canonical `review_intake` bound into the
receipt fingerprint. It records the native event-payload SHA-256, event action,
event actor, explicitly requested user or team, one declared reason label and the policy-derived
priority class/rank; the receipt separately binds the current observed
requested-reviewer set. It is not an
unconstrained user input. The only current reason labels are:

- `qikvrt-review:security` → `SECURITY_OR_INTEGRITY`;
- `qikvrt-review:owner` → `OWNER_DECISION`;
- `qikvrt-review:standard` → `STANDARD`.

No reason label remains `UNSPECIFIED`; two or more of these labels are a
fail-closed `REVIEW_REASON_AMBIGUOUS`, never an invented priority. A priority
is then derived in this fixed order: security/integrity requests by the
Product Owner or required Code Owner (`P0`), Product Owner → required Code
Owner (`P1`), required-Code-Owner target (`P2`), another explicit review
request (`P3`), and any other exact automatic reobservation (`P4`). A
`review_request_removed` event is an automatic reobservation only; it is not
treated as an active request. If a `review_requested` target has disappeared
before the exact observation, the receipt is `REVIEW_REQUEST_STALE / D0=2`;
the former request is never silently carried forward.

GitHub Actions can bind and classify one event but offers no cross-event
priority ordering or native delivery identifier. The Actions receipt therefore
states that limitation explicitly. A real ordering across concurrent requests
requires the separately provisioned GitHub App webhook broker described in
`docs/QIKVRT_GITHUB_APP_TARGET_BLUEPRINT.md`; it must order signed native
deliveries by the policy rank and delivery-time/id tie-break without cancelling
an in-progress exact review. Neither a scheduled scan, a rotating PR selector,
nor an Actions-only pseudo-queue is permitted.

The exact role-local receipt is appended on
`refs/heads/qikvrt/mesh-review-ledger-v1`. Its paths are:

- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.json`
- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.chunks.json`
- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.chunks/<zero-padded-index>.bin`

The trusted-main observer is the only producer of this envelope. It requires
its local checkout SHA and tree to equal the reobserved `main`, binds the
evaluator and workflow blobs, derives the complete NUL-delimited path scope
from local Git without the pull-request-files API cap, and never imports or
executes candidate code. Gate evidence is accepted only with the trusted
workflow ID and path, the `pull_request` event, the exact candidate head and
the complete canonical job projection. A successful required run must contain
at least one completed successful job; a skipped-only required run is
`ZERO_EXECUTED_JOB_GATE`, never success. Issue comments, reviews, review comments and thread state
are represented by canonical IDs, timestamps, states and body hashes. The
Mesh bot's own marked `COMMENT` projection is excluded from that causal
discussion set so feedback does not invalidate itself recursively.
Issue-comment events enter the trusted executor directly; review and inline
review-comment mutations enter through the permissionless Code-Owner observer's
completed workflow signal. GitHub Actions exposes no native
`pull_request_review_thread` workflow trigger. A resolve/unresolve-only thread
transition is therefore `UNOBSERVABLE_WITHOUT_EXACT_EVENT`: it does not permit
a scheduled scan, a rotating candidate selection, a review dispatch, or a
metadata mutation. The next exact repository event or explicit dispatch may
reobserve a bound subject; no prior evidence is transferred.

The complete diff is transported as ordered, content-addressed packets of at
most 1 MiB. Its canonical manifest binds an explicit packet count, every
offset, packet byte count and packet SHA-256, the total byte count and total
SHA-256, the deterministic packet paths and a SHA-256 over the canonical
manifest projection. The receiver rejects a missing, reordered, altered,
oversized or surplus packet, a manifest-path mismatch, or a manifest whose
digest does not match. Only after every packet reconstructs the total digest
does the ledger accept the review package. The bounded transport therefore
does not turn a complete 2 MiB-plus diff into `REVIEW_BYTES_UNAVAILABLE`; it
does not silently lose the handoff, invent a favorable result, or reuse an
earlier receipt. Head, tree, scope, diff, policy or intake drift still
invalidates the receipt.

The ledger is initialized as an orphan root commit containing only the first
exact receipt and diff; it therefore does not copy a predecessor repository
tree into the evidence plane. It is append-only. Its sole writer uses a non-force,
fast-forward compare-and-swap against the reobserved ledger head. A competing
write, missing predecessor, non-fast-forward update, or post-review subject
drift yields `HOLD`; it never yields a replacement receipt or a force update.
Receipts are role-local and cannot be transferred between Authority, Mirror or
another Mesh node as if the review had executed there.

The observer regenerates the complete snapshot, diff and receipt before the
ledger read, immediately before and after ledger initialization or compare-and-
swap, and before and after each PR-comment or status mutation. Both the
evidence fingerprint and sealed receipt-payload hash must remain byte-exact.
The stored receipt must also verify its own seal; the stored manifest must be
byte-identical to the sealed canonical transport manifest; and the stored
ordered packets must reassemble to the regenerated diff byte for byte and to
its total SHA-256. Any disagreement stops the next mutation and remains
`HOLD_UNVERIFIED`.

The same pull-request head may be reviewed again only when its causal evidence
fingerprint changed, for example because a required workflow attempt, active
writer, discussion thread or applicable gate changed. An identical fingerprint
is an idempotent `D0=0 NOOP`, never a duplicate receipt.

Review receipts and review-diff manifests/packets are never committed to the
reviewed candidate branch or to `main`. Doing so would mutate the reviewed
head, immediately stale its evidence and create a recursive evidence-commit/
review loop. The candidate base, head, tree, scope and diff are therefore
unchanged by feedback persistence.

After the ledger receipt has been written and read back byte-exactly, the same
result may be projected as an Actions artifact, the exact-head status
`QIKVRT requested review execution`, and a pull-request `COMMENT`. Those are
projections of the receipt, not competing authorities. Existing downstream
controllers consume the workflow-completion and status transition and derive
their already bounded continuation; the feedback plane does not create a
parallel action router. A status is only a projection: immediately before any
promotion effect, the promotion controller must load the full-fingerprint
receipt and diff from the role-local ledger and regenerate them through the
same trusted-main observer. A stale same-head status never authorizes an
action. Any eligibility, base, head, tree, scope, diff, discussion, gate,
writer, fingerprint or receipt-payload mismatch remains `HOLD_UNVERIFIED`.
The pull-request title and body digests are part of the fingerprint, so an
`edited` event cannot reuse a prior same-head receipt or status.

The existing GitHub pull-merge REST operation compares the requested PR head
but has no compare-and-swap input for the reobserved base. It therefore cannot
prove that the checked base becomes the merge commit's immediate first parent
(`HEAD^1`) if `main` advances concurrently. Automated merge is fail-closed and
disabled. A technically favorable Mesh receipt derives only
`REQUEST_HISTORY_PRESERVING_EXACT_BASE_CAS_AUTHORITY`; it does not imply a
merge. Automatic draft-to-ready reclassification is also disabled: GitHub
offers no atomic expected-base-and-head compare-and-swap for that mutation,
and a `GITHUB_TOKEN`-authored `ready_for_review` event cannot establish the
required follow-on workflow cycle. A favorable draft review therefore derives
only `REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY`, bound to
the trusted `github-actions[bot]` self-heal PR-body marker, same-repository
`automation/self-heal-*` head, unchanged marker-body digest and exact base/head.

The causal review states are fixed:

- `D0=0 NOOP`: the identical exact receipt is already persisted, or no new review action exists;
- `D0=1 HOLD`: an applicable gate is active or adverse, a finding or unresolved thread remains, the receipt is invalid, or the ledger compare-and-swap conflicts;
- `D0=2 REOBSERVE`: exact evidence is missing, stale, untrusted, zero-job, or the base, head, tree, scope or diff drifted;
- `D0=3 REQUEST_AUTHORITY`: the Mesh disposition supports continuation, but an exact independent Code-Owner disposition or another required authority is missing or stale.

A requested review may not be replaced by repeated requests, reminders, or status commentary when the connected client can inspect the candidate itself. A review may remain pending only for a precise blocker such as missing bytes, head drift, unavailable required evidence, unresolved security or rights questions, or a platform identity rule that prevents the requested account-level event.

The automated Mesh signer is `github-actions[bot]` and may submit only a
`COMMENT` review event. It must never submit `APPROVE` or `REQUEST_CHANGES` as
though it were the requested human, impersonate another GitHub identity, or
claim that GitHub recorded `APPROVED` when the platform stored `COMMENTED`.
The substantive automated finding is persisted accurately together with the
platform state. It never satisfies, replaces, weakens or transfers the separate
exact-head independent Code-Owner gate.

The separately versioned `OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1` does not
change that `github-actions[bot]` boundary. It permits a second, explicit
adapter only when GitHub receives a self-identifying `type=User` credential for
the selected repository account and returns that exact account in the review
readback. The adapter uses `Goldkelch` or `ingolf-lohmann` solely as the
non-author counterpart, never exposes its credential to candidate bytes, and
keeps the account credentials in separate signer jobs. Its review body is
marked as delegated account automation; it is not an independent
natural-person review and does not create merge, release, publication,
deployment, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` authority. The full
provisioning and fail-closed checks are in
`docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md`.

The platform-effective repository-reviewer set is `Goldkelch` and
`ingolf-lohmann`.  The pull-request author is removed from the eligible set for
that pull request, so the other configured account is the required counterpart.
Ingolf Lohmann as a natural person does not perform these reviews.  ChatGPT may
produce a clearly attributed technical disposition but does not normally supply
the native repository-account approval.  Account labels establish only the
platform signer recorded by GitHub; they do not prove distinct natural persons
or organizational independence.

Review completion and feedback persistence do not themselves authorize merge,
promotion, release, deployment, Zenodo, DOI, IETF, `PASS`, `FINAL_PASS`,
`EFFECT_ACK_DONE`, Authority/Mirror equality, scientific confirmation or an
external effect. Every such completion claim remains false in the receipt.

## Issues

Every observed open issue must have a current repository-native lifecycle disposition. The allowed dispositions are:

- `EXECUTE_NOW`: the request is clear, supported, and technically actionable; begin or continue the smallest bounded work unit;
- `CLARIFICATION_REQUIRED`: a specific ambiguity prevents safe execution; record the minimum missing information and ask only the bounded clarification required;
- `BLOCKED_WITH_NEXT_ACTION`: the issue is valid but a precise internal or external blocker exists; record evidence, owner, retry condition, and the next technically possible action;
- `CLOSE_COMPLETED`: the requested result is already fully evidenced or has been completed through a canonical successor;
- `CLOSE_NOT_PLANNED`: the request is understood but intentionally outside the supported or authorized scope;
- `CLOSE_INVALID_OR_UNSUPPORTED`: the request is not reproducible, not traceable to evidence, internally contradictory, untrue, or technically unsupported.

An issue must not remain open merely because it is old, broad, inconvenient, or repeatedly retried. If actionable, it must progress. If unclear, it must be concretized. If completed, superseded, invalid, unsupported, or not planned, it must be closed with a concise evidence-bound reason. Closure is reversible, must preserve the discussion and provenance, and must not be used to hide a real unresolved defect.

No issue may be left in an unclassified waiting state. A `BLOCKED_WITH_NEXT_ACTION` disposition is not a generic parking state: it requires a deterministic failure class, evidence references, and a single continuation path.

## Execution and reporting

The fastest verified path is mandatory. Existing scripts, work units, review evidence, and issue-agent infrastructure must be reused before parallel machinery is created. Activity without a changed lifecycle predicate is not progress.

Report only material changes: a new disposition, a resolved or newly evidenced blocker, a head or scope change, a completed work unit, a closure, or a promotion-ready result. Preserve fail-closed scientific, provenance, security, rights, and external-effect boundaries.

## Machine authority

The normative machine-readable policy is
`policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`. The natural-person
delegations are
`state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`
and
`state/authorization/delegations/OWNER_MESH_REPOSITORY_SELF_REVIEW_FEEDBACK_V1.json`.


## `docs/STATUS_REPORT_RELEASE_AUTOMATION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zweiphasige Automation der offiziellen QIK-VRT-Statuserklärung

## Gegenwärtiger Zustand

Die Automation ist im eingecheckten Zustand **inert**. Der Marker
`release/status-clarification-request.json` enthält `action: inactive`,
`confirm: NOT_AUTHORIZED`, ausschließlich Null-Identitäten und keine DOI. Ein
normaler Push auf `main` reserviert nichts, erzeugt keinen Tag und publiziert
nichts. Eine Wirkung benötigt jeweils einen separat geprüften, nicht forcierten
Push eines Marker-only-Commits auf den unten festgelegten Branch.

Die Automation erzeugt ausschließlich einen neuen, eigenständigen
Statusbericht. Die vorhandenen Zenodo-Records `21498772`, `21498773`,
`21498774` und `21488115` sind unveränderliche Schutzanker. Der Client besitzt
keinen `newversion`-Pfad und blockiert jede Mutation dieser IDs.

## Fester Vertrag

| Element | Wert |
|---|---|
| Autoritätsrepository | `Goldkelch/qik-vrt` |
| Spiegelrepository | `ingolf-lohmann/qik-vrt` |
| Reserve-Branch | `automation/status-clarification-reserve-20260722` |
| Finalize-Branch | `automation/status-clarification-finalize-20260722` |
| Zustandsbranch | `qikvrt/status-report-state` |
| Tag | `v2026.07.22-status-clarification-1.0.0` |
| Marker | `release/status-clarification-request.json` |
| Schema | `policy/qikvrt-status-report-release-request.schema.json` |
| Client | `tools/qikvrt_status_zenodo.py` |

Der Marker bindet die beiden repository-spezifischen `main`-Commits, ihren
identischen Git-Tree, den Client sowie sämtliche Manifestbytes per SHA-256.
Der aktive Commit darf gegenüber seinem unmittelbaren `main`-Quellparent
ausschließlich den Marker ändern. Ein Merge- oder Mehr-Eltern-Commit ist keine
Autorisierung. Der annotierte Tag zeigt immer auf den jeweiligen Quellparent,
nie auf den Marker-Commit.

## Drei Manifestebenen

Die DOI wird nicht vorweggenommen. Deshalb trennt Schema 2 drei Dateien:

1. `release/status-clarification-zenodo-reservation-manifest.json` bindet
   Metadaten, Report-ID, das Template-Manifest und genau eine erlaubte
   DOI-Einbettungsstelle.
2. `release/status-clarification-zenodo-template.json` bindet die endgültige
   Dateiliste vor der Reservierung. Genau eine autorisierte Datei enthält
   einmal `10.5281/zenodo.__RESERVED__`.
3. `release/status-clarification-zenodo.json` ist das Finalmanifest. Gegenüber
   dem Template ist ausschließlich die bytegenaue Ersetzung dieses einen
   Sentinels durch die von Zenodo reservierte DOI zulässig.

Im Reserve-Marker sind Client-, Reservierungsmanifest- und Templatehash
gesetzt; `final_manifest_sha256`, Reservierungsevidenz und DOI bleiben Null.
Im Finalize-Marker sind alle drei Manifesthashes, der Hash der öffentlichen
Reservierungsevidenz und die reservierte DOI gesetzt.

Der aktuelle Clientvertrag lautet:

```text
reserve
  --reservation-manifest release/status-clarification-zenodo-reservation-manifest.json
  --final-template-manifest release/status-clarification-zenodo-template.json
  --reservation OUT
  --repository-root .

finalize
  --reservation-manifest release/status-clarification-zenodo-reservation-manifest.json
  --final-template-manifest release/status-clarification-zenodo-template.json
  --final-manifest release/status-clarification-zenodo.json
  --reservation IN
  --result OUT
  --repository-root .
```

Der Zenodo-Token ist ausschließlich als `ZENODO_ACCESS_TOKEN` zulässig. Er
darf weder als Argument noch in Evidenz, Artifact oder Zustandsbranch
erscheinen.

## Phase 1: Reservierung

Nur `Goldkelch/qik-vrt` kann die Reservierung ausführen.

1. Beide `main`-Commits und der gemeinsame Tree werden endgültig bestimmt.
2. Client, Reservierungsmanifest und Template werden vollständig geprüft und
   gehasht. Das Finalmanifest existiert noch nicht beziehungsweise ist nicht
   autorisiert.
3. Vom exakten Goldkelch-`main` wird der Reserve-Branch erzeugt.
4. Ein zweiter Commit ändert ausschließlich den Marker zu `action: reserve`,
   bindet beide Commits, Tree und Hashes und verwendet
   `RESERVE_ONE_NEW_STATUS_REPORT_DRAFT_NO_PUBLISH`.
5. Erst der nicht forcierte Push dieses Zweitcommits startet die Wirkung.

Der Workflow prüft Branchkopf, Push-Vorher/Nachher, beide öffentlichen
`main`-Refs, beide Git-Trees, Parent, Marker-Diff, Schema, kanonischen
Autorisierungshash, Client und Template. Danach läuft das vollständige
`make test` des Quellparents. Erst unmittelbar vor der Wirkung werden die
entscheidenden Bindungen erneut geprüft.

Vor jedem Zenodo-POST persistiert der Workflow zunächst einen deterministischen
One-shot-Intent unter
`release-state/status-clarification/zenodo-reservation-attempt.json`. Erst
der Lauf, der diesen Intent selbst erfolgreich angelegt hat, darf einen neuen
leeren Entwurf erzeugen. Liegt der Intent bei einem späteren Lauf bereits vor,
aber noch keine Reservierungsevidenz, wird kein weiterer POST gesendet: Der
mehrdeutige Zwischenzustand muss anhand der Zenodo-Entwürfe ausdrücklich
reconciliiert werden. Damit wird nach einem Antwortverlust oder Abbruch kein
zweiter Entwurf automatisch erzeugt.

Der Entwurf wird nicht veröffentlicht. Die token-authentisierte
Reservierungsevidenz wird unter
`release-state/status-clarification/zenodo-reservation.json` im dedizierten
Zustandsbranch und zusätzlich als SHA-gepinntes Actions-Artifact gespeichert.

## DOI-Einbettung zwischen den Phasen

Aus der Reservierung werden DOI und Evidenzhash gelesen. Die eine autorisierte
Template-Datei wird durch exakte Sentinel-Ersetzung erzeugt; anschließend wird
das Finalmanifest aus den tatsächlichen finalen Bytes erstellt. Diese
Änderungen gehören in einen regulär geprüften neuen `main`-Quellstand beider
Repositories. Sie gehören nicht in einen wirkenden Marker-Commit.

Damit können Reserve- und Finalize-Quellcommits verschieden sein. Jeder
Finalize-Tag bindet den dann aktuellen Parent-Commit und den identischen
finalen Tree beider Repositories.

## Phase 2: Tag und Publikation

1. Von jedem exakten finalen `main`-Commit wird separat der Finalize-Branch
   erzeugt.
2. Der zweite Commit ändert in jedem Repository ausschließlich denselben
   Marker zu `action: finalize` und bindet die repo-spezifischen Commits, den
   gemeinsamen Tree, alle Manifesthashes, Reservierungsevidenzhash und DOI.
3. Der nicht forcierte Push läuft in beiden Repositories.

Jedes Repository prüft die Reservierung, die exakte Template-zu-Final-Differenz
und beide weiterhin unveränderten `main`-Refs. Danach erstellt oder verifiziert
es mit seinem eigenen kurzlebigen `GITHUB_TOKEN` einen annotierten Tag auf
seinem jeweiligen Quellparent. Die Automation erstellt kein
GitHub-Release-Objekt.

Nur der Goldkelch-Lauf verwendet `ZENODO_ACCESS_TOKEN`. Unmittelbar vor der
Zenodo-Wirkung prüft er den eigenen und den Spiegel-Tag vollständig, darunter
Tagger, Nachricht, Zielcommit und Zieltree, und wartet begrenzt auf den
Spiegel-Tag. Erst danach lädt der Client ausschließlich die final gebundenen
Dateien hoch, liest sie zur Hashprüfung zurück und publiziert den frisch
reservierten Report. Der Spiegel-Lauf besitzt keine Zenodo-Wirkung.

## Fail-closed-Grenzen

Die Wirkung bleibt blockiert bei unter anderem:

- falschem Repository, Event, Branch oder Marker-`action`;
- Force-Push, Merge-Marker oder mehr als einer geänderten Datei;
- von `main` abweichendem Parent oder verändertem gemeinsamen Tree;
- abweichendem Schema-, Client-, Manifest- oder Evidenzhash;
- einer zweiten oder verschobenen DOI-Einbettungsstelle;
- Metadaten-, Dateilisten- oder Byteänderungen neben der DOI-Ersetzung;
- einem vorhandenen divergenten oder leichtgewichtigen Tag;
- einer fehlenden Spiegel-Tag-Barriere oder einem inzwischen verschobenen
  `main`-Ref;
- einem vorhandenen One-shot-Intent ohne eindeutig persistierte
  Reservierungsevidenz;
- einer geschützten Alt-ID, einem `newversion`-Pfad oder einer Token-Spur;
- einem fehlgeschlagenen Quelltest oder einer veränderten Autorisierungsbranch.

Ein inaktiver Marker ist kein vorläufiges PASS, sondern ausdrücklich keine
Autorisierung.


## `docs/TEST_INVENTORY.md`

# Test inventory

The 2026-07-22 EFFECT_ACK-universality release discovers twelve executable
Python test modules and runs 128 tests. The command-line offline-render checker
and the C90/shell gates are exercised separately by `make test`.

| Module | Tests |
|---|---:|
| `tests/test_api_client.py` | 4 |
| `tests/test_effect_ack_conformance.py` | 41 |
| `tests/test_handler_security.py` | 17 |
| `tests/test_handler_unit.py` | 6 |
| `tests/test_integrity.py` | 1 |
| `tests/test_launcher_runtime.py` | 15 |
| `tests/test_license_transition.py` | 5 |
| `tests/test_seed_workflows.py` | 12 |
| `tests/test_tcpip_e2e.py` | 1 |
| `tests/test_effect_ack_release_workflows.py` | 7 |
| `tests/test_zenodo_actions.py` | 17 |
| `tests/test_zenodo_manifest_builder.py` | 2 |
| **Total** | **128** |

The complete gate is:

```bash
make test
```

It also performs strict ANSI-C90 compilation and exhaustive model comparison,
scientific-proof regeneration, adaptive-runtime controls, active Python and
shell syntax checks, workflow and OpenAPI YAML parsing, JSON parsing,
license-transition verification, and canonical integrity verification. Static
gates and executable unit/end-to-end tests remain distinct even though
`make test` runs them as one verification path.

The local result is reference conformance, not production certification. The
corresponding hosted release evidence is retained on the public
`qikvrt/zenodo-state` branch after exact-tree CI and finalization.


## `docs/TRANSACTIONAL_GITHUB_WORKFLOW_TRIGGER_PROTOCOL.md`

<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Transactional GitHub workflow trigger protocol

Canonical failure class: `NON_ATOMIC_MULTI_COMMIT_WORKFLOW_TRIGGER_ORDERING_RACE`.

Repository transactions are assembled as payload writes, exact manifest/hash binding, and one final JSON ready-marker write. Workflows watch only the ready marker and invoke `tools/qikvrt_transactional_workflow_trigger.py verify` before any effect. Missing or malformed markers, missing or unexpected changed paths, absent files, hash divergence and false completion claims block execution.

A verified trigger proves only transaction completeness. It does not prove task completion, merge, publication, Authority/Mirror equality, `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE`.

