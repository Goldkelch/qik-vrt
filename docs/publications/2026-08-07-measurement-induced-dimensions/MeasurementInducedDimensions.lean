import Std

/-!
# MID-001: Measurement-induced dimensional representation

This module formalizes a deliberately premetric finite model contract.

The ontic layer contains only distinguishability and a causal relation. Physical
dimension labels are introduced only by a measurement channel. The theorems below
show that the same premetric ontology and the same operational observation/calibration
maps can carry distinct dimension labels. They also show that the same causal boundary
can be represented with different numerical tokens for an invariant propagation speed
(e.g. `299792458` in the SI metre/second convention or `1` in a normalized convention).

This establishes a representation-layer non-uniqueness theorem. It does **not** prove
that nature is fundamentally dimensionless, derive the SI, derive the physical value
of `c`, `hbar` or `G`, or establish the physical QCE correspondence. Those require
additional correspondence, normalization and dynamics theorems.
-/

namespace QIKVRT
namespace V2
namespace Physics
namespace MeasurementInducedDimensions

universe u v

/-- A premetric ontology: no scalar, unit or physical-dimension field occurs here. -/
structure PremetricOntology (State : Type u) where
  distinguishable : State → State → Prop
  causal : State → State → Prop

/-- Seven-component signature used only at the measurement-representation layer. -/
structure DimensionSignature where
  lengthExp : Int
  timeExp : Int
  massExp : Int
  temperatureExp : Int
  currentExp : Int
  amountExp : Int
  luminousIntensityExp : Int
deriving DecidableEq, Repr, BEq

/-- Dimensionless representation label. -/
def dimensionless : DimensionSignature := ⟨0, 0, 0, 0, 0, 0, 0⟩

/-- Conventional length representation label. -/
def lengthDimension : DimensionSignature := ⟨1, 0, 0, 0, 0, 0, 0⟩

/-- Conventional time representation label. -/
def timeDimension : DimensionSignature := ⟨0, 1, 0, 0, 0, 0, 0⟩

/-- [MID-T01] Length and time are distinct measurement-layer labels. -/
theorem MID_T01_length_and_time_labels_are_distinct :
    lengthDimension ≠ timeDimension := by
  decide

/-- A measurement channel adds operational maps and a dimension signature. -/
structure MeasurementChannel (State : Type u) (Reading : Type v) where
  observe : State → Reading
  calibrate : Reading → Reading
  dimension : DimensionSignature

/-- Equality of the operational maps while deliberately ignoring the dimension label. -/
def sameOperationalMap
    (left right : MeasurementChannel State Reading) : Prop :=
  left.observe = right.observe ∧ left.calibrate = right.calibrate

/-- Change only the dimension label of a measurement channel. -/
def relabelDimension
    (channel : MeasurementChannel State Reading)
    (dimension : DimensionSignature) : MeasurementChannel State Reading :=
  { channel with dimension := dimension }

/-- [MID-T02] Dimension relabeling leaves observation and calibration unchanged. -/
theorem MID_T02_relabel_preserves_operational_map
    (channel : MeasurementChannel State Reading)
    (leftDimension rightDimension : DimensionSignature) :
    sameOperationalMap
      (relabelDimension channel leftDimension)
      (relabelDimension channel rightDimension) := by
  exact ⟨rfl, rfl⟩

/--
[MID-T03] The same operational observation/calibration maps admit distinct length and
time labels. Therefore the label is not determined by those maps alone.
-/
theorem MID_T03_same_operational_map_allows_distinct_dimensions
    (channel : MeasurementChannel State Reading) :
    sameOperationalMap
        (relabelDimension channel lengthDimension)
        (relabelDimension channel timeDimension) ∧
      (relabelDimension channel lengthDimension).dimension ≠
        (relabelDimension channel timeDimension).dimension := by
  constructor
  · exact MID_T02_relabel_preserves_operational_map
      channel lengthDimension timeDimension
  · exact MID_T01_length_and_time_labels_are_distinct

/-- A measurement system couples a premetric ontology to a measurement channel. -/
structure MeasurementSystem (State : Type u) (Reading : Type v) where
  ontology : PremetricOntology State
  channel : MeasurementChannel State Reading

