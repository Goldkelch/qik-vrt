import Std

/-!
# DIM-006A: dimension-safe addition of quantities

This module formalizes atomic subclaim `DIM-006A`, the additive fragment of
manuscript claim `DIM-006`
(TeX lines 1483--1488).  A `Quantity` carries its dimension as a type index,
so its ordinary `Add` operation can only receive operands with the same
dimension and returns a quantity with that dimension.  `PackedQuantity` is
the corresponding run-time representation; `addChecked` is defined exactly
when its two dimensions agree.

The result is a typing and representation invariant.  It does not assert an
empirical law of nature, dimensional sufficiency, or the manuscript's
separate condition about arguments of transcendental functions.
-/

namespace QIKVRT.V2

namespace Physics

universe u

/-- Exponents of the seven SI base dimensions. -/
structure Dimension where
  lengthExp : Int
  timeExp : Int
  massExp : Int
  temperatureExp : Int
  currentExp : Int
  amountExp : Int
  luminousIntensityExp : Int
deriving DecidableEq, Repr

/-- The dimension vector whose seven base exponents are zero. -/
def dimensionless : Dimension where
  lengthExp := 0
  timeExp := 0
  massExp := 0
  temperatureExp := 0
  currentExp := 0
  amountExp := 0
  luminousIntensityExp := 0

/-- A scalar magnitude indexed by its physical dimension. -/
structure Quantity (Scalar : Type u) (dimension : Dimension) where
  magnitude : Scalar

/-- Addition internal to one dimension-indexed quantity type. -/
def Quantity.addSameDimension [Add Scalar]
    {dimension : Dimension}
    (left right : Quantity Scalar dimension) : Quantity Scalar dimension :=
  ⟨left.magnitude + right.magnitude⟩

instance [Add Scalar] : Add (Quantity Scalar dimension) where
  add := Quantity.addSameDimension

/-- Recover the phantom dimension index as a value. -/
def Quantity.dimensionOf {dimension : Dimension}
    (_quantity : Quantity Scalar dimension) : Dimension :=
  dimension

/-- Dimension-indexed addition preserves its common dimension by typing. -/
theorem Quantity.dimensionOf_add [Add Scalar]
    {dimension : Dimension}
    (left right : Quantity Scalar dimension) :
    Quantity.dimensionOf (left + right) = dimension := by
  rfl

/-- A run-time package used when the dimension is not known statically. -/
structure PackedQuantity (Scalar : Type u) where
  dimension : Dimension
  magnitude : Scalar

/--
Run-time checked addition.  Unequal dimensions return `none`; equal
dimensions return a package carrying the shared dimension.
-/
def PackedQuantity.addChecked [Add Scalar]
    (left right : PackedQuantity Scalar) : Option (PackedQuantity Scalar) :=
  if left.dimension = right.dimension then
    some ⟨left.dimension, left.magnitude + right.magnitude⟩
  else
    none

/-- `addChecked` is defined when it produces a result package. -/
def PackedQuantity.AddDefined [Add Scalar]
    (left right : PackedQuantity Scalar) : Prop :=
  ∃ result, PackedQuantity.addChecked left right = some result

theorem PackedQuantity.addChecked_some_implies_dimensions [Add Scalar]
    {left right result : PackedQuantity Scalar}
    (hResult : PackedQuantity.addChecked left right = some result) :
    left.dimension = right.dimension ∧
      result.dimension = left.dimension := by
  by_cases hDimension : left.dimension = right.dimension
  · rw [PackedQuantity.addChecked, if_pos hDimension] at hResult
    constructor
    · exact hDimension
    · injection hResult with hResultEqual
      cases hResultEqual
      rfl
  · rw [PackedQuantity.addChecked, if_neg hDimension] at hResult
    cases hResult

theorem PackedQuantity.addChecked_exists_of_sameDimension [Add Scalar]
    {left right : PackedQuantity Scalar}
    (hDimension : left.dimension = right.dimension) :
    ∃ result,
      PackedQuantity.addChecked left right = some result ∧
      result.dimension = left.dimension := by
  let result : PackedQuantity Scalar :=
    ⟨left.dimension, left.magnitude + right.magnitude⟩
  refine ⟨result, ?_, rfl⟩
  rw [PackedQuantity.addChecked, if_pos hDimension]

/-- Checked addition is defined exactly for equal dimensions. -/
theorem PackedQuantity.addDefined_iff_sameDimension [Add Scalar]
    (left right : PackedQuantity Scalar) :
    PackedQuantity.AddDefined left right ↔
      left.dimension = right.dimension := by
  constructor
  · rintro ⟨result, hResult⟩
    exact (PackedQuantity.addChecked_some_implies_dimensions hResult).1
  · intro hDimension
    rcases PackedQuantity.addChecked_exists_of_sameDimension hDimension with
      ⟨result, hResult, _hResultDimension⟩
    exact ⟨result, hResult⟩

/-- Any successful checked sum carries the shared input dimension. -/
theorem PackedQuantity.addChecked_preserves_dimension [Add Scalar]
    {left right result : PackedQuantity Scalar}
    (hResult : PackedQuantity.addChecked left right = some result) :
    result.dimension = left.dimension :=
  (PackedQuantity.addChecked_some_implies_dimensions hResult).2

end Physics

open Physics

universe u

/--
Exact checked content of atomic subclaim `DIM-006A`: statically
typed addition preserves its dimension; dynamically checked addition is
defined exactly for equal dimensions; and every successful result carries
that shared dimension.

The parent manuscript claim `DIM-006` also asserts necessity from unit-scaling
invariance and dimensionless arguments for exp/log/sin/cos.  Those obligations
remain pending and are not implied by this checked API invariant.
-/
def DIM006AAdditiveStatement : Prop :=
  (forall (Scalar : Type u) [Add Scalar]
      (dimension : Dimension)
      (left right : Quantity Scalar dimension),
    Quantity.dimensionOf (left + right) = dimension) ∧
  (forall (Scalar : Type u) [Add Scalar]
      (left right : PackedQuantity Scalar),
    PackedQuantity.AddDefined left right ↔
      left.dimension = right.dimension) ∧
  (forall (Scalar : Type u) [Add Scalar]
      (left right result : PackedQuantity Scalar),
    PackedQuantity.addChecked left right = some result →
      result.dimension = left.dimension)

theorem DIM006A_additive_checked : DIM006AAdditiveStatement := by
  refine ⟨?_, ?_, ?_⟩
  · intro Scalar _instance dimension left right
    exact Quantity.dimensionOf_add left right
  · intro Scalar _instance left right
    exact PackedQuantity.addDefined_iff_sameDimension left right
  · intro Scalar _instance left right result hResult
    exact PackedQuantity.addChecked_preserves_dimension hResult

end QIKVRT.V2
