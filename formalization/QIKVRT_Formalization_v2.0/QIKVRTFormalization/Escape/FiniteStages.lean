import Std

/-!
# Finite escape stages

This module isolates the set-theoretic core of the manuscript's staged escape
reconstruction. It does not assume complex arithmetic. Instead it proves that,
for any natural-valued escape time predicate, the finite stages are monotone
and their union is exactly the set of points with a finite escape witness.

The complex Mandelbrot escape-radius lemma remains a separate prerequisite for
identifying this abstract finite-witness exterior with the analytic complement.
-/

namespace QIKVRT.V2.Escape

abbrev PointSet (α : Type) := α → Prop

/-- Stage `N`: points whose escape time has a witness no later than `N`. -/
def Stage (escapeAt : α → Nat → Prop) (N : Nat) : PointSet α :=
  fun x => ∃ n, n ≤ N ∧ escapeAt x n

/-- Exterior by finite witness. -/
def FiniteWitnessExterior (escapeAt : α → Nat → Prop) : PointSet α :=
  fun x => ∃ n, escapeAt x n

/-- Escape stages grow monotonically with their stage index. -/
theorem stage_mono (escapeAt : α → Nat → Prop) {N M : Nat}
    (hNM : N ≤ M) : ∀ x, Stage escapeAt N x → Stage escapeAt M x := by
  intro x hx
  rcases hx with ⟨n, hnN, hEscape⟩
  exact ⟨n, Nat.le_trans hnN hNM, hEscape⟩

/-- Consecutive stages are monotone. -/
theorem stage_succ_mono (escapeAt : α → Nat → Prop) (N : Nat) :
    ∀ x, Stage escapeAt N x → Stage escapeAt (N + 1) x := by
  intro x hx
  exact stage_mono escapeAt (Nat.le_succ N) x hx

/-- Membership in some finite stage is equivalent to possessing a finite witness. -/
theorem exists_stage_iff_finite_witness (escapeAt : α → Nat → Prop) (x : α) :
    (∃ N, Stage escapeAt N x) ↔ FiniteWitnessExterior escapeAt x := by
  constructor
  · rintro ⟨N, n, hnN, hEscape⟩
    exact ⟨n, hEscape⟩
  · rintro ⟨n, hEscape⟩
    exact ⟨n, n, Nat.le_refl n, hEscape⟩

/-- Extensional reconstruction of the finite-witness exterior by all stages. -/
theorem finite_stages_reconstruct (escapeAt : α → Nat → Prop) :
    (fun x => ∃ N, Stage escapeAt N x) = FiniteWitnessExterior escapeAt := by
  funext x
  exact propext (exists_stage_iff_finite_witness escapeAt x)

/-- Exact proposition-indexed source subclaim for the manuscript ESC-003 chain. -/
def ESC003AStatement : Prop :=
  ∀ (α : Type) (escapeAt : α → Nat → Prop),
    (∀ N x, Stage escapeAt N x → Stage escapeAt (N + 1) x) ∧
    (fun x => ∃ N, Stage escapeAt N x) = FiniteWitnessExterior escapeAt

/-- Kernel-checked staged reconstruction theorem. -/
theorem ESC003A_checked : ESC003AStatement := by
  intro α escapeAt
  exact ⟨stage_succ_mono escapeAt, finite_stages_reconstruct escapeAt⟩

#print axioms stage_mono
#print axioms exists_stage_iff_finite_witness
#print axioms finite_stages_reconstruct
#print axioms ESC003A_checked

end QIKVRT.V2.Escape
