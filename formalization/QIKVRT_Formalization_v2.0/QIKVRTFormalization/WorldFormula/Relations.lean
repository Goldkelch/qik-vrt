import Std

/-!
# Executable world-formula relation kernel

This module gives a typed, `Std`-only kernel for the relations required by the
owner delegation. It separates definitional executability, formal derivability,
model satisfaction, reference binding, operationalization, evidence, known-limit
recovery, prediction and independent validation.

No theorem in this module promotes a formal result to a claim about physical
reality without the additional relations required for physical qualification.
-/

namespace QIKVRT.V2.WorldFormula

universe u v w

/-- Stages of the executable epistemic round trip. -/
inductive EpistemicStage where
  | reality
  | difference
  | information
  | relation
  | causalOrder
  | model
  | formalization
  | proofAndPrediction
  | measurement
  | realityComparison
  | newDifference
  deriving DecidableEq, Repr

/-- The deterministic next stage, including the recursive return from a new difference. -/
def successor : EpistemicStage → EpistemicStage
  | .reality => .difference
  | .difference => .information
  | .information => .relation
  | .relation => .causalOrder
  | .causalOrder => .model
  | .model => .formalization
  | .formalization => .proofAndPrediction
  | .proofAndPrediction => .measurement
  | .measurement => .realityComparison
  | .realityComparison => .newDifference
  | .newDifference => .difference

/-- The admissible directed edges of the round-trip architecture. -/
inductive RoundTripStep : EpistemicStage → EpistemicStage → Prop where
  | reality_difference : RoundTripStep .reality .difference
  | difference_information : RoundTripStep .difference .information
  | information_relation : RoundTripStep .information .relation
  | relation_causalOrder : RoundTripStep .relation .causalOrder
  | causalOrder_model : RoundTripStep .causalOrder .model
  | model_formalization : RoundTripStep .model .formalization
  | formalization_proofAndPrediction :
      RoundTripStep .formalization .proofAndPrediction
  | proofAndPrediction_measurement :
      RoundTripStep .proofAndPrediction .measurement
  | measurement_realityComparison :
      RoundTripStep .measurement .realityComparison
  | realityComparison_newDifference :
      RoundTripStep .realityComparison .newDifference
  | newDifference_difference : RoundTripStep .newDifference .difference

/-- The executable successor function produces exactly an admissible round-trip step. -/
theorem successor_is_roundTripStep (stage : EpistemicStage) :
    RoundTripStep stage (successor stage) := by
  cases stage <;> constructor

/-- Every epistemic stage has a constructive next stage. -/
theorem every_stage_has_a_successor (stage : EpistemicStage) :
    ∃ next, RoundTripStep stage next :=
  ⟨successor stage, successor_is_roundTripStep stage⟩

/--
The typed signature of a generative world architecture.

`State` is the state space. The fields keep ontology, fundamental relation,
dynamics, causal structure, emergence, observation and prediction explicit.
-/
structure Architecture (State : Type u) (Observation : Type v) where
  ontology : State → Prop
  fundamentalRelation : State → State → Prop
  dynamics : State → State
  causalStructure : State → State → Prop
  emergence : State → State
  measurement : State → Observation
  prediction : State → Observation

/-- Closure of the declared ontology under dynamics and emergence. -/
def ClosedGenerative {State : Type u} {Observation : Type v}
    (architecture : Architecture State Observation) : Prop :=
  (∀ state, architecture.ontology state →
      architecture.ontology (architecture.dynamics state)) ∧
  (∀ state, architecture.ontology state →
      architecture.ontology (architecture.emergence state))

/--
Repository definition: a closed generative world architecture is an executable
world formula at the architectural-definition level.
-/
def ExecutableWorldFormula {State : Type u} {Observation : Type v}
    (architecture : Architecture State Observation) : Prop :=
  ClosedGenerative architecture

/-- The definitional equivalence does not assert physical correspondence. -/
theorem closedGenerative_iff_executableWorldFormula
    {State : Type u} {Observation : Type v}
    (architecture : Architecture State Observation) :
    ClosedGenerative architecture ↔ ExecutableWorldFormula architecture :=
  Iff.rfl

/-- A finite witness proving consistency of the architectural signature. -/
def unitArchitecture : Architecture Unit Unit where
  ontology := fun _ => True
  fundamentalRelation := fun _ _ => True
  dynamics := fun state => state
  causalStructure := fun _ _ => True
  emergence := fun state => state
  measurement := fun _ => ()
  prediction := fun _ => ()

/-- The finite witness is closed under its declared generators. -/
theorem unitArchitecture_closed : ClosedGenerative unitArchitecture := by
  constructor
  · intro state _
    exact True.intro
  · intro state _
    exact True.intro

/-- The finite witness is an executable world formula under the declared definition. -/
theorem unitArchitecture_executable :
    ExecutableWorldFormula unitArchitecture :=
  unitArchitecture_closed

/-- A claim with an exact identifier, assumptions and proposition. -/
structure FormalClaim where
  id : String
  assumptions : Prop
  statement : Prop

/-- Formal derivability is the implication from declared assumptions to statement. -/
def FormalDerivability (claim : FormalClaim) : Prop :=
  claim.assumptions → claim.statement

