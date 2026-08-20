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
import QIKVRTFormalization.Decision.ObservationSufficiency
import QIKVRTFormalization.Decision.PredictiveOptimality

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

The decision-sufficiency tranche generalizes the witness theorem: evidence is
deterministically sufficient exactly when observation fibers do not mix histories
requiring different correct actions. Equivalently, the observation kernel must
refine the action kernel. Authority/Mirror/Witness recovery is a specialization.

The predictive-optimality tranche makes the equal-information comparison
explicit.  Admissibility and the objective preorder are independent inputs;
under sufficient bound information, an independently certified optimal correct
prediction transfers through the unique reachable selector, so no admissible
comparator under the same information can be strictly preferred by that
objective.  This remains a formal decision result, not an empirical claim for
an unspecified loss function or a physical measurement beyond a knowledge
boundary.
-/
