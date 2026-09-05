# QIK-VRT Information -> Evidence -> Effect Axis v1

Status: `PROPOSED_REVIEW_CARRIER`

This research object makes one existing QIK-VRT invariant explicit for downstream Mesh systems:

`distinction -> information -> evidence binding -> causality assessment -> authorization -> effect -> readback`

## Mandatory semantic boundaries

- `BYTES != MEANING`
- `SEQUENCE != CAUSALITY`
- `TRANSPORT_ACK != EFFECT_ACK`
- `OBSERVATION != TRUTH`
- `MODEL != REALITY`
- `VERIFIED_IMPLEMENTATION != AUTHORITY_EFFECT`
- `BOUND != EMPIRICALLY_CONFIRMED`
- `REPOSITORY_EVIDENCE != PUBLICATION`

## Minimum physical/digital measurement envelope

A measurement object that is intended to carry physical meaning MUST expose at least:

`(value, time, uncertainty, unit, calibration, provenance)`

For sampled/quantized signals, systems SHOULD additionally expose sampling rate, bandwidth/anti-alias assumptions, quantizer/scale, rounding mode and the transformation version.

## Fail-closed integration rule

Missing mandatory evidence does not become implicit success.

- missing metadata -> `HOLD`
- stale/unknown observation -> `REOBSERVE`
- external authority required -> `REQUEST_AUTHORITY`
- no action required -> `NOOP`

No repository-only success may be projected as merge, deployment, publication, physical execution, empirical confirmation, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` without exact evidence.

## Scientific positioning

Shannon, Wheeler, Landauer and QIK-VRT occupy different layers.

- Shannon: communication/information and sampling constraints.
- Wheeler: an information-and-physics research program / interpretation.
- Landauer: thermodynamic cost bound for logically irreversible erasure under stated assumptions.
- QIK-VRT: evidence, causality, authorization and effect-boundary architecture.

The point is interoperability, not equation-by-slogan.

## Files

- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.json` - machine-readable contract.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.schema.json` - JSON Schema.
- `README.md` - integration semantics.

Author / Product & Code Owner: Ingolf Lohmann.
