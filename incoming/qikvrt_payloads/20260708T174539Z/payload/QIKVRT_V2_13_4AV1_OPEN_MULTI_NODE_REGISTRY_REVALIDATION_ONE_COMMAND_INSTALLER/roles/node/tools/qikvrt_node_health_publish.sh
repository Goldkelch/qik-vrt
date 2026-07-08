#!/bin/sh
set -eu
CONFIG="qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv"
[ -f "$CONFIG" ] || { echo "BLOCK missing $CONFIG"; exit 2; }
line=$(grep -v '^#' "$CONFIG" | grep -v '^$' | head -n 1)
guid=$(printf '%s' "$line" | cut -f1)
source_repo=$(printf '%s' "$line" | cut -f2)
seed_repo=$(printf '%s' "$line" | cut -f3)
node_branch=$(printf '%s' "$line" | cut -f6)
ttl_min=$(printf '%s' "$line" | cut -f7)
[ -n "$node_branch" ] || node_branch="main"
[ -n "$ttl_min" ] || ttl_min="1500"
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EXPIRES="$(date -u -d "+$ttl_min minutes" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p qikvrt/runtime/onboarding evidence/node_health
cat > qikvrt/runtime/onboarding/NODE_HEALTH.json <<JSON
{
  "qikvrt_event": "NODE_HEALTH_HEARTBEAT_4AV1",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "node_branch": "$node_branch",
  "status": "ACTIVE",
  "heartbeat_utc": "$UTC",
  "expires_utc": "$EXPIRES",
  "heartbeat_ttl_minutes": $ttl_min,
  "run_id": "$RUN_ID",
  "boundaries": {
    "node_writes_only_to_node_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON
cat > "evidence/node_health/$RUN_ID.json" <<JSON
{
  "qikvrt_event": "NODE_HEALTH_EVIDENCE_4AV1",
  "guid": "$guid",
  "repository": "$source_repo",
  "status": "PASS",
  "heartbeat_utc": "$UTC",
  "expires_utc": "$EXPIRES",
  "run_id": "$RUN_ID"
}
JSON
cp "evidence/node_health/$RUN_ID.json" evidence/node_health/LATEST.json
echo "QIKVRT_NODE_HEALTH_PUBLISH PASS $guid run_id=$RUN_ID"
