import QIKVRTFormalization.Foundation.RelativeComplement

/-!
# Images of relative complements (MAP-003)

The strongest theorem below does not need `A ⊆ X`.  The manuscript wrapper
retains that stated hypothesis explicitly and thereby checks the published
formulation without silently strengthening its assumptions.
-/

namespace QIKVRT.V2
namespace Class

universe u v

theorem imageComplement_inclusion (f : α → β) (X A : Class α) :
    Diff (Image f X) (Image f A) ⊆ₚ Image f (Diff X A) := by
  intro y hy
  rcases hy.1 with ⟨x, hX, hxy⟩
  exact ⟨x, ⟨hX, fun hA => hy.2 ⟨x, hA, hxy⟩⟩, hxy⟩

theorem imageRelativeComplement_eq_iff_imageClasses_disjoint
    (f : α → β) (X A : Class α) :
    (Image f (Diff X A) =ₚ Diff (Image f X) (Image f A)) ↔
      Disjoint (Image f A) (Image f (Diff X A)) := by
  constructor
  · intro hEqual y hA hComplement
    exact ((hEqual y).1 hComplement).2 hA
  · intro hDisjoint y
    constructor
    · intro hComplement
      refine ⟨?_, ?_⟩
      · rcases hComplement with ⟨x, hXA, hxy⟩
        exact ⟨x, hXA.1, hxy⟩
      · intro hA
        exact hDisjoint hA hComplement
    · intro hDifference
      exact imageComplement_inclusion f X A hDifference

theorem injective_imageRelativeComplement
    (f : α → β) (hf : Injective f) (X A : Class α) :
    Image f (Diff X A) =ₚ Diff (Image f X) (Image f A) := by
  intro y
  constructor
  · rintro ⟨x, ⟨hX, hNotA⟩, hxy⟩
    refine ⟨⟨x, hX, hxy⟩, ?_⟩
    rintro ⟨a, hA, hay⟩
    have hfa : f a = f x := hay.trans hxy.symm
    exact hNotA (hf hfa ▸ hA)
  · intro hy
    exact imageComplement_inclusion f X A hy

theorem bijective_imageRelativeComplement
    (f : α → β) (hf : Bijective f) (A : Class α) :
    Image f (Diff Univ A) =ₚ Diff Univ (Image f A) := by
  intro y
  constructor
  · rintro ⟨x, ⟨_, hNotA⟩, hxy⟩
    refine ⟨trivial, ?_⟩
    rintro ⟨a, hA, hay⟩
    exact hNotA (hf.1 (hay.trans hxy.symm) ▸ hA)
  · rintro ⟨_, hNotImage⟩
    rcases hf.2 y with ⟨x, hxy⟩
    refine ⟨x, ⟨trivial, ?_⟩, hxy⟩
    intro hA
    exact hNotImage ⟨x, hA, hxy⟩

def MAP003Statement (f : α → β) (X A : Class α)
    (_manuscriptAssumption : A ⊆ₚ X) : Prop :=
  (Diff (Image f X) (Image f A) ⊆ₚ Image f (Diff X A)) ∧
  ((Image f (Diff X A) =ₚ Diff (Image f X) (Image f A)) ↔
    Disjoint (Image f A) (Image f (Diff X A))) ∧
  (Injective f →
    Image f (Diff X A) =ₚ Diff (Image f X) (Image f A)) ∧
  (Bijective f →
    Image f (Diff Univ A) =ₚ Diff Univ (Image f A))

theorem MAP003_checked (f : α → β) (X A : Class α)
    (hAX : A ⊆ₚ X) : MAP003Statement f X A hAX := by
  refine ⟨imageComplement_inclusion f X A, ?_, ?_, ?_⟩
  · exact imageRelativeComplement_eq_iff_imageClasses_disjoint f X A
  · intro hf
    exact injective_imageRelativeComplement f hf X A
  · intro hf
    exact bijective_imageRelativeComplement f hf A

end Class
end QIKVRT.V2
