import Std
import VRTCore_QCE_Model
import MeasurementDerivedDimensions
import QCENowSerialization

/-!
# QCA-004: QCE operational causal-axis and null-boundary bridge

This module continues the proof chain after QCE now-state serialization.

The preceding QNS result provides a unique serial coordinate and an additive abstract
calibration response for QCE-generated now-states. The present module adds explicit
*operational* criteria for interpreting that response:

* the temporal axis is the calibration axis that records one unit for a pure causal
  succession and zero units on the length axis;
* the spatial axis is the calibration axis that records one unit for a pure separation
  observation and zero units on the time axis;
* an admissible classical-cone witness supplies a stable null boundary;
* combining the selected spatial and temporal dimensions yields the propagation-speed
  dimension L T^-1.

The operational criteria are correspondence premises, not conclusions of bare
seriality. The model therefore proves conditional uniqueness while retaining an
explicit countermodel showing that seriality alone does not choose a physical axis.
It does not derive the SI second or metre, the numerical value of c, hbar, G, Einstein
dynamics, or physical/empirical correspondence.
-/

namespace QIKVRT.V2.Physics.QCECausalAxisBridge

open QIKVRT.VRTCore.QCE
open QIKVRT.V2.Physics.MeasurementDerivedDimensions
open QIKVRT.V2.Physics.QCENowSerialization

/-- Operational criterion: one pure QCE succession is recorded on the time axis. -/
def TemporalSuccessionAgreement (binding : AxisBinding) : Prop :=
  (liftSerialCalibration binding).response .timeScale 1 = 1 ∧
  (liftSerialCalibration binding).response .lengthScale 1 = 0

/-- Operational criterion: one pure separation is recorded on the length axis. -/
def SpatialSeparationAgreement (binding : AxisBinding) : Prop :=
  (liftSerialCalibration binding).response .lengthScale 1 = 1 ∧
  (liftSerialCalibration binding).response .timeScale 1 = 0

/-- [QCA-T01] The canonical time binding satisfies the succession criterion. -/
theorem QCA_T01_time_binding_satisfies_succession :
    TemporalSuccessionAgreement qceTimeBinding := by
  simp [TemporalSuccessionAgreement, qceTimeBinding, liftSerialCalibration,
    qceSerialCalibration]

/-- [QCA-T02] The succession criterion uniquely selects the time generator. -/
theorem QCA_T02_succession_agreement_selects_time_axis
    (binding : AxisBinding)
    (agreement : TemporalSuccessionAgreement binding) :
    binding.axis = .timeScale := by
  rcases agreement with ⟨timeResponse, _⟩
  cases binding with
  | mk axis =>
      cases axis <;>
        simp [liftSerialCalibration, qceSerialCalibration] at timeResponse ⊢

/-- [QCA-T03] The canonical length binding satisfies the separation criterion. -/
theorem QCA_T03_length_binding_satisfies_separation :
    SpatialSeparationAgreement qceLengthBinding := by
  simp [SpatialSeparationAgreement, qceLengthBinding, liftSerialCalibration,
    qceSerialCalibration]

/-- [QCA-T04] The separation criterion uniquely selects the length generator. -/
theorem QCA_T04_separation_agreement_selects_length_axis
    (binding : AxisBinding)
    (agreement : SpatialSeparationAgreement binding) :
    binding.axis = .lengthScale := by
  rcases agreement with ⟨lengthResponse, _⟩
  cases binding with
  | mk axis =>
      cases axis <;>
        simp [liftSerialCalibration, qceSerialCalibration] at lengthResponse ⊢

/-- [QCA-T05] Axis bindings are equal when their sole axis fields are equal. -/
theorem QCA_T05_axis_binding_extensionality
    (left right : AxisBinding)
    (sameAxis : left.axis = right.axis) :
    left = right := by
  cases left
  cases right
  cases sameAxis
  rfl

/-- [QCA-T06] Any succession-compatible binding is the canonical time binding. -/
theorem QCA_T06_temporal_binding_is_unique
    (binding : AxisBinding)
    (agreement : TemporalSuccessionAgreement binding) :
    binding = qceTimeBinding := by
  apply QCA_T05_axis_binding_extensionality
  simpa [qceTimeBinding] using
    QCA_T02_succession_agreement_selects_time_axis binding agreement

/-- [QCA-T07] Any separation-compatible binding is the canonical length binding. -/
theorem QCA_T07_spatial_binding_is_unique
    (binding : AxisBinding)
    (agreement : SpatialSeparationAgreement binding) :
    binding = qceLengthBinding := by
  apply QCA_T05_axis_binding_extensionality
  simpa [qceLengthBinding] using
    QCA_T04_separation_agreement_selects_length_axis binding agreement

/-- Evidence package connecting QCE cone closure to operational axis criteria. -/
structure CausalNullAxisEvidence where
  cone : ClassicalConeWitnesses
  coneAdmissible : classicalConeAdmissible cone = true
  temporalBinding : AxisBinding
  spatialBinding : AxisBinding
  temporalAgreement : TemporalSuccessionAgreement temporalBinding
  spatialAgreement : SpatialSeparationAgreement spatialBinding

/-- [QCA-T08] Admissible cone evidence necessarily contains a stable null boundary. -/
theorem QCA_T08_admissible_cone_has_stable_null_boundary
    (evidence : CausalNullAxisEvidence) :
    evidence.cone.nullBoundaryStable = true := by
  exact classicalCone_requires_stableNullBoundary
    evidence.cone evidence.coneAdmissible

/-- [QCA-T09] Complete operational evidence uniquely fixes the temporal binding. -/
theorem QCA_T09_evidence_selects_time_binding
    (evidence : CausalNullAxisEvidence) :
    evidence.temporalBinding = qceTimeBinding := by
  exact QCA_T06_temporal_binding_is_unique
    evidence.temporalBinding evidence.temporalAgreement

