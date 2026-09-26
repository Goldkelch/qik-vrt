# QIK-VRT public-state observation ledger

This is the data-only branch `qikvrt/publication-monitor-state-v1`, not a product branch to merge into Main. It contains no executable workflows.

Canonical state: `monitor/state.json`. Append-only history: `monitor/history/`. Public HTTP response bytes: `monitor/responses/`.

Read the branch ref as an exact commit/tree, then read state on that commit. Do not use a chat file or the latest matching artifact as a substitute. Missing state is BLOCK; never reinitialize an existing history.

Implementation candidate: `fd241010125e03820bbd3571e099c6662c7a2527`, tree `a1a7bf7cf2e26fcdc068455f2d07b8a7826f5d2f` in Goldkelch/qik-vrt. Stable source locator: root `PUBLICATION_MONITOR.json` after legitimate Main integration. Initializing this ledger is not source approval or deployment.

Generation zero preserves the user's consumed crates.io zero baseline and records other platforms as recovery-required. Previous assistant reports remain historical; no fresh public observation is fabricated. The original local acknowledgment is also retained verbatim in `monitor/migration/`.

Only exact official public readbacks may advance subject state. Publication, scientific validation, package ownership and repository approval remain separate facts. External publication writes are forbidden. Outbox events are not delivered messages until an authorized consumer obtains delivery evidence and persists an exact event acknowledgment.
