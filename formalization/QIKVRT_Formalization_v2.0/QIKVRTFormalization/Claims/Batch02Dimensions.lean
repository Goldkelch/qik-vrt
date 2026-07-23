import QIKVRTFormalization.Physics.Dimensions

/-!
# DIM-006A checked atomic subclaim constructor

This sidecar is intentionally independent of the shared Batch 02 registry so
that the dimension proof can be integrated without changing another batch's
claim IDs or imports.
-/

namespace QIKVRT.V2.Claims

inductive Batch02DimensionsClaimId where
  | dim006a
deriving DecidableEq, Repr, BEq

structure CheckedDimensionsClaim
    (id : Batch02DimensionsClaimId) (statement : Prop) : Type where
  checked : statement

def batch02DimensionsClaimIds : List Batch02DimensionsClaimId :=
  [.dim006a]

theorem batch02DimensionsClaimIds_count :
    batch02DimensionsClaimIds.length = 1 := by
  decide

def DIM006A : CheckedDimensionsClaim .dim006a QIKVRT.V2.DIM006AAdditiveStatement :=
  ⟨QIKVRT.V2.DIM006A_additive_checked⟩

end QIKVRT.V2.Claims
