-- SPDX-License-Identifier: Apache-2.0
-- Copyright (c) 2026 Ingolf Lohmann.

import Std

/-!
# Viability-preserving connectability simulations (FIT-002)

This module formalizes a second, deliberately scoped computer-science result
for the interpretation "survival of the anschlussfaehigsten".  A typed
labelled transition system distinguishes admissible steps from locally viable
steps.  Finite traces contain only viable steps.  A simulation that preserves
viability and matches every viable source step preserves every finite viable
trace and therefore includes the source system's viable language.

The resulting "at least as connectable" relation is reflexive and transitive.
It compares systems by finite viable behaviour; it is not a biological fitness
measure.

## Truth boundary

Darwinian fitness in evolutionary biology remains relative reproductive
success in a specified population and environment.  Nothing in this module
identifies reproductive success with transition-system simulation, language
inclusion, interoperability, degree, or successor count.  FIT-002 is a theorem
about the definitions below.  Applying it to software, networks, organisms, or
physical environments requires a separately justified correspondence model.
-/

namespace QIKVRT.V2.ConnectabilitySimulation

universe u v w x

/-! ## Typed viable transition systems and finite traces -/

/--
A labelled transition system with an explicit local viability predicate.
Lean's types ensure that every transition has a source and target in `State`
and a label in `Label`.
-/
structure TypedTransitionSystem (State : Type u) (Label : Type v) where
  step : State → Label → State → Prop
  viable : State → Prop

/-!
For the paper's tuple `(X, x0, U, transition, P, Q)`, instantiate `viable` as
`P` and instantiate `step x u x'` as the conjunction of the raw transition
with contract `Q x u x'`.  `ValidStep` below then adds endpoint viability.
This mapping is part of the formal model; evidence that a concrete runtime
implements it remains a separate refinement obligation.
-/

/--
An admissible transition whose source and target are both viable.
-/
structure ValidStep {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label)
    (source : State) (label : Label) (target : State) : Prop where
  sourceViable : system.viable source
  transition : system.step source label target
  targetViable : system.viable target

/-- FIT-002A: a valid step contains a transition with the declared types. -/
theorem valid_step_has_typed_transition
    {State : Type u} {Label : Type v}
    {system : TypedTransitionSystem State Label}
    {source target : State} {label : Label}
    (hStep : ValidStep system source label target) :
    system.step source label target :=
  hStep.transition

/--
A finite viable trace from `source` to `target` carrying exactly `labels`.

The empty trace requires a viable state and leaves it unchanged.  A nonempty
trace begins with a valid step and recursively continues with a viable tail.
-/
def ViableTrace {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label) :
    State → List Label → State → Prop
  | source, [], target => source = target ∧ system.viable source
  | source, label :: labels, target =>
      ∃ next,
        ValidStep system source label next ∧
        ViableTrace system next labels target

/-- Every finite viable trace begins in a viable state. -/
theorem viable_trace_start_viable
    {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label)
    (source target : State) (labels : List Label) :
    ViableTrace system source labels target → system.viable source := by
  cases labels with
  | nil =>
      intro hTrace
      exact hTrace.2
  | cons label labels =>
      rintro ⟨next, hStep, hTail⟩
      exact hStep.sourceViable

/-- Every finite viable trace ends in a viable state. -/
theorem viable_trace_target_viable
    {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label)
    (source target : State) (labels : List Label) :
    ViableTrace system source labels target → system.viable target := by
  induction labels generalizing source with
  | nil =>
      rintro ⟨hSame, hViable⟩
      rw [← hSame]
      exact hViable
  | cons label labels inductionHypothesis =>
      rintro ⟨next, hStep, hTail⟩
      exact inductionHypothesis next hTail

/-! ## Viability-preserving simulations -/

/--
A forward simulation between systems with the same label type.

Related viable source states remain viable in the target.  Every valid source
step has a valid target step with the same label, and the successor states are
again related.
-/
structure ViabilitySimulation
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    (source : TypedTransitionSystem SourceState Label)
    (target : TypedTransitionSystem TargetState Label)
    (relation : SourceState → TargetState → Prop) : Prop where
  preservesViability :
    ∀ {sourceState targetState},
      relation sourceState targetState →
      source.viable sourceState →
      target.viable targetState
  simulatesValidStep :
    ∀ {sourceState sourceNext targetState label},
      relation sourceState targetState →
      ValidStep source sourceState label sourceNext →
      ∃ targetNext,
        ValidStep target targetState label targetNext ∧
        relation sourceNext targetNext

