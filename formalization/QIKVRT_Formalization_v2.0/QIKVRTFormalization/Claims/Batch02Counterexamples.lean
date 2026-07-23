import QIKVRTFormalization.Quantization.NonDiscreteness
import QIKVRTFormalization.Physics.Lorentz

/-!
# Batch 02: constructive counterexamples

This registry is deliberately independent of Batch 01.  A value of
`Batch02CheckedClaim id statement` contains the kernel-checked proof of the
exact proposition indexed by the public claim identifier.
-/

namespace QIKVRT.V2.Claims

inductive Batch02CounterexampleClaimId where
  | qua003a
  | dim007a
deriving DecidableEq, Repr, BEq

structure CheckedCounterexampleClaim (id : Batch02CounterexampleClaimId)
    (statement : Prop) : Type where
  checked : statement

def batch02CounterexampleClaimIds : List Batch02CounterexampleClaimId :=
  [.qua003a, .dim007a]

theorem batch02CounterexampleClaimIds_count :
    batch02CounterexampleClaimIds.length = 2 := by
  decide

theorem batch02CounterexampleClaimIds_pairwise :
    batch02CounterexampleClaimIds.Pairwise (· ≠ ·) := by
  decide

def QUA003A : CheckedCounterexampleClaim .qua003a QUA003APrefixStatement :=
  ⟨QUA003A_prefix_checked⟩

def DIM007A : CheckedCounterexampleClaim .dim007a DIM007ACountermodelStatement :=
  ⟨DIM007A_countermodel_checked⟩

end QIKVRT.V2.Claims
