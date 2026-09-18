import QIKVRTFormalization.TEMDD.MetaGrammar

namespace QIKVRT.V2.TEMDD
universe u

inductive EpistemicState where
  | trueState | falseState | unknown | conflict | stale | unobservable
  deriving DecidableEq, Repr

structure TemporalOrder where
  sourceOrder : Nat
  observationOrder : Nat
  deriving DecidableEq, Repr

structure TemporalStamp (Stamp : Type u) where
  emittedAt : Stamp
  observedAt : Stamp

def RetrogradeReference (earlier later : TemporalOrder) : Prop :=
  earlier.observationOrder < later.observationOrder ∧ later.sourceOrder < earlier.sourceOrder

def KnowledgeRefines {State : Type u} (before after : KnowledgeRegion State) : Prop :=
  ∀ state, after state → before state

structure ContextBinding (Context Perspective : Type u) where
  context : Context
  perspective : Perspective

def SameContext {Context Perspective : Type u} (before after : ContextBinding Context Perspective) : Prop :=
  before.context = after.context ∧ before.perspective = after.perspective

def ContextTransitionAllowed {Context Perspective : Type u}
    (authorized : ContextBinding Context Perspective → ContextBinding Context Perspective → Prop)
    (before after : ContextBinding Context Perspective) : Prop :=
  SameContext before after ∨ authorized before after

theorem changed_context_requires_authority
    {Context Perspective : Type u}
    (authorized : ContextBinding Context Perspective → ContextBinding Context Perspective → Prop)
    (before after : ContextBinding Context Perspective)
    (changed : ¬ SameContext before after)
    (allowed : ContextTransitionAllowed authorized before after) :
    authorized before after := by
  rcases allowed with same | approved
  · exact False.elim (changed same)
  · exact approved

def EvidenceTransferAllowed {Context Perspective : Type u}
    (before after : ContextBinding Context Perspective) : Prop := SameContext before after

theorem context_drift_denies_evidence_transfer
    {Context Perspective : Type u}
    (before after : ContextBinding Context Perspective)
    (changed : ¬ SameContext before after) :
    ¬ EvidenceTransferAllowed before after := by
  exact changed

structure RelationSubject (Entity Relation Context Perspective : Type u) where
  source : Entity
  relation : Relation
  target : Entity
  context : ContextBinding Context Perspective
  epistemic : EpistemicState

structure SemanticRepresentation
    (Subject Authority Entity Relation Context Perspective : Type u) where
  subject : Subject
  authority : Authority
  relation : RelationSubject Entity Relation Context Perspective
  requiresEffectReadback : Bool

def ConservesRepresentation
    {Subject Authority Entity Relation Context Perspective : Type u}
    (source target : SemanticRepresentation Subject Authority Entity Relation Context Perspective) : Prop :=
  source.subject = target.subject ∧ source.authority = target.authority ∧
  source.relation = target.relation ∧
  source.requiresEffectReadback = target.requiresEffectReadback

theorem identity_conserves_representation
    {Subject Authority Entity Relation Context Perspective : Type u}
    (value : SemanticRepresentation Subject Authority Entity Relation Context Perspective) :
    ConservesRepresentation value value := by
  exact ⟨rfl, rfl, rfl, rfl⟩

end QIKVRT.V2.TEMDD
