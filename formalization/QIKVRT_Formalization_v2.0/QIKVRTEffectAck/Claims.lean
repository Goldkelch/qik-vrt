import QIKVRTEffectAck.Mediation
import QIKVRTEffectAck.InformationBoundary

/-!
# Proposition-indexed EFFECT_ACK claim registry

Every registry value contains a kernel proof of its exact proposition.  Claim
identifiers are audit data; they cannot turn an unproved statement into a
checked claim.
-/

namespace QIKVRT.EffectAck.V1.Claims

universe u v w

inductive ClaimId where
  | stateSpace
  | doneSelection
  | releaseSafety
  | completeMediation
  | conditionalPhysicalBridge
  | semanticBoundary
  | inversionBoundary
  | collapsedDecoderCounterexample
deriving DecidableEq, Repr

structure CheckedClaim (id : ClaimId) (statement : Prop) : Type where
  checked : statement

def claimIds : List ClaimId :=
  [.stateSpace, .doneSelection, .releaseSafety, .completeMediation,
    .conditionalPhysicalBridge, .semanticBoundary, .inversionBoundary,
    .collapsedDecoderCounterexample]

theorem claimIds_count : claimIds.length = 8 := by decide

theorem claimIds_pairwise : claimIds.Pairwise (· ≠ ·) := by decide

def StateSpaceStatement : Prop :=
  states.length = 5 ∧ states.Pairwise (· ≠ ·) ∧
  (∀ state, state ∈ states) ∧
  connectionDecisions.length = 5 ∧
  connectionDecisions.Pairwise (· ≠ ·) ∧
  (∀ decision, decision ∈ connectionDecisions)

def StateSpace : CheckedClaim .stateSpace StateSpaceStatement :=
  ⟨states_count, states_pairwise, states_complete,
    connectionDecisions_count, connectionDecisions_pairwise,
    connectionDecisions_complete⟩

def DoneSelection (snapshot : Snapshot) :
    CheckedClaim .doneSelection
      (selectState snapshot = .done ↔ DoneSelectionConditions snapshot) :=
  ⟨selectState_eq_done_iff snapshot⟩

def ReleaseSafetyStatement
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool) : Prop :=
  authorizeOrdinaryRelease checks snapshot recordState ordinaryReleaseClaim =
      true →
    ConsumerCheckConditions checks ∧
    recordState = .done ∧
    selectState snapshot = .done

def ReleaseSafety
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool) :
    CheckedClaim .releaseSafety
      (ReleaseSafetyStatement checks snapshot recordState
        ordinaryReleaseClaim) := by
  refine ⟨?_⟩
  intro hAuthorized
  exact ⟨authorized_implies_consumer_checks
      checks snapshot recordState ordinaryReleaseClaim hAuthorized,
    authorized_implies_recorded_and_recomputed_done
      checks snapshot recordState ordinaryReleaseClaim hAuthorized⟩

def CompleteMediationStatement
    {Effect : Type u}
    (executes : Effect → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool) : Prop :=
  CompletelyMediated executes checks snapshot recordState
      ordinaryReleaseClaim →
    ∀ effect, executes effect →
      recordState effect = .done ∧ selectState (snapshot effect) = .done

def CompleteMediation
    {Effect : Type u}
    (executes : Effect → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool) :
    CheckedClaim .completeMediation
      (CompleteMediationStatement executes checks snapshot recordState
        ordinaryReleaseClaim) :=
  ⟨fun hMediated _ hExecutes =>
    completelyMediated_execution_implies_done
      executes checks snapshot recordState ordinaryReleaseClaim
      hMediated hExecutes⟩

def ConditionalPhysicalBridge
    {Effect : Type u} {PhysicalOccurrence : Type v}
    (executes : Effect → Prop)
    (occurs : PhysicalOccurrence → Prop)
    (causedBy : Effect → PhysicalOccurrence → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool) :
    CheckedClaim .conditionalPhysicalBridge
      (CompletelyMediated executes checks snapshot recordState
          ordinaryReleaseClaim →
       FaithfulPhysicalBridge executes occurs causedBy →
       ∀ occurrence, occurs occurrence →
         ∃ effect,
           causedBy effect occurrence ∧
           recordState effect = .done ∧
           selectState (snapshot effect) = .done) :=
  ⟨fun hMediated hBridge _ hOccurs =>
    physicalOccurrence_implies_authorized_done_conditionally
      executes occurs causedBy checks snapshot recordState
      ordinaryReleaseClaim hMediated hBridge hOccurs⟩

def SemanticBoundary
    {Source : Type u} {Observation : Type v} {Meaning : Type w}
    (observe : Source → Observation) (meaning : Source → Meaning) :
    CheckedClaim .semanticBoundary
      (SemanticReconstructionExists observe meaning ↔
        MeaningConstantOnObservationFibers observe meaning) :=
  ⟨semanticReconstruction_iff_fiberConstant observe meaning⟩

def InversionBoundary
    {Source : Type u} {Observation : Type v}
    (observe : Source → Observation) :
    CheckedClaim .inversionBoundary
      (ExactHistoricalReconstruction observe → Injective observe) :=
  ⟨exactHistoricalReconstruction_implies_injective observe⟩

def CollapsedDecoderCounterexample :
    CheckedClaim .collapsedDecoderCounterexample
      (¬ ExactHistoricalReconstruction collapsedObservation) :=
  ⟨noExactDecoder_forCollapsedObservation⟩

end QIKVRT.EffectAck.V1.Claims
