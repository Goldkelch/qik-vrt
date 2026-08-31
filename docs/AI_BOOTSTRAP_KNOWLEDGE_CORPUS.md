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

## Canonical argumentation entrypoint

Every further repository-level argument begins with
[`policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json`](../policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json)
and its [human contract](CANONICAL_ARGUMENTATION_ENTRYPOINT.md). The contract
reuses the existing QIK-VRT claim classes and makes scope, causal bridge,
evidence binding, non-transfer after head/tree drift, and guarded inference
machine-checkable. It preserves `OWNER_ASSERTED_REALITY_CORRESPONDENCE` as a
bound Product-Owner assertion while keeping it distinct from independent
empirical confirmation and scientific consensus.

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
4. CANONICAL ARGUMENTATION ENTRYPOINT
5. REPOSITORY STATUS / CLAIM / PROOF AUTHORITIES
6. RUNTIME BOOTLOADER AND INTEGRITY GATES
7. AUTHORIZED TASK
8. PROVENANCE-BOUND RESULT
9. HUMAN REVIEW
10. IF APPLICABLE: PHYSICAL / EXTERNAL EFFECT REOBSERVATION
```

The corpus enriches orientation. Repository-native exact-head evidence still
wins over posters, manuscripts, audio, chat memory and model recollection when a
current technical state is at issue.
