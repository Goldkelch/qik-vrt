import QIKVRTFormalization.Process.Factorization

/-!
# Information-theoretic reconstruction boundary

EFFECT_ACK can gate a reconstruction process; it does not manufacture missing
information.  These theorems reuse the existing image-factorization proof and
make the exact historical inversion boundary explicit.
-/

namespace QIKVRT.EffectAck.V1

universe u v w

def SemanticReconstructionExists
    {Source : Type u} {Observation : Type v} {Meaning : Type w}
    (observe : Source → Observation) (meaning : Source → Meaning) : Prop :=
  QIKVRT.V2.FactorsThroughProcessImage observe meaning

def MeaningConstantOnObservationFibers
    {Source : Type u} {Observation : Type v} {Meaning : Type w}
    (observe : Source → Observation) (meaning : Source → Meaning) : Prop :=
  QIKVRT.V2.ClassifierFiberConstant observe meaning

theorem semanticReconstruction_iff_fiberConstant
    {Source : Type u} {Observation : Type v} {Meaning : Type w}
    (observe : Source → Observation) (meaning : Source → Meaning) :
    SemanticReconstructionExists observe meaning ↔
      MeaningConstantOnObservationFibers observe meaning := by
  constructor
  · exact QIKVRT.V2.factorization_implies_fiberConstant observe meaning
  · exact QIKVRT.V2.fiberConstant_implies_factorization observe meaning

def Injective {Source : Type u} {Observation : Type v}
    (observe : Source → Observation) : Prop :=
  ∀ ⦃left right⦄, observe left = observe right → left = right

def LeftInverse {Source : Type u} {Observation : Type v}
    (decode : Observation → Source) (observe : Source → Observation) : Prop :=
  ∀ source, decode (observe source) = source

def ExactHistoricalReconstruction
    {Source : Type u} {Observation : Type v}
    (observe : Source → Observation) : Prop :=
  ∃ decode : Observation → Source, LeftInverse decode observe

theorem leftInverse_implies_injective
    {Source : Type u} {Observation : Type v}
    (observe : Source → Observation) (decode : Observation → Source)
    (hLeftInverse : LeftInverse decode observe) :
    Injective observe := by
  intro left right hSameObservation
  calc
    left = decode (observe left) := (hLeftInverse left).symm
    _ = decode (observe right) := congrArg decode hSameObservation
    _ = right := hLeftInverse right

theorem exactHistoricalReconstruction_implies_injective
    {Source : Type u} {Observation : Type v}
    (observe : Source → Observation) :
    ExactHistoricalReconstruction observe → Injective observe := by
  rintro ⟨decode, hLeftInverse⟩
  exact leftInverse_implies_injective observe decode hLeftInverse

theorem noninjectiveObservation_blocksExactReconstruction
    {Source : Type u} {Observation : Type v}
    (observe : Source → Observation)
    (hNotInjective : ¬ Injective observe) :
    ¬ ExactHistoricalReconstruction observe := by
  intro hExact
  exact hNotInjective
    (exactHistoricalReconstruction_implies_injective observe hExact)

def collapsedObservation (_ : Bool) : Unit := ()

theorem collapsedObservation_not_injective :
    ¬ Injective collapsedObservation := by
  intro hInjective
  have hFalseTrue : (false : Bool) = true := hInjective rfl
  cases hFalseTrue

theorem noExactDecoder_forCollapsedObservation :
    ¬ ExactHistoricalReconstruction collapsedObservation :=
  noninjectiveObservation_blocksExactReconstruction
    collapsedObservation collapsedObservation_not_injective

end QIKVRT.EffectAck.V1
