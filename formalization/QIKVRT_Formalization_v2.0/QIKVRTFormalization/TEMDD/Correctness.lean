import QIKVRTFormalization.QuantumFoundations.MeasurementIndependence

/-!
# TEMDD evidence-bound completion correctness

This module formalizes the core completion rule used by QIK-VRT terminology for
Tested Event Model Driven Development (TEMDD) without adding a Mathlib
dependency.  Sets are represented extensionally as predicates `State → Prop`,
which is sufficient for the required subset and non-emptiness reasoning.

The kernel distinguishes three obligations:

1. the evidence-compatible state family is non-empty;
2. every evidence-compatible state satisfies the declared goal; and
3. the actual state is itself bound into the evidence-compatible family.

The third obligation is explicit because a consistent but incorrectly scoped
evidence family does not establish correctness of the actual state.
-/

universe u

namespace QIKVRT.TEMDD

variable {State : Type u}

/-- Predicate-set representation used by the Std-only formalization. -/
abbrev StateSet (State : Type u) := State → Prop

/-- Inclusion between predicate-sets. -/
def Subset (A B : StateSet State) : Prop :=
  ∀ s, A s → B s

/-- Non-emptiness of a predicate-set. -/
def NonemptySet (A : StateSet State) : Prop :=
  ∃ s, A s

/-- Menge zulässiger Zielzustände für Anforderung `R`. -/
def GR (isGoal : State → Prop) : StateSet State :=
  fun s => isGoal s

/-- Menge der unter Evidenz `E` noch möglichen Zustände. -/
def K (compatible : State → Prop) : StateSet State :=
  fun s => compatible s

/-- Evidenzgebundene TEMDD-Abschlussregel.

`DONE K_E GR_R` bedeutet zugleich:
* die durch Evidenz verbleibende Zustandsfamilie ist nicht leer; und
* jeder mit der Evidenz vereinbare Zustand erfüllt die Anforderung.
-/
def DONE (K_E GR_R : StateSet State) : Prop :=
  NonemptySet K_E ∧ Subset K_E GR_R

/-- Explizite Bindung des tatsächlichen Zustands an die Evidenzfamilie. -/
structure EvidenceBinding (K_E : StateSet State) (s_star : State) : Prop where
  actualCompatible : K_E s_star

/-- Satz über evidenzgebundene Abschlusskorrektheit. -/
theorem DONE_correct
    {K_E GR_R : StateSet State}
    {s_star : State}
    (h_done : DONE K_E GR_R)
    (h_bound : K_E s_star) :
    GR_R s_star := by
  exact h_done.2 s_star h_bound

/-- Dieselbe Aussage mit einer expliziten `EvidenceBinding`. -/
theorem DONE_correct_from_binding
    {K_E GR_R : StateSet State}
    {s_star : State}
    (h_done : DONE K_E GR_R)
    (binding : EvidenceBinding K_E s_star) :
    GR_R s_star := by
  exact DONE_correct h_done binding.actualCompatible

/-- `DONE` kann nicht allein wegen einer leeren Evidenzfamilie trivial gelten. -/
theorem DONE_nonempty_not_vacuous
    {K_E GR_R : StateSet State}
    (h_done : DONE K_E GR_R) :
    NonemptySet K_E :=
  h_done.1

/-- Ein erfolgreicher Abschluss schließt jeden evidenzkompatiblen Zustand aus,
der außerhalb des Zielbereichs läge. -/
theorem DONE_rejects_outside_goal
    {K_E GR_R : StateSet State}
    (h_done : DONE K_E GR_R)
    {s : State}
    (h_not_goal : ¬ GR_R s) :
    ¬ K_E s := by
  intro h_compatible
  exact h_not_goal (h_done.2 s h_compatible)

/-!
## Concrete `4 → 2 → 1` witness binding

The repository witness has two binary payload components.  Before either
record, four Boolean histories are admissible.  The first received record fixes
`newBit = true`; the second, source-older but later-received record additionally
fixes `oldBit = false`.  The theorems below bind the concrete actual state into
both successive evidence families and prove the refinement chain required by
TEMDD correctness.  Cardinality/logarithmic-information claims remain outside
this minimal Std-only kernel.
-/

structure WitnessState where
  oldBit : Bool
  newBit : Bool
  deriving DecidableEq, Repr

/-- Before either record, every two-bit state is compatible. -/
def E0 : StateSet WitnessState :=
  fun _ => True

/-- After the first (`new`) record with payload `1`. -/
def E1 : StateSet WitnessState :=
  fun s => s.newBit = true

/-- After the second (`old`) record with payload `0`. -/
def E2 : StateSet WitnessState :=
  fun s => s.newBit = true ∧ s.oldBit = false

/-- The concrete state bound by the canonical witness: `(old,new) = (0,1)`. -/
def witnessActual : WitnessState :=
  ⟨false, true⟩

/-- The actual witness state is compatible before any record. -/
theorem witnessActual_mem_E0 : E0 witnessActual := by
  trivial

/-- The actual witness state remains compatible after the first record. -/
theorem witnessActual_mem_E1 : E1 witnessActual := by
  rfl

/-- The actual witness state remains compatible after both records. -/
theorem witnessActual_mem_E2 : E2 witnessActual := by
  constructor <;> rfl

/-- The first record refines the admissible family. -/
theorem E1_subset_E0 : Subset E1 E0 := by
  intro s _
  trivial

/-- The second, retrogradely oriented record refines the admissible family again. -/
theorem E2_subset_E1 : Subset E2 E1 := by
  intro s hs
  exact hs.1

/-- Explicit actual-state/evidence binding for the fully refined witness. -/
def witnessEvidenceBinding : EvidenceBinding E2 witnessActual :=
  ⟨witnessActual_mem_E2⟩

/-- For the minimal demonstration, the declared goal is exactly the fully
refined evidence family.  Production use may choose a wider goal predicate. -/
def WitnessGoal : StateSet WitnessState := E2

/-- The fully refined witness satisfies the TEMDD completion rule. -/
theorem witness_DONE : DONE E2 WitnessGoal := by
  constructor
  · exact ⟨witnessActual, witnessActual_mem_E2⟩
  · intro s hs
    exact hs

/-- The actual witness state therefore satisfies the declared goal. -/
theorem witness_DONE_correct : WitnessGoal witnessActual := by
  exact DONE_correct_from_binding witness_DONE witnessEvidenceBinding

/-!
## QCE / superdeterminism boundary

The `4 → 2 → 1` evidence refinement does not itself establish measurement
independence.  The existing QIK-VRT quantum-foundations module requires a
`QCEFreedomCertificate` carrying that independent obligation.  Only then does
the conditional kernel theorem exclude a `SuperdeterministicCandidate` in the
repository's defined sense.
-/

open QIKVRT.V2.QuantumFoundations

/-- TEMDD reuses the existing QCE boundary without promoting the witness into a
measurement-independence certificate. -/
theorem qce_certificate_excludes_superdeterministic_candidate
    {model : TwoWingSupportModel}
    (certificate : QCEFreedomCertificate model) :
    ¬ SuperdeterministicCandidate model :=
  qceFreedomCertificate_excludes_superdeterministicCandidate certificate

end QIKVRT.TEMDD
