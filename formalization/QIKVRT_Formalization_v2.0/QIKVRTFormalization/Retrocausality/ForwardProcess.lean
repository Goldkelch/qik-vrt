import Std

/-!
# Deterministic forward processes and immutable prefixes

The result is a genuine relational invariance theorem: two different input
histories that agree before a cut generate equal state prefixes and therefore
equal captured prefix records through that cut.
-/

namespace QIKVRT.V2

universe u v

def run (step : State → Input → State) (initial : State)
    (inputs : Nat → Input) : Nat → State
  | 0 => initial
  | n + 1 => step (run step initial inputs n) (inputs n)

def InputPrefixAgrees (u v : Nat → Input) (cut : Nat) : Prop :=
  ∀ k, k < cut → u k = v k

def StatePrefixAgrees (a b : Nat → State) (cut : Nat) : Prop :=
  ∀ k, k ≤ cut → a k = b k

theorem run_at_depends_only_on_input_prefix
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (n : Nat)
    (hPrefix : InputPrefixAgrees u v n) :
    run step initial u n = run step initial v n := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [run]
      rw [ih (fun k hk => hPrefix k (Nat.lt_trans hk (Nat.lt_succ_self n)))]
      rw [hPrefix n (Nat.lt_succ_self n)]

theorem forwardProcess_prefix_invariant
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (hPrefix : InputPrefixAgrees u v cut) :
    StatePrefixAgrees (run step initial u) (run step initial v) cut := by
  intro k hk
  apply run_at_depends_only_on_input_prefix step initial u v k
  intro j hj
  exact hPrefix j (Nat.lt_of_lt_of_le hj hk)

structure PrefixRecord (State : Type u) (cut : Nat) where
  stateAt : Fin (cut + 1) → State

namespace PrefixRecord

@[ext] theorem ext {left right : PrefixRecord State cut}
    (h : ∀ k, left.stateAt k = right.stateAt k) : left = right := by
  cases left with
  | mk leftState =>
      cases right with
      | mk rightState =>
          congr
          funext k
          exact h k

end PrefixRecord

def capturePrefix (trajectory : Nat → State) (cut : Nat) : PrefixRecord State cut where
  stateAt k := trajectory k.val

theorem capturedPrefix_invariant
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (hPrefix : InputPrefixAgrees u v cut) :
    capturePrefix (run step initial u) cut =
      capturePrefix (run step initial v) cut := by
  apply PrefixRecord.ext
  intro k
  apply forwardProcess_prefix_invariant step initial u v cut hPrefix
  exact Nat.le_of_lt_succ k.isLt

end QIKVRT.V2

