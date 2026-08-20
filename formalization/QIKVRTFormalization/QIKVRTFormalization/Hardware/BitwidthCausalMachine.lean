import Mathlib

namespace QIKVRTFormalization.Hardware

/-- The four fail-closed QIK-VRT boundary decisions. -/
inductive Decision where
  | noop
  | hold
  | reobserve
  | requestAuthority
  deriving DecidableEq, Repr

/-- Stable two-bit semantic code.  Wider machine words embed this code; they do not redefine it. -/
def Decision.code : Decision → Fin 4
  | .noop => 0
  | .hold => 1
  | .reobserve => 2
  | .requestAuthority => 3

/-- A finite machine word of width `n`. -/
abbrev Word (n : Nat) := Fin (2 ^ n)

/-- Encode a decision in any word width that can represent the four-state ABI. -/
def encode {n : Nat} (h : 2 ≤ n) (d : Decision) : Word n :=
  ⟨d.code.val, by
    have h4 : 4 ≤ 2 ^ n := by
      calc
        4 = 2 ^ 2 := by norm_num
        _ ≤ 2 ^ n := Nat.pow_le_pow_right (by norm_num) h
    exact lt_of_lt_of_le d.code.isLt h4⟩

/-- Zero-extension from width `n` to a wider width `m`. -/
def widen {n m : Nat} (h : n ≤ m) (w : Word n) : Word m :=
  ⟨w.val, by
    exact lt_of_lt_of_le w.isLt (Nat.pow_le_pow_right (by norm_num) h)⟩

/-- Widening preserves the represented natural value exactly. -/
theorem widen_val {n m : Nat} (h : n ≤ m) (w : Word n) :
    (widen h w).val = w.val := rfl

/-- Core refinement theorem: widening a QIK-VRT decision preserves its semantic code. -/
theorem encode_refines {n m : Nat} (hn : 2 ≤ n) (h : n ≤ m) (d : Decision) :
    widen h (encode hn d) = encode (le_trans hn h) d := by
  apply Fin.ext
  rfl

/-- The concrete 8/16/32/64/128-bit chain therefore carries one invariant decision semantics. -/
theorem standard_width_chain (d : Decision) :
    widen (by norm_num : 8 ≤ 16) (encode (by norm_num : 2 ≤ 8) d) =
      encode (by norm_num : 2 ≤ 16) d ∧
    widen (by norm_num : 16 ≤ 32) (encode (by norm_num : 2 ≤ 16) d) =
      encode (by norm_num : 2 ≤ 32) d ∧
    widen (by norm_num : 32 ≤ 64) (encode (by norm_num : 2 ≤ 32) d) =
      encode (by norm_num : 2 ≤ 64) d ∧
    widen (by norm_num : 64 ≤ 128) (encode (by norm_num : 2 ≤ 64) d) =
      encode (by norm_num : 2 ≤ 128) d := by
  constructor
  · exact encode_refines _ _ d
  constructor
  · exact encode_refines _ _ d
  constructor
  · exact encode_refines _ _ d
  · exact encode_refines _ _ d

/-- One bit can encode a binary distinction, but not the four-state boundary ABI injectively. -/
theorem one_bit_not_enough_for_four_states : ¬ Function.Injective (fun d : Decision => (d.code.val % 2 : Nat)) := by
  intro h
  have : Decision.noop = Decision.reobserve := h (by decide)
  cases this

end QIKVRTFormalization.Hardware
