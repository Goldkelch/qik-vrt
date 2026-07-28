# QIK-VRT manuscript formalization v2.0

This directory is the theorem-by-theorem reconstruction of the 62-page
manuscript **Mandelbrot, Anschlussordnung, Physik und Retrokausalität**.
The published v1.0 package remains unchanged as an archival baseline.

## What “machine-checkable manuscript” means here

The project distinguishes four separate obligations:

1. **Source coverage** — every formal LaTeX environment and every row of the
   appendix claim matrix has a stable identifier and an exact source span.
2. **Logical coverage** — definitions, assumptions and dependency edges are
   explicit and acyclic.
3. **Kernel coverage** — mathematical claims have a Lean `statement` and a
   Lean theorem `checked : statement`; names alone are not accepted as proof
   bindings. The ledger also locks the defining module and proposition-indexed
   registry bytes by SHA-256.
4. **Epistemic coverage** — empirical, interpretive and normative claims are
   classified and testable as metadata, but are never promoted to mathematical
   theorems about nature.

The phrase “fully formalized” is release-gated until all 20 definitions are
typechecked, all 20 theorem-like environments are kernel checked (or explicitly
and accurately represented as conditional statements), and all 34 appendix
matrix rows are classified. Five remarks are tracked as context and do not add
proof obligations.

<!-- qikvrt-global-formalization-coverage:start -->
## Current verified coverage

The locked 62-page manuscript formalization is complete at the formal-environment boundary. The claim graph contains 43 nodes: one locked source anchor and 42 strong Lean bindings. All 20 definitions and all 20 theorem-like environments are closed; six theorem bindings remain explicitly conditional.

The global ledger includes all 43 manuscript graph nodes, all 34 appendix rows, and all 15 EFFECT_ACK claims, with one terminal disposition each. Empirical, interpretive, normative, OPEN and OUT_OF_SCOPE records are preserved without proof inflation.

Authoritative generated views are `claims/CLAIM_GRAPH.json`, `MANUSCRIPT_PROOF_MAP.md`, `VERIFICATION_REPORT.md`, and the repository-root `GLOBAL_CLAIM_INVENTORY.json`.
<!-- qikvrt-global-formalization-coverage:end -->
## Reproducible checks

```sh
python3 scripts/extract_tex_inventory.py --check
python3 scripts/verify_source_lock.py
python3 scripts/validate_claim_graph.py
python3 -m unittest discover -s tests -v
lake build
python3 scripts/audit_lean_axioms.py
```

Lean is pinned by `lean-toolchain`. CI must reject `sorry`, `admit`, project
`axiom` declarations, stale source hashes, missing source environments, cycles,
forbidden category dependencies and proof fields on non-formal claims.
