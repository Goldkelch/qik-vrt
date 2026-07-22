import Std

/-!
# Set-theoretic foundation

This module formalizes the claims that are independent of topology, metric,
dimension, and physics: relative complement, disjoint partition, preimage
partition, and complement preservation under injective maps.
-/

namespace QIKVRT

universe u v

public abbrev Class (α : Type u) := α → Prop

namespace Class

public def subset (A B : Class α) : Prop := ∀ ⦃x⦄, A x → B x
public def equal (A B : Class α) : Prop := ∀ x, A x ↔ B x
public def inter (A B : Class α) : Class α := fun x => A x ∧ B x
public def union (A B : Class α) : Class α := fun x => A x ∨ B x
public def diff (A B : Class α) : Class α := fun x => A x ∧ ¬ B x
public def empty : Class α := fun _ => False
public def preimage (f : α → β) (B : Class β) : Class α := fun x => B (f x)
public def image (f : α → β) (A : Class α) : Class β := fun y => ∃ x, A x ∧ f x = y
public def disjoint (A B : Class α) : Prop := ∀ ⦃x⦄, A x → B x → False
public def bijective (f : α → β) : Prop :=
  Function.Injective f ∧ ∀ y, ∃ x, f x = y

notation:50 A " ⊆ₚ " B => subset A B
notation:50 A " =ₚ " B => equal A B

public theorem equal_refl (A : Class α) : A =ₚ A := by
  intro x
  exact Iff.rfl

public theorem equal_symm {A B : Class α} (h : A =ₚ B) : B =ₚ A := by
  intro x
  exact (h x).symm

public theorem relativeComplement_complete (U A : Class α) :
    union (inter A U) (diff U (inter A U)) =ₚ U := by
  classical
  intro x
  constructor
  · intro hx
    cases hx with
    | inl h => exact h.2
    | inr h => exact h.1
  · intro hU
    by_cases hA : A x
    · exact Or.inl ⟨hA, hU⟩
    · exact Or.inr ⟨hU, fun h => hA h.1⟩

public theorem relativeComplement_disjoint (U A : Class α) :
    disjoint (inter A U) (diff U (inter A U)) := by
  intro x hAU hDiff
  exact hDiff.2 hAU

public theorem dimensionsIndependentPartition (X A : Class α) :
    union (inter A X) (diff X (inter A X)) =ₚ X :=
  relativeComplement_complete X A

public theorem preimage_inter (f : α → β) (A B : Class β) :
    preimage f (inter A B) =ₚ inter (preimage f A) (preimage f B) := by
  intro x
  exact Iff.rfl

public theorem preimage_diff (f : α → β) (A B : Class β) :
    preimage f (diff A B) =ₚ diff (preimage f A) (preimage f B) := by
  intro x
  exact Iff.rfl

public theorem preimage_partition (f : α → β) (U A : Class β)
    (htotal : ∀ x, U (f x)) :
    union (preimage f (inter A U)) (preimage f (diff U (inter A U))) =ₚ
      (fun _ : α => True) := by
  classical
  intro x
  constructor
  · intro _
    trivial
  · intro _
    have h := (relativeComplement_complete U A (f x)).2 (htotal x)
    exact h

public theorem image_complement_inclusion (f : α → β) (X A : Class α) :
    diff (image f X) (image f A) ⊆ₚ image f (diff X A) := by
  intro y hy
  rcases hy.1 with ⟨x, hX, hxy⟩
  refine ⟨x, ?_, hxy⟩
  exact ⟨hX, fun hA => hy.2 ⟨x, hA, hxy⟩⟩

public theorem injective_image_complement (f : α → β) (hf : Function.Injective f)
    (X A : Class α) (hAX : A ⊆ₚ X) :
    image f (diff X A) =ₚ diff (image f X) (image f A) := by
  intro y
  constructor
  · rintro ⟨x, ⟨hX, hnA⟩, hxy⟩
    refine ⟨⟨x, hX, hxy⟩, ?_⟩
    rintro ⟨a, hA, hay⟩
    have hfa : f a = f x := hay.trans hxy.symm
    exact hnA (hf hfa ▸ hA)
  · intro hy
    exact image_complement_inclusion f X A hy

public theorem bijective_image_complement (f : α → β) (hf : bijective f)
    (A : Class α) :
    image f (diff (fun _ => True) A) =ₚ diff (fun _ => True) (image f A) := by
  intro y
  constructor
  · rintro ⟨x, ⟨_, hnA⟩, hxy⟩
    refine ⟨trivial, ?_⟩
    rintro ⟨a, hA, hay⟩
    exact hnA (hf.1 (hay.trans hxy.symm) ▸ hA)
  · intro hy
    rcases hf.2 y with ⟨x, hxy⟩
    refine ⟨x, ⟨trivial, ?_⟩, hxy⟩
    intro hA
    exact hy.2 ⟨x, hA, hxy⟩

end Class
end QIKVRT
