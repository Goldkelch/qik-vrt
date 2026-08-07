import Std
import QCENowSerialization

/-!
# CAS-004: QCE causal-evidence axis selection

This module advances the QCE serialization chain without identifying an abstract
serial coordinate with a physical axis by declaration.

A causal-axis evidence object assigns each measurement-calibration generator an
additive signed trace together with two independent classification bits:
preservation of the causal/null boundary and discrimination of past from future.
An axis qualifies only when its complete signed trace equals the canonical QCE
serial response and both causal-classification bits are present.

A certificate is admissible only when exactly one generator qualifies. The module
proves the positive uniqueness case and the two fail-closed cases: no qualifying
axis and more than one qualifying axis. It also gives an explicit countermodel in
which the same QCE mechanism is paired with resolved and ambiguous axis evidence.
Therefore the QCE mechanism alone still does not establish a physical axis.

Scientific boundary: this is a finite model-theoretic evidence-sufficiency theorem.
The canonical temporal evidence below is an explicit witness model, not an empirical
identification of physical time. The module does not derive the SI second or metre,
the measured value of c, hbar, G, an Einstein limit, universal stress-energy
coupling, physical correspondence, or empirical confirmation.
-/

namespace QIKVRT.V2.Physics.QCECausalAxisSelection

open QIKVRT.VRTCore.QCE
open QIKVRT.V2.Physics.MeasurementDerivedDimensions
open QIKVRT.V2.Physics.QCENowSerialization

/-- One additive signed trace together with independent causal-classification bits. -/
structure AxisCausalTrace where
  response : Int → Int
  zeroResponse : response 0 = 0
  composeResponse : ∀ left right,
    response (left + right) = response left + response right
  preservesNullBoundary : Bool
  distinguishesPastFuture : Bool

/-- Evidence supplies one causal trace for every calibration generator. -/
structure CausalAxisEvidence where
  trace : CalibrationGenerator → AxisCausalTrace

/--
A generator qualifies only if its complete signed response equals the canonical QCE
serial response and it carries both causal-classification witnesses.
-/
def TracksQCESerial
    (evidence : CausalAxisEvidence)
    (generator : CalibrationGenerator) : Prop :=
  (∀ count,
      (evidence.trace generator).response count =
        qceSerialCalibration.response count) ∧
    (evidence.trace generator).preservesNullBoundary = true ∧
    (evidence.trace generator).distinguishesPastFuture = true

/-- Identity signed trace with both causal-classification witnesses present. -/
def serialCausalTrace : AxisCausalTrace where
  response count := count
  zeroResponse := rfl
  composeResponse := by
    intro left right
    rfl
  preservesNullBoundary := true
  distinguishesPastFuture := true

/-- Inert trace carrying no causal-axis classification. -/
def inertCausalTrace : AxisCausalTrace where
  response _count := 0
  zeroResponse := rfl
  composeResponse := by
    intro left right
    rfl
  preservesNullBoundary := false
  distinguishesPastFuture := false

/--
Explicit resolved witness model: only the conventional time generator carries the
complete QCE serial trace plus both causal-classification witnesses.
-/
def canonicalTemporalEvidence : CausalAxisEvidence where
  trace generator :=
    match generator with
    | .timeScale => serialCausalTrace
    | _ => inertCausalTrace

/-- [CAS-T01] The time generator qualifies in the resolved witness model. -/
theorem CAS_T01_canonical_time_axis_tracks_qce_seriality :
    TracksQCESerial canonicalTemporalEvidence .timeScale := by
  constructor
  · intro count
    rfl
  · exact ⟨rfl, rfl⟩

/-- [CAS-T02] Every qualifying generator in the resolved model is the time axis. -/
theorem CAS_T02_canonical_tracking_axis_is_unique
    (generator : CalibrationGenerator)
    (tracks : TracksQCESerial canonicalTemporalEvidence generator) :
    generator = .timeScale := by
  cases generator <;>
    simp [TracksQCESerial, canonicalTemporalEvidence, serialCausalTrace,
      inertCausalTrace, qceSerialCalibration] at tracks ⊢

