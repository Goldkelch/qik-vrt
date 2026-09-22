# QIK-VRT MVP — Exact-Subject Recovery Contract

Status: normative MVP acceptance contract
Authority: Goldkelch/qik-vrt

## Equivalence

QIK-VRT MVP <=>
- NO CLAIM BEYOND EVIDENCE
- NO MUTATION WITHOUT EXACT SUBJECT
- NO PREDECESSOR EVIDENCE TRANSFER
- NO VALIDATION-AS-PERSISTENCE
- NO TRANSPORT_ACK-AS-EFFECT_ACK
- RECURSIVE RECOVERY UNTIL VERIFIED EFFECT

## Current exact-subject recovery case

TARGET
  repository = Goldkelch/qik-vrt
  basename = qikvrt_productive_recovery.py

CURRENT_STATE
  PATCH_IDENTIFIED = TRUE
  REPOSITORY_SOURCE_BINDING = NOT_ESTABLISHED
  PATCH_APPLICATION_AUTHORIZED_BY_EVIDENCE = FALSE
  SUCCESSOR_HEAD = UNKNOWN
  SUCCESSOR_TREE = UNKNOWN
  EFFECT_ACK_DONE = FALSE

SEARCH_EVIDENCE
  byte_identical_carrier = NOT_ESTABLISHED
  exact_path = UNKNOWN
  exact_HEAD = UNKNOWN
  exact_TREE = UNKNOWN
  all_open_PRs_scanned = FALSE
  all_branch_trees = FALSE
  global_absence = NOT_ESTABLISHED

No observation of the same state counts as progress.

## Required next material transition

COMPLETE_SUCCESSOR_TREE_SEARCH

If no candidate is found in a partial search:
  preserve UNKNOWN and continue the search.

If a candidate is found:
1. read candidate bytes;
2. require exactly 8986 bytes;
3. require exact SHA-256 equality with the supplied BASE fingerprint;
4. require exact Git-blob identity with the supplied BASE object;
5. bind immutable {repository, path, HEAD, TREE, blob}.

Only after that binding may PATCH_APPLICATION_AUTHORIZED_BY_EVIDENCE become TRUE.

## Mutation and closure

After evidence-authorized binding only:

APPLY_PATCH
  -> MUTATION
  -> REBIND NEW EXACT SUBJECT {HEAD, TREE}
  -> FRESH VALIDATION
  -> EXECUTION
  -> EFFECT READBACK
  -> EFFECT_ACK evaluation

Mutation invalidates predecessor subject binding. Fresh gates are not applicable before the new HEAD/TREE exists.

## Deadlock semantics

DEADLOCK_CONFIRMED is a truthful intermediate state, not completion and not permission to substitute evidence.

rerun != repair
validation != persistence
TRANSPORT_ACK != EFFECT_ACK
UNKNOWN => FAIL_CLOSED
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
CLAIM_SCOPE <= EVIDENCE_SCOPE

## Persistence requirement

This contract is part of the Mesh inheritance surface defined by MESH_EFFECT_EVIDENCE_INHERITANCE_V1.md. Every conforming current or future Mesh node/repository MUST inherit this MVP contract or an Authority-bound byte-identical canonical reference before it may claim QIK-VRT MVP conformance.

MVP completion requires a freshly verified postcondition and must never be inferred merely from this document, a dispatch, a workflow start, validation, persistence attempt, or authority-independent predecessor evidence.
