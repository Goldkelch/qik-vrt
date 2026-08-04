/-
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.

Source-only formalization candidate. Kernel verification remains a repository CI gate.
-/

namespace QIKVRT.AphorismCorpus

structure TimedNode where
  time : Nat

/-- A declared forward edge never points from a later node to a strictly earlier node. -/
def ForwardEdge (source target : TimedNode) : Prop := source.time ≤ target.time

theorem present_not_forward_ancestor_of_past
    (past present : TimedNode)
    (h : past.time < present.time) :
    ¬ ForwardEdge present past := by
  intro hle
  exact Nat.not_le_of_lt h hle

/-- Two descriptive propositions do not, without a bridge premise, entail an
arbitrary normative proposition. -/
theorem descriptive_premises_do_not_entail_arbitrary_norm
    (D G T : Prop)
    (hD : D)
    (hG : G) :
    ¬ ((D ∧ G) → T) ↔ ¬ T := by
  constructor
  · intro hnot hT
    exact hnot (fun _ => hT)
  · intro hnotT himp
    exact hnotT (himp ⟨hD, hG⟩)

end QIKVRT.AphorismCorpus
