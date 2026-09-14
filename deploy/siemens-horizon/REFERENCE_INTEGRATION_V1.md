# QIK-VRT Siemens Executable Reference Integration V1

This is the durable executable reference implementation for the Siemens/Horizon/Xcelerator integration profile already carried on Trusted Main.

## Closed roundtrip

`OBSERVE -> exact subject hash -> PREPARE -> deterministic twin simulation -> AUTHORITY_COMMIT(simulated) -> POST_EFFECT_REOBSERVE -> EFFECT_ACK receipt`

The executable implementation is `src/qikvrt_siemens_reference_integration.py`. The canonical reference subject is `deploy/siemens-horizon/reference-twin-state.json`. The dedicated workflow executes the same roundtrip and preserves an exact-head JSONL receipt artifact.

## Safety and claim boundary

The current adapter is deliberately `SIMULATED_DIGITAL_TWIN_ONLY`. It proves the software contract and effect-ack semantics for a deterministic reference twin. It does not claim Siemens tenant connectivity, Siemens endorsement, rail SIL evidence, clinical validation, physical actuator execution, or physical EFFECT_ACK.

A real Siemens adapter may replace only the bounded adapter edge. It MUST retain exact subject/version binding, PREPARE without effect, explicit authority before COMMIT, post-effect reobservation, and fail-closed `HOLD_UNVERIFIED` on stale or ambiguous state.

## Successor adapters

1. D4R::Horizon SDK / RailML read-write adapter.
2. Siemens Xcelerator / Executable Digital Twin API adapter.
3. Siemens-supported Edge/OCI deployment wrapper for the existing Firefox + EFFECT_ACK HTTP terminal.

Each successor must produce its own exact external readback receipt; this reference receipt is not transferable evidence.
