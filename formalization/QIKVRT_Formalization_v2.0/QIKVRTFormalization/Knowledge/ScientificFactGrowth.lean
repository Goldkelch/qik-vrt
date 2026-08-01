-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import Std

/-!
# Bounded scientific fact growth for QIK-VRT repositories

This module proves structural properties of a finite, content-addressed claim
corpus.  It deliberately does not postulate a universal truth oracle, global
scientific novelty, physical retrocausality, or automatic proof synthesis.
Kernel results apply only to the explicit data structures and assumptions
below.  Empirical premises remain external observations.
-/

namespace QIKVRT.V2.Knowledge

inductive EpistemicClass where
  | formalProved
  | empiricallyEvidenced
  | sourceBound
  | normative
  | interpretative
  | open
deriving DecidableEq, Repr, BEq

inductive ClaimStatus where
  | proved
  | evidenced
  | bound
  | declared
  | open
deriving DecidableEq, Repr, BEq

def Compatible : EpistemicClass → ClaimStatus → Prop
  | .formalProved, .proved => True
  | .empiricallyEvidenced, .evidenced => True
  | .sourceBound, .bound => True
  | .normative, .declared => True
  | .interpretative, .declared => True
  | .open, .open => True
  | _, _ => False

theorem formalProved_requires_proved
    {status : ClaimStatus} (h : Compatible .formalProved status) :
    status = .proved := by
  cases status <;> simp [Compatible] at h ⊢

theorem openClass_requires_openStatus
    {status : ClaimStatus} (h : Compatible .open status) :
    status = .open := by
  cases status <;> simp [Compatible] at h ⊢

structure Claim where
  id : Nat
  statementDigest : Nat
  epistemicClass : EpistemicClass
  status : ClaimStatus
  dependencies : List Nat
  negates : List Nat
deriving DecidableEq, Repr

abbrev Corpus := List Claim

def WellClassified (claim : Claim) : Prop :=
  Compatible claim.epistemicClass claim.status

def Extends (older newer : Corpus) : Prop :=
  ∀ claim, claim ∈ older → claim ∈ newer

def SameClaims (left right : Corpus) : Prop :=
  ∀ claim, claim ∈ left ↔ claim ∈ right

theorem extends_refl (corpus : Corpus) : Extends corpus corpus := by
  intro claim h
  exact h

theorem extends_trans {first second third : Corpus}
    (hFirst : Extends first second) (hSecond : Extends second third) :
    Extends first third := by
  intro claim h
  exact hSecond claim (hFirst claim h)

theorem append_extends (older additions : Corpus) :
    Extends older (older ++ additions) := by
  intro claim h
  exact List.mem_append.mpr (Or.inl h)

def merge (left right : Corpus) : Corpus := left ++ right

theorem merge_commutative_by_membership (left right : Corpus) :
    SameClaims (merge left right) (merge right left) := by
  intro claim
  simp [merge, or_comm]

theorem merge_associative (first second third : Corpus) :
    merge (merge first second) third = merge first (merge second third) := by
  simp [merge, List.append_assoc]

theorem merge_idempotent_by_membership (corpus : Corpus) :
    SameClaims (merge corpus corpus) corpus := by
  intro claim
  simp [merge]

theorem replicas_converge_after_same_updates
    {left right : Corpus} (hSame : SameClaims left right)
    (updates : Corpus) :
    SameClaims (merge left updates) (merge right updates) := by
  intro claim
  simp only [merge, List.mem_append]
  rw [hSame claim]

def HasId (corpus : Corpus) (id : Nat) : Prop :=
  ∃ claim, claim ∈ corpus ∧ claim.id = id

def EvidenceClosed (corpus : Corpus) (claim : Claim) : Prop :=
  ∀ dependency, dependency ∈ claim.dependencies → HasId corpus dependency

theorem hasId_mono {older newer : Corpus} (hExtends : Extends older newer)
    {id : Nat} : HasId older id → HasId newer id := by
  rintro ⟨claim, hMember, hId⟩
  exact ⟨claim, hExtends claim hMember, hId⟩

theorem evidenceClosed_mono {older newer : Corpus}
    (hExtends : Extends older newer) {claim : Claim} :
    EvidenceClosed older claim → EvidenceClosed newer claim := by
  intro hClosed dependency hDependency
  exact hasId_mono hExtends (hClosed dependency hDependency)

