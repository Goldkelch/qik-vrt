import QIKVRTFormalization.Hardware.AuthorityMirrorWitness

/-!
# D3 projection fixed point over the 8-bit IED carrier

This module gives the repository-precise meaning of the Product-Owner statement
"Register 3 ist Fixpunkt!".

The existing four-state decision ABI remains in `D0`: the semantic values are
0=NOOP, 1=HOLD, 2=REOBSERVE, and 3=REQUEST_AUTHORITY.  `D3` is a distinct data
register.  The fixed-point claim is therefore modeled as a projection invariant:
the full machine state may advance, while its `D3` byte remains unchanged.

The IED phase cycles Intelligence → Evidence → Development → Intelligence.
The theorem over arbitrary finite traces is the rigorous unbounded-iteration
counterpart of the infinity framing; it is not a claim of completed physical
infinity.
-/

namespace QIKVRT.V2.D3FixedPoint

open QIKVRT.V2.BitwidthCausalMachine

/-- One 8-bit carrier. -/
abbrev Byte := Fin 256

/-- Register identity is distinct from a value stored in another register. -/
inductive RegisterIndex where
  | d0
  | d3
  deriving DecidableEq, Repr

/-- The authorial IED cycle. -/
inductive IEDPhase where
  | intelligence
  | evidence
  | development
  deriving DecidableEq, Repr

def IEDPhase.next : IEDPhase → IEDPhase
  | .intelligence => .evidence
  | .evidence => .development
  | .development => .intelligence

/-- Embed the four-state semantic code in one 8-bit carrier. -/
def decisionByte (d : Decision) : Byte :=
  ⟨d.code.val, Nat.lt_trans d.code.isLt (by decide : 4 < 256)⟩

/--
`D0` carries the current decision; `D3` carries the stable semantic witness.
The phase may move around the IED cycle.
-/
structure RegisterFile where
  d0 : Decision
  d3 : Byte
  phase : IEDPhase
  deriving DecidableEq, Repr

/-- One admissible control step may change `D0` and the IED phase, never `D3`. -/
def step (nextDecision : Decision) (s : RegisterFile) : RegisterFile :=
  { d0 := nextDecision
    d3 := s.d3
    phase := s.phase.next }

/-- Execute an arbitrary finite decision trace. -/
def run : List Decision → RegisterFile → RegisterFile
  | [], s => s
  | d :: ds, s => run ds (step d s)

/-- The 8-bit representation preserves the exact four-state semantic code. -/
theorem decision_byte_preserves_code (d : Decision) :
    (decisionByte d).val = d.code.val := rfl

/-- `D0=3` denotes REQUEST_AUTHORITY in the existing ABI. -/
theorem d0_value_three_is_request_authority :
    Decision.requestAuthority.code = (3 : Fin 4) := rfl

/-- `D0=3` and register `D3` are not the same architectural object. -/
theorem d0_and_d3_are_distinct_registers :
    RegisterIndex.d0 ≠ RegisterIndex.d3 := by decide

/-- Strict fixed-point statement for the `D3` projection of one step. -/
theorem d3_projection_fixed_under_step (d : Decision) (s : RegisterFile) :
    (step d s).d3 = s.d3 := rfl

/--
For every finite trace, without any fixed length bound, the `D3` projection is
unchanged even though the full state may evolve.
-/
theorem d3_projection_fixed_under_any_finite_trace
    (trace : List Decision) (s : RegisterFile) :
    (run trace s).d3 = s.d3 := by
  induction trace generalizing s with
  | nil => rfl
  | cons d ds ih =>
      calc
        (run (d :: ds) s).d3 = (run ds (step d s)).d3 := rfl
        _ = (step d s).d3 := ih (step d s)
        _ = s.d3 := rfl

/--
One complete IED cycle returns the phase and simultaneously preserves `D3`.
The changing phase is a three-cycle; the stable `D3` projection is the fixed
point.
-/
theorem one_ied_cycle_returns_phase_and_preserves_d3
    (a b c : Decision) (s : RegisterFile) :
    (run [a, b, c] s).phase = s.phase ∧
    (run [a, b, c] s).d3 = s.d3 := by
  constructor
  · change s.phase.next.next.next = s.phase
    cases s.phase <;> rfl
  · exact d3_projection_fixed_under_any_finite_trace [a, b, c] s

end QIKVRT.V2.D3FixedPoint
