import Std
import VRTCore_QCE_Model
import MeasurementDerivedDimensions

/-!
# QNS-003: QCE now-state serialization and calibration bridge

This module composes the existing finite QCE relation-network model with the
measurement-derived-dimensions model.

The QCE network extension adds two events and one globally bound relation. Repeated
extension therefore supplies a canonical, recoverable serial index for every network
in the generated now-set. The resulting abstract serial response is additive. It can
be lifted into the measurement calibration layer only through an explicit axis
binding.

The formal result is deliberately bounded: QCE network extension determines a unique
serial coordinate inside this finite model. It does not by itself identify that
coordinate with physical time, physical length, the SI second or metre, or a measured
value of c. The existence of distinct length and time bindings with the same abstract
serial response is retained as an explicit countermodel to an unproved physical-axis
identification.
-/

namespace QIKVRT.V2.Physics.QCENowSerialization

open QIKVRT.VRTCore.QCE
open QIKVRT.V2.Physics.MeasurementDerivedDimensions

/-- Apply the existing QCE network extension a finite number of times. -/
def iterateNetwork : Nat → RelationNetwork → RelationNetwork
  | 0, network => network
  | Nat.succ steps, network => iterateNetwork steps (extendNetwork network)

/-- [QNS-T01] Every QCE extension contributes exactly one relation record. -/
theorem QNS_T01_iterated_relation_count
    (steps : Nat) (network : RelationNetwork) :
    (iterateNetwork steps network).relations = network.relations + steps := by
  induction steps generalizing network with
  | zero => rfl
  | succ steps ih =>
      calc
        (iterateNetwork (Nat.succ steps) network).relations =
            (iterateNetwork steps (extendNetwork network)).relations := rfl
        _ = (extendNetwork network).relations + steps := ih (extendNetwork network)
        _ = network.relations + Nat.succ steps := by
          simp [extendNetwork]
          omega

/-- [QNS-T02] Every QCE extension contributes exactly two event records. -/
theorem QNS_T02_iterated_event_count
    (steps : Nat) (network : RelationNetwork) :
    (iterateNetwork steps network).events = network.events + 2 * steps := by
  induction steps generalizing network with
  | zero => rfl
  | succ steps ih =>
      calc
        (iterateNetwork (Nat.succ steps) network).events =
            (iterateNetwork steps (extendNetwork network)).events := rfl
        _ = (extendNetwork network).events + 2 * steps := ih (extendNetwork network)
        _ = network.events + 2 * Nat.succ steps := by
          simp [extendNetwork]
          omega

/-- [QNS-T03] Repeated QCE extension preserves the global-binding flag. -/
theorem QNS_T03_iterated_extension_preserves_global_binding
    (steps : Nat) (network : RelationNetwork) :
    (iterateNetwork steps network).globallyBound = network.globallyBound := by
  induction steps generalizing network with
  | zero => rfl
  | succ steps ih =>
      calc
        (iterateNetwork (Nat.succ steps) network).globallyBound =
            (iterateNetwork steps (extendNetwork network)).globallyBound := rfl
        _ = (extendNetwork network).globallyBound := ih (extendNetwork network)
        _ = network.globallyBound := rfl

/-- The nth generated QCE now-state, starting from the existing seed network. -/
def canonicalNow (step : Nat) : RelationNetwork :=
  iterateNetwork step seedNetwork

/-- [QNS-T04] Relation count is the normalized serial coordinate plus one. -/
theorem QNS_T04_canonical_relation_count (step : Nat) :
    (canonicalNow step).relations = step + 1 := by
  unfold canonicalNow
  rw [QNS_T01_iterated_relation_count]
  simp [seedNetwork, Nat.add_comm]

/-- [QNS-T05] Event count is twice the normalized serial coordinate plus one. -/
theorem QNS_T05_canonical_event_count (step : Nat) :
    (canonicalNow step).events = 2 * (step + 1) := by
  unfold canonicalNow
  rw [QNS_T02_iterated_event_count]
  simp [seedNetwork]
  omega

/-- Recover a normalized now-index from a generated relation network. -/
def nowIndex (network : RelationNetwork) : Nat :=
  network.relations - 1

/-- [QNS-T06] The recovered index is a left inverse of canonical generation. -/
theorem QNS_T06_now_index_recovers_step (step : Nat) :
    nowIndex (canonicalNow step) = step := by
  simp [nowIndex, QNS_T04_canonical_relation_count]

/-- [QNS-T07] Distinct serial steps cannot generate the same canonical now-state. -/
theorem QNS_T07_canonical_now_is_injective
    (left right : Nat)
    (sameNetwork : canonicalNow left = canonicalNow right) :
    left = right := by
  have sameIndex := congrArg nowIndex sameNetwork
  simpa only [QNS_T06_now_index_recovers_step] using sameIndex

/-- Membership in the finite-model set of QCE-generated now-states. -/
def InCanonicalNowSet (network : RelationNetwork) : Prop :=
  ∃ step, canonicalNow step = network

/-- [QNS-T08] Every generated now-state has exactly one normalized serial index. -/
theorem QNS_T08_canonical_now_has_unique_index
    (network : RelationNetwork)
    (member : InCanonicalNowSet network) :
    ∃ step,
      canonicalNow step = network ∧
      ∀ candidate, canonicalNow candidate = network → candidate = step := by
  rcases member with ⟨step, hStep⟩
  refine ⟨step, hStep, ?_⟩
  intro candidate hCandidate
  apply QNS_T07_canonical_now_is_injective candidate step
  calc
    canonicalNow candidate = network := hCandidate
    _ = canonicalNow step := hStep.symm

