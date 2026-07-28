-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import Std

/-!
# QIK-VRT quantum-classical runtime assurance model

This file formalizes only the abstract transaction and release semantics used by
the article "Vom verantwortungsgebundenen Erkenntnisprozess zur virtuellen
Wirkungsmaschine".

It does not model quantum mechanics, a quantum instruction set, hardware noise,
error correction, a concrete QPU adapter, or empirical performance.  The kernel
results establish logical properties of the evidence, uncertainty, gate,
backend-envelope, and effect-acknowledgement abstraction.
-/

namespace QIKVRT.QuantumClassicalRuntime.V1

inductive BackendKind where
  | simulator
  | qpu
deriving DecidableEq, Repr

inductive RuntimeState where
  | continue
  | block
  | effectAcknowledged
deriving DecidableEq, Repr

structure Snapshot where
  problemBound : Bool
  sourceBound : Bool
  circuitOrIrBound : Bool
  backendBound : Bool
  measurementAvailable : Bool
  uncertaintyClassified : Bool
  postprocessingBound : Bool
  claimBound : Bool
  gatePassed : Bool
  effectObserved : Bool
  measurementDeterministic : Bool
  backend : BackendKind
deriving Repr

def responsibleRelease (snapshot : Snapshot) : Bool :=
  snapshot.problemBound &&
  snapshot.sourceBound &&
  snapshot.circuitOrIrBound &&
  snapshot.backendBound &&
  snapshot.measurementAvailable &&
  snapshot.uncertaintyClassified &&
  snapshot.postprocessingBound &&
  snapshot.claimBound &&
  snapshot.gatePassed &&
  snapshot.effectObserved

def ReleaseConditions (snapshot : Snapshot) : Prop :=
  snapshot.problemBound = true ∧
  snapshot.sourceBound = true ∧
  snapshot.circuitOrIrBound = true ∧
  snapshot.backendBound = true ∧
  snapshot.measurementAvailable = true ∧
  snapshot.uncertaintyClassified = true ∧
  snapshot.postprocessingBound = true ∧
  snapshot.claimBound = true ∧
  snapshot.gatePassed = true ∧
  snapshot.effectObserved = true

theorem responsibleRelease_eq_true_iff (snapshot : Snapshot) :
    responsibleRelease snapshot = true ↔ ReleaseConditions snapshot := by
  simp [responsibleRelease, ReleaseConditions, and_assoc]

theorem responsibleRelease_requires_uncertainty (snapshot : Snapshot) :
    responsibleRelease snapshot = true →
      snapshot.uncertaintyClassified = true := by
  simp [responsibleRelease]

theorem responsibleRelease_requires_gate (snapshot : Snapshot) :
    responsibleRelease snapshot = true →
      snapshot.gatePassed = true := by
  simp [responsibleRelease]

theorem responsibleRelease_requires_effect_observation (snapshot : Snapshot) :
    responsibleRelease snapshot = true →
      snapshot.effectObserved = true := by
  simp [responsibleRelease]

def selectState (snapshot : Snapshot) : RuntimeState :=
  if responsibleRelease snapshot = true then .effectAcknowledged
  else if snapshot.backendBound = false then .block
  else .continue

def probabilisticButResponsible : Snapshot where
  problemBound := true
  sourceBound := true
  circuitOrIrBound := true
  backendBound := true
  measurementAvailable := true
  uncertaintyClassified := true
  postprocessingBound := true
  claimBound := true
  gatePassed := true
  effectObserved := true
  measurementDeterministic := false
  backend := .qpu

theorem responsibility_does_not_force_deterministic_measurement :
    ∃ snapshot,
      responsibleRelease snapshot = true ∧
      snapshot.measurementDeterministic = false := by
  exact ⟨probabilisticButResponsible, by decide, rfl⟩

def measurementOnly : Snapshot where
  problemBound := false
  sourceBound := false
  circuitOrIrBound := false
  backendBound := true
  measurementAvailable := true
  uncertaintyClassified := false
  postprocessingBound := false
  claimBound := false
  gatePassed := false
  effectObserved := false
  measurementDeterministic := false
  backend := .qpu

theorem measurement_alone_does_not_authorize_release :
    measurementOnly.measurementAvailable = true ∧
    responsibleRelease measurementOnly = false := by
  decide

structure EnvelopeShape where
  requestIdPresent : Bool
  problemBindingPresent : Bool
  sourceBindingPresent : Bool
  circuitOrIrBindingPresent : Bool
  backendBindingPresent : Bool
  measurementSchemaPresent : Bool
  uncertaintySchemaPresent : Bool
  postprocessingSchemaPresent : Bool
  claimSchemaPresent : Bool
  gateSchemaPresent : Bool
  effectAckSchemaPresent : Bool
deriving DecidableEq, Repr

structure RuntimeEnvelope where
  backend : BackendKind
  shape : EnvelopeShape
deriving Repr

def replaceBackend
    (envelope : RuntimeEnvelope)
    (backend : BackendKind) : RuntimeEnvelope :=
  { envelope with backend := backend }

theorem backend_replacement_preserves_shape
    (envelope : RuntimeEnvelope)
    (left right : BackendKind) :
    (replaceBackend envelope left).shape =
      (replaceBackend envelope right).shape := by
  rfl

def completeShape : EnvelopeShape where
  requestIdPresent := true
  problemBindingPresent := true
  sourceBindingPresent := true
  circuitOrIrBindingPresent := true
  backendBindingPresent := true
  measurementSchemaPresent := true
  uncertaintySchemaPresent := true
  postprocessingSchemaPresent := true
  claimSchemaPresent := true
  gateSchemaPresent := true
  effectAckSchemaPresent := true

def simulatorEnvelope : RuntimeEnvelope where
  backend := .simulator
  shape := completeShape

def qpuEnvelope : RuntimeEnvelope where
  backend := .qpu
  shape := completeShape

theorem simulator_and_qpu_share_complete_shape :
    simulatorEnvelope.shape = qpuEnvelope.shape := by
  rfl

theorem selectState_effect_ack_iff (snapshot : Snapshot) :
    selectState snapshot = .effectAcknowledged ↔
      responsibleRelease snapshot = true := by
  unfold selectState
  by_cases h : responsibleRelease snapshot = true
  · simp [h]
  · simp [h]

end QIKVRT.QuantumClassicalRuntime.V1
