import QIKVRTFormalization.Foundation.RelativeComplement
import QIKVRTFormalization.Foundation.ImageComplement
import QIKVRTFormalization.Process.Gates
import QIKVRTFormalization.Process.GateCompleteness
import QIKVRTFormalization.Process.ShiftInvariance
import QIKVRTFormalization.Process.OperationalContinuation
import QIKVRTFormalization.Process.ConnectabilitySimulation
import QIKVRTFormalization.Process.WeightedConnectability
import QIKVRTFormalization.Escape.FiniteStages
import QIKVRTFormalization.Retrocausality.ForwardProcess
import QIKVRTFormalization.Retrocausality.Reclassification
import QIKVRTFormalization.Physics.EmpiricalBridge
import QIKVRTFormalization.Definitions.Manuscript
import QIKVRTFormalization.Completion.OpenClaims
import QIKVRTFormalization.Claims.CheckedRegistry
import QIKVRTFormalization.Claims.Batch01
import QIKVRTFormalization.Claims.Batch02
import QIKVRTFormalization.Claims.Batch02Counterexamples
import QIKVRTFormalization.Claims.Batch02Dimensions
import QIKVRTFormalization.Claims.Batch02Factorization
import QIKVRTFormalization.Claims.Batch04
import QIKVRTFormalization.Claims.Batch05
import QIKVRTFormalization.Claims.Completion
import QIKVRTFormalization.WorldFormula.Relations
import QIKVRTFormalization.QuantumFoundations.MeasurementIndependence
import QIKVRTFormalization.Hardware.AuthorityMirrorWitness
import QIKVRTFormalization.Hardware.D3FixedPoint
import QIKVRTFormalization.Hardware.M68000D3Step
import QIKVRTFormalization.Decision.ObservationSufficiency

/-!
Top-level import for the checked QIK-VRT formalization v2 tranches.

This project deliberately depends only on Lean's `Std` library. Every formal
definition environment now has an explicit type, and every theorem-like
manuscript environment has a proposition-indexed kernel proof. Where the locked
source relies on analytic or topological infrastructure not present in `Std`,
the corresponding assumptions are explicit in the checked Lean statement.
Empirical, interpretive, and normative claims remain outside mathematical proof
promotion.

The executable world-formula relation kernel additionally formalizes the
round-trip stage relation, the closed-generative architecture definition,
formal derivability, model satisfaction, interpretation/reference binding,
operationalization, evidence, known-limit recovery, distinctive prediction,
independent validation, dependency closure and artifact identity. Its explicit
countermodel proves that formal establishment alone does not imply physical
qualification.

The quantum-foundations tranche additionally formalizes the exact logical
boundary around measurement independence and superdeterminism: measurement
independence conditionally excludes a measurement-dependent candidate, while a
finite common-cause countermodel proves that structurally local two-wing
responses alone do not establish measurement independence. Physical exclusion
therefore still requires a separately justified QCE freedom certificate and
physical reference/evidence binding.

The hardware-witness tranche formalizes a duplex Authority/Mirror NVM model
with an independent commit witness, fail-closed witnessless divergence,
idempotent recovery, monotone epochs, and witness-bound Effect ACK semantics.
Its mathematical digest is symbolic and injective; operational SHA-256 collision
resistance remains an explicit external implementation assumption.

The bitwidth/D3 tranche preserves the four-state D0 semantics across 8→16→32→64→128
carriers, proves that one bit cannot injectively encode all four states, keeps
`D0=3` distinct from register `D3`, and formalizes the Product-Owner fixed-point
statement as invariance of the D3 projection across any finite control trace.
The M68000 D3-step projection additionally binds the finite machine-visible step:
D0 carries the next four-state decision, D3 remains unchanged, and D2 advances
through the three-state IED cycle.

The decision-sufficiency tranche generalizes the witness theorem: evidence is
deterministically sufficient exactly when observation fibers do not mix histories
requiring different correct actions. Equivalently, the observation kernel must
refine the action kernel. Authority/Mirror/Witness recovery is a specialization.
-/