/-- [QNS-T09] One further QCE extension advances the recovered index by one. -/
theorem QNS_T09_extension_advances_now_index (step : Nat) :
    nowIndex (extendNetwork (canonicalNow step)) = Nat.succ step := by
  simp [nowIndex, extendNetwork, QNS_T04_canonical_relation_count]

/-- Abstract signed calibration response of the serial coordinate. -/
structure SerialCalibrationAction where
  response : Int → Int
  zeroResponse : response 0 = 0
  composeResponse : ∀ left right,
    response (left + right) = response left + response right

/-- Canonical QCE serial calibration: a signed step is represented by itself. -/
def qceSerialCalibration : SerialCalibrationAction where
  response count := count
  zeroResponse := rfl
  composeResponse := by
    intro left right
    rfl

/-- [QNS-T10] The canonical serial calibration preserves the neutral step. -/
theorem QNS_T10_serial_calibration_zero :
    qceSerialCalibration.response 0 = 0 := by
  exact qceSerialCalibration.zeroResponse

/-- [QNS-T11] Serial calibration composes additively. -/
theorem QNS_T11_serial_calibration_is_additive
    (left right : Int) :
    qceSerialCalibration.response (left + right) =
      qceSerialCalibration.response left + qceSerialCalibration.response right := by
  exact qceSerialCalibration.composeResponse left right

/-- Explicit interpretation binding from abstract seriality to one measurement axis. -/
structure AxisBinding where
  axis : CalibrationGenerator

/-- Lift the abstract QCE serial response into the MDD calibration interface. -/
def liftSerialCalibration (binding : AxisBinding) : CalibrationAction where
  response generator count :=
    if generator = binding.axis then qceSerialCalibration.response count else 0
  zeroResponse := by
    intro generator
    by_cases sameAxis : generator = binding.axis
    · simp [sameAxis, qceSerialCalibration]
    · simp [sameAxis]
  composeResponse := by
    intro generator left right
    by_cases sameAxis : generator = binding.axis
    · simp [sameAxis, qceSerialCalibration]
    · simp [sameAxis]

/-- [QNS-T12] The selected axis carries the complete abstract serial response. -/
theorem QNS_T12_bound_axis_carries_serial_response
    (binding : AxisBinding) (count : Int) :
    (liftSerialCalibration binding).response binding.axis count =
      qceSerialCalibration.response count := by
  simp [liftSerialCalibration]

/-- [QNS-T13] Every unselected measurement axis has zero serial response. -/
theorem QNS_T13_unbound_axis_has_zero_response
    (binding : AxisBinding)
    (generator : CalibrationGenerator)
    (different : generator ≠ binding.axis)
    (count : Int) :
    (liftSerialCalibration binding).response generator count = 0 := by
  simp [liftSerialCalibration, different]

/-- Bind abstract seriality to the conventional length representation axis. -/
def qceLengthBinding : AxisBinding := ⟨.lengthScale⟩

/-- Bind abstract seriality to the conventional time representation axis. -/
def qceTimeBinding : AxisBinding := ⟨.timeScale⟩

/-- [QNS-T14] A length-axis interpretation yields the MDD length signature. -/
theorem QNS_T14_length_binding_derives_length_dimension :
    derivedDimension (liftSerialCalibration qceLengthBinding) =
      lengthDimension := by
  rfl

/-- [QNS-T15] A time-axis interpretation yields the MDD time signature. -/
theorem QNS_T15_time_binding_derives_time_dimension :
    derivedDimension (liftSerialCalibration qceTimeBinding) =
      timeDimension := by
  rfl

/-- [QNS-T16] The two explicit axis bindings produce distinct dimensions. -/
theorem QNS_T16_length_and_time_bindings_are_dimensionally_distinct :
    derivedDimension (liftSerialCalibration qceLengthBinding) ≠
      derivedDimension (liftSerialCalibration qceTimeBinding) := by
  decide

/--
[QNS-T17] Countermodel to axis selection from seriality alone: two distinct physical
axis bindings carry the same unit serial response.
-/
theorem QNS_T17_seriality_alone_does_not_select_physical_axis :
    ∃ left right : AxisBinding,
      left.axis ≠ right.axis ∧
      (liftSerialCalibration left).response left.axis 1 =
        (liftSerialCalibration right).response right.axis 1 := by
  refine ⟨qceLengthBinding, qceTimeBinding, ?_, ?_⟩
  · decide
  · rfl

/-- A generated now-state together with an explicit measurement-axis interpretation. -/
structure NowCalibrationSystem where
  network : RelationNetwork
  binding : AxisBinding

/-- Change only the measurement interpretation of a QCE now-state. -/
def rebindAxis
    (system : NowCalibrationSystem)
    (binding : AxisBinding) : NowCalibrationSystem :=
  { system with binding := binding }

/-- [QNS-T18] Axis rebinding cannot rewrite the underlying QCE now-state. -/
theorem QNS_T18_axis_rebinding_preserves_qce_network
    (system : NowCalibrationSystem)
    (binding : AxisBinding) :
    (rebindAxis system binding).network = system.network := by
  rfl

end QIKVRT.V2.Physics.QCENowSerialization
