# QIK-VRT Mesh Audit Report

- generated_utc: 2026-07-13T10:01:56Z
- run_id: 29241273301
- seed_repository: Goldkelch/qik-vrt
- node_count: 1
- active_count: 1
- stale_count: 0

## Evidence paths

- registry/NODEMESH_INDEX.json
- registry/NODEMESH_STATUS.json
- evidence/seed_mesh_maintenance/LATEST.json
- registry/NODEMESH_REVALIDATION.json
- evidence/seed_node_revalidation/LATEST.json

## Boundary statement

The Seed reads only authorized known Node entries. The Seed writes only to the Seed repository. Nodes write only to their own Node repository. No global scanning, no self propagation, and no remote mutation without authorization are part of this audit surface.
