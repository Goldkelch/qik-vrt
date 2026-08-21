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

/-!
# Plural scaling and distinct-unit support

This module gives the repository-precise formal boundary for Product-Owner
Receipt #221, `SKALIERUNG_⊕_MEHR_ALS_EINS_⊕_WIRKUNG`.

The source records a concrete development fact: one artificial-cognitive system
unit did not suffice for the author's work and more than one was needed.  The
formal theorem does not universalize that autobiographical observation.  It
isolates the structural relation that genuinely requires plurality: one unit
cannot provide support from two distinct unit identities.

Horizontal scaling by adding a unit is kept separate from vertical carrier-width
scaling.  Unit count is not bit width; one system unit is not one bit, and more
than one unit is not one byte.  Plurality enables comparison and distinct-unit
support, but does not by itself imply agreement, correctness, fault tolerance,
independent review authority, or an observed effect.
-/

namespace QIKVRT.V2.PluralScaling

open QIKVRT.V2.BitwidthCausalMachine
open QIKVRT.V2.D3FixedPoint

/-- Two structurally distinct unit identities. -/
abbrev TwoUnits := Sum Unit Unit

/-- Every unit reports the same decision. -/
def Agreement {ι : Type} (report : ι → Decision) : Prop :=
  ∀ i j, report i = report j

/-- At least two reports differ. -/
def Divergence {ι : Type} (report : ι → Decision) : Prop :=
  ∃ i j, report i ≠ report j

/--
The same decision is supported by two distinct unit identities.  Distinct unit
identity is a structural property, not a claim of independent review authority.
-/
def DistinctUnitSupport {ι : Type} (report : ι → Decision)
    (decision : Decision) : Prop :=
  ∃ i j, i ≠ j ∧ report i = decision ∧ report j = decision

/-- One unit agrees with itself; this is vacuous agreement, not peer support. -/
theorem one_unit_agreement_is_vacuous (report : Unit → Decision) :
    Agreement report := by
  intro i j
  cases i
  cases j
  rfl

/-- A single unit cannot supply two distinct supporting identities. -/
theorem one_unit_has_no_distinct_support
    (report : Unit → Decision) (decision : Decision) :
    ¬ DistinctUnitSupport report decision := by
  intro h
  rcases h with ⟨i, j, hne, _hi, _hj⟩
  cases i
  cases j
  exact hne rfl

/-- More than one unit does not automatically imply agreement. -/
def divergentTwoUnitReport : TwoUnits → Decision
  | .inl _ => .noop
  | .inr _ => .hold

/-- Two units can genuinely diverge. -/
theorem two_units_can_diverge : Divergence divergentTwoUnitReport := by
  exact ⟨Sum.inl (), Sum.inr (), by decide⟩

/-- Agreement and divergence cannot hold for the same report family. -/
theorem agreement_excludes_divergence {ι : Type}
    {report : ι → Decision} (hAgreement : Agreement report) :
    ¬ Divergence report := by
  intro hDivergence
  rcases hDivergence with ⟨i, j, hne⟩
  exact hne (hAgreement i j)

/--
With two distinct units, agreement yields support from two distinct identities.
The theorem proves a structural relation only; it does not prove correctness or
independent authority.
-/
theorem two_unit_agreement_yields_distinct_support
    (report : TwoUnits → Decision) (hAgreement : Agreement report) :
    ∃ decision, DistinctUnitSupport report decision := by
  let left : TwoUnits := Sum.inl ()
  let right : TwoUnits := Sum.inr ()
  refine ⟨report left, left, right, ?_, rfl, ?_⟩
  · decide
  · exact hAgreement right left

/--
Fail-closed collective triage.  Stale evidence is reobserved; current divergent
evidence holds; current agreement without shared authority requests authority;
only current, agreeing, authority-bound evidence returns the proposal.
-/
def collectiveControl : Bool → Bool → Bool → Decision → Decision
  | false, _, _, _ => .reobserve
  | true, false, _, _ => .hold
  | true, true, false, _ => .requestAuthority
  | true, true, true, proposal => proposal

/-- Stale evidence selects REOBSERVE. -/
theorem stale_evidence_reobserves
    (evidenceAgrees authorityBound : Bool) (proposal : Decision) :
    collectiveControl false evidenceAgrees authorityBound proposal = .reobserve := rfl

/-- Current but divergent evidence selects HOLD. -/
theorem current_divergence_holds
    (authorityBound : Bool) (proposal : Decision) :
    collectiveControl true false authorityBound proposal = .hold := rfl

/-- Current agreement without shared authority selects REQUEST_AUTHORITY. -/
theorem current_agreement_without_authority_requests
    (proposal : Decision) :
    collectiveControl true true false proposal = .requestAuthority := rfl

/-- Current, agreeing, authority-bound evidence preserves the proposed decision. -/
theorem current_bound_agreement_returns_proposal
    (proposal : Decision) :
    collectiveControl true true true proposal = proposal := rfl

/-- The missing-shared-authority branch remains the existing D0 value three. -/
theorem missing_shared_authority_is_d0_three
    (proposal : Decision) :
    (collectiveControl true true false proposal).code = (3 : Fin 4) := rfl

/-- A horizontally indexed family of D3-carrying register files. -/
abbrev Mesh (ι : Type) := ι → RegisterFile

/-- Add one unit without rewriting any existing unit. -/
def extendMesh {ι : Type} (mesh : Mesh ι) (newUnit : RegisterFile) :
    Mesh (Sum ι Unit)
  | .inl i => mesh i
  | .inr _ => newUnit

/-- Horizontal extension preserves every existing unit exactly. -/
theorem horizontal_extension_preserves_existing_unit
    {ι : Type} (mesh : Mesh ι) (newUnit : RegisterFile) (i : ι) :
    extendMesh mesh newUnit (Sum.inl i) = mesh i := rfl

/-- Horizontal extension therefore preserves every existing D3 projection. -/
theorem horizontal_extension_preserves_existing_d3
    {ι : Type} (mesh : Mesh ι) (newUnit : RegisterFile) (i : ι) :
    (extendMesh mesh newUnit (Sum.inl i)).d3 = (mesh i).d3 := rfl

/-- Apply one admissible D0 decision step independently to each unit. -/
def meshStep {ι : Type} (nextDecision : ι → Decision) (mesh : Mesh ι) : Mesh ι :=
  fun i => QIKVRT.V2.D3FixedPoint.step (nextDecision i) (mesh i)

/-- Every unit retains its D3 fixed projection during a mesh step. -/
theorem mesh_step_preserves_each_d3
    {ι : Type} (nextDecision : ι → Decision) (mesh : Mesh ι) (i : ι) :
    (meshStep nextDecision mesh i).d3 = (mesh i).d3 := rfl

/-- Replicate one semantic decision across any unit index set. -/
def replicateDecisionByte {ι : Type} (decision : Decision) : ι → Byte :=
  fun _ => decisionByte decision

/-- Replication changes unit cardinality, not the four-state semantic code. -/
theorem replicated_decision_preserves_code
    {ι : Type} (decision : Decision) (i : ι) :
    (replicateDecisionByte decision i).val = decision.code.val := by
  exact decision_byte_preserves_code decision

end QIKVRT.V2.PluralScaling
