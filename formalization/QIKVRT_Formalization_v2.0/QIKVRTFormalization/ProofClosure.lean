import Std

/-!
# QIK-VRT Proof Closure v1

A minimal formalization of the terminal meta-condition for one exactly bound
subject. This file proves properties of the declared Boolean model only.
It does not establish the truth of external evidence.
-/

namespace QIKVRT.ProofClosure.V1

structure Snapshot where
  allRequiredProofsValid : Bool
  provenanceBound : Bool
  verifierChecked : Bool
  freshIndependentReadback : Bool
  boundariesExplicit : Bool
  noOpenObligations : Bool
  subjectUnchanged : Bool
  noPredecessorEvidenceTransfer : Bool
deriving Repr

def closed (s : Snapshot) : Bool :=
  s.allRequiredProofsValid &&
  s.provenanceBound &&
  s.verifierChecked &&
  s.freshIndependentReadback &&
  s.boundariesExplicit &&
  s.noOpenObligations &&
  s.subjectUnchanged &&
  s.noPredecessorEvidenceTransfer

def ClosureConditions (s : Snapshot) : Prop :=
  s.allRequiredProofsValid = true ∧
  s.provenanceBound = true ∧
  s.verifierChecked = true ∧
  s.freshIndependentReadback = true ∧
  s.boundariesExplicit = true ∧
  s.noOpenObligations = true ∧
  s.subjectUnchanged = true ∧
  s.noPredecessorEvidenceTransfer = true

theorem closed_eq_true_iff (s : Snapshot) :
    closed s = true ↔ ClosureConditions s := by
  simp [closed, ClosureConditions, and_assoc]

theorem open_obligation_prevents_closure (s : Snapshot)
    (h : s.noOpenObligations = false) :
    closed s = false := by
  simp [closed, h]

theorem subject_change_prevents_inherited_closure (s : Snapshot)
    (h : s.subjectUnchanged = false) :
    closed s = false := by
  simp [closed, h]

theorem predecessor_transfer_prevents_closure (s : Snapshot)
    (h : s.noPredecessorEvidenceTransfer = false) :
    closed s = false := by
  simp [closed, h]

def complete : Snapshot where
  allRequiredProofsValid := true
  provenanceBound := true
  verifierChecked := true
  freshIndependentReadback := true
  boundariesExplicit := true
  noOpenObligations := true
  subjectUnchanged := true
  noPredecessorEvidenceTransfer := true

theorem complete_is_closed : closed complete = true := by decide

end QIKVRT.ProofClosure.V1
