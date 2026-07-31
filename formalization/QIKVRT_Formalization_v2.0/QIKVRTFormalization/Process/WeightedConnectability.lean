-- SPDX-License-Identifier: Apache-2.0
-- Copyright (c) 2026 Ingolf Lohmann.

import Std

/-!
# Finite weighted connectability scores (MAT-001 / MAT-002)

This file proves the discrete, kernel-checkable form of the manuscript's
weighted finite-horizon score result. Weights are natural numbers, hence
nonnegative by construction. A normalized score is represented by its
accepted-weight numerator together with the common total-weight denominator.
For two scores with the same strictly positive denominator, comparison of the
normalized ratios is exactly comparison of their numerators; no division or
floating-point arithmetic enters the kernel theorem.

## Truth boundary

The result applies to an explicitly finite, duplicate-free trace universe,
decidable acceptance predicates, natural-number weights, and a shared
strictly positive normalizer. Rational weights with a common denominator can
be scaled into this representation. This module does not prove an arbitrary
real-weight theorem, an empirical persistence advantage, or an identity with
biological fitness.
-/

namespace QIKVRT.V2.WeightedConnectability

universe u

/-- A finite, duplicate-free universe of traces up to a declared horizon. -/
structure FiniteTraceUniverse (Label : Type u) where
  horizon : Nat
  traces : List (List Label)
  nodup : traces.Nodup
  bounded : ∀ trace, trace ∈ traces → trace.length ≤ horizon

/-- Total nonnegative weight of a finite list. -/
def totalWeight {Trace : Type u}
    (weight : Trace → Nat) : List Trace → Nat
  | [] => 0
  | trace :: rest => weight trace + totalWeight weight rest

/-- Weight of exactly those listed traces satisfying `accepts`. -/
def weightedMass {Trace : Type u}
    (weight : Trace → Nat)
    (accepts : Trace → Prop)
    [DecidablePred accepts] : List Trace → Nat
  | [] => 0
  | trace :: rest =>
      (if accepts trace then weight trace else 0) +
        weightedMass weight accepts rest

/-- Exact finite representation of a common-denominator normalized score. -/
structure WeightedScore where
  acceptedWeight : Nat
  totalWeight : Nat

/-- Build the score pair `(accepted mass, total mass)`. -/
def score {Label : Type u}
    (traceUniverse : FiniteTraceUniverse Label)
    (weight : List Label → Nat)
    (accepts : List Label → Prop)
    [DecidablePred accepts] : WeightedScore :=
  { acceptedWeight := weightedMass weight accepts traceUniverse.traces
    totalWeight := totalWeight weight traceUniverse.traces }

/-!
Order of normalized scores when the denominator is common and positive. This
is equivalent to comparing `small.acceptedWeight / D` and
`large.acceptedWeight / D` for the shared `D > 0`, without defining division
inside the checked model.
-/
def CommonDenominatorScoreLE
    (small large : WeightedScore) : Prop :=
  0 < small.totalWeight ∧
  small.totalWeight = large.totalWeight ∧
  small.acceptedWeight ≤ large.acceptedWeight

/-- Strict common-positive-denominator score order. -/
def CommonDenominatorScoreLT
    (small large : WeightedScore) : Prop :=
  0 < small.totalWeight ∧
  small.totalWeight = large.totalWeight ∧
  small.acceptedWeight < large.acceptedWeight

/-- Weighted mass is monotone under predicate/language inclusion. -/
theorem weightedMass_mono
    {Trace : Type u}
    (weight : Trace → Nat)
    (small large : Trace → Prop)
    [DecidablePred small] [DecidablePred large]
    (traceUniverse : List Trace)
    (hInclusion : ∀ trace, small trace → large trace) :
    weightedMass weight small traceUniverse ≤
      weightedMass weight large traceUniverse := by
  induction traceUniverse with
  | nil =>
      exact Nat.le_refl 0
  | cons trace rest inductionHypothesis =>
      change
        (if small trace then weight trace else 0) +
              weightedMass weight small rest ≤
          (if large trace then weight trace else 0) +
              weightedMass weight large rest
      by_cases hSmall : small trace
      · have hLarge : large trace := hInclusion trace hSmall
        rw [if_pos hSmall, if_pos hLarge]
        omega
      · rw [if_neg hSmall]
        by_cases hLarge : large trace
        · rw [if_pos hLarge]
          omega
        · rw [if_neg hLarge]
          omega

