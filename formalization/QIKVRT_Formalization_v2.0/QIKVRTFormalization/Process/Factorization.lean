import QIKVRTFormalization.Process.Gates

/-!
# Factorization criterion for gate preservation (GAT-002)

This module formalizes manuscript lines 1233--1242.  For the fixed resolution
`N`, the function `sourceGate` represents the manuscript classifier
`A_N`.  A deterministic gate on the image of a trajectory map exists exactly
when that classifier is constant on every fiber of the map.

The reverse implication chooses one source trajectory above each image point.
That use of `Classical.choice` is explicit in the proof; fiber constancy proves
that the resulting target gate is independent of the chosen representative.
-/

namespace QIKVRT.V2

universe u v w

/-- The actual image of a process or trajectory map, not its full codomain. -/
abbrev ProcessImage {Source : Type u} {Target : Type v}
    (trajectoryMap : Source → Target) :=
  {target : Target // ∃ source : Source, trajectoryMap source = target}

/-- The canonical restriction of a map to its image. -/
def intoProcessImage {Source : Type u} {Target : Type v}
    (trajectoryMap : Source → Target) (source : Source) :
    ProcessImage trajectoryMap :=
  ⟨trajectoryMap source, ⟨source, rfl⟩⟩

/-- A classifier is constant on each fiber of the process map. -/
def ClassifierFiberConstant
    {Source : Type u} {Target : Type v} {Status : Type w}
    (trajectoryMap : Source → Target) (classifier : Source → Status) : Prop :=
  ∀ ⦃source₁ source₂ : Source⦄,
    trajectoryMap source₁ = trajectoryMap source₂ →
      classifier source₁ = classifier source₂

/-- The classifier is the pullback of a deterministic classifier on the image. -/
def FactorsThroughProcessImage
    {Source : Type u} {Target : Type v} {Status : Type w}
    (trajectoryMap : Source → Target) (classifier : Source → Status) : Prop :=
  ∃ imageClassifier : ProcessImage trajectoryMap → Status,
    classifier = imageClassifier ∘ intoProcessImage trajectoryMap

theorem factorization_implies_fiberConstant
    {Source : Type u} {Target : Type v} {Status : Type w}
    (trajectoryMap : Source → Target) (classifier : Source → Status) :
    FactorsThroughProcessImage trajectoryMap classifier →
      ClassifierFiberConstant trajectoryMap classifier := by
  rintro ⟨imageClassifier, hFactor⟩ source₁ source₂ hSameImage
  calc
    classifier source₁ =
        imageClassifier (intoProcessImage trajectoryMap source₁) :=
      congrFun hFactor source₁
    _ = imageClassifier (intoProcessImage trajectoryMap source₂) := by
      apply congrArg imageClassifier
      apply Subtype.ext
      exact hSameImage
    _ = classifier source₂ := (congrFun hFactor source₂).symm

theorem fiberConstant_implies_factorization
    {Source : Type u} {Target : Type v} {Status : Type w}
    (trajectoryMap : Source → Target) (classifier : Source → Status) :
    ClassifierFiberConstant trajectoryMap classifier →
      FactorsThroughProcessImage trajectoryMap classifier := by
  classical
  intro hFiber
  let representative : ProcessImage trajectoryMap → Source :=
    fun target => Classical.choose target.property
  let imageClassifier : ProcessImage trajectoryMap → Status :=
    fun target => classifier (representative target)
  refine ⟨imageClassifier, ?_⟩
  funext source
  apply hFiber
  exact (Classical.choose_spec
    (intoProcessImage trajectoryMap source).property).symm

/--
The exact GAT-002 proposition for a fixed manuscript gate `A_N`.

The target classifier is defined only on `trajectoryMap(Source)`, matching
the manuscript domain `Phi_infinity(Sigma_U)` exactly.
-/
def GAT002Statement
    {SourceTrajectory : Type u} {TargetTrajectory : Type v}
    (trajectoryMap : SourceTrajectory → TargetTrajectory)
    (sourceGate : SourceTrajectory → Gate) : Prop :=
  FactorsThroughProcessImage trajectoryMap sourceGate ↔
    ClassifierFiberConstant trajectoryMap sourceGate

theorem GAT002_checked
    {SourceTrajectory : Type u} {TargetTrajectory : Type v}
    (trajectoryMap : SourceTrajectory → TargetTrajectory)
    (sourceGate : SourceTrajectory → Gate) :
    GAT002Statement trajectoryMap sourceGate := by
  constructor
  · exact factorization_implies_fiberConstant trajectoryMap sourceGate
  · exact fiberConstant_implies_factorization trajectoryMap sourceGate

end QIKVRT.V2
