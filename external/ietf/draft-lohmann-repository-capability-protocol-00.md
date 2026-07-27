<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Repository Capability Protocol (RCP)

## Internet-Draft source

**Intended status:** Experimental  
**Expires:** January 2027  
**Author:** Ingolf Lohmann  
**Filename:** `draft-lohmann-repository-capability-protocol-00`

## Abstract

Repositories expose source code, history and automation artifacts, but they do not provide a uniform protocol by which a client can discover what the repository can do, where a capability is implemented, which authority is required, how execution is triggered, which evidence proves success, and which failure class prevents progress. The Repository Capability Protocol (RCP) defines machine-readable discovery resources, capability records, execution-plan descriptions and effect receipts for repositories and repository-adjacent services. RCP is platform-neutral and can be implemented through HTTP resources, Git-native files or forge-specific adapters.

## 1. Introduction

Automation agents currently infer repository capabilities from conventions, forge APIs and project-specific documentation. This inference is incomplete and produces false denials, unsafe execution attempts and duplicated tooling. RCP defines a standard self-disclosure interface for repository capabilities.

The key invariant is:

`NO_CAPABILITY_DISCOVERY_NO_CAPABILITY_DENIAL`

A conforming client MUST perform capability discovery before asserting that a requested repository effect is unavailable.

## 2. Conventions and terminology

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY and OPTIONAL are to be interpreted as described in BCP 14 when, and only when, they appear in all capitals.

- **Repository:** A versioned information space and its associated execution services.
- **Capability:** A declared operation or verifiable effect.
- **Implementation Location:** A file, API route, workflow, adapter or external service that realizes a capability.
- **Execution Plan:** A deterministic ordered set of work units.
- **Effect Receipt:** Evidence binding a requested effect to an observed state transition.
- **Authority:** The repository role that promotes canonical state.
- **Mirror:** A repository role that independently receives and verifies promoted state.
- **Failure Class:** A stable identifier for a blocked or invalid execution state.

## 3. Discovery

An HTTP-enabled repository SHOULD publish:

`GET /.well-known/rcp`

The discovery document MUST identify a protocol version and links to capability, status, evidence and execution resources.

A Git-native fallback MUST be available at a stable repository path, RECOMMENDED:

- `capabilities/catalog.json`
- `capabilities/runtime-status.json`
- `capabilities/locations.json`
- `capabilities/history.jsonl`

## 4. Capability records

Each capability record MUST contain:

- stable capability identifier;
- semantic version;
- status;
- implementation locations;
- invocation methods;
- required permission names, without secret values;
- tests and current evidence references;
- idempotency and retry semantics;
- known failure classes;
- minimal deterministic next effect;
- provenance and digest bindings;
- Authority and Mirror coverage.

## 5. Status model

The base status vocabulary is:

- `AVAILABLE`
- `PARTIAL`
- `BLOCKED`
- `UNSUPPORTED`
- `DEPRECATED`

The existence of source files alone MUST NOT establish `AVAILABLE`. Availability requires current execution evidence or an explicitly declared unexecuted state.

## 6. Query-before-denial

Before returning an unavailable result, a client MUST:

1. resolve the requested effect to capability identifiers;
2. retrieve the latest capability and runtime records;
3. follow declared implementation locations;
4. inspect required permissions and triggers;
5. inspect current evidence and failure classes;
6. identify the minimal deterministic next effect.

The result SHOULD distinguish:

- `AVAILABLE_NOW`
- `AVAILABLE_VIA_EXISTING_WORKFLOW`
- `AVAILABLE_AFTER_OWNER_BOOTSTRAP`
- `PARTIAL_WITH_MINIMAL_NEXT_EFFECT`
- `BLOCKED_WITH_FAILURE_CLASS`
- `TRULY_UNSUPPORTED`

## 7. Execution plans

An execution plan MUST bind:

- requested capability;
- repository and revision;
- ordered work units;
- preconditions;
- required authorization class;
- expected effects;
- verification steps;
- rollback or forward-recovery behavior.

Execution endpoints MUST be authenticated and MUST fail closed when plan bindings or permissions cannot be verified.

## 8. Effect receipts

A receipt SHOULD contain:

- request identifier;
- plan identifier;
- capability identifier;
- input revision;
- output revision;
- observed state transition;
- test and gate results;
- SHA-256 or stronger digest bindings;
- timestamp;
- issuer identity and verification method;
- Authority/Mirror synchronization result where applicable.

A receipt MUST NOT claim success when mandatory gates are missing, pending or failed.

## 9. Authority and Mirror

RCP supports asymmetric repository roles. A pair-level capability MUST NOT be reported as available unless compatible capability records exist for both roles and the relevant synchronization or declared role asymmetry is evidenced.

`NO_MIRROR_CAPABILITY_RECEIPT_NO_PAIR_AVAILABILITY`

## 10. Security considerations

Capability records can reveal attack surface. Implementations MUST disclose permission and secret names only to the extent required and MUST NOT disclose secret values. Execution routes require authenticated authorization, replay protection, revision binding and least privilege. Capability catalogs MUST be integrity protected. Stale records MUST fail closed.

Biometric raw data MUST NOT be stored in repository capability records. RCP MAY reference attestations from trusted identity providers, passkey systems or hardware-backed authenticators.

## 11. Privacy considerations

Receipts SHOULD minimize personal data and SHOULD use pseudonymous or scoped identifiers where possible. Retention rules and revocation semantics MUST be documented.

## 12. IANA considerations

This initial draft requests no IANA action. A future revision may request registration of the `/.well-known/rcp` well-known URI and media types for capability and receipt documents.

## 13. Interoperability

Initial interoperability targets include GitHub, GitLab, Forgejo and local Git services. The protocol semantics are independent of the forge-specific transport adapter.

## 14. Open issues

- canonical media types;
- version negotiation;
- detached signatures;
- capability delegation;
- federated discovery;
- receipt transparency logs;
- formal semantics for deterministic next effects.

## 15. Reference implementation

The initial reference implementation is developed in `Goldkelch/qik-vrt`, with `ingolf-lohmann/qik-vrt` serving as verification Mirror. Until code, tests, mandatory gates and synchronization receipts exist, the implementation status remains `EFFECT_ACK_CONTINUE`.
