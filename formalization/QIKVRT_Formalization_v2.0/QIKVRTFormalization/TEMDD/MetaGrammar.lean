import QIKVRTFormalization.TEMDD.Completion

/-!
# TEMDD meta-grammar kernel

This module gives a deliberately definition-relative formal meaning to the
claim that TEMDD is a meta-grammar.  A meta-grammar here is not an assertion
that every future claim, model, or physical law is already decided.  It is a
typed syntax with an explicit interpretation discipline such that every
declared conservative extension preserves the meaning of embedded TEMDD
formulas under restriction of its interpretation.

The completion lifting theorem below is separate from formula preservation.
It shows which explicit preservation and reflection premises are sufficient to
carry the `Done` predicate from one state model to an extended state model.
-/

namespace QIKVRT.V2.TEMDD

universe u v w x

/-- A vocabulary whose primitive symbols are indexed by a declared sort. -/
structure TypedVocabulary where
  Sort : Type u
  Symbol : Sort → Type u

/-- Propositional formulas over a typed vocabulary. -/
inductive Formula (V : TypedVocabulary.{u}) : Type u where
  | atom : {sort : V.Sort} → V.Symbol sort → Formula V
  | truth : Formula V
  | falsity : Formula V
  | conjunction : Formula V → Formula V → Formula V
  | disjunction : Formula V → Formula V → Formula V
  | implication : Formula V → Formula V → Formula V
  | negation : Formula V → Formula V

/-- A sort-respecting map from one vocabulary into another. -/
structure VocabularyEmbedding
    (source : TypedVocabulary.{u})
    (target : TypedVocabulary.{v}) where
  mapSort : source.Sort → target.Sort
  mapSymbol : ∀ {sort : source.Sort},
    source.Symbol sort → target.Symbol (mapSort sort)

/--
The sorts of an extension: inherited source sorts remain distinct from one
fresh sort whose primitive symbols have the payload type.
-/
inductive ExtensionSort
    (source : TypedVocabulary.{u})
    (payload : Type v) : Type (max u v) where
  | inherited : source.Sort → ExtensionSort source payload
  | extension : ExtensionSort source payload

/--
Extend a vocabulary by one separate sort whose symbols are values of
`payload`.  Existing source symbols retain their original sort and type.
-/
def extend
    (source : TypedVocabulary.{u})
    (payload : Type v) : TypedVocabulary.{max u v} where
  Sort := ExtensionSort source payload
  Symbol := fun sort =>
    match sort with
    | .inherited inheritedSort => source.Symbol inheritedSort
    | .extension => payload

/-- The canonical inclusion of every source sort and symbol into `extend`. -/
def inclusion
    (source : TypedVocabulary.{u})
    (payload : Type v) :
    VocabularyEmbedding source (extend source payload) where
  mapSort := ExtensionSort.inherited
  mapSymbol := fun symbol => symbol

namespace Formula

/-- Embed a source formula into a target vocabulary by mapping every atom. -/
def embed
    {source : TypedVocabulary.{u}}
    {target : TypedVocabulary.{v}}
    (embedding : VocabularyEmbedding source target) :
    Formula source → Formula target
  | .atom symbol => .atom (embedding.mapSymbol symbol)
  | .truth => .truth
  | .falsity => .falsity
  | .conjunction left right =>
      .conjunction (embed embedding left) (embed embedding right)
  | .disjunction left right =>
      .disjunction (embed embedding left) (embed embedding right)
  | .implication antecedent consequent =>
      .implication (embed embedding antecedent) (embed embedding consequent)
  | .negation inner => .negation (embed embedding inner)

end Formula

/-- An interpretation assigns a proposition to each well-typed primitive. -/
abbrev Interpretation (V : TypedVocabulary.{u}) :=
  ∀ {sort : V.Sort}, V.Symbol sort → Prop

namespace Formula

/-- Satisfaction of a formula under an interpretation. -/
def Holds
    {V : TypedVocabulary.{u}}
    (interpretation : Interpretation V) :
    Formula V → Prop
  | .atom symbol => interpretation symbol
  | .truth => True
  | .falsity => False
  | .conjunction left right => Holds interpretation left ∧ Holds interpretation right
  | .disjunction left right => Holds interpretation left ∨ Holds interpretation right
  | .implication antecedent consequent =>
      Holds interpretation antecedent → Holds interpretation consequent
  | .negation inner => ¬ Holds interpretation inner

