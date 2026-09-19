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

structure BoundSubject where
 repository : String
 head : String
 tree : String
deriving DecidableEq

structure CausalEvent where
 eventId : Nat
 sequence : Nat
 causeEventIds : List Nat
deriving DecidableEq

def causalEdge (a b : CausalEvent) : Prop := a.eventId ∈ b.causeEventIds

theorem sequence_does_not_imply_cause :
    ∃ e1 e2 : CausalEvent, e1.sequence < e2.sequence ∧ ¬ causalEdge e1 e2 := by
  refine ⟨{ eventId := 1, sequence := 1, causeEventIds := [] },
          { eventId := 2, sequence := 2, causeEventIds := [] }, ?_, ?_⟩
  · decide
  · simp [causalEdge]

structure BoundEvidence where
 subject : BoundSubject
 fresh : Bool

def validates (e : BoundEvidence) (s : BoundSubject) : Prop :=
  e.fresh = true ∧ e.subject = s

theorem evidence_non_transfer (e : BoundEvidence) (s0 s1 : BoundSubject)
    (hne : s0 ≠ s1) (h0 : validates e s0) : ¬ validates e s1 := by
  intro h1
  apply hne
  exact h0.2.symm.trans h1.2

structure EffectAckWitness where
 authority : Bool
 committed : Bool
 freshReadback : Bool
 exactSubject : Bool
 expectedMatchesObserved : Bool

def effectAck (w : EffectAckWitness) : Bool :=
  w.authority && w.committed && w.freshReadback && w.exactSubject &&
    w.expectedMatchesObserved

theorem effect_ack_requires_fresh_readback (w : EffectAckWitness)
    (h : effectAck w = true) : w.freshReadback = true := by
  cases hfr : w.freshReadback with
  | false =>
      simp [effectAck, hfr] at h
  | true =>
      rfl

end QIKVRT.TEMDD
