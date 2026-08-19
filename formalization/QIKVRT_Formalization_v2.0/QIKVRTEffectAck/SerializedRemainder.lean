import Std

/-!
# EFFECT_ACK live serialization and complementary remainder

This module proves properties of an abstract, typed serialization frame.  It
is not a proof of JSON parsing, HTTP transport, authentication, GitHub state,
or an external repository effect.  Those boundaries remain adapter and
evidence obligations.

The wire sequence is retained as transport metadata.  Causal authority is
carried only by the explicit transaction, observation and predecessor
references.  Therefore `CAUSALITY != SEQUENCE` is represented directly in the
model.
-/

namespace QIKVRT.EffectAck.Live.V1

inductive EffectState where
  | requestReceived
  | authorizationChecked
  | workStarted
  | effectAckContinue
  | block
  | stall
  | completionCandidate
  | pairAcknowledged
deriving DecidableEq, Repr

inductive GateState where
  | pending
  | running
  | success
  | failure
  | actionRequired
  | cancelled
  | skipped
  | notApplicable
deriving DecidableEq, Repr

structure NodeBinding where
  repository : String
  head : String
  tree : String
deriving DecidableEq, Repr

structure CausalReference where
  transactionId : String
  observationId : String
  predecessorId : Option String
deriving DecidableEq, Repr

structure ClosureInventory where
  requirements : List String
  closedVerified : List String
deriving DecidableEq, Repr

/-- The order-preserving complement of verified closure within requirements. -/
def activeRemainder (inventory : ClosureInventory) : List String :=
  inventory.requirements.filter fun requirement =>
    decide (requirement ∉ inventory.closedVerified)

theorem mem_activeRemainder_iff
    (inventory : ClosureInventory) (requirement : String) :
    requirement ∈ activeRemainder inventory ↔
      requirement ∈ inventory.requirements ∧
      requirement ∉ inventory.closedVerified := by
  simp [activeRemainder]

theorem activeRemainder_subset_requirements
    (inventory : ClosureInventory) {requirement : String}
    (hRemainder : requirement ∈ activeRemainder inventory) :
    requirement ∈ inventory.requirements :=
  ((mem_activeRemainder_iff inventory requirement).mp hRemainder).1

theorem closedVerified_not_active
    (inventory : ClosureInventory) {requirement : String}
    (hClosed : requirement ∈ inventory.closedVerified) :
    requirement ∉ activeRemainder inventory := by
  simp [activeRemainder, hClosed]

structure LiveSnapshot where
  authority : NodeBinding
  mirror : Option NodeBinding
  candidate : NodeBinding
  effectState : EffectState
  causal : CausalReference
  mandatoryGates : List (String × GateState)
  evidenceRefs : List String
  reasonCodes : List String
  nextPossibleStep : String
  observedAt : String
  closure : ClosureInventory
deriving DecidableEq, Repr

structure SerializedFrame where
  protocolVersion : String
  profileVersion : String
  sequence : Nat
  authority : NodeBinding
  mirror : Option NodeBinding
  candidate : NodeBinding
  effectState : EffectState
  causal : CausalReference
  mandatoryGates : List (String × GateState)
  evidenceRefs : List String
  reasonCodes : List String
  nextPossibleStep : String
  observedAt : String
  requirements : List String
  closedVerified : List String
  activeRemainder : List String
deriving DecidableEq, Repr

def wireProtocolVersion : String := "effect-ack-v1"

def liveProfileVersion : String := "qikvrt-repository-live-v1"

def frameInventory (frame : SerializedFrame) : ClosureInventory where
  requirements := frame.requirements
  closedVerified := frame.closedVerified

def encode (sequence : Nat) (snapshot : LiveSnapshot) : SerializedFrame where
  protocolVersion := wireProtocolVersion
  profileVersion := liveProfileVersion
  sequence := sequence
  authority := snapshot.authority
  mirror := snapshot.mirror
  candidate := snapshot.candidate
  effectState := snapshot.effectState
  causal := snapshot.causal
  mandatoryGates := snapshot.mandatoryGates
  evidenceRefs := snapshot.evidenceRefs
  reasonCodes := snapshot.reasonCodes
  nextPossibleStep := snapshot.nextPossibleStep
  observedAt := snapshot.observedAt
  requirements := snapshot.closure.requirements
  closedVerified := snapshot.closure.closedVerified
  activeRemainder := activeRemainder snapshot.closure

def FrameConsistent (frame : SerializedFrame) : Prop :=
  frame.protocolVersion = wireProtocolVersion ∧
  frame.profileVersion = liveProfileVersion ∧
  frame.activeRemainder = activeRemainder (frameInventory frame)

instance frameConsistentDecidable (frame : SerializedFrame) :
    Decidable (FrameConsistent frame) := by
  unfold FrameConsistent
  infer_instance

def decode (frame : SerializedFrame) : Option LiveSnapshot :=
  if _h : FrameConsistent frame then
    some {
      authority := frame.authority
      mirror := frame.mirror
      candidate := frame.candidate
      effectState := frame.effectState
      causal := frame.causal
      mandatoryGates := frame.mandatoryGates
      evidenceRefs := frame.evidenceRefs
      reasonCodes := frame.reasonCodes
      nextPossibleStep := frame.nextPossibleStep
      observedAt := frame.observedAt
      closure := frameInventory frame
    }
  else
    none

theorem frameConsistent_encode (sequence : Nat) (snapshot : LiveSnapshot) :
    FrameConsistent (encode sequence snapshot) := by
  simp [FrameConsistent, encode, frameInventory]

theorem decode_encode (sequence : Nat) (snapshot : LiveSnapshot) :
    decode (encode sequence snapshot) = some snapshot := by
  have hConsistent : FrameConsistent (encode sequence snapshot) :=
    frameConsistent_encode sequence snapshot
  simp [decode, hConsistent, encode, frameInventory]

theorem remainder_encode (sequence : Nat) (snapshot : LiveSnapshot) :
    (encode sequence snapshot).activeRemainder =
      activeRemainder snapshot.closure := by
  rfl

/-- Wire ordering cannot manufacture or alter the explicit causal reference. -/
theorem wireSequence_not_causalAuthority
    (first second : Nat) (snapshot : LiveSnapshot) :
    (encode first snapshot).causal = (encode second snapshot).causal := by
  rfl

/-- Wire ordering cannot alter the decoded semantic snapshot. -/
theorem wireSequence_not_snapshotAuthority
    (first second : Nat) (snapshot : LiveSnapshot) :
    decode (encode first snapshot) = decode (encode second snapshot) := by
  rw [decode_encode first snapshot, decode_encode second snapshot]

def withRemainder
    (frame : SerializedFrame) (remainder : List String) : SerializedFrame :=
  { frame with activeRemainder := remainder }

theorem inconsistentRemainder_rejected
    (frame : SerializedFrame) (remainder : List String)
    (hInconsistent : remainder ≠ activeRemainder (frameInventory frame)) :
    decode (withRemainder frame remainder) = none := by
  simp [decode, FrameConsistent, withRemainder, frameInventory, hInconsistent]

end QIKVRT.EffectAck.Live.V1
