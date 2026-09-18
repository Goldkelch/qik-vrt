namespace QIKVRT.TEMDD
inductive State where | hold | continue | successorRequired | done deriving DecidableEq
inductive Event where | unknown | evidence | blocker deriving DecidableEq
def transition : State -> Event -> State
| State.done, _ => State.done
| _, Event.blocker => State.successorRequired
| _, Event.evidence => State.continue
| _, Event.unknown => State.hold
structure DoD where
 zeroBugs : Bool
 allPullRequestsRegarded : Bool
 allBranchesRegarded : Bool
 allProductiveBranchesMerged : Bool
 freshExactMainValidationPass : Bool
 freshEffectReadback : Bool
def complete (d : DoD) : Bool := d.zeroBugs && d.allPullRequestsRegarded && d.allBranchesRegarded && d.allProductiveBranchesMerged && d.freshExactMainValidationPass && d.freshEffectReadback
theorem blocker_requires_successor (s : State) (h : s != State.done) : transition s Event.blocker = State.successorRequired := by cases s <;> simp [transition] at h ⊢
theorem missing_effect_readback_not_done (d : DoD) (h : d.freshEffectReadback = false) : complete d = false := by simp [complete, h]

structure ExactSubject where
  repository : String
  head : String
  tree : String
  deriving DecidableEq, Repr

structure RuntimeEvent where
  eventId : String
  sequence : Nat
  causeEventIds : List String
  deriving DecidableEq, Repr

def Causes (cause effect : RuntimeEvent) : Prop :=
  cause.eventId ∈ effect.causeEventIds

theorem sequence_does_not_imply_cause
    (cause effect : RuntimeEvent)
    (_ordered : cause.sequence < effect.sequence)
    (notDeclared : cause.eventId ∉ effect.causeEventIds) :
    ¬ Causes cause effect := by
  simpa [Causes] using notDeclared

structure BoundEvidence where
  subject : ExactSubject
  fresh : Bool
  deriving Repr

def EvidenceApplies (evidence : BoundEvidence) (subject : ExactSubject) : Prop :=
  evidence.subject = subject ∧ evidence.fresh = true

theorem evidence_non_transfer
    (evidence : BoundEvidence)
    (source successor : ExactSubject)
    (bound : evidence.subject = source)
    (changed : source ≠ successor) :
    ¬ EvidenceApplies evidence successor := by
  intro applies
  apply changed
  calc
    source = evidence.subject := bound.symm
    _ = successor := applies.1

structure EffectWitness where
  authority : Bool
  committed : Bool
  freshReadback : Bool
  exactSubject : Bool
  expectedMatchesObserved : Bool
  deriving DecidableEq, Repr

def effectAck (witness : EffectWitness) : Bool :=
  witness.authority &&
  witness.committed &&
  witness.freshReadback &&
  witness.exactSubject &&
  witness.expectedMatchesObserved

theorem effect_ack_requires_fresh_readback
    (witness : EffectWitness)
    (missing : witness.freshReadback = false) :
    effectAck witness = false := by
  simp [effectAck, missing]

end QIKVRT.TEMDD