/--
The relation family needed to keep proof, model, interpretation, evidence and
provenance obligations distinct.
-/
structure EpistemicRelations (FormalState : Type u)
    (Observable : Type v) (Evidence : Type w) where
  derives : FormalClaim → Prop
  satisfies : FormalState → FormalClaim → Prop
  interprets : FormalState → Observable
  referenceBound : FormalClaim → Prop
  operationalized : FormalClaim → Prop
  evidenceSupports : Evidence → FormalClaim → Prop
  recoversKnownLimit : FormalClaim → Prop
  distinctivePrediction : FormalClaim → Prop
  independentlyValidated : FormalClaim → Prop
  dependsOn : FormalClaim → FormalClaim → Prop
  artifactBound : FormalClaim → Prop

/-- Kernel-level establishment requires derivability, registration and artifact binding. -/
def FormallyEstablished
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    (relations : EpistemicRelations FormalState Observable Evidence)
    (claim : FormalClaim) : Prop :=
  FormalDerivability claim ∧ relations.derives claim ∧
    relations.artifactBound claim

/-- Model establishment additionally requires satisfaction by an explicit model state. -/
def ModelEstablished
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    (relations : EpistemicRelations FormalState Observable Evidence)
    (state : FormalState) (claim : FormalClaim) : Prop :=
  FormallyEstablished relations claim ∧ relations.satisfies state claim

/--
Physical qualification is deliberately stronger than formal establishment. It
requires reference binding, operationalization, evidence, known-limit recovery,
a distinctive prediction and independent validation.
-/
def PhysicallyQualified
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    (relations : EpistemicRelations FormalState Observable Evidence)
    (claim : FormalClaim) : Prop :=
  FormallyEstablished relations claim ∧
  relations.referenceBound claim ∧
  relations.operationalized claim ∧
  (∃ evidence, relations.evidenceSupports evidence claim) ∧
  relations.recoversKnownLimit claim ∧
  relations.distinctivePrediction claim ∧
  relations.independentlyValidated claim

/-- Physical qualification contains, but is not identical to, formal establishment. -/
theorem physicallyQualified_implies_formallyEstablished
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    {relations : EpistemicRelations FormalState Observable Evidence}
    {claim : FormalClaim}
    (qualified : PhysicallyQualified relations claim) :
    FormallyEstablished relations claim :=
  qualified.1

/-- Physical qualification necessarily contains an explicit reference binding. -/
theorem physicallyQualified_implies_referenceBound
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    {relations : EpistemicRelations FormalState Observable Evidence}
    {claim : FormalClaim}
    (qualified : PhysicallyQualified relations claim) :
    relations.referenceBound claim :=
  qualified.2.1

/-- A formally trivial witness used to prove the epistemic non-implication. -/
def witnessClaim : FormalClaim where
  id := "WF-BOUNDARY-WITNESS"
  assumptions := True
  statement := True

/--
A countermodel in which formal and provenance relations hold while every
physical qualification relation is false.
-/
def formalOnlyRelations : EpistemicRelations Unit Unit Unit where
  derives := fun _ => True
  satisfies := fun _ _ => True
  interprets := fun _ => ()
  referenceBound := fun _ => False
  operationalized := fun _ => False
  evidenceSupports := fun _ _ => False
  recoversKnownLimit := fun _ => False
  distinctivePrediction := fun _ => False
  independentlyValidated := fun _ => False
  dependsOn := fun _ _ => False
  artifactBound := fun _ => True

/-- The witness is formally established in the countermodel. -/
theorem witness_formallyEstablished :
    FormallyEstablished formalOnlyRelations witnessClaim := by
  constructor
  · intro _
    exact True.intro
  · constructor
    · exact True.intro
    · exact True.intro

/-- The same witness is not physically qualified in the countermodel. -/
theorem witness_notPhysicallyQualified :
    ¬ PhysicallyQualified formalOnlyRelations witnessClaim := by
  intro qualified
  exact qualified.2.1

/--
Machine-checked counterexample: formal establishment alone is insufficient for
physical qualification.
-/
theorem formalDerivability_not_sufficient_for_physicalQualification :
    FormallyEstablished formalOnlyRelations witnessClaim ∧
      ¬ PhysicallyQualified formalOnlyRelations witnessClaim :=
  ⟨witness_formallyEstablished, witness_notPhysicallyQualified⟩

/-- Exact source, tree, toolchain and artifact identity for a proof receipt. -/
structure ArtifactIdentity where
  sourceCommit : String
  sourceTree : String
  toolchain : String
  artifactSha256 : String

namespace ArtifactIdentity

/-- A complete identity has no empty binding component. -/
def Complete (identity : ArtifactIdentity) : Prop :=
  identity.sourceCommit ≠ "" ∧
  identity.sourceTree ≠ "" ∧
  identity.toolchain ≠ "" ∧
  identity.artifactSha256 ≠ ""

/-- Completeness exposes the exact source-commit binding. -/
theorem complete_implies_sourceCommit
    {identity : ArtifactIdentity} (complete : Complete identity) :
    identity.sourceCommit ≠ "" :=
  complete.1

end ArtifactIdentity

/-- Every declared dependency of an in-scope claim is itself in scope. -/
def DependencyClosed
    {FormalState : Type u} {Observable : Type v} {Evidence : Type w}
    (relations : EpistemicRelations FormalState Observable Evidence)
    (claims : List FormalClaim) : Prop :=
  ∀ claim, claim ∈ claims →
    ∀ dependency, relations.dependsOn claim dependency →
      dependency ∈ claims

end QIKVRT.V2.WorldFormula
