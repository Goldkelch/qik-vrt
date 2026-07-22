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