end Formula

/-- Restrict a target interpretation along a vocabulary embedding. -/
def restrictInterpretation
    {source : TypedVocabulary.{u}}
    {target : TypedVocabulary.{v}}
    (embedding : VocabularyEmbedding source target)
    (interpretation : Interpretation target) :
    Interpretation source :=
  fun {sort} symbol => interpretation (embedding.mapSymbol symbol)

/-- Formula embedding preserves meaning under the corresponding restriction. -/
theorem formula_embedding_preserves_interpretation
    {source : TypedVocabulary.{u}}
    {target : TypedVocabulary.{v}}
    (embedding : VocabularyEmbedding source target)
    (interpretation : Interpretation target) :
    ∀ formula : Formula source,
      Formula.Holds (restrictInterpretation embedding interpretation) formula ↔
        Formula.Holds interpretation (Formula.embed embedding formula) := by
  intro formula
  induction formula with
  | atom symbol =>
      rfl
  | truth =>
      rfl
  | falsity =>
      rfl
  | conjunction left right leftIH rightIH =>
      constructor
      · intro h
        exact ⟨leftIH.mp h.1, rightIH.mp h.2⟩
      · intro h
        exact ⟨leftIH.mpr h.1, rightIH.mpr h.2⟩
  | disjunction left right leftIH rightIH =>
      constructor
      · intro h
        cases h with
        | inl hLeft => exact Or.inl (leftIH.mp hLeft)
        | inr hRight => exact Or.inr (rightIH.mp hRight)
      · intro h
        cases h with
        | inl hLeft => exact Or.inl (leftIH.mpr hLeft)
        | inr hRight => exact Or.inr (rightIH.mpr hRight)
  | implication antecedent consequent antecedentIH consequentIH =>
      constructor
      · intro h hAntecedent
        exact consequentIH.mp (h (antecedentIH.mpr hAntecedent))
      · intro h hAntecedent
        exact consequentIH.mpr (h (antecedentIH.mp hAntecedent))
  | negation inner innerIH =>
      constructor
      · intro h hInner
        exact h (innerIH.mpr hInner)
      · intro h hInner
        exact h (innerIH.mp hInner)

/--
An extension is conservative when it carries an explicit embedding and proves
that the target interpretation restricts to the source interpretation on every
source formula.
-/
structure ConservativeExtension
    (source : TypedVocabulary.{u})
    (target : TypedVocabulary.{v}) where
  embedding : VocabularyEmbedding source target
  restriction_preserves :
    ∀ (interpretation : Interpretation target) (formula : Formula source),
      Formula.Holds (restrictInterpretation embedding interpretation) formula ↔
        Formula.Holds interpretation (Formula.embed embedding formula)

/-- Every sort-respecting vocabulary embedding supplies a conservative extension. -/
def canonicalConservativeExtension
    {source : TypedVocabulary.{u}}
    {target : TypedVocabulary.{v}}
    (embedding : VocabularyEmbedding source target) :
    ConservativeExtension source target where
  embedding := embedding
  restriction_preserves := formula_embedding_preserves_interpretation embedding

/-- The conservative extension constructed for an arbitrary payload type. -/
def payloadExtension
    (source : TypedVocabulary.{u})
    (payload : Type v) :
    ConservativeExtension source (extend source payload) :=
  canonicalConservativeExtension (inclusion source payload)

/--
Every payload type can be introduced as a separate extension sort while the
source vocabulary is retained by the canonical inclusion.
-/
theorem arbitrary_payload_has_conservative_extension
    (source : TypedVocabulary.{u})
    (payload : Type v) :
    ∃ extension : ConservativeExtension source (extend source payload),
      extension.embedding = inclusion source payload := by
  exact ⟨payloadExtension source payload, rfl⟩

/--
Embedding into the arbitrary-payload extension preserves evaluation of every
formula written in the source vocabulary.
-/
theorem arbitrary_payload_extension_preserves_source_formula
    (source : TypedVocabulary.{u})
    (payload : Type v)
    (interpretation : Interpretation (extend source payload))
    (formula : Formula source) :
    Formula.Holds (restrictInterpretation (inclusion source payload) interpretation) formula ↔
      Formula.Holds interpretation
        (Formula.embed (inclusion source payload) formula) := by
  exact formula_embedding_preserves_interpretation
    (inclusion source payload) interpretation formula

