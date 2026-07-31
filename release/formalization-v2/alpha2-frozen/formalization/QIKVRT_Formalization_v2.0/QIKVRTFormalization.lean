import QIKVRTFormalization.Foundation.RelativeComplement
import QIKVRTFormalization.Foundation.ImageComplement
import QIKVRTFormalization.Process.Gates
import QIKVRTFormalization.Process.GateCompleteness
import QIKVRTFormalization.Process.ShiftInvariance
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

/-!
Top-level import for the checked QIK-VRT formalization v2 tranches.

This project deliberately depends only on Lean's `Std` library. Every formal
definition environment now has an explicit type, and every theorem-like
manuscript environment has a proposition-indexed kernel proof. Where the locked
source relies on analytic or topological infrastructure not present in `Std`,
the corresponding assumptions are explicit in the checked Lean statement.
Empirical, interpretive, and normative claims remain outside mathematical proof
promotion.
-/
