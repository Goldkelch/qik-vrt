import Std

/-!
# Kernel-checked claim wrappers

`CheckedClaim` cannot be constructed without a proof of its indexed
statement.  The claim identifier is data for auditing; logical validity is
carried by the `checked` field and remains under Lean's kernel.
-/

namespace QIKVRT.V2.Claims

inductive Batch01ClaimId where
  | map003
  | gat004
  | gat005
  | gat006
  | ret011
deriving DecidableEq, Repr, BEq

structure CheckedClaim (id : Batch01ClaimId) (statement : Prop) : Type where
  checked : statement

def batch01ClaimIds : List Batch01ClaimId :=
  [.map003, .gat004, .gat005, .gat006, .ret011]

theorem batch01ClaimIds_count : batch01ClaimIds.length = 5 := by
  decide

theorem batch01ClaimIds_pairwise : batch01ClaimIds.Pairwise (· ≠ ·) := by
  decide

end QIKVRT.V2.Claims

