import Std

/-!
# QIK-VRT Monotone Evidence Sphere V1

Originator of the "monotonically growing evidence sphere" concept: Ingolf
Lohmann.

This deliberately narrow Lean model formalizes the state transition

`Eₖ = (Cₖ, μₖ, Lₖ)`

for an accepted core `C`, a natural-valued membership degree `μ`, and a sealed
append-only history `L`. A new relation is added by core union-as-membership,
pointwise `max` for membership, and history append. The theorems below are
about this finite data structure and its declared transition relation only.

They do not establish a physical sphere, a quantum field, human agency, a
hardware implementation, or an empirical performance result.
-/

namespace QIKVRT
namespace MonotoneEvidenceSphere

abbrev RelationId := Nat
abbrev Degree := Nat

/-- A finite, machine-level abstraction of an evidence sphere. -/
structure EvidenceSphere where
  core : List RelationId
  membership : RelationId → Degree
  sealedHistory : List RelationId
  mass : Degree
  radius : Nat

/-- Every relation accepted in the left state is accepted in the right state. -/
def CoreMonotone (left right : EvidenceSphere) : Prop :=
  ∀ relation, relation ∈ left.core → relation ∈ right.core

/-- The right history is the left history with a suffix, never a rewrite. -/
def HistoryMonotone (left right : EvidenceSphere) : Prop :=
  ∃ suffix, right.sealedHistory = left.sealedHistory ++ suffix

/-- Every sealed historical relation remains a member of the accepted core. -/
def SealedHistoryIntact (sphere : EvidenceSphere) : Prop :=
  ∀ relation, relation ∈ sphere.sealedHistory → relation ∈ sphere.core

/-- A relation lies in an alpha-cut if its model membership reaches the threshold. -/
def AlphaCut (sphere : EvidenceSphere) (threshold : Degree)
    (relation : RelationId) : Prop :=
  threshold ≤ sphere.membership relation

/--
Append one relation. The core and sealed history receive the new relation,
while membership is updated by pointwise maximum rather than replacing a prior
degree. `mass` and `radius` are explicit natural-valued model coordinates.
-/
def append (sphere : EvidenceSphere) (relation : RelationId)
    (degree : Degree) : EvidenceSphere where
  core := sphere.core ++ [relation]
  membership := fun candidate =>
    max (sphere.membership candidate)
      (if candidate = relation then degree else 0)
  sealedHistory := sphere.sealedHistory ++ [relation]
  mass := sphere.mass + degree
  radius := sphere.radius + 1

/-- [MES-T01] Appending never removes an accepted relation. -/
theorem MES_T01_append_core_monotone (sphere : EvidenceSphere)
    (relation : RelationId) (degree : Degree) :
    CoreMonotone sphere (append sphere relation degree) := by
  intro candidate accepted
  simp [append, accepted]

/-- [MES-T02] Appending extends sealed history by one suffix element. -/
theorem MES_T02_append_history_monotone (sphere : EvidenceSphere)
    (relation : RelationId) (degree : Degree) :
    HistoryMonotone sphere (append sphere relation degree) := by
  exact ⟨[relation], rfl⟩

/-- [MES-T03] Appending preserves the sealed-history-in-core invariant. -/
theorem MES_T03_append_preserves_sealed_history (sphere : EvidenceSphere)
    (relation : RelationId) (degree : Degree)
    (intact : SealedHistoryIntact sphere) :
    SealedHistoryIntact (append sphere relation degree) := by
  intro candidate sealed
  have oldOrNew : candidate ∈ sphere.sealedHistory ∨ candidate = relation := by
    simpa [append] using sealed
  cases oldOrNew with
  | inl oldSealed =>
      simpa [append] using
        (show candidate ∈ sphere.core ∨ candidate = relation from
          Or.inl (intact candidate oldSealed))
  | inr isNew =>
      simpa [append] using
        (show candidate ∈ sphere.core ∨ candidate = relation from Or.inr isNew)

/-- [MES-T04] Appending cannot reduce a membership degree. -/
theorem MES_T04_append_membership_monotone (sphere : EvidenceSphere)
    (relation candidate : RelationId) (degree : Degree) :
    sphere.membership candidate ≤
      (append sphere relation degree).membership candidate := by
  change sphere.membership candidate ≤
    max (sphere.membership candidate)
      (if candidate = relation then degree else 0)
  exact Nat.le_max_left _ _

