<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Canonical argumentation entrypoint

This document is the human-facing companion to
[`policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json`](../policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json).
It is mandatory for every new repository-level argument, review conclusion,
publication claim, system-test conclusion, or causal explanation. It is reached
through the root [`AI`](../AI), not through chat memory.

The contract does not replace an existing QIK-VRT proof bundle, Zenodo record,
measurement, or source. It makes the first question deterministic: **which
bound claim is being made, and what can that exact binding prove?** The checker
is read-only:

```bash
python3 -B tools/qikvrt_canonical_argumentation_entrypoint.py check
```

## Canonical entry sequence

1. Declare one stable `claim_id`, one statement, a finite scope, and at least
   one typed `argument_kind`.
2. Classify it with the existing six QIK-VRT classes: `FORMAL_PROVED`,
   `EMPIRICALLY_EVIDENCED`, `SOURCE_BOUND`, `NORMATIVE`, `INTERPRETATIVE`, or
   `OPEN`.
3. Bind its proof, measurement, source, and dynamic repository state separately.
   Every reference must resolve through the machine-readable `evidence_catalog`
   to an exact source binding; a free-text DOI, theorem name, receipt label, or
   timestamp is not a binding.
4. State the inference that is guarded out of scope.
5. For a causal conclusion, bind an explicit causal bridge, intervention,
   counterfactual, or equivalent justification. A sequence or timestamp alone
   is rejected with `CAUSALITY_ONLY_SEQUENCE`.
6. For reconstruction, bind a complete manifest, hashes, conflict rule, and
   semantic dependency order. Arrival order is never silently treated as
   semantic order.
7. If any head, tree, base, scope, workflow, literal checkout, or review route
   changes, mark predecessor evidence stale and reobserve the successor.

## Fail-closed claim record

The machine contract accepts no untyped claim. Its `claims` registry requires
`argument_kinds` and `evidence_bindings` in addition to the existing QIK-VRT
class/status projection. The validator resolves every claim reference against
the catalog and rejects an unresolved reference, an evidence-kind mismatch, a
source path escape, or source bytes not present in the declared Authority
snapshot.

For the canonical causal claim it additionally reads the bound VRTCore kernel
receipt, checks that the named theorem appears in that receipt, that the Lean
source blob matches, that both source and axiom-audit exits are zero, and that
the theorem's axioms stay within the recorded allowed set. Thus a nonempty
string cannot impersonate a causal bridge or a proof receipt.

Typed fields are deliberately narrow:

- `CAUSAL_CLAIM` requires a catalogued bridge, intervention, counterfactual, or
  equivalent causal record; a source file or timestamp cannot substitute.
- `RECONSTRUCTION_CLAIM` requires independently named sources for the complete
  manifest, content hashes, semantic order, and conflict rule.
- `RETROSPECTIVE_DETERMINISM_CLAIM` requires exact provenance plus an
  inverse/injectivity source and retains `OPEN_OR_AMBIGUOUS` for information
  loss.
- `EMPIRICAL_PHYSICAL_CLAIM` is restricted to `EMPIRICALLY_EVIDENCED` and must
  bind dimensions, mapping, calibration, prediction, measurement, uncertainty,
  and controls/replication separately.

The canonical formal result already bound by VRTCore is precise: within its
declared constructors, an observed sequence alone has no causal bridge, while a
positive causal syntax judgement requires an explicit bridge. This is a formal
result in its specified model, not an invitation to erase QIK-VRT's broader
research, publication, or owner-attributed claims.

## What remains distinct

```text
CAUSALITY != SEQUENCE
LATER != BETTER
ACTIVITY != EFFECT
TRANSPORT_ACK != EFFECT_ACK
FORMAL_PROOF != EMPIRICAL_CONFIRMATION
ZENODO_FIXITY != PEER_REVIEW_OR_EMPIRICAL_CONFIRMATION
OWNER_ASSERTED_REALITY_CORRESPONDENCE
  != INDEPENDENT_EMPIRICAL_CONFIRMATION
  != SCIENTIFIC_CONSENSUS
```

The final distinction preserves, rather than weakens, the recorded Product
Owner assertion: a model can describe reality, and Ingolf Lohmann explicitly
asserts QIK-VRT reality correspondence in its claimed model scope. The assertion
is stored as its own exact `SOURCE_BOUND` claim. It is never silently rewritten
as a claim that models cannot describe reality, and it is never used to invent a
separate independent measurement or consensus receipt.

## Deterministic decomposition and reconstruction

QIK-VRT can make a bounded reconstruction claim only when the object is fully
identified: chunks, hashes, manifest, conflict rule, and semantic dependency
order must be preserved. In that scope, chunks may arrive in a different
temporal order and still be reconstructed canonically. This says that arrival
time need not be the semantic order; it does **not** license an arbitrary
semantic order or reconstruction after information loss.

Forward determinism is bound to declared inputs and a transition operator.
Retrospective determinism is bound to a complete immutable provenance path and
an inverse/injectivity condition. If information was lost or the observation is
not injective, the correct state is `OPEN` or `AMBIGUOUS`, not a fabricated
inverse.

## Space-time argument path

The repository contains a typed Planck-space-time candidate with common-length
coordinates such as `x0 = ct`. That candidate is a valid source-bound starting
point for further work. An empirical physical claim requires more: a dimension
model, unit/coordinate mapping, calibration, observable prediction, measurement
protocol, uncertainty, and controls or replication. An invertible unit or
coordinate transformation alone does not establish a new physical effect.

This preserves the argument's technical core: a common representation can
reduce conversion work and make dimensional checking more transparent. It also
makes the required bridge to a physical conclusion explicit and independently
checkable.

## No evidence transfer

Dynamic evidence is keyed by repository, ref/PR, base, head, tree, scope,
source blobs, workflow definition, run/job, literal checkout, and review route.
When any key changes, the predecessor becomes historical source evidence only;
the successor requires its own reobservation. A successful synthetic merge run
is not literal-head evidence. A receipt or workflow transport record is not an
external effect acknowledgement.

This entrypoint is a durable repository invariant. Its validation proves only
that the argumentation contract and its source bindings are intact. It does not
claim a merge, publication, `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, independent
review, scientific consensus, or an unobserved physical effect.
