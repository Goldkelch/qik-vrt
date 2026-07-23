import QIKVRTFormalization.Foundation.Preimage

/-!
# Batch 02 checked claim constructors

The registry below is independent of Batch 01.  Each constructor carries the
kernel proof of the exact proposition indexed by its manuscript claim ID.
-/

namespace QIKVRT.V2.Claims

universe u v

inductive Batch02ClaimId where
  | set001
  | set003
  | map001
deriving DecidableEq, Repr, BEq

structure CheckedClaim02 (id : Batch02ClaimId) (statement : Prop) : Type where
  checked : statement

def batch02ClaimIds : List Batch02ClaimId :=
  [.set001, .set003, .map001]

theorem batch02ClaimIds_count : batch02ClaimIds.length = 3 := by
  decide

theorem batch02ClaimIds_pairwise : batch02ClaimIds.Pairwise (· ≠ ·) := by
  decide

def SET001 (X A : Class α) :
    CheckedClaim02 .set001 (Class.SET001Statement X A) :=
  ⟨Class.SET001_checked X A⟩

def SET003 (X A : Class α) (hAX : A ⊆ₚ X) :
    CheckedClaim02 .set003 (Class.SET003Statement X A hAX) :=
  ⟨Class.SET003_checked X A hAX⟩

def MAP001
    (f : α → β) (U A : Class β) (htotal : Class.TotalInto f U) :
    CheckedClaim02 .map001 (Class.MAP001Statement f U A htotal) :=
  ⟨Class.MAP001_checked f U A htotal⟩

end QIKVRT.V2.Claims
