import QIKVRTEffectAck.Model
import QIKVRTEffectAck.Safety
import QIKVRTEffectAck.Mediation
import QIKVRTEffectAck.InformationBoundary
import QIKVRTEffectAck.Claims
import QIKVRTEffectAck.QuantumClassicalRuntime

/-!
# QIK-VRT EFFECT_ACK Draft-01 and quantum-classical runtime formalization

This second library target reuses the repository's locked Lean 4.19 / Std-only
runtime while keeping the IETF protocol claims and the bounded
quantum-classical runtime assurance model separate from the 62-page manuscript
claim graph.

The EFFECT_ACK checked scope is the abstract decision and authorization core of
`draft-lohmann-qikvrt-effect-ack-01`, Sections 3, 4.1, 4.2 and 14. The
quantum-classical article scope proves only properties of its abstract runtime,
evidence, uncertainty, gate, backend-envelope and effect-acknowledgement model.
Wire parsing, JCS/SHA-256 implementations, authentication, concrete QPU
adapters, quantum mechanics, hardware noise, calibration, error correction,
fresh-record discovery, complete deployment mediation and physical safety
remain outside unconditional kernel results unless represented as explicit
hypotheses.
-/