/-- [QCA-T10] Complete operational evidence uniquely fixes the spatial binding. -/
theorem QCA_T10_evidence_selects_length_binding
    (evidence : CausalNullAxisEvidence) :
    evidence.spatialBinding = qceLengthBinding := by
  exact QCA_T07_spatial_binding_is_unique
    evidence.spatialBinding evidence.spatialAgreement

/-- [QCA-T11] The selected temporal and spatial bindings are distinct. -/
theorem QCA_T11_selected_axes_are_distinct
    (evidence : CausalNullAxisEvidence) :
    evidence.temporalBinding ≠ evidence.spatialBinding := by
  rw [QCA_T09_evidence_selects_time_binding evidence]
  rw [QCA_T10_evidence_selects_length_binding evidence]
  intro equalBindings
  have equalAxes := congrArg AxisBinding.axis equalBindings
  simpa [qceTimeBinding, qceLengthBinding] using equalAxes

/-- Componentwise difference of two measurement-layer dimension signatures. -/
def dimensionDifference
    (left right : DimensionSignature) : DimensionSignature :=
  {
    lengthExp := left.lengthExp - right.lengthExp
    timeExp := left.timeExp - right.timeExp
    massExp := left.massExp - right.massExp
    temperatureExp := left.temperatureExp - right.temperatureExp
    currentExp := left.currentExp - right.currentExp
    amountExp := left.amountExp - right.amountExp
    luminousIntensityExp :=
      left.luminousIntensityExp - right.luminousIntensityExp
  }

/-- Conventional representation of propagation speed: L T^-1. -/
def propagationSpeedDimension : DimensionSignature :=
  ⟨1, -1, 0, 0, 0, 0, 0⟩

/-- Calibration action for one null-propagation unit in normalized representation. -/
def nullPropagationCalibration : CalibrationAction where
  response generator count :=
    match generator with
    | .lengthScale => count
    | .timeScale => -count
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
    cases generator <;> simp <;> omega

/-- [QCA-T12] Null-propagation calibration derives the speed dimension L T^-1. -/
theorem QCA_T12_null_calibration_derives_speed_dimension :
    derivedDimension nullPropagationCalibration = propagationSpeedDimension := by
  rfl

/-- [QCA-T13] Any signature agreeing with null calibration is the speed dimension. -/
theorem QCA_T13_speed_dimension_is_unique
    (dimension : DimensionSignature)
    (agreement : BasisAgreement nullPropagationCalibration dimension) :
    dimension = propagationSpeedDimension := by
  calc
    dimension = derivedDimension nullPropagationCalibration :=
      MDD_T02_basis_agreement_is_unique
        nullPropagationCalibration dimension agreement
    _ = propagationSpeedDimension :=
      QCA_T12_null_calibration_derives_speed_dimension

/-- [QCA-T14] Selected length minus selected time yields the speed dimension. -/
theorem QCA_T14_evidence_derives_speed_dimension
    (evidence : CausalNullAxisEvidence) :
    dimensionDifference
      (derivedDimension (liftSerialCalibration evidence.spatialBinding))
      (derivedDimension (liftSerialCalibration evidence.temporalBinding)) =
    propagationSpeedDimension := by
  rw [QCA_T10_evidence_selects_length_binding evidence]
  rw [QCA_T09_evidence_selects_time_binding evidence]
  rw [QNS_T14_length_binding_derives_length_dimension]
  rw [QNS_T15_time_binding_derives_time_dimension]
  rfl

/-- [QCA-T15] Bare seriality still admits distinct length and time bindings. -/
theorem QCA_T15_seriality_alone_does_not_select_axis :
    ∃ left right : AxisBinding,
      left.axis ≠ right.axis ∧
      (liftSerialCalibration left).response left.axis 1 =
        (liftSerialCalibration right).response right.axis 1 := by
  exact QNS_T17_seriality_alone_does_not_select_physical_axis

/-- [QCA-T16] The repository's current QCE cone candidate remains unclosed. -/
theorem QCA_T16_current_qce_cone_candidate_remains_open :
    classicalConeAdmissible currentConeCandidate = false := by
  exact currentConeCandidate_is_not_admissible

/-- A constructively satisfiable finite evidence package, not a physical discovery. -/
def completeFiniteAxisEvidence : CausalNullAxisEvidence where
  cone := completeConeWitness
  coneAdmissible := completeConeWitness_is_admissible
  temporalBinding := qceTimeBinding
  spatialBinding := qceLengthBinding
  temporalAgreement := QCA_T01_time_binding_satisfies_succession
  spatialAgreement := QCA_T03_length_binding_satisfies_separation

/-- [QCA-T17] The complete finite evidence package has a stable null boundary. -/
theorem QCA_T17_complete_finite_evidence_has_stable_null_boundary :
    completeFiniteAxisEvidence.cone.nullBoundaryStable = true := by
  exact QCA_T08_admissible_cone_has_stable_null_boundary
    completeFiniteAxisEvidence

/-- [QCA-T18] The complete finite evidence package derives L T^-1. -/
theorem QCA_T18_complete_finite_evidence_derives_speed_dimension :
    dimensionDifference
      (derivedDimension
        (liftSerialCalibration completeFiniteAxisEvidence.spatialBinding))
      (derivedDimension
        (liftSerialCalibration completeFiniteAxisEvidence.temporalBinding)) =
    propagationSpeedDimension := by
  exact QCA_T14_evidence_derives_speed_dimension completeFiniteAxisEvidence

end QIKVRT.V2.Physics.QCECausalAxisBridge