/-- [MES-T05] Each alpha-cut is monotone under append. -/
theorem MES_T05_append_alpha_cut_monotone (sphere : EvidenceSphere)
    (relation candidate : RelationId) (degree threshold : Degree)
    (inCut : AlphaCut sphere threshold candidate) :
    AlphaCut (append sphere relation degree) threshold candidate := by
  exact Nat.le_trans inCut
    (MES_T04_append_membership_monotone sphere relation candidate degree)

/-- [MES-T06] Model mass cannot decrease under append. -/
theorem MES_T06_append_mass_monotone (sphere : EvidenceSphere)
    (relation : RelationId) (degree : Degree) :
    sphere.mass ≤ (append sphere relation degree).mass := by
  change sphere.mass ≤ sphere.mass + degree
  exact Nat.le_add_right _ _

/-- [MES-T07] The model radius grows by one under append. -/
theorem MES_T07_append_radius_strict_growth (sphere : EvidenceSphere)
    (relation : RelationId) (degree : Degree) :
    sphere.radius < (append sphere relation degree).radius := by
  change sphere.radius < sphere.radius + 1
  exact Nat.lt_succ_self _

/-- The only declared state transitions of this compact model. -/
inductive EvidenceTransition where
  | appendRelation (relation : RelationId) (degree : Degree)
  | hold
  | reobserve
  | requestAuthority
  deriving DecidableEq, Repr

/-- Interpret a declared transition. Non-append controls preserve the state. -/
def step (sphere : EvidenceSphere) : EvidenceTransition → EvidenceSphere
  | .appendRelation relation degree => append sphere relation degree
  | .hold => sphere
  | .reobserve => sphere
  | .requestAuthority => sphere

/-- [MES-T08] Every declared transition preserves accepted-core monotonicity. -/
theorem MES_T08_step_core_monotone (sphere : EvidenceSphere)
    (transition : EvidenceTransition) :
    CoreMonotone sphere (step sphere transition) := by
  cases transition with
  | appendRelation relation degree =>
      exact MES_T01_append_core_monotone sphere relation degree
  | hold =>
      intro candidate accepted
      exact accepted
  | reobserve =>
      intro candidate accepted
      exact accepted
  | requestAuthority =>
      intro candidate accepted
      exact accepted

/-- [MES-T09] Every declared transition preserves append-only sealed history. -/
theorem MES_T09_step_history_monotone (sphere : EvidenceSphere)
    (transition : EvidenceTransition) :
    HistoryMonotone sphere (step sphere transition) := by
  cases transition with
  | appendRelation relation degree =>
      exact MES_T02_append_history_monotone sphere relation degree
  | hold =>
      exact ⟨[], by simp [step]⟩
  | reobserve =>
      exact ⟨[], by simp [step]⟩
  | requestAuthority =>
      exact ⟨[], by simp [step]⟩

/-- [MES-T10] Every declared transition preserves intact sealed history. -/
theorem MES_T10_step_preserves_sealed_history (sphere : EvidenceSphere)
    (transition : EvidenceTransition) (intact : SealedHistoryIntact sphere) :
    SealedHistoryIntact (step sphere transition) := by
  cases transition with
  | appendRelation relation degree =>
      exact MES_T03_append_preserves_sealed_history sphere relation degree intact
  | hold => exact intact
  | reobserve => exact intact
  | requestAuthority => exact intact

/-- Four control outcomes fit into, but do not exhaust, a four-bit field. -/
inductive ControlNibble where
  | continue
  | hold
  | reobserve
  | requestAuthority
  deriving DecidableEq, Repr

/-- A model-level four-bit encoding for the control plane. -/
def ControlNibble.code : ControlNibble → Fin 16
  | .continue => 0
  | .hold => 1
  | .reobserve => 2
  | .requestAuthority => 3

/-- [MES-T11] Each declared control code is representable in four bits. -/
theorem MES_T11_control_code_fits_nibble (control : ControlNibble) :
    control.code.val < 16 := control.code.isLt

/-- [MES-T12] The four declared controls retain distinct code identities. -/
theorem MES_T12_control_code_injective (left right : ControlNibble)
    (sameCode : left.code = right.code) : left = right := by
  cases left <;> cases right <;> simp [ControlNibble.code] at sameCode ⊢

end MonotoneEvidenceSphere
end QIKVRT
