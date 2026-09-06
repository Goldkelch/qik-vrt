# QIK-VRT Information -> Evidence -> Effect Axis v2.1

Status: `PROPOSED_REVIEW_CARRIER`

This research object makes an existing QIK-VRT invariant explicit for downstream Mesh systems, corrects the predecessor carrier against the already-public Zenodo corpus, and adds the transputer/scaling/AD-DA/singularity bridge:

`distinction -> information -> evidence binding -> causality assessment -> authorization -> effect -> readback`

The additional architectural chain is:

`compute scaling -> state scaling -> evidence scaling -> authority scaling -> effect scaling`

under the invariant:

**No transition may claim more than its boundary actually carries.**

## Public Zenodo prior-art binding

A repository-native inventory dated 2026-07-22 records a public Zenodo corpus already containing **14 version records in five concept lines**, verified there against the public Zenodo Records API and DOI records. The present carrier therefore treats the following as public publication anchors, not project-local-only artifacts:

- `10.5281/zenodo.20712301` — early repository/provenance/release-gating version;
- concept `10.5281/zenodo.21244411`, nine RFC/node/repository versions through `10.5281/zenodo.21267021`;
- `10.5281/zenodo.21482023` — mathematical-physical working version;
- `10.5281/zenodo.21488116` — machine-verifiable formalization;
- `10.5281/zenodo.21498773` — EFFECT_ACK working paper;
- `10.5281/zenodo.21498774` — versioned EFFECT_ACK software;
- `10.5281/zenodo.22283396` — *From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law*, published working paper / falsifiable hypothesis.

`QIKVRT_ZENODO_PRIOR_ART_V1.json` carries the machine-readable subset used by this synthesis. It is intentionally non-exhaustive beyond the explicitly bound records; later or additional public records remain discoverable without being silently inferred here.

## Transputer-to-evidence-mesh bridge

The added bridge treats the INMOS transputer and Atari Transputer Workstation as historical comparison architectures, not as predecessors that already implemented QIK-VRT. The historically supported continuity is the use of local compute nodes with explicit communication boundaries. QIK-VRT extends the architecture question to state semantics, evidence, authority, physical effect and readback.

The bridge connects:

- local compute and explicit channels;
- distributed serialization and canonical state identity;
- numeric scale, fixed point and quantization;
- ADC measurement envelopes;
- DAC/actuator effect attempts and physical readback;
- recursive Mesh composition;
- explicit classification of singularities, model boundaries and numerical pathologies.

It does **not** equate these domains physically. Their common structure is the disciplined analysis of mappings between state spaces and of the evidence carried across each mapping.

## Mandatory semantic boundaries

- `BYTES != MEANING`
- `SEQUENCE != CAUSALITY`
- `TRANSPORT_ACK != EFFECT_ACK`
- `COMMAND != OBSERVED_EFFECT`
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

Shannon, Wheeler, Landauer, the historical transputer architecture and QIK-VRT occupy different layers.

- Shannon: communication/information and sampling constraints.
- Wheeler: an information-and-physics research program / interpretation.
- Landauer: thermodynamic cost bound for logically irreversible erasure under stated assumptions.
- INMOS/Transputer: explicit local compute and communication architecture.
- QIK-VRT: evidence, causality, authorization and effect-boundary architecture.

The point is interoperability and structural comparison, not equation-by-slogan.

## Files

- `MANUSCRIPT.md` — canonical scientific synthesis, now including the transputer/scaling/AD-DA/singularity bridge.
- `TRANSPUTER_TO_EVIDENCE_MESH.md` — focused scientific bridge from historical parallel compute to evidence-bound Mesh architecture.
- `PROSA_ARTIKEL_FUER_ALLE.md` — original public read-aloud bridge from distinction to responsible effect.
- `PROSA_TRANSPUTER_ZUM_EVIDENZ_MESH.md` — public prose companion explaining the transputer-to-evidence-mesh bridge.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.json` — machine-readable Mesh contract.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1.schema.json` — JSON Schema.
- `QIKVRT_INFORMATION_EFFECT_AXIS_V1_TEST_VECTORS.json` — fail-closed examples.
- `QIKVRT_ZENODO_PRIOR_ART_V1.json` — explicit public Zenodo prior-art anchors.
- `ZENODO_METADATA.json` — metadata for a possible new synthesis deposit; existing DOI anchors are references, not the new record DOI.
- `DELIVERY_ACCEPTANCE_STATE.json` — fail-closed publication/readback acceptance boundary.

Author / Product & Code Owner: Ingolf Lohmann.
