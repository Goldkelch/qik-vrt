import Std

/-!
# GAT-003: shift invariance of the exact boundedness classifier

This module formalizes the manuscript argument that deleting finitely many
terms of a trajectory changes neither boundedness nor unboundedness.  The
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

/-- Maximum of the first `k` observations, with zero as the empty-prefix bound. -/
def prefixMax (trajectory : Trajectory) : Nat → Nat
  | 0 => 0
  | k + 1 => max (prefixMax trajectory k) (trajectory k)

theorem prefix_le_prefixMax (trajectory : Trajectory) :
    ∀ {k n}, n < k → trajectory n ≤ prefixMax trajectory k := by
  intro k
  induction k with
  | zero =>
      intro n h
      omega
  | succ k ih =>
      intro n h
      by_cases hnk : n = k
      · subst n
        exact Nat.le_max_right _ _
      · have hlt : n < k := by omega
        exact le_trans (ih hlt) (Nat.le_max_left _ _)

theorem shift_bounded_of_bounded {trajectory : Trajectory} {k : Nat}
    (hBounded : Bounded trajectory) : Bounded (shift k trajectory) := by
  rcases hBounded with ⟨bound, hBound⟩
  exact ⟨bound, fun n => hBound (k + n)⟩

theorem bounded_of_shift_bounded {trajectory : Trajectory} {k : Nat}
    (hTail : Bounded (shift k trajectory)) : Bounded trajectory := by
  rcases hTail with ⟨tailBound, hTailBound⟩
  refine ⟨max (prefixMax trajectory k) tailBound, ?_⟩
  intro n
  by_cases hPrefix : n < k
  · exact le_trans (prefix_le_prefixMax trajectory hPrefix)
      (Nat.le_max_left _ _)
  · have hkn : k ≤ n := by omega
    obtain ⟨m, hm⟩ := Nat.exists_eq_add_of_le hkn
    subst n
    exact le_trans (hTailBound m) (Nat.le_max_right _ _)

theorem bounded_shift_iff (trajectory : Trajectory) (k : Nat) :
    Bounded (shift k trajectory) ↔ Bounded trajectory := by
  exact ⟨bounded_of_shift_bounded, shift_bounded_of_bounded⟩

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
