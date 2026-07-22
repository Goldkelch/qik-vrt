import QIKVRTFormalization.Iteration

/-!
# PASS / CONTINUE / BLOCK and factorization

Soundness is proof-carrying: a gate specification contains proofs that each
terminal certificate implies the corresponding exact class.  CONTINUE is
deliberately non-terminal.
-/

namespace QIKVRT

universe u v w

public inductive Gate where
  | pass
  | continue
  | block
deriving DecidableEq, Repr, BEq

public structure GateSpecification (α : Type u) where
  inside : α → Prop
  outside : α → Prop
  passCertificate : Nat → α → Prop
  blockCertificate : Nat → α → Prop
  passSound : ∀ n x, passCertificate n x → inside x
  blockSound : ∀ n x, blockCertificate n x → outside x
  passMonotone : ∀ n x, passCertificate n x → passCertificate (n + 1) x
  blockMonotone : ∀ n x, blockCertificate n x → blockCertificate (n + 1) x
  classesDisjoint : ∀ x, inside x → outside x → False

@[expose] public noncomputable def evaluateGate
    (spec : GateSpecification α) (n : Nat) (x : α) : Gate := by
  classical
  exact if spec.blockCertificate n x then Gate.block
    else if spec.passCertificate n x then Gate.pass
    else Gate.continue

public theorem evaluate_block_sound (spec : GateSpecification α) (n : Nat) (x : α)
    (h : evaluateGate spec n x = Gate.block) : spec.outside x := by
  classical
  simp only [evaluateGate] at h
  split at h
  next hBlock => exact spec.blockSound n x hBlock
  next hNoBlock =>
    split at h
    next hPass => cases h
    next hNoPass => cases h

public theorem evaluate_pass_sound (spec : GateSpecification α) (n : Nat) (x : α)
    (h : evaluateGate spec n x = Gate.pass) : spec.inside x := by
  classical
  simp only [evaluateGate] at h
  split at h
  next hBlock => simp_all
  next hNoBlock =>
    split at h
    next hPass => exact spec.passSound n x hPass
    next hNoPass => simp_all

public theorem terminal_certificates_exclusive (spec : GateSpecification α)
    (n m : Nat) (x : α) (hp : spec.passCertificate n x)
    (hb : spec.blockCertificate m x) : False :=
  spec.classesDisjoint x (spec.passSound n x hp) (spec.blockSound m x hb)

@[expose] public def FiberConstant (f : α → β) (g : α → γ) : Prop :=
  ∀ ⦃x y⦄, f x = f y → g x = g y

public abbrev RangePoint (f : α → β) := {y : β // ∃ x, f x = y}

public theorem factorization_iff_fiberConstant (f : α → β) (g : α → γ) :
    (∃ h : RangePoint f → γ,
      ∀ x, h ⟨f x, ⟨x, rfl⟩⟩ = g x) ↔ FiberConstant f g := by
  classical
  constructor
  · rintro ⟨h, hh⟩ x y hxy
    rw [← hh x, ← hh y]
    congr
  · intro hFiber
    let h : RangePoint f → γ := fun y => g (Classical.choose y.property)
    refine ⟨h, ?_⟩
    intro x
    apply hFiber
    exact Classical.choose_spec (show ∃ a, f a = f x from ⟨x, rfl⟩)

public structure TaggedTrajectory (P : Type u) (S : Type v) where
  trace : Nat → TaggedState P S
  parameterConstant : ∀ n, (trace n).parameter = (trace 0).parameter

@[expose] public def shiftTrajectory (γ : TaggedTrajectory α β) : TaggedTrajectory α β where
  trace n := γ.trace (n + 1)
  parameterConstant n := by
    rw [γ.parameterConstant (n + 1), γ.parameterConstant 1]

@[expose] public def classifyTrajectory (member : α → Gate) (γ : TaggedTrajectory α β) : Gate :=
  member (γ.trace 0).parameter

public theorem exactClassifier_shiftInvariant (member : α → Gate)
    (γ : TaggedTrajectory α β) :
    classifyTrajectory member (shiftTrajectory γ) = classifyTrajectory member γ := by
  simp only [classifyTrajectory, shiftTrajectory]
  rw [γ.parameterConstant 1]

end QIKVRT
