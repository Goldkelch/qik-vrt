import QIKVRTFormalization.Dimensions

/-!
# Temporal taxonomy and no-backward-channel theorem

The central distinction is formal: later evidence may change a label assigned
to an earlier record, while a deterministic forward transition leaves that
earlier record unchanged.  Operational backward signalling would require a
different model in which a later intervention changes an earlier observable.
-/

namespace QIKVRT

universe u v w

public inductive TemporalRelationKind where
  | retrodiction
  | semanticBackDetermination
  | timeReversalSymmetry
  | twoBoundaryDependence
  | onticRetrocausality
  | backwardSignalling
  | closedTimelikeCurve
deriving DecidableEq, Repr, BEq

public theorem retrodiction_ne_ontic :
    TemporalRelationKind.retrodiction ≠ TemporalRelationKind.onticRetrocausality := by
  decide

public theorem semantic_ne_ontic :
    TemporalRelationKind.semanticBackDetermination ≠
      TemporalRelationKind.onticRetrocausality := by
  decide

public theorem ontic_ne_signalling :
    TemporalRelationKind.onticRetrocausality ≠
      TemporalRelationKind.backwardSignalling := by
  decide

@[expose] public def run (step : State → Input → State) (initial : State)
    (inputs : Nat → Input) : Nat → State
  | 0 => initial
  | n + 1 => step (run step initial inputs n) (inputs n)

public theorem run_depends_only_on_input_prefix
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (n : Nat)
    (hprefix : ∀ k, k < n → u k = v k) :
    run step initial u n = run step initial v n := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simp only [run]
      rw [ih (fun k hk => hprefix k (Nat.lt_trans hk (Nat.lt_succ_self n)))]
      rw [hprefix n (Nat.lt_succ_self n)]

@[expose] public def LaterOnlyDifference (u v : Nat → Input) (cut : Nat) : Prop :=
  ∀ k, k < cut → u k = v k

public theorem noBackwardStateChannel
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (hlater : LaterOnlyDifference u v cut) :
    run step initial u cut = run step initial v cut :=
  run_depends_only_on_input_prefix step initial u v cut hlater

public structure EvidenceLabel (R : Type u) (E : Type v) (L : Type w) where
  classify : R → E → L

public theorem semanticReclassificationDoesNotOverwrite
    (scheme : EvidenceLabel Record Evidence Label)
    (record : Record) (earlier later : Evidence) :
    record = record := rfl

@[expose] public def OperationalBackwardSignal
    (earlierObservable : Intervention → Observation) : Prop :=
  ∃ a b, earlierObservable a ≠ earlierObservable b

public theorem constantEarlierObservable_noBackwardSignal
    (o : Observation) :
    ¬ OperationalBackwardSignal (fun _ : Intervention => o) := by
  rintro ⟨a, b, h⟩
  exact h rfl

public theorem reclassification_not_backward_signal
    (scheme : EvidenceLabel Record Evidence Label)
    (record : Record) :
    ¬ OperationalBackwardSignal (fun _ : Evidence => record) :=
  constantEarlierObservable_noBackwardSignal record

end QIKVRT
