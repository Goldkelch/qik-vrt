namespace QIKVRT.CoreInvariant
inductive EffectState where | nack | continue | done | isolate | block deriving DecidableEq, Repr
def decide (t b i r : Bool) : EffectState :=
  if t = false then .nack else if b then .block else if i then .isolate else if r then .done else .continue
def ordinaryRelease (s : EffectState) : Bool := s == .done
theorem ordinary_release_iff_done (s : EffectState) : ordinaryRelease s = true ↔ s = .done := by
  cases s <;> simp [ordinaryRelease]
theorem transport_ack_not_sufficient : decide true false false false ≠ .done := by decide
theorem release_requires_transport (t b i r : Bool)
    (h : ordinaryRelease (decide t b i r) = true) : t = true := by
  cases t <;> simp [decide, ordinaryRelease] at h ⊢
theorem block_dominates (i r : Bool) : decide true true i r = .block := by simp [decide]
theorem isolate_precedes_release (r : Bool) : decide true false true r = .isolate := by simp [decide]
theorem done_exactly_ready_unblocked_unisolated : decide true false false true = .done := by rfl
end QIKVRT.CoreInvariant
