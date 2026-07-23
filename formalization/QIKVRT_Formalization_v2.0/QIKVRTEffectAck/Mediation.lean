import QIKVRTEffectAck.Safety

/-!
# Complete mediation and the conditional cyberphysical bridge

The software theorem is unconditional once `CompletelyMediated` is supplied:
every ordinary executor invocation has passed the exact consumer authorization
predicate.  The physical theorem additionally assumes a faithful causal bridge
from each scoped physical occurrence to such an invocation.  The assumptions
are arguments, not hidden conclusions.
-/

namespace QIKVRT.EffectAck.V1

universe u v

def CompletelyMediated
    {Effect : Type u}
    (executes : Effect → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool) : Prop :=
  ∀ effect, executes effect →
    authorizeOrdinaryRelease (checks effect) (snapshot effect)
      (recordState effect) (ordinaryReleaseClaim effect) = true

theorem completelyMediated_execution_implies_done
    {Effect : Type u}
    (executes : Effect → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool)
    (hMediated :
      CompletelyMediated executes checks snapshot recordState
        ordinaryReleaseClaim)
    {effect : Effect}
    (hExecutes : executes effect) :
    recordState effect = .done ∧ selectState (snapshot effect) = .done := by
  exact authorized_implies_recorded_and_recomputed_done
    (checks effect) (snapshot effect) (recordState effect)
    (ordinaryReleaseClaim effect) (hMediated effect hExecutes)

def FaithfulPhysicalBridge
    {Effect : Type u} {PhysicalOccurrence : Type v}
    (executes : Effect → Prop)
    (occurs : PhysicalOccurrence → Prop)
    (causedBy : Effect → PhysicalOccurrence → Prop) : Prop :=
  ∀ occurrence, occurs occurrence →
    ∃ effect, executes effect ∧ causedBy effect occurrence

theorem physicalOccurrence_implies_authorized_done_conditionally
    {Effect : Type u} {PhysicalOccurrence : Type v}
    (executes : Effect → Prop)
    (occurs : PhysicalOccurrence → Prop)
    (causedBy : Effect → PhysicalOccurrence → Prop)
    (checks : Effect → ConsumerChecks)
    (snapshot : Effect → Snapshot)
    (recordState : Effect → State)
    (ordinaryReleaseClaim : Effect → Bool)
    (hMediated :
      CompletelyMediated executes checks snapshot recordState
        ordinaryReleaseClaim)
    (hBridge : FaithfulPhysicalBridge executes occurs causedBy)
    {occurrence : PhysicalOccurrence}
    (hOccurs : occurs occurrence) :
    ∃ effect,
      causedBy effect occurrence ∧
      recordState effect = .done ∧
      selectState (snapshot effect) = .done := by
  rcases hBridge occurrence hOccurs with ⟨effect, hExecutes, hCausedBy⟩
  rcases completelyMediated_execution_implies_done
      executes checks snapshot recordState ordinaryReleaseClaim
      hMediated hExecutes with
    ⟨hRecordedDone, hRederivedDone⟩
  exact ⟨effect, hCausedBy, hRecordedDone, hRederivedDone⟩

end QIKVRT.EffectAck.V1
