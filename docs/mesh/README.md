# QIK-VRT Mesh Live Terminal

Canonical Authority URL after Pages promotion:

`https://goldkelch.github.io/qik-vrt/mesh/`

Canonical node URL:

`https://goldkelch.github.io/qik-vrt/mesh/nodes/<NODE-GUID>/`

The GUID is the stable registry identity and must not be replaced by a branch, PR, commit, mutable repository name, or transient runner identity.

## Event-driven transport

The HTML client contains no periodic GitHub polling loop. It accepts `qikvrt_effect_ack_mesh_event_v1` events through browser-local `BroadcastChannel`/`window.postMessage` adapters and, when explicitly bound, an SSE `effect_stream` transport. Absence or loss of a push transport is a visible `HOLD`; the UI must not fabricate freshness.

Required event fields are `schema`, `node_guid`, and a state payload. Recommended fields are `event_id`, `observed_utc`, `head`, `tree`, `state`, `progress`, `mesh_progress`, `front`, and effect-ack provenance.

## Current topology seed

Authority: `Goldkelch/qik-vrt`

Known accepted remote node from `registry/NODEMESH_INDEX.json`:

- GUID `a84f157a-cef2-4c47-bca9-8f407085bdbe`
- repository `ingolf-lohmann/qik-vrt`

Future authorized nodes receive their own immutable GUID URL. Child-node topology must come from repository-bound registry data or authenticated effect events; the UI must not discover or mutate arbitrary repositories.

## Boundary

A visual update is not itself `EFFECT_ACK_DONE`. Repository state, transport acknowledgement, effect acknowledgement, browser rendering, physical-machine execution, review authority, merge authority, and external publication remain distinct evidence classes.
