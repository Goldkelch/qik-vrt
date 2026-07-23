import QIKVRTEffectAck.Model

/-!
# Deterministic priority and DONE-only release

These theorems formalize the abstract state selector from Draft-01 Section 4.2
and the consumer-side release boundary from Sections 3 and 4.1.  The result is
symbolic over every `Snapshot`; unlike a finite enumeration, it does not depend
on a fixed list of test inputs.
-/

namespace QIKVRT.EffectAck.V1

def DoneSelectionConditions (snapshot : Snapshot) : Prop :=
  snapshot.predecessorInvalid ≠ true ∧
  snapshot.deadlineExceeded ≠ true ∧
  effectCheckableReception snapshot ≠ false ∧
  snapshot.integrityFailure ≠ true ∧
  snapshot.connectionDecision ≠ .block ∧
  snapshot.connectionDecision ≠ .isolate ∧
  snapshot.connectionDecision = .release ∧
  coreDone snapshot = true

theorem selectState_eq_done_iff (snapshot : Snapshot) :
    selectState snapshot = .done ↔ DoneSelectionConditions snapshot := by
  cases hPredecessor : snapshot.predecessorInvalid <;>
  cases hDeadline : snapshot.deadlineExceeded <;>
  cases hReception : effectCheckableReception snapshot <;>
  cases hIntegrity : snapshot.integrityFailure <;>
  cases hDecision : snapshot.connectionDecision <;>
  cases hCore : coreDone snapshot <;>
  simp [selectState, DoneSelectionConditions, hPredecessor, hDeadline,
    hReception, hIntegrity, hDecision, hCore]

theorem predecessorInvalid_blocks (snapshot : Snapshot)
    (h : snapshot.predecessorInvalid = true) :
    selectState snapshot = .block := by
  simp [selectState, h]

theorem deadlineExceeded_blocks (snapshot : Snapshot)
    (hPredecessor : snapshot.predecessorInvalid ≠ true)
    (hDeadline : snapshot.deadlineExceeded = true) :
    selectState snapshot = .block := by
  simp [selectState, hPredecessor, hDeadline]

theorem missingEffectCheckableReception_nacks (snapshot : Snapshot)
    (hPredecessor : snapshot.predecessorInvalid ≠ true)
    (hDeadline : snapshot.deadlineExceeded ≠ true)
    (hReception : effectCheckableReception snapshot = false) :
    selectState snapshot = .nack := by
  simp [selectState, hPredecessor, hDeadline, hReception]

theorem integrityFailure_blocks (snapshot : Snapshot)
    (hPredecessor : snapshot.predecessorInvalid ≠ true)
    (hDeadline : snapshot.deadlineExceeded ≠ true)
    (hReception : effectCheckableReception snapshot ≠ false)
    (hIntegrity : snapshot.integrityFailure = true) :
    selectState snapshot = .block := by
  simp [selectState, hPredecessor, hDeadline, hReception, hIntegrity]

theorem explicitBlock_precedes_later_outcomes (snapshot : Snapshot)
    (hPredecessor : snapshot.predecessorInvalid ≠ true)
    (hDeadline : snapshot.deadlineExceeded ≠ true)
    (hReception : effectCheckableReception snapshot ≠ false)
    (hIntegrity : snapshot.integrityFailure ≠ true)
    (hBlock : snapshot.connectionDecision = .block) :
    selectState snapshot = .block := by
  simp [selectState, hPredecessor, hDeadline, hReception, hIntegrity, hBlock]

theorem explicitIsolate_precedes_done (snapshot : Snapshot)
    (hPredecessor : snapshot.predecessorInvalid ≠ true)
    (hDeadline : snapshot.deadlineExceeded ≠ true)
    (hReception : effectCheckableReception snapshot ≠ false)
    (hIntegrity : snapshot.integrityFailure ≠ true)
    (hIsolate : snapshot.connectionDecision = .isolate) :
    selectState snapshot = .isolate := by
  simp [selectState, hPredecessor, hDeadline, hReception, hIntegrity,
    hIsolate]

theorem selectedDone_implies_coreDone (snapshot : Snapshot)
    (hDone : selectState snapshot = .done) :
    CoreDoneConditions snapshot := by
  rcases (selectState_eq_done_iff snapshot).1 hDone with
    ⟨_, _, _, _, _, _, _, hCore⟩
  exact (coreDone_eq_true_iff snapshot).1 hCore

theorem selectedDone_implies_releaseDecision (snapshot : Snapshot)
    (hDone : selectState snapshot = .done) :
    snapshot.connectionDecision = .release := by
  rcases (selectState_eq_done_iff snapshot).1 hDone with
    ⟨_, _, _, _, _, _, hRelease, _⟩
  exact hRelease

theorem authorized_implies_recorded_and_recomputed_done
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool)
    (hAuthorized :
      authorizeOrdinaryRelease checks snapshot recordState
        ordinaryReleaseClaim = true) :
    recordState = .done ∧ selectState snapshot = .done := by
  rcases
      (authorizeOrdinaryRelease_eq_true_iff
        checks snapshot recordState ordinaryReleaseClaim).1 hAuthorized with
    ⟨_, hMatches, hRecordedDone, _⟩
  exact ⟨hRecordedDone, hMatches.symm.trans hRecordedDone⟩

theorem authorized_implies_consumer_checks
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool)
    (hAuthorized :
      authorizeOrdinaryRelease checks snapshot recordState
        ordinaryReleaseClaim = true) :
    ConsumerCheckConditions checks := by
  have hAll :=
    ((authorizeOrdinaryRelease_eq_true_iff
      checks snapshot recordState ordinaryReleaseClaim).1 hAuthorized).1
  exact (allConsumerChecks_eq_true_iff checks).1 hAll

theorem nonDone_record_never_authorized
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool)
    (hNotDone : recordState ≠ .done) :
    authorizeOrdinaryRelease checks snapshot recordState
      ordinaryReleaseClaim = false := by
  simp [authorizeOrdinaryRelease, hNotDone]

theorem stale_record_never_authorized
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool)
    (hStale : checks.fresh = false) :
    authorizeOrdinaryRelease checks snapshot recordState
      ordinaryReleaseClaim = false := by
  simp [authorizeOrdinaryRelease, allConsumerChecks, hStale]

def transportAckOnly : Snapshot where
  transportAck := true
  inputIdAvailable := false
  inputHashIsSha256Identifier := false
  predecessorInvalid := false
  deadlineExceeded := false
  integrityFailure := false
  originChecked := false
  contextChecked := false
  semanticsReconstructed := false
  effectAnticipated := false
  riskClassified := false
  riskKnown := false
  responsibilityAssigned := false
  responsibilityOwnerPresent := false
  connectionDecided := false
  policyAllowsRelease := false
  noOpenQuestions := false
  noNextRequiredChecks := false
  requiredEvidenceComplete := false
  connectionDecision := .undecided

theorem transportAck_is_not_effectAuthorization :
    transportAckOnly.transportAck = true ∧
    selectState transportAckOnly = .nack ∧
    authorizeOrdinaryRelease fullyValidConsumerChecks transportAckOnly
      .nack false = false := by
  decide

end QIKVRT.EffectAck.V1
