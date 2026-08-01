<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# IETF applicability profile: epistemic fairness and observation transparency

## Status and scope

This is a draft-only applicability profile for the individual Experimental
Internet-Draft candidate in the IETF stream
`draft-lohmann-qikvrt-epistemic-fairness-observation-profile-00`.

It has not been submitted to the IETF Datatracker. It is not an RFC, an IETF
standard, a working-group product, an implementation report, an endorsement,
or evidence of deployment. The Datatracker and the IETF archive, not this
repository text, determine whether any Internet-Draft has been submitted and
its current status.

The profile builds on the existing version-1 QIK-VRT EFFECT_ACK record without
changing it. It adds no wire member, state, message type, media type, CDDL rule,
registry, or release condition. The five EFFECT_ACK outcomes, closed 35-member
version-1 record, version negotiation, hash projection, and DONE-only ordinary
release rule remain controlled by `draft-lohmann-qikvrt-effect-ack-02`.

The profile translates two author-supplied concepts into bounded protocol
obligations:

- **Vorstellungskraft** is treated as the ability to form a hypothesis,
  scenario, simulation, or counterfactual. It is not automatically an
  observation, proof, fact, prediction, consent, or effect authorization.
- **Übervorteilung** is treated as a risk of undisclosed informational,
  procedural, economic, technical, or decision power asymmetry. The term does
  not itself prove that an unfair act occurred; a concrete determination needs
  stated criteria, evidence, jurisdiction, and review.

## Purpose

The profile applies when an EFFECT_ACK-controlled application uses observations
about persons, groups, systems, environments, virtual-time replays, simulations,
or physical devices. Its purpose is to prevent technical receipt or software
possibility from being represented as epistemic truth, valid consent, fair
treatment, physical capability, or permission for downstream effect.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and
**OPTIONAL** are to be interpreted as described in BCP 14 when, and only when,
they appear in all capitals.

## Integration with EFFECT_ACK version 1

This profile is an application and policy profile, not a wire extension.
Profile evidence is carried as externally retrievable, content-addressed
objects referenced through the existing `evidence_refs`,
`required_evidence_refs`, `reasons`, `open_questions`, and
`next_required_checks` members. The existing immutable policy triple identifies
the exact policy that makes profile evidence mandatory.

An application claiming conformance to this profile MUST make all required
profile evidence available to the evaluator before it can select
`EFFECT_ACK_DONE`. Missing, inaccessible, unauthenticated, stale, internally
inconsistent, or digest-mismatched required profile evidence MUST prevent
ordinary release. The base protocol still determines whether the resulting
state is CONTINUE, ISOLATE, BLOCK, or another non-releasing outcome.

Nothing in this profile permits an evaluator to trust a claimed state string
without independently applying the version-1 validation and state-selection
rules.

## Observation transparency

For every observation used in an effect decision, the application MUST provide
a profile evidence object that discloses at least:

1. whether the item is directly observed, inferred, simulated,
   counterfactual, hypothetical, imagined, or reported by another source;
2. the subject and temporal scope of the observation;
3. the collection or generation method and its material assumptions;
4. the source, collector or generator role, and applicable model or software
   version;
5. material transformations, filtering, transcription, summarization, or human
   correction;
6. known uncertainty, missing context, measurement limits, and plausible
   alternative explanations; and
7. the exact octet identity or separately specified canonical identity used by
   the EFFECT_ACK evidence reference.

An application MUST NOT relabel a simulation, replay, model output,
counterfactual, or act of imagination as a direct physical observation. It MUST
NOT infer semantic truth merely from byte identity, successful reconstruction,
transport acknowledgement, deterministic execution, or agreement between
software components.

## Authorization and consent

The application MUST distinguish authorization for each relevant operation,
including collection, processing, retention, sharing, publication, model use,
and downstream effect. Permission for one operation MUST NOT be silently widened
to another.

Where consent is the stated basis, the profile evidence MUST identify its scope,
subject, time, information supplied, withdrawal mechanism, and the principal or
system that recorded it. A transport acknowledgement, account possession,
silence, continued service use, or the technical ability to access data MUST
NOT by itself be treated as informed consent.

Where another lawful or policy basis is asserted, that basis and its responsible
principal MUST be disclosed instead of being mislabeled as consent. Withdrawal
or correction cannot undo a completed physical effect, but it MUST be applied to
future release decisions according to the governing policy.

## Provenance