def Substantive : ClaimStatus → Prop
  | .open => False
  | _ => True

def Answerable (corpus : Corpus) (queryId : Nat) : Prop :=
  ∃ claim, claim ∈ corpus ∧ claim.id = queryId ∧
    Substantive claim.status ∧ EvidenceClosed corpus claim

theorem answerability_mono {older newer : Corpus}
    (hExtends : Extends older newer) {queryId : Nat} :
    Answerable older queryId → Answerable newer queryId := by
  rintro ⟨claim, hMember, hId, hSubstantive, hClosed⟩
  exact ⟨claim, hExtends claim hMember, hId, hSubstantive,
    evidenceClosed_mono hExtends hClosed⟩

theorem empty_corpus_answers_no_query (queryId : Nat) :
    ¬ Answerable [] queryId := by
  rintro ⟨claim, hMember, _⟩
  simp at hMember

def SyntacticallyNovel (corpus : Corpus) (digest : Nat) : Bool :=
  corpus.all (fun claim => claim.statementDigest != digest)

theorem empty_corpus_marks_every_digest_novel (digest : Nat) :
    SyntacticallyNovel [] digest = true := by
  rfl

theorem adding_digest_makes_it_nonNovel (corpus : Corpus) (claim : Claim) :
    SyntacticallyNovel (claim :: corpus) claim.statementDigest = false := by
  simp [SyntacticallyNovel]

theorem corpus_relative_novelty_is_not_global (claim : Claim) :
    SyntacticallyNovel [] claim.statementDigest = true ∧
    SyntacticallyNovel [claim] claim.statementDigest = false := by
  simp [SyntacticallyNovel]

def ExplicitConflict (left right : Claim) : Prop :=
  right.id ∈ left.negates ∨ left.id ∈ right.negates

def ConflictPresent (corpus : Corpus) : Prop :=
  ∃ left, left ∈ corpus ∧ ∃ right, right ∈ corpus ∧
    ExplicitConflict left right

theorem conflicts_are_preserved_by_extension {older newer : Corpus}
    (hExtends : Extends older newer) :
    ConflictPresent older → ConflictPresent newer := by
  rintro ⟨left, hLeft, right, hRight, hConflict⟩
  exact ⟨left, hExtends left hLeft, right, hExtends right hRight, hConflict⟩

structure ObservationEnvelope where
  acquisitionBound : Bool
  calibrated : Bool
  temporalBinding : Bool
  provenanceBound : Bool
  integrityBound : Bool
  uncertaintyBound : Bool
  falsifiable : Bool
  governanceBound : Bool
deriving DecidableEq, Repr

def qualifiedObservation (observation : ObservationEnvelope) : Bool :=
  observation.acquisitionBound &&
  observation.calibrated &&
  observation.temporalBinding &&
  observation.provenanceBound &&
  observation.integrityBound &&
  observation.uncertaintyBound &&
  observation.falsifiable &&
  observation.governanceBound

def ObservationConditions (observation : ObservationEnvelope) : Prop :=
  observation.acquisitionBound = true ∧
  observation.calibrated = true ∧
  observation.temporalBinding = true ∧
  observation.provenanceBound = true ∧
  observation.integrityBound = true ∧
  observation.uncertaintyBound = true ∧
  observation.falsifiable = true ∧
  observation.governanceBound = true

theorem qualifiedObservation_eq_true_iff
    (observation : ObservationEnvelope) :
    qualifiedObservation observation = true ↔
      ObservationConditions observation := by
  simp [qualifiedObservation, ObservationConditions, and_assoc]

structure CausalEvidence where
  temporalOrderBound : Bool
  interventionOrIdentificationBound : Bool
  alternativesControlled : Bool
  provenanceBound : Bool
  uncertaintyBound : Bool
deriving DecidableEq, Repr

def causallyAttributable (evidence : CausalEvidence) : Bool :=
  evidence.temporalOrderBound &&
  evidence.interventionOrIdentificationBound &&
  evidence.alternativesControlled &&
  evidence.provenanceBound &&
  evidence.uncertaintyBound