/--
FIT-002B: a viability-preserving simulation lifts every finite viable source
trace to a target trace with the same labels and a related final state.
-/
theorem simulation_preserves_viable_trace
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    {source : TypedTransitionSystem SourceState Label}
    {target : TypedTransitionSystem TargetState Label}
    {relation : SourceState → TargetState → Prop}
    (simulation : ViabilitySimulation source target relation)
    (sourceState sourceFinal : SourceState)
    (targetState : TargetState) (labels : List Label)
    (hRelated : relation sourceState targetState)
    (hTrace : ViableTrace source sourceState labels sourceFinal) :
    ∃ targetFinal,
      ViableTrace target targetState labels targetFinal ∧
      relation sourceFinal targetFinal := by
  induction labels generalizing sourceState sourceFinal targetState with
  | nil =>
      rcases hTrace with ⟨hSame, hViable⟩
      subst sourceFinal
      exact
        ⟨targetState,
          ⟨rfl, simulation.preservesViability hRelated hViable⟩,
          hRelated⟩
  | cons label labels inductionHypothesis =>
      rcases hTrace with ⟨sourceNext, hSourceStep, hSourceTail⟩
      rcases simulation.simulatesValidStep hRelated hSourceStep with
        ⟨targetNext, hTargetStep, hRelatedNext⟩
      rcases inductionHypothesis sourceNext sourceFinal targetNext
          hRelatedNext hSourceTail with
        ⟨targetFinal, hTargetTail, hRelatedFinal⟩
      exact
        ⟨targetFinal,
          ⟨targetNext, hTargetStep, hTargetTail⟩,
          hRelatedFinal⟩

/-! ## Pointed systems and initial-state language inclusion -/

/--
A typed transition system with a distinguished initial state.

Both systems compared below share the same `Label` type, so the theorem matches
identical label values rather than silently translating unrelated alphabets.
The additional interpretation that equal labels denote the same external
action is an explicit model-correspondence premise; Lean does not manufacture
that empirical semantics.
-/
structure PointedTransitionSystem (State : Type u) (Label : Type v) where
  system : TypedTransitionSystem State Label
  initial : State
  initialViable : system.viable initial

/--
The finite viable language reachable from the distinguished initial state.
-/
def PointedViableLanguage {State : Type u} {Label : Type v}
    (system : PointedTransitionSystem State Label)
    (labels : List Label) : Prop :=
  ∃ target,
    ViableTrace system.system system.initial labels target

/--
A viability-preserving simulation whose distinguished initial states are
related.  No global coverage premise is needed for its pointed language.
-/
structure PointedViabilitySimulation
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    (source : PointedTransitionSystem SourceState Label)
    (target : PointedTransitionSystem TargetState Label)
    (relation : SourceState → TargetState → Prop) : Prop where
  simulation :
    ViabilitySimulation source.system target.system relation
  initialRelated :
    relation source.initial target.initial

/--
FIT-003A: related initial states plus viability-preserving step simulation
imply pointed viable-language inclusion.

In the argument order used here, `source` is the behaviour being simulated and
`target` is the system that matches it.  Consequently
`PointedLanguage(source) ⊆ PointedLanguage(target)`.
-/
theorem pointed_simulation_implies_viable_language_inclusion
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    {source : PointedTransitionSystem SourceState Label}
    {target : PointedTransitionSystem TargetState Label}
    {relation : SourceState → TargetState → Prop}
    (pointedSimulation :
      PointedViabilitySimulation source target relation) :
    ∀ labels,
      PointedViableLanguage source labels →
      PointedViableLanguage target labels := by
  intro labels hSourceLanguage
  rcases hSourceLanguage with ⟨sourceFinal, hSourceTrace⟩
  rcases simulation_preserves_viable_trace pointedSimulation.simulation
      source.initial sourceFinal target.initial labels
      pointedSimulation.initialRelated hSourceTrace with
    ⟨targetFinal, hTargetTrace, hRelatedFinal⟩
  exact ⟨targetFinal, hTargetTrace⟩

/-!
The pointed theorem matches the distinguished-start formulation used in the
paper.  The global language below instead ranges over every viable source
state and therefore retains the stronger `CoversViableStates` premise.
-/

/-! ## Viable languages and relative connectability -/

/-- A word belongs to a system's viable language if some viable trace carries it. -/
def ViableLanguage {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label)
    (labels : List Label) : Prop :=
  ∃ source target, ViableTrace system source labels target

/-- Every viable source state is represented by a related target state. -/
def CoversViableStates
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    (source : TypedTransitionSystem SourceState Label)
    (relation : SourceState → TargetState → Prop) : Prop :=
  ∀ sourceState,
    source.viable sourceState →
    ∃ targetState, relation sourceState targetState

