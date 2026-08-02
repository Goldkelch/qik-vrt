import Std

/-!
# QIK-VRT VRTCore candidate

Structural candidate for Lean 4.19.

Scope:
* six non-collapsed epistemic kinds;
* sequence is not silently identified with causality;
* VRT := Rec(D,I,M,W,R,C,A,P);
* componentwise additive preservation;
* technical success and external authorization remain separate;
* a causal claim requires an explicit bridge;
* the Minkowski boundary is admitted only conditionally.

Non-scope:
* no derivation of physical causality;
* no derivation of Minkowski spacetime from quantum dynamics;
* no general Lorentzian emergence theorem;
* no empirical correspondence theorem.

Verification state on 2026-08-02:
CANDIDATE_UNVERIFIED_IN_THIS_RUNTIME.
The runtime exposed neither Lean 4.19.0 nor Lake. No installation was
authorized. This source contains no `sorry`, `admit`, project `axiom`,
`unsafe`, or Mathlib dependency.
-/

namespace QIKVRT
namespace VRTCore

/-- The six epistemic kinds used by this candidate. -/
inductive EpistemicKind where
  | formallyProved
  | empiricallySupported
  | sourceBound
  | normative
  | interpretive
  | unresolved
deriving DecidableEq, Repr, BEq

/-- Text carrying a proof that it is not empty. -/
structure NonemptyText where
  value : String
  nonempty : value ≠ ""

/-- Every claim has exactly one epistemic kind at this layer. -/
structure Claim where
  id : String
  kind : EpistemicKind
  body : NonemptyText

/-- [T01] Every epistemic kind is one of the six declared constructors. -/
theorem epistemicKindExhaustive (kind : EpistemicKind) :
    kind = .formallyProved ∨
    kind = .empiricallySupported ∨
    kind = .sourceBound ∨
    kind = .normative ∨
    kind = .interpretive ∨
    kind = .unresolved := by
  cases kind <;> simp

/-- [T02] A formal proof is not an empirical support status. -/
theorem formalAndEmpiricalAreDistinct :
    EpistemicKind.formallyProved ≠ .empiricallySupported := by
  decide

/-- [T03] Interpretation is not silently collapsed into unresolved status. -/
theorem interpretiveAndUnresolvedAreDistinct :
    EpistemicKind.interpretive ≠ .unresolved := by
  decide

structure Distinction where
  id : String
  left : NonemptyText
  right : NonemptyText

structure Information where
  id : String
  claim : Claim
  provenance : List NonemptyText

structure Measurement where
  id : String
  instrument : NonemptyText
  context : NonemptyText
  uncertainty : NonemptyText

structure ObservedEffect where
  id : String
  inputDescription : NonemptyText
  outputDescription : NonemptyText

inductive RelationKind where
  | observedBefore
  | compatibleWith
  | supports
  | refutes
  | dependsOn
  | causalCandidate
deriving DecidableEq, Repr, BEq

structure Relation where
  id : String
  source : NonemptyText
  target : NonemptyText
  kind : RelationKind

/-
An explicit bridge carries assumptions, a proposed mechanism and a
falsifier. Its construction is a structural certificate only; it does not
prove that the proposed mechanism is physically true.
-/
structure CausalBridge where
  assumptions : List NonemptyText
  assumptionsNonempty : assumptions ≠ []
  mechanism : NonemptyText
  falsifier : NonemptyText

/-
A sequence observation and a bridge-bearing relation are different
constructors.
-/
inductive CausalEvidence where
  | observedSequence (earlier later : NonemptyText)
  | bridgedRelation (relation : Relation) (bridge : CausalBridge)

def causalBridge? : CausalEvidence → Option CausalBridge
  | .observedSequence _ _ => none
  | .bridgedRelation _ bridge => some bridge

/-
This is a syntactic admissibility rule. It is not a theorem that the
licensed relation is physically causal.
-/
def syntacticallyLicensesCausalClaim
    (evidence : CausalEvidence) : Bool :=
  (causalBridge? evidence).isSome

/-- [T04] A sequence carries no causal bridge. -/
theorem observedSequenceHasNoBridge
    (earlier later : NonemptyText) :
    causalBridge? (.observedSequence earlier later) = none := rfl

/-- [T05] A bridged relation exposes the bridge it carries. -/
theorem bridgedRelationHasBridge
    (relation : Relation) (bridge : CausalBridge) :
    causalBridge? (.bridgedRelation relation bridge) = some bridge := rfl

