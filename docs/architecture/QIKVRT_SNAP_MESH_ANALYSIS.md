<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# SNAP analysis on the existing real-Mesh path

This adapter consumes `qikvrt_real_mesh_execution_receipt_v1` from
`tools/qikvrt_real_mesh.py`. It does not create a second Mesh controller.
The existing `.github/workflows/qikvrt_real_mesh.yml` executes the Mesh,
verifies its receipt, builds the pinned native SNAP bridge, and analyzes the
same receipt against the independently supplied exact candidate head/tree.

## Implemented scope

* Canonical, deterministic node-ID mapping and undirected topology projection;
  isolated nodes are retained. Per-node metadata, including unequal root trees,
  stays separate from the execution source tree.
* SNAP C++ `TUNGraph`, `TSnap::GetWccs` and `TSnap::GetShortPath`: node/edge
  counts, degrees, component count, maximum finite component diameter and
  unreachable **ordered** node pairs. The current adapter inherits the existing
  4..16-node real-Mesh scope. This is integration evidence, not a scalability
  benchmark or a claim that SNAP is necessary for a four-node graph.
* Byte SHA-256, canonical receipt SHA-256, topology hash, graph hash, head/tree,
  bridge/adapter hashes, locked SNAP source, compiler version and binary hash.
* No Python graph-library fallback. Missing or unbound SNAP returns nonzero
  `HOLD`; a prior output is not overwritten. Builds and outputs are create-only.

A topology link is not a causal event edge. A declared route is not fresh
node-ledger readback. Receipt integrity is not authentication. Causal motif
mining, event-level predecessor validation, automatic review/merge/publication,
Authority/Mirror synchronization and effect authorization are **not** implemented
by this adapter. The original Effect-Ack engine and Mesh verification remain
separate. In particular, `TRANSPORT_ACK != EFFECT_ACK` is unchanged.

## Reproduce with the real backend (Linux)

Use a clean, authorized QIK-VRT checkout. Provision the external dependency
explicitly; analysis and the builder themselves make no network requests:

```sh
git clone https://github.com/snap-stanford/snap.git /tmp/qikvrt-snap-source
git -C /tmp/qikvrt-snap-source checkout --detach 6924a035aabd1ce0a547b94e995e142f29eb5040
python3 -B tools/qikvrt_tool_cache.py verify
mkdir -p .qikvrt/real-mesh/snap
python3 -B tools/qikvrt_build_snap.py --source /tmp/qikvrt-snap-source \
  --output .qikvrt/real-mesh/snap/qikvrt-snap
QIKVRT_SNAP_BACKEND="$PWD/.qikvrt/real-mesh/snap/qikvrt-snap" \
  python3 -B -m unittest discover -s tests -p test_qikvrt_snap_mesh.py -v
python3 -B tools/qikvrt_real_mesh.py demo \
  --source-head "$(git rev-parse HEAD)" --source-tree "$(git rev-parse HEAD^{tree})" \
  --workdir .qikvrt/real-mesh/runtime \
  --output .qikvrt/real-mesh/QIKVRT_REAL_MESH_EXECUTION_RECEIPT_V1.json
python3 -B tools/qikvrt_real_mesh_system_verification.py verify \
  --receipt .qikvrt/real-mesh/QIKVRT_REAL_MESH_EXECUTION_RECEIPT_V1.json
python3 -B tools/qikvrt_snap_mesh.py \
  --receipt .qikvrt/real-mesh/QIKVRT_REAL_MESH_EXECUTION_RECEIPT_V1.json \
  --expected-head "$(git rev-parse HEAD)" --expected-tree "$(git rev-parse HEAD^{tree})" \
  --backend .qikvrt/real-mesh/snap/qikvrt-snap \
  --output .qikvrt/real-mesh/SNAP_ANALYSIS.json
```

The build self-test uses a cycle plus an isolated node. Native integration tests
are explicitly skipped when the backend environment variable is absent. Such a
local test run is not native SNAP execution evidence; the workflow sets the
variable and requires an executable backend. Failures retain diagnostics and do
not fall back to synthetic results. Reproduction uses fresh output directories.
There is no polling, auto-installation or remote writer in this adapter.

## Dependency, cache and rights

`runtime/toolchains/SNAP.lock.json` pins source commit and tree, not a moving
branch or an ambiguous PyPI package. The builder checks clean source before and
after compilation, preserves the exact BSD notice beside the binary, and
records a native self-test. Compiler and SNAP provisioning are registered in the
existing tool-cache registry. Builds are job-local, retained as workflow
artifacts and not automatically restored from untrusted PR caches. Removing
only the disposable build directory is the rollback; no global install occurs.

Only SNAP core/GLib core are linked. No SNAP dataset or `snap-adv` component is
imported. The unmodified upstream license is `third_party/snap/LICENSE.txt`;
source download/build does not relicense the QIK-VRT adapter. The source pin is
unsigned; Git object IDs and local build hashes are identity/integrity evidence,
not publisher signatures or remote attestation. Runtime provenance assumes a
trusted local compiler/process environment.

Upstream references:
https://snap.stanford.edu/snap/
https://snap.stanford.edu/snap/doc/snapdev-ref/
https://github.com/snap-stanford/snap/tree/6924a035aabd1ce0a547b94e995e142f29eb5040
