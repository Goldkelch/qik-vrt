import Std
import VRTCore_QCE_Model
import MeasurementDerivedDimensions
import QCENowSerialization
import QCECausalAxisBridge
import QCENullCalibrationRatio

/-!
# QCMB-006: Fail-closed empirical binding of the numerical c token

The upstream QNCR module proves that a fixed unit-time convention leaves one unique
numerical c token, while unchanged QCE/null evidence does not determine its numerical
value. This module formalizes the next epistemic bridge: a numerical token may be
classified as empirically bound only through an explicit measurement receipt.

An accepted receipt must bind its source, calibrated instrument, null observable,
unit convention, uncertainty account and independent reproduction. It must also use a
unit-time calibration and report exactly the c token carried by that calibration.

The theorems establish necessity and uniqueness of this binding contract. A complete
finite SI-like receipt is provided only to prove constructive satisfiability of the
contract. It is not evidence that such a receipt has actually been obtained, does not
replace external measurement bytes, and does not derive 299792458 from QCE dynamics.
No SI, hbar, G, Einstein dynamics or physical correspondence is established here.
-/

namespace QIKVRT.V2.Physics.QCECMeasurementBinding

open QIKVRT.VRTCore.QCE
open QIKVRT.V2.Physics.MeasurementDerivedDimensions
open QIKVRT.V2.Physics.QCENowSerialization
open QIKVRT.V2.Physics.QCECausalAxisBridge
open QIKVRT.V2.Physics.QCENullCalibrationRatio

/-- Contract-level record for one numerical light-speed measurement binding. -/
structure CMeasurementReceipt where
  sourceDigestBound : Bool
  instrumentCalibrated : Bool
  nullObservableBound : Bool
  unitConventionBound : Bool
  uncertaintyBound : Bool
  independentlyReproduced : Bool
  calibration : NullNumericalCalibration
  measuredToken : Nat

/--
Accepted evidence is structural, not rhetorical: every gate and both numerical
consistency obligations must be inhabited.
-/
structure AcceptedCMeasurementReceipt
    (receipt : CMeasurementReceipt) : Prop where
  sourceDigestBound : receipt.sourceDigestBound = true
  instrumentCalibrated : receipt.instrumentCalibrated = true
  nullObservableBound : receipt.nullObservableBound = true
  unitConventionBound : receipt.unitConventionBound = true
  uncertaintyBound : receipt.uncertaintyBound = true
  independentlyReproduced : receipt.independentlyReproduced = true
  unitTimeStandard : UnitTimeStandard receipt.calibration
  tokenMatchesCalibration :
    receipt.measuredToken = cToken receipt.calibration

/-- [QCMB-T01] Acceptance requires source-digest binding. -/
theorem QCMB_T01_acceptance_requires_source_binding
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.sourceDigestBound = true :=
  accepted.sourceDigestBound

/-- [QCMB-T02] Acceptance requires instrument calibration. -/
theorem QCMB_T02_acceptance_requires_instrument_calibration
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.instrumentCalibrated = true :=
  accepted.instrumentCalibrated

/-- [QCMB-T03] Acceptance requires binding to the null observable. -/
theorem QCMB_T03_acceptance_requires_null_observable_binding
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.nullObservableBound = true :=
  accepted.nullObservableBound

/-- [QCMB-T04] Acceptance requires an explicit unit-convention binding. -/
theorem QCMB_T04_acceptance_requires_unit_convention
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.unitConventionBound = true :=
  accepted.unitConventionBound

/-- [QCMB-T05] Acceptance requires an uncertainty account. -/
theorem QCMB_T05_acceptance_requires_uncertainty_binding
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.uncertaintyBound = true :=
  accepted.uncertaintyBound

/-- [QCMB-T06] Acceptance requires independent reproduction. -/
theorem QCMB_T06_acceptance_requires_independent_reproduction
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.independentlyReproduced = true :=
  accepted.independentlyReproduced

/-- [QCMB-T07] An accepted receipt uses a unit-time calibration. -/
theorem QCMB_T07_acceptance_requires_unit_time
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    UnitTimeStandard receipt.calibration :=
  accepted.unitTimeStandard

/-- [QCMB-T08] An accepted measured token equals its calibration's c token. -/
theorem QCMB_T08_acceptance_binds_measured_token
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    receipt.measuredToken = cToken receipt.calibration :=
  accepted.tokenMatchesCalibration

/-- [QCMB-T09] Acceptance creates a fixed unit-time reading. -/
theorem QCMB_T09_acceptance_yields_fixed_unit_time_reading
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt) :
    FixedUnitTimeReading receipt.calibration receipt.measuredToken := by
  constructor
  · exact accepted.unitTimeStandard
  · simpa [cToken] using accepted.tokenMatchesCalibration.symm

