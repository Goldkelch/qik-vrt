import Std
set_option warningAsError true
namespace QIKVRT.FullDraft03

/-- A priority expression, with no dependence on another carrier. -/
def choose (valid blocked checkable integrity block isolate ready : Bool) : Nat :=
  if !valid then 5
  else if blocked then 4
  else if !checkable then 0
  else if integrity then 4
  else if block then 4
  else if isolate then 3
  else if ready then 2
  else 1

theorem choose_done_iff (v b c i k s r : Bool) :
    choose v b c i k s r = 2 ↔
    v = true ∧ b = false ∧ c = true ∧ i = false ∧
    k = false ∧ s = false ∧ r = true := by
  cases v <;> cases b <;> cases c <;> cases i <;>
    cases k <;> cases s <;> cases r <;> decide

/-- Declarative disjoint cubes corresponding to the frozen first-match contract. -/
def selectionContract (v b c i k s r : Bool) (result : Nat) : Prop :=
  (v = false ∧ result = 5) ∨
  (v = true ∧ b = true ∧ result = 4) ∨
  (v = true ∧ b = false ∧ c = false ∧ result = 0) ∨
  (v = true ∧ b = false ∧ c = true ∧ i = true ∧ result = 4) ∨
  (v = true ∧ b = false ∧ c = true ∧ i = false ∧ k = true ∧ result = 4) ∨
  (v = true ∧ b = false ∧ c = true ∧ i = false ∧ k = false ∧ s = true ∧ result = 3) ∨
  (v = true ∧ b = false ∧ c = true ∧ i = false ∧ k = false ∧ s = false ∧ r = true ∧ result = 2) ∨
  (v = true ∧ b = false ∧ c = true ∧ i = false ∧ k = false ∧ s = false ∧ r = false ∧ result = 1)

theorem choose_contract_iff (v b c i k s r : Bool) (result : Nat) :
    selectionContract v b c i k s r result ↔ result = choose v b c i k s r := by
  cases v <;> cases b <;> cases c <;> cases i <;>
    cases k <;> cases s <;> cases r <;> simp [selectionContract, choose]

def bit (m n : Nat) : Bool := m.testBit n
def valid (r d : Nat) : Bool := decide (r < 5 ∧ d < 5)
def blocked (m : Nat) : Bool := bit m 16 || bit m 12
def checkable (m : Nat) : Bool := bit m 1 && bit m 2
/-- The 17 CoreDone conjuncts; deadline is repeated intentionally. -/
def ready (m r d : Nat) : Bool :=
  bit m 0 && bit m 2 && bit m 3 && bit m 4 && bit m 5 &&
  bit m 6 && bit m 7 && (!(r == 0)) && bit m 8 && bit m 9 &&
  bit m 10 && (d == 2) && bit m 11 && !(bit m 12) &&
  bit m 13 && bit m 14 && bit m 15

def core (m r d : Nat) : Nat :=
  choose (valid r d) (blocked m) (checkable m) (bit m 17)
    (d == 4) (d == 3) (ready m r d)

/-- Total correctness for the declarative state-selection relation.
    The encoding-to-JSON-cube correspondence is also exhaustively cross-checked. -/
theorem core_correct (m r d : Nat) :
    selectionContract (valid r d) (blocked m) (checkable m) (bit m 17)
      (d == 4) (d == 3) (ready m r d) (core m r d) := by
  apply (choose_contract_iff _ _ _ _ _ _ _ _).2
  rfl

/-- Exact DONE boundary for every natural-number encoding. -/
theorem core_done_iff (m r d : Nat) :
    core m r d = 2 ↔
    valid r d = true ∧ blocked m = false ∧ checkable m = true ∧
    bit m 17 = false ∧ (d == 4) = false ∧ (d == 3) = false ∧
    ready m r d = true := by
  exact choose_done_iff _ _ _ _ _ _ _

def admit (derived declared validators : Nat) : Nat :=
  if derived = 2 ∧ declared = 2 ∧ validators = 511 then 1 else 0

theorem admission_iff (s t v : Nat) :
    admit s t v = 1 ↔ s = 2 ∧ t = 2 ∧ v = 511 := by
  simp [admit]

theorem positive_done : core 61439 1 2 = 2 := by decide
theorem positive_admission : admit (core 61439 1 2) 2 511 = 1 := by decide
theorem transport_alone_insufficient : core 1 1 2 ≠ 2 := by decide

/-- Component equality implies equality of every Cartesian composition.
    The consumer equality is required only on the six checked result classes.
    Finite component equality and the output bound are checked against the frozen neutral contract
    externally, not assumed to have been proved by this theorem. -/
def compose (f : α → Nat) (g : Nat → β → Nat) (x : α) (y : β) : Nat × Nat :=
  (f x, g (f x) y)

theorem composition_refinement
    (f fSpec : α → Nat) (g gSpec : Nat → β → Nat)
    (hf : ∀ x, f x = fSpec x)
    (hg : ∀ s y, s < 6 → g s y = gSpec s y)
    (hbound : ∀ x, f x < 6)
    (x : α) (y : β) :
    compose f g x y = compose fSpec gSpec x y := by
  unfold compose
  rw [hg (f x) y (hbound x), hf x]

#print axioms choose_contract_iff
#print axioms core_correct
#print axioms choose_done_iff
#print axioms core_done_iff
#print axioms admission_iff
#print axioms positive_done
#print axioms positive_admission
#print axioms transport_alone_insufficient
#print axioms composition_refinement
end QIKVRT.FullDraft03

open QIKVRT.FullDraft03 in
def main : IO Unit := do
  let mut output := ByteArray.empty
  for m in [0:262144] do
    for r in [0:6] do
      for d in [0:6] do
        output := output.push (UInt8.ofNat (48 + core m r d))
  for s in [0:6] do
    for t in [0:6] do
      for v in [0:512] do
        output := output.push (UInt8.ofNat (48 + admit s t v))
  IO.FS.writeBinFile "full-lean.out" output
