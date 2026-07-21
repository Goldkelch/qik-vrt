<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Submission copy

## Title

**QIK-VRT Effect Haltpoint: Auditable Release Before Real-World Effects**

## German title

**QIK-VRT-Wirkungshaltepunkt: Prüfen, bevor digitale Ausgaben reale Wirkung
erhalten**

## Tagline

QIK-VRT separates technical output from accountable effect release through
five states, DONE-only authorization, bounded checks, and auditable evidence.

## Fifty-word abstract

QIK-VRT adds an auditable effect haltpoint between digital output and ordinary
release. Five states, DONE-only authorization, fail-closed behavior, versioned
evidence, and responsibility records are publicly implemented. The fixed
release is hash-bound and verified by 102 tests, separating technical delivery,
semantic effect, and accountable decision in consequential information
systems.

## 150-word pitch

Digital systems usually acknowledge transport, processing, or program
completion. They do not automatically determine whether a resulting effect
may be responsibly released. QIK-VRT addresses this boundary. Its public
effect haltpoint classifies candidate effects as NACK, CONTINUE, DONE, ISOLATE,
or BLOCK; only DONE permits ordinary release. Provenance, context, evidence,
policy, responsibility, and decision are version-bound and recorded for audit.
The reference implementation is bounded and fail-closed: error, timeout, or
incomplete evidence cannot silently become DONE. Release
v2026.07.20-wirkungshaltepunkt-evolution is tied to an immutable commit,
content-tree SHA, and document SHA-256. Its verification set contains 102 tests
across nine modules, including 41 protocol and conformance tests. QIK-VRT
therefore supplies a falsifiable reference control layer for systems whose
technical outputs can produce real consequences. It is designed for reuse in
AI, administration, platforms, scientific evidence chains, and other
consequential workflows. Independent reproduction, external security review,
production validation, and broad adoption remain open next steps.

## Problem

Network acknowledgements, successful function returns, and exit code `0`
establish technical events. They do not establish that origin, meaning, risk,
evidence, policy, and responsibility are sufficient for downstream effect.

## Solution

QIK-VRT inserts a bounded decision gate between a candidate effect and its
ordinary commit. The closed state set is:

- `EFFECT_NACK`
- `EFFECT_ACK_CONTINUE`
- `EFFECT_ACK_DONE`
- `EFFECT_ACK_ISOLATE`
- `EFFECT_ACK_BLOCK`

Only `DONE` authorizes ordinary release. Errors, timeouts, missing evidence,
integrity failures, and unresolved responsibility do not default to `DONE`.

## Verifiable innovation claim

The implementation combines a semantic candidate effect, bounded synchronous
decision, five normative states, DONE-only release, versioned evidence,
canonical hash binding, responsibility records, audit, replay control, and
re-entry paths. It does not claim that policy enforcement or interruption in
general was invented here; historical priority remains a separate review.

## Potential value

The architecture targets settings in which technical outputs have external
consequences: AI-agent actions, administrative decisions, platform operations,
scientific evidence chains, publication workflows, and security-relevant
automation. The current evidence establishes a reference implementation and
testable contract, not measured production impact.

## Foundational research

The ontology of difference is presented by the author as a universal,
transcendental condition of determination: denying difference already requires
distinguishing the denial from its negation. The software is a constructive
operationalization of that foundation. This does not collapse separate proof
levels: a mathematical derivation, an executable software instance, an
empirical physical correspondence, and a personal spiritual interpretation
retain their own validation paths.

## Limitations

- Reference implementation, not universal production certification.
- No independent third-party reproduction or external security audit yet.
- The IETF document is an Internet-Draft, not an RFC or Internet standard.
- HMAC authenticates with a shared secret; it is not a publicly verifiable
  digital signature.
- The mirrored repository proves content equality, not independent scientific
  reproduction.
- The active code license is source-available and noncommercial, not
  OSI-approved open source.

