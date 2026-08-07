import Std
import VRTCore_QCE_Model
import MeasurementDerivedDimensions
import QCENowSerialization
import QCECausalAxisBridge

/-!
# QNCR-005: Null calibration ratio and the numerical c token

This module continues the serialized QIK-VRT proof chain.

The upstream QCA bridge conditionally selects temporal and spatial calibration axes
and derives the propagation-speed dimension L T^-1 for a stable null boundary. The
present module separates that dimension from its numerical representation.

A null numerical calibration assigns positive length and time numerals to one fixed
null-propagation step. When the time standard is fixed to one unit, exactly one scalar
remains: the length numeral per unit time. This scalar is the numerical c token of the
chosen calibration. A time-preserving conversion from the normalized 1:1 calibration
is therefore completely determined by one length factor.

The same QCE/null evidence admits both a normalized token 1 and an SI-like token
299792458. Consequently the abstract QCE structure and stable null boundary do not by
themselves derive the physical numerical value of c. That value requires an external
calibration/measurement binding. This module does not derive the SI, hbar, G, Einstein
dynamics, or physical/empirical correspondence.
-/

namespace QIKVRT.V2.Physics.QCENullCalibrationRatio

open QIKVRT.VRTCore.QCE
open QIKVRT.V2.Physics.MeasurementDerivedDimensions
open QIKVRT.V2.Physics.QCENowSerialization
open QIKVRT.V2.Physics.QCECausalAxisBridge

/-- Positive numerical readings assigned to one fixed null-propagation step. -/
structure NullNumericalCalibration where
  lengthNumeral : Nat
  timeNumeral : Nat
  lengthPositive : 0 < lengthNumeral
  timePositive : 0 < timeNumeral

/-- A fixed QCE/null evidence package together with one numerical calibration. -/
structure CalibratedNullRepresentation where
  evidence : CausalNullAxisEvidence
  calibration : NullNumericalCalibration

/-- Two representations have the same causal evidence when only numerals may differ. -/
def sameCausalEvidence
    (left right : CalibratedNullRepresentation) : Prop :=
  left.evidence = right.evidence

/-- Replace only numerical readings; retain the QCE/null evidence. -/
def reencodeNullCalibration
    (representation : CalibratedNullRepresentation)
    (calibration : NullNumericalCalibration) : CalibratedNullRepresentation :=
  { representation with calibration := calibration }

/-- Normalized null calibration: one length unit per one time unit. -/
def normalizedCalibration : NullNumericalCalibration where
  lengthNumeral := 1
  timeNumeral := 1
  lengthPositive := by decide
  timePositive := by decide

/-- SI-like calibration token; this is an explicit representation, not a derivation. -/
def siLikeCalibration : NullNumericalCalibration where
  lengthNumeral := 299792458
  timeNumeral := 1
  lengthPositive := by decide
  timePositive := by decide

/-- The same complete finite QCE evidence in normalized numerical representation. -/
def normalizedRepresentation : CalibratedNullRepresentation where
  evidence := completeFiniteAxisEvidence
  calibration := normalizedCalibration

/-- The same complete finite QCE evidence in SI-like numerical representation. -/
def siLikeRepresentation : CalibratedNullRepresentation where
  evidence := completeFiniteAxisEvidence
  calibration := siLikeCalibration

/-- [QNCR-T01] Normalized and SI-like encodings retain identical QCE/null evidence. -/
theorem QNCR_T01_normalized_and_si_share_causal_evidence :
    sameCausalEvidence normalizedRepresentation siLikeRepresentation := by
  rfl

/-- [QNCR-T02] The two numerical calibration records are distinct. -/
theorem QNCR_T02_normalized_and_si_calibrations_are_distinct :
    normalizedCalibration ≠ siLikeCalibration := by
  intro sameCalibration
  have sameLength := congrArg NullNumericalCalibration.lengthNumeral sameCalibration
  simp [normalizedCalibration, siLikeCalibration] at sameLength

/-- [QNCR-T03] Every calibrated representation retains a stable null boundary. -/
theorem QNCR_T03_representation_has_stable_null_boundary
    (representation : CalibratedNullRepresentation) :
    representation.evidence.cone.nullBoundaryStable = true := by
  exact QCA_T08_admissible_cone_has_stable_null_boundary representation.evidence

/-- Dimension of the selected null propagation, independent of numerical readings. -/
def representationSpeedDimension
    (representation : CalibratedNullRepresentation) : DimensionSignature :=
  dimensionDifference
    (derivedDimension
      (liftSerialCalibration representation.evidence.spatialBinding))
    (derivedDimension
      (liftSerialCalibration representation.evidence.temporalBinding))

/-- [QNCR-T04] Every calibrated representation has speed dimension L T^-1. -/
theorem QNCR_T04_representation_has_speed_dimension
    (representation : CalibratedNullRepresentation) :
    representationSpeedDimension representation = propagationSpeedDimension := by
  exact QCA_T14_evidence_derives_speed_dimension representation.evidence

/-- [QNCR-T05] Numerical re-encoding cannot change the QCE/null evidence. -/
theorem QNCR_T05_reencoding_preserves_causal_evidence
    (representation : CalibratedNullRepresentation)
    (calibration : NullNumericalCalibration) :
    sameCausalEvidence
      (reencodeNullCalibration representation calibration)
      representation := by
  rfl

/-- [QNCR-T06] Numerical re-encoding cannot change the speed dimension. -/
theorem QNCR_T06_reencoding_preserves_speed_dimension
    (representation : CalibratedNullRepresentation)
    (calibration : NullNumericalCalibration) :
    representationSpeedDimension
      (reencodeNullCalibration representation calibration) =
    representationSpeedDimension representation := by
  rfl

