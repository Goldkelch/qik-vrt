import QIKVRTFormalization.Foundation.ImageComplement
import QIKVRTFormalization.Process.GateCompleteness
import QIKVRTFormalization.Retrocausality.Reclassification
import QIKVRTFormalization.Claims.CheckedRegistry

/-!
# Batch 01A checked claim constructors

Each constructor returns an indexed `CheckedClaim`; callers receive both the
exact proposition and its kernel-checked proof, rather than an unverified
status flag.
-/

namespace QIKVRT.V2.Claims

universe u v w

def MAP003
    (f : α → β) (X A : Class α) (hAX : Class.Subset A X) :
    CheckedClaim .map003 (Class.MAP003Statement f X A hAX) :=
  ⟨Class.MAP003_checked f X A hAX⟩

def GAT004 (spec : GateSpecification α) :
    CheckedClaim .gat004 (GAT004Statement spec) :=
  ⟨GAT004_checked spec⟩

def GAT005 (spec : GateSpecification α) (hExterior : ExteriorComplete spec) :
    CheckedClaim .gat005 (GAT005Statement spec hExterior) :=
  ⟨GAT005_checked spec hExterior⟩

def GAT006 (spec : GateSpecification α)
    (hExhaustive : ClassesExhaustive spec)
    (hExterior : ExteriorComplete spec) :
    CheckedClaim .gat006 (GAT006Statement spec hExhaustive hExterior) :=
  ⟨GAT006_checked spec hExhaustive hExterior⟩

def RET011
    (step : State → Input → State) (initial : State)
    (uInputs vInputs : Nat → Input) (cut : Nat)
    (hPrefix : InputPrefixAgrees uInputs vInputs cut)
    (classifier : EvidenceClassifier (PrefixRecord State cut) Evidence Label)
    (earlierEvidence laterEvidence : Evidence) :
    CheckedClaim .ret011
      (RET011Statement step initial uInputs vInputs cut classifier
        earlierEvidence laterEvidence) :=
  ⟨RET011_checked step initial uInputs vInputs cut hPrefix classifier
    earlierEvidence laterEvidence⟩

end QIKVRT.V2.Claims

