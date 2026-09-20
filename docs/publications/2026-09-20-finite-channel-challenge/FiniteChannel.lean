/-
Copyright 2026 Ingolf Lohmann.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

Conditional finite-channel mathematics. No spacetime channel is assumed to
exist. This model is not a refinement proof of the Python/C implementations.
-/
import Std

namespace QIKVRTChallenge

def segment {α : Type} (width : Nat) (xs : List α) : List (List α) :=
  if width = 0 then [xs]
  else if xs.length = 0 then []
  else xs.take width :: segment width (xs.drop width)
termination_by xs.length
decreasing_by
  simp_all only [List.length_drop]
  omega

theorem segment_roundtrip {α : Type} (width : Nat) (xs : List α) :
    (segment width xs).flatten = xs := by
  rw [segment]
  split
  · simp
  · split
    · simp_all
    · simp only [List.flatten_cons]
      rw [segment_roundtrip width (xs.drop width), List.take_append_drop]
termination_by xs.length
decreasing_by
  simp only [List.length_drop]
  omega

theorem segment_bounded {α : Type} (width : Nat) (positive : 0 < width)
    (xs : List α) : ∀ chunk ∈ segment width xs, chunk.length ≤ width := by
  rw [segment]
  split
  · omega
  · split
    · simp
    · intro chunk member
      rcases List.mem_cons.mp member with same | rest
      · subst chunk
        exact List.length_take_le _ _
      · exact segment_bounded width positive (xs.drop width) chunk rest
termination_by xs.length
decreasing_by
  simp only [List.length_drop]
  omega

theorem lossless_delivery {α : Type} (width : Nat) (xs : List α)
    (deliver : List α → List α) (lossless : ∀ chunk, deliver chunk = chunk) :
    ((segment width xs).map deliver).flatten = xs := by
  have unchanged : deliver = id := funext lossless
  simp [unchanged, segment_roundtrip]

theorem no_fixed_message_length_bound (limit : Nat) :
    ∃ xs : List Bool, limit < xs.length := by
  exact ⟨List.replicate (limit + 1) false, by simp⟩

theorem bidirectional_roundtrip {α : Type} (width : Nat)
    (request : List α) (respond : List α → List α) :
    (segment width (respond (segment width request).flatten)).flatten =
      respond request := by
  simp only [segment_roundtrip]

structure Haltpoint where
  recursionRecognized : Bool
  effectChecked : Bool
  connectionApproved : Bool

def release (h : Haltpoint) : Bool :=
  h.recursionRecognized && h.effectChecked && h.connectionApproved

theorem release_requires_complete_haltpoint (h : Haltpoint) :
    release h = true ↔ h.recursionRecognized = true ∧
      h.effectChecked = true ∧ h.connectionApproved = true := by
  simp [release, and_assoc]

theorem transport_alone_does_not_release (r c : Bool) :
    release ⟨r, false, c⟩ = false := by
  simp [release]

theorem append_preserves_sealed_prefix {α : Type} (early later : List α) :
    (early ++ later).take early.length = early := by
  simp

theorem virtual_address_does_not_reverse_host_order
    (sendHost receiveHost virtualSend virtualReceive : Nat)
    (hostOrder : sendHost < receiveHost)
    (_virtualReverse : virtualReceive < virtualSend) :
    ¬ receiveHost ≤ sendHost := by
  omega

theorem identical_early_state_cannot_decode_both_choices {S : Type}
    (early : S) (decode : S → Bool) :
    ¬ (decode early = false ∧ decode early = true) := by
  intro ⟨zero, one⟩
  rw [zero] at one
  contradiction

end QIKVRTChallenge

#print axioms QIKVRTChallenge.segment_roundtrip
#print axioms QIKVRTChallenge.segment_bounded
#print axioms QIKVRTChallenge.lossless_delivery
#print axioms QIKVRTChallenge.no_fixed_message_length_bound
#print axioms QIKVRTChallenge.bidirectional_roundtrip
#print axioms QIKVRTChallenge.release_requires_complete_haltpoint
#print axioms QIKVRTChallenge.transport_alone_does_not_release
#print axioms QIKVRTChallenge.append_preserves_sealed_prefix
#print axioms QIKVRTChallenge.virtual_address_does_not_reverse_host_order
#print axioms QIKVRTChallenge.identical_early_state_cannot_decode_both_choices
