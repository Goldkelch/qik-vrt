import QIKVRTFormalization.Retrocausality.ForwardProcess

/-!
# Reklassifikation ohne Überschreiben (RET-011)

Reclassification is defined as a label update on an archived record.  The
record is not merely asserted equal to itself: the theorem compares the output
of the update operation with its input and connects that record to two
potentially different forward histories sharing the relevant input prefix.
-/

namespace QIKVRT.V2

universe u v w

structure ClassifiedRecord (Record : Type u) (Label : Type v) where
  record : Record
  label : Label

def EvidenceClassifier (Record : Type u) (Evidence : Type v)
    (Label : Type w) := Record → Evidence → Label

def classifyRecord (classifier : EvidenceClassifier Record Evidence Label)
    (record : Record) (evidence : Evidence) : ClassifiedRecord Record Label where
  record := record
  label := classifier record evidence

def reclassify (classifier : EvidenceClassifier Record Evidence Label)
    (archived : ClassifiedRecord Record Label) (laterEvidence : Evidence) :
    ClassifiedRecord Record Label where
  record := archived.record
  label := classifier archived.record laterEvidence

theorem reclassification_preserves_record
    (classifier : EvidenceClassifier Record Evidence Label)
    (archived : ClassifiedRecord Record Label) (laterEvidence : Evidence) :
    (reclassify classifier archived laterEvidence).record = archived.record := by
  rfl

theorem reclassification_updates_only_the_label
    (classifier : EvidenceClassifier Record Evidence Label)
    (archived : ClassifiedRecord Record Label) (laterEvidence : Evidence) :
    reclassify classifier archived laterEvidence =
      { record := archived.record,
        label := classifier archived.record laterEvidence } := by
  rfl

def RET011Statement
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (classifier : EvidenceClassifier (PrefixRecord State cut) Evidence Label)
    (earlierEvidence laterEvidence : Evidence) : Prop :=
  let earlierRecord := capturePrefix (run step initial u) cut
  let archived := classifyRecord classifier earlierRecord earlierEvidence
  let updated := reclassify classifier archived laterEvidence
  StatePrefixAgrees (run step initial u) (run step initial v) cut ∧
    updated.record = earlierRecord ∧
    (∀ k, updated.record.stateAt k =
      (capturePrefix (run step initial v) cut).stateAt k)

theorem RET011_checked
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (hPrefix : InputPrefixAgrees u v cut)
    (classifier : EvidenceClassifier (PrefixRecord State cut) Evidence Label)
    (earlierEvidence laterEvidence : Evidence) :
    RET011Statement step initial u v cut classifier earlierEvidence laterEvidence := by
  dsimp [RET011Statement]
  have hStates := forwardProcess_prefix_invariant step initial u v cut hPrefix
  refine ⟨hStates, rfl, ?_⟩
  intro k
  exact hStates k.val (Nat.le_of_lt_succ k.isLt)

end QIKVRT.V2
