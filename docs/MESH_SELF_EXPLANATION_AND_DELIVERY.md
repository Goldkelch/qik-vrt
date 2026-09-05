# QIK-VRT Mesh self-explanation and delivery contract

This file is an ordinary human/machine entrypoint into the QIK-VRT evidence model.

## Start here

QIK-VRT preserves distinctions that must not be collapsed:

```text
BYTES != MEANING
SEQUENCE != CAUSALITY
TRANSPORT_ACK != EFFECT_ACK
OBSERVATION != TRUTH
MODEL != REALITY
FORMAL_VERIFIED != PHYSICAL_CORRESPONDENCE
REPOSITORY_EVIDENCE != ZENODO_PUBLICATION
ZENODO_PUBLICATION != EMPIRICAL_CONFIRMATION
DELIVERY_PREPARATION != DELIVERY_ACCEPTED
```

The central operational chain is:

```text
DISTINCTION
-> OBSERVATION / MEASUREMENT
-> REPRESENTATION / INFORMATION
-> PROVENANCE + UNCERTAINTY
-> CLAIM CLASSIFICATION
-> CAUSALITY ASSESSMENT
-> AUTHORIZATION
-> EFFECT
-> READBACK
-> NEXT STATE
```

## Delivery rule

When Product/Code Owner Ingolf Lohmann requests Zenodo publication before a document is delivered, the document is **not an accepted delivery** until all of the following are true for the exact frozen candidate:

1. candidate bytes and metadata are frozen and hash-bound;
2. required machine-proof, claim classification, provenance and rights gates are satisfied;
3. the authorized Zenodo production effect has executed;
4. the public Zenodo record and DOI resolve;
5. the public file names, sizes and checksums match the frozen upload manifest;
6. the public metadata matches the authorized metadata.

A local file, chat attachment, repository commit, pull request, workflow artifact, Zenodo draft, reserved DOI, publication intent or monitoring task is preparation/evidence only. None of these is a substitute for the public Zenodo readback.

Normative machine-readable policy: `policy/DELIVERY_ACCEPTANCE_ZENODO_V1.json`.

## How every client must remove ambiguity

A conforming client must not answer an unresolved material question with plausible inference. It must guide the user/system through the following path until each material question is either resolved by evidence or explicitly classified:

1. **Subject** — What exact object, commit, tree, file, record or physical claim is being discussed?
2. **Scope** — What does the claimed status apply to, and what is outside scope?
3. **Claim class** — Repository fact, formal theorem, implementation result, publication state, empirical measurement, interpretation, normative rule or owner assertion?
4. **Evidence** — What exact receipt, hash, run, DOI, measurement or source supports it?
5. **Boundary** — Which neighboring stronger claims do *not* follow?
6. **Uncertainty** — What is still unknown or stale?
7. **Next action** — What is the smallest authorized action that can resolve the uncertainty?
8. **Readback** — What actually happened after the action?
9. **Successor state** — What remains `OPEN`, `HOLD`, `REOBSERVE` or `REQUEST_AUTHORITY`?

No material doubt may be hidden. "Doubt removed" means either evidence resolved the question or the unresolved remainder is explicitly bounded. It never means manufactured certainty.

Normative machine-readable policy: `policy/MESH_SELF_EXPLANATION_V1.json`.

## Adaptation contract

Downstream Mesh nodes and adapters may add stronger checks, richer metadata, domain-specific schemas and local execution logic. They may not weaken the core semantic distinctions above. At minimum they must preserve:

- provenance;
- exact-subject binding;
- claim/evidence class;
- uncertainty;
- authorization boundary;
- effect readback.

A missing mandatory field or stale binding is fail-closed, not implicit success.

## Scientific information-effect axis

For measurement-bearing systems, the reusable bridge is:

```text
physical phenomenon
-> sensor interaction
-> bandwidth / anti-alias assumptions
-> sampling
-> quantization
-> digital representation
-> measurement metadata
-> provenance
-> claim
-> causality assessment
-> authorization
-> effect
-> readback
```

The minimum measurement envelope is:

```text
(value, time, uncertainty, unit, calibration, provenance)
```

A hash binds bytes, not meaning. Calibration binds measurement context, not causal truth. Publication binds public archive state, not empirical confirmation.

For the full synthesis and public-language bridge, continue to:

- `docs/research/2026-09-05-information-effect-axis/MANUSCRIPT.md`
- `docs/research/2026-09-05-information-effect-axis/PROSA_ARTIKEL_FUER_ALLE.md`
- `docs/research/2026-09-05-information-effect-axis/QIKVRT_INFORMATION_EFFECT_AXIS_V1.json`
- `docs/research/2026-09-05-information-effect-axis/QIKVRT_ZENODO_PRIOR_ART_V1.json`

## Bootstrap

Artificial-cognitive systems must still begin at `/AI` and follow `AI_CONTEXT.json`. This document is an explanatory and interoperability surface, not a replacement for the repository boot protocol.