theorem causallyAttributable_requires_identification
    (evidence : CausalEvidence) :
    causallyAttributable evidence = true →
      evidence.interventionOrIdentificationBound = true := by
  intro h
  simp [causallyAttributable] at h
  exact h.1.1.1.2

structure MirrorView where
  trace : List Nat
  physicalCausation : Bool
deriving DecidableEq, Repr

def traceOnly : MirrorView where
  trace := [1, 2, 3]
  physicalCausation := false

def traceWithCausalAttribution : MirrorView where
  trace := [1, 2, 3]
  physicalCausation := true

theorem identical_trace_does_not_determine_physical_causation :
    traceOnly.trace = traceWithCausalAttribution.trace ∧
    traceOnly.physicalCausation ≠
      traceWithCausalAttribution.physicalCausation := by
  decide

structure TwinTransition where
  observation : ObservationEnvelope
  modelVersionBound : Bool
  stateTransitionBound : Bool
  policyPassed : Bool
  effectAckDone : Bool
deriving DecidableEq, Repr

def twinActuationReady (transition : TwinTransition) : Bool :=
  qualifiedObservation transition.observation &&
  transition.modelVersionBound &&
  transition.stateTransitionBound &&
  transition.policyPassed &&
  transition.effectAckDone

theorem twinActuation_requires_qualifiedObservation
    (transition : TwinTransition) :
    twinActuationReady transition = true →
      qualifiedObservation transition.observation = true := by
  intro h
  simp [twinActuationReady] at h
  exact h.1.1.1.1

theorem twinActuation_requires_effectAck (transition : TwinTransition) :
    twinActuationReady transition = true →
      transition.effectAckDone = true := by
  intro h
  simp [twinActuationReady] at h
  exact h.2

def singletonSegments : List α → List (List α)
  | [] => []
  | symbol :: rest => [symbol] :: singletonSegments rest

theorem flatten_singletonSegments (message : List α) :
    (singletonSegments message).flatten = message := by
  induction message with
  | nil => rfl
  | cons symbol rest inductionHypothesis =>
      simp [singletonSegments, inductionHypothesis]

def Prefix (older newer : List α) : Prop :=
  ∃ suffix, newer = older ++ suffix

theorem append_preserves_prefix (older suffix : List α) :
    Prefix older (older ++ suffix) := by
  exact ⟨suffix, rfl⟩

theorem prefix_trans {first second third : List α}
    (hFirst : Prefix first second) (hSecond : Prefix second third) :
    Prefix first third := by
  rcases hFirst with ⟨middleSuffix, rfl⟩
  rcases hSecond with ⟨lastSuffix, rfl⟩
  exact ⟨middleSuffix ++ lastSuffix, by simp [List.append_assoc]⟩

inductive IntakeState where
  | proposed
  | heldOpen
  | classified
  | contested
  | rejected
deriving DecidableEq, Repr, BEq

structure IntakeDecision where
  state : IntakeState
  effectAckDone : Bool
deriving DecidableEq, Repr

def proposalOnly (state : IntakeState) : IntakeDecision where
  state := state
  effectAckDone := false

theorem proposalOnly_never_authorizes_effect (state : IntakeState) :
    (proposalOnly state).effectAckDone = false := by
  rfl

#print axioms formalProved_requires_proved
#print axioms openClass_requires_openStatus
#print axioms append_extends
#print axioms merge_commutative_by_membership
#print axioms merge_associative
#print axioms merge_idempotent_by_membership
#print axioms replicas_converge_after_same_updates
#print axioms evidenceClosed_mono
#print axioms answerability_mono
#print axioms empty_corpus_answers_no_query
#print axioms corpus_relative_novelty_is_not_global
#print axioms conflicts_are_preserved_by_extension
#print axioms qualifiedObservation_eq_true_iff
#print axioms causallyAttributable_requires_identification
#print axioms identical_trace_does_not_determine_physical_causation
#print axioms twinActuation_requires_qualifiedObservation
#print axioms twinActuation_requires_effectAck
#print axioms flatten_singletonSegments
#print axioms append_preserves_prefix
#print axioms prefix_trans
#print axioms proposalOnly_never_authorizes_effect

end QIKVRT.V2.Knowledge