/--
FIT-002C: a viability simulation that covers all viable source states induces
inclusion of finite viable languages.
-/
theorem simulation_implies_viable_language_inclusion
    {SourceState : Type u} {TargetState : Type v} {Label : Type w}
    {source : TypedTransitionSystem SourceState Label}
    {target : TypedTransitionSystem TargetState Label}
    {relation : SourceState → TargetState → Prop}
    (simulation : ViabilitySimulation source target relation)
    (coverage : CoversViableStates source relation) :
    ∀ labels,
      ViableLanguage source labels →
      ViableLanguage target labels := by
  intro labels hSourceLanguage
  rcases hSourceLanguage with ⟨sourceState, sourceFinal, hSourceTrace⟩
  have hSourceViable : source.viable sourceState :=
    viable_trace_start_viable source sourceState sourceFinal labels hSourceTrace
  rcases coverage sourceState hSourceViable with ⟨targetState, hRelated⟩
  rcases simulation_preserves_viable_trace simulation
      sourceState sourceFinal targetState labels hRelated hSourceTrace with
    ⟨targetFinal, hTargetTrace, hRelatedFinal⟩
  exact ⟨targetState, targetFinal, hTargetTrace⟩

/--
`target` is at least as connectable as `source` when every finite viable word
of `source` is also a finite viable word of `target`.

The argument order is intentional: `AtLeastAsConnectable target source` means
`ViableLanguage source ⊆ ViableLanguage target`.
-/
def AtLeastAsConnectable
    {TargetState : Type u} {SourceState : Type v} {Label : Type w}
    (target : TypedTransitionSystem TargetState Label)
    (source : TypedTransitionSystem SourceState Label) : Prop :=
  ∀ labels,
    ViableLanguage source labels →
    ViableLanguage target labels

/-- FIT-002D: relative connectability is reflexive. -/
theorem at_least_as_connectable_refl
    {State : Type u} {Label : Type v}
    (system : TypedTransitionSystem State Label) :
    AtLeastAsConnectable system system := by
  intro labels hLanguage
  exact hLanguage

/-- FIT-002E: relative connectability is transitive. -/
theorem at_least_as_connectable_trans
    {SourceState : Type u} {MiddleState : Type v}
    {TargetState : Type w} {Label : Type x}
    (source : TypedTransitionSystem SourceState Label)
    (middle : TypedTransitionSystem MiddleState Label)
    (target : TypedTransitionSystem TargetState Label)
    (hMiddle : AtLeastAsConnectable middle source)
    (hTarget : AtLeastAsConnectable target middle) :
    AtLeastAsConnectable target source := by
  intro labels hSourceLanguage
  exact hTarget labels (hMiddle labels hSourceLanguage)

/-- The stable proposition-indexed claim checked by FIT-002. -/
def FIT002Statement : Prop :=
  ∀ (SourceState : Type u) (TargetState : Type v) (Label : Type w)
    (source : TypedTransitionSystem SourceState Label)
    (target : TypedTransitionSystem TargetState Label)
    (relation : SourceState → TargetState → Prop),
    ViabilitySimulation source target relation →
    CoversViableStates source relation →
    AtLeastAsConnectable target source

/--
FIT-002: kernel-checkable viable-language inclusion under a total
viability-preserving simulation.

This theorem makes no claim about Darwinian reproductive fitness.
-/
theorem FIT002_checked : FIT002Statement := by
  intro SourceState TargetState Label source target relation
    simulation coverage
  exact simulation_implies_viable_language_inclusion simulation coverage

/-- The stable proposition-indexed pointed-language claim checked by FIT-003. -/
def FIT003Statement : Prop :=
  ∀ (SourceState : Type u) (TargetState : Type v) (Label : Type w)
    (source : PointedTransitionSystem SourceState Label)
    (target : PointedTransitionSystem TargetState Label)
    (relation : SourceState → TargetState → Prop),
    PointedViabilitySimulation source target relation →
    ∀ labels,
      PointedViableLanguage source labels →
      PointedViableLanguage target labels

/--
FIT-003: kernel-checkable pointed viable-language inclusion under an
initial-state-related, viability-preserving simulation.

This theorem uses a shared label type and makes no biological fitness claim.
-/
theorem FIT003_checked : FIT003Statement := by
  intro SourceState TargetState Label source target relation
    pointedSimulation labels hSourceLanguage
  exact pointed_simulation_implies_viable_language_inclusion
    pointedSimulation labels hSourceLanguage

#print axioms valid_step_has_typed_transition
#print axioms viable_trace_start_viable
#print axioms viable_trace_target_viable
#print axioms simulation_preserves_viable_trace
#print axioms pointed_simulation_implies_viable_language_inclusion
#print axioms simulation_implies_viable_language_inclusion
#print axioms at_least_as_connectable_refl
#print axioms at_least_as_connectable_trans
#print axioms FIT002_checked
#print axioms FIT003_checked

end QIKVRT.V2.ConnectabilitySimulation
