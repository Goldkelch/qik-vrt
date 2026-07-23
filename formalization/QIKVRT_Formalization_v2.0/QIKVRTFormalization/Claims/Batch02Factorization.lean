import QIKVRTFormalization.Process.Factorization

/-!
# GAT-002 checked claim wrapper

The indexed wrapper can be constructed only from a kernel proof of the exact
GAT-002 statement.  It is intentionally independent of the other Batch 02
registries so those files need not be changed by this proof tranche.
-/

namespace QIKVRT.V2.Claims

universe u v

inductive FactorizationClaimId where
  | gat002
deriving DecidableEq, Repr, BEq

structure CheckedFactorizationClaim
    (id : FactorizationClaimId) (statement : Prop) : Type where
  checked : statement

def GAT002
    {SourceTrajectory : Type u} {TargetTrajectory : Type v}
    (trajectoryMap : SourceTrajectory → TargetTrajectory)
    (sourceGate : SourceTrajectory → Gate) :
    CheckedFactorizationClaim .gat002
      (GAT002Statement trajectoryMap sourceGate) :=
  ⟨GAT002_checked trajectoryMap sourceGate⟩

end QIKVRT.V2.Claims
