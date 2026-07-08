#!/bin/sh
set -eu
mkdir -p registry evidence/seed_node_revalidation/runs
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
STATUS="registry/NODEMESH_STATUS.json"
INDEX="registry/NODEMESH_INDEX.json"
[ -f "$STATUS" ] || { echo "BLOCK missing $STATUS"; exit 2; }
[ -f "$INDEX" ] || { echo "BLOCK missing $INDEX"; exit 3; }
count_status() { grep -o '"effective_status"[[:space:]]*:[[:space:]]*"'$1'"' "$STATUS" 2>/dev/null | wc -l | tr -d ' '; }
node_count=$(sed -n 's/.*"node_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1); [ -n "$node_count" ] || node_count=0
active_count=$(count_status ACTIVE); stale_count=$(count_status STALE); suspended_count=$(count_status SUSPENDED); revoked_count=$(count_status REVOKED); unknown_count=$(count_status UNKNOWN)
accepted_count=$(grep -o '"registry_status"[[:space:]]*:[[:space:]]*"ACCEPTED"' "$STATUS" 2>/dev/null | wc -l | tr -d ' ')
status="PASS"; [ "$node_count" -lt 1 ] && status="BLOCK"
cat > registry/NODEMESH_REVALIDATION.json <<JSON
{
  "qikvrt_event": "NODEMESH_OPEN_MULTI_NODE_REVALIDATION_4AV1",
  "generated_utc": "$UTC",
  "run_id": "$RUN_ID",
  "status": "$status",
  "seed_repository": "Goldkelch/qik-vrt",
  "fixed_node_count": false,
  "node_count": $node_count,
  "accepted_count": $accepted_count,
  "active_count": $active_count,
  "stale_count": $stale_count,
  "suspended_count": $suspended_count,
  "revoked_count": $revoked_count,
  "unknown_count": $unknown_count,
  "open_multi_node_capable": true,
  "future_nodes_without_installer_change": true,
  "lifecycle_states": ["ACTIVE", "STALE", "SUSPENDED", "REVOKED", "UNKNOWN"],
  "source_status_path": "registry/NODEMESH_STATUS.json",
  "source_index_path": "registry/NODEMESH_INDEX.json",
  "node_addition_method": "append rows to registry/node_request_queue/*.tsv or registry/KNOWN_NODE_REQUESTS.tsv",
  "boundaries": {"known_or_queued_nodes_only": true, "seed_writes_only_to_seed_repository": true, "node_revalidation_does_not_write_to_node_repositories": true, "no_global_scanning": true, "no_self_propagation": true, "no_remote_mutation_without_authorization": true}
}
JSON
EVID="evidence/seed_node_revalidation/runs/$RUN_ID.json"
cp registry/NODEMESH_REVALIDATION.json "$EVID"
cp "$EVID" evidence/seed_node_revalidation/LATEST.json
[ "$status" = "PASS" ] || { echo "BLOCK QIKVRT_SEED_NODE_REVALIDATION node_count=$node_count"; exit 4; }
echo "QIKVRT_SEED_NODE_REVALIDATION PASS open_registry=true node_count=$node_count active=$active_count stale=$stale_count suspended=$suspended_count revoked=$revoked_count run_id=$RUN_ID"
