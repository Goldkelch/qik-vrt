import QIKVRTFormalization.Gates

/-!
# Representational quantizability without ontic discreteness

Cantor bit streams provide a fully constructive countermodel.  Every finite
precision `n` has a finite code (`Fin n → Bool`), yet no finite precision
determines the whole stream.  Thus arbitrarily fine finite representation
does not entail an ontically finite or discrete underlying state.
-/

namespace QIKVRT

public abbrev BitStream := Nat → Bool
public abbrev BitPrefix (n : Nat) := Fin n → Bool

public def truncate (n : Nat) (x : BitStream) : BitPrefix n := fun i => x i.val

public def extendZero (n : Nat) (p : BitPrefix n) : BitStream := fun k =>
  if h : k < n then p ⟨k, h⟩ else false

public def AgreeThrough (n : Nat) (x y : BitStream) : Prop :=
  ∀ k, k < n → x k = y k

public theorem truncate_extend_agrees (n : Nat) (x : BitStream) :
    AgreeThrough n x (extendZero n (truncate n x)) := by
  intro k hk
  simp [extendZero, truncate, hk]

public theorem finiteCodeAtEveryPrecision (n : Nat) :
    ∃ encode : BitStream → BitPrefix n, ∃ decode : BitPrefix n → BitStream,
      ∀ x, AgreeThrough n x (decode (encode x)) := by
  exact ⟨truncate n, extendZero n, truncate_extend_agrees n⟩

public def flipAt (n : Nat) (x : BitStream) : BitStream := fun k =>
  if k = n then !(x k) else x k

public theorem flipAt_ne (n : Nat) (x : BitStream) : flipAt n x ≠ x := by
  intro h
  have hn := congrFun h n
  simpa [flipAt] using hn

public theorem flipAt_agrees_before (n : Nat) (x : BitStream) :
    AgreeThrough n x (flipAt n x) := by
  intro k hk
  have hne : k ≠ n := Nat.ne_of_lt hk
  simp [flipAt, hne]

public theorem noFinitePrecisionDeterminesOnticState (n : Nat) (x : BitStream) :
    ∃ y, y ≠ x ∧ AgreeThrough n x y := by
  exact ⟨flipAt n x, flipAt_ne n x, flipAt_agrees_before n x⟩

public theorem quantizable_does_not_imply_finite_resolution :
    (∀ n, ∃ encode : BitStream → BitPrefix n, ∃ decode : BitPrefix n → BitStream,
      ∀ x, AgreeThrough n x (decode (encode x))) ∧
    (∀ n x, ∃ y, y ≠ x ∧ AgreeThrough n x y) := by
  exact ⟨finiteCodeAtEveryPrecision, noFinitePrecisionDeterminesOnticState⟩

end QIKVRT
