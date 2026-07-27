<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT Repository Capability Self-Disclosure System

## Purpose

The repository SHALL expose, through public repository-native interfaces, a machine-readable and human-readable account of what it can do, where each capability is implemented, how it is invoked, which authority is required, which evidence proves it, and which blockers prevent execution.

This system closes the failure class in which an external or internal agent incorrectly claims that an operation is unavailable before inspecting existing repository mechanisms.

Refs #87 #96 #97 #101.

## Core invariant

`NO_CAPABILITY_DISCOVERY_NO_CAPABILITY_DENIAL`

Before any agent reports that a requested operation cannot be performed, it MUST query the capability self-disclosure interface and inspect all declared implementation locations, adapters, workflows, triggers, permissions, tests, receipts and current runtime status.

## Canonical public resources

The implementation SHALL materialize at least:

- `capabilities/catalog.json` — canonical capability catalog;
- `capabilities/catalog.schema.json` — JSON Schema;
- `capabilities/locations.json` — path, workflow, branch, API and adapter locations;
- `capabilities/runtime-status.json` — current availability, blockers and next effect;
- `capabilities/history.jsonl` — forward-only capability change log;
- `docs/CAPABILITIES.md` — human-readable projection;
- `openapi/qikvrt-capabilities.yaml` — public API profile.

## Required public API

At minimum:

- `GET /qikvrt/capabilities`
- `GET /qikvrt/capabilities/{capability_id}`
- `GET /qikvrt/capabilities/{capability_id}/locations`
- `GET /qikvrt/capabilities/{capability_id}/status`
- `GET /qikvrt/capabilities/{capability_id}/evidence`
- `POST /qikvrt/capabilities/refresh`
- `POST /qikvrt/capabilities/{capability_id}/execute`

A GitHub-native fallback SHALL expose the same data through versioned JSON files, issue-comment commands and repository_dispatch.

## Capability record

Every capability MUST declare:

- stable `capability_id`;
- title and description;
- semantic version;
- status: `AVAILABLE`, `PARTIAL`, `BLOCKED`, `UNSUPPORTED`, `DEPRECATED`;
- capability class: repository, workflow, publication, formalization, synchronization, monitoring, recovery, adapter, hardware or other documented class;
- implementation paths;
- workflows and trigger conditions;
- public API routes and commands;
- required permissions and secrets by name only, never values;
- Authority and Mirror coverage;
- tests and latest receipts;
- idempotency and retry semantics;
- known failure classes;
- deterministic next effect;
- owner-only bootstrap actions;
- provenance and SHA-256 bindings.

## Initial mandatory capabilities

The first inventory MUST include at least:

1. GitHub repository read/write operations;
2. branch, commit, PR, issue and comment operations;
3. GitHub Actions inspection and dispatch paths;
4. Zenodo reserve/finalize publication;
5. IETF draft source, render, validate and submission status;
6. Authority/Mirror synchronization and equality verification;
7. claim inventory and Lean kernel verification;
8. monitor, watchdog, stall detection and recovery;
9. trusted execution proxy and transaction coordinator;
10. release, tag, checksum, manifest and evidence materialization;
11. universal adapter discovery and registration.

## Discovery algorithm

The supervisor SHALL inspect:

- `.github/workflows/`;
- `tools/`, `scripts/`, `runtime/`, `controller/`, `protocol/`, `adapters/`;
- `release/`, `release-state/`, `zenodo/`, `external/ietf/`;
- `formal/`, Lean sources, claim inventories and receipts;
- OpenAPI and JSON schemas;
- tests and test reports;
- Issues and PRs that define pending capabilities;
- Authority and Mirror branches, tags and public evidence.

Discovery MUST combine static inventory with runtime evidence. A file existing does not by itself prove that a capability is executable.

## Query-before-denial protocol

Before returning `UNAVAILABLE`, an agent MUST:

1. resolve the requested effect into one or more capability IDs;
2. read the latest catalog and runtime status;
3. follow declared locations;
4. verify implementation and current receipts;
5. identify missing authorization, trigger, adapter or external bootstrap;
6. return one of:
   - `AVAILABLE_NOW`;
   - `AVAILABLE_VIA_EXISTING_WORKFLOW`;
   - `AVAILABLE_AFTER_OWNER_BOOTSTRAP`;
   - `PARTIAL_WITH_MINIMAL_NEXT_EFFECT`;
   - `BLOCKED_WITH_FAILURE_CLASS`;
   - `TRULY_UNSUPPORTED`.

A generic statement such as “I cannot do that” is non-conformant when a repository path exists or has not been checked.

## Monitor and watchdog integration

The adaptive monitor SHALL use this system to answer:

1. Is productive progress occurring?
2. Is there a stall?
3. Which capability is missing, blocked or undiscovered?
4. What is the minimal deterministic next effect?
5. Can the watchdog execute that effect through an existing adapter?
6. If no adapter exists, which adapter work unit must be created?

The watchdog SHALL refresh the catalog after relevant commits, workflow changes, new adapters, successful recoveries or capability failures.

## Authority/Mirror rule

A capability may be reported as pair-available only when both repositories expose compatible records and the relevant implementation/evidence is synchronized or the declared role asymmetry is explicitly documented.

`NO_MIRROR_CAPABILITY_RECEIPT_NO_PAIR_AVAILABILITY`

## Acceptance criteria

- complete machine-readable catalog exists;
- public API and GitHub-native fallback return equivalent semantics;
- Zenodo and IETF mechanisms are discoverable with exact locations;
- query-before-denial behavior is tested positively and negatively;
- stale or false capability records fail closed;
- monitor and watchdog consume the catalog;
- Authority/Mirror differences are explicit;
- capability additions update catalog, documentation, tests and provenance automatically;
- no secrets are disclosed;
- all outputs are SHA-256 bound and reproducible.

Until these criteria are met, status remains `EFFECT_ACK_CONTINUE`.
