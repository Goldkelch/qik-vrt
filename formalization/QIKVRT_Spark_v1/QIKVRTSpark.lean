import Std

/-!
# QIK-VRT virtual Spark branch-work kernel

One Spark pass consumes one already admitted finite branch-work capsule. The
formal result is a four-state local decision plus completion/activity witnesses;
it is not a Git merge, network effect or physical timing claim.
-/

namespace QIKVRT.Spark.V1

inductive Decision where
  | noop
  | hold
  | reobserve
  | requestAuthority
  deriving DecidableEq, Repr

def Decision.code : Decision → Fin 4
  | .noop => 0
  | .hold => 1
  | .reobserve => 2
  | .requestAuthority => 3

structure BranchFlags where
  implemented : Bool
  verified : Bool
  persisted : Bool
  reobserved : Bool
  staleEvidence : Bool
  authorityRequired : Bool
  authorityPresent : Bool
  unclassified : Bool
  deriving DecidableEq, Repr

def BranchFlags.allReady (f : BranchFlags) : Bool :=
  f.implemented && f.verified && f.persisted && f.reobserved

/-- Priority is fail-closed: unclassified, stale and missing-authority states
are resolved before a complete local work ring can return NOOP. -/
def branchDecision (f : BranchFlags) : Decision :=
  if f.unclassified = true then .hold
  else if f.staleEvidence = true then .reobserve
  else if f.authorityRequired = true && f.authorityPresent = false then .requestAuthority
  else if f.allReady = true then .noop
  else .reobserve

structure Projection where
  decision : Decision
  complete : Bool
  active : Bool
  d3 : Fin 256
  deriving DecidableEq, Repr

/-- D1 is the completion witness; D2 is active only for machine-owned
reobservation; D3 is copied byte-identically. -/
def project (f : BranchFlags) (d3 : Fin 256) : Projection :=
  let d := branchDecision f
  { decision := d
    complete := decide (d = .noop)
    active := decide (d = .reobserve)
    d3 := d3 }

theorem decision_code_abi :
    Decision.noop.code = 0 ∧
    Decision.hold.code = 1 ∧
    Decision.reobserve.code = 2 ∧
    Decision.requestAuthority.code = 3 := by decide

theorem projection_preserves_d3 (f : BranchFlags) (d3 : Fin 256) :
    (project f d3).d3 = d3 := rfl

def completeFlags : BranchFlags :=
  { implemented := true, verified := true, persisted := true, reobserved := true
    staleEvidence := false, authorityRequired := false, authorityPresent := false
    unclassified := false }

def staleFlags : BranchFlags :=
  { completeFlags with staleEvidence := true }

def authorityFlags : BranchFlags :=
  { completeFlags with authorityRequired := true, authorityPresent := false }

def unclassifiedFlags : BranchFlags :=
  { completeFlags with unclassified := true }

def incompleteFlags : BranchFlags :=
  { completeFlags with persisted := false, reobserved := false }

/-- One admitted complete capsule closes one bounded work ring in one pass. -/
theorem one_spark_pass_closes_complete_capsule (d3 : Fin 256) :
    project completeFlags d3 =
      { decision := .noop, complete := true, active := false, d3 := d3 } := rfl

theorem stale_capsule_requires_reobservation (d3 : Fin 256) :
    project staleFlags d3 =
      { decision := .reobserve, complete := false, active := true, d3 := d3 } := rfl

theorem missing_authority_requests_authority (d3 : Fin 256) :
    project authorityFlags d3 =
      { decision := .requestAuthority, complete := false, active := false, d3 := d3 } := rfl

theorem unclassified_capsule_holds_fail_closed (d3 : Fin 256) :
    project unclassifiedFlags d3 =
      { decision := .hold, complete := false, active := false, d3 := d3 } := rfl

theorem incomplete_machine_owned_capsule_remains_active (d3 : Fin 256) :
    project incompleteFlags d3 =
      { decision := .reobserve, complete := false, active := true, d3 := d3 } := rfl

end QIKVRT.Spark.V1
