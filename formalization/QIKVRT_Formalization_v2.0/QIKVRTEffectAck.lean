import QIKVRTEffectAck.Model
import QIKVRTEffectAck.Safety
import QIKVRTEffectAck.Mediation
import QIKVRTEffectAck.InformationBoundary
import QIKVRTEffectAck.Claims

/-!
# QIK-VRT EFFECT_ACK Draft-01 formalization

This second library target reuses the repository's locked Lean 4.19 / Std-only
runtime while keeping the IETF protocol claims separate from the 62-page
manuscript claim graph.

The checked scope is the abstract decision and authorization core of
`draft-lohmann-qikvrt-effect-ack-01`, Sections 3, 4.1, 4.2 and 14.  Wire
parsing, JCS/SHA-256 implementations, authentication, fresh-record discovery,
complete deployment mediation and physical safety remain outside the
unconditional kernel result unless represented as explicit hypotheses.
-/
