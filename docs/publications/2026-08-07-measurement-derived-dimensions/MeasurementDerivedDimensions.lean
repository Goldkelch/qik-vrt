import Std

/-!
# MDD-002: Measurement-derived physical dimensions

This module strengthens the measurement-induced-dimension separation result.

The premetric ontology still contains only distinguishability and causal relation.
A measurement channel no longer carries an independently selectable dimension label.
Instead it carries an admissible calibration action. The action records how the
measurement representation responds to integer compositions of seven independent
calibration generators. Admissibility requires zero preservation and additive
composition for each generator.

The dimension signature is then *derived* from the action by reading its response to
one unit step of each generator. The central theorem proves uniqueness: any signature
that agrees with those seven observable basis responses is equal to the derived
signature. Hence, inside this formal model, dimension is not a primitive ontic field
or a free measurement label; it is a uniquely recoverable invariant of the declared
calibration action.

Scientific boundary: this is a model-theoretic theorem. It does not prove that nature
uses this calibration action, that QCE uniquely supplies the seven generators, that SI
is fundamental, or that c, hbar, G, the Einstein limit, or empirical correspondence
have been derived. Those require additional physical correspondence and dynamics.
-/

namespace QIKVRT
namespace V2
namespace Physics
namespace MeasurementDerivedDimensions

universe u v

/-- Premetric ontic layer: no unit, scalar, calibration or dimension field. -/
structure PremetricOntology (State : Type u) where
  distinguishable : State → State → Prop
  causal : State → State → Prop

/-- Independent generators of the measurement-calibration representation. -/
inductive CalibrationGenerator where
  | lengthScale
  | timeScale
  | massScale
  | temperatureScale
  | currentScale
  | amountScale
  | luminousIntensityScale
deriving DecidableEq, Repr

/-- Conventional seven-component representation of a physical dimension. -/
structure DimensionSignature where
  lengthExp : Int
  timeExp : Int
  massExp : Int
  temperatureExp : Int
  currentExp : Int
  amountExp : Int
  luminousIntensityExp : Int
deriving DecidableEq, Repr

/--
An admissible calibration action. Integer composition models repeated/inverse changes
of a measurement convention along one generator. The response must preserve identity
and composition, i.e. it is additive in the rescaling count for each generator.
-/
structure CalibrationAction where
  response : CalibrationGenerator → Int → Int
  zeroResponse : ∀ generator, response generator 0 = 0
  composeResponse : ∀ generator left right,
    response generator (left + right) =
      response generator left + response generator right

/-- Derive the dimension signature from unit responses of the calibration action. -/
def derivedDimension (action : CalibrationAction) : DimensionSignature :=
  {
    lengthExp := action.response .lengthScale 1
    timeExp := action.response .timeScale 1
    massExp := action.response .massScale 1
    temperatureExp := action.response .temperatureScale 1
    currentExp := action.response .currentScale 1
    amountExp := action.response .amountScale 1
    luminousIntensityExp := action.response .luminousIntensityScale 1
  }

/-- Explicit agreement of a proposed signature with all seven calibration generators. -/
structure BasisAgreement
    (action : CalibrationAction)
    (dimension : DimensionSignature) : Prop where
  length : dimension.lengthExp = action.response .lengthScale 1
  time : dimension.timeExp = action.response .timeScale 1
  mass : dimension.massExp = action.response .massScale 1
  temperature : dimension.temperatureExp = action.response .temperatureScale 1
  current : dimension.currentExp = action.response .currentScale 1
  amount : dimension.amountExp = action.response .amountScale 1
  luminousIntensity :
    dimension.luminousIntensityExp = action.response .luminousIntensityScale 1

/-- [MDD-T01] The derived signature agrees with every basis calibration response. -/
theorem MDD_T01_derived_dimension_agrees_with_basis
    (action : CalibrationAction) :
    BasisAgreement action (derivedDimension action) := by
  exact ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

/--
[MDD-T02] Central uniqueness theorem: no second dimension signature can agree with the
same seven calibration basis responses.
-/
theorem MDD_T02_basis_agreement_is_unique
    (action : CalibrationAction)
    (dimension : DimensionSignature)
    (agreement : BasisAgreement action dimension) :
    dimension = derivedDimension action := by
  cases dimension with
  | mk lengthExp timeExp massExp temperatureExp currentExp amountExp luminousIntensityExp =>
      cases agreement with
      | mk hLength hTime hMass hTemperature hCurrent hAmount hLuminousIntensity =>
          cases hLength
          cases hTime
          cases hMass
          cases hTemperature
          cases hCurrent
          cases hAmount
          cases hLuminousIntensity
          rfl

/-- [MDD-T03] A non-derived signature is rejected by at least one basis constraint. -/
theorem MDD_T03_nonderived_dimension_cannot_agree_with_all_basis_responses
    (action : CalibrationAction)
    (dimension : DimensionSignature)
    (different : dimension ≠ derivedDimension action) :
    ¬ BasisAgreement action dimension := by
  intro agreement
  exact different (MDD_T02_basis_agreement_is_unique action dimension agreement)

