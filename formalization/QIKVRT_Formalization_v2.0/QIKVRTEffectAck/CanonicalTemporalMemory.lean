-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import Std

/-!
# QIK-VRT canonical temporal memory and operational retrocausality

This file formalizes the finite Boolean release core used by the article
"QIK-VRT und das Effect-Acknowledgement-Protokoll: Kanonischer Speicher
zwischen Vergangenheit und Zukunft".

The word `future` denotes a present, canonical representation of an
anticipated or required later effect.  The model proves that this
future-indexed boundary is a non-eliminable input to the present release
decision.  It does not assume an observation arriving from the physical
future, a changed past, backward signalling, quantum mechanics, consciousness,
or panpsychism.
-/

namespace QIKVRT.CanonicalTemporalMemory.V1

inductive TemporalStatus where
  | observed
  | anticipated
deriving DecidableEq, Repr

structure CanonicalArchive where
  status : TemporalStatus
  payloadBound : Bool
  provenanceBound : Bool
  canonicalEncoding : Bool
deriving DecidableEq, Repr

structure ProspectiveRelease where
  causeId : Nat
  anticipatedEffectId : Nat
  pastArchive : CanonicalArchive
  futureArchive : CanonicalArchive
  causeBound : Bool
  policyPassed : Bool
  effectAckDone : Bool
deriving Repr

def pastValid (snapshot : ProspectiveRelease) : Bool :=
  snapshot.pastArchive.status == .observed &&
  snapshot.pastArchive.payloadBound &&
  snapshot.pastArchive.provenanceBound &&
  snapshot.pastArchive.canonicalEncoding

def futureValid (snapshot : ProspectiveRelease) : Bool :=
  snapshot.futureArchive.status == .anticipated &&
  snapshot.futureArchive.payloadBound &&
  snapshot.futureArchive.provenanceBound &&
  snapshot.futureArchive.canonicalEncoding

def release (snapshot : ProspectiveRelease) : Bool :=
  pastValid snapshot &&
  futureValid snapshot &&
  snapshot.causeBound &&
  snapshot.policyPassed &&
  snapshot.effectAckDone

def ReleaseConditions (snapshot : ProspectiveRelease) : Prop :=
  pastValid snapshot = true ∧
  futureValid snapshot = true ∧
  snapshot.causeBound = true ∧
  snapshot.policyPassed = true ∧
  snapshot.effectAckDone = true

theorem release_eq_true_iff (snapshot : ProspectiveRelease) :
    release snapshot = true ↔ ReleaseConditions snapshot := by
  simp [release, ReleaseConditions, and_assoc]

theorem release_requires_valid_past (snapshot : ProspectiveRelease) :
    release snapshot = true → pastValid snapshot = true := by
  intro h
  exact (release_eq_true_iff snapshot).mp h |>.1

theorem release_requires_valid_future (snapshot : ProspectiveRelease) :
    release snapshot = true → futureValid snapshot = true := by
  intro h
  exact (release_eq_true_iff snapshot).mp h |>.2.1

theorem release_requires_effect_ack (snapshot : ProspectiveRelease) :
    release snapshot = true → snapshot.effectAckDone = true := by
  intro h
  exact (release_eq_true_iff snapshot).mp h |>.2.2.2.2

def validPast : CanonicalArchive where
  status := .observed
  payloadBound := true
  provenanceBound := true
  canonicalEncoding := true

def validFuture : CanonicalArchive where
  status := .anticipated
  payloadBound := true
  provenanceBound := true
  canonicalEncoding := true

def invalidFuture : CanonicalArchive where
  status := .anticipated
  payloadBound := false
  provenanceBound := true
  canonicalEncoding := true

def admittedCandidate : ProspectiveRelease where
  causeId := 7
  anticipatedEffectId := 11
  pastArchive := validPast
  futureArchive := validFuture
  causeBound := true
  policyPassed := true
  effectAckDone := true

def futureRejectedCandidate : ProspectiveRelease where
  causeId := 7
  anticipatedEffectId := 11
  pastArchive := validPast
  futureArchive := invalidFuture
  causeBound := true
  policyPassed := true
  effectAckDone := true

theorem future_boundary_is_counterfactually_relevant :
    admittedCandidate.causeId = futureRejectedCandidate.causeId ∧
    admittedCandidate.anticipatedEffectId =
      futureRejectedCandidate.anticipatedEffectId ∧
    admittedCandidate.pastArchive = futureRejectedCandidate.pastArchive ∧
    admittedCandidate.causeBound = futureRejectedCandidate.causeBound ∧
    admittedCandidate.policyPassed = futureRejectedCandidate.policyPassed ∧
    admittedCandidate.effectAckDone = futureRejectedCandidate.effectAckDone ∧
    release admittedCandidate = true ∧
    release futureRejectedCandidate = false := by
  decide

def pastProjection
    (past : CanonicalArchive)
    (_future : CanonicalArchive) : CanonicalArchive :=
  past

theorem future_boundary_does_not_overwrite_past
    (past : CanonicalArchive)
    (leftFuture rightFuture : CanonicalArchive) :
    pastProjection past leftFuture = pastProjection past rightFuture := by
  rfl

structure EffectReceipt where
  causeId : Nat
  observedEffectId : Nat
  effectObserved : Bool
  receiptBound : Bool
deriving Repr

def identifierBound
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) : Bool :=
  prospective.causeId == receipt.causeId &&
  prospective.anticipatedEffectId == receipt.observedEffectId

theorem identifier_bound_eq_true_iff
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) :
    identifierBound prospective receipt = true ↔
      prospective.causeId = receipt.causeId ∧
      prospective.anticipatedEffectId = receipt.observedEffectId := by
  simp [identifierBound]

def reciprocalClosure
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) : Bool :=
  release prospective &&
  identifierBound prospective receipt &&
  receipt.effectObserved &&
  receipt.receiptBound

def ReciprocalConditions
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) : Prop :=
  release prospective = true ∧
  identifierBound prospective receipt = true ∧
  receipt.effectObserved = true ∧
  receipt.receiptBound = true

theorem reciprocal_closure_eq_true_iff
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) :
    reciprocalClosure prospective receipt = true ↔
      ReciprocalConditions prospective receipt := by
  simp [reciprocalClosure, ReciprocalConditions, and_assoc]

theorem reciprocal_closure_requires_cause_and_effect
    (prospective : ProspectiveRelease)
    (receipt : EffectReceipt) :
    reciprocalClosure prospective receipt = true →
      prospective.causeBound = true ∧
      futureValid prospective = true ∧
      prospective.causeId = receipt.causeId ∧
      prospective.anticipatedEffectId = receipt.observedEffectId ∧
      receipt.effectObserved = true := by
  intro h
  have conditions := (reciprocal_closure_eq_true_iff prospective receipt).mp h
  have released := conditions.1
  have releaseConditions := (release_eq_true_iff prospective).mp released
  have identifiers :=
    (identifier_bound_eq_true_iff prospective receipt).mp conditions.2.1
  exact
    ⟨releaseConditions.2.2.1,
      releaseConditions.2.1,
      identifiers.1,
      identifiers.2,
      conditions.2.2.1⟩

end QIKVRT.CanonicalTemporalMemory.V1
