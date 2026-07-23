# Batch 01B: analytic and topological proof plan

This is the next kernel tranche after the Std-only core. It is pinned to:

- Lean `v4.19.0` (`6caaee842e9495688c1567e78c0e68dbb96942aa`)
- mathlib tag `v4.19.0`
- mathlib commit `c44e0c8ee63ca166450922a373c7409c5d26b00b`

The dependency is not added to the current Std-only package until all imported
module revisions and the resulting `lake-manifest.json` are locked.

## Ordered proof tranche

1. **GAT-003 — finite-tail boundedness.** Prove for every pseudometric space
   that `range (fun n => u (n + k))` is bounded iff `range u` is bounded. The
   reverse direction is the union of the bounded finite prefix with the bounded
   tail. This is the actual shift-invariance argument used by the manuscript,
   rather than invariance of a separately stored parameter.

2. **GAT-007 — classifier/frontier theorem.** For a set `s` and its classical
   Bool membership classifier, prove `ContinuousAt classifier x ↔ x ∉ frontier
   s`. For the manuscript, instantiate the ambient type as the subtype `U`, so
   `frontier` is the relative boundary. This proves a topological statement,
   not computable decidability of Mandelbrot membership.

3. **QUA-003/004/005 — metric epsilon nets and the exact countermodel.** Define a finite codebook and encoder
   with error at most positive `ε`. Use compact closure of bounded sets in
   finite-dimensional real normed spaces and a finite ball cover. The result is
   existential/classical; an executable grid encoder is a separate obligation.
   The Euclidean specialization uses `EuclideanSpace ℝ (Fin d)`, not an
   unspecified norm on `Fin d → ℝ`. Then instantiate `[0,1]^4` and prove that
   it has no least positive distance, completing the metric parent claim behind
   checked representation subclaim `QUA-003A`. The finite-net claim is false
   for arbitrary bounded subsets of infinite-dimensional normed spaces.

4. **DIM-006/007 — full dimensional and real-spacetime bridges.** The checked
   subclaim `DIM-006A` already enforces dimension-safe addition; add the
   unit-scaling invariance theorem and dimensionless-argument obligations for
   exp/log/sin/cos. The checked subclaim `DIM-007A` already supplies exact
   integer-coordinate null and timelike witnesses for signature `(-+++)`;
   transport them into standard real affine Minkowski spacetime and bind the
   aggregate source claim. Transport to another Lorentz form only under an
   explicit form equivalence. On a general manifold, `q-p` is not canonical.

5. **ESC-004/005 and ESC-003 — concrete escape radius.** Define the critical
   orbit `z₀=0`, `zₙ₊₁=zₙ²+c`. Prove the lower norm recurrence, parameter bound
   at the first escape witness, geometric growth of the shifted tail and then
   `Tendsto (fun n => ‖z n‖) atTop atTop` from `2 < ‖z n‖`. Derive
   unboundedness, the finite escape witness characterization and the union of
   finite escape sets. The threshold statement is not valid for arbitrary
   initial values without an additional parameter-dependent bound.

## Principal mathlib APIs

- Escape: `norm_sub_norm_le`, `norm_pow`, `tendsto_atTop_of_geom_le`,
  `tendsto_add_atTop_iff_nat`, `isBounded_iff_forall_norm_le`.
- Quantization: `Bornology.IsBounded.isCompact_closure`,
  `exists_finite_cover_balls_of_isCompact_closure`,
  `FiniteDimensional.proper`.
- Tail: `Set.finite_Iio`, `Set.Finite.image`, `Set.Finite.isBounded`,
  `Bornology.IsBounded.union`, `Bornology.IsBounded.subset`.
- Boundary: `ContinuousAt.preimage_mem_nhds`, `mem_interior_iff_mem_nhds`,
  `compl_frontier_eq_union_interior`, `isClopen_iff_frontier_eq_empty`.
- Lorentz: `QuadraticMap.sq`, `QuadraticMap.prod`,
  `QuadraticMap.not_anisotropic_iff_exists`, `QuadraticMap.PosDef.nonneg`.

Every completed claim must receive a raw manuscript span, an exact
`Statement`/`_checked` pair, an indexed registry constructor, a Lean source
fingerprint and a `#print axioms` result before the ledger status can change
from `PENDING`.
