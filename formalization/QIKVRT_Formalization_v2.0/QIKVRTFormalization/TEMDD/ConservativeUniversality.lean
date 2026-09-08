import QIKVRTFormalization.TEMDD.Completion

/-!
# TEMDD conservative universality / semantic embedding metatheory

This module is an additive layer over TEMDD Language 1.0.  It does not alter
`Completion.Done`, subject binding, mutation invalidation, or any repository
completion/effect boundary.

The strong U3 universality statement is represented as an explicit proposition.
It is deliberately *not* proved here.  In particular this file introduces no
`axiom` and no `sorry` to manufacture universality.  The remaining proof burden
is the independently specified admissible class and a construction of a
conservative embedding for every member of that class.
-/

namespace QIKVRT.V2.TEMDD.ConservativeUniversality

universe uS uR uE uA uU uSub
universe vS vR vE vA vU vSub

/--
A source language exposes exactly the semantic surfaces relevant to the U3
claim: states, exact subjects, requirements, evidence, actions, authority,
satisfaction, binding, transitions, completion, and an evidence-strength
ordering.
-/
structure SourceLanguage where
  State : Type uS
  Subject : Type uSub
  Requirement : Type uR
  Evidence : Type uE
  Action : Type uA
  Authority : Type uU
  Satisfies : State → Requirement → Prop
  Bound : Evidence → Subject → Prop
  Step : State → Action → State → Prop
  Done : Requirement → Evidence → Subject → State → Prop
  ClaimStrength : Evidence → Nat
  Authorized : Authority → Action → Prop

/--
A semantic view of the target TEMDD layer used by the metatheorem.

The concrete Language 1.0 completion calculus is intentionally not replaced by
this interface.  A future instantiation must show that its `Done`, `Bound`, and
other fields are the intended TEMDD semantics rather than a weakened surrogate.
-/
structure TargetLanguage where
  State : Type vS
  Subject : Type vSub
  Requirement : Type vR
  Evidence : Type vE
  Action : Type vA
  Authority : Type vU
  Satisfies : State → Requirement → Prop
  Bound : Evidence → Subject → Prop
  Step : State → Action → State → Prop
  Reachable : State → Action → State → Prop
  Done : Requirement → Evidence → Subject → State → Prop
  ClaimStrength : Evidence → Nat
  Authorized : Authority → Action → Prop