/-- Any explicitly declared conservative extension preserves every source formula. -/
theorem arbitrary_conservative_extension
    {source : TypedVocabulary.{u}}
    {target : TypedVocabulary.{v}}
    (extension : ConservativeExtension source target)
    (interpretation : Interpretation target)
    (formula : Formula source) :
    Formula.Holds (restrictInterpretation extension.embedding interpretation) formula ↔
      Formula.Holds interpretation (Formula.embed extension.embedding formula) := by
  exact extension.restriction_preserves interpretation formula

/--
Definition-relative meta-grammar property: the source grammar is preserved by
every explicitly represented conservative extension into the given target
vocabulary.
-/
def IsMetaGrammar
    (source : TypedVocabulary.{u})
    (target : TypedVocabulary.{v}) : Prop :=
  ∀ (extension : ConservativeExtension source target)
      (interpretation : Interpretation target)
      (formula : Formula source),
    Formula.Holds (restrictInterpretation extension.embedding interpretation) formula ↔
      Formula.Holds interpretation (Formula.embed extension.embedding formula)

/-- TEMDD's six primary domains as sorts in its core vocabulary. -/
inductive TEMDDSort where
  | state
  | evidence
  | requirement
  | action
  | model
  | authority

/-- A minimal typed core vocabulary for TEMDD's primary domains. -/
inductive TEMDDPrimitive : TEMDDSort → Type where
  | observedState : TEMDDPrimitive .state
  | boundEvidence : TEMDDPrimitive .evidence
  | completion : TEMDDPrimitive .evidence
  | requirementContract : TEMDDPrimitive .requirement
  | permittedAction : TEMDDPrimitive .action
  | worldModel : TEMDDPrimitive .model
  | authorizedCapability : TEMDDPrimitive .authority

/-- The typed vocabulary used by the TEMDD meta-grammar theorem. -/
def TEMDDVocabulary : TypedVocabulary where
  Sort := TEMDDSort
  Symbol := TEMDDPrimitive

/-- The core formula naming a completion claim. -/
def completionFormula : Formula TEMDDVocabulary :=
  Formula.atom TEMDDPrimitive.completion

/-- Every declared conservative extension preserves the TEMDD core language. -/
theorem temdd_is_a_metagrammar
    (target : TypedVocabulary.{u}) :
    IsMetaGrammar TEMDDVocabulary target := by
  intro extension interpretation formula
  exact arbitrary_conservative_extension extension interpretation formula

/-- The completion formula has the same meaning after any conservative extension. -/
theorem completion_formula_lift
    (target : TypedVocabulary.{u})
    (extension : ConservativeExtension TEMDDVocabulary target)
    (interpretation : Interpretation target) :
    Formula.Holds
        (restrictInterpretation extension.embedding interpretation)
        completionFormula ↔
      Formula.Holds interpretation
        (Formula.embed extension.embedding completionFormula) := by
  exact arbitrary_conservative_extension extension interpretation completionFormula

/--
`Done` lifts to an extended state model when the extended knowledge region is
both covered by, and reflects back into, the mapped source knowledge region,
and the requirement is preserved by the state map.
-/
theorem completion_lift
    {State : Type u}
    {LiftedState : Type v}
    {Subject : Type w}
    {LiftedSubject : Type x}
    (stateMap : State → LiftedState)
    (subjectMap : Subject → LiftedSubject)
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (liftedR : Requirement LiftedState)
    (liftedK : KnowledgeRegion LiftedState)
    (evidenceSubject actualSubject : Subject)
    (actual : State)
    (hDone : Done R K evidenceSubject actualSubject actual)
    (hKMap : ∀ state, K state → liftedK (stateMap state))
    (hKReflect : ∀ liftedState, liftedK liftedState →
      ∃ state, K state ∧ stateMap state = liftedState)
    (hRMap : ∀ state, R state → liftedR (stateMap state)) :
    Done liftedR liftedK
      (subjectMap evidenceSubject) (subjectMap actualSubject) (stateMap actual) := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · rcases hDone.1 with ⟨state, hState⟩
    exact ⟨stateMap state, hKMap state hState⟩
  · intro liftedState hLiftedState
    rcases hKReflect liftedState hLiftedState with ⟨state, hState, hMap⟩
    rw [← hMap]
    exact hRMap state (hDone.2.1 state hState)
  · exact congrArg subjectMap hDone.2.2.1
  · exact hKMap actual hDone.2.2.2

end QIKVRT.V2.TEMDD
