/-
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
-/

import Std

/-!
# Universal ontology finite-model kernel

This module formalizes a finite, typed architecture for the two QIK-VRT chains

* difference → information → relation → causality → spacetime → matter →
  life → cognition → responsibility → future; and
* reality → difference → information → relation → causal order → model →
  formalization → proof/prediction → measurement → reality reconciliation →
  new difference.

The theorems below establish properties of this explicitly defined model. They
do not by themselves establish that physical nature instantiates the model,
that finite paired values are quantum-entangled particles, or that the model is
a complete theory of the universe.
-/

namespace QIKVRT.UniversalOntology

inductive OntologyStage where
  | difference
  | information
  | relation
  | causality
  | spacetime
  | matter
  | life
  | cognition
  | responsibility
  | future
deriving DecidableEq, Repr, BEq

def ontologyRank : OntologyStage → Nat
  | .difference => 0
  | .information => 1
  | .relation => 2
  | .causality => 3
  | .spacetime => 4
  | .matter => 5
  | .life => 6
  | .cognition => 7
  | .responsibility => 8
  | .future => 9

def ontologyChain : List OntologyStage :=
  [.difference, .information, .relation, .causality, .spacetime,
   .matter, .life, .cognition, .responsibility, .future]

def OntologyPrecedes (left right : OntologyStage) : Prop :=
  ontologyRank left < ontologyRank right

theorem ontologyChain_length : ontologyChain.length = 10 := by
  decide

theorem ontologyChain_pairwise : ontologyChain.Pairwise (· ≠ ·) := by
  decide

theorem difference_precedes_information :
    OntologyPrecedes .difference .information := by
  decide

theorem information_precedes_relation :
    OntologyPrecedes .information .relation := by
  decide

theorem relation_precedes_causality :
    OntologyPrecedes .relation .causality := by
  decide

theorem causality_precedes_spacetime :
    OntologyPrecedes .causality .spacetime := by
  decide

theorem spacetime_precedes_matter :
    OntologyPrecedes .spacetime .matter := by
  decide

theorem matter_precedes_life :
    OntologyPrecedes .matter .life := by
  decide

theorem life_precedes_cognition :
    OntologyPrecedes .life .cognition := by
  decide

theorem cognition_precedes_responsibility :
    OntologyPrecedes .cognition .responsibility := by
  decide

theorem responsibility_precedes_future :
    OntologyPrecedes .responsibility .future := by
  decide

theorem difference_precedes_future :
    OntologyPrecedes .difference .future := by
  decide

theorem ontologyPrecedes_irrefl (stage : OntologyStage) :
    ¬ OntologyPrecedes stage stage := by
  exact Nat.lt_irrefl (ontologyRank stage)

theorem ontologyPrecedes_trans {a b c : OntologyStage}
    (hab : OntologyPrecedes a b) (hbc : OntologyPrecedes b c) :
    OntologyPrecedes a c := by
  exact Nat.lt_trans hab hbc

universe u

structure Distinction (α : Type u) where
  left : α
  right : α
  different : left ≠ right

structure InformationWitness (α : Type u) where
  source : Distinction α

def informationOfDistinction (difference : Distinction α) :
    InformationWitness α :=
  ⟨difference⟩

theorem information_preserves_difference (difference : Distinction α) :
    (informationOfDistinction difference).source.left ≠
      (informationOfDistinction difference).source.right := by
  exact difference.different

abbrev CausalRelation (α : Type u) := α → α → Prop

structure CausalModel (α : Type u) where
  relates : CausalRelation α
  irreflexive : ∀ point, ¬ relates point point
  transitive : ∀ {a b c}, relates a b → relates b c → relates a c

theorem causalModel_is_relational (model : CausalModel α) :
    CausalRelation α = (α → α → Prop) := by
  rfl

inductive EpistemicStage where
  | reality
  | difference
  | information
  | relation
  | causalOrder
  | model
  | formalization
  | proofPrediction
  | measurement
  | realityReconciliation
  | newDifference
deriving DecidableEq, Repr, BEq

def epistemicRank : EpistemicStage → Nat
  | .reality => 0
  | .difference => 1
  | .information => 2
  | .relation => 3
  | .causalOrder => 4
  | .model => 5
  | .formalization => 6
  | .proofPrediction => 7
  | .measurement => 8
  | .realityReconciliation => 9
  | .newDifference => 10

def epistemicChain : List EpistemicStage :=
  [.reality, .difference, .information, .relation, .causalOrder, .model,
   .formalization, .proofPrediction, .measurement, .realityReconciliation,
   .newDifference]

def EpistemicPrecedes (left right : EpistemicStage) : Prop :=
  epistemicRank left < epistemicRank right

def Feedback : EpistemicStage → EpistemicStage → Prop
  | .newDifference, .reality => True
  | _, _ => False

theorem epistemicChain_length : epistemicChain.length = 11 := by
  decide

theorem epistemicChain_pairwise : epistemicChain.Pairwise (· ≠ ·) := by
  decide

theorem reality_precedes_newDifference :
    EpistemicPrecedes .reality .newDifference := by
  decide

theorem epistemic_roundTrip_closes :
    EpistemicPrecedes .reality .newDifference ∧
      Feedback .newDifference .reality := by
  constructor <;> decide

inductive PairBit where
  | zero
  | one
deriving DecidableEq, Repr, BEq

def FinitePairRelated (left right : PairBit) : Prop :=
  left ≠ right

theorem finitePair_exists :
    ∃ left right, FinitePairRelated left right := by
  exact ⟨.zero, .one, by decide⟩

theorem finitePair_symmetric {left right : PairBit}
    (related : FinitePairRelated left right) :
    FinitePairRelated right left := by
  exact Ne.symm related

inductive ClaimKind where
  | definition
  | assumption
  | formalTheorem
  | correspondencePostulate
  | empiricalClaim
  | interpretation
  | normativeRule
deriving DecidableEq, Repr, BEq

inductive ClaimDisposition where
  | kernelProved
  | kernelProvedConditional
  | evidenceRequired
  | openCandidate
  | interpretive
  | normative
  | refuted
  | outOfScope
deriving DecidableEq, Repr, BEq

def machineProofEligible : ClaimKind → Bool
  | .formalTheorem => true
  | .definition => true
  | .assumption => true
  | .correspondencePostulate => false
  | .empiricalClaim => false
  | .interpretation => false
  | .normativeRule => false

theorem empirical_claim_not_kernel_promoted :
    machineProofEligible .empiricalClaim = false := by
  decide

theorem interpretation_not_kernel_promoted :
    machineProofEligible .interpretation = false := by
  decide

inductive EffectState where
  | continueState
  | blocked
  | done
deriving DecidableEq, Repr, BEq

def ordinaryRelease : EffectState → Bool
  | .done => true
  | .continueState => false
  | .blocked => false

theorem ordinaryRelease_only_done (state : EffectState) :
    ordinaryRelease state = true → state = .done := by
  cases state <;> simp [ordinaryRelease]

structure CheckedClaim (id : String) (statement : Prop) : Type where
  checked : statement

def differenceFutureChecked :
    CheckedClaim "UO-THM-012" (OntologyPrecedes .difference .future) where
  checked := difference_precedes_future

def roundTripChecked :
    CheckedClaim "UO-THM-019"
      (EpistemicPrecedes .reality .newDifference ∧
        Feedback .newDifference .reality) where
  checked := epistemic_roundTrip_closes

end QIKVRT.UniversalOntology
