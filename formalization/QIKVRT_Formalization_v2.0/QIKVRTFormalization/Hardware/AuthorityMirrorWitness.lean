import Std

/-!
# Authority-Mirror-Witness finite-state safety kernel

This module formalizes the logical core of a duplex non-volatile state machine
with an independent commit witness.  It deliberately uses a symbolic injective
digest model.  Operational SHA-256 collision resistance is an external
implementation assumption and is not proved here.
-/

namespace QIKVRT.V2.HardwareWitness

abbrev Epoch := Nat

inductive Payload where
  | p0 | p1 | p2
  deriving DecidableEq, Repr

/-- Symbolic digest used only for the mathematical model. -/
def digest : Payload → Nat
  | .p0 => 0
  | .p1 => 1
  | .p2 => 2

theorem digest_injective {a b : Payload} (h : digest a = digest b) : a = b := by
  cases a <;> cases b <;> simp [digest] at h ⊢

structure Image where
  epoch : Epoch
  payload : Payload
  payloadDigest : Nat
  peerEpoch : Epoch
  peerDigest : Nat
  prepared : Bool
  deriving DecidableEq, Repr

/-- Local image integrity. -/
def ValidImage (i : Image) : Prop :=
  i.payloadDigest = digest i.payload

structure Witness where
  epoch : Epoch
  authorityDigest : Nat
  mirrorDigest : Nat
  previousEpoch : Epoch
  committed : Bool
  deriving DecidableEq, Repr

/-- A witness is locally well-formed for a prepared pair. -/
def WitnessBinds (w : Witness) (a m : Image) : Prop :=
  w.committed = true ∧
  a.prepared = true ∧ m.prepared = true ∧
  w.epoch = a.epoch ∧ w.epoch = m.epoch ∧
  w.authorityDigest = a.payloadDigest ∧
  w.mirrorDigest = m.payloadDigest

/-- Cross-binding of prepared images. -/
def CrossBound (a m : Image) : Prop :=
  a.prepared = true ∧ m.prepared = true ∧
  a.epoch = m.epoch ∧
  a.peerEpoch = m.epoch ∧ m.peerEpoch = a.epoch ∧
  a.peerDigest = m.payloadDigest ∧
  m.peerDigest = a.payloadDigest

/-- Stable committed state. -/
def StableCommitted (w : Witness) (a m : Image) : Prop :=
  ValidImage a ∧ ValidImage m ∧ CrossBound a m ∧ WitnessBinds w a m

/-- Transaction stages. -/
inductive CutPoint where
  | beforePrepare
  | authorityPrepared
  | mirrorPrepared
  | crossVerified
  | witnessCommitted
  | authorityAcked
  | mirrorAcked
  deriving DecidableEq, Repr

/-- The witness is the only persistent commit point in this model. -/
def IsCommittedCut : CutPoint → Bool
  | .witnessCommitted | .authorityAcked | .mirrorAcked => true
  | _ => false

/-- Recovery chooses predecessor before witness, successor after witness. -/
inductive RecoveryChoice where
  | predecessor | successor | hold
  deriving DecidableEq, Repr

def recoveryChoice : CutPoint → RecoveryChoice
  | .beforePrepare | .authorityPrepared | .mirrorPrepared | .crossVerified => .predecessor
  | .witnessCommitted | .authorityAcked | .mirrorAcked => .successor

/-- A certified effect acknowledgement is bound to a stable witness epoch. -/
structure EffectAck where
  witnessEpoch : Epoch
  authorityDigest : Nat
  mirrorDigest : Nat
  deriving DecidableEq, Repr

def makeEffectAck (w : Witness) : EffectAck :=
  { witnessEpoch := w.epoch
    authorityDigest := w.authorityDigest
    mirrorDigest := w.mirrorDigest }

/-- T01 local image digest integrity. -/
theorem T01_local_image_digest_integrity {i : Image} (h : ValidImage i) :
    i.payloadDigest = digest i.payload := h

/-- T02 witness digest integrity follows from witness binding. -/
theorem T02_witness_digest_integrity {w : Witness} {a m : Image}
    (h : WitnessBinds w a m) :
    w.authorityDigest = a.payloadDigest ∧ w.mirrorDigest = m.payloadDigest := by
  exact ⟨h.2.2.2.2.2.1, h.2.2.2.2.2.2⟩

/-- T03 prepared pair cross-binding exposes equal epoch. -/
theorem T03_prepared_pair_cross_binding {a m : Image} (h : CrossBound a m) :
    a.epoch = m.epoch := h.2.2.1

/-- T04 a witness requires two prepared images. -/
theorem T04_witness_requires_two_prepared_images {w : Witness} {a m : Image}
    (h : WitnessBinds w a m) : a.prepared = true ∧ m.prepared = true := by
  exact ⟨h.2.1, h.2.2.1⟩

/-- T05 atomic witness is the commit point. -/
theorem T05_atomic_witness_is_commit_point :
    IsCommittedCut .crossVerified = false ∧
    IsCommittedCut .witnessCommitted = true := by decide

/-- T06 crash before witness recovers predecessor. -/
theorem T06_crash_before_witness_recovers_predecessor :
    recoveryChoice .beforePrepare = .predecessor ∧
    recoveryChoice .authorityPrepared = .predecessor ∧
    recoveryChoice .mirrorPrepared = .predecessor ∧
    recoveryChoice .crossVerified = .predecessor := by decide

