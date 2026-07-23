import QIKVRTFormalization.Foundation.RelativeComplement

/-!
# Preimages of a relative complement (MAP-001)

The Lean domain type `α` represents the manuscript's set `X`.  Since the
codomain is represented by a predicate `U : Class β`, totality into the
chosen codomain is retained as the explicit hypothesis
`htotal : TotalInto f U` rather than being hidden in prose.
-/

namespace QIKVRT.V2
namespace Class

universe u v

def Preimage (f : α → β) (B : Class β) : Class α :=
  fun x => B (f x)

def TotalInto (f : α → β) (U : Class β) : Prop :=
  ∀ x, U (f x)

theorem preimageRelativeComplement_complete
    (f : α → β) (U A : Class β) (htotal : TotalInto f U) :
    Union (Preimage f (Inter A U))
      (Preimage f (Diff U (Inter A U))) =ₚ Univ := by
  classical
  intro x
  constructor
  · intro _
    trivial
  · intro _
    have hU : U (f x) := htotal x
    by_cases hA : A (f x)
    · exact Or.inl ⟨hA, hU⟩
    · exact Or.inr ⟨hU, fun hAU => hA hAU.1⟩

theorem preimageRelativeComplement_disjoint
    (f : α → β) (U A : Class β) :
    Disjoint (Preimage f (Inter A U))
      (Preimage f (Diff U (Inter A U))) := by
  intro x hClass hComplement
  exact hComplement.2 hClass

def MAP001Statement
    (f : α → β) (U A : Class β)
    (_manuscriptAssumption : TotalInto f U) : Prop :=
  (Union (Preimage f (Inter A U))
      (Preimage f (Diff U (Inter A U))) =ₚ Univ) ∧
  Disjoint (Preimage f (Inter A U))
    (Preimage f (Diff U (Inter A U)))

theorem MAP001_checked
    (f : α → β) (U A : Class β) (htotal : TotalInto f U) :
    MAP001Statement f U A htotal := by
  exact ⟨preimageRelativeComplement_complete f U A htotal,
    preimageRelativeComplement_disjoint f U A⟩

end Class
end QIKVRT.V2