/-- [T06] Temporal or textual sequence alone is not causal licensing. -/
theorem observedSequenceAloneIsNotCausality
    (earlier later : NonemptyText) :
    syntacticallyLicensesCausalClaim
      (.observedSequence earlier later) = false := rfl

/-- [T07] A structurally valid explicit bridge passes the syntax gate. -/
theorem bridgedRelationIsStructurallyLicensed
    (relation : Relation) (bridge : CausalBridge) :
    syntacticallyLicensesCausalClaim
      (.bridgedRelation relation bridge) = true := rfl

/-- [T08] Every positive causal syntax judgement has a bridge. -/
theorem causalLicenseRequiresBridge
    {evidence : CausalEvidence}
    (h : syntacticallyLicensesCausalClaim evidence = true) :
    (causalBridge? evidence).isSome = true := by
  simpa [syntacticallyLicensesCausalClaim] using h

structure TechnicalReceipt where
  exitCode : Nat
  checksPassed : Bool

def technicalSuccess (receipt : TechnicalReceipt) : Bool :=
  receipt.exitCode == 0 && receipt.checksPassed

inductive EffectAuthorization where
  | withheld
  | granted (authority scope : NonemptyText)

def externallyAuthorized : EffectAuthorization → Bool
  | .withheld => false
  | .granted _ _ => true

/-
External mutation requires the conjunction of technical success and
separate authority.
-/
def mayMutateExternally
    (receipt : TechnicalReceipt)
    (authorization : EffectAuthorization) : Bool :=
  technicalSuccess receipt && externallyAuthorized authorization

def successfulReceipt : TechnicalReceipt where
  exitCode := 0
  checksPassed := true

/-- [T09] The canonical success receipt is technically successful. -/
theorem successfulReceiptIsTechnicallySuccessful :
    technicalSuccess successfulReceipt = true := by
  decide

/-- [T10] Withheld authority is not external authorization. -/
theorem withheldAuthorizationIsFalse :
    externallyAuthorized .withheld = false := rfl

/-- [T11] A supplied authority and scope satisfy the authorization gate. -/
theorem grantedAuthorizationIsTrue
    (authority scope : NonemptyText) :
    externallyAuthorized (.granted authority scope) = true := rfl

/-- [T12] Any receipt remains blocked if authority is withheld. -/
theorem withheldAuthorizationBlocksAnyReceipt
    (receipt : TechnicalReceipt) :
    mayMutateExternally receipt .withheld = false := by
  simp [mayMutateExternally, externallyAuthorized]

/-
[T13] Even an explicitly successful receipt remains blocked without
authority.
-/
theorem successfulReceiptStillBlockedWithoutAuthority :
    mayMutateExternally successfulReceipt .withheld = false :=
  withheldAuthorizationBlocksAnyReceipt successfulReceipt

structure Admissibility where
  objectId : String
  admitted : Bool
  rationale : NonemptyText

structure PolicyDecision where
  target : String
  authorization : EffectAuthorization
  rationale : NonemptyText

/-
The eight fields of

  VRT := Rec(D,I,M,W,R,C,A,P)

D = distinctions
I = information
M = measurements
W = observed effects
R = typed relations
C = causal evidence and assessments
A = admissibility decisions
P = policy and effect decisions
-/
structure RecFields where
  D : List Distinction
  I : List Information
  M : List Measurement
  W : List ObservedEffect
  R : List Relation
  C : List CausalEvidence
  A : List Admissibility
  P : List PolicyDecision

def RecFields.empty : RecFields where
  D := []
  I := []
  M := []
  W := []
  R := []
  C := []
  A := []
  P := []

/-- Componentwise additive materialization. -/
def merge (state delta : RecFields) : RecFields where
  D := state.D ++ delta.D
  I := state.I ++ delta.I
  M := state.M ++ delta.M
  W := state.W ++ delta.W
  R := state.R ++ delta.R
  C := state.C ++ delta.C
  A := state.A ++ delta.A
  P := state.P ++ delta.P

/-
A finite recursive history. Each extension adds a further
Rec(D,I,M,W,R,C,A,P) layer.
-/
inductive VRT where
  | seed (fields : RecFields)
  | extend (prior : VRT) (delta : RecFields)

def VRT.materialize : VRT → RecFields
  | .seed fields => fields
  | .extend prior delta => merge (VRT.materialize prior) delta