Profile evidence MUST preserve an attributable transformation chain from the
available source bytes to the representation used in the decision. At minimum,
the chain MUST identify:

- source identifiers and content digests;
- collection, transcription, decoding, normalization, and summarization steps;
- model, tool, policy, and material configuration versions;
- automated and human contributions without inferring natural-person identity
  from an unverified identifier;
- timestamps and ordering claims together with their clock and trust boundary;
- corrections, disputes, redactions, and superseding versions; and
- any point at which exact source bytes are unavailable.

Provenance establishes an accountable derivation path within its stated trust
boundary. It does not establish that the originating assertion is true, that a
named person is authenticated, or that independent observers exist.

## Fairness and redress

Before ordinary release, the governing policy MUST identify material benefits,
burdens, information asymmetries, conflicts of interest, and groups or persons
likely to be affected. The application MUST disclose any privileged access,
hidden comparison group, asymmetric error cost, or unavailable appeal path that
could systematically advantage one party over another.

The application MUST provide a reachable redress mechanism appropriate to the
effect. It MUST permit an affected party or authorized representative to obtain
the decision basis allowed by law and policy, contest materially incorrect
inputs, submit corrections, and receive a recorded disposition. A disputed
record MUST NOT be silently overwritten; a correction or appeal outcome SHOULD
be represented as a new attributable version.

This profile does not define a universal mathematical fairness metric. A policy
claiming fairness MUST name its criterion, comparison population, protected
interests, error allocation, jurisdictional assumptions, and known limitations.
Absence of a detected disparity MUST NOT be described as proof of fairness.

## Device and bridge disclosure

An implementation MUST state whether a claimed path is:

- software-only processing;
- deterministic replay or simulation;
- communication between virtual addresses;
- ordinary forward-time network transport;
- sensor input from a physical environment;
- actuator output to a physical environment; or
- a claimed bridge between a virtual model and a physical process.

For every physical device or bridge, profile evidence MUST identify the device
class, operator, direction of information or effect flow, interface, calibration
or validation basis, timing model, authentication boundary, failure modes, and
whether the capability was merely designed, locally demonstrated, independently
replicated, or deployed.

Software possibility MUST NOT be represented as evidence that a corresponding
device, bridge, physical channel, or deployment exists. Virtual-time addressing,
replay, bidirectional virtual dialogue, and deterministic reconstruction MUST
NOT be represented as physical future-to-past signalling, modification of a past
event, superluminal communication, or a demonstrated violation of ordinary
host-time causality.

## Minimum conformance cases

A conformance suite for this profile SHOULD include at least these cases:

| Case | Required result |
| --- | --- |
| Direct observation with complete provenance and valid authorization | Continue through the ordinary version-1 evaluation; this profile alone does not force DONE |
| Simulation labeled as physical observation | Non-releasing result |
| Consent for collection reused as publication consent | Non-releasing result |
| Missing transformation or transcription provenance | Non-releasing result |
| Material asymmetry with no redress path | Non-releasing result |
| Software-only virtual replay described as an existing physical bridge | Non-releasing result |
| Corrected evidence version with predecessor retained | Re-evaluate under the base version-chain and freshness rules |

Passing these cases is evidence about the tested implementation and profile
revision. It is not evidence of universal fairness, factual correctness,
independent interoperability, deployment, physical retrocausality, IETF
consensus, or standards status.

## Security and privacy summary

The principal security risks are forged provenance, fabricated consent,
observation-class laundering, model or policy substitution, concealed device
boundaries, stale-decision replay, asymmetric access to correction mechanisms,
and bypass of the effect gate. Implementations need authenticated provenance,
freshness controls, bounded evidence processing, protected executors, and an
auditable redress path.

Transparency can itself expose sensitive observations, identities, locations,
health information, beliefs, vulnerabilities, or device details. Implementations
MUST minimize disclosed personal data, separate public explanations from
restricted evidence, use scoped pseudonymous identifiers where appropriate,
apply retention limits, and disclose lawful correction or erasure constraints.
A digest is not anonymization.

## IANA and deployment boundary

This profile requests no IANA action. It allocates no media type, protocol
number, registry, state, field, or code point.

No implementation or deployment is asserted by these draft artifacts. A future
submission would remain an individual Experimental proposal unless and until
the IETF process establishes a different status. Repository persistence,
deterministic rendering, a Zenodo record, software execution, or an
Internet-Draft listing would not constitute IETF endorsement or scientific
validation.
