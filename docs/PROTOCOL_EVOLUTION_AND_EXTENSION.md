<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT Protocol Evolution and Extension Contract

## Purpose

This contract materializes the Product Owner authorization to evolve the
QIK-VRT Effect Acknowledgement Protocol, define further QIK-VRT protocols, and
prepare suitable extension profiles for existing protocols.

The authorization is architectural and repository-internal. It permits
specification, schema, state-machine, reference-implementation, formal-model,
conformance, interoperability, adversarial-test, migration, deprecation and
review work. It does not itself authorize an IETF Datatracker submission, an
IANA or other registry request, a release, deployment, Zenodo publication,
credentialed external write, merge, or activation in an external system.

Machine-readable authorities:

- `state/authorization/delegations/OWNER_PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json`
- `policy/PROTOCOL_EVOLUTION_AND_EXTENSION_V1.json`
- `schemas/qikvrt_protocol_change_envelope_v1.schema.json`

## Existing Effect ACK core

The current core remains the five-state model:

1. `EFFECT_NACK`
2. `EFFECT_ACK_CONTINUE`
3. `EFFECT_ACK_DONE`
4. `EFFECT_ACK_ISOLATE`
5. `EFFECT_ACK_BLOCK`

The release invariant remains:

`ordinary_release(result) == (result.state is EFFECT_ACK_DONE)`

This authorization does not silently add a sixth state, weaken a DONE
predicate, or reclassify a transport acknowledgement as an effect
acknowledgement.

## Suitable extension strategy

The default extension form is an orthogonal, versioned envelope or profile.
This preserves the closed five-state core while allowing additional evidence
planes to be bound:

- authorization;
- execution;
- observation;
- receipt;
- single-use consumption;
- recovery.

Such an extension can require additional evidence before
`EFFECT_ACK_DONE`. It may never make DONE easier to reach than the core
contract. Unknown critical extensions fail closed. Unknown non-critical
extensions may be ignored only when their exact bytes are preserved for later
interpretation.

A core-state or release-invariant change is a major revision candidate. It
requires an independently established normative delta, explicit migration and
dual-read evidence, conformance and adversarial tests, repository-native review,
and a separately authorized promotion.

## Protocol change classes

Every candidate is classified as exactly one of:

- `NO_PROTOCOL_CHANGE_REQUIRED`
- `NON_NORMATIVE_CLARIFICATION`
- `COMPATIBLE_EXTENSION_PROFILE`
- `NEW_QIKVRT_PROTOCOL`
- `EXTERNAL_PROTOCOL_EXTENSION_CANDIDATE`
- `MAJOR_EFFECT_ACK_REVISION_CANDIDATE`
- `REJECT_OR_DEFER`

`NO_PROTOCOL_CHANGE_REQUIRED` remains the correct disposition until a concrete
wire, state-machine, security, interoperability or other normative delta is
established. Product Owner permission to develop protocols is not itself a
technical delta.

## Reuse before creation

Existing QIK-VRT components are examined before new machinery is introduced,
including:

- `src/qikvrt_effect_ack.py`;
- `external/ietf/EFFECT_ACK_PROTOCOL_SUMMARY.json`;
- `tests/test_effect_ack_conformance.py`;
- existing responsibility protocols, targeted-effect envelopes, receipt
  formats, authorization controls and recovery contracts.

A new protocol is justified only when an existing protocol, profile, extension
point or schema cannot express the requirement without ambiguity or unsafe
coupling.

## Existing external protocols

QIK-VRT may define an extension candidate or interoperability profile for an
existing external protocol only when one of these is true:

- an official extension point is used according to the upstream protocol;
- a private-use or experimental mechanism is explicitly labelled;
- a new independent protocol is used without claiming upstream authority.

No code point, media type, URI scheme, header field, IANA assignment, IETF
status, standards consensus or third-party namespace authority is inferred
before the corresponding external process independently establishes it.

## Required change envelope

Every protocol candidate binds:

- exact source commit and tree;
- problem and interoperability gap;
- reuse analysis;
- change class and normative delta;
- affected protocols and authorities;
- version, compatibility and unknown-extension behavior;
- wire and state-machine impact;
- security, privacy, rights and abuse analysis;
- interoperability impact;
- migration, rollback and deprecation;
- conformance, interoperability and adversarial tests;
- formal and implementation evidence or explicit open/not-applicable states;
- IETF, registry and upstream disposition;
- repository and external-effect boundaries;
- non-claims.

The JSON schema is closed and fail-closed for the effect boundary:
repository-internal design is permitted, while external effect, credential use
and promotion remain false until separately authorized.

## Gate order

1. Reobserve current main, exact head and tree.
2. Establish a single writer or an explicit stack.
3. Reuse existing components or document technical insufficiency.
4. Classify the normative delta and change class.
5. Bind version, wire, state, security, privacy, rights and interoperability.
6. Implement schemas, conformance and adversarial tests.
7. Add formal evidence or an explicit reason why it is not applicable.
8. Regenerate repository-native integrity.
9. Require every applicable exact-head gate to be terminal.
10. Review and promote separately.
11. Evaluate any IETF, registry, release, deployment or publication action as a
    new exact-artifact external effect.

## Scientific and standards boundary

Formal protocol proof is model-relative. Conformance of one implementation does
not establish global interoperability. Repository acceptance does not establish
IETF or other standards consensus. Protocol work does not establish physical
correspondence or scientific confirmation.

Current completion claims remain:

- `PASS = false`
- `FINAL_PASS = false`
- `EFFECT_ACK_DONE = false`
- `IETF_SUBMISSION = false`