/-- Componentwise membership preservation. -/
structure Extends (earlier later : RecFields) : Prop where
  preserveD : ∀ x, x ∈ earlier.D → x ∈ later.D
  preserveI : ∀ x, x ∈ earlier.I → x ∈ later.I
  preserveM : ∀ x, x ∈ earlier.M → x ∈ later.M
  preserveW : ∀ x, x ∈ earlier.W → x ∈ later.W
  preserveR : ∀ x, x ∈ earlier.R → x ∈ later.R
  preserveC : ∀ x, x ∈ earlier.C → x ∈ later.C
  preserveA : ∀ x, x ∈ earlier.A → x ∈ later.A
  preserveP : ∀ x, x ∈ earlier.P → x ∈ later.P

/-- [T14] Appending a list preserves every member of its left operand. -/
theorem memAppendLeft {α : Type} (xs ys : List α) :
    ∀ x, x ∈ xs → x ∈ xs ++ ys := by
  intro x hx
  exact List.mem_append.mpr (Or.inl hx)

/-- [T15] Componentwise merging preserves the complete earlier state. -/
theorem mergePreserves (state delta : RecFields) :
    Extends state (merge state delta) where
  preserveD := memAppendLeft state.D delta.D
  preserveI := memAppendLeft state.I delta.I
  preserveM := memAppendLeft state.M delta.M
  preserveW := memAppendLeft state.W delta.W
  preserveR := memAppendLeft state.R delta.R
  preserveC := memAppendLeft state.C delta.C
  preserveA := memAppendLeft state.A delta.A
  preserveP := memAppendLeft state.P delta.P

/-- [T16] Every materialized state extends itself. -/
theorem extendsRefl (state : RecFields) :
    Extends state state where
  preserveD := fun _ hx => hx
  preserveI := fun _ hx => hx
  preserveM := fun _ hx => hx
  preserveW := fun _ hx => hx
  preserveR := fun _ hx => hx
  preserveC := fun _ hx => hx
  preserveA := fun _ hx => hx
  preserveP := fun _ hx => hx

/-- [T17] Additive preservation is transitive. -/
theorem extendsTrans
    {first second third : RecFields}
    (h1 : Extends first second)
    (h2 : Extends second third) :
    Extends first third where
  preserveD := fun x hx => h2.preserveD x (h1.preserveD x hx)
  preserveI := fun x hx => h2.preserveI x (h1.preserveI x hx)
  preserveM := fun x hx => h2.preserveM x (h1.preserveM x hx)
  preserveW := fun x hx => h2.preserveW x (h1.preserveW x hx)
  preserveR := fun x hx => h2.preserveR x (h1.preserveR x hx)
  preserveC := fun x hx => h2.preserveC x (h1.preserveC x hx)
  preserveA := fun x hx => h2.preserveA x (h1.preserveA x hx)
  preserveP := fun x hx => h2.preserveP x (h1.preserveP x hx)

/-- [T18] A seed materializes to its supplied fields. -/
theorem seedMaterializes (state : RecFields) :
    VRT.materialize (.seed state) = state := rfl

/-- [T19] Every recursive VRT step preserves its prior materialization. -/
theorem recursiveStepPreserves
    (prior : VRT) (delta : RecFields) :
    Extends
      (VRT.materialize prior)
      (VRT.materialize (.extend prior delta)) := by
  change Extends
    (VRT.materialize prior)
    (merge (VRT.materialize prior) delta)
  exact mergePreserves _ _

inductive MetricSignature where
  | mostlyPlus
  | mostlyMinus
deriving DecidableEq, Repr, BEq

/-
A supplied witness for the initially scoped four-dimensional Minkowski
boundary. It is not a construction of that boundary from quantum data.
-/
structure MinkowskiWitness where
  dimension : Nat
  dimensionIsFour : dimension = 4
  signatureConvention : MetricSignature
  modelEvidence : NonemptyText

structure ClassicalBoundaryCandidate where
  stable : Bool
  minkowski : Option MinkowskiWitness

def classicalBoundaryAdmissible
    (candidate : ClassicalBoundaryCandidate) : Bool :=
  candidate.stable && candidate.minkowski.isSome

/-
[T20] Conditional only: supplied stability plus a supplied Minkowski
witness pass the structural boundary gate.
-/
theorem suppliedStableMinkowskiWitnessIsAdmissible
    (witness : MinkowskiWitness) :
    classicalBoundaryAdmissible
      { stable := true, minkowski := some witness } = true := rfl

/-- [T21] Stability alone is insufficient without a Minkowski witness. -/
theorem missingMinkowskiWitnessIsRejected
    (stable : Bool) :
    classicalBoundaryAdmissible
      { stable := stable, minkowski := none } = false := by
  cases stable <;> rfl

end VRTCore
end QIKVRT
