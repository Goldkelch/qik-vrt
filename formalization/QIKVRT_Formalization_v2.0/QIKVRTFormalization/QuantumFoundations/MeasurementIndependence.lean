import Std

/-!
# Measurement independence and the superdeterminism boundary

This module formalizes the exact logical boundary needed for a QIK-VRT claim
about superdeterminism without smuggling a physical conclusion into the kernel.

The core result is deliberately conditional:

* measurement independence excludes measurement-dependent (superdeterministic)
  candidates by definition;
* local two-wing response structure and delayed comparison do not, by themselves,
  establish measurement independence;
* a concrete finite common-cause countermodel witnesses that insufficiency;
* a QCE freedom certificate must therefore supply measurement independence as a
  separately justified obligation before the exclusion can be promoted.

This module does not prove that nature satisfies measurement independence.
Physical qualification remains an evidence/reference-binding question.
-/

namespace QIKVRT.V2.QuantumFoundations

universe u v w x y

/--
A support-level two-wing Bell scenario.  The response functions are structurally
local at the measurement stage: A receives no B-setting and B receives no A-setting.
The support relation `jointlyPossible` carries the preparation/setting coupling.
-/
structure TwoWingSupportModel where
  Hidden : Type u
  SettingA : Type v
  SettingB : Type w
  OutcomeA : Type x
  OutcomeB : Type y
  hiddenPossible : Hidden → Prop
  settingsPossible : SettingA → SettingB → Prop
  jointlyPossible : Hidden → SettingA → SettingB → Prop
  responseA : Hidden → SettingA → OutcomeA
  responseB : Hidden → SettingB → OutcomeB

/-- Support-factorization form of measurement independence. -/
def MeasurementIndependent (model : TwoWingSupportModel) : Prop :=
  ∀ hidden settingA settingB,
    model.jointlyPossible hidden settingA settingB ↔
      model.hiddenPossible hidden ∧ model.settingsPossible settingA settingB

/-- Failure of the support-factorization independence condition. -/
def MeasurementDependent (model : TwoWingSupportModel) : Prop :=
  ¬ MeasurementIndependent model

/--
Kernel proxy for the superdeterministic escape route relevant to Bell reasoning:
measurement settings are not independent of the hidden preparation support.
This intentionally does not claim to encode every philosophical use of the word
"superdeterminism".
-/
def SuperdeterministicCandidate (model : TwoWingSupportModel) : Prop :=
  MeasurementDependent model

/-- Measurement independence excludes the formal superdeterministic candidate. -/
theorem measurementIndependence_excludes_superdeterministicCandidate
    {model : TwoWingSupportModel}
    (independent : MeasurementIndependent model) :
    ¬ SuperdeterministicCandidate model := by
  intro dependent
  exact dependent independent

/-- A superdeterministic candidate entails failure of measurement independence. -/
theorem superdeterministicCandidate_implies_measurementDependence
    {model : TwoWingSupportModel}
    (candidate : SuperdeterministicCandidate model) :
    MeasurementDependent model :=
  candidate

/-- Lift A's local response to a notation that also carries an unused remote setting. -/
def observedA (model : TwoWingSupportModel)
    (hidden : model.Hidden) (settingA : model.SettingA)
    (_settingB : model.SettingB) : model.OutcomeA :=
  model.responseA hidden settingA

/-- Lift B's local response to a notation that also carries an unused remote setting. -/
def observedB (model : TwoWingSupportModel)
    (hidden : model.Hidden) (_settingA : model.SettingA)
    (settingB : model.SettingB) : model.OutcomeB :=
  model.responseB hidden settingB

/-- Structural parameter locality on wing A: the remote setting is not an input. -/
theorem responseA_remoteSettingInsensitive
    (model : TwoWingSupportModel)
    (hidden : model.Hidden) (settingA : model.SettingA)
    (settingB₁ settingB₂ : model.SettingB) :
    observedA model hidden settingA settingB₁ =
      observedA model hidden settingA settingB₂ := by
  rfl