/-- Forget the measurement layer and retain only the premetric ontology. -/
def forgetMeasurement
    (system : MeasurementSystem State Reading) : PremetricOntology State :=
  system.ontology

/-- Relabel only the measurement channel of a system. -/
def relabelSystem
    (system : MeasurementSystem State Reading)
    (dimension : DimensionSignature) : MeasurementSystem State Reading :=
  { system with channel := relabelDimension system.channel dimension }

/-- [MID-T04] Dimension relabeling cannot change the premetric ontology. -/
theorem MID_T04_dimension_relabel_preserves_premetric_ontology
    (system : MeasurementSystem State Reading)
    (dimension : DimensionSignature) :
    forgetMeasurement (relabelSystem system dimension) = forgetMeasurement system := by
  rfl

/--
[MID-T05] Explicit countermodel to dimension-from-premetric-ontology uniqueness:
for any premetric ontology and fixed operational maps, there are two measurement
systems with the same premetric projection and operational map but distinct dimensions.
-/
theorem MID_T05_dimension_not_determined_by_premetric_ontology
    (ontology : PremetricOntology State)
    (observe : State → Reading)
    (calibrate : Reading → Reading) :
    ∃ left right : MeasurementSystem State Reading,
      forgetMeasurement left = forgetMeasurement right ∧
      sameOperationalMap left.channel right.channel ∧
      left.channel.dimension ≠ right.channel.dimension := by
  let base : MeasurementChannel State Reading :=
    ⟨observe, calibrate, dimensionless⟩
  let left : MeasurementSystem State Reading :=
    ⟨ontology, relabelDimension base lengthDimension⟩
  let right : MeasurementSystem State Reading :=
    ⟨ontology, relabelDimension base timeDimension⟩
  refine ⟨left, right, ?_, ?_, ?_⟩
  · rfl
  · exact MID_T02_relabel_preserves_operational_map
      base lengthDimension timeDimension
  · exact MID_T01_length_and_time_labels_are_distinct

/-- A metric representation of one premetric causal boundary. -/
structure MetricCausalRepresentation (State : Type u) (Reading : Type v) where
  boundary : State → State → Prop
  spaceReading : State → Reading
  timeReading : State → Reading
  speedNumeral : Reading

/-- Equality of the causal boundary while ignoring metric numerical encoding. -/
def sameCausalBoundary
    (left right : MetricCausalRepresentation State Reading) : Prop :=
  left.boundary = right.boundary

/-- Change only the displayed numerical token for propagation speed. -/
def reencodeSpeedNumeral
    (representation : MetricCausalRepresentation State Reading)
    (speedNumeral : Reading) : MetricCausalRepresentation State Reading :=
  { representation with speedNumeral := speedNumeral }

/-- [MID-T06] Re-encoding the speed numeral leaves the causal boundary unchanged. -/
theorem MID_T06_speed_numeral_reencoding_preserves_causal_boundary
    (representation : MetricCausalRepresentation State Reading)
    (leftNumeral rightNumeral : Reading) :
    sameCausalBoundary
      (reencodeSpeedNumeral representation leftNumeral)
      (reencodeSpeedNumeral representation rightNumeral) := by
  rfl

/--
[MID-T07] The same causal boundary can carry the SI numeral `299792458` or normalized
numeral `1`. This is a representation theorem only; it does not derive physical `c`.
-/
theorem MID_T07_same_boundary_allows_c_299792458_or_1
    (representation : MetricCausalRepresentation State Nat) :
    sameCausalBoundary
        (reencodeSpeedNumeral representation 299792458)
        (reencodeSpeedNumeral representation 1) ∧
      (reencodeSpeedNumeral representation 299792458).speedNumeral ≠
        (reencodeSpeedNumeral representation 1).speedNumeral := by
  constructor
  · exact MID_T06_speed_numeral_reencoding_preserves_causal_boundary
      representation 299792458 1
  · simp [reencodeSpeedNumeral]

end MeasurementInducedDimensions
end Physics
end V2
end QIKVRT
