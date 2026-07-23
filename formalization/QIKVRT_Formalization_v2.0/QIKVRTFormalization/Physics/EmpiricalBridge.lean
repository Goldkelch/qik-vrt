import Std

/-!
# Empirical bridge for mathematical and physical claims

This module formalizes the boundary between a kernel-checked mathematical
model and a statement about measured physical reality. Lean checks the
mathematics and the consequence of explicit bridge assumptions; empirical
premises remain external measured inputs.
-/

namespace QIKVRT.V2.Physics

structure EmpiricalContext where
  ModelState : Type
  Observation : Type
  PhysicalClaim : Type

structure EmpiricalBridge (C : EmpiricalContext) where
  modelHolds : C.ModelState → Prop
  evidenceSupports : C.Observation → Prop
  concludes : C.ModelState → C.Observation → C.PhysicalClaim → Prop
  bridgeRule : ∀ m o p, modelHolds m → evidenceSupports o → concludes m o p

def PhysicallySupported {C : EmpiricalContext} (B : EmpiricalBridge C)
    (m : C.ModelState) (o : C.Observation) (p : C.PhysicalClaim) : Prop :=
  B.modelHolds m ∧ B.evidenceSupports o ∧ B.concludes m o p

theorem physicallySupported_of_bridge {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (hm : B.modelHolds m)
    (ho : B.evidenceSupports o) : PhysicallySupported B m o p := by
  exact ⟨hm, ho, B.bridgeRule m o p hm ho⟩

theorem physicallySupported_has_model_evidence {C : EmpiricalContext}
    (B : EmpiricalBridge C) (m : C.ModelState) (o : C.Observation)
    (p : C.PhysicalClaim) (h : PhysicallySupported B m o p) :
    B.modelHolds m ∧ B.evidenceSupports o := by
  exact ⟨h.1, h.2.1⟩

structure ForwardModel where
  State : Type
  time : State → Nat
  Step : State → State → Prop
  advances : ∀ {a b}, Step a b → time a < time b

theorem no_backward_step (M : ForwardModel) {a b : M.State}
    (h : M.Step a b) : ¬ M.time b ≤ M.time a := by
  exact Nat.not_le_of_lt (M.advances h)

structure RetrospectiveClassifier (M : ForwardModel) where
  Label : Type
  classify : M.State → M.State → Label

def ReclassificationWithoutBackwardStep (M : ForwardModel)
    (R : RetrospectiveClassifier M) (past future : M.State) : Prop :=
  M.time past ≤ M.time future ∧
  ¬ M.Step future past ∧
  ∃ label, R.classify past future = label

theorem reclassification_without_backward_step (M : ForwardModel)
    (R : RetrospectiveClassifier M) {past future : M.State}
    (hOrder : M.time past ≤ M.time future)
    (hNoBack : ¬ M.Step future past) :
    ReclassificationWithoutBackwardStep M R past future := by
  exact ⟨hOrder, hNoBack, ⟨R.classify past future, rfl⟩⟩

#print axioms physicallySupported_of_bridge
#print axioms physicallySupported_has_model_evidence
#print axioms no_backward_step
#print axioms reclassification_without_backward_step

end QIKVRT.V2.Physics
