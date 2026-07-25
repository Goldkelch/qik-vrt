/-
SPDX-License-Identifier: Apache-2.0
Copyright 2026 Ingolf Lohmann.
-/
import Mathlib

/-!
# The action square of the Planck scale

This file proves the algebraic core of the publication
`Das Wirkungsquadrat der Planck-Skala` from explicit positive real-valued
definitions.  It does not assert empirical spacetime discreteness, a specific
dynamics of quantum gravity, or a cosmological origin claim.
-/

noncomputable section

open Real

namespace QIKVRT.Wirkungsquadrat

/-- Positive Planck length in the reduced-phase convention. -/
def ellP (c hbar G : ℝ) : ℝ :=
  Real.sqrt (hbar * G / c ^ 3)

/-- Planck time derived from the light-cone ratio. -/
def tP (c hbar G : ℝ) : ℝ :=
  ellP c hbar G / c

/-- Planck mass derived from the gravitational length convention `G m / c²`. -/
def mP (c hbar G : ℝ) : ℝ :=
  ellP c hbar G * c ^ 2 / G

/-- Planck momentum. -/
def pP (c hbar G : ℝ) : ℝ :=
  mP c hbar G * c

/-- Planck energy. -/
def EP (c hbar G : ℝ) : ℝ :=
  pP c hbar G * c

/-- Reduced temporal scale of a massless mode. -/
def modeTau (lam c : ℝ) : ℝ := lam / c

/-- Momentum of a reduced-wavelength mode. -/
def modeP (lam hbar : ℝ) : ℝ := hbar / lam

/-- Energy of a massless reduced-wavelength mode. -/
def modeE (lam c hbar : ℝ) : ℝ := c * modeP lam hbar

/-- The universal action square for any positive reduced wavelength. -/
theorem universal_action_square
    {lam c hbar : ℝ}
    (hlam : 0 < lam) (hc : 0 < c) :
    lam / modeTau lam c = c ∧
    modeE lam c hbar / modeP lam hbar = c ∧
    lam * modeP lam hbar = hbar ∧
    modeTau lam c * modeE lam c hbar = hbar := by
  have hlam0 : lam ≠ 0 := ne_of_gt hlam
  have hc0 : c ≠ 0 := ne_of_gt hc
  have hp0 : modeP lam hbar = 0 ↔ hbar = 0 := by
    simp [modeP, hlam0]
  constructor
  · unfold modeTau
    field_simp
  constructor
  · by_cases hh : hbar = 0
    · simp [modeE, modeP, hh]
    · have hmp : modeP lam hbar ≠ 0 := by
        simpa [hp0] using hh
      unfold modeE
      field_simp
  constructor
  · unfold modeP
    field_simp
  · unfold modeTau modeE modeP
    field_simp

/-- Positivity of the Planck length. -/
theorem ellP_pos
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    0 < ellP c hbar G := by
  unfold ellP
  apply Real.sqrt_pos.2
  positivity

/-- The defining square equation of the Planck length. -/
theorem ellP_sq
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    (ellP c hbar G) ^ 2 = hbar * G / c ^ 3 := by
  unfold ellP
  rw [Real.sq_sqrt]
  positivity

/-- Positivity of Planck time. -/
theorem tP_pos
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    0 < tP c hbar G := by
  unfold tP
  positivity [ellP_pos hc hh hG]

/-- Positivity of Planck mass. -/
theorem mP_pos
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    0 < mP c hbar G := by
  unfold mP
  positivity [ellP_pos hc hh hG]

/-- Positivity of Planck momentum. -/
theorem pP_pos
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    0 < pP c hbar G := by
  unfold pP
  positivity [mP_pos hc hh hG]

/-- Positivity of Planck energy. -/
theorem EP_pos
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    0 < EP c hbar G := by
  unfold EP
  positivity [pP_pos hc hh hG]

/-- `ℓP / tP = c`. -/
theorem ellP_div_tP
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    ellP c hbar G / tP c hbar G = c := by
  have he0 : ellP c hbar G ≠ 0 := ne_of_gt (ellP_pos hc hh hG)
  have hc0 : c ≠ 0 := ne_of_gt hc
  unfold tP
  field_simp

