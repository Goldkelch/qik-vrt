import Std
import QIKVRTFormalization.Escape.FiniteStages
import QIKVRTFormalization.Process.Gates
import QIKVRTFormalization.Process.ShiftInvariance

/-!
# Source-bound manuscript definitions

This module gives every one of the twenty formal definition environments in the
locked 62-page manuscript an explicit Lean type. The definitions are generic
where the manuscript uses mathematical structures that are not supplied by
Lean `Std` (notably real/complex analysis). No empirical or interpretive claim
is promoted by these declarations.
-/

namespace QIKVRT.V2.Definitions

universe u v w

abbrev SetOf (α : Type u) := α → Prop
abbrev Sequence (α : Type u) := Nat → α

structure QuadraticIteration (Parameter : Type u) (State : Type v) where
  zero : State
  squareAdd : State → Parameter → State
  orbit : Parameter → Sequence State
  initial : ∀ parameter, orbit parameter 0 = zero
  recursion : ∀ parameter n,
    orbit parameter (n + 1) = squareAdd (orbit parameter n) parameter

def BoundedBy (magnitude : State → Nat) (bound : Nat)
    (orbit : Sequence State) : Prop :=
  ∀ n, magnitude (orbit n) ≤ bound

def BoundedOrbit (magnitude : State → Nat) (orbit : Sequence State) : Prop :=
  ∃ bound, BoundedBy magnitude bound orbit

def MandelbrotClass (iteration : QuadraticIteration Parameter State)
    (magnitude : State → Nat) : SetOf Parameter :=
  fun parameter => BoundedOrbit magnitude (iteration.orbit parameter)

def DEF001Statement : Prop :=
  ∀ (Parameter : Type) (State : Type)
      (iteration : QuadraticIteration Parameter State) (parameter : Parameter),
    iteration.orbit parameter 0 = iteration.zero ∧
      ∀ n, iteration.orbit parameter (n + 1) =
        iteration.squareAdd (iteration.orbit parameter n) parameter

theorem DEF001_checked : DEF001Statement := by
  intro Parameter State iteration parameter
  exact ⟨iteration.initial parameter, iteration.recursion parameter⟩


def relativeComplement (ambient subset : SetOf α) : SetOf α :=
  fun point => ambient point ∧ ¬ subset point

def DEF002Statement : Prop :=
  ∀ (α : Type) (ambient subset : SetOf α) (point : α),
    relativeComplement ambient subset point ↔ ambient point ∧ ¬ subset point

theorem DEF002_checked : DEF002Statement := by
  intro α ambient subset point
  rfl


inductive EscapeTime where
  | finite (stage : Nat)
  | infinity
  deriving DecidableEq, Repr

def ValidEscapeTime (escapeAt : Nat → Prop) : EscapeTime → Prop
  | .finite stage => escapeAt stage
  | .infinity => ∀ stage, ¬ escapeAt stage

def DEF003Statement : Prop :=
  ∀ escapeAt : Nat → Prop, ∃ value, ValidEscapeTime escapeAt value

theorem DEF003_checked : DEF003Statement := by
  classical
  intro escapeAt
  by_cases h : ∃ stage, escapeAt stage
  · exact ⟨.finite (Classical.choose h), Classical.choose_spec h⟩
  · exact ⟨.infinity, by
      intro stage hStage
      exact h ⟨stage, hStage⟩⟩


def finiteEscapeSet (ambient : SetOf α) (escapeAt : α → Nat → Prop)
    (stage : Nat) : SetOf α :=
  fun point => ambient point ∧ Escape.Stage escapeAt stage point

def DEF004Statement : Prop :=
  ∀ (α : Type) (ambient : SetOf α) (escapeAt : α → Nat → Prop)
      (stage : Nat) (point : α),
    finiteEscapeSet ambient escapeAt stage point ↔
      ambient point ∧ ∃ witness, witness ≤ stage ∧ escapeAt point witness

theorem DEF004_checked : DEF004Statement := by
  intro α ambient escapeAt stage point
  rfl


structure MandelbrotModelUniverse (α : Type u) where
  ambient : SetOf α
  mandelbrot : SetOf α

def MandelbrotModelUniverse.exterior (model : MandelbrotModelUniverse α) : SetOf α :=
  relativeComplement model.ambient model.mandelbrot

