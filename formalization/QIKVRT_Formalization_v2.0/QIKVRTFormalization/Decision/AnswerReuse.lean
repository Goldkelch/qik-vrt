-- SPDX-License-Identifier: Apache-2.0
-- Copyright (c) 2026 Ingolf Lohmann.

import QIKVRTFormalization.Process.Factorization
import QIKVRTFormalization.Decision.ObservationSufficiency

/-!
# Evidence-preserving answer reuse

This extension reuses the existing GAT-002 factorization theorem. Correctness
is relative to a supplied answer function, admissible domain and interpretation.
Existence on the reachable image does not supply a computable or fast selector.
Finite iteration preserves an invariant under an explicit preservation premise;
it does not establish termination, observation fidelity or universal truth.
-/

namespace QIKVRT.V2.AnswerReuse

universe u v w x

variable {Source : Type u} {Key : Type v} {Answer : Type w}

/-- AR-01: exact answer reuse is precisely the existing fiber criterion. -/
theorem answer_reuse_iff (key : Source → Key) (answer : Source → Answer) :
    FactorsThroughProcessImage key answer ↔ ClassifierFiberConstant key answer := by
  exact ⟨factorization_implies_fiberConstant key answer,
    fiberConstant_implies_factorization key answer⟩

/-- AR-02: one key serves a declared question family exactly when it preserves
each answer in that family. No claim is made that this family is all questions. -/
theorem question_family_iff {Question : Type x}
    (key : Source → Key) (answer : Source → Question → Answer) :
    ClassifierFiberConstant key answer ↔
      ∀ q, ClassifierFiberConstant key (fun s => answer s q) := by
  constructor
  · intro h q left right hk
    exact congrFun (h hk) q
  · intro h left right hk
    funext q
    exact h q hk

/-- AR-03: enriching a sufficient key preserves sufficiency. -/
theorem refinement_preserves_answers {Fine : Type x}
    (coarse : Source → Key) (fine : Source → Fine) (forget : Fine → Key)
    (answer : Source → Answer)
    (hBinding : ∀ s, forget (fine s) = coarse s)
    (hSufficient : ClassifierFiberConstant coarse answer) :
    ClassifierFiberConstant fine answer := by
  intro left right hFine
  apply hSufficient
  calc
    coarse left = forget (fine left) := (hBinding left).symm
    _ = forget (fine right) := congrArg forget hFine
    _ = coarse right := hBinding right

/-- AR-04: two verified computational substitutions compose. -/
theorem shortcuts_compose {Middle : Type x}
    (key : Source → Key) (middle : Key → Middle) (finish : Middle → Answer)
    (reference : Source → Answer) (first : Key → Answer)
    (hFirst : ∀ s, first (key s) = reference s)
    (hSecond : ∀ k, finish (middle k) = first k) :
    ∀ s, finish (middle (key s)) = reference s := by
  intro s
  exact (hSecond (key s)).trans (hFirst s)

/-- A key preserves every proposition-valued question over the source domain. -/
def PreservesEveryQuestion (key : Source → Key) : Prop :=
  ∀ question : Source → Prop, ClassifierFiberConstant key question

/-- AR-05: preserving every question requires keeping all distinguishable
states. This is a set-theoretic theorem, not a complexity lower bound. -/
theorem every_question_iff_injective (key : Source → Key) :
    PreservesEveryQuestion key ↔
      ∀ left right, key left = key right → left = right := by
  constructor
  · intro h left right hk
    have hp : (left = left) = (right = left) :=
      h (fun s => s = left) hk
    exact (Eq.mp hp rfl).symm
  · intro h question left right hk
    exact congrArg question (h left right hk)

/-- AR-06: lossy coarsening has a concrete failing question. -/
theorem collapsed_bool_cannot_preserve_identity :
    ¬ ClassifierFiberConstant (fun _ : Bool => ()) (fun b : Bool => b) := by
  intro h
  have hf : (false : Bool) = true := h (source₁ := false) (source₂ := true) rfl
  cases hf

/-- A proof carries explicit applicability conditions for a new context. -/
structure ConditionalCertificate (Context : Type u) where
  applicable : Context → Prop
  conclusion : Context → Prop
  checked : ∀ c, applicable c → conclusion c

