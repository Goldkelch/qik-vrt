# QIK-VRT Mesh Authority Pages

Canonical Authority URL after a directly observed GitHub Pages delivery:

`https://goldkelch.github.io/qik-vrt/mesh/`

Canonical node URL form:

`https://goldkelch.github.io/qik-vrt/mesh/nodes/<NODE-GUID>/`

The pages are a deterministic projection of `registry/NODEMESH_INDEX.json`. Only registry entries simultaneously marked `ACCEPTED`, `ACTIVE`, and `ACTIVE` receive a GUID page.

## Automation

The client contains no timer and no periodic GitHub polling. It accepts repository-defined events through `BroadcastChannel`, `window.postMessage`, or an explicitly bound SSE stream. A missing transport remains visible as `HOLD`.

A `page_build` event performs exactly one HTTPS reobservation of the Authority root, machine topology, and every active GUID URL. The result is an audit receipt; no retry loop fabricates availability.

## Fail-closed boundary

`SOURCE_PRESENT_ON_PR != EFFECTIVE_ON_MAIN != PAGES_DEPLOYED != BROWSER_REOBSERVED != EFFECT_ACK_DONE`

The receipt does not claim independent review, physical M68000/Mega-ST execution, general Internet reachability, publication, `PASS`, `FINAL_PASS`, or general `EFFECT_ACK_DONE`.