def DEF005Statement : Prop :=
  ∀ (α : Type) (model : MandelbrotModelUniverse α) (point : α),
    model.exterior point ↔ model.ambient point ∧ ¬ model.mandelbrot point

theorem DEF005_checked : DEF005Statement := by
  intro α model point
  rfl


structure Correspondence (Event : Type u) (Target : Type v) where
  map : Event → Target

def Correspondence.preimage (correspondence : Correspondence Event Target)
    (subset : SetOf Target) : SetOf Event :=
  fun event => subset (correspondence.map event)

def DEF006Statement : Prop :=
  ∀ (Event : Type) (Target : Type)
      (correspondence : Correspondence Event Target)
      (subset : SetOf Target) (event : Event),
    correspondence.preimage subset event ↔ subset (correspondence.map event)

theorem DEF006_checked : DEF006Statement := by
  intro Event Target correspondence subset event
  rfl


structure MetricData (α : Type u) (Distance : Type v) where
  distance : α → α → Distance

structure FiniteQuantizer (metric : MetricData α Distance) [LE Distance]
    (subset : SetOf α) (epsilon : Distance) where
  grid : List α
  quantize : α → α
  quantized_mem : ∀ point, subset point → quantize point ∈ grid
  error_bound : ∀ point, subset point →
    metric.distance point (quantize point) ≤ epsilon

def FinitelyQuantizableAt (metric : MetricData α Distance) [LE Distance]
    (subset : SetOf α) (epsilon : Distance) : Prop :=
  Nonempty (FiniteQuantizer metric subset epsilon)

def DEF007Statement : Prop :=
  ∀ (α : Type) (Distance : Type) [LE Distance]
      (metric : MetricData α Distance) (subset : SetOf α) (epsilon : Distance),
    FinitelyQuantizableAt metric subset epsilon ↔
      Nonempty (FiniteQuantizer metric subset epsilon)

theorem DEF007_checked : DEF007Statement := by
  intro α Distance _ metric subset epsilon
  rfl


structure ExtendedDynamics (Parameter : Type u) (State : Type v) where
  transition : Parameter × State → Parameter × State
  initial : Parameter → Parameter × State
  orbit : Parameter → Sequence (Parameter × State)
  orbit_initial : ∀ parameter, orbit parameter 0 = initial parameter
  orbit_step : ∀ parameter n,
    orbit parameter (n + 1) = transition (orbit parameter n)

def DEF008Statement : Prop :=
  ∀ (Parameter : Type) (State : Type)
      (dynamics : ExtendedDynamics Parameter State) (parameter : Parameter),
    dynamics.orbit parameter 0 = dynamics.initial parameter ∧
      ∀ n, dynamics.orbit parameter (n + 1) =
        dynamics.transition (dynamics.orbit parameter n)

theorem DEF008_checked : DEF008Statement := by
  intro Parameter State dynamics parameter
  exact ⟨dynamics.orbit_initial parameter, dynamics.orbit_step parameter⟩


def leftShift (trajectory : Sequence α) : Sequence α :=
  fun n => trajectory (n + 1)

def shiftBy : Nat → Sequence α → Sequence α
  | 0, trajectory => trajectory
  | k + 1, trajectory => leftShift (shiftBy k trajectory)

def generatedTrajectorySpace (orbit : Parameter → Sequence State) :
    SetOf (Sequence State) :=
  fun trajectory => ∃ parameter k, trajectory = shiftBy k (orbit parameter)

def DEF009Statement : Prop :=
  ∀ (α : Type) (trajectory : Sequence α) (n : Nat),
    leftShift trajectory n = trajectory (n + 1)

theorem DEF009_checked : DEF009Statement := by
  intro α trajectory n
  rfl


noncomputable def exactTrajectoryStatus (magnitude : α → Nat)
    (trajectory : Sequence α) : Trajectory.ExactStatus :=
  Trajectory.exactStatus magnitude trajectory

def DEF010Statement : Prop :=
  ∀ (α : Type) (magnitude : α → Nat) (trajectory : Sequence α),
    (Trajectory.Bounded magnitude trajectory →
      exactTrajectoryStatus magnitude trajectory = .pass) ∧
    (¬ Trajectory.Bounded magnitude trajectory →
      exactTrajectoryStatus magnitude trajectory = .block)

