import Mathlib.Data.Set.Basic
import QIKVRTFormalization.QuantumFoundations.MeasurementIndependence

universe u

namespace QIKVRT.TEMDD

variable {State : Type u}

/-- Menge zulässiger Zielzustände für Anforderung `R`. -/
def GR (isGoal : State → Prop) : Set State :=
  {s | isGoal s}

/-- Menge der unter Evidenz `E` noch möglichen Zustände. -/
def K (compatible : State → Prop) : Set State :=
  {s | compatible s}

/-- Evidenzgebundene TEMDD-Abschlussregel.

`DONE K_E GR_R` bedeutet zugleich:
* die durch Evidenz verbleibende Zustandsmenge ist nicht leer; und
* jeder mit der Evidenz vereinbare Zustand erfüllt die Anforderung.
-/
def DONE (K_E GR_R : Set State) : Prop :=
  K_E.Nonempty ∧ K_E ⊆ GR_R

/-- Satz über evidenzgebundene Abschlusskorrektheit. -/
theorem DONE_correct
    {K_E GR_R : Set State}
    {s_star : State}
    (h_done : DONE K_E GR_R)
    (h_bound : s_star ∈ K_E) :
    s_star ∈ GR_R := by
  exact h_done.2 h_bound

/-- `DONE` kann nicht allein wegen einer leeren Evidenzmenge trivial gelten. -/
theorem DONE_nonempty_not_vacuous
    {K_E GR_R : Set State}
    (h_done : DONE K_E GR_R) :
    K_E.Nonempty :=
  h_done.1

/-- Zweibit-Zustand des endlichen `4 → 2 → 1`-Witness. -/
structure WitnessState where
  oldBit : Bool
  newBit : Bool
  deriving DecidableEq, Repr

/-- Vor irgendeinem Record sind alle vier Zweibit-Zustände evidenzkompatibel. -/
def E0 : Set WitnessState := Set.univ

/-- Nach dem zuerst empfangenen `new`-Record mit Payload `1` bleibt `newBit = true`. -/
def E1 : Set WitnessState :=
  {s | s.newBit = true}

/-- Nach dem später empfangenen, quellenzeitlich älteren `old`-Record mit Payload `0`
bleibt zusätzlich `oldBit = false`. -/
def E2 : Set WitnessState :=
  {s | s.newBit = true ∧ s.oldBit = false}

/-- Der im kanonischen Witness gebundene Zustand `(old,new) = (0,1)`. -/
def witnessActual : WitnessState :=
  ⟨false, true⟩

/-- Der konkrete Zustand ist nach dem ersten Record noch mit der Evidenz vereinbar. -/
theorem witnessActual_mem_E1 : witnessActual ∈ E1 := by
  rfl

/-- Der konkrete Zustand ist nach beiden Records mit der verfeinerten Evidenz vereinbar. -/
theorem witnessActual_mem_E2 : witnessActual ∈ E2 := by
  constructor <;> rfl

/-- Der erste Record verfeinert die Evidenzmenge. -/
theorem E1_subset_E0 : E1 ⊆ E0 := by
  intro s _
  trivial

/-- Der zweite, retrograd orientierte Record verfeinert die Evidenzmenge erneut. -/
theorem E2_subset_E1 : E2 ⊆ E1 := by
  intro s hs
  exact hs.1

/-- Konkreter TEMDD-Abschluss für den vollständig gebundenen Zweibit-Witness:
Wenn der Zielbereich genau den durch beide Records verbleibenden Zustand zulässt,
ist `DONE` erfüllt und der gebundene tatsächliche Zustand liegt im Zielbereich. -/
def WitnessGoal : Set WitnessState := E2

theorem witness_DONE : DONE E2 WitnessGoal := by
  constructor
  · exact ⟨witnessActual, witnessActual_mem_E2⟩
  · intro s hs
    exact hs

theorem witness_DONE_correct : witnessActual ∈ WitnessGoal := by
  exact DONE_correct witness_DONE witnessActual_mem_E2

/-!
## QCE / Superdeterminismus-Grenze

Der endliche `4 → 2 → 1`-Witness liefert keine Messunabhängigkeit.
Die bestehende QIK-VRT-Formalisation verlangt dafür ausdrücklich ein
`QCEFreedomCertificate`.  Erst dieses Zertifikat erlaubt den konditionalen
Ausschluss eines `SuperdeterministicCandidate` im dort definierten Sinn.
-/

open QIKVRT.V2.QuantumFoundations

/-- TEMDD übernimmt die bestehende QCE-Grenze unverändert:
Ein explizites Freedom Certificate trägt die Messunabhängigkeit, nicht die
retrograde Empfangsordnung des Witness. -/
theorem qce_certificate_excludes_superdeterministic_candidate
    {model : TwoWingSupportModel}
    (certificate : QCEFreedomCertificate model) :
    ¬ SuperdeterministicCandidate model :=
  qceFreedomCertificate_excludes_superdeterministicCandidate certificate

end QIKVRT.TEMDD
