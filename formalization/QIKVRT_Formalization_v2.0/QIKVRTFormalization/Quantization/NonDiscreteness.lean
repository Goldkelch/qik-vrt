import Std

/-!
# QUA-003A: finite prefix representation does not determine an ontic bit stream

This module proves the representation-theoretic subclaim `QUA-003A` used in
the decomposition of manuscript claim `QUA-003`.
The represented states are infinite Boolean streams.  At precision `n`, the
code is the finite type of Boolean functions on `Fin n`, and zero extension
decodes every such code exactly.  Nevertheless, every prefix fibre contains
an injective copy of `Nat`: independently flipping any one tail coordinate
produces pairwise different streams with exactly the same finite code.
-/

namespace QIKVRT.V2

namespace Quantization

abbrev BitStream := Nat → Bool

abbrev BitPrefix (n : Nat) := Fin n → Bool

def Injective (f : α → β) : Prop :=
  ∀ ⦃left right⦄, f left = f right → left = right

def LeftInverse (decode : β → α) (encode : α → β) : Prop :=
  ∀ value, decode (encode value) = value

def HasFiniteEnumeration (α : Type) : Prop :=
  ∃ values : List α, ∀ value, value ∈ values

def observe (n : Nat) (stream : BitStream) : BitPrefix n :=
  fun k => stream k.val

def zeroExtend (n : Nat) (code : BitPrefix n) : BitStream :=
  fun k => if h : k < n then code ⟨k, h⟩ else false

def SamePrefix (n : Nat) (left right : BitStream) : Prop :=
  observe n left = observe n right

