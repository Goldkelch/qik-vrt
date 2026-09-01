# QIK-VRT Open Node Request Queue

This folder is intentionally open-ended. Do not predeclare a node count.
Add future Node request rows to OPEN_NODE_REQUESTS.tsv or add additional TSV files with the same columns.
The Seed revalidation workflow reads all queue rows on each run and does not perform global scanning.

Columns:
guid<TAB>source_repo<TAB>seed_repo<TAB>request_url<TAB>node_branch<TAB>node_state_ref<TAB>heartbeat_ttl_minutes<TAB>lifecycle_policy

`node_branch` binds the repository-native workflow-executor continuity receipt.
`node_state_ref` independently binds the three role-local liveness records
(`NODE_HEALTH.json`, `SEED_ACCEPTANCE_STATUS.json`, and
`NODE_REGISTRATION_RENEWAL.json`). The two refs may be equal, but a Mirror may
keep these role-local records on a dedicated state branch so portable `main`
content remains independent of mutable node state.

Allowed lifecycle_policy values: ACTIVE, SUSPENDED, REVOKED.