/-- `EP / pP = c`. -/
theorem EP_div_pP
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    EP c hbar G / pP c hbar G = c := by
  have hp0 : pP c hbar G ≠ 0 := ne_of_gt (pP_pos hc hh hG)
  unfold EP
  field_simp

/-- `ℓP · pP = ℏ`. -/
theorem ellP_mul_pP
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    ellP c hbar G * pP c hbar G = hbar := by
  have hc0 : c ≠ 0 := ne_of_gt hc
  have hG0 : G ≠ 0 := ne_of_gt hG
  have hsq := ellP_sq hc hh hG
  field_simp [hc0] at hsq
  unfold pP mP
  field_simp [hG0]
  nlinarith

/-- `tP · EP = ℏ`. -/
theorem tP_mul_EP
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    tP c hbar G * EP c hbar G = hbar := by
  have hc0 : c ≠ 0 := ne_of_gt hc
  calc
    tP c hbar G * EP c hbar G
        = ellP c hbar G * pP c hbar G := by
            unfold tP EP
            field_simp
    _ = hbar := ellP_mul_pP hc hh hG

/-- `G mP / c² = ℓP` under the declared gravitational-radius convention. -/
theorem ellP_gravitational_anchor
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    G * mP c hbar G / c ^ 2 = ellP c hbar G := by
  have hc0 : c ≠ 0 := ne_of_gt hc
  have hG0 : G ≠ 0 := ne_of_gt hG
  unfold mP
  field_simp

/-- `ℏ / (mP c) = ℓP`. -/
theorem ellP_quantum_anchor
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    hbar / (mP c hbar G * c) = ellP c hbar G := by
  have hp0 : pP c hbar G ≠ 0 := ne_of_gt (pP_pos hc hh hG)
  change hbar / pP c hbar G = ellP c hbar G
  apply (div_eq_iff hp0).2
  simpa using (ellP_mul_pP hc hh hG).symm

/-- A positive length is gravitationally selected when it has the Planck square. -/
def GravitationallySelected (ell c hbar G : ℝ) : Prop :=
  0 < ell ∧ ell ^ 2 = hbar * G / c ^ 3

/-- The Planck length is gravitationally selected. -/
theorem ellP_selected
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    GravitationallySelected (ellP c hbar G) c hbar G := by
  exact ⟨ellP_pos hc hh hG, ellP_sq hc hh hG⟩

/-- Uniqueness of the positive gravitationally selected point. -/
theorem gravitational_anchor_unique
    {ell c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G)
    (hsel : GravitationallySelected ell c hbar G) :
    ell = ellP c hbar G := by
  rcases hsel with ⟨hell, hellsq⟩
  have hep := ellP_pos hc hh hG
  have hepsq := ellP_sq hc hh hG
  nlinarith

/-- The complete three-line core of the Planck action square. -/
theorem three_line_core
    {c hbar G : ℝ}
    (hc : 0 < c) (hh : 0 < hbar) (hG : 0 < G) :
    ellP c hbar G / tP c hbar G = c ∧
    EP c hbar G / pP c hbar G = c ∧
    ellP c hbar G * pP c hbar G = hbar ∧
    tP c hbar G * EP c hbar G = hbar ∧
    ellP c hbar G = hbar / (mP c hbar G * c) ∧
    ellP c hbar G = G * mP c hbar G / c ^ 2 := by
  exact ⟨
    ellP_div_tP hc hh hG,
    EP_div_pP hc hh hG,
    ellP_mul_pP hc hh hG,
    tP_mul_EP hc hh hG,
    (ellP_quantum_anchor hc hh hG).symm,
    (ellP_gravitational_anchor hc hh hG).symm
  ⟩

#print axioms universal_action_square
#print axioms ellP_sq
#print axioms ellP_mul_pP
#print axioms tP_mul_EP
#print axioms ellP_gravitational_anchor
#print axioms ellP_quantum_anchor
#print axioms gravitational_anchor_unique
#print axioms three_line_core

end QIKVRT.Wirkungsquadrat