/-- [QCMB-T10] No second token can satisfy the same accepted calibration. -/
theorem QCMB_T10_accepted_measurement_token_is_unique
    (receipt : CMeasurementReceipt)
    (accepted : AcceptedCMeasurementReceipt receipt)
    (candidate : Nat)
    (candidateAgreement :
      FixedUnitTimeReading receipt.calibration candidate) :
    candidate = receipt.measuredToken := by
  exact QNCR_T12_fixed_reading_token_is_unique
    receipt.calibration candidate receipt.measuredToken
    candidateAgreement
    (QCMB_T09_acceptance_yields_fixed_unit_time_reading receipt accepted)

/-- [QCMB-T11] Two accepted receipts on the same calibration bind the same token. -/
theorem QCMB_T11_same_calibration_forces_same_accepted_token
    (left right : CMeasurementReceipt)
    (leftAccepted : AcceptedCMeasurementReceipt left)
    (rightAccepted : AcceptedCMeasurementReceipt right)
    (sameCalibration : left.calibration = right.calibration) :
    left.measuredToken = right.measuredToken := by
  calc
    left.measuredToken = cToken left.calibration :=
      leftAccepted.tokenMatchesCalibration
    _ = cToken right.calibration := by rw [sameCalibration]
    _ = right.measuredToken :=
      rightAccepted.tokenMatchesCalibration.symm

/-- [QCMB-T12] An unbound source fails closed. -/
theorem QCMB_T12_unbound_source_cannot_be_accepted
    (receipt : CMeasurementReceipt)
    (unbound : receipt.sourceDigestBound = false) :
    ¬ AcceptedCMeasurementReceipt receipt := by
  intro accepted
  have impossible : (false : Bool) = true :=
    unbound.symm.trans accepted.sourceDigestBound
  cases impossible

/-- [QCMB-T13] An uncalibrated instrument fails closed. -/
theorem QCMB_T13_uncalibrated_instrument_cannot_be_accepted
    (receipt : CMeasurementReceipt)
    (uncalibrated : receipt.instrumentCalibrated = false) :
    ¬ AcceptedCMeasurementReceipt receipt := by
  intro accepted
  have impossible : (false : Bool) = true :=
    uncalibrated.symm.trans accepted.instrumentCalibrated
  cases impossible

/-- [QCMB-T14] Missing independent reproduction fails closed. -/
theorem QCMB_T14_unreproduced_receipt_cannot_be_accepted
    (receipt : CMeasurementReceipt)
    (unreproduced : receipt.independentlyReproduced = false) :
    ¬ AcceptedCMeasurementReceipt receipt := by
  intro accepted
  have impossible : (false : Bool) = true :=
    unreproduced.symm.trans accepted.independentlyReproduced
  cases impossible

/-- [QCMB-T15] A measured token inconsistent with its calibration fails closed. -/
theorem QCMB_T15_mismatched_token_cannot_be_accepted
    (receipt : CMeasurementReceipt)
    (different : receipt.measuredToken ≠ cToken receipt.calibration) :
    ¬ AcceptedCMeasurementReceipt receipt := by
  intro accepted
  exact different accepted.tokenMatchesCalibration

/-- Repository state: no actual byte-bound external measurement receipt is supplied. -/
def currentRepositoryCMeasurementCandidate : CMeasurementReceipt where
  sourceDigestBound := false
  instrumentCalibrated := false
  nullObservableBound := false
  unitConventionBound := false
  uncertaintyBound := false
  independentlyReproduced := false
  calibration := normalizedCalibration
  measuredToken := 1

/-- [QCMB-T16] The current repository candidate is not empirically accepted. -/
theorem QCMB_T16_current_repository_candidate_is_not_accepted :
    ¬ AcceptedCMeasurementReceipt currentRepositoryCMeasurementCandidate := by
  apply QCMB_T12_unbound_source_cannot_be_accepted
  rfl

/--
A constructively complete SI-like contract witness. This is model satisfiability only,
not an assertion that external experimental evidence has been ingested.
-/
def completeFiniteSILikeReceipt : CMeasurementReceipt where
  sourceDigestBound := true
  instrumentCalibrated := true
  nullObservableBound := true
  unitConventionBound := true
  uncertaintyBound := true
  independentlyReproduced := true
  calibration := siLikeCalibration
  measuredToken := 299792458

/-- [QCMB-T17] The complete finite contract witness is accepted in the model. -/
theorem QCMB_T17_complete_finite_si_like_receipt_is_accepted :
    AcceptedCMeasurementReceipt completeFiniteSILikeReceipt := by
  exact ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

/-- [QCMB-T18] Its token is the explicitly supplied SI-like token. -/
theorem QCMB_T18_complete_finite_si_like_token_is_299792458 :
    completeFiniteSILikeReceipt.measuredToken = 299792458 := by
  rfl

end QIKVRT.V2.Physics.QCECMeasurementBinding