/-- AR-07: reuse requires evidence of applicability in the new context. -/
theorem contextual_reuse (certificate : ConditionalCertificate Source)
    (current : Source) (hCurrent : certificate.applicable current) :
    certificate.conclusion current :=
  certificate.checked current hCurrent

/-- Scoped receipt identity. These symbolic fields model bindings, not hashes
as mathematical injections and not authentication of an actual event. -/
structure Binding where
  repository : String
  subject : String
  head : String
  tree : String
  policy : String
  deriving DecidableEq, Repr

structure Receipt where
  binding : Binding
  checked : Bool

def Admits (receipt : Receipt) (current : Binding) : Prop :=
  receipt.binding = current ∧ receipt.checked = true

/-- AR-08: a different head cannot inherit a scoped admission receipt. -/
theorem changed_head_rejects (receipt : Receipt) (current : Binding)
    (hChanged : receipt.binding.head ≠ current.head) :
    ¬ Admits receipt current := by
  intro h
  exact hChanged (congrArg Binding.head h.1)

/-- AR-09: an unverified receipt never admits, even with matching identity. -/
theorem unchecked_receipt_rejects (receipt : Receipt) (current : Binding)
    (hUnchecked : receipt.checked = false) : ¬ Admits receipt current := by
  intro h
  have hc := h.2
  rw [hUnchecked] at hc
  cases hc

/-- Iterate a supplied total transition for a finite number of steps. -/
def iterate (step : Source → Source) : Nat → Source → Source
  | 0, s => s
  | n + 1, s => iterate step n (step s)

/-- AR-10: every finite answer cycle preserves the chosen invariant,
provided each transition preserves it. This does not prove eventual completion. -/
theorem finite_cycle_preserves (step : Source → Source) (valid : Source → Prop)
    (hStep : ∀ s, valid s → valid (step s)) :
    ∀ n s, valid s → valid (iterate step n s) := by
  intro n
  induction n with
  | zero => intro s hs; exact hs
  | succ n ih => intro s hs; exact ih (step s) (hStep s hs)

/-- AR-11: safe iteration may remain forever outside a chosen goal. -/
theorem invariant_does_not_imply_completion :
    (∀ n, (fun _ : Bool => True) (iterate id n false)) ∧
    (∀ n, iterate id n false ≠ true) := by
  constructor
  · intro n; trivial
  · intro n
    have hi : ∀ n : Nat, iterate id n false = false := by
      intro k
      induction k with
      | zero => rfl
      | succ k ih => exact ih
    rw [hi n]
    decide

/-- AR-12: an explicit operation-count model gives a conditional saving.
The first derivation is paid once; each later reuse still pays checking cost. -/
theorem reuse_cost_strictly_less (reuses derive check : Nat)
    (hPositive : 0 < reuses) (hCheaper : check < derive) :
    derive + reuses * check < (reuses + 1) * derive := by
  have hm : reuses * check < reuses * derive :=
    Nat.mul_lt_mul_of_pos_left hCheaper hPositive
  rw [Nat.add_mul, Nat.one_mul]
  omega

/-- AR-13: completion within a finite rank bound requires a strictly decreasing
natural-number rank at every non-goal state. The hypothesis is a substantive
progress obligation; queues, absent authority and waiting do not establish it. -/
theorem completion_of_decreasing_rank (step : Source → Source)
    (goal : Source → Prop) (rank : Source → Nat)
    (hDecrease : ∀ s, ¬ goal s → rank (step s) < rank s) :
    ∀ s, ∃ n, n ≤ rank s ∧ goal (iterate step n s) := by
  classical
  have aux : ∀ r s, rank s = r → ∃ n, n ≤ rank s ∧ goal (iterate step n s) := by
    intro r
    induction r using Nat.strongRecOn with
    | ind r ih =>
      intro s hr
      by_cases hGoal : goal s
      · exact ⟨0, Nat.zero_le _, hGoal⟩
      · have hLt : rank (step s) < r := by
          rw [← hr]
          exact hDecrease s hGoal
        obtain ⟨n, hn, hResult⟩ := ih (rank (step s)) hLt (step s) rfl
        refine ⟨n + 1, ?_, hResult⟩
        have := hDecrease s hGoal
        omega
  intro s
  exact aux (rank s) s rfl

end QIKVRT.V2.AnswerReuse
