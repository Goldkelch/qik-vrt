import Std

/-!
# GAT-003: shift invariance of the exact boundedness classifier

This module formalizes the manuscript argument that deleting finitely many
terms of a trajectory changes neither boundedness nor unboundedness. The
observable is represented as a natural-valued sequence; this is sufficient for
the exact PASS/BLOCK classifier because only the existence of a finite upper
bound is used.
-/

namespace QIKVRT.V2

namespace ShiftClassification

abbrev Trajectory := Nat → Nat

/-- The left shift by `k` positions. -/
def shift (k : Nat) (trajectory : Trajectory) : Trajectory :=
  fun n => trajectory (k + n)

/-- A trajectory is bounded when one natural number bounds every observation. -/
def Bounded (trajectory : Trajectory) : Prop :=
  ∃ bound, ∀ n, trajectory n ≤ bound

theorem shift_bounded_of_bounded {trajectory : Trajectory} {k : Nat}
    (hBounded : Bounded trajectory) : Bounded (shift k trajectory) := by
  rcases hBounded with ⟨bound, hBound⟩
  exact ⟨bound, fun n => hBound (k + n)⟩

theorem bounded_shift_succ_of_bounded_shift {trajectory : Trajectory} {k : Nat}
    (hTail : Bounded (shift (k + 1) trajectory)) : Bounded (shift k trajectory) := by
  rcases hTail with ⟨bound, hBound⟩
  refine ⟨trajectory k + bound, ?_⟩
  intro n
  cases n with
  | zero =>
      change trajectory k ≤ trajectory k + bound
      omega
  | succ n =>
      change trajectory (k + Nat.succ n) ≤ trajectory k + bound
      have hIndex : k + Nat.succ n = (k + 1) + n := by omega
      rw [hIndex]
      have hValue : trajectory ((k + 1) + n) ≤ bound := hBound n
      omega

theorem bounded_of_shift_bounded {trajectory : Trajectory} :
    ∀ k, Bounded (shift k trajectory) → Bounded trajectory := by
  intro k
  induction k with
  | zero =>
      intro h
      simpa [shift] using h
  | succ k ih =>
      intro h
      exact ih (bounded_shift_succ_of_bounded_shift h)

theorem bounded_shift_iff (trajectory : Trajectory) (k : Nat) :
    Bounded (shift k trajectory) ↔ Bounded trajectory := by
  constructor
  · exact bounded_of_shift_bounded k
  · exact shift_bounded_of_bounded

inductive ExactStatus where
  | pass
  | block
  deriving DecidableEq, Repr

/-- Exact classifier used by the manuscript: PASS exactly for bounded tails. -/
noncomputable def classify (trajectory : Trajectory) : ExactStatus :=
  if Bounded trajectory then .pass else .block

theorem classify_shift_invariant (trajectory : Trajectory) (k : Nat) :
    classify (shift k trajectory) = classify trajectory := by
  classical
  unfold classify
  rw [bounded_shift_iff trajectory k]

/-- Exact proposition bound to manuscript claim `GAT-003`. -/
def GAT003Statement : Prop :=
  ∀ trajectory k, classify (shift k trajectory) = classify trajectory

/-- Kernel-checked discharge of the full shift-invariance environment. -/
theorem GAT003_checked : GAT003Statement := by
  intro trajectory k
  exact classify_shift_invariant trajectory k

end ShiftClassification

end QIKVRT.V2
