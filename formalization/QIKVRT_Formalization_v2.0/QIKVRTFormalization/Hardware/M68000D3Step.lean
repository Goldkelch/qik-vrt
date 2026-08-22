import QIKVRTFormalization.Hardware.D3FixedPoint

/-!
# Finite Motorola 68000 projection of the proved D0/D3 lifecycle step

This module exposes the machine-observable finite projection of the already
proved `D3FixedPoint.step` rule.  It does not add a physical-execution claim.
-/

namespace QIKVRT.V2.M68000D3Step

open QIKVRT.V2.BitwidthCausalMachine
open QIKVRT.V2.D3FixedPoint

/-- Compact three-state code for the IED phase used by the machine projection. -/
def phaseCode : IEDPhase → Fin 3
  | .intelligence => 0
  | .evidence => 1
  | .development => 2

@[simp] theorem phaseCode_next_intelligence :
    phaseCode IEDPhase.intelligence.next = 1 := rfl

@[simp] theorem phaseCode_next_evidence :
    phaseCode IEDPhase.evidence.next = 2 := rfl

@[simp] theorem phaseCode_next_development :
    phaseCode IEDPhase.development.next = 0 := rfl

/-- The finite phase transition is exactly increment modulo three. -/
theorem phaseCode_next_mod_three (p : IEDPhase) :
    (phaseCode p.next).val = ((phaseCode p).val + 1) % 3 := by
  cases p <;> decide

/-- Machine-visible projection of one formal step: D0 becomes the next decision,
D3 is preserved exactly, and D2 advances through the three-state phase cycle. -/
def machineProjection (nextDecision : Decision) (s : RegisterFile) : Fin 4 × Byte × Fin 3 :=
  (nextDecision.code, s.d3, phaseCode s.phase.next)

/-- The machine projection is extensionally the projection of the formal step. -/
theorem machineProjection_refines_step (nextDecision : Decision) (s : RegisterFile) :
    machineProjection nextDecision s =
      ((step nextDecision s).d0.code,
       (step nextDecision s).d3,
       phaseCode (step nextDecision s).phase) := rfl

/-- In particular, the compiled step must not mutate the D3 witness. -/
theorem machineProjection_preserves_d3 (nextDecision : Decision) (s : RegisterFile) :
    (machineProjection nextDecision s).2.1 = s.d3 := rfl

end QIKVRT.V2.M68000D3Step
