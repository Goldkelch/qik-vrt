import QIKVRTFormalization.Foundations
import QIKVRTFormalization.Iteration
import QIKVRTFormalization.Gates
import QIKVRTFormalization.Quantizability
import QIKVRTFormalization.Dimensions
import QIKVRTFormalization.Retrocausality
import QIKVRTFormalization.Claims

/-!
Top-level import for the machine-checked QIK-VRT formal core.

The absence of `axiom`, `sorry`, and `admit` is checked independently by
Gate 20.  Physical correspondence hypotheses are represented as data and
open test obligations, never imported as logical assumptions.
-/