/-- Structural parameter locality on wing B: the remote setting is not an input. -/
theorem responseB_remoteSettingInsensitive
    (model : TwoWingSupportModel)
    (hidden : model.Hidden) (settingA₁ settingA₂ : model.SettingA)
    (settingB : model.SettingB) :
    observedB model hidden settingA₁ settingB =
      observedB model hidden settingA₂ settingB := by
  rfl

inductive Bit where
  | zero
  | one
  deriving DecidableEq, Repr

/--
Finite common-cause model: both settings are constrained to equal the same hidden
bit.  The local response functions still have no access to the remote setting.
-/
def commonCauseModel : TwoWingSupportModel where
  Hidden := Bit
  SettingA := Bit
  SettingB := Bit
  OutcomeA := Bit
  OutcomeB := Bit
  hiddenPossible := fun _ => True
  settingsPossible := fun _ _ => True
  jointlyPossible := fun hidden settingA settingB =>
    settingA = hidden ∧ settingB = hidden
  responseA := fun hidden settingA => if settingA = hidden then .one else .zero
  responseB := fun hidden settingB => if settingB = hidden then .one else .zero

/-- The common-cause model violates measurement independence. -/
theorem commonCauseModel_not_measurementIndependent :
    ¬ MeasurementIndependent commonCauseModel := by
  intro independent
  have factorization := independent Bit.zero Bit.one Bit.one
  have admissible :
      commonCauseModel.hiddenPossible Bit.zero ∧
        commonCauseModel.settingsPossible Bit.one Bit.one := by
    exact ⟨True.intro, True.intro⟩
  have jointly := factorization.mpr admissible
  exact Bit.noConfusion jointly.1

/-- The finite common-cause model is therefore a superdeterministic candidate. -/
theorem commonCauseModel_superdeterministicCandidate :
    SuperdeterministicCandidate commonCauseModel :=
  commonCauseModel_not_measurementIndependent

/--
Counterexample to the invalid inference "two local/spacelike response wings imply
measurement independence".  The model has structurally remote-insensitive local
responses while measurement independence fails.
-/
theorem localResponseStructure_not_sufficient_for_measurementIndependence :
    (∀ hidden settingA settingB₁ settingB₂,
        observedA commonCauseModel hidden settingA settingB₁ =
          observedA commonCauseModel hidden settingA settingB₂) ∧
    (∀ hidden settingA₁ settingA₂ settingB,
        observedB commonCauseModel hidden settingA₁ settingB =
          observedB commonCauseModel hidden settingA₂ settingB) ∧
    ¬ MeasurementIndependent commonCauseModel := by
  refine ⟨?_, ?_, commonCauseModel_not_measurementIndependent⟩
  · intro hidden settingA settingB₁ settingB₂
    exact responseA_remoteSettingInsensitive commonCauseModel hidden settingA settingB₁ settingB₂
  · intro hidden settingA₁ settingA₂ settingB
    exact responseB_remoteSettingInsensitive commonCauseModel hidden settingA₁ settingA₂ settingB

/--
A QCE-level certificate records the additional obligation that must be derived
from independently justified QCE axioms or established by physical evidence.
-/
structure QCEFreedomCertificate (model : TwoWingSupportModel) : Prop where
  measurementIndependent : MeasurementIndependent model

/-- A valid QCE freedom certificate excludes the formal superdeterministic candidate. -/
theorem qceFreedomCertificate_excludes_superdeterministicCandidate
    {model : TwoWingSupportModel}
    (certificate : QCEFreedomCertificate model) :
    ¬ SuperdeterministicCandidate model :=
  measurementIndependence_excludes_superdeterministicCandidate
    certificate.measurementIndependent

/--
The kernel boundary in one conjunction: the conditional exclusion is proved,
while locality alone is formally insufficient because of the finite countermodel.
-/
theorem superdeterminism_boundary_summary :
    (∀ model : TwoWingSupportModel,
      MeasurementIndependent model → ¬ SuperdeterministicCandidate model) ∧
    ¬ MeasurementIndependent commonCauseModel := by
  constructor
  · intro model independent
    exact measurementIndependence_excludes_superdeterministicCandidate independent
  · exact commonCauseModel_not_measurementIndependent

end QIKVRT.V2.QuantumFoundations
