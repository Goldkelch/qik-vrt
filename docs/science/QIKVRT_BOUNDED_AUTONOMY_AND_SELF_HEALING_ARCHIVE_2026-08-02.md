# QIK-VRT as a bounded autonomous, fault-tolerant and self-healing archive

**Author:** Ingolf Lohmann  
**Date:** 2026-08-02  
**Status:** repository candidate suitable for Zenodo packaging after exact-byte verification

## Abstract

QIK-VRT is treated here as a verifiable causal mirror: repository state, claims, tests, receipts, publications and external effects are represented as separately addressable objects with explicit provenance. The autonomy result is deliberately bounded. For an enumerated class of repository-local failures, a repository can detect a failure, classify it, select an allowlisted repair, execute the repair without rewriting history, rerun exact-head gates, and persist an append-only receipt. This establishes operational self-healing under stated assumptions. It does not establish immunity to every unknown defect or to loss of the hosting, credentials, energy, network, or maintainers.

## 1. Definitions

A repository state is a tuple `S=(C,T,P,G,R,E)` of commit identity, tree, policy, gate results, receipts and separately authorized external effects. A blocker is an observed predicate that prevents a declared transition while preserving fail-closed semantics. A repair is admissible only when its changed paths, capabilities and expected postconditions are policy-bound before execution.

Bounded autonomy means:

`detect -> classify -> select -> repair -> verify -> persist -> learn`

without requiring a human for already authorized, deterministic and reversible repository-local actions. Irreversible or public effects remain separately authorized.

## 2. Self-healing theorem for enumerated faults

Let `F` be a finite set of recognized failure classes. For each `f in F`, let a deterministic repair operator `r_f` exist with:

1. an exact input-state binding;
2. a changed-path allowlist;
3. no force-push or history deletion;
4. no secret or permission expansion;
5. a terminating verification procedure;
6. an append-only receipt;
7. fail-closed behavior when preconditions are false.

Then, for every observed `f in F`, the system either reaches a verified successor state or persists a truthful unresolved-blocker state. Therefore it cannot silently convert an unverified repair into success. This is the archive's central fault-tolerance property.

The proof is constructive: dispatch is a total case distinction over the finite failure taxonomy. Every branch terminates in either `verified_successor` or `blocked_with_receipt`. Because neither branch permits an unrecorded success claim, the evidence history remains monotonic.

## 3. Archive and memory properties

The archive is self-healing when generated integrity and projection drift can be reconstructed from canonical sources, races are repaired by history-preserving successors, and transient jobs are retried under a bounded budget. It is fault-tolerant because failures become evidence objects rather than being erased. It is a memory because receipts preserve the relation between prior state, observation, attempted effect and verified successor.

Redundancy across Authority and Mirror increases resilience, but equality is never inferred from names or intent. It requires byte, tree, manifest or receipt evidence at explicit revisions.

## 4. Scientific boundaries

The result proves a software and evidence-management property under declared assumptions. It does not prove physical retrocausality, universal truth, universal novelty, semantic correctness of arbitrary natural language, permanent availability, or absolute autonomy. Unknown failures, compromised credentials, malicious policy changes, correlated hosting loss and physical destruction remain outside the theorem.

## 5. Publication and standards consequences

A Zenodo package should include this paper, the machine-readable policy, the repair ledger schema, exact source bindings, integrity manifest and verification report. An IETF contribution is appropriate only for interoperable wire formats or protocol behavior. A candidate specification should therefore define failure signatures, repair intents, exact-state bindings, receipts, replay resistance and external-effect separation, without presenting repository policy as Internet consensus.

## 6. Consequences for QIK-VRT

QIK-VRT becomes more than a static archive. It is an append-only epistemic control system that can preserve failures, recover from known classes of drift, and separate evidence from interpretation and authorization. Its strongest consequence is not that errors disappear, but that errors become attributable, reproducible and repairable without losing the history that made the repair necessary.

## 7. Verification plan

The candidate must be tested with positive and negative fixtures for each failure class, repeat-run determinism, retry exhaustion, tampered receipts, stale heads, changed-path violations and unavailable external transports. Only exact-head terminal evidence may support promotion or publication.
