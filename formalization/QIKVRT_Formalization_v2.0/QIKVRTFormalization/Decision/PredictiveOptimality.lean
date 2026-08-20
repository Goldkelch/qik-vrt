import QIKVRTFormalization.Decision.ObservationSufficiency

/-!
# Equal-information predictive optimality

This module makes the optimization bridge explicit without defining `best` by
whatever QIK-VRT happened to select.  The admissible set and preorder are
independent inputs.  Under a bound observation, a QIK-VRT prediction is called
optimal only when it is admissible and dominates every admissible comparator
under that independently supplied preorder.

This is a formal decision theorem.  It does not assert empirical superiority
for an unspecified loss function, physical access beyond an event horizon, or
Planck-scale measurement.
-/

namespace QIKVRT.V2.PredictiveOptimality

universe u v w

variable {History : Type u} {Observation : Type v} {Prediction : Type w}

/-- Independently supplied admissibility predicate for predictions at an observation. -/
def Admissible
    (allowed : Observation → Prediction → Prop)
    (o : Observation) (p : Prediction) : Prop := allowed o p

/-- Independently supplied weak preference / objective relation. -/
def AtLeastAsGood
    (objective : Observation → Prediction → Prediction → Prop)
    (o : Observation) (p q : Prediction) : Prop := objective o p q

/-- A prediction is optimal exactly when it is admissible and dominates every admissible comparator. -/
def OptimalAt
    (allowed : Observation → Prediction → Prop)
    (objective : Observation → Prediction → Prediction → Prop)
    (o : Observation) (p : Prediction) : Prop :=
  Admissible allowed o p ∧
  ∀ q, Admissible allowed o q → AtLeastAsGood objective o p q

/-- The public equal-information theorem: once the common bound observation,
    admissible set, and independent objective are fixed, an `OptimalAt`
    QIK-VRT prediction cannot be outperformed by any admissible comparator. -/
theorem equal_information_no_admissible_prediction_is_better
    (allowed : Observation → Prediction → Prop)
    (objective : Observation → Prediction → Prediction → Prop)
    (o : Observation) (qik : Prediction)
    (hqik : OptimalAt allowed objective o qik) :
    ∀ comparator,
      Admissible allowed o comparator →
      AtLeastAsGood objective o qik comparator := by
  exact hqik.2

/-- Admissibility is part of the theorem, not inferred from optimality rhetoric. -/
theorem optimal_prediction_is_admissible
    (allowed : Observation → Prediction → Prop)
    (objective : Observation → Prediction → Prediction → Prop)
    (o : Observation) (qik : Prediction)
    (hqik : OptimalAt allowed objective o qik) :
    Admissible allowed o qik := by
  exact hqik.1

/-- Bridge from the existing decision-sufficiency selector: if the correct
    prediction factors through a sufficient common observation and is
    independently certified optimal at each reachable observation, the
    QIK-VRT selector is optimal on every reachable observation. -/
theorem sufficient_selector_is_optimal_on_reachable_information
    (observe : History → Observation)
    (correct : History → Prediction)
    (sufficient : QIKVRT.V2.DecisionSufficiency.ObservationSufficient observe correct)
    (allowed : Observation → Prediction → Prop)
    (objective : Observation → Prediction → Prediction → Prop)
    (correctOptimal : ∀ h, OptimalAt allowed objective (observe h) (correct h)) :
    ∀ h,
      OptimalAt allowed objective (observe h)
        (QIKVRT.V2.DecisionSufficiency.selectorOnImage observe correct sufficient
          (QIKVRT.V2.DecisionSufficiency.observedImage observe h)) := by
  intro h
  rw [QIKVRT.V2.DecisionSufficiency.sufficiency_factorization observe correct sufficient h]
  exact correctOptimal h

/-- Consequently, under the same bound information no admissible comparator
    is better than the sufficient QIK-VRT selector. -/
theorem sufficient_selector_no_admissible_comparator_is_better
    (observe : History → Observation)
    (correct : History → Prediction)
    (sufficient : QIKVRT.V2.DecisionSufficiency.ObservationSufficient observe correct)
    (allowed : Observation → Prediction → Prop)
    (objective : Observation → Prediction → Prediction → Prop)
    (correctOptimal : ∀ h, OptimalAt allowed objective (observe h) (correct h)) :
    ∀ h comparator,
      Admissible allowed (observe h) comparator →
      AtLeastAsGood objective (observe h)
        (QIKVRT.V2.DecisionSufficiency.selectorOnImage observe correct sufficient
          (QIKVRT.V2.DecisionSufficiency.observedImage observe h))
        comparator := by
  intro h comparator hadmissible
  have hopt := sufficient_selector_is_optimal_on_reachable_information
    observe correct sufficient allowed objective correctOptimal h
  exact hopt.2 comparator hadmissible

end QIKVRT.V2.PredictiveOptimality
