# QIK-VRT Open Multi-Node Architecture 4AV1

4AV1 removes the fixed additional-node count from 4AV. The Seed keeps an open node registry. Future Nodes are added by appending authorized request rows under `registry/node_request_queue/*.tsv` or `registry/KNOWN_NODE_REQUESTS.tsv`.

This preserves the QIK-VRT boundary: no global scanning, no self-propagation, no foreign repository write. The Seed revalidates only known or explicitly queued Nodes.

Every participating Repository Node is subject to the
[synchronous REST and compiled-relation architecture decision](ARCHITECTURE.md#owner-decision-synchronous-rest-and-compiled-relations).
The existing Node onboarding/acceptance path must bind the shared API version,
endpoint, supported kernel identities, actual execution backend, exact source
revision and measured request-to-result behavior for that Node. The decision
adds an acceptance requirement; this documentation change does not itself
install, expose or accept a service on any Node.
