# QIK-VRT manuscript formalization v2.0 (work in progress)

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

## Current verified coverage

The current Std-only package contains **12 kernel-checked atomic bindings**.
Nine bind complete source claims and cover **10 of 20 theorem-like LaTeX
environments** (one claim spans three environments). Three further bindings
are deliberately labeled `SOURCE_SUBCLAIM`: they are checked progress inside a
source theorem, not proof of its pending parent claim.

Complete source-claim bindings:

- `SET-001`: disjoint relative-complement partition;
- `MAP-001`: conditional pullback of the partition;
- `SET-003`: ambient-dimension-independent complement partition;
- `MAP-003`: image-complement inclusion, the equality/disjointness iff,
  injective sufficiency and the bijective codomain-complement case;
- `GAT-004`: persistence of terminal PASS/BLOCK results;
- `GAT-005`: exterior completeness from finite block certificates;
- `GAT-006`: conditional total terminality with explicit certificate
  completeness assumptions;
- `RET-011`: later inputs/evidence do not mutate earlier recursive states or
  immutable records;
- `GAT-002`: factorization through the process map iff the status is constant
  on process fibres.

Checked source subclaims whose aggregate parent remains `PENDING`:

- `QUA-003A`: finite exact Boolean-prefix codes do not determine the underlying
  infinite stream; the metric epsilon-quantizer theorem is still open;
- `DIM-006A`: dimension-safe addition; unit-scaling necessity and
  dimensionless transcendental arguments are still open;
- `DIM-007A`: explicit integer-coordinate null and timelike Minkowski
  witnesses; transport to standard real affine spacetime is still open.

The remaining aggregate theorem obligations are `ESC-003`, `ESC-004`,
`ESC-005`, `QUA-003`, `QUA-004`, `QUA-005`, `GAT-003`, `GAT-007`, `DIM-006`
and `DIM-007`. The generated proof map is the authoritative live ledger.

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