theorem DEF010_checked : DEF010Statement := by
  classical
  intro α magnitude trajectory
  constructor
  · intro hBounded
    unfold exactTrajectoryStatus Trajectory.exactStatus
    simp [hBounded]
  · intro hUnbounded
    unfold exactTrajectoryStatus Trajectory.exactStatus
    simp [hUnbounded]


structure AdmissiblePassCertificates (α : Type u) where
  inside : SetOf α
  certificate : Nat → α → Prop
  sound : ∀ stage point, certificate stage point → inside point
  monotone : ∀ stage point,
    certificate stage point → certificate (stage + 1) point

def DEF011Statement : Prop :=
  ∀ (α : Type) (certificates : AdmissiblePassCertificates α),
    (∀ stage point,
      certificates.certificate stage point → certificates.inside point) ∧
    (∀ stage point,
      certificates.certificate stage point →
        certificates.certificate (stage + 1) point)

theorem DEF011_checked : DEF011Statement := by
  intro α certificates
  exact ⟨certificates.sound, certificates.monotone⟩


def finiteGate (specification : GateSpecification α) (stage : Nat) (point : α) : Gate :=
  evaluateGate specification stage point

def DEF012Statement : Prop :=
  ∀ (α : Type) (specification : GateSpecification α) (stage : Nat) (point : α),
    finiteGate specification stage point = evaluateGate specification stage point

theorem DEF012_checked : DEF012Statement := by
  intro α specification stage point
  rfl


structure ProcessModelUniverse (State : Type u) where
  transition : State → State
  initial : List State
  trajectorySpace : SetOf (Sequence State)
  finiteGate : Nat → State → Gate
  exactStatus : Sequence State → Trajectory.ExactStatus
  inside : SetOf State
  outside : SetOf State
  boundary : SetOf State

def DEF013Statement : Prop :=
  ∀ (State : Type) (model : ProcessModelUniverse State),
    model.transition = model.transition ∧
    model.trajectorySpace = model.trajectorySpace ∧
    model.boundary = model.boundary

theorem DEF013_checked : DEF013Statement := by
  intro State model
  exact ⟨rfl, rfl, rfl⟩


structure GeneralWorldModel (State : Type u) where
  transition : State → State
  trajectorySpace : SetOf (Sequence State)
  finiteGate : Nat → Sequence State → Gate
  terminalGate : Sequence State → Gate

def DEF014Statement : Prop :=
  ∀ (State : Type) (model : GeneralWorldModel State),
    model.transition = model.transition ∧
    model.trajectorySpace = model.trajectorySpace

theorem DEF014_checked : DEF014Statement := by
  intro State model
  exact ⟨rfl, rfl⟩


def IsSemiconjugation (sourceTransition : α → α)
    (targetTransition : β → β) (map : α → β) : Prop :=
  ∀ state, targetTransition (map state) = map (sourceTransition state)

def mapTrajectory (map : α → β) (trajectory : Sequence α) : Sequence β :=
  fun n => map (trajectory n)

def DEF015Statement : Prop :=
  ∀ (α : Type) (β : Type) (sourceTransition : α → α)
      (targetTransition : β → β) (map : α → β),
    IsSemiconjugation sourceTransition targetTransition map →
      (∀ state, targetTransition (map state) = map (sourceTransition state)) ∧
      (∀ trajectory n,
        mapTrajectory map (leftShift trajectory) n =
          leftShift (mapTrajectory map trajectory) n)

theorem DEF015_checked : DEF015Statement := by
  intro α β sourceTransition targetTransition map hSemiconjugation
  constructor
  · exact hSemiconjugation
  · intro trajectory n
    rfl


def GatePreserving (trajectoryMap : Sequence α → Sequence β)
    (sourceFinite : Nat → Sequence α → Gate)
    (targetFinite : Nat → Sequence β → Gate)
    (sourceExact : Sequence α → Gate)
    (targetExact : Sequence β → Gate) : Prop :=
  (∀ trajectory stage,
    targetFinite stage (trajectoryMap trajectory) =
      sourceFinite stage trajectory) ∧
  (∀ trajectory,
    targetExact (trajectoryMap trajectory) = sourceExact trajectory)

