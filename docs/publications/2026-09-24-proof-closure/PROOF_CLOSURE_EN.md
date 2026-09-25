<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# The Final Proof Is the Proof That No Proof Obligation Remains

**Ingolf Lohmann · 24 September 2026**

A system can keep confirming itself indefinitely and become increasingly persuasive without producing any new knowledge. Therefore the terminal step of a proof chain must not be yet another proof of the same proposition.

The terminal step concerns a different object:

> **The final proof is not another proof of the same truth. The final proof is evidence that, for the same exactly bound subject, no further proof obligation remains open.**

This is not circularity. It is a rule that terminates circularity.

## Closure condition

For an unchanged subject s, PROOF_CLOSURE is reached only when every required proof is valid, provenance and exact-subject binding are established, the verifiers are checked, a fresh independent readback is accepted, the boundaries are explicit, no proof obligation remains open, the subject is unchanged, and predecessor evidence has not been transferred to a mutated successor.

    PROOF_CLOSURE(s)
    =
    ALL_REQUIRED_PROOFS_VALID(s)
    ∧ PROVENANCE_BOUND(s)
    ∧ VERIFIER_CHECKED(s)
    ∧ FRESH_INDEPENDENT_READBACK(s)
    ∧ BOUNDARIES_EXPLICIT(s)
    ∧ NO_OPEN_OBLIGATIONS(s)
    ∧ SUBJECT_UNCHANGED(s)
    ∧ NO_PREDECESSOR_EVIDENCE_TRANSFER(s)

For exactly that subject:

    PROOF_CLOSURE(s) = TRUE
    → HALT

A changed subject s' starts a new closure question. Closure of s remains historical evidence but is not inherited by s'.

This turns repeated self-confirmation into an epistemic spiral: locally closed transitions can become the evidence base for a new subject without pretending that the new subject was already proved.

The rule complements the QIK-VRT runtime chain:

    COMPILE → BIND → RESOLVE → EXECUTE → TEST
    → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE

EFFECT_ACK_DONE terminates one bound effect transition. PROOF_CLOSURE answers the additional meta-question whether any proof obligation for that exact subject remains open.

It is not universal truth, and it is not a proof of arbitrary premises. It is a bounded halt condition over an explicit subject, obligation set, evidence set, verifier set and time.

**q.e.d.**

**Ingolf Lohmann**