/-- A conservative semantic embedding from one source language into TEMDD. -/
structure ConservativeEmbedding
    (L : SourceLanguage)
    (T : TargetLanguage) where
  mapState : L.State → T.State
  mapSubject : L.Subject → T.Subject
  mapRequirement : L.Requirement → T.Requirement
  mapEvidence : L.Evidence → T.Evidence
  mapAction : L.Action → T.Action
  mapAuthority : L.Authority → T.Authority

  /-- Requirement semantics is preserved and reflected on the embedding image. -/
  requirement_preserved :
    ∀ s r,
      L.Satisfies s r ↔
        T.Satisfies (mapState s) (mapRequirement r)

  /-- Exact evidence/subject binding is preserved and reflected. -/
  binding_preserved :
    ∀ e σ,
      L.Bound e σ ↔
        T.Bound (mapEvidence e) (mapSubject σ)

  /-- Distinct source subjects remain distinct target subjects. -/
  injective_subject :
    ∀ ⦃σ σ'⦄,
      mapSubject σ = mapSubject σ' → σ = σ'

  /-- Translation cannot increase the declared evidence strength. -/
  evidence_non_amplifying :
    ∀ e,
      T.ClaimStrength (mapEvidence e) ≤ L.ClaimStrength e

  /-- Every source transition has an admissible target simulation path. -/
  transition_preserved :
    ∀ s a s',
      L.Step s a s' →
        T.Reachable (mapState s) (mapAction a) (mapState s')

  /-- Source authority may not be weakened by translation. -/
  authority_preserved :
    ∀ authority action,
      T.Authorized (mapAuthority authority) (mapAction action) →
        L.Authorized authority action

  /--
  Central conservative reflection direction: target completion for an embedded
  source subject cannot manufacture source completion.
  -/
  completion_reflected :
    ∀ r e σ s,
      T.Done
          (mapRequirement r)
          (mapEvidence e)
          (mapSubject σ)
          (mapState s) →
        L.Done r e σ s

/--
A stronger embedding is completion-complete in the opposite direction as well.
This is intentionally separate from the minimal conservative U3 obligation.
-/
def CompletionComplete
    {L : SourceLanguage}
    {T : TargetLanguage}
    (Φ : ConservativeEmbedding L T) : Prop :=
  ∀ r e σ s,
    L.Done r e σ s →
      T.Done
        (Φ.mapRequirement r)
        (Φ.mapEvidence e)
        (Φ.mapSubject σ)
        (Φ.mapState s)

/-- Completion equivalence follows from conservative reflection plus completeness. -/
theorem completion_iff_of_complete
    {L : SourceLanguage}
    {T : TargetLanguage}
    (Φ : ConservativeEmbedding L T)
    (hComplete : CompletionComplete Φ)
    (r : L.Requirement)
    (e : L.Evidence)
    (σ : L.Subject)
    (s : L.State) :
    L.Done r e σ s ↔
      T.Done
        (Φ.mapRequirement r)
        (Φ.mapEvidence e)
        (Φ.mapSubject σ)
        (Φ.mapState s) := by
  constructor
  · exact hComplete r e σ s
  · exact Φ.completion_reflected r e σ s

/--
An admissibility predicate is intentionally a parameter of the metatheory.
Its definition determines the actual scope of the word "universal" and must be
supplied independently rather than chosen to make the theorem vacuous.
-/
abbrev AdmissibleClass := SourceLanguage → Prop

/--
U3 — Conservative Semantic Universality.

This is the theorem *statement* to be established for a concrete TEMDD target
and an independently fixed admissible class.  Defining this proposition does
not establish it.
-/
def U3ConservativeSemanticUniversality
    (C : AdmissibleClass)
    (T : TargetLanguage) : Prop :=
  ∀ L : SourceLanguage,
    C L → Nonempty (ConservativeEmbedding L T)

/-- U3 immediately supplies a conservative embedding for every admissible source. -/
theorem embedding_of_u3
    (C : AdmissibleClass)
    (T : TargetLanguage)
    (hU3 : U3ConservativeSemanticUniversality C T)
    (L : SourceLanguage)
    (hL : C L) :
    Nonempty (ConservativeEmbedding L T) := by
  exact hU3 L hL

/--
No-truth-manufacture corollary for any already constructed conservative
embedding: completion in the target reflects to completion in the source.
-/
theorem no_completion_manufactured_by_translation
    {L : SourceLanguage}
    {T : TargetLanguage}
    (Φ : ConservativeEmbedding L T)
    (r : L.Requirement)
    (e : L.Evidence)
    (σ : L.Subject)
    (s : L.State)
    (hDone :
      T.Done
        (Φ.mapRequirement r)
        (Φ.mapEvidence e)
        (Φ.mapSubject σ)
        (Φ.mapState s)) :
    L.Done r e σ s := by
  exact Φ.completion_reflected r e σ s hDone

/-- Subject identity cannot be collapsed by a conservative embedding. -/
theorem distinct_subjects_remain_distinct
    {L : SourceLanguage}
    {T : TargetLanguage}
    (Φ : ConservativeEmbedding L T)
    {σ σ' : L.Subject}
    (hDifferent : σ ≠ σ') :
    Φ.mapSubject σ ≠ Φ.mapSubject σ' := by
  intro hEqual
  exact hDifferent (Φ.injective_subject hEqual)

/--
The open proof obligation for a concrete TEMDD target is therefore exactly:
choose an independently justified `C`, instantiate `T` from Language 1.0 without
weakening its semantics, and prove `U3ConservativeSemanticUniversality C T`.
-/

end QIKVRT.V2.TEMDD.ConservativeUniversality