/-- A unit-time calibration fixes the temporal numerical standard to one. -/
def UnitTimeStandard (calibration : NullNumericalCalibration) : Prop :=
  calibration.timeNumeral = 1

/-- The numerical c token under a unit-time reading. -/
def cToken (calibration : NullNumericalCalibration) : Nat :=
  calibration.lengthNumeral

/-- [QNCR-T07] The normalized calibration uses one unit of time. -/
theorem QNCR_T07_normalized_calibration_has_unit_time :
    UnitTimeStandard normalizedCalibration := by
  rfl

/-- [QNCR-T08] The SI-like calibration also uses one unit of time. -/
theorem QNCR_T08_si_calibration_has_unit_time :
    UnitTimeStandard siLikeCalibration := by
  rfl

/-- [QNCR-T09] The normalized numerical c token is one. -/
theorem QNCR_T09_normalized_c_token_is_one :
    cToken normalizedCalibration = 1 := by
  rfl

/-- [QNCR-T10] The explicit SI-like numerical c token is 299792458. -/
theorem QNCR_T10_si_like_c_token_is_299792458 :
    cToken siLikeCalibration = 299792458 := by
  rfl

/-- A reported token agrees with both numerical readings of one calibration. -/
def FixedUnitTimeReading
    (calibration : NullNumericalCalibration)
    (token : Nat) : Prop :=
  calibration.timeNumeral = 1 ∧ calibration.lengthNumeral = token

/-- [QNCR-T11] A fixed unit-time reading determines the reported c token. -/
theorem QNCR_T11_fixed_reading_determines_c_token
    (calibration : NullNumericalCalibration)
    (token : Nat)
    (agreement : FixedUnitTimeReading calibration token) :
    cToken calibration = token := by
  exact agreement.2

/-- [QNCR-T12] One fixed calibration cannot report two different c tokens. -/
theorem QNCR_T12_fixed_reading_token_is_unique
    (calibration : NullNumericalCalibration)
    (left right : Nat)
    (leftAgreement : FixedUnitTimeReading calibration left)
    (rightAgreement : FixedUnitTimeReading calibration right) :
    left = right := by
  exact leftAgreement.2.symm.trans rightAgreement.2

/-- Multiplicative change of the numerical length/time standards. -/
structure CalibrationConversion
    (source target : NullNumericalCalibration) where
  lengthFactor : Nat
  timeFactor : Nat
  lengthRule :
    target.lengthNumeral = source.lengthNumeral * lengthFactor
  timeRule :
    target.timeNumeral = source.timeNumeral * timeFactor

/-- Explicit conversion from normalized to SI-like numerical representation. -/
def normalizedToSIConversion :
    CalibrationConversion normalizedCalibration siLikeCalibration where
  lengthFactor := 299792458
  timeFactor := 1
  lengthRule := rfl
  timeRule := rfl

/-- [QNCR-T13] The normalized-to-SI conversion uses one length factor and unit time factor. -/
theorem QNCR_T13_normalized_to_si_conversion_factors :
    normalizedToSIConversion.lengthFactor = 299792458 ∧
    normalizedToSIConversion.timeFactor = 1 := by
  exact ⟨rfl, rfl⟩

/-- [QNCR-T14] That explicit conversion preserves the chosen time standard. -/
theorem QNCR_T14_normalized_to_si_preserves_unit_time :
    siLikeCalibration.timeNumeral = normalizedCalibration.timeNumeral := by
  rfl

/-- [QNCR-T15] A time-preserving conversion from normalized units keeps unit time. -/
theorem QNCR_T15_time_preserving_conversion_keeps_unit_time
    (target : NullNumericalCalibration)
    (conversion : CalibrationConversion normalizedCalibration target)
    (preservesTime : conversion.timeFactor = 1) :
    target.timeNumeral = 1 := by
  calc
    target.timeNumeral =
        normalizedCalibration.timeNumeral * conversion.timeFactor :=
      conversion.timeRule
    _ = 1 := by simp [normalizedCalibration, preservesTime]

/-- [QNCR-T16] Under fixed unit time, one length factor is the complete c token. -/
theorem QNCR_T16_one_scalar_determines_c_token
    (target : NullNumericalCalibration)
    (conversion : CalibrationConversion normalizedCalibration target) :
    cToken target = conversion.lengthFactor := by
  calc
    cToken target = target.lengthNumeral := rfl
    _ = normalizedCalibration.lengthNumeral * conversion.lengthFactor :=
      conversion.lengthRule
    _ = conversion.lengthFactor := by simp [normalizedCalibration]

/--
[QNCR-T17] Countermodel: identical QCE/null evidence admits different numerical c
tokens. Therefore abstract QCE plus the cone does not fix 299792458.
-/
theorem QNCR_T17_same_causal_evidence_allows_distinct_c_tokens :
    ∃ left right : CalibratedNullRepresentation,
      sameCausalEvidence left right ∧
      cToken left.calibration ≠ cToken right.calibration := by
  refine ⟨normalizedRepresentation, siLikeRepresentation, ?_, ?_⟩
  · exact QNCR_T01_normalized_and_si_share_causal_evidence
  · decide

/-- [QNCR-T18] Every unit-time calibration has exactly one numerical c token. -/
theorem QNCR_T18_unit_time_calibration_has_unique_c_token
    (calibration : NullNumericalCalibration)
    (unitTime : UnitTimeStandard calibration) :
    ∃ token,
      FixedUnitTimeReading calibration token ∧
      ∀ candidate,
        FixedUnitTimeReading calibration candidate → candidate = token := by
  refine ⟨cToken calibration, ?_, ?_⟩
  · exact ⟨unitTime, rfl⟩
  · intro candidate agreement
    simpa [cToken] using agreement.2.symm

end QIKVRT.V2.Physics.QCENullCalibrationRatio
