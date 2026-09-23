# IETF-facing note: Information Carrier and EFFECT_ACK

Status: `REPOSITORY_CANDIDATE_NOT_SUBMITTED`

This note separates transport completion from effect completion.

`TRANSPORT_ACK != EFFECT_ACK != EFFECT_ACK_DONE`

A transport acknowledgement proves arrival at a communication boundary. It does not prove that the intended downstream state or physical effect occurred.

Carrier path:

`state -> encode/serialize -> constrained carrier -> decode/deserialize -> successor state`

The round-trip equivalence relation must be explicit. Byte identity, semantic equivalence, functional equivalence and bounded measurement equivalence are different contracts.

If the application requires effect verification, the transport result is followed by:

`successor -> test -> observe -> fresh readback -> accept -> EFFECT_ACK_DONE`

`EFFECT_ACK_DONE` is terminal only for the exact bound subject and acceptance scope. A mutation creates a successor and does not inherit predecessor acceptance.

The terms neutron-star, bidirectional singularity and Planck boundary are explanatory architecture metaphors only. They are not claims about spacetime singularities, black-hole information dynamics or Planck-scale physics.

Canonical synthesis:
`docs/research/2026-09-24-information-singularity-effect-verification.md`

Author: Ingolf Lohmann
