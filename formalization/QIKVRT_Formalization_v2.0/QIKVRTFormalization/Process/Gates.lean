import Std

/-!
# Proof-carrying three-state gates

PASS and BLOCK are terminal only when supported by sound, monotonically
persistent certificates.  CONTINUE deliberately carries no class assertion.
-/

namespace QIKVRT.V2

universe u

inductive Gate where
  | pass
  | continue
  | block
deriving DecidableEq, Repr, BEq

namespace Gate

def Terminal : Gate → Prop
  | .pass => True
  | .block => True
  | .continue => False

@[simp] theorem pass_terminal : Terminal .pass := trivial

@[simp] theorem block_terminal : Terminal .block := trivial

@[simp] theorem continue_not_terminal : ¬ Terminal .continue := by
  intro h
  exact h

end Gate

structure GateSpecification (α : Type u) where
  inside : α → Prop
  outside : α → Prop
  passCertificate : Nat → α → Prop
  blockCertificate : Nat → α → Prop
  passDecidable : ∀ n x, Decidable (passCertificate n x)
  blockDecidable : ∀ n x, Decidable (blockCertificate n x)
  passSound : ∀ n x, passCertificate n x → inside x
  blockSound : ∀ n x, blockCertificate n x → outside x
  passStep : ∀ n x, passCertificate n x → passCertificate (n + 1) x
  blockStep : ∀ n x, blockCertificate n x → blockCertificate (n + 1) x
  classesDisjoint : ∀ x, inside x → outside x → False

def evaluateGate (spec : GateSpecification α) (n : Nat) (x : α) : Gate := by
  letI : Decidable (spec.blockCertificate n x) := spec.blockDecidable n x
  letI : Decidable (spec.passCertificate n x) := spec.passDecidable n x
  exact if spec.blockCertificate n x then .block
    else if spec.passCertificate n x then .pass
    else .continue

theorem evaluateGate_eq_block_iff (spec : GateSpecification α)
    (n : Nat) (x : α) :
    evaluateGate spec n x = .block ↔ spec.blockCertificate n x := by
  constructor
  · intro h
    unfold evaluateGate at h
    split at h
    next hBlock => exact hBlock
    next _ =>
      split at h <;> cases h
  · intro hBlock
    unfold evaluateGate
    split
    · rfl
    · next hNoBlock => exact False.elim (hNoBlock hBlock)

theorem evaluateGate_eq_pass_iff (spec : GateSpecification α)
    (n : Nat) (x : α) :
    evaluateGate spec n x = .pass ↔
      ¬ spec.blockCertificate n x ∧ spec.passCertificate n x := by
  constructor
  · intro h
    unfold evaluateGate at h
    split at h
    next _ => cases h
    next hNoBlock =>
      split at h
      next hPass => exact ⟨hNoBlock, hPass⟩
      next _ => cases h
  · rintro ⟨hNoBlock, hPass⟩
    unfold evaluateGate
    split
    · next hBlock => exact False.elim (hNoBlock hBlock)
    · rfl

theorem evaluateGate_eq_continue_iff (spec : GateSpecification α)
    (n : Nat) (x : α) :
    evaluateGate spec n x = .continue ↔
      ¬ spec.blockCertificate n x ∧ ¬ spec.passCertificate n x := by
  constructor
  · intro h
    unfold evaluateGate at h
    split at h
    next _ => cases h
    next hNoBlock =>
      split at h
      next _ => cases h
      next hNoPass => exact ⟨hNoBlock, hNoPass⟩
  · rintro ⟨hNoBlock, hNoPass⟩
    unfold evaluateGate
    split
    · next hBlock => exact False.elim (hNoBlock hBlock)
    · rfl

theorem passCertificate_mono (spec : GateSpecification α)
    {n m : Nat} {x : α} (hnm : n ≤ m)
    (hPass : spec.passCertificate n x) : spec.passCertificate m x := by
  induction hnm with
  | refl => exact hPass
  | @step m _ ih => exact spec.passStep m x ih

theorem blockCertificate_mono (spec : GateSpecification α)
    {n m : Nat} {x : α} (hnm : n ≤ m)
    (hBlock : spec.blockCertificate n x) : spec.blockCertificate m x := by
  induction hnm with
  | refl => exact hBlock
  | @step m _ ih => exact spec.blockStep m x ih

theorem terminalCertificates_exclusive (spec : GateSpecification α)
    {n m : Nat} {x : α} (hPass : spec.passCertificate n x)
    (hBlock : spec.blockCertificate m x) : False :=
  spec.classesDisjoint x
    (spec.passSound n x hPass)
    (spec.blockSound m x hBlock)

theorem evaluateGate_pass_sound (spec : GateSpecification α)
    {n : Nat} {x : α} (hPass : evaluateGate spec n x = .pass) :
    spec.inside x := by
  exact spec.passSound n x ((evaluateGate_eq_pass_iff spec n x).1 hPass).2

theorem evaluateGate_block_sound (spec : GateSpecification α)
    {n : Nat} {x : α} (hBlock : evaluateGate spec n x = .block) :
    spec.outside x := by
  exact spec.blockSound n x ((evaluateGate_eq_block_iff spec n x).1 hBlock)

theorem pass_persistent (spec : GateSpecification α) {n m : Nat} {x : α}
    (hnm : n ≤ m) (hPass : evaluateGate spec n x = .pass) :
    evaluateGate spec m x = .pass := by
  have hPassCertificate := (evaluateGate_eq_pass_iff spec n x).1 hPass |>.2
  have hPassLater := passCertificate_mono spec hnm hPassCertificate
  apply (evaluateGate_eq_pass_iff spec m x).2
  refine ⟨?_, hPassLater⟩
  intro hBlockLater
  exact terminalCertificates_exclusive spec hPassLater hBlockLater

theorem block_persistent (spec : GateSpecification α) {n m : Nat} {x : α}
    (hnm : n ≤ m) (hBlock : evaluateGate spec n x = .block) :
    evaluateGate spec m x = .block := by
  apply (evaluateGate_eq_block_iff spec m x).2
  exact blockCertificate_mono spec hnm
    ((evaluateGate_eq_block_iff spec n x).1 hBlock)

def GAT004Statement (spec : GateSpecification α) : Prop :=
  (∀ (x : α) (n : Nat),
      evaluateGate spec n x = .pass → spec.inside x) ∧
  (∀ (x : α) (n : Nat),
      evaluateGate spec n x = .block → spec.outside x) ∧
  ((∀ (x : α) (n m : Nat), n ≤ m →
      evaluateGate spec n x = .pass → evaluateGate spec m x = .pass) ∧
   (∀ (x : α) (n m : Nat), n ≤ m →
      evaluateGate spec n x = .block → evaluateGate spec m x = .block)) ∧
  (∀ (x : α) (n : Nat), evaluateGate spec n x = .continue →
      ¬ spec.passCertificate n x ∧ ¬ spec.blockCertificate n x)

theorem GAT004_checked (spec : GateSpecification α) :
    GAT004Statement spec := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro x n hPass
    exact evaluateGate_pass_sound spec hPass
  · intro x n hBlock
    exact evaluateGate_block_sound spec hBlock
  · constructor
    · intro x n m hnm hPass
      exact pass_persistent spec hnm hPass
    · intro x n m hnm hBlock
      exact block_persistent spec hnm hBlock
  · intro x n hContinue
    have hNoCertificates := (evaluateGate_eq_continue_iff spec n x).1 hContinue
    exact ⟨hNoCertificates.2, hNoCertificates.1⟩

end QIKVRT.V2
