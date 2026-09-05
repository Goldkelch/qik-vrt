# QIK-VRT Information -> Evidence -> Effect Axis v2

Status: `PROPOSED_REVIEW_CARRIER`

This research object makes an existing QIK-VRT invariant explicit for downstream Mesh systems and corrects the predecessor carrier against the already-public Zenodo corpus:

`distinction -> information -> evidence binding -> causality assessment -> authorization -> effect -> readback`

## Public Zenodo prior-art binding

A repository-native inventory dated 2026-07-22 records a public Zenodo corpus already containing **14 version records in five concept lines**, verified there against the public Zenodo Records API and DOI records. The present carrier therefore treats the following as public publication anchors, not project-local-only artifacts:

- `10.5281/zenodo.20712301` — early repository/provenance/release-gating version;
- concept `10.5281/zenodo.21244411`, nine RFC/node/repository versions through `10.5281/zenodo.21267021`;
- `10.5281/zenodo.21482023` — 62-page mathematical-physical working version;
- `10.5281/zenodo.21488116` — machine-verifiable formalization;
- `10.5281/zenodo.21498773` — EFFECT_ACK working paper;
- `10.5281/zenodo.21498774` — versioned EFFECT_ACK software;
- `10.5281/zenodo.22283396` — *From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law*, published working paper / falsifiable hypothesis.

`QIKVRT_ZENODO_PRIOR_ART_V1.json` carries the machine-readable subset used by this synthesis. It is intentionally non-exhaustive beyond the explicitly bound records; later or additional public records remain discoverable without being silently inferred here.

## Mandatory semantic boundaries

- `BYTES != MEANING`
- `SEQUENCE != CAUSALITY`
- `TRANSPORT_ACK != EFFECT_ACK`
- `OBSERVATION != TRUTH`
- `MODEL != REALITY`
- `VERIFIED_IMPLEMENTATION != AUTHORITY_EFFECT`
- `BOUND != EMPIRICALLY_CONFIRMED`
- `REPOSITORY_EVIDENCE != ZENODO_PUBLICATION`
- `ZENODO_PUBLICATION != EMPIRICAL_CONFIRMATION`
- `FALSIFIABLE_HYPOTHESIS != EMPIRICALLY_CONFIRMED_LAW`

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

No repository-only success may be projected as merge, deployment, new publication, physical execution, empirical confirmation, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` without exact evidence. Conversely, an existing Zenodo publication is public-publication evidence but still not empirical confirmation.

## Scientific positioning

Shannon, Wheeler, Landauer and QIK-VRT occupy different layers.

- Shannon: communication/information and sampling constraints.
- Wheeler: an information-and-physics research program / interpretation.
- Landauer: thermodynamic cost bound for logically irreversible erasure under stated assumptions.
- QIK-VRT: evidence, causality, authorization and effect-boundary architecture.

The point is interoperability, not equation-by-slogan.

## Files

- `MANUSCRIPT.md` — corrected scientific synthesis with public Zenodo publication history.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.json` — machine-readable Mesh contract.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.schema.json` — JSON Schema.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1_TEST_VECTORS.json` — fail-closed examples.
- `QIKVRT_ZENODO_PRIOR_ART_V1.json` — explicit public Zenodo prior-art anchors.
- `ZENODO_METADATA.json` — metadata for a possible new synthesis deposit; existing DOI anchors are references, not the new record DOI.

Author / Product & Code Owner: Ingolf Lohmann.
