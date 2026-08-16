<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT mesh replica orchestration

`state/autonomy/MESH_REPLICA_ORCHESTRATION_CONTRACT_V1.json` and
`tools/qikvrt_mesh_replica_orchestrator.py` define a bounded planning surface
for future mesh replicas. The controller has only `PLAN_VALIDATE_ONLY` mode.
It observes local Git identity and caller-supplied JSON; it makes no network
request, filesystem mutation, repository creation, fork, clone, fetch, push,
remote ref update, credential use, resource provisioning, or synchronization.

## Current operational result

The only possible results are `NOOP` and `HOLD`. A syntactically complete plan
still ends in `HOLD/APPLY_MODE_NOT_IMPLEMENTED`. This is intentional: planning
does not create a replica and a successful plan does not prove availability,
synchronization, equality, resource use, security, or an external effect.

The planner requires all of the following before it can even reach that bounded
`HOLD` state:

1. Exact source repository, `main` ref, head and tree equal the current local
   Authority identity.
2. A current Authority-bound observation with `FRESH_BOUND` node liveness.
3. No active productive writer and at most the declared queue capacity.
4. An allowlisted source, an isolated local read-only target, bounded task
   identity, and fixed replica/TTL/disk/CPU/network quotas.
5. No requested synchronization and no duplicate exact request.

The current Authority/Mirror liveness records are not fresh execution authority.
If they are missing, stale, divergent or unbound, the correct plan result is
`HOLD`, not a speculative replica or a false synchronization claim.

## Future execution boundary

Actual replica execution needs a separately persisted
`qikvrt_mesh_replica_execution_authorization_v1` that binds source and target
identity, visibility, read/write mode, task hash, resource caps, expiry,
path scope, synchronization direction, conflict handling and rollback. A later
apply controller also requires review and exact-head evidence.

Synchronization, if separately authorized in the future, is restricted to a
create-only review branch and pull request after fresh source-and-target
head/tree observation. Conflict or divergence remains `HOLD`; direct main
writes, force updates, deletion, automatic merging and credentialed writes are
forbidden.

Run the contract regression with:

```sh
python3 -B -m unittest -v tests.test_qikvrt_mesh_replica_orchestrator
```

This document and the controller do not authorize an execution effect.
