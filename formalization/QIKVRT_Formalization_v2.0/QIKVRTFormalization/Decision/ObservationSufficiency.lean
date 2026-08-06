import Std

/-!
# Observation sufficiency for deterministic recovery

General theorem: a partial observation is sufficient for a deterministic action
exactly when every reachable observation fiber is constant with respect to the
correct action. Equivalently, the observation kernel refines the action kernel.

This is intentionally domain-general. Authority/Mirror/Witness recovery is only
one specialization.
-/

namespace QIKVRT.V2.DecisionSufficiency

universe u v w

variable {History : Type u} {Observation : Type v} {Action : Type w}

/-- Recovery-relevant equivalence: histories are equivalent iff they require the same action. -/
def RecoveryEquivalent (correct : History → Action) (h₁ h₂ : History) : Prop :=
  correct h₁ = correct h₂

/-- Recovery relevance is an equivalence relation. -/
theorem recoveryEquivalent_equivalence (correct : History → Action) :
    Equivalence (RecoveryEquivalent correct) := by
  constructor
  · intro h
    rfl
  · intro a b hab
    exact hab.symm
  · intro a b c hab hbc
    exact hab.trans hbc

/-- Observation kernel: two histories are observationally indistinguishable. -/
def SameObservation (observe : History → Observation) (h₁ h₂ : History) : Prop :=
  observe h₁ = observe h₂

/-- Kernel-refinement / fiber-constancy condition. -/
def ObservationSufficient
    (observe : History → Observation) (correct : History → Action) : Prop :=
  ∀ h₁ h₂, observe h₁ = observe h₂ → correct h₁ = correct h₂

/-- Same condition, named as kernel inclusion. -/
def KernelIncluded
    (observe : History → Observation) (correct : History → Action) : Prop :=
  ∀ h₁ h₂, SameObservation observe h₁ h₂ → RecoveryEquivalent correct h₁ h₂

/-- The two formulations are definitionally equivalent. -/
theorem observationSufficient_iff_kernelIncluded
    (observe : History → Observation) (correct : History → Action) :
    ObservationSufficient observe correct ↔ KernelIncluded observe correct := by
  rfl

/-- Reachable observation image. -/
def ObservationImage (observe : History → Observation) :=
  {o : Observation // ∃ h : History, observe h = o}

/-- Lift a history to its reachable observation. -/
def observedImage (observe : History → Observation) (h : History) :
    ObservationImage observe :=
  ⟨observe h, ⟨h, rfl⟩⟩

/--
If the observation kernel refines the action kernel, a selector exists on the
reachable observation image.
-/
noncomputable def selectorOnImage
    (observe : History → Observation) (correct : History → Action)
    (_sufficient : ObservationSufficient observe correct) :
    ObservationImage observe → Action :=
  fun o => correct (Classical.choose o.property)

/-- Sufficiency theorem: the correct action factors through the reachable observation image. -/
theorem sufficiency_factorization
    (observe : History → Observation) (correct : History → Action)
    (sufficient : ObservationSufficient observe correct) :
    ∀ h, selectorOnImage observe correct sufficient (observedImage observe h) = correct h := by
  intro h
  unfold selectorOnImage
  apply sufficient
  exact Classical.choose_spec (observedImage observe h).property

/-- Any two selectors that factor the correct action agree on every reachable observation. -/
theorem selector_unique_on_reachable_image
    (observe : History → Observation) (correct : History → Action)
    (S₁ S₂ : ObservationImage observe → Action)
    (h₁ : ∀ h, S₁ (observedImage observe h) = correct h)
    (h₂ : ∀ h, S₂ (observedImage observe h) = correct h) :
    ∀ o : ObservationImage observe, S₁ o = S₂ o := by
  intro o
  rcases o.property with ⟨h, hh⟩
  have ho : observedImage observe h = o := by
    apply Subtype.ext
    exact hh
  calc
    S₁ o = correct h := by
      rw [← ho]
      exact h₁ h
    _ = S₂ o := by
      rw [← ho]
      exact (h₂ h).symm

/--
Impossibility theorem: if two admissible histories have the same observation but
require different correct actions, no universally correct deterministic selector
through that observation can exist.
-/
theorem impossibility_of_mixed_fiber
    (observe : History → Observation) (correct : History → Action)
    (h₁ h₂ : History)
    (sameObservation : observe h₁ = observe h₂)
    (differentAction : correct h₁ ≠ correct h₂) :
    ¬ ∃ S : Observation → Action, ∀ h, S (observe h) = correct h := by
  intro existsSelector
  rcases existsSelector with ⟨S, factorization⟩
  apply differentAction
  calc
    correct h₁ = S (observe h₁) := (factorization h₁).symm
    _ = S (observe h₂) := by rw [sameObservation]
    _ = correct h₂ := factorization h₂

/-- Any global deterministic factorization implies observation sufficiency. -/
theorem factorization_implies_sufficiency
    (observe : History → Observation) (correct : History → Action)
    (S : Observation → Action)
    (factorization : ∀ h, S (observe h) = correct h) :
    ObservationSufficient observe correct := by
  intro h₁ h₂ sameObservation
  calc
    correct h₁ = S (observe h₁) := (factorization h₁).symm
    _ = S (observe h₂) := by rw [sameObservation]
    _ = correct h₂ := factorization h₂

/--
Exact recoverability criterion on a nonempty fiber: if every history in the
fiber requires the same action, that action is the unique correct recovery
choice for the observation.
-/
def FiberConstantAt
    (observe : History → Observation) (correct : History → Action)
    (o : Observation) : Prop :=
  ∃ h₀, observe h₀ = o ∧ ∀ h, observe h = o → correct h = correct h₀

/-- A sufficient observation makes every reachable fiber action-constant. -/
theorem sufficient_implies_reachable_fiber_constant
    (observe : History → Observation) (correct : History → Action)
    (sufficient : ObservationSufficient observe correct)
    (o : Observation) (reachable : ∃ h, observe h = o) :
    FiberConstantAt observe correct o := by
  rcases reachable with ⟨h₀, hh₀⟩
  refine ⟨h₀, hh₀, ?_⟩
  intro h hh
  apply sufficient h h₀
  exact hh.trans hh₀.symm

/--
Witness/refinement theorem: any refined observation sufficient for the action
admits deterministic recovery on its reachable image.
-/
theorem refinedObservation_enables_recovery
    (observeRefined : History → Observation) (correct : History → Action)
    (kernelRefinement : KernelIncluded observeRefined correct) :
    ∃ S : ObservationImage observeRefined → Action,
      ∀ h, S (observedImage observeRefined h) = correct h := by
  have sufficient : ObservationSufficient observeRefined correct := kernelRefinement
  exact ⟨selectorOnImage observeRefined correct sufficient,
    sufficiency_factorization observeRefined correct sufficient⟩

end QIKVRT.V2.DecisionSufficiency
