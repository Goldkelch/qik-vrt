-- SPDX-License-Identifier: Apache-2.0
-- Copyright (c) 2026 Ingolf Lohmann.

import Std

/-!
# Operational continuation through viable connections (FIT-001)

This module gives a deliberately scoped computer-science interpretation of
the phrase "survival of the fittest": operational continuation for a bounded
horizon requires a chain of viable successor connections.

## Truth boundary

Darwinian fitness in evolutionary biology remains relative reproductive
success in a specified population and environment.  This module neither
redefines that biological quantity nor proves that biological fitness is
identical to graph connectivity, software interoperability, or the number of
successors.

The checked result is about an abstract transition system only.  In that
model, "anschlussfaehig" means that a state is viable and has an admissible
transition to a viable successor.  The theorem establishes continuation under
those explicit definitions; application to a concrete computer, organism, or
environment requires a separately justified model correspondence.
-/

namespace QIKVRT.V2.OperationalContinuation

universe u v w

/-!
The biological object is kept distinct at the type level.  No theorem below
identifies this environment-relative reproductive-success measurement with
the operational continuation model.
-/

/--
An abstract representation of Darwinian fitness as relative reproductive
success measured for an organism in an environment.

The score type is intentionally generic because the empirical definition and
normalization belong to the selected biological study.
-/
structure DarwinianFitnessModel
    (Organism : Type u) (Environment : Type v) (Score : Type w) where
  relativeReproductiveSuccess : Environment → Organism → Score

/--
The operational model used by the computer-science theorem.  `connects`
records admissible successor transitions; `viable` records the explicit local
continuation condition.
-/
structure ContinuationSystem (State : Type u) where
  connects : State → State → Prop
  viable : State → Prop

/--
A viable connection preserves viability at both endpoints and supplies an
admissible successor transition.
-/
def ViableConnection {State : Type u}
    (system : ContinuationSystem State) (current successor : State) : Prop :=
  system.viable current ∧
    system.connects current successor ∧
    system.viable successor

/-- A state has at least one viable operational successor. -/
def HasViableSuccessor {State : Type u}
    (system : ContinuationSystem State) (current : State) : Prop :=
  ∃ successor, ViableConnection system current successor

/--
`Survives system horizon current` means that `current` remains operationally
continuable for the requested finite horizon.

At horizon zero, current viability is sufficient.  At a successor horizon,
one viable connection and survival of its successor for the remaining horizon
are necessary and sufficient.
-/
def Survives {State : Type u}
    (system : ContinuationSystem State) : Nat → State → Prop
  | 0, current => system.viable current
  | Nat.succ horizon, current =>
      ∃ successor,
        ViableConnection system current successor ∧
        Survives system horizon successor

/--
FIT-001A: successor-horizon continuation is exactly one viable connection plus
tail continuation.  This is the central operational, not biological,
equivalence.
-/
theorem survival_at_successor_iff_viable_connection_and_tail
    {State : Type u} (system : ContinuationSystem State)
    (horizon : Nat) (current : State) :
    Survives system (Nat.succ horizon) current ↔
      ∃ successor,
        ViableConnection system current successor ∧
        Survives system horizon successor := by
  rfl

/-- Any positive-horizon survivor is viable at the current state. -/
theorem survival_at_successor_requires_current_viability
    {State : Type u} (system : ContinuationSystem State)
    (horizon : Nat) (current : State) :
    Survives system (Nat.succ horizon) current →
      system.viable current := by
  rintro ⟨successor, hConnection, _⟩
  exact hConnection.1

/-- FIT-001B: a state without a viable successor cannot survive one more step. -/
theorem nonconnectable_cannot_survive
    {State : Type u} (system : ContinuationSystem State)
    (horizon : Nat) (current : State) :
    ¬ HasViableSuccessor system current →
      ¬ Survives system (Nat.succ horizon) current := by
  intro hNoSuccessor hSurvives
  rcases hSurvives with ⟨successor, hConnection, _⟩
  exact hNoSuccessor ⟨successor, hConnection⟩

/-- Survival for one additional step implies survival for the shorter horizon. -/
theorem survival_horizon_drop_one
    {State : Type u} (system : ContinuationSystem State)
    (horizon : Nat) (current : State) :
    Survives system (Nat.succ horizon) current →
      Survives system horizon current := by
  induction horizon generalizing current with
  | zero =>
      exact survival_at_successor_requires_current_viability system 0 current
  | succ horizon inductionHypothesis =>
      rintro ⟨successor, hConnection, hTail⟩
      exact ⟨successor, hConnection, inductionHypothesis hTail⟩

/--
FIT-001C: survival is monotone under shortening a finite horizon.  `extra`
states how many continuation obligations are removed.
-/
theorem survival_horizon_monotone
    {State : Type u} (system : ContinuationSystem State)
    (base extra : Nat) (current : State) :
    Survives system (base + extra) current →
      Survives system base current := by
  induction extra with
  | zero =>
      simpa
  | succ extra inductionHypothesis =>
      intro hSurvives
      apply inductionHypothesis
      apply survival_horizon_drop_one system (base + extra) current
      simpa [Nat.add_succ] using hSurvives

/--
The stable, proposition-indexed claim for the computer-age operational reading.
It deliberately contains no statement about biological reproductive success.
-/
def FIT001Statement : Prop :=
  ∀ (State : Type u) (system : ContinuationSystem State),
    (∀ horizon current,
      Survives system (Nat.succ horizon) current ↔
        ∃ successor,
          ViableConnection system current successor ∧
          Survives system horizon successor) ∧
    (∀ horizon current,
      ¬ HasViableSuccessor system current →
        ¬ Survives system (Nat.succ horizon) current) ∧
    (∀ base extra current,
      Survives system (base + extra) current →
        Survives system base current)

/--
FIT-001: kernel-checkable operational continuation theorem.

The theorem justifies "survival of the anschlussfaehigsten" only as the scoped
computer-system interpretation encoded by `ContinuationSystem` and `Survives`.
It does not change Darwin's biological meaning and makes no empirical claim.
-/
theorem FIT001_checked : FIT001Statement := by
  intro State system
  exact
    ⟨survival_at_successor_iff_viable_connection_and_tail system,
      nonconnectable_cannot_survive system,
      survival_horizon_monotone system⟩

#print axioms survival_at_successor_iff_viable_connection_and_tail
#print axioms nonconnectable_cannot_survive
#print axioms survival_horizon_monotone
#print axioms FIT001_checked

end QIKVRT.V2.OperationalContinuation