def PrefixFiber (n : Nat) (stream : BitStream) :=
  { candidate : BitStream // SamePrefix n candidate stream }

theorem observe_zeroExtend (n : Nat) (code : BitPrefix n) :
    observe n (zeroExtend n code) = code := by
  funext k
  simp [observe, zeroExtend, k.isLt]

theorem zeroExtend_observe_samePrefix (n : Nat) (stream : BitStream) :
    SamePrefix n (zeroExtend n (observe n stream)) stream := by
  unfold SamePrefix
  exact observe_zeroExtend n (observe n stream)

def prepend (head : Bool) (tail : BitPrefix n) : BitPrefix (n + 1) :=
  fun k => Fin.cases head tail k

def allPrefixes : (n : Nat) → List (BitPrefix n)
  | 0 => [fun k => Fin.elim0 k]
  | n + 1 =>
      (allPrefixes n).map (prepend false) ++
      (allPrefixes n).map (prepend true)

theorem mem_allPrefixes : ∀ n (code : BitPrefix n), code ∈ allPrefixes n := by
  intro n
  induction n with
  | zero =>
      intro code
      have hCode : code = fun k => Fin.elim0 k := by
        funext k
        exact Fin.elim0 k
      simp [allPrefixes, hCode]
  | succ n ih =>
      intro code
      let tail : BitPrefix n := fun k => code k.succ
      have hTail : tail ∈ allPrefixes n := ih tail
      cases hHead : code 0 with
      | false =>
          have hCode : code = prepend false tail := by
            funext k
            refine Fin.cases ?_ (fun j => ?_) k
            · simpa [prepend] using hHead
            · rfl
          rw [hCode]
          apply List.mem_append.mpr
          exact Or.inl (List.mem_map.mpr ⟨tail, hTail, rfl⟩)
      | true =>
          have hCode : code = prepend true tail := by
            funext k
            refine Fin.cases ?_ (fun j => ?_) k
            · simpa [prepend] using hHead
            · rfl
          rw [hCode]
          apply List.mem_append.mpr
          exact Or.inr (List.mem_map.mpr ⟨tail, hTail, rfl⟩)

theorem finitePrefixCode (n : Nat) : HasFiniteEnumeration (BitPrefix n) := by
  exact ⟨allPrefixes n, mem_allPrefixes n⟩

theorem finitePrefixCodingAtEveryPrecision :
    ∀ n, HasFiniteEnumeration (BitPrefix n) ∧
      LeftInverse (observe n) (zeroExtend n) ∧
      ∀ stream, SamePrefix n (zeroExtend n (observe n stream)) stream := by
  intro n
  exact ⟨finitePrefixCode n, observe_zeroExtend n,
    zeroExtend_observe_samePrefix n⟩

def flipAt (position : Nat) (stream : BitStream) : BitStream :=
  fun k => if k = position then !(stream k) else stream k

theorem flipAt_changed (position : Nat) (stream : BitStream) :
    flipAt position stream position = !(stream position) := by
  simp [flipAt]

theorem flipAt_ne (position : Nat) (stream : BitStream) :
    flipAt position stream ≠ stream := by
  intro hEqual
  have hAtPosition := congrFun hEqual position
  simp [flipAt] at hAtPosition

theorem flipAt_preserves_prefix {n position : Nat} (stream : BitStream)
    (hTail : n ≤ position) :
    SamePrefix n (flipAt position stream) stream := by
  apply funext
  intro k
  have hDifferent : k.val ≠ position := by
    intro hEqual
    have : position < n := hEqual ▸ k.isLt
    exact (Nat.not_lt_of_ge hTail) this
  simp [SamePrefix, observe, flipAt, hDifferent]

theorem flipAt_pairwise {left right : Nat} (stream : BitStream)
    (hDifferent : left ≠ right) :
    flipAt left stream ≠ flipAt right stream := by
  intro hEqual
  have hAtLeft := congrFun hEqual left
  have hRightDifferent : left ≠ right := hDifferent
  simp [flipAt, hRightDifferent] at hAtLeft

def tailFlip (n : Nat) (stream : BitStream) (offset : Nat) : BitStream :=
  flipAt (n + offset) stream

theorem tailFlip_preserves_prefix (n : Nat) (stream : BitStream)
    (offset : Nat) :
    SamePrefix n (tailFlip n stream offset) stream := by
  apply flipAt_preserves_prefix
  exact Nat.le_add_right n offset

theorem tailFlip_ne (n : Nat) (stream : BitStream) (offset : Nat) :
    tailFlip n stream offset ≠ stream := by
  exact flipAt_ne (n + offset) stream

theorem tailFlip_injective (n : Nat) (stream : BitStream) :
    Injective (tailFlip n stream) := by
  intro left right hEqual
  by_cases hOffsets : left = right
  · exact hOffsets
  · have hPositions : n + left ≠ n + right := by
      intro hPositionEqual
      exact hOffsets (Nat.add_left_cancel hPositionEqual)
    exact False.elim (flipAt_pairwise stream hPositions hEqual)

def tailAlternative (n : Nat) (stream : BitStream) (offset : Nat) :
    PrefixFiber n stream :=
  ⟨tailFlip n stream offset, tailFlip_preserves_prefix n stream offset⟩

theorem tailAlternative_injective (n : Nat) (stream : BitStream) :
    Injective (tailAlternative n stream) := by
  intro left right hEqual
  apply tailFlip_injective n stream
  exact congrArg Subtype.val hEqual

theorem prefix_does_not_determine_stream (n : Nat) (stream : BitStream) :
    ∃ alternative, alternative ≠ stream ∧
      observe n alternative = observe n stream := by
  exact ⟨tailFlip n stream 0, tailFlip_ne n stream 0,
    tailFlip_preserves_prefix n stream 0⟩

theorem prefix_not_injective (n : Nat) :
    ¬ Injective (observe n) := by
  intro hInjective
  let base : BitStream := fun _ => false
  rcases prefix_does_not_determine_stream n base with
    ⟨alternative, hDifferent, hSameCode⟩
  exact hDifferent (hInjective hSameCode)

end Quantization

open Quantization

/--
The exact machine-checkable content of atomic subclaim `QUA-003A`: finite exact prefix codes
exist at every finite precision, but the corresponding observation map is
never injective and every one of its fibres contains an injective copy of
`Nat` consisting of states distinct from the observed stream.

This is not yet the manuscript's full metric-space statement involving every
positive epsilon and the absence of a least positive distance.  That parent
claim remains pending until the metric countermodel is formalized.
-/
def QUA003APrefixStatement : Prop :=
  (∀ n, HasFiniteEnumeration (BitPrefix n) ∧
    LeftInverse (observe n) (zeroExtend n) ∧
    ∀ stream, SamePrefix n (zeroExtend n (observe n stream)) stream) ∧
  (∀ n, ¬ Injective (observe n)) ∧
  (∀ n stream, ∃ alternative, alternative ≠ stream ∧
    observe n alternative = observe n stream) ∧
  (∀ n stream,
    Injective (tailAlternative n stream) ∧
    ∀ offset, (tailAlternative n stream offset).val ≠ stream)

theorem QUA003A_prefix_checked : QUA003APrefixStatement := by
  refine ⟨finitePrefixCodingAtEveryPrecision, prefix_not_injective, ?_, ?_⟩
  · exact prefix_does_not_determine_stream
  · intro n stream
    exact ⟨tailAlternative_injective n stream, tailFlip_ne n stream⟩

end QIKVRT.V2
