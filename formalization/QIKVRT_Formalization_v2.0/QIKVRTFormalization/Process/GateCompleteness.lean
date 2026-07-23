import QIKVRTFormalization.Process.Gates

/-!
# Exterior completeness and conditional total terminality

The assumptions that are prose-level context in the manuscript are explicit
here: exterior completeness supplies a finite BLOCK certificate for every
outside point; exhaustive classes state that the domain really is partitioned;
and PASS completeness is exactly coverage of the inside class by finite
positive certificates.
-/

namespace QIKVRT.V2

universe u

def ExteriorComplete (spec : GateSpecification α) : Prop :=
  ∀ x, spec.outside x → ∃ n, spec.blockCertificate n x

def PassComplete (spec : GateSpecification α) : Prop :=
  ∀ x, spec.inside x → ∃ n, spec.passCertificate n x

def PassCertificateUnion (spec : GateSpecification α) : α → Prop :=
  fun x => ∃ n, spec.passCertificate n x

def PassCoverageExact (spec : GateSpecification α) : Prop :=
  ∀ x, spec.inside x ↔ PassCertificateUnion spec x

def ClassesExhaustive (spec : GateSpecification α) : Prop :=
  ∀ x, spec.inside x ∨ spec.outside x

def EventuallyTerminalAt (spec : GateSpecification α) (x : α) : Prop :=
  ∃ n₀, ∀ n, n₀ ≤ n → Gate.Terminal (evaluateGate spec n x)

def TotallyEventuallyTerminal (spec : GateSpecification α) : Prop :=
  ∀ x, EventuallyTerminalAt spec x

theorem exterior_eventually_block (spec : GateSpecification α)
    (hExterior : ExteriorComplete spec) (x : α) (hOutside : spec.outside x) :
    ∃ n₀, ∀ n, n₀ ≤ n → evaluateGate spec n x = .block := by
  rcases hExterior x hOutside with ⟨n₀, hCertificate⟩
  refine ⟨n₀, ?_⟩
  intro n hn
  apply (evaluateGate_eq_block_iff spec n x).2
  exact blockCertificate_mono spec hn hCertificate

def GAT005Statement (spec : GateSpecification α)
    (_hExterior : ExteriorComplete spec) : Prop :=
  ∀ x, spec.outside x →
    ∃ n₀, ∀ n, n₀ ≤ n → evaluateGate spec n x = .block

theorem GAT005_checked (spec : GateSpecification α)
    (hExterior : ExteriorComplete spec) : GAT005Statement spec hExterior := by
  intro x hOutside
  exact exterior_eventually_block spec hExterior x hOutside

theorem certificate_implies_pass (spec : GateSpecification α)
    {n : Nat} {x : α} (hCertificate : spec.passCertificate n x) :
    evaluateGate spec n x = .pass := by
  apply (evaluateGate_eq_pass_iff spec n x).2
  refine ⟨?_, hCertificate⟩
  intro hBlock
  exact terminalCertificates_exclusive spec hCertificate hBlock

theorem terminal_inside_implies_pass (spec : GateSpecification α)
    {n : Nat} {x : α} (hInside : spec.inside x)
    (hTerminal : Gate.Terminal (evaluateGate spec n x)) :
    evaluateGate spec n x = .pass := by
  generalize hGate : evaluateGate spec n x = gate at hTerminal ⊢
  cases gate with
  | pass => rfl
  | «continue» => exact False.elim hTerminal
  | block =>
      have hOutside := spec.blockSound n x
        ((evaluateGate_eq_block_iff spec n x).1 hGate)
      exact False.elim (spec.classesDisjoint x hInside hOutside)

theorem totalTerminality_iff_passCompleteness
    (spec : GateSpecification α)
    (hExhaustive : ClassesExhaustive spec)
    (hExterior : ExteriorComplete spec) :
    TotallyEventuallyTerminal spec ↔ PassComplete spec := by
  constructor
  · intro hTotal x hInside
    rcases hTotal x with ⟨n₀, hAfter⟩
    have hPass := terminal_inside_implies_pass spec hInside (hAfter n₀ (Nat.le_refl n₀))
    exact ⟨n₀, (evaluateGate_eq_pass_iff spec n₀ x).1 hPass |>.2⟩
  · intro hPassComplete x
    cases hExhaustive x with
    | inl hInside =>
        rcases hPassComplete x hInside with ⟨n₀, hPassCertificate⟩
        have hPass : evaluateGate spec n₀ x = .pass :=
          certificate_implies_pass spec hPassCertificate
        refine ⟨n₀, ?_⟩
        intro n hn
        rw [pass_persistent spec hn hPass]
        exact Gate.pass_terminal
    | inr hOutside =>
        rcases exterior_eventually_block spec hExterior x hOutside with
          ⟨n₀, hBlockAfter⟩
        refine ⟨n₀, ?_⟩
        intro n hn
        rw [hBlockAfter n hn]
        exact Gate.block_terminal

theorem passCoverageExact_iff_passComplete (spec : GateSpecification α) :
    PassCoverageExact spec ↔ PassComplete spec := by
  constructor
  · intro hCoverage x hInside
    exact (hCoverage x).1 hInside
  · intro hComplete x
    constructor
    · exact hComplete x
    · rintro ⟨n, hCertificate⟩
      exact spec.passSound n x hCertificate

theorem eventually_pass_iff_passCertificateUnion
    (spec : GateSpecification α) (x : α) :
    (∃ n, evaluateGate spec n x = .pass) ↔ PassCertificateUnion spec x := by
  constructor
  · rintro ⟨n, hPass⟩
    exact ⟨n, ((evaluateGate_eq_pass_iff spec n x).1 hPass).2⟩
  · rintro ⟨n, hCertificate⟩
    exact ⟨n, certificate_implies_pass spec hCertificate⟩

def GAT006Statement (spec : GateSpecification α)
    (_hExhaustive : ClassesExhaustive spec)
    (_hExterior : ExteriorComplete spec) : Prop :=
  (∀ x, spec.inside x →
    ((∃ n, evaluateGate spec n x = .pass) ↔ PassCertificateUnion spec x)) ∧
  (TotallyEventuallyTerminal spec ↔ PassCoverageExact spec)

theorem GAT006_checked (spec : GateSpecification α)
    (hExhaustive : ClassesExhaustive spec)
    (hExterior : ExteriorComplete spec) :
    GAT006Statement spec hExhaustive hExterior := by
  constructor
  · intro x _hInside
    exact eventually_pass_iff_passCertificateUnion spec x
  · exact (totalTerminality_iff_passCompleteness spec hExhaustive hExterior).trans
      (passCoverageExact_iff_passComplete spec).symm

end QIKVRT.V2