/-- Weighted mass distributes over list concatenation. -/
theorem weightedMass_append
    {Trace : Type u}
    (weight : Trace → Nat)
    (accepts : Trace → Prop)
    [DecidablePred accepts]
    (left right : List Trace) :
    weightedMass weight accepts (left ++ right) =
      weightedMass weight accepts left +
        weightedMass weight accepts right := by
  induction left with
  | nil =>
      rfl
  | cons trace rest inductionHypothesis =>
      change
        (if accepts trace then weight trace else 0) +
              weightedMass weight accepts (rest ++ right) =
          ((if accepts trace then weight trace else 0) +
              weightedMass weight accepts rest) +
            weightedMass weight accepts right
      rw [inductionHypothesis]
      omega

/-!
A positive-weight witness accepted only by `large`, together with inclusion,
makes the finite weighted mass strictly larger.
-/
theorem weightedMass_strict_of_positive_witness
    {Trace : Type u}
    (weight : Trace → Nat)
    (small large : Trace → Prop)
    [DecidablePred small] [DecidablePred large]
    (left right : List Trace)
    (witness : Trace)
    (hInclusion : ∀ trace, small trace → large trace)
    (hLarge : large witness)
    (hNotSmall : ¬ small witness)
    (hPositive : 0 < weight witness) :
    weightedMass weight small (left ++ witness :: right) <
      weightedMass weight large (left ++ witness :: right) := by
  rw [weightedMass_append weight small left (witness :: right)]
  rw [weightedMass_append weight large left (witness :: right)]
  simp only [weightedMass, if_neg hNotSmall, if_pos hLarge]
  have hLeft := weightedMass_mono weight small large left hInclusion
  have hRight := weightedMass_mono weight small large right hInclusion
  omega

/-!
MAT-001: inclusion of finite viable languages implies monotonicity of their
common-positive-denominator weighted scores.
-/
theorem MAT001_checked
    {Label : Type u}
    (traceUniverse : FiniteTraceUniverse Label)
    (weight : List Label → Nat)
    (small large : List Label → Prop)
    [DecidablePred small] [DecidablePred large]
    (hTotalPositive : 0 < totalWeight weight traceUniverse.traces)
    (hInclusion : ∀ trace, small trace → large trace) :
    CommonDenominatorScoreLE
      (score traceUniverse weight small)
      (score traceUniverse weight large) := by
  refine ⟨hTotalPositive, rfl, ?_⟩
  exact
    weightedMass_mono weight small large traceUniverse.traces hInclusion

/-!
MAT-002: if a trace in the finite universe lies in `large \ small` and has
positive weight, inclusion upgrades score monotonicity to strict increase.
The split equation is constructive evidence that the witness is in the
finite universe. `traceUniverse.nodup` ensures set-like, non-duplicated counting.
-/
theorem MAT002_checked
    {Label : Type u}
    (traceUniverse : FiniteTraceUniverse Label)
    (weight : List Label → Nat)
    (small large : List Label → Prop)
    [DecidablePred small] [DecidablePred large]
    (left right : List (List Label))
    (witness : List Label)
    (hSplit : traceUniverse.traces = left ++ witness :: right)
    (hTotalPositive : 0 < totalWeight weight traceUniverse.traces)
    (hInclusion : ∀ trace, small trace → large trace)
    (hLarge : large witness)
    (hNotSmall : ¬ small witness)
    (hWitnessPositive : 0 < weight witness) :
    CommonDenominatorScoreLT
      (score traceUniverse weight small)
      (score traceUniverse weight large) := by
  refine ⟨hTotalPositive, rfl, ?_⟩
  change
    weightedMass weight small traceUniverse.traces <
      weightedMass weight large traceUniverse.traces
  rw [hSplit]
  exact
    weightedMass_strict_of_positive_witness
      weight small large left right witness hInclusion
      hLarge hNotSmall hWitnessPositive

#print axioms weightedMass_mono
#print axioms weightedMass_append
#print axioms weightedMass_strict_of_positive_witness
#print axioms MAT001_checked
#print axioms MAT002_checked

end QIKVRT.V2.WeightedConnectability
