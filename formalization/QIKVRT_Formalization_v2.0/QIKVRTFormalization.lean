import QIKVRTFormalization.Foundation.RelativeComplement
import QIKVRTFormalization.Foundation.ImageComplement
import QIKVRTFormalization.Process.Gates
import QIKVRTFormalization.Process.GateCompleteness
import QIKVRTFormalization.Process.ShiftInvariance
import QIKVRTFormalization.Retrocausality.ForwardProcess
import QIKVRTFormalization.Retrocausality.Reclassification
import QIKVRTFormalization.Physics.EmpiricalBridge
import QIKVRTFormalization.Claims.CheckedRegistry
import QIKVRTFormalization.Claims.Batch01
import QIKVRTFormalization.Claims.Batch02
import QIKVRTFormalization.Claims.Batch02Counterexamples
import QIKVRTFormalization.Claims.Batch02Dimensions
import QIKVRTFormalization.Claims.Batch02Factorization
import QIKVRTFormalization.Claims.Batch04

/-!
Top-level import for the checked QIK-VRT formalization v2 tranches.

This project deliberately depends only on Lean's `Std` library. The theorem
wrappers expose exact proposition-indexed proofs. Aggregate manuscript claims
whose current proof covers only a source subclaim remain pending in the claim
graph and are not promoted by this import.
-/
