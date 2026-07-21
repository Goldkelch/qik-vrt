<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# GOAI 2026 Agent Infra preparation

**Preparation status:** preliminary submission narrative ready; organizer
registration and acceptance of terms not completed; AgentTeams multi-agent
extension designed below but not yet implemented.

## Verified event fit

The [GOAI Global Open-source AI Challenge](https://www.goaihz.com/en) is open
to worldwide individual and team participants. Its
[Agent Infra track](https://www.goaihz.com/en/tracks?track=infra) targets
multi-agent infrastructure with reusable skills, tool integration, runtime
verification, evidence capture, and security auditability.

Preliminary submissions close on **2026-08-16** according to the track page.
They require a short project introduction and proposal deck; runnable code is
optional in the preliminary stage. The organizer may change the schedule, so
the authenticated submission portal remains controlling.

## Proposed entry

**QIK-VRT Effect Gate — Auditable Release Decisions for Multi-Agent Systems**

QIK-VRT supplies the effect-release and verification layer for a multi-agent
software-development loop. Proposed enterprise scenario:

```text
defect or change request
→ evidence and provenance review
→ risk and policy classification
→ bounded implementation or containment
→ independent result verification
→ QIK-VRT effect haltpoint
→ DONE-only release or explicit non-release path
→ audit and experience capture
```

## Required AgentTeams design baseline

The track requires at least three distinct agent roles and AgentTeams as the
collaboration baseline. Proposed identities:

| Agent | Capability boundary | Output |
|---|---|---|
| Provenance & Evidence Agent | Collects and canonicalizes repository state, requirements, test evidence, hashes, and source provenance; cannot authorize release | Evidence bundle with unresolved questions |
| Risk & Policy Agent | Classifies candidate effects, checks policy and security boundaries, proposes `CONTINUE`, `ISOLATE`, or `BLOCK`; cannot execute release | Risk/policy decision with reasons |
| Verification & Release Agent | Re-runs declared checks, validates bindings, calls the QIK-VRT haltpoint, and may commit only when the gate returns `DONE` | Responsibility protocol, release receipt, or non-release path |
| Human accountable owner | Required for high-risk approval, scope changes, and irreversible effects | Explicit authorization or refusal |

The controller decomposes work, passes content-addressed shared state, and
records every agent/tool transition. No agent may convert technical success
into release permission outside the haltpoint.

## Mandatory reusable Skill

**Skill name:** `qikvrt-effect-release`

| Field | Definition |
|---|---|
| Purpose | Classify a bounded candidate effect and return a five-state QIK-VRT result |
| Inputs | Candidate effect, input hash, context, evidence refs, risk, policy version, responsible owner, deadline |
| Outputs | State, ordinary-release boolean, reasons, next checks, immutable responsibility protocol, protocol hash |
| Invocation | Before any ordinary external commit or release |
| Dependencies | QIK-VRT reference engine; authenticated tool adapters; shared-state store |
| Failure handling | Timeout, malformed binding, missing evidence, or corrupt predecessor never yields `DONE` |
| Security boundary | Skill cannot authenticate evidence it did not receive through a trusted adapter and cannot bypass external enforcement |
| Reuse | AI-agent actions, software release, incident response, administrative workflow, publication gate |

## Context and observability plan

The track requires at least two of agent memory, RAG, shared state, and
trajectory observability. The minimum competition implementation will use:

1. **Shared state management:** content-addressed evidence bundles, versioned
   responsibility protocols, stable request IDs, and replay-conflict
   isolation.
2. **Trajectory observability:** structured logs for role transitions, tool
   calls, states, timings, evidence hashes, reasons, and final authorization.

RAG remains optional. If later used for standards, runbooks, or prior incident
records, retrieved text must be treated as evidence input rather than automatic
truth.

## Tool contract and MCP path

The existing OpenAPI handler provides a stable alternative tool contract with
authentication, schemas, errors, idempotency, and audit records. A competition
adapter can expose the same bounded operations through MCP without redesigning
the QIK-VRT state machine. The adapter must preserve repository scope, secret
separation, size limits, request IDs, and DONE-only enforcement.

## Preliminary deliverables prepared

- Project introduction: [SUBMISSION.md](SUBMISSION.md)
- Proposal deck: competition jury deck generated outside the fixed release
- Architecture and role design: this document
- Evidence and current progress: [EVIDENCE.md](EVIDENCE.md)
- Safety and claim boundaries: `STATUS.md`, `docs/BOUNDARIES.md`, and
  `docs/QIKVRT_THREAT_MODEL.md`
- License disclosure: `LICENSE`, `LICENSE_TRANSITION.md`, and
  `COMMERCIAL_USE_POLICY.md`

## Work required for the semi-final

- Implement the AgentTeams orchestration and identity list.
- Package `qikvrt-effect-release` as an invocable Skill.
- Add shared-state and trajectory-observability adapters.
- Provide sample input/output, configuration, and no-secret demo data.
- Run a complete multi-agent software-change scenario including exception,
  human approval, rollback path, and audit export.
- Publish an executable package, logs/trace/metrics, evaluation results, and a
  runnable demo or video.
- Recheck organizer terms and license disclosure before submission.

These are `CONTINUE` items. They must not be represented to judges as already
implemented merely because the single-gate reference architecture exists.

