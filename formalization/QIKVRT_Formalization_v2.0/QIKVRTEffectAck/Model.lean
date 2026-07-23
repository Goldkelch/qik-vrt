import Std

/-!
# EFFECT_ACK version-1 abstract model

The field abstraction and priority order are bound externally to
`draft-lohmann-qikvrt-effect-ack-01`, Sections 4.1 and 4.2.  The model is
deliberately smaller than the full 35-field wire record: it represents the
decision-relevant predicates, not a parser, canonical JSON encoder,
authentication scheme or deployment.
-/

namespace QIKVRT.EffectAck.V1

inductive State where
  | nack
  | continue
  | done
  | isolate
  | block
deriving DecidableEq, Repr

inductive ConnectionDecision where
  | undecided
  | continue
  | release
  | isolate
  | block
deriving DecidableEq, Repr

def states : List State :=
  [.nack, .continue, .done, .isolate, .block]

def connectionDecisions : List ConnectionDecision :=
  [.undecided, .continue, .release, .isolate, .block]

theorem states_count : states.length = 5 := by decide

theorem states_pairwise : states.Pairwise (· ≠ ·) := by decide

theorem states_complete (state : State) : state ∈ states := by
  cases state <;> decide

theorem connectionDecisions_count : connectionDecisions.length = 5 := by
  decide

theorem connectionDecisions_pairwise :
    connectionDecisions.Pairwise (· ≠ ·) := by
  decide

theorem connectionDecisions_complete (decision : ConnectionDecision) :
    decision ∈ connectionDecisions := by
  cases decision <;> decide

structure Snapshot where
  transportAck : Bool
  inputIdAvailable : Bool
  inputHashIsSha256Identifier : Bool
  predecessorInvalid : Bool
  deadlineExceeded : Bool
  integrityFailure : Bool
  originChecked : Bool
  contextChecked : Bool
  semanticsReconstructed : Bool
  effectAnticipated : Bool
  riskClassified : Bool
  riskKnown : Bool
  responsibilityAssigned : Bool
  responsibilityOwnerPresent : Bool
  connectionDecided : Bool
  policyAllowsRelease : Bool
  noOpenQuestions : Bool
  noNextRequiredChecks : Bool
  requiredEvidenceComplete : Bool
  connectionDecision : ConnectionDecision
deriving Repr

/--
Draft-01 defines effect-checkable reception as availability of an input
identifier and digest at the gate.  In this abstraction the digest-availability
predicate is represented by a syntactically valid SHA-256 identifier.  This
does not assert that the digest was independently recomputed over input bytes;
that stronger binding remains a consumer check.
-/
def effectCheckableReception (snapshot : Snapshot) : Bool :=
  snapshot.inputIdAvailable && snapshot.inputHashIsSha256Identifier

def coreDone (snapshot : Snapshot) : Bool :=
  snapshot.transportAck &&
  snapshot.inputHashIsSha256Identifier &&
  snapshot.originChecked &&
  snapshot.contextChecked &&
  snapshot.semanticsReconstructed &&
  snapshot.effectAnticipated &&
  snapshot.riskClassified &&
  snapshot.riskKnown &&
  snapshot.responsibilityAssigned &&
  snapshot.responsibilityOwnerPresent &&
  snapshot.connectionDecided &&
  decide (snapshot.connectionDecision = .release) &&
  snapshot.policyAllowsRelease &&
  (!snapshot.deadlineExceeded) &&
  snapshot.noOpenQuestions &&
  snapshot.noNextRequiredChecks &&
  snapshot.requiredEvidenceComplete

def CoreDoneConditions (snapshot : Snapshot) : Prop :=
  snapshot.transportAck = true ∧
  snapshot.inputHashIsSha256Identifier = true ∧
  snapshot.originChecked = true ∧
  snapshot.contextChecked = true ∧
  snapshot.semanticsReconstructed = true ∧
  snapshot.effectAnticipated = true ∧
  snapshot.riskClassified = true ∧
  snapshot.riskKnown = true ∧
  snapshot.responsibilityAssigned = true ∧
  snapshot.responsibilityOwnerPresent = true ∧
  snapshot.connectionDecided = true ∧
  snapshot.connectionDecision = .release ∧
  snapshot.policyAllowsRelease = true ∧
  snapshot.deadlineExceeded = false ∧
  snapshot.noOpenQuestions = true ∧
  snapshot.noNextRequiredChecks = true ∧
  snapshot.requiredEvidenceComplete = true

theorem coreDone_eq_true_iff (snapshot : Snapshot) :
    coreDone snapshot = true ↔ CoreDoneConditions snapshot := by
  simp [coreDone, CoreDoneConditions, and_assoc]

def selectState (snapshot : Snapshot) : State :=
  if snapshot.predecessorInvalid = true then .block
  else if snapshot.deadlineExceeded = true then .block
  else if effectCheckableReception snapshot = false then .nack
  else if snapshot.integrityFailure = true then .block
  else if snapshot.connectionDecision = .block then .block
  else if snapshot.connectionDecision = .isolate then .isolate
  else if snapshot.connectionDecision = .release ∧
      coreDone snapshot = true then .done
  else .continue

structure ConsumerChecks where
  wireVersionSupported : Bool
  schemaValid : Bool
  authenticated : Bool
  inputBindingValid : Bool
  policyBindingValid : Bool
  evidenceBindingValid : Bool
  chainValid : Bool
  fresh : Bool
deriving Repr

def allConsumerChecks (checks : ConsumerChecks) : Bool :=
  checks.wireVersionSupported &&
  checks.schemaValid &&
  checks.authenticated &&
  checks.inputBindingValid &&
  checks.policyBindingValid &&
  checks.evidenceBindingValid &&
  checks.chainValid &&
  checks.fresh

def ConsumerCheckConditions (checks : ConsumerChecks) : Prop :=
  checks.wireVersionSupported = true ∧
  checks.schemaValid = true ∧
  checks.authenticated = true ∧
  checks.inputBindingValid = true ∧
  checks.policyBindingValid = true ∧
  checks.evidenceBindingValid = true ∧
  checks.chainValid = true ∧
  checks.fresh = true

theorem allConsumerChecks_eq_true_iff (checks : ConsumerChecks) :
    allConsumerChecks checks = true ↔ ConsumerCheckConditions checks := by
  simp [allConsumerChecks, ConsumerCheckConditions, and_assoc]

def authorizeOrdinaryRelease
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool) : Bool :=
  allConsumerChecks checks &&
  decide (recordState = selectState snapshot) &&
  decide (recordState = .done) &&
  ordinaryReleaseClaim

def AuthorizationConditions
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool) : Prop :=
  allConsumerChecks checks = true ∧
  recordState = selectState snapshot ∧
  recordState = .done ∧
  ordinaryReleaseClaim = true

theorem authorizeOrdinaryRelease_eq_true_iff
    (checks : ConsumerChecks)
    (snapshot : Snapshot)
    (recordState : State)
    (ordinaryReleaseClaim : Bool) :
    authorizeOrdinaryRelease checks snapshot recordState ordinaryReleaseClaim =
      true ↔
    AuthorizationConditions checks snapshot recordState ordinaryReleaseClaim := by
  simp [authorizeOrdinaryRelease, AuthorizationConditions, and_assoc]

def fullyValidConsumerChecks : ConsumerChecks where
  wireVersionSupported := true
  schemaValid := true
  authenticated := true
  inputBindingValid := true
  policyBindingValid := true
  evidenceBindingValid := true
  chainValid := true
  fresh := true

end QIKVRT.EffectAck.V1
