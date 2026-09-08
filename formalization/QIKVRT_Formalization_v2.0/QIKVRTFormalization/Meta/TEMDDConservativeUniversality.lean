-- SPDX-License-Identifier: CC-BY-NC-ND-4.0
-- Copyright (c) 2026 Ingolf Lohmann.

import Std

/-!
# TEMDD conservative universality

This module formalizes the claim at its correct scope: admissible source
languages are those for which a witness carrying the required preservation
obligations exists.  It does not assert that every language has such a
witness, nor does formal embedding establish empirical truth.
-/

namespace QIKVRT.V2.TEMDD

universe u v w x y z

structure Language where
  State : Type u
  Requirement : Type v
  Evidence : Type w
  Action : Type x
  Authority : Type y
  Subject : Type z
  satisfies : State → Requirement → Prop
  bound : Evidence → Subject → Prop
  consistent : Evidence → Prop
  evidencePossible : State → Evidence → Prop
  allowed : Authority → Action → Prop
  hasCapability : Authority → Authority → Prop
  actor : Action → Authority
  step : State → Action → State → Prop
  reachable : State → Action → State → Prop
  done : Requirement → Evidence → State → Prop
  unknown : Prop → Prop
  mutated : Subject → Subject → Prop
  evidenceTransferAllowed : Prop

def GoalRegion (L : Language) (requirement : L.Requirement) :
    L.State → Prop :=
  fun state => L.satisfies state requirement

def KnowledgeRegion (L : Language) (evidence : L.Evidence) :
    L.State → Prop :=
  fun state => L.evidencePossible state evidence

def EvidenceNonAmplification (source target : Language)
    (mapEvidence : source.Evidence → target.Evidence) : Prop :=
  ∀ evidence state,
    target.evidencePossible state (mapEvidence evidence) →
      source.evidencePossible state evidence

structure ConservativeEmbedding (source : Language) (target : Language) where
  mapState : source.State → target.State
  mapRequirement : source.Requirement → target.Requirement
  mapEvidence : source.Evidence → target.Evidence
  mapAction : source.Action → target.Action
  mapAuthority : source.Authority → target.Authority
  mapSubject : source.Subject → target.Subject
  mapState_injective : Function.Injective mapState
  mapSubject_injective : Function.Injective mapSubject
  requirement_preserved :
    ∀ state requirement,
      source.satisfies state requirement ↔
        target.satisfies (mapState state) (mapRequirement requirement)
  evidence_preserved :
    ∀ state evidence,
      source.evidencePossible state evidence ↔
        target.evidencePossible (mapState state) (mapEvidence evidence)
  evidence_consistency_preserved :
    ∀ evidence,
      source.consistent evidence ↔ target.consistent (mapEvidence evidence)
  evidence_not_amplified : EvidenceNonAmplification source target mapEvidence
  subject_binding_preserved :
    ∀ evidence subject,
      source.bound evidence subject ↔
        target.bound (mapEvidence evidence) (mapSubject subject)
  mutation_preserved :
    ∀ oldSubject newSubject,
      source.mutated oldSubject newSubject →
        target.mutated (mapSubject oldSubject) (mapSubject newSubject)
  transition_preserved :
    ∀ state action next,
      source.step state action next →
        target.reachable (mapState state) (mapAction action) (mapState next)
  authority_preserved :
    ∀ authority action,
      target.allowed (mapAuthority authority) (mapAction action) →
        target.hasCapability (mapAuthority (source.actor action))
          (mapAuthority authority)
  completion_reflected :
    ∀ requirement evidence state,
      target.done (mapRequirement requirement) (mapEvidence evidence)
          (mapState state) →
        source.done requirement evidence state
  contradiction_preserved :
    ∀ evidence,
      ¬ source.consistent evidence →
        ¬ target.consistent (mapEvidence evidence)
  unknown_preserved :
    ∀ proposition,
      source.unknown proposition →
        target.unknown proposition
  transfer_denied :
    ¬ source.evidenceTransferAllowed →
      ¬ target.evidenceTransferAllowed

def AdmissibleClass (source target : Language) : Prop :=
  Nonempty (ConservativeEmbedding source target)

theorem completion_reflection (source target : Language)
    (embedding : ConservativeEmbedding source target)
    (requirement : source.Requirement) (evidence : source.Evidence)
    (state : source.State) :
    target.done (embedding.mapRequirement requirement)
        (embedding.mapEvidence evidence) (embedding.mapState state) →
      source.done requirement evidence state :=
  embedding.completion_reflected requirement evidence state

theorem temdd_conservative_universality (source target : Language)
    (hSource : AdmissibleClass source target) :
    ∃ embedding : ConservativeEmbedding source target, True := by
  rcases hSource with ⟨embedding⟩
  exact ⟨embedding, True.intro⟩

theorem no_freedom_to_redefine_truth (source target : Language)
    (embedding : ConservativeEmbedding source target)
    (requirement : source.Requirement) (evidence : source.Evidence)
    (state : source.State)
    (hDone : target.done (embedding.mapRequirement requirement)
      (embedding.mapEvidence evidence) (embedding.mapState state)) :
    source.done requirement evidence state :=
  embedding.completion_reflected requirement evidence state hDone

end QIKVRT.V2.TEMDD