/--
A certificate is valid only when its axis qualifies and every other qualifying
candidate is propositionally equal to that axis.
-/
structure CausalAxisCertificate (evidence : CausalAxisEvidence) where
  axis : CalibrationGenerator
  tracks : TracksQCESerial evidence axis
  unique : ∀ candidate,
    TracksQCESerial evidence candidate → candidate = axis

/-- Canonical certificate for the explicit resolved witness model. -/
def canonicalTemporalCertificate :
    CausalAxisCertificate canonicalTemporalEvidence where
  axis := .timeScale
  tracks := CAS_T01_canonical_time_axis_tracks_qce_seriality
  unique := by
    intro candidate candidateTracks
    exact CAS_T02_canonical_tracking_axis_is_unique candidate candidateTracks

/-- [CAS-T03] The resolved witness model admits a causal-axis certificate. -/
theorem CAS_T03_canonical_evidence_is_resolvable :
    Nonempty (CausalAxisCertificate canonicalTemporalEvidence) := by
  exact ⟨canonicalTemporalCertificate⟩

/-- [CAS-T04] Two valid certificates over identical evidence select the same axis. -/
theorem CAS_T04_certificates_over_same_evidence_agree
    {evidence : CausalAxisEvidence}
    (left right : CausalAxisCertificate evidence) :
    left.axis = right.axis := by
  exact (left.unique right.axis right.tracks).symm

/-- Convert a valid causal-axis certificate into the QNS axis-binding interface. -/
def certifiedBinding
    {evidence : CausalAxisEvidence}
    (certificate : CausalAxisCertificate evidence) : AxisBinding :=
  ⟨certificate.axis⟩

/-- [CAS-T05] A certified binding carries the complete canonical QCE serial response. -/
theorem CAS_T05_certified_binding_carries_qce_serial_response
    {evidence : CausalAxisEvidence}
    (certificate : CausalAxisCertificate evidence)
    (count : Int) :
    (liftSerialCalibration (certifiedBinding certificate)).response
        certificate.axis count =
      qceSerialCalibration.response count := by
  simpa [certifiedBinding] using
    QNS_T12_bound_axis_carries_serial_response
      (certifiedBinding certificate) count

/-- [CAS-T06] The explicit resolved witness derives the MDD time signature. -/
theorem CAS_T06_canonical_certificate_derives_time_dimension :
    derivedDimension
        (liftSerialCalibration
          (certifiedBinding canonicalTemporalCertificate)) =
      timeDimension := by
  rfl

/-- Evidence ambiguity means that two distinct generators both qualify. -/
def AmbiguousEvidence (evidence : CausalAxisEvidence) : Prop :=
  ∃ left right : CalibrationGenerator,
    left ≠ right ∧
      TracksQCESerial evidence left ∧
      TracksQCESerial evidence right

/-- Two-axis countermodel: both length and time carry the same causal serial trace. -/
def ambiguousLengthTimeEvidence : CausalAxisEvidence where
  trace generator :=
    match generator with
    | .lengthScale => serialCausalTrace
    | .timeScale => serialCausalTrace
    | _ => inertCausalTrace

/-- [CAS-T07] Length qualifies in the explicit ambiguous countermodel. -/
theorem CAS_T07_ambiguous_length_axis_tracks_qce_seriality :
    TracksQCESerial ambiguousLengthTimeEvidence .lengthScale := by
  constructor
  · intro count
    rfl
  · exact ⟨rfl, rfl⟩

/-- [CAS-T08] Time also qualifies in the explicit ambiguous countermodel. -/
theorem CAS_T08_ambiguous_time_axis_tracks_qce_seriality :
    TracksQCESerial ambiguousLengthTimeEvidence .timeScale := by
  constructor
  · intro count
    rfl
  · exact ⟨rfl, rfl⟩

/-- [CAS-T09] The length/time countermodel is genuinely ambiguous. -/
theorem CAS_T09_length_time_evidence_is_ambiguous :
    AmbiguousEvidence ambiguousLengthTimeEvidence := by
  refine ⟨.lengthScale, .timeScale, ?_, ?_, ?_⟩
  · decide
  · exact CAS_T07_ambiguous_length_axis_tracks_qce_seriality
  · exact CAS_T08_ambiguous_time_axis_tracks_qce_seriality

