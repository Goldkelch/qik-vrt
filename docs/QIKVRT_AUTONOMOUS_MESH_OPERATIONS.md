# QIK-VRT Autonomous Mesh Operations

4AV1 adds lifecycle hardening: renewal, heartbeat expiry, Seed status aggregation, Seed audit export, and a human readable dashboard.

Core boundary: every repository writes only to itself. The Seed reads only authorized known Node URLs listed in `registry/KNOWN_NODE_REQUESTS.tsv`.

The registry keeps executable continuity and mutable node liveness on separate
refs. `node_branch` binds the workflow-executor continuity receipt;
`node_state_ref` binds health, Seed-acceptance acknowledgement, and renewal.
This permits a Mirror to retain role-local state on its own dedicated branch
without adding those mutable records to the portable `main` tree. Every remote
liveness document must bind both values, so moving bytes between refs cannot
silently transfer continuity or freshness evidence.
