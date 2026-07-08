# QIKVRT V2.13.4AV11 Open Multi-Node Registry and Revalidation Installer

One-command Windows installer for extending the public QIK-VRT Seed/Node mesh from a single-node productization proof to a multi-node-capable registry and revalidation surface.

Start on Windows:

```text
START_HIER_OPEN_MULTI_NODE_REVALIDATION_INSTALL.cmd
```

Properties:

- ASCII-only CMD surface
- masked local token dialogs
- two repository-specific token contexts
- no PowerShell primary path
- no `.ps1` files
- no Git in the Windows installer
- no embedded token
- seed multi-node registry configuration
- per-node ACTIVE / STALE / SUSPENDED / REVOKED / UNKNOWN revalidation
- central `registry/NODEMESH_REVALIDATION.json`
- run-id-scoped evidence

Default repositories:

```text
Seed: Goldkelch/qik-vrt
Node: ingolf-lohmann/qik-vrt
Branch: main
```

The installer first configures the known-node registry. It always includes the primary Ingolf node and can optionally add additional Node request URLs interactively before uploading the Seed role files.

Expected Seed outputs after workflow dispatch:

```text
registry/NODEMESH_INDEX.json
registry/NODEMESH_STATUS.json
registry/NODEMESH_REVALIDATION.json
evidence/seed_node_revalidation/runs/<RUN_ID>.json
evidence/seed_mesh_audit/LATEST.json
docs/qikvrt_mesh_dashboard.html
```

Expected Node outputs for the primary node:

```text
qikvrt/runtime/onboarding/NODE_HEALTH.json
qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json
qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json
evidence/node_self_audit/LATEST.json
```

Boundary:

```text
Seed reads only authorized known Node entries.
Seed writes only to the Seed repository.
Node workflows write only to their own Node repository.
No global scanning.
No self propagation.
No remote mutation without authorization.
```


## 4AV1 Open Registry Repair

This package fixes the 4AV usability/architecture regression: it does not ask for a predetermined number of additional Nodes. Future Nodes are added through the open authorized queue `registry/node_request_queue/*.tsv` and are revalidated by scheduled Seed workflows.
