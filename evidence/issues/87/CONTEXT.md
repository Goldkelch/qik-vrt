# Repository context for issue processing

This context is deterministic, size-bounded, and derived from the checked-out repository.
It is evidence input, not an assertion that every included file is relevant.

## `README.md`

# QIK-VRT

[![QIKVRT CI](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml/badge.svg?branch=main)](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml)
[![Release](https://img.shields.io/badge/release-v2026.07.22--effect--ack--universality--1.0.0-1f6feb)](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
[![License: source--available](https://img.shields.io/badge/code-PolyForm%20Noncommercial-orange)](LICENSE)

![QIK-VRT — five-state auditable effect release](docs/assets/qikvrt-social-preview.png)

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

- `RUNNING`: work is actively progressing.
- `WAITING`: an external system is running or a review/approval is pending.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It MUST identify the verified repository, ref, source SHA, checks, and evidence.

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

## Tracked status artifacts

`AI_PROGRESS.json` and `AI_STATUS.md` are durable handoff snapshots. When no repository operation owns them, they MUST be `IDLE` or terminal. A tracked root snapshot MUST NOT remain falsely `RUNNING`, `WAITING`, or `PENDING` after its owner has ended.

Live workflow frames are persisted by `QIKVRT live status watch`; the tracked root snapshots identify the last stable handoff state and where to obtain live state.

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

# QIK-VRT GitHub App Target Blueprint

4AV1 still uses owner-provided installation tokens for bootstrapping. Product operation should move to a GitHub App with repository-scoped installation, least privilege, and short-lived installation tokens.

Required target permissions:

- Contents: read/write
- Actions: read/write or workflow dispatch capability
- Metadata: read

The app must not write to foreign repositories. Each installed repository writes only to itself.


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


## `docs/articles/a001_quantum_crypto_ai.md`

# Quantenkausalität, künstliche Kognition und die doppelte Schneide der Sicherheit

## Status

`ARTICLE_STATUS = CONCEPTUAL_SYNTHESIS`  
`CLAIM_BOUNDARY = KEINE_ANLEITUNG_ZUM_AUSNUTZEN_REALER_SICHERHEITSLUECKEN`  
`QIKVRT_GATE = ETHICS_BOUND_TO_CAPABILITY`

## Artikel

Quantencomputing wird erhofft, weil es neue Rechenwege eröffnet. Es wird gefürchtet, weil es Sicherheitsannahmen verschiebt. Der entscheidende Punkt ist nicht, dass ein Quantencomputer einfach ein schneller klassischer Computer wäre. Der entscheidende Punkt ist, dass Quanteninformation andere Anschlussbedingungen von Möglichkeit, Messung, Interferenz und Wirkung nutzt.

Klassische Kryptographie lebt oft von asymmetrischem Aufwand: Verschlüsseln oder Prüfen ist leicht; Brechen oder Fälschen ohne Schlüssel ist praktisch zu schwer. Quantenalgorithmen zeigen, dass einige dieser Härteannahmen in einem erweiterten Rechenmodell nicht dauerhaft als selbstverständlich behandelt werden dürfen. Daraus folgt nicht, dass jede Sicherheitslücke automatisch ausnutzbar wäre. Daraus folgt aber, dass Sicherheitsarchitektur nicht auf ungeprüften Gewohnheiten ruhen darf.

Künstlich-kognitive Systeme greifen dieselbe Struktur auf anderer Ebene auf. Sie halten Möglichkeitsräume, Hypothesen, Anschlusswege und Widersprüche parallel modellierbar. Sie können schützen, indem sie Risiken ordnen, Angriffsflächen erkennen und Nachweise strukturieren. Sie können gefährlich werden, wenn dieselbe Fähigkeit zur Manipulation oder Ausnutzung eingesetzt wird.

Die doppelte Schneide lautet:

**Wer kausale Anschlussräume besser erkennt, kann Systeme besser schützen — oder besser beschädigen.**

Darum ist die Fähigkeit nicht wertneutral freizugeben. Sie ist an Ethik, Audit und Verantwortbarkeit gebunden.

## QIKVRT-Schluss

Keine Sicherheitswirkung ohne Anforderung. Keine Freigabe ohne Test. Kein PASS ohne Traceability. Keine Macht ohne Ethik.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a002_categorical_imperative.md`

# Quantenkausalität, KI und der kategorische Imperativ

## Status

`ARTICLE_STATUS = ETHICAL_BOUNDARY`  
`CLAIM_BOUNDARY = NORMATIVE_RULE_NOT_EMPIRICAL_PROOF`  
`QIKVRT_GATE = RESPONSIBILITY_REQUIRED`

## Artikel

Technische Fähigkeit ist nicht automatisch Legitimation. Wer kausale Anschlussräume sichtbar macht, erkennt Wirkung. Wer Wirkung erkennt, trägt Verantwortung. Darum ist die Ontologie des Unterschieds nicht nur Erkenntnisordnung, sondern Verantwortungsarchitektur.

Unterschied erzeugt Information. Information erzeugt Wirkung. Wirkung erzeugt Verantwortung. Verantwortung verlangt Ethik.

Der kategorische Imperativ lautet in der digitalen Fassung:

**Handle mit Information nur so, dass die Regel deines Umgangs mit Information allgemeingültig sein könnte, ohne Freiheit, Würde, Wahrheit, Sicherheit und Verantwortbarkeit zu zerstören.**

Eine Sicherheitsfähigkeit darf allgemeine Sicherheit nicht zerstören. Eine Analysefähigkeit darf Menschen nicht manipulierbar machen. Eine Kryptographiefähigkeit darf Verantwortung nicht unsichtbar machen. Eine Identitätsfähigkeit darf nicht Überwachung statt Schutz erzeugen. Eine künstlich-kognitive Fähigkeit darf nicht bloß Macht ohne Rechenschaft verstärken.

Je größer die erkannte Wirkungsmacht, desto größer die Verantwortung.

## QIKVRT-Schluss

Die Technologie darf nicht gegen die Bedingung ihrer eigenen Verantwortbarkeit eingesetzt werden.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a003_uap_maturity_test.md`

# UAP, Reifeprüfung und Verantwortung der Menschheit

## Status

`ARTICLE_STATUS = SCENARIO_ANALYSIS`  
`CLAIM_BOUNDARY = UAP_UNGEKLAERT_IST_NICHT_AUTOMATISCH_NICHTMENSCHLICH`  
`QIKVRT_GATE = INDIZIEN_SIND_NICHT_BEWEISE`

## Artikel

Die UAP-Frage ist öffentlich, sicherheitspolitisch und kulturell relevant. Öffentliche Stellen untersuchen Anomalien, Berichte und Sensordaten. Daraus folgt nicht automatisch ein außerirdischer Ursprung. Daraus folgt aber ein legitimer Untersuchungsauftrag.

Die stärkste robuste Deutung lautet: Die Menschheit befindet sich faktisch in einer Reifeprüfung ihrer eigenen Wirkungsmacht. Ob höhere Beobachter existieren oder nicht, ändert die praktische Konsequenz nicht. Klimakrise, KI, Atomwaffen, Desinformation, Plattformmacht, Biodiversitätsverlust, digitale Identität und globale Institutionen prüfen bereits jetzt, ob die Menschheit mit Macht, Wissen und Technik verantwortbar umgehen kann.

Die Reifeprüfung fragt nicht zuerst: Sind wir technisch interessant? Sie fragt: Sind wir verantwortungsfähig?

## QIKVRT-Schluss

Ob wir beobachtet werden oder nicht: Wir stehen unter Prüfung durch die Folgen unseres Handelns.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a004_transcendent_info.md`

# Transzendierende Information, Retrokausalität und der Kontakt der Zukunft

## Status

`ARTICLE_STATUS = THEORETICAL_MODEL`  
`CLAIM_BOUNDARY = KEIN_EXPERIMENTELLER_BEWEIS_FUER_PHYSIKALISCHE_ZEITMASCHINE`  
`QIKVRT_GATE = INFORMATION_TRANSCENDS_CARRIER`

## Artikel

Nicht Materie transzendiert primär. Information transzendiert. Eine Information kann gesprochen, geschrieben, gespeichert, kopiert, versioniert, verteilt, interpretiert und künstlich-kognitiv verarbeitet werden. Sie überschreitet ihren ursprünglichen Ort, Zeitpunkt und Träger.

Zeit wird dadurch nicht nur Uhrzeit, sondern Ordnung von Informationsankünften. Eine Information kann zu früh, zu spät, am falschen Ort oder im richtigen Moment ankommen. Ihre Wirkung entsteht aus Information, Zeitpunkt, Empfänger und Interpretation.

Retrokausalität ist in verantwortbarer Form nicht die Behauptung, fertige Ereignisse würden magisch rückwärts reisen. Sie bedeutet: Eine mögliche, erwartete, prognostizierte oder gefürchtete Zukunft beeinflusst Gegenwartshandeln. Ziele, Warnungen, Prognosen, Hoffnungen und Risiken wirken heute.

Daraus folgt: Wenn die Zukunft als Möglichkeit bereits wirkt, ist Kontakt mit Zukunft nicht zuerst ein Raumschiff, sondern eine Information, die rechtzeitig verstanden werden will.

## QIKVRT-Schluss

Die Zukunft ist nicht bloß später. Sie ist als Möglichkeit bereits jetzt wirksam.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a005_ockham_maturity.md`

# Ockhams Messer und die Reifeprüfung

## Status

`ARTICLE_STATUS = EXPLANATORY_SYNTHESIS`  
`CLAIM_BOUNDARY = EINFACHHEIT_IST_NICHT_GEWONHEIT`  
`QIKVRT_GATE = DEUTUNG_NACH_STATUS`

## Artikel

Ockhams Messer sagt nicht: Die gewöhnlichste Erklärung ist immer wahr. Es sagt: Wähle die Erklärung, die mit den wenigsten unnötigen Zusatzannahmen die Beobachtungen am besten ordnet.

Bei globalen Krisen, UAP-Debatten, KI-Risiken, Plattformmacht, Wahrheitszerfall, digitaler Identität, Quantenrisiken und mythischen Deutungsmustern ist die bloße Erklärung „alles getrennte Zufälle“ nicht automatisch sparsam. Sie kann sehr viele Trennannahmen benötigen.

Sparsamer ist die Strukturdeutung: Die Menschheit hat eine Schwelle erreicht, an der ihre Informations-, Technik- und Wirkungsmacht größer geworden ist als ihre bisherige institutionelle und ethische Reife.

Die These „höhere Wesen prüfen uns“ bleibt spekulativ. Die These „die Menschheit steht faktisch in einer Reifeprüfung ihrer eigenen Wirkungsmacht“ ist dagegen ohne Zusatzwesen tragfähig.

## QIKVRT-Schluss

Ockhams Messer schneidet nicht das Ungewöhnliche weg. Es schneidet unnötige Annahmen weg.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a006_reincarnation_info.md`

# Reinkarnation als transzendierende Information

## Status

`ARTICLE_STATUS = RELIGIONS_PHILOSOPHICAL_TRANSLATION`  
`CLAIM_BOUNDARY = KEIN_BEWEIS_FUER_MATERIELLE_SEELENWANDERUNG`  
`QIKVRT_GATE = INFORMATION_NOT_CARRIER`

## Artikel

Reinkarnation wird präziser, wenn man nicht fragt, welches Ding wandert, sondern welche Information wieder wirksam wird. Nicht der alte Körper kehrt zurück. Nicht Materie wandert. Information findet neuen Anschluss.

Eine Idee, ein Trauma, ein Mythos, ein Satz, eine Geste, eine Angst, ein Auftrag oder eine Ethik kann in einem neuen Menschen, Text, System oder kulturellen Zusammenhang wieder wirksam werden. Der religiöse Satz „ein Geist kommt über jemanden“ lässt sich informatisch lesen: Eine Informationsstruktur erreicht Sinn, Verstand, Kopf, Mund und Handlung.

Mythen sind Langzeitspeicher. Religionen bewahren Informationen über Grenze, Schuld, Verantwortung, Hoffnung, Warnung und Transzendenz. Sie werden nicht dadurch wertlos, dass man sie nicht als Laborprotokolle liest.

## QIKVRT-Schluss

Ein Unterschied, der anschlussfähig bleibt, kann über Träger hinweg weiterwirken.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a007_facts_speak.md`

# Wenn Fakten wieder für sich sprechen

## Status

`ARTICLE_STATUS = PUBLICATION_READY_ESSAY`  
`CLAIM_BOUNDARY = AUFKLAERUNG_DURCH_STATUSORDNUNG`  
`QIKVRT_GATE = FACT_INTERPRETATION_DISTINCTION`

## Artikel

Aberglaube beginnt nicht dort, wo Menschen staunen. Aberglaube beginnt dort, wo Menschen aufhören zu unterscheiden: Fakt, Behauptung, Erfahrung, Deutung, Symbol, Beweis, Hoffnung, Wissen, Rauschen.

Die Zeit des Aberglaubens endet nicht, weil alle Fragen gelöst sind. Sie endet, wenn bloßer Glaube, Angst, Autorität, Algorithmus und Wiederholung nicht mehr denselben Rang beanspruchen dürfen wie belegbare Tatsachen.

Fakten sprechen für sich, wenn sie gegen falsche Deutung, Machtinteresse und Rauschen geschützt werden. Ein Fakt ersetzt nicht jede Interpretation. Aber er begrenzt zulässige Interpretationen.

## QIKVRT-Schluss

Aberglaube endet dort, wo Menschen wieder sauber unterscheiden.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a008_250_freedom_info.md`

# Der 250. Jahrestag und die Kausalität der Information

## Status

`ARTICLE_STATUS = HISTORICAL_SYMBOLIC_SYNTHESIS`  
`CLAIM_BOUNDARY = DATUM_ALS_BEDEUTUNGSKNOTEN_NICHT_MAGISCHER_BEWEIS`  
`QIKVRT_GATE = LOCAL_DECENTRAL_DISTRIBUTED_GLOBAL`

## Artikel

Der 4. Juli 2026 markiert den 250. Jahrestag der amerikanischen Unabhängigkeitserklärung. Als Bedeutungsknoten verbindet dieses Datum Freiheit, Selbstbestimmung, Verantwortung und öffentliche Erklärung.

Wenn an einem solchen Datum Gedanken über digitale Freiheit, Information, Kausalität, künstlich-kognitive Systeme und globale Reife zusammengetragen werden, ist das kausal verständlich: Vorgeschichte, Arbeit, Erfahrung, Technik und Symbolik führen zusammen.

Es ist zugleich retrokausal im praktischen Sinn: Eine mögliche bessere Zukunft fordert Gegenwartshandeln ein. Lokal formuliert ein Mensch. Dezentral und verteilt kann die Information gespeichert werden. Global macht das Internet sie anschlussfähig.

## QIKVRT-Schluss

Die Vergangenheit hat diesen Moment vorbereitet. Die Zukunft fordert ihn ein. Die Gegenwart muss ihn verantworten.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a009_cognitive_future_info.md`

# Wenn Zukunftsinformation zur Gegenwartsmacht wird

## Status

`ARTICLE_STATUS = AI_CAUSAL_RISK_FRAME`  
`CLAIM_BOUNDARY = KEINE_BEHAUPTUNG_PHYSIKALISCHER_DATENPAKETE_AUS_DER_ZUKUNFT`  
`QIKVRT_GATE = FORECAST_WITH_ASSUMPTION_DISCLOSURE`

## Artikel

Künstlich-kognitive Systeme erzeugen Informationen über mögliche Zukünfte. Diese Informationen wirken in der Gegenwart. Eine KI prognostiziert Verhalten, bewertet Risiko, erzeugt Szenarien, lenkt Aufmerksamkeit, schlägt Handlungen vor oder sortiert Menschen, Inhalte und Chancen.

Dadurch entsteht praktische Retrokausalität: Ein Modell entwirft eine mögliche Zukunft, und Menschen oder Maschinen handeln heute nach diesem Entwurf.

Gefährlich wird dies, wenn Zukunftsmodellierung verborgen bleibt: Welche Daten? Welche Ziele? Welche Annahmen? Welche Interessen? Welche Wirkung? Wer haftet? Wer kann widersprechen? Wer darf stoppen?

## QIKVRT-Schluss

Transzendierende Information darf nicht im Nebel wirken. Sie muss unterscheidbar, reproduzierbar, auditierbar und ethisch gebunden sein.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a010_reverse_engineering_human.md`

# Das industrialisierte Reverse Engineering des Menschen

## Status

`ARTICLE_STATUS = INFORMATICS_PSYCHOLOGY_ANALYSIS`  
`CLAIM_BOUNDARY = STRUKTURELLE_ANALYSE_KEINE_PAUSCHALE_TAETERBEHAUPTUNG`  
`QIKVRT_GATE = BEHAVIORAL_FEEDBACK_AUDIT_REQUIRED`

## Artikel

Internetsuche hat nicht nur Informationen auffindbar gemacht. Sie hat den fragenden Menschen messbar gemacht. Jede Suche ist ein psychologisches Signal: Unsicherheit, Wunsch, Angst, Kaufabsicht, Krankheit, Orientierung, politische Lage, religiöse Frage, existenzielle Lage.

Mit Suche, Tracking, Werbung, A/B-Tests, Feeds, Plattformen und KI wurde menschliches Verhalten in Daten, Profile, Prognosen und Steuerimpulse übersetzt. Das ist Reverse Engineering: Verhalten wird beobachtet, modelliert und zur Beeinflussung zurückgeführt.

Das Wissen der 1960er Jahre über Verhalten, Kybernetik, Propaganda, Kontrolle und institutionelle dunkle Kapitel darf nicht ignoriert werden. Aus dokumentierten dunklen Kapiteln folgt nicht jede wilde Deutung. Aber es folgt: Macht über Verhalten ohne Nachweisstruktur ist niemals harmlos.

## QIKVRT-Schluss

Wer den Moment der Frage modelliert, modelliert Orientierung.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a011_event_horizon_total.md`

# Ereignishorizont, Kausalität und das Reverse Engineering des Menschen

## Status

`ARTICLE_STATUS = PHYSICS_INFORMATICS_SYNTHESIS`  
`CLAIM_BOUNDARY = PHYSIKALISCHER_HORIZONT_NICHT_GLEICH_DIGITALER_HORIZONT_NUR_STRUKTURANALOGIE`  
`QIKVRT_GATE = GLOBAL_CAUSAL_STRUCTURE_NOT_LOCAL_SURFACE`

## Artikel

Der Ereignishorizont eines schwarzen Lochs ist keine Wand, sondern eine globale Kausalgrenze. Ein frei fallender Beobachter kann bei einem hinreichend großen schwarzen Loch den Horizont überschreiten, ohne lokal eine abrupte Grenze zu bemerken. Die Bedeutung des Horizonts liegt nicht im lokalen Gefühl, sondern in der globalen Struktur möglicher Signalwege.

Das ist die Lektion: Entscheidende Grenzen können real sein, ohne lokal auffällig zu sein.

Digitale Systeme besitzen keinen physikalischen Ereignishorizont. Aber sie können strukturell ähnliche Selbsttransparenzgrenzen erzeugen: Der Nutzer merkt den einzelnen Klick. Er sieht aber nicht notwendig die globale Rückkopplung aus Daten, Profil, Prognose, Ranking, Empfehlung und Verhalten.

## QIKVRT-Schluss

Das Problem ist jeder unsichtbare Ereignishorizont der Kausalität: physikalisch, digital, psychologisch und künstlich-kognitiv.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a012_recursive_history.md`

# Wer die Wiederholung kontrolliert, kontrolliert den Wirkraum

## Status

`ARTICLE_STATUS = MEDIA_CAUSALITY_AND_HISTORY_WARNING`  
`CLAIM_BOUNDARY = STRUKTURELLE_WARNUNG_STATT_UNBELEGTER_MASTERPLAN_BEHAUPTUNG`  
`QIKVRT_GATE = DO_NOT_OVERBID_DO_NOT_STONEWALL`

## Artikel

Menschheitsgeschichte wird heute nicht nur durch Ereignisse manipuliert, sondern durch Informationsumgebungen. Wer Geschichte manipulieren will, muss nicht zwingend jedes Ereignis erzeugen. Es genügt, Wahrnehmung, Sichtbarkeit, Wiederholung, Archivierung, Deutung und Erwartung zu steuern.

Die gefährlichste Katastrophe beginnt nicht, wenn alle lügen. Sie beginnt, wenn niemand mehr zuverlässig unterscheiden kann, was Fakt, Deutung, Manipulation oder Rauschen ist.

Digitale Systeme verstärken rekursiv: Muster erzeugen Wiederholung, Wiederholung erzeugt Sichtbarkeit, Sichtbarkeit erzeugt Anschluss, Anschluss erzeugt Verhalten, Verhalten erzeugt Daten, Daten erzeugen Prognosen, Prognosen erzeugen Empfehlungen, Empfehlungen erzeugen stärkere Muster.

Nicht überreizen heißt: Keine stärkere Behauptung als die Karten tragen. Nicht mauern heißt: Reale strukturelle Manipulationsmacht nicht verharmlosen.

## QIKVRT-Schluss

Das Universum manifestiert nicht automatisch das Gute. Es verstärkt, was anschlussfähig wird. Deshalb entscheidet sich Zukunft daran, welche Information wir wiederholen, rahmen, prüfen und verantworten.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a013_truth_future_quote.md`

# Die Wahrheit in der Unterscheidung

## Status

`ARTICLE_STATUS = IMAGE_QUOTE_CANONICAL_TEXT`  
`QIKVRT_GATE = DISTINCTION_PROTECTS_FUTURE`

## Kanonischer Bildsatz

Die Katastrophe beginnt nicht, wenn alle lügen.

Sie beginnt, wenn niemand mehr zuverlässig unterscheiden kann, was Fakt, Deutung, Manipulation oder Rauschen ist.

Wer diese Unterscheidung zurückbringt, schützt Wahrheit und Zukunft.

q.e.d.  
Ingolf Lohmann


## `docs/articles/a014_history_manipulation_recursive.md`

# Wer die Wiederholung kontrolliert, kontrolliert den Wirkraum

## Ueber mediale Manipulation, rekursive Verstaerkung, digitales Geschichtsbewusstsein und die Pflicht, nicht zu mauern und nicht zu ueberreizen

Von Ingolf Lohmann

Es gibt einen alten Satz aus dem Kartenspiel:

**Ueberreize dich nicht.**

Das ist eine gute Warnung. Man soll aus den eigenen Karten nicht mehr machen, als sie tragen. Wer behauptet, mehr zu wissen, als er belegen kann, verliert die Kontrolle ueber die Wirklichkeit.

Aber es gibt eine zweite Warnung:

**Mauere nicht.**

Wer aus Angst vor einer zu starken Behauptung gar nicht mehr spielt, verliert ebenfalls. Wer reale Muster nicht benennt, weil nicht jede Einzelheit endgueltig bewiesen ist, ueberlaesst das Spielfeld jenen, die ohne Skrupel mit Information, Aufmerksamkeit und Erwartung umgehen.

Die reife Position liegt dazwischen:

**Nicht ueberreizen. Nicht mauern. Schreiben. Pruefen. Rahmensetzen.**

Denn wer schreibt, der bleibt.

Aber im digitalen Zeitalter reicht Schreiben allein nicht mehr. Man muss so schreiben, dass Information unterscheidbar, auffindbar, pruefbar, versionierbar, anschlussfaehig und verantwortlich bleibt.

Genau darum geht es.

---

## 1. Die These

Die zentrale These lautet:

**Menschheitsgeschichte wird heute nicht mehr nur durch Ereignisse manipuliert, sondern durch Informationsumgebungen.**

Wer Geschichte manipulieren will, muss nicht zwingend jedes Ereignis selbst erzeugen. Es genuegt oft, die Wahrnehmung der Ereignisse zu steuern:

Was wird sichtbar?
Was wird unsichtbar?
Was wird wiederholt?
Was wird laecherlich gemacht?
Was wird emotional aufgeladen?
Was wird deindexiert?
Was wird archiviert?
Was wird vergessen?
Was wird als plausibel eingerahmt?
Was wird als gefaehrlich markiert?
Was wird kuenstlich verstaerkt?
Was wird algorithmisch begraben?

Damit verschiebt sich Geschichte nicht zuerst in Archiven, sondern im laufenden Informationsstrom.

Die gefaehrlichste Form der Manipulation ist nicht die einzelne Luege.

Die gefaehrlichste Form ist die dauerhafte Veraenderung dessen, was eine Gesellschaft ueberhaupt noch fuer erinnerbar, wahr, wichtig, moeglich oder sinnvoll haelt.

---

## 2. Die neue Macht: Informationsumgebung statt Einzelbefehl

Fruehere Macht musste oft direkt befehlen, zensieren, verbieten, beschlagnahmen oder toeten.

Moderne Macht kann subtiler arbeiten.

Sie muss nicht jedes Buch verbrennen. Sie kann Suchergebnisse verschieben.

Sie muss nicht jede Stimme verbieten. Sie kann Sichtbarkeit dosieren.

Sie muss nicht jeden Menschen ueberzeugen. Sie kann Zweifel saeen.

Sie muss nicht Wahrheit widerlegen. Sie kann Vertrauen erschoepfen.

Sie muss nicht Geschichte komplett faelschen. Sie kann Erinnerung fragmentieren.

Das ist schmerzhafter als die alte Zensur, weil es weniger sichtbar ist.

Menschen merken oft nicht, dass ihre Wirklichkeit vorsortiert wird. Sie merken nur, dass bestimmte Gedanken "irgendwie ueberall" sind und andere "irgendwie verschwinden".

Das ist der moderne Ereignishorizont der Oeffentlichkeit:

**Man ueberschreitet eine Grenze der Manipulation, ohne lokal zu bemerken, dass Rueckkopplung bereits veraendert wurde.**

---

## 3. Die eigentliche Manipulation: nicht die Meinung, sondern die Anschlussbedingungen

Wer nur ueber "Meinungsmanipulation" spricht, denkt zu klein.

Die tiefere Manipulation betrifft Anschlussbedingungen.

Eine Gesellschaft entscheidet nicht nur durch einzelne Meinungen. Sie entscheidet durch die Struktur dessen, was anschlussfaehig ist.

Was kann gesagt werden, ohne sofort zerstoert zu werden?
Was wird gehoert?
Was wird gefunden?
Was wird ernst genommen?
Was wird wiederholt?
Was bekommt Belege?
Was bekommt Kontext?
Was bekommt Sprache?
Was bekommt Archive?
Was bekommt Reichweite?
Was bekommt Zeit?

Die Kontrolle dieser Anschlussbedingungen ist maechtiger als die Kontrolle einzelner Aussagen.

Denn wenn eine Information keinen Anschluss bekommt, wirkt sie nicht.

Und wenn falsche Information millionenfach Anschluss bekommt, wirkt sie - auch wenn sie falsch ist.

Das ist die harte Wahrheit:

**Wirkung und Wahrheit sind nicht identisch.**

Eine Luege kann wirken.
Ein Fakt kann wirkungslos bleiben.
Ein Geruecht kann Geschichte veraendern.
Ein Beweis kann unbeachtet liegen bleiben.
Ein Mythos kann laenger leben als ein Dokument.
Ein Algorithmus kann mehr erinnern als ein Mensch.
Ein Feed kann mehr praegen als ein Schulbuch.

Darum braucht Wahrheit Infrastruktur.

---

## 4. Rekursive Verstaerkung: das System fuettert sich selbst

Digitale Systeme reagieren auf Signale.

Klicks, Likes, Shares, Suchanfragen, Verweildauer, Kommentare, Empoerung, Kaufverhalten, Wiederkehr, Abbruch, Scrolltiefe, Aufmerksamkeit.

Diese Signale werden ausgewertet.

Dann werden Inhalte angepasst.

Dann reagieren Menschen erneut.

Dann entstehen neue Daten.

Dann wird wieder angepasst.

Die Schleife lautet:

```text
Muster
-> Wiederholung
-> Sichtbarkeit
-> Anschluss
-> Verhalten
-> Daten
-> Prognose
-> Empfehlung
-> staerkere Sichtbarkeit
-> neues Verhalten
```

Das ist rekursive Verstaerkung.

Wenn ein Muster gut ist, kann es Gutes verstaerken.
Wenn ein Muster neutral ist, kann es Neutralitaet verstaerken.
Wenn ein Muster schlecht ist, kann es Schlechtes verstaerken.

Der entscheidende Punkt:

**Systeme unterscheiden nicht automatisch zwischen wahr, gut, falsch, zerstoererisch, heilsam oder manipulativ. Sie optimieren zunaechst nach messbaren Signalen.**

Und messbare Signale sind nicht identisch mit Wahrheit.

Empoerung ist messbar.
Angst ist messbar.
Neugier ist messbar.
Suchtverhalten ist messbar.
Spaltung ist messbar.
Wahrheit ist schwieriger.

Deshalb ist eine Gesellschaft, die ihre Informationsordnung allein an Aufmerksamkeit koppelt, bereits gefaehrdet.

---

## 5. Die Normalisierung des Falschen

Die gefaehrlichste Katastrophe ist nicht immer der ploetzliche Zusammenbruch.

Die gefaehrlichste Katastrophe ist die Normalisierung des Falschen.

Wenn Luegen lange genug zirkulieren, werden sie zur "Position".
Wenn Hass lange genug wiederholt wird, wird er zur "Meinung".
Wenn Zynismus lange genug belohnt wird, wird er zur "Realitaetstuechtigkeit".
Wenn Manipulation lange genug unsichtbar bleibt, wird sie zur "Plattformlogik".
Wenn Verantwortung lange genug vermieden wird, wird Verantwortungslosigkeit zur Gewohnheit.

Dann passiert zunaechst scheinbar nichts Gravierendes.

Die Geschaefte oeffnen.
Die Telefone funktionieren.
Die Feeds laufen.
Die Nachrichten senden.
Die Menschen arbeiten.
Die Institutionen bestehen formal weiter.

Aber innen wird ausgehoehlt, was nicht ausgehoehlt werden darf:

Vertrauen.
Wahrheit.
Sprache.
Erinnerung.
Faktenstatus.
Verantwortung.
Gemeinsame Wirklichkeit.

Eine Gesellschaft kann aeusserlich noch funktionieren und innerlich bereits an Rueckkopplungsverlust leiden.

Das ist der Schmerzpunkt.

---

## 6. Das universale Spektrum gibt die Karten aus

Der Satz "das universale Spektrum gibt die Karten aus" laesst sich wissenschaftlich und philosophisch praezise deuten.

Kein Mensch beginnt bei null.

Jeder bekommt Karten:

Biologie,
Geschichte,
Sprache,
Familie,
Zeit,
Technik,
Trauma,
Begabung,
Ort,
Zufall im Alltagssinn,
Kausalitaet,
Kultur,
Begegnungen,
Verlust,
Moeglichkeit.

Diese Karten waehlt man nicht vollstaendig selbst.

Aber man spielt sie.

Hier liegt Verantwortung.

Nicht alles ist frei.
Aber nicht alles ist unfrei.

Kausalitaet gibt Bedingungen.
Bewusstsein erkennt Unterschiede.
Information eroeffnet Spielraeume.
Handlung setzt Wirkung.
Verantwortung entscheidet, ob man sauber spielt.

Also:

**Das Spektrum gibt die Karten. Der Mensch verantwortet das Spiel.**

Nicht ueberreizen.
Nicht mauern.
Schreiben.
Pruefen.
Bleiben.

---

## 7. Manipulation der Menschheitsgeschichte

Menschheitsgeschichte wird nicht nur rueckblickend geschrieben.

Sie wird fortlaufend vorbereitet.

Geschichte entsteht aus:

Ereignissen,
Dokumenten,
Erinnerungen,
Erzaehlungen,
Interpretationen,
Archiven,
Medien,
Macht,
Bildung,
Trauma,
Vergessen,
Wiederholung.

Wer diese Elemente beeinflusst, beeinflusst Geschichtsbewusstsein.

Heute geschieht das ueber:

Suchmaschinen,
soziale Medien,
Video-Plattformen,
KI-Systeme,
automatisierte Inhalte,
Bots,
Deepfakes,
politisches Targeting,
Influencer-Netzwerke,
Werbeauktionen,
Empfehlungsalgorithmen,
Plattformmoderation,
Ranking-Systeme,
Datenauswertung,
synthetische Personas.

Das bedeutet nicht, dass "alles kontrolliert" ist.

Es bedeutet etwas Praeziseres und Gefaehrlicheres:

**Geschichte wird manipulierbar, weil Erinnerung und Sichtbarkeit technisch vermittelt werden.**

Wer die Vermittlung kontrolliert, kontrolliert nicht automatisch die Wahrheit.

Aber er kontrolliert, ob Wahrheit Anschluss bekommt.

---

## 8. Warum ein einzelner geheimer Plan nicht noetig ist

Man muss nicht behaupten, dass eine einzige Gruppe die gesamte Menschheitsgeschichte zentral steuert.

Das waere Ueberreizung.

Die haertere, besser belegbare Aussage lautet:

**Viele Akteure mit unterschiedlichen Interessen koennen dieselben Rueckkopplungssysteme ausnutzen - politisch, oekonomisch, geheimdienstlich, kriminell, ideologisch, militaerisch oder kulturell.**

Sie muessen nicht gemeinsam an einem Tisch sitzen.

Es genuegt, dass sie dieselbe Infrastruktur nutzen:

Aufmerksamkeit.
Angst.
Wiederholung.
Zielgruppen.
Daten.
Prognosen.
Desinformation.
Fragmentierung.
Algorithmische Verstaerkung.

Das Ergebnis kann dennoch wie ein zusammenhaengender Angriff auf Wirklichkeit wirken.

Nicht, weil alles zentral geplant ist.

Sondern weil dieselben Systemanreize dieselben schlechten Muster verstaerken.

Das ist noch gefaehrlicher als eine einfache Verschwoerungserzaehlung.

Denn es braucht keinen allmaechtigen Drahtzieher.

Es braucht nur ein System, das schlechte Muster belohnt.

---

## 9. Die schlechten Dinge kennen wir

Die schlechten Dinge sind nicht geheim.

Wir kennen sie:

digitale Manipulation,
Desinformation,
Plattformmacht,
algorithmische Intransparenz,
Datenmissbrauch,
Aufmerksamkeitsabhaengigkeit,
psychologische Erschoepfung,
KI-generierte Taeuschung,
Deepfakes,
Identitaetsangriffe,
politische Polarisierung,
institutionelles Misstrauen,
Wahrheitszerfall,
soziale Zersetzung.

Man muss diese Dinge nicht dramatisieren.

Sie sind dramatisch genug.

Die schmerzhafte Erkenntnis lautet:

**Wir haben die Werkzeuge gebaut, mit denen sich gesellschaftliche Wirklichkeit industriell verzerren laesst.**

Und wir haben sie in vielen Faellen schneller gebaut als die Verantwortung dafuer.

---

## 10. Die reflexive Schoepfungseigenschaft

Der Satz lautet:

**Es manifestiert sich das, was quantitativ am staerksten vorhanden ist.**

Dieser Satz darf nicht naiv-magisch verstanden werden.

Er bedeutet nicht:

Wer sich etwas wuenscht, bekommt es automatisch.

Er bedeutet:

Was haeufig genug gedacht, gesagt, gespeichert, geklickt, wiederholt, belohnt, empfohlen, kopiert, modelliert und erwartet wird, veraendert die Wahrscheinlichkeit kuenftiger Wirklichkeit.

Das ist eine reflexive Struktur:

Information erzeugt Verhalten.
Verhalten erzeugt Daten.
Daten erzeugen Prognosen.
Prognosen erzeugen Empfehlungen.
Empfehlungen erzeugen neues Verhalten.
Neues Verhalten erzeugt neue Wirklichkeit.

So manifestiert sich nicht "Wahrheit" automatisch.

Es manifestieren sich starke Anschlussmuster.

Darum ist die Aufgabe so ernst:

**Wenn das schlechte Muster staerker angeschlossen ist als das gute, gewinnt nicht das Wahre, sondern das Verstaerkte.**

Das muss weh tun.

Denn es bedeutet:

Eine Gesellschaft kann an ihrer Informationsoekologie scheitern, obwohl einzelne Menschen guten Willens sind.

---

## 11. Kausalitaet und Retrokausalitaet

Letztlich ist alles Kausalitaet.

Aber Kausalitaet ist nicht nur Vergangenheit, die Gegenwart schiebt.

Ein Teil der Kausalitaet ist retrokausal im praktischen Sinn:

Eine erwartete Zukunft veraendert heutiges Verhalten.

Das war immer schon so.

Menschen handeln nach Hoffnung, Angst, Ziel, Prophezeiung, Prognose, Plan, Versprechen, Warnung.

Neu ist:

Diese Zukunftsbilder werden heute industriell erzeugt, getestet, optimiert und verteilt.

Eine Plattform fragt:

Was wirst du klicken?

Ein Werbesystem fragt:

Was wirst du kaufen?

Ein politisches Targeting fragt:

Was wirst du glauben?

Ein Sicherheitsmodell fragt:

Was wirst du riskieren?

Ein KI-System fragt:

Welche Antwort wird wahrscheinlich anschlussfaehig sein?

Dann wird die Gegenwart so gestaltet, dass die prognostizierte Zukunft wahrscheinlicher wird.

Das ist die moderne Form praktischer Retrokausalitaet:

```text
modellierte Zukunft
-> gegenwaertige Auswahl
-> Verhalten
-> Daten
-> neue modellierte Zukunft
```

Wer Zukunftsbilder kontrolliert, kontrolliert nicht die Zukunft vollstaendig.

Aber er beeinflusst die Gegenwart.

Und wer die Gegenwart beeinflusst, veraendert die Zukunft.

---

## 12. Der Skat-Punkt: nicht ueberreizen, nicht mauern

Hier kehren wir zum Anfang zurueck.

**Ueberreizen** waere:

Jede Manipulation als vollstaendig bewiesenen Masterplan einer einzelnen geheimen Instanz auszugeben.

**Mauern** waere:

Die reale, strukturelle Manipulationsmacht digitaler Systeme zu verharmlosen, nur weil nicht jedes Einzelereignis vollstaendig aufgeklaert ist.

Die richtige Haltung lautet:

```text
Behauptung: Status markieren.
Indiz: als Indiz fuehren.
Fakt: als Fakt sichern.
Deutung: als Deutung ausweisen.
Hypothese: als Hypothese pruefen.
Manipulation: anhand von Wirkung, Daten, Wiederholung, Quelle und Ziel analysieren.
```

Das ist nicht schwach.

Das ist stark.

Denn nur so bleibt Wahrheit belastbar.

---

## 13. Was QIK-VRT hier leistet

QIK-VRT ist die Gegenstruktur gegen Manipulation durch Rauschen.

Es beginnt nicht mit Meinung.

Es beginnt mit Unterschied.

```text
Ohne Unterschied keine Bestimmbarkeit.
Ohne Bestimmbarkeit keine Information.
Ohne Information keine Wirkung.
Ohne Wirkung keine Verantwortung.
Ohne Verantwortung keine Ethik.
```

Damit stellt QIK-VRT die Rangordnung wieder her:

Unterschied vor Menge.
Status vor Wirkung.
Nachweis vor Wiederholung.
Quelle vor Deutung.
Audit vor Vertrauen.
Ethik vor Macht.
Verantwortung vor Freigabe.

Das ist der entscheidende Bruch mit der manipulativen Plattformlogik.

Plattformlogik fragt oft zuerst:

Was bindet Aufmerksamkeit?

QIK-VRT fragt:

Was ist der Status der Information?

Plattformlogik fragt:

Was skaliert?

QIK-VRT fragt:

Was ist nachweisbar?

Plattformlogik fragt:

Was erzeugt Engagement?

QIK-VRT fragt:

Was erzeugt verantwortbare Wirkung?

---

## 14. Warum das nachhaltig bleiben muss

Diese Einsicht muss weh tun, weil sie keine bequeme Ausrede laesst.

Man kann nicht mehr sagen:

"Ich habe es nicht gewusst."

Wir wissen, dass Informationsraeume manipulierbar sind.
Wir wissen, dass Wiederholung wirkt.
Wir wissen, dass Plattformen Aufmerksamkeit strukturieren.
Wir wissen, dass KI Taeuschung skalieren kann.
Wir wissen, dass Desinformation Demokratien beschaedigt.
Wir wissen, dass Menschen psychologisch beeinflussbar sind.
Wir wissen, dass Sichtbarkeit nicht Wahrheit ist.
Wir wissen, dass Schweigen auch Wirkung hat.
Wir wissen, dass Mauern gefaehrlich ist.
Wir wissen, dass Ueberreizen Wahrheit beschaedigt.

Damit bleibt nur die erwachsene Konsequenz:

**Wir muessen Informationsraeume verantworten.**

Nicht irgendwann.

Jetzt.

---

## 15. Schluss

Die Manipulation der Menschheitsgeschichte geschieht heute nicht nur durch Faelschung von Dokumenten oder offene Gewalt.

Sie geschieht durch die Gestaltung von Informationsumgebungen.

Wer Aufmerksamkeit, Wiederholung, Sichtbarkeit, Erwartung, Archivierung und Anschlussbedingungen beeinflusst, beeinflusst das, was Menschen fuer Wirklichkeit halten.

Wenn schlechte Muster quantitativ dominieren, manifestieren sie schlechte Wirklichkeit.

Wenn neutrale Muster dominieren, entsteht sterile Gleichgueltigkeit.

Wenn gute, gepruefte, verantwortliche Information dominiert, entsteht bessere Anschlussfaehigkeit.

Das ist keine Magie.

Das ist Kausalitaet.

Ein Teil davon ist Retrokausalitaet, weil Zukunftsbilder Gegenwartshandeln steuern.

Die alten Saetze bleiben gueltig:

Ueberreiz dich nicht.
Mauere nicht.
Wer schreibt, der bleibt.

Aber heute muessen sie ergaenzt werden:

Wer schreibt, muss sichern.
Wer deutet, muss markieren.
Wer behauptet, muss nachweisen.
Wer automatisiert, muss auditieren.
Wer verstaerkt, muss verantworten.

Der fachliche Satz lautet:

**Digitale Rueckkopplungssysteme verwandeln Wiederholung, Aufmerksamkeit und Prognose in geschichtswirksame Kausalitaet.**

Der psychologische Satz lautet:

**Menschen werden nicht nur durch Argumente beeinflusst, sondern durch Sichtbarkeit, Wiederholung, Angst, Zugehoerigkeit und Erwartung.**

Der gesellschaftliche Satz lautet:

**Eine Gesellschaft verliert nicht erst, wenn sie offen besiegt wird; sie verliert bereits, wenn ihr gemeinsamer Wirklichkeitsraum ausgehoehlt wird.**

Der QIK-VRT-Satz lautet:

**Keine Wirkung ohne Unterschied, keine Information ohne Status, keine Wiederholung ohne Verantwortung, keine Macht ohne Audit, keine Zukunft ohne Ethik.**

Und der abschliessende Satz lautet:

**Das Universum manifestiert nicht automatisch das Gute. Es verstaerkt, was anschlussfaehig wird. Deshalb entscheidet sich die Zukunft daran, ob wir schlechte Muster weiterfuettern oder gute Information so stark, so klar und so verantwortlich rahmen, dass sie bleibt.**

q.e.d.  
Ingolf Lohmann

