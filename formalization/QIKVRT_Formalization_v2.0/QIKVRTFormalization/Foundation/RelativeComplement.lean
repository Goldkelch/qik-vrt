import Std

/-!
# Predicate classes and relative complements

The manuscript's sets are represented as predicates.  Consequently these
definitions make no assumptions about topology, metric, dimension, or
finiteness.
-/

namespace QIKVRT.V2

universe u v

abbrev Class (α : Type u) := α → Prop

namespace Class

def Subset (A B : Class α) : Prop := ∀ ⦃x⦄, A x → B x

def Equal (A B : Class α) : Prop := ∀ x, A x ↔ B x

def Inter (A B : Class α) : Class α := fun x => A x ∧ B x

def Union (A B : Class α) : Class α := fun x => A x ∨ B x

def Diff (A B : Class α) : Class α := fun x => A x ∧ ¬ B x

def Univ : Class α := fun _ => True

def Empty : Class α := fun _ => False

def Disjoint (A B : Class α) : Prop := ∀ ⦃x⦄, A x → B x → False

def Image (f : α → β) (A : Class α) : Class β :=
  fun y => ∃ x, A x ∧ f x = y

def Range (f : α → β) : Class β := Image f Univ

def Injective (f : α → β) : Prop :=
  ∀ ⦃x y⦄, f x = f y → x = y

def Surjective (f : α → β) : Prop :=
  ∀ y, ∃ x, f x = y

def Bijective (f : α → β) : Prop :=
  Injective f ∧ Surjective f

notation:50 A " ⊆ₚ " B => Subset A B
notation:50 A " =ₚ " B => Equal A B

theorem equal_refl (A : Class α) : A =ₚ A := by
  intro x
  exact Iff.rfl

theorem equal_symm {A B : Class α} (h : A =ₚ B) : B =ₚ A := by
  intro x
  exact (h x).symm

theorem relativeComplement_complete (X A : Class α) :
    Union (Inter A X) (Diff X (Inter A X)) =ₚ X := by
  classical
  intro x
  constructor
  · rintro (hAX | hDiff)
    · exact hAX.2
    · exact hDiff.1
  · intro hX
    by_cases hA : A x
    · exact Or.inl ⟨hA, hX⟩
    · exact Or.inr ⟨hX, fun hAX => hA hAX.1⟩

theorem relativeComplement_disjoint (X A : Class α) :
    Disjoint (Inter A X) (Diff X (Inter A X)) := by
  intro x hAX hDiff
  exact hDiff.2 hAX

/-!
## Manuscript claims SET-001 and SET-003

`SET001Statement` is the relative formulation used for the Mandelbrot class:
the class is first restricted to the chosen ground domain.  `SET003Statement`
is the same membership argument for an arbitrary subtype-like predicate
`A ⊆ X`.  Its type is deliberately polymorphic and requests no dimensional,
topological, metric, or vector-space structure.
-/

def SET001Statement (X A : Class α) : Prop :=
  (Union (Inter A X) (Diff X (Inter A X)) =ₚ X) ∧
  Disjoint (Inter A X) (Diff X (Inter A X))

theorem SET001_checked (X A : Class α) : SET001Statement X A := by
  exact ⟨relativeComplement_complete X A, relativeComplement_disjoint X A⟩

theorem subsetRelativeComplement_complete
    (X A : Class α) (hAX : A ⊆ₚ X) :
    Union A (Diff X A) =ₚ X := by
  classical
  intro x
  constructor
  · rintro (hA | hDiff)
    · exact hAX hA
    · exact hDiff.1
  · intro hX
    by_cases hA : A x
    · exact Or.inl hA
    · exact Or.inr ⟨hX, hA⟩

theorem subsetRelativeComplement_disjoint (X A : Class α) :
    Disjoint A (Diff X A) := by
  intro x hA hDiff
  exact hDiff.2 hA

def SET003Statement (X A : Class α)
    (_manuscriptAssumption : A ⊆ₚ X) : Prop :=
  (Union A (Diff X A) =ₚ X) ∧ Disjoint A (Diff X A)

theorem SET003_checked (X A : Class α) (hAX : A ⊆ₚ X) :
    SET003Statement X A hAX := by
  exact ⟨subsetRelativeComplement_complete X A hAX,
    subsetRelativeComplement_disjoint X A⟩

end Class
end QIKVRT.V2
