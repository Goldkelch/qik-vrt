import Std

/-!
# QIK-VRT Circular Spark Architecture V2

This project binds the finite arithmetic, circular hardware/software phase
ordering, and complete bounded branch-plan selection used by the Motorola 68000
Spark architecture.

The symbolic state cardinality `2^(256^3)` is represented as a base/exponent
pair. It is not enumerated or materialized.
-/

namespace QIKVRT.SparkV2

def controlBits : Nat := 2 ^ 3
def controlStates : Nat := 2 ^ controlBits
def evidenceBits : Nat := 256
def macroRingBits : Nat := evidenceBits ^ 3
def macroRingBytes : Nat := macroRingBits / 8

structure SymbolicCardinality where
  base : Nat
  exponent : Nat
  deriving DecidableEq, Repr

def macroRingStateCardinality : SymbolicCardinality :=
  { base := 2, exponent := macroRingBits }

theorem control_bits_are_eight : controlBits = 8 := by decide
theorem control_states_are_256 : controlStates = 256 := by decide
theorem macro_ring_bits_are_256_cubed :
    macroRingBits = 16777216 := by decide
theorem macro_ring_bytes_are_two_mebibytes :
    macroRingBytes = 2097152 := by decide
theorem macro_state_cardinality_is_symbolic :
    macroRingStateCardinality.base = 2 ∧
    macroRingStateCardinality.exponent = macroRingBits := by
  constructor <;> rfl

inductive StructuralRing where
  | control
  | evidence
  | completion
  deriving DecidableEq, Repr

def nextRing : StructuralRing → StructuralRing
  | .control => .evidence
  | .evidence => .completion
  | .completion => .control

theorem three_structural_rings_cycle (r : StructuralRing) :
    nextRing (nextRing (nextRing r)) = r := by
  cases r <;> rfl

inductive LayerPhase where
  | virtualCompile
  | physicalPlan
  | virtualInterpret
  | physicalClosure
  deriving DecidableEq, Repr

def nextLayer : LayerPhase → LayerPhase
  | .virtualCompile => .physicalPlan
  | .physicalPlan => .virtualInterpret
  | .virtualInterpret => .physicalClosure
  | .physicalClosure => .virtualCompile

def isPhysical : LayerPhase → Bool
  | .virtualCompile => false
  | .physicalPlan => true
  | .virtualInterpret => false
  | .physicalClosure => true

theorem layer_cycle_is_circular (p : LayerPhase) :
    nextLayer (nextLayer (nextLayer (nextLayer p))) = p := by
  cases p <;> rfl

theorem physical_and_virtual_layers_alternate (p : LayerPhase) :
    isPhysical (nextLayer p) = !isPhysical p := by
  cases p <;> rfl

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
    chooseByAuthority o.authorityAvailable
      .materializeToClose .materializeToAuthority
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

theorem plan_is_total (o : BranchObservation) :
    ∃ p, decidePlan o = p := by
  exact ⟨decidePlan o, rfl⟩

theorem malformed_observation_holds
    (o : BranchObservation) (h : o.malformedOrScopeInvalid = true) :
    decidePlan o = .holdInvalid := by
  simp [decidePlan, h]

theorem completion_requires_observed_main_effect
    (o : BranchObservation) (h : decidePlan o = .alreadyComplete) :
    o.malformedOrScopeInvalid = false ∧ o.mainEffectObserved = true := by
  rcases o with ⟨malformed, mainEffect, base, integrity, terminal,
    nonAdverse, mergeable, authority⟩
  cases malformed <;> cases mainEffect <;> cases base <;> cases integrity <;>
    cases terminal <;> cases nonAdverse <;> cases mergeable <;>
    cases authority <;>
    simp [decidePlan, chooseByAuthority] at h ⊢

theorem authority_plan_requires_authority
    (o : BranchObservation) (h : IsAuthorityConsumingPlan (decidePlan o)) :
    o.authorityAvailable = true := by
  rcases o with ⟨malformed, mainEffect, base, integrity, terminal,
    nonAdverse, mergeable, authority⟩
  cases malformed <;> cases mainEffect <;> cases base <;> cases integrity <;>
    cases terminal <;> cases nonAdverse <;> cases mergeable <;>
    cases authority <;>
    simp [decidePlan, chooseByAuthority, IsAuthorityConsumingPlan] at h ⊢

theorem ready_with_authority_selects_complete_merge_ring
    (o : BranchObservation)
    (hMalformed : o.malformedOrScopeInvalid = false)
    (hMain : o.mainEffectObserved = false)
    (hBase : o.baseCurrent = true)
    (hIntegrity : o.integrityCurrent = true)
    (hTerminal : o.gatesTerminal = true)
    (hNonAdverse : o.gatesNonAdverse = true)
    (hMergeable : o.mergeable = true)
    (hAuthority : o.authorityAvailable = true) :
    decidePlan o = .mergeToClose := by
  simp [decidePlan, chooseByAuthority, hMalformed, hMain, hBase, hIntegrity,
    hTerminal, hNonAdverse, hMergeable, hAuthority]

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

end QIKVRT.SparkV2
