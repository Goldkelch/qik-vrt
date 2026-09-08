import Std

/-!
# TEMDD completion calculus

A small, domain-general kernel for Tested Event Model Driven Development.
It formalizes completion as a property of a requirement, a nonempty knowledge
region, exact subject binding, and coverage of the actual state.

This file deliberately does not identify repository workflow success, review,
publication, empirical truth, or external effect acknowledgement with `Done`.
Those remain separate evidence classes and obligations.
-/

namespace QIKVRT.V2.TEMDD

universe u v

variable {State : Type u} {Subject : Type v}

/-- A requirement denotes the admissible goal region. -/
abbrev Requirement (State : Type u) := State → Prop

/-- Evidence determines the states still compatible with what has been observed. -/
abbrev KnowledgeRegion (State : Type u) := State → Prop

/-- The evidence model is consistent exactly when at least one state remains possible. -/
def Consistent (K : KnowledgeRegion State) : Prop :=
  ∃ s, K s

/-- Every state still compatible with the evidence satisfies the requirement. -/
def SoundFor (R : Requirement State) (K : KnowledgeRegion State) : Prop :=
  ∀ s, K s → R s

/-- Evidence is bound to exactly the subject for which completion is claimed. -/
def Bound (evidenceSubject actualSubject : Subject) : Prop :=
  evidenceSubject = actualSubject

/-- The actual state is contained in the evidence-compatible region. -/
def ActualCovered (K : KnowledgeRegion State) (actual : State) : Prop :=
  K actual

/--
TEMDD completion predicate.

`Done` is intentionally subject-relative and requires:
* nonempty/consistent evidence,
* closure of the knowledge region inside the requirement region,
* exact subject binding,
* coverage of the actual state.
-/
def Done
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (evidenceSubject actualSubject : Subject)
    (actual : State) : Prop :=
  Consistent K ∧
  SoundFor R K ∧
  Bound evidenceSubject actualSubject ∧
  ActualCovered K actual

/-- A completed exact subject's actual state satisfies the requirement. -/
theorem done_actual_satisfies
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (evidenceSubject actualSubject : Subject)
    (actual : State)
    (h : Done R K evidenceSubject actualSubject actual) :
    R actual := by
  exact h.2.1 actual h.2.2.2

/-- Empty/inconsistent evidence cannot establish completion. -/
theorem inconsistent_not_done
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (evidenceSubject actualSubject : Subject)
    (actual : State)
    (h : ¬ Consistent K) :
    ¬ Done R K evidenceSubject actualSubject actual := by
  intro hd
  exact h hd.1

/-- Evidence bound to a different subject cannot establish completion. -/
theorem unbound_not_done
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (evidenceSubject actualSubject : Subject)
    (actual : State)
    (h : evidenceSubject ≠ actualSubject) :
    ¬ Done R K evidenceSubject actualSubject actual := by
  intro hd
  exact h hd.2.2.1

/-- Failure to cover the actual state prevents completion. -/
theorem uncovered_actual_not_done
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (evidenceSubject actualSubject : Subject)
    (actual : State)
    (h : ¬ ActualCovered K actual) :
    ¬ Done R K evidenceSubject actualSubject actual := by
  intro hd
  exact h hd.2.2.2

/-- A witness outside the goal region proves that the knowledge region is not sound. -/
theorem counterexample_refutes_soundness
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (s : State)
    (hK : K s)
    (hR : ¬ R s) :
    ¬ SoundFor R K := by
  intro hs
  exact hR (hs s hK)

/-- A changed subject invalidates completion evidence from the old subject. -/
theorem mutation_invalidates_done
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (oldSubject newSubject : Subject)
    (actual : State)
    (changed : oldSubject ≠ newSubject) :
    ¬ Done R K oldSubject newSubject actual := by
  exact unbound_not_done R K oldSubject newSubject actual changed

/-- A transition may keep the same requirement, or change it only with explicit authority. -/
def RequirementTransitionAllowed
    (authorized : Requirement State → Requirement State → Prop)
    (before after : Requirement State) : Prop :=
  before = after ∨ authorized before after

/-- Any actual requirement change admitted by the contract carries explicit authority. -/
theorem changed_requirement_requires_authority
    (authorized : Requirement State → Requirement State → Prop)
    (before after : Requirement State)
    (changed : before ≠ after)
    (allowed : RequirementTransitionAllowed authorized before after) :
    authorized before after := by
  rcases allowed with unchanged | approved
  · exact False.elim (changed unchanged)
  · exact approved

/-- A post-state relation is safe when every possible execution remains in the goal region. -/
def Safe
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (post : State → State → Prop) : Prop :=
  ∀ before, K before → ∀ after, post before after → R after

/-- A counterexample transition refutes action safety. -/
theorem counterexample_refutes_safety
    (R : Requirement State)
    (K : KnowledgeRegion State)
    (post : State → State → Prop)
    (before after : State)
    (hK : K before)
    (hPost : post before after)
    (hR : ¬ R after) :
    ¬ Safe R K post := by
  intro hs
  exact hR (hs before hK after hPost)

end QIKVRT.V2.TEMDD
