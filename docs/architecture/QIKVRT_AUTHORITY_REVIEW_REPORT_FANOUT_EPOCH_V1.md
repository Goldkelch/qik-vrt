<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Authority review-report fan-out: frozen Mesh epoch

`qikvrt_authority_review_report_fanout.yml` is an event-driven, finite
delivery projection for one already-bound Authority review report.  It is not a
Mesh discovery loop, a remote-state polling service, a merge mechanism, or an
effect acknowledgement.

## Frozen epoch before delivery

Before the workflow sends a repository-dispatch event, it reads the trusted
Authority `main` checkout and constructs one
`qikvrt_authority_review_mesh_epoch_v1` record.  The record is canonical JSON
whose `epoch_sha256` binds all of the following:

- the Authority repository, exact `main` commit and tree;
- the exact `registry/NODEMESH_INDEX.json` Git blob and SHA-256;
- the exact quadratic-codec policy bytes at
  `state/mesh/QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_V1.json`;
- the ordered projection of active nodes (`repository`, GUID, branch and
  registry path);
- `registry_node_count`, active `node_count`, a finite maximum, and
  `lane_count`; and
- every row-major lane identifier.

The workflow accepts only a non-empty active projection.  It rejects malformed
identities, duplicate active GUIDs or repositories, inconsistent registry
counts, and a registry or active-node cardinality above
`MAX_ACTIVE_MESH_NODES=64`.  A larger topology therefore reaches
`HOLD_UNVERIFIED` before a token-bearing remote request is attempted; it is not
silently truncated or made unbounded.

`N` is the number of ordered active nodes in this frozen epoch.  Nodes are
ordered lexicographically by `(repository, guid)`.  The lane at row `r` and
column `c` is represented by
`qikvrt-mesh-lane-v1/<r>/<c>/<source-guid>/<target-guid>`, with index
`row*N+column`; the record therefore contains exactly `N*N` row-major lane IDs.
This reuses the canonical mapping in the existing quadratic codec policy.  It
does not assert that a repository dispatch itself consumes a physical hardware
lane.

## Drift check

Immediately before the finite delivery loop, the workflow reobserves the
Authority `main` commit, tree, and Registry Git blob through the GitHub API.  A
Registry drift or Authority-main drift from the frozen epoch, an invalid epoch
digest, or an inconsistent `N*N` topology produces `HOLD_UNVERIFIED` and exits
before any dispatch.  The run retains the epoch and reobservation receipts as
workflow artifacts.

This is a single event-edge reobservation inside the triggering workflow: there
is no polling, periodic scan, or retry loop.  A change after the reobservation
is not hidden: each accepted dispatch remains bound to the earlier exact epoch.

## Stable per-target idempotency binding

For each target, the workflow derives canonical JSON under
`qikvrt_authority_review_report_delivery_idempotency_v1` and hashes it as the
`idempotency_key`.  Its binding inputs are:

```text
epoch_sha256 + source_head_sha + target_repository + target_guid
+ target_index + target_self_lane_id + event_type
```

The source head is the exact reviewed pull-request head, and the target identity
comes from the frozen epoch.  Thus the same epoch/source/target tuple produces
the same key, while a changed epoch, source head, or target produces a different
key.  The JSON is sent in the repository-dispatch `client_payload` together
with a compact epoch projection; the complete epoch is preserved in the
Authority workflow artifact rather than duplicated into every request.

GitHub's transport acceptance is not a target receipt and not an
`EFFECT_ACK_DONE`.  A target must retain and validate the provided key to make
a later replay idempotent.  The Authority workflow records only
`DISPATCH_ACCEPTED`; it does not assert delivery, processing, `PASS`,
`FINAL_PASS`, `EFFECT_ACK_DONE`, merge, deployment, or another external effect.