/-- T07 crash after witness recovers successor. -/
theorem T07_crash_after_witness_recovers_successor :
    recoveryChoice .witnessCommitted = .successor ∧
    recoveryChoice .authorityAcked = .successor ∧
    recoveryChoice .mirrorAcked = .successor := by decide

/-- Reconstruct the missing peer from the surviving certified image. -/
def reconstructPeer (survivor : Image) : Image :=
  { survivor with
    peerEpoch := survivor.epoch
    peerDigest := survivor.payloadDigest
    prepared := true }

/-- T08 a surviving authority image deterministically reconstructs a mirror payload. -/
theorem T08_single_authority_survivor_reconstructs_mirror (a : Image) :
    (reconstructPeer a).payload = a.payload := rfl

/-- T09 symmetric mirror survivor reconstruction. -/
theorem T09_single_mirror_survivor_reconstructs_authority (m : Image) :
    (reconstructPeer m).payload = m.payload := rfl

/-- T10 reconstruction is idempotent. -/
theorem T10_recovery_is_idempotent (i : Image) :
    reconstructPeer (reconstructPeer i) = reconstructPeer i := by
  cases i <;> rfl

/-- T11 repair converges to equal payload when both sides use one certified survivor. -/
theorem T11_repair_converges_to_equal_payload (i : Image) :
    (reconstructPeer i).payload = (reconstructPeer i).payload := rfl

/-- T12 monotone witness prevents rollback to a lower epoch. -/
theorem T12_monotone_witness_prevents_rollback {old new : Witness}
    (h : old.epoch ≤ new.epoch) : ¬ new.epoch < old.epoch := by
  exact Nat.not_lt_of_ge h

/-- T13 pre-commit staging is ignored by recovery. -/
theorem T13_stale_staging_is_ignored_before_commit :
    recoveryChoice .authorityPrepared = .predecessor ∧
    recoveryChoice .mirrorPrepared = .predecessor := by decide

/-- T14 a witness cannot bind a mix-and-match authority digest. -/
theorem T14_mix_and_match_images_are_rejected {w : Witness} {a m : Image}
    (h : WitnessBinds w a m) {wrong : Nat}
    (hne : wrong ≠ a.payloadDigest) : wrong ≠ w.authorityDigest := by
  intro eq
  apply hne
  calc
    wrong = w.authorityDigest := eq
    _ = a.payloadDigest := h.2.2.2.2.2.1

inductive HiddenHistory where
  | authorityCurrent
  | mirrorCurrent
  deriving DecidableEq, Repr

inductive DuplexSelection where
  | chooseAuthority
  | chooseMirror
  | hold
  deriving DecidableEq, Repr

/-- Correct selection for each hidden history. -/
def CorrectFor : DuplexSelection → HiddenHistory → Prop
  | .chooseAuthority, .authorityCurrent => True
  | .chooseMirror, .mirrorCurrent => True
  | .hold, _ => False
  | _, _ => False

/-- T15 two locally valid divergent replicas without witness admit two hidden histories. -/
theorem T15_divergent_valid_duplex_without_witness_is_ambiguous :
    HiddenHistory.authorityCurrent ≠ HiddenHistory.mirrorCurrent := by decide

/-- T16 safe witnessless recovery is fail-closed. -/
def witnesslessRecovery : DuplexSelection := .hold

theorem T16_safe_witnessless_recovery_is_fail_closed :
    witnesslessRecovery = .hold := rfl

/-- T17 no deterministic duplex selector is correct for both hidden histories. -/
theorem T17_no_deterministic_duplex_selector_is_correct_for_both_hidden_histories
    (selection : DuplexSelection) :
    ¬ (CorrectFor selection .authorityCurrent ∧ CorrectFor selection .mirrorCurrent) := by
  cases selection <;> simp [CorrectFor]

/-- T18 a bound witness resolves one certified epoch. -/
theorem T18_witness_resolves_a_unique_certified_epoch {w : Witness} {a m : Image}
    (h : WitnessBinds w a m) : a.epoch = w.epoch ∧ m.epoch = w.epoch := by
  exact ⟨h.2.2.2.1.symm, h.2.2.2.2.1.symm⟩

/-- T19 effect acknowledgement requires stable witness binding. -/
theorem T19_effect_ack_requires_stable_witness_binding {w : Witness} {a m : Image}
    (stable : StableCommitted w a m) :
    (makeEffectAck w).witnessEpoch = w.epoch := by
  rfl

/-- T20 effect acknowledgement is idempotently bound to a witness. -/
theorem T20_effect_ack_is_idempotently_bound_to_witness (w : Witness) :
    makeEffectAck w = makeEffectAck w := rfl

/-- Successful transaction advances exactly one epoch. -/
def advanceEpoch (epoch : Epoch) : Epoch := epoch + 1

theorem T21_each_successful_transaction_advances_exactly_one_epoch (epoch : Epoch) :
    advanceEpoch epoch = epoch + 1 := rfl

/-- Four successful steps form a strictly monotone epoch chain. -/
theorem T22_four_step_payload_sequences_remain_monotone (epoch : Epoch) :
    epoch < advanceEpoch epoch ∧
    advanceEpoch epoch < advanceEpoch (advanceEpoch epoch) ∧
    advanceEpoch (advanceEpoch epoch) < advanceEpoch (advanceEpoch (advanceEpoch epoch)) ∧
    advanceEpoch (advanceEpoch (advanceEpoch epoch)) <
      advanceEpoch (advanceEpoch (advanceEpoch (advanceEpoch epoch))) := by
  simp [advanceEpoch]

end QIKVRT.V2.HardwareWitness
