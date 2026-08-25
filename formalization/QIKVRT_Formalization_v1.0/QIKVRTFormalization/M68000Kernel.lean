import QIKVRTFormalization.Gates

/-!
# Finite executable projection for the Motorola 68000 gate kernel

This module narrows the already-proved `evaluateGate` control rule to two
explicit Boolean certificate bits.  It does not compile arbitrary predicates
or claim physical M68000 execution.  The projection preserves the formal gate
priority exactly: BLOCK dominates PASS; absent both certificates the result is
CONTINUE.
-/

namespace QIKVRT

/-- Finite executable projection of `evaluateGate`.

`passCertificate` and `blockCertificate` are evidence-presence bits.  The
returned `Gate` is the same three-state gate used by `Gates.lean`.
-/
def evaluateBooleanGate (passCertificate blockCertificate : Bool) : Gate :=
  if blockCertificate then Gate.block
  else if passCertificate then Gate.pass
  else Gate.continue

@[simp] theorem evaluateBooleanGate_none :
    evaluateBooleanGate false false = Gate.continue := rfl

@[simp] theorem evaluateBooleanGate_pass :
    evaluateBooleanGate true false = Gate.pass := rfl

@[simp] theorem evaluateBooleanGate_block :
    evaluateBooleanGate false true = Gate.block := rfl

@[simp] theorem evaluateBooleanGate_block_dominates_pass :
    evaluateBooleanGate true true = Gate.block := rfl

/-- If the two Boolean bits exactly reflect the proposition-valued
certificates of a `GateSpecification`, the finite projection is extensionally
identical to the formal evaluator. -/
theorem evaluateGate_boolean_projection
    (spec : GateSpecification α) (n : Nat) (x : α)
    (passCertificate blockCertificate : Bool)
    (hPass : spec.passCertificate n x ↔ passCertificate = true)
    (hBlock : spec.blockCertificate n x ↔ blockCertificate = true) :
    evaluateGate spec n x = evaluateBooleanGate passCertificate blockCertificate := by
  classical
  cases blockCertificate <;> cases passCertificate <;>
    simp_all [evaluateGate, evaluateBooleanGate]

/-- The executable projection never upgrades missing evidence to PASS/BLOCK. -/
theorem evaluateBooleanGate_no_certificates_nonterminal :
    evaluateBooleanGate false false = Gate.continue := rfl

end QIKVRT
