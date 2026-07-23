import Std

/-!
# DIM-007A: a Lorentz-form countermodel to positive distance axioms

This module proves the concrete countermodel subclaim `DIM-007A` in the
decomposition of manuscript claim `DIM-007`.  We use four-dimensional
integer-coordinate events and signature `(-+++)`.  The event `(1,1,0,0)` is
distinct from the origin but null-separated from it, while `(1,0,0,0)` has
strictly negative (indeed, `-1`) squared interval from the origin.  Thus the
Lorentz quadratic form violates two independent necessary conditions for a
positive distance: nonnegativity and separation of distinct points.
-/

namespace QIKVRT.V2

namespace Lorentz

structure Event4 where
  time : Int
  x : Int
  y : Int
  z : Int
deriving DecidableEq, Repr

def separation (start finish : Event4) : Event4 where
  time := finish.time - start.time
  x := finish.x - start.x
  y := finish.y - start.y
  z := finish.z - start.z

/-- Minkowski quadratic form with signature `(-+++)`. -/
def quadraticForm (vector : Event4) : Int :=
  -(vector.time * vector.time) +
    vector.x * vector.x + vector.y * vector.y + vector.z * vector.z

def intervalSquared (left right : Event4) : Int :=
  quadraticForm (separation left right)

def origin : Event4 := ⟨0, 0, 0, 0⟩

def nullEvent : Event4 := ⟨1, 1, 0, 0⟩

def timelikeEvent : Event4 := ⟨1, 0, 0, 0⟩

def Nonnegative (form : Event4 → Event4 → Int) : Prop :=
  ∀ left right, 0 ≤ form left right

def SeparatesPoints (form : Event4 → Event4 → Int) : Prop :=
  ∀ left right, form left right = 0 → left = right

/-- Two necessary axioms of any positive event-distance representation. -/
def PositiveDistanceAxioms (form : Event4 → Event4 → Int) : Prop :=
  Nonnegative form ∧ SeparatesPoints form

theorem null_events_distinct : origin ≠ nullEvent := by
  decide

theorem distinct_null_separation :
    intervalSquared origin nullEvent = 0 := by
  decide

theorem timelike_interval_exact :
    intervalSquared origin timelikeEvent = -1 := by
  decide

theorem timelike_interval_negative :
    intervalSquared origin timelikeEvent < 0 := by
  decide

theorem intervalSquared_not_nonnegative :
    ¬ Nonnegative intervalSquared := by
  intro hNonnegative
  have hAtTimelike := hNonnegative origin timelikeEvent
  have hNegative := timelike_interval_negative
  omega

theorem intervalSquared_does_not_separate :
    ¬ SeparatesPoints intervalSquared := by
  intro hSeparates
  have hEqual := hSeparates origin nullEvent distinct_null_separation
  exact null_events_distinct hEqual

theorem intervalSquared_not_positive_distance :
    ¬ PositiveDistanceAxioms intervalSquared := by
  intro hPositive
  exact intervalSquared_not_nonnegative hPositive.1

end Lorentz

open Lorentz

/--
The exact machine-checkable content of atomic subclaim `DIM-007A`: explicit integer-coordinate
null and timelike event pairs violate, respectively, point separation and
nonnegativity, hence the Lorentz squared interval cannot be a positive
distance on events.

The parent claim about the standard real affine spacetime remains pending
until these witnesses are transported through an explicit integer-to-real
embedding in the mathlib-backed tranche.
-/
def DIM007ACountermodelStatement : Prop :=
  origin ≠ nullEvent ∧
  intervalSquared origin nullEvent = 0 ∧
  intervalSquared origin timelikeEvent = -1 ∧
  intervalSquared origin timelikeEvent < 0 ∧
  ¬ Nonnegative intervalSquared ∧
  ¬ SeparatesPoints intervalSquared ∧
  ¬ PositiveDistanceAxioms intervalSquared

theorem DIM007A_countermodel_checked : DIM007ACountermodelStatement := by
  exact ⟨null_events_distinct, distinct_null_separation,
    timelike_interval_exact, timelike_interval_negative,
    intervalSquared_not_nonnegative, intervalSquared_does_not_separate,
    intervalSquared_not_positive_distance⟩

end QIKVRT.V2