/-- [MDD-T04] Every admissible calibration action determines exactly one dimension. -/
theorem MDD_T04_calibration_action_has_unique_dimension
    (action : CalibrationAction) :
    ∃ dimension : DimensionSignature,
      BasisAgreement action dimension ∧
      ∀ candidate : DimensionSignature,
        BasisAgreement action candidate → candidate = dimension := by
  refine ⟨derivedDimension action, MDD_T01_derived_dimension_agrees_with_basis action, ?_⟩
  intro candidate agreement
  exact MDD_T02_basis_agreement_is_unique action candidate agreement

/-- [MDD-T05] Identity calibration has zero response by admissibility. -/
theorem MDD_T05_zero_calibration_has_zero_response
    (action : CalibrationAction)
    (generator : CalibrationGenerator) :
    action.response generator 0 = 0 := by
  exact action.zeroResponse generator

/-- [MDD-T06] Sequential calibration changes compose additively by admissibility. -/
theorem MDD_T06_calibration_composition_is_additive
    (action : CalibrationAction)
    (generator : CalibrationGenerator)
    (left right : Int) :
    action.response generator (left + right) =
      action.response generator left + action.response generator right := by
  exact action.composeResponse generator left right

/-- A measurement channel carries an action, not an independent dimension field. -/
structure DerivedMeasurementChannel (State : Type u) (Reading : Type v) where
  observe : State → Reading
  calibrate : Reading → Reading
  calibrationAction : CalibrationAction

/-- The channel dimension is computed from its calibration action. -/
def channelDimension
    (channel : DerivedMeasurementChannel State Reading) : DimensionSignature :=
  derivedDimension channel.calibrationAction

/-- [MDD-T07] Every channel's dimension satisfies its own calibration basis contract. -/
theorem MDD_T07_channel_dimension_is_basis_derived
    (channel : DerivedMeasurementChannel State Reading) :
    BasisAgreement channel.calibrationAction (channelDimension channel) := by
  exact MDD_T01_derived_dimension_agrees_with_basis channel.calibrationAction

/-- [MDD-T08] Equal calibration actions force equal derived dimensions. -/
theorem MDD_T08_equal_calibration_action_forces_equal_dimension
    (left right : DerivedMeasurementChannel State Reading)
    (sameAction : left.calibrationAction = right.calibrationAction) :
    channelDimension left = channelDimension right := by
  exact congrArg derivedDimension sameAction

/-- A full system couples the dimension-free ontology to the derived measurement layer. -/
structure DerivedMeasurementSystem (State : Type u) (Reading : Type v) where
  ontology : PremetricOntology State
  channel : DerivedMeasurementChannel State Reading

/-- Forget all measurement/calibration structure. -/
def forgetMeasurement
    (system : DerivedMeasurementSystem State Reading) : PremetricOntology State :=
  system.ontology

/-- Replace only the calibration action of the measurement layer. -/
def replaceCalibrationAction
    (system : DerivedMeasurementSystem State Reading)
    (action : CalibrationAction) : DerivedMeasurementSystem State Reading :=
  {
    system with
    channel := { system.channel with calibrationAction := action }
  }

/-- [MDD-T09] Changing measurement calibration cannot rewrite the premetric ontology. -/
theorem MDD_T09_calibration_change_preserves_premetric_ontology
    (system : DerivedMeasurementSystem State Reading)
    (action : CalibrationAction) :
    forgetMeasurement (replaceCalibrationAction system action) =
      forgetMeasurement system := by
  rfl

/-- Conventional length signature, now only a measurement-layer representation. -/
def lengthDimension : DimensionSignature := ⟨1, 0, 0, 0, 0, 0, 0⟩

/-- Calibration action whose only unit response is the length generator. -/
def lengthCalibrationAction : CalibrationAction where
  response generator count :=
    match generator with
    | .lengthScale => count
    | .timeScale => 0
    | .massScale => 0
    | .temperatureScale => 0
    | .currentScale => 0
    | .amountScale => 0
    | .luminousIntensityScale => 0
  zeroResponse := by
    intro generator
    cases generator <;> rfl
  composeResponse := by
    intro generator left right
    cases generator <;> rfl

/-- [MDD-T10] The conventional length signature is derived from its calibration action. -/
theorem MDD_T10_length_dimension_is_calibration_derived :
    derivedDimension lengthCalibrationAction = lengthDimension := by
  rfl

/-- Conventional time signature, again only at the measurement representation layer. -/
def timeDimension : DimensionSignature := ⟨0, 1, 0, 0, 0, 0, 0⟩

/-- Calibration action whose only unit response is the time generator. -/
def timeCalibrationAction : CalibrationAction where
  response generator count :=
    match generator with
    | .lengthScale => 0
    | .timeScale => count
    | .massScale => 0
    | .temperatureScale => 0
    | .currentScale => 0
    | .amountScale => 0
    | .luminousIntensityScale => 0
  zeroResponse := by
    intro generator
    cases generator <;> rfl
  composeResponse := by
    intro generator left right
    cases generator <;> rfl

/-- [MDD-T11] The conventional time signature is derived from its calibration action. -/
theorem MDD_T11_time_dimension_is_calibration_derived :
    derivedDimension timeCalibrationAction = timeDimension := by
  rfl

end MeasurementDerivedDimensions
end Physics
end V2
end QIKVRT