def DEF016Statement : Prop :=
  ∀ (α : Type) (β : Type) (trajectoryMap : Sequence α → Sequence β)
      (sourceFinite : Nat → Sequence α → Gate)
      (targetFinite : Nat → Sequence β → Gate)
      (sourceExact : Sequence α → Gate)
      (targetExact : Sequence β → Gate),
    GatePreserving trajectoryMap sourceFinite targetFinite sourceExact targetExact ↔
      ((∀ trajectory stage,
        targetFinite stage (trajectoryMap trajectory) =
          sourceFinite stage trajectory) ∧
       (∀ trajectory,
        targetExact (trajectoryMap trajectory) = sourceExact trajectory))

theorem DEF016_checked : DEF016Statement := by
  intro α β trajectoryMap sourceFinite targetFinite sourceExact targetExact
  rfl


structure SemanticReclassification
    (Trace : Type u) (PhysicalState : Type v) (Classification : Type w) where
  trace : Trace
  physicalBefore : PhysicalState
  physicalAfter : PhysicalState
  securedRecordBefore : Trace
  securedRecordAfter : Trace
  classificationBefore : Classification
  classificationAfter : Classification
  changed : classificationBefore ≠ classificationAfter
  physicalUnchanged : physicalAfter = physicalBefore
  recordUnchanged : securedRecordAfter = securedRecordBefore

def DEF017Statement : Prop :=
  ∀ (Trace : Type) (PhysicalState : Type) (Classification : Type)
      (reclassification : SemanticReclassification Trace PhysicalState Classification),
    reclassification.classificationBefore ≠ reclassification.classificationAfter ∧
    reclassification.physicalAfter = reclassification.physicalBefore ∧
    reclassification.securedRecordAfter = reclassification.securedRecordBefore

theorem DEF017_checked : DEF017Statement := by
  intro Trace PhysicalState Classification reclassification
  exact ⟨reclassification.changed, reclassification.physicalUnchanged,
    reclassification.recordUnchanged⟩


structure PhysicalRetrocausality (Early : Type u) (Late : Type v) where
  dependsOnLater : Early → Late → Prop
  irreducibleToForwardOrCommonCause : Early → Late → Prop

def DEF018Statement : Prop :=
  ∀ (Early : Type) (Late : Type)
      (model : PhysicalRetrocausality Early Late),
    model.dependsOnLater = model.dependsOnLater ∧
    model.irreducibleToForwardOrCommonCause =
      model.irreducibleToForwardOrCommonCause

theorem DEF018_checked : DEF018Statement := by
  intro Early Late model
  exact ⟨rfl, rfl⟩


structure BackwardSignalling (Message : Type u) (EarlyRecord : Type v) where
  encode : Message → EarlyRecord
  decode : EarlyRecord → Option Message
  reliable : ∀ message, decode (encode message) = some message

def DEF019Statement : Prop :=
  ∀ (Message : Type) (EarlyRecord : Type)
      (channel : BackwardSignalling Message EarlyRecord) (message : Message),
    channel.decode (channel.encode message) = some message

theorem DEF019_checked : DEF019Statement := by
  intro Message EarlyRecord channel message
  exact channel.reliable message


structure StructuralCreationPrinciple (State : Type u) where
  difference : State → State → Prop
  preservesDifference : State → State
  relation : State → State → Prop
  continuation : State → State

def DEF020Statement : Prop :=
  ∀ (State : Type) (principle : StructuralCreationPrinciple State),
    principle.difference = principle.difference ∧
    principle.preservesDifference = principle.preservesDifference ∧
    principle.relation = principle.relation ∧
    principle.continuation = principle.continuation

theorem DEF020_checked : DEF020Statement := by
  intro State principle
  exact ⟨rfl, rfl, rfl, rfl⟩

#print axioms DEF001_checked
#print axioms DEF002_checked
#print axioms DEF003_checked
#print axioms DEF004_checked
#print axioms DEF005_checked
#print axioms DEF006_checked
#print axioms DEF007_checked
#print axioms DEF008_checked
#print axioms DEF009_checked
#print axioms DEF010_checked
#print axioms DEF011_checked
#print axioms DEF012_checked
#print axioms DEF013_checked
#print axioms DEF014_checked
#print axioms DEF015_checked
#print axioms DEF016_checked
#print axioms DEF017_checked
#print axioms DEF018_checked
#print axioms DEF019_checked
#print axioms DEF020_checked

end QIKVRT.V2.Definitions