/-- [CAS-T10] Ambiguous evidence cannot authorize any unique axis certificate. -/
theorem CAS_T10_ambiguous_evidence_fails_closed
    {evidence : CausalAxisEvidence}
    (ambiguous : AmbiguousEvidence evidence) :
    ¬ Nonempty (CausalAxisCertificate evidence) := by
  intro certificateExists
  rcases certificateExists with ⟨certificate⟩
  rcases ambiguous with ⟨left, right, different, leftTracks, rightTracks⟩
  have leftEquals : left = certificate.axis :=
    certificate.unique left leftTracks
  have rightEquals : right = certificate.axis :=
    certificate.unique right rightTracks
  apply different
  exact leftEquals.trans rightEquals.symm

/-- No-axis countermodel: no generator carries causal-axis evidence. -/
def absentAxisEvidence : CausalAxisEvidence where
  trace _generator := inertCausalTrace

/-- [CAS-T11] No generator qualifies in the absent-evidence model. -/
theorem CAS_T11_absent_evidence_has_no_candidate
    (generator : CalibrationGenerator) :
    ¬ TracksQCESerial absentAxisEvidence generator := by
  cases generator <;>
    simp [TracksQCESerial, absentAxisEvidence, inertCausalTrace,
      qceSerialCalibration]

/-- [CAS-T12] Absence of a qualifying generator also fails closed. -/
theorem CAS_T12_absent_evidence_fails_closed :
    ¬ Nonempty (CausalAxisCertificate absentAxisEvidence) := by
  intro certificateExists
  rcases certificateExists with ⟨certificate⟩
  exact
    (CAS_T11_absent_evidence_has_no_candidate certificate.axis)
      certificate.tracks

/-- Couple the existing QCE mechanism to independently supplied axis evidence. -/
structure AxisExtendedQCE where
  network : RelationNetwork
  evidence : CausalAxisEvidence

/-- Forget the evidence extension and retain exactly the underlying QCE network. -/
def forgetAxisEvidence (system : AxisExtendedQCE) : RelationNetwork :=
  system.network

/-- Resolved and ambiguous evidence extensions of the identical canonical QCE now-state. -/
def resolvedCurrentQCE : AxisExtendedQCE :=
  ⟨canonicalNow 0, canonicalTemporalEvidence⟩

def ambiguousCurrentQCE : AxisExtendedQCE :=
  ⟨canonicalNow 0, ambiguousLengthTimeEvidence⟩

/--
[CAS-T13] The same QCE now-state admits both a resolvable and an ambiguous evidence
extension. Thus the serialized network alone still cannot select a physical axis.
-/
theorem CAS_T13_same_qce_network_allows_resolved_and_ambiguous_evidence :
    forgetAxisEvidence resolvedCurrentQCE =
        forgetAxisEvidence ambiguousCurrentQCE ∧
      Nonempty
        (CausalAxisCertificate resolvedCurrentQCE.evidence) ∧
      AmbiguousEvidence ambiguousCurrentQCE.evidence := by
  exact
    ⟨rfl, CAS_T03_canonical_evidence_is_resolvable,
      CAS_T09_length_time_evidence_is_ambiguous⟩

/-- Replace only the evidence extension of a QCE system. -/
def replaceAxisEvidence
    (system : AxisExtendedQCE)
    (evidence : CausalAxisEvidence) : AxisExtendedQCE :=
  { system with evidence := evidence }

/-- [CAS-T14] Updating axis evidence cannot rewrite the underlying QCE mechanism. -/
theorem CAS_T14_evidence_replacement_preserves_qce_network
    (system : AxisExtendedQCE)
    (evidence : CausalAxisEvidence) :
    forgetAxisEvidence (replaceAxisEvidence system evidence) =
      forgetAxisEvidence system := by
  rfl

/--
[CAS-T15] The present QCE cone candidate still lacks an admissible null boundary.
-/
theorem CAS_T15_current_qce_cone_candidate_remains_open :
    classicalConeAdmissible currentConeCandidate = false := by
  exact currentConeCandidate_is_not_admissible

/-- [CAS-T16] The current QCE physical candidate still marks correspondence as open. -/
theorem CAS_T16_current_qce_empirical_correspondence_remains_open :
    currentQCECandidate.empiricalCorrespondence = false := by
  rfl

end QIKVRT.V2.Physics.QCECausalAxisSelection
