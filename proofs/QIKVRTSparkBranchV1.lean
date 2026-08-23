import Std

/-!
# QIK-VRT Spark branch work-unit planner

One normalized branch observation is mapped to one complete bounded plan.  The
plan is a repository-control contract, not a claim that Motorola machine code
itself performs GitHub effects.  A host adapter executes the selected plan with
exact-head compare-and-swap and reobservation after every effect.
-/

namespace QIKVRT.SparkV1

inductive SparkPlan where
  | alreadyComplete
  | holdInvalid
  | rebaseToClose
  | rebaseToAuthority
  | materializeToClose
  | materializeToAuthority
  | verifyToClose
  | verifyToAuthority
  | repairToClose
  | repairToAuthority
  | mergeToClose
  | requestAuthority
  deriving DecidableEq, Repr

def SparkPlan.code : SparkPlan → Fin 12
  | .alreadyComplete => 0
  | .holdInvalid => 1
  | .rebaseToClose => 2
  | .rebaseToAuthority => 3
  | .materializeToClose => 4
  | .materializeToAuthority => 5
  | .verifyToClose => 6
  | .verifyToAuthority => 7
  | .repairToClose => 8
  | .repairToAuthority => 9
  | .mergeToClose => 10
  | .requestAuthority => 11

structure BranchObservation where
  malformedOrScopeInvalid : Bool
  mainEffectObserved : Bool
  baseCurrent : Bool
  integrityCurrent : Bool
  gatesTerminal : Bool
  gatesNonAdverse : Bool
  mergeable : Bool
  authorityAvailable : Bool
  deriving DecidableEq, Repr

def chooseByAuthority
    (authority : Bool) (closePlan authorityPlan : SparkPlan) : SparkPlan :=
  if authority = true then closePlan else authorityPlan

def decidePlan (o : BranchObservation) : SparkPlan :=
  if o.malformedOrScopeInvalid = true then .holdInvalid
  else if o.mainEffectObserved = true then .alreadyComplete
  else if o.baseCurrent = false then
    chooseByAuthority o.authorityAvailable .rebaseToClose .rebaseToAuthority
  else if o.integrityCurrent = false then
    chooseByAuthority o.authorityAvailable .materializeToClose .materializeToAuthority
  else if o.gatesTerminal = false then
    chooseByAuthority o.authorityAvailable .verifyToClose .verifyToAuthority
  else if o.gatesNonAdverse = false then
    chooseByAuthority o.authorityAvailable .repairToClose .repairToAuthority
  else if o.mergeable = false then
    chooseByAuthority o.authorityAvailable .repairToClose .repairToAuthority
  else
    chooseByAuthority o.authorityAvailable .mergeToClose .requestAuthority

def IsAuthorityConsumingPlan : SparkPlan → Prop
  | .rebaseToClose
  | .materializeToClose
  | .verifyToClose
  | .repairToClose
  | .mergeToClose => True
  | _ => False

/-- Every observation has one deterministic plan. -/
theorem plan_is_total (o : BranchObservation) :
    ∃ p, decidePlan o = p := by
  exact ⟨decidePlan o, rfl⟩

/-- Malformed or scope-invalid observations fail closed before all other flags. -/
theorem malformed_observation_holds
    (o : BranchObservation) (h : o.malformedOrScopeInvalid = true) :
    decidePlan o = .holdInvalid := by
  simp [decidePlan, h]

/-- Completion requires a well-formed observation of the main effect. -/
theorem completion_requires_observed_main_effect
    (o : BranchObservation) (h : decidePlan o = .alreadyComplete) :
    o.malformedOrScopeInvalid = false ∧ o.mainEffectObserved = true := by
  rcases o with ⟨malformed, mainEffect, base, integrity, terminal,
    nonAdverse, mergeable, authority⟩
  cases malformed <;> cases mainEffect <;> cases base <;> cases integrity <;>
    cases terminal <;> cases nonAdverse <;> cases mergeable <;> cases authority <;>
    simp [decidePlan, chooseByAuthority] at h ⊢

/-- A plan containing the merge edge is never selected without authority. -/
theorem authority_plan_requires_authority
    (o : BranchObservation) (h : IsAuthorityConsumingPlan (decidePlan o)) :
    o.authorityAvailable = true := by
  rcases o with ⟨malformed, mainEffect, base, integrity, terminal,
    nonAdverse, mergeable, authority⟩
  cases malformed <;> cases mainEffect <;> cases base <;> cases integrity <;>
    cases terminal <;> cases nonAdverse <;> cases mergeable <;> cases authority <;>
    simp [decidePlan, chooseByAuthority, IsAuthorityConsumingPlan] at h ⊢

/-- With a ready branch but no authority, the exact result is REQUEST_AUTHORITY. -/
theorem ready_without_authority_requests_authority
    (o : BranchObservation)
    (hMalformed : o.malformedOrScopeInvalid = false)
    (hMain : o.mainEffectObserved = false)
    (hBase : o.baseCurrent = true)
    (hIntegrity : o.integrityCurrent = true)
    (hTerminal : o.gatesTerminal = true)
    (hNonAdverse : o.gatesNonAdverse = true)
    (hMergeable : o.mergeable = true)
    (hAuthority : o.authorityAvailable = false) :
    decidePlan o = .requestAuthority := by
  simp [decidePlan, chooseByAuthority, hMalformed, hMain, hBase, hIntegrity,
    hTerminal, hNonAdverse, hMergeable, hAuthority]

end QIKVRT.SparkV1
