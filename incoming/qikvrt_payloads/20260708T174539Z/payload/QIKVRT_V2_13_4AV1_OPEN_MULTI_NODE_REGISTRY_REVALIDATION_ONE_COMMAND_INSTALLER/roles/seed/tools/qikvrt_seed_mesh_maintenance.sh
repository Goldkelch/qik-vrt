#!/bin/sh
set -eu
KNOWN="registry/KNOWN_NODE_REQUESTS.tsv"
POLICY="registry/NODE_POLICY.tsv"
QUEUE_DIR="registry/node_request_queue"
[ -f "$KNOWN" ] || { echo "BLOCK missing $KNOWN"; exit 2; }
mkdir -p registry evidence/seed_mesh_maintenance/runs
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
TMPDIR="${TMPDIR:-/tmp}"
ALL_NODES="$TMPDIR/qikvrt_4av1_maintenance_nodes_$RUN_ID.tsv"
: > "$ALL_NODES"
append_tsv(){ f="$1"; [ -f "$f" ] || return 0; while IFS= read -r line || [ -n "$line" ]; do case "$line" in ''|'#'*) continue ;; esac; printf '%s\n' "$line" >> "$ALL_NODES"; done < "$f"; }
append_tsv "$KNOWN"
if [ -d "$QUEUE_DIR" ]; then for q in "$QUEUE_DIR"/*.tsv; do [ -f "$q" ] && append_tsv "$q" || true; done; fi
INDEX="registry/NODEMESH_INDEX.json"
STATUS="registry/NODEMESH_STATUS.json"
NODE_TMP="registry/.nodemesh_nodes.tmp"
STATUS_TMP="registry/.nodemesh_status.tmp"
: > "$NODE_TMP"; : > "$STATUS_TMP"
count=0; active_count=0; stale_count=0; suspended_count=0; revoked_count=0; unknown_count=0; duplicate_count=0; seen_guids=" "
policy_status_for(){ g="$1"; if [ -f "$POLICY" ]; then awk -F '\t' -v G="$g" 'BEGIN{v="ACTIVE"} $1==G {v=$2} END{print v}' "$POLICY"; else printf '%s\n' ACTIVE; fi; }
json_get_string(){ key="$1"; file="$2"; sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$file" | head -n 1; }
now_epoch=$(date -u +%s)
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  guid=$(printf '%s' "$line" | cut -f1); source_repo=$(printf '%s' "$line" | cut -f2); seed_repo=$(printf '%s' "$line" | cut -f3); request_url=$(printf '%s' "$line" | cut -f4); node_branch=$(printf '%s' "$line" | cut -f5); ttl_min=$(printf '%s' "$line" | cut -f6)
  [ -n "$node_branch" ] || node_branch="main"; [ -n "$ttl_min" ] || ttl_min="1500"
  case "$seen_guids" in *" $guid "*) duplicate_count=$((duplicate_count+1)); continue ;; esac
  seen_guids="$seen_guids$guid "
  entry="registry/nodes/$guid.json"; registry_status="UNKNOWN"; [ -f "$entry" ] && registry_status=$(json_get_string status "$entry"); [ -n "$registry_status" ] || registry_status="UNKNOWN"
  policy_status=$(policy_status_for "$guid")
  node_health_url="https://raw.githubusercontent.com/$source_repo/$node_branch/qikvrt/runtime/onboarding/NODE_HEALTH.json"; node_ack_url="https://raw.githubusercontent.com/$source_repo/$node_branch/qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json"; node_renewal_url="https://raw.githubusercontent.com/$source_repo/$node_branch/qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json"
  health="false"; ack="false"; renewal="false"; heartbeat_status="MISSING"; effective_status="UNKNOWN"; heartbeat_utc=""; expires_utc=""
  hfile="$TMPDIR/qikvrt_health_$guid.json"; afile="$TMPDIR/qikvrt_ack_$guid.json"; rfile="$TMPDIR/qikvrt_renewal_$guid.json"
  if curl -fsSL "$node_health_url" -o "$hfile"; then health="true"; heartbeat_utc=$(json_get_string heartbeat_utc "$hfile"); expires_utc=$(json_get_string expires_utc "$hfile"); if [ -n "$expires_utc" ]; then exp_epoch=$(date -u -d "$expires_utc" +%s 2>/dev/null || printf '%s' 0); else exp_epoch=0; fi; if [ "$exp_epoch" -gt "$now_epoch" ]; then heartbeat_status="FRESH"; else heartbeat_status="STALE"; fi; fi
  if curl -fsSL "$node_ack_url" -o "$afile"; then ack="true"; fi
  if curl -fsSL "$node_renewal_url" -o "$rfile"; then renewal="true"; fi
  if [ "$policy_status" = "SUSPENDED" ]; then effective_status="SUSPENDED"; suspended_count=$((suspended_count+1));
  elif [ "$policy_status" = "REVOKED" ]; then effective_status="REVOKED"; revoked_count=$((revoked_count+1));
  elif [ "$registry_status" = "ACCEPTED" ] && [ "$health" = "true" ] && [ "$heartbeat_status" = "FRESH" ] && [ "$ack" = "true" ]; then effective_status="ACTIVE"; active_count=$((active_count+1));
  elif [ "$registry_status" = "ACCEPTED" ]; then effective_status="STALE"; stale_count=$((stale_count+1)); else effective_status="UNKNOWN"; unknown_count=$((unknown_count+1)); fi
  [ "$count" -gt 0 ] && printf ',\n' >> "$NODE_TMP"
  cat >> "$NODE_TMP" <<JSON
    {"guid":"$guid","repository":"$source_repo","seed_repository":"$seed_repo","node_branch":"$node_branch","registry_status":"$registry_status","policy_status":"$policy_status","effective_status":"$effective_status","registry_path":"$entry","node_request_url":"$request_url","node_health_url":"$node_health_url","node_ack_url":"$node_ack_url","node_renewal_url":"$node_renewal_url"}
JSON
  [ "$count" -gt 0 ] && printf ',\n' >> "$STATUS_TMP"
  cat >> "$STATUS_TMP" <<JSON
    {"guid":"$guid","repository":"$source_repo","registry_status":"$registry_status","policy_status":"$policy_status","effective_status":"$effective_status","node_health_visible":$health,"node_ack_visible":$ack,"node_renewal_visible":$renewal,"heartbeat_status":"$heartbeat_status","heartbeat_utc":"$heartbeat_utc","expires_utc":"$expires_utc"}
JSON
  count=$((count+1))
done < "$ALL_NODES"
cat > "$INDEX" <<JSON
{
  "qikvrt_event": "NODEMESH_INDEX_AGGREGATE_4AV1_OPEN_REGISTRY",
  "generated_utc": "$UTC",
  "run_id": "$RUN_ID",
  "seed_repository": "Goldkelch/qik-vrt",
  "fixed_node_count": false,
  "node_count": $count,
  "active_count": $active_count,
  "stale_count": $stale_count,
  "suspended_count": $suspended_count,
  "revoked_count": $revoked_count,
  "unknown_count": $unknown_count,
  "duplicate_count": $duplicate_count,
  "nodes": [
$(cat "$NODE_TMP")
  ],
  "discovery_scope": ["registry/KNOWN_NODE_REQUESTS.tsv", "registry/node_request_queue/*.tsv"],
  "boundaries": {"seed_index_only_reads_authorized_known_nodes_and_queue": true, "seed_writes_only_to_seed_repository": true, "no_global_scanning": true, "no_self_propagation": true, "no_remote_mutation_without_authorization": true}
}
JSON
cat > "$STATUS" <<JSON
{"qikvrt_event":"NODEMESH_STATUS_AGGREGATE_4AV1_OPEN_REGISTRY","generated_utc":"$UTC","run_id":"$RUN_ID","seed_repository":"Goldkelch/qik-vrt","fixed_node_count":false,"node_count":$count,"active_count":$active_count,"stale_count":$stale_count,"suspended_count":$suspended_count,"revoked_count":$revoked_count,"unknown_count":$unknown_count,"nodes":[
$(cat "$STATUS_TMP")
]}
JSON
EVID="evidence/seed_mesh_maintenance/runs/$RUN_ID.json"
cat > "$EVID" <<JSON
{"qikvrt_event":"SEED_MESH_MAINTENANCE_EVIDENCE_4AV1","generated_utc":"$UTC","run_id":"$RUN_ID","status":"PASS","fixed_node_count":false,"node_count":$count,"active_count":$active_count,"stale_count":$stale_count,"suspended_count":$suspended_count,"revoked_count":$revoked_count,"unknown_count":$unknown_count,"index_path":"$INDEX","status_path":"$STATUS"}
JSON
cp "$EVID" evidence/seed_mesh_maintenance/LATEST.json
rm -f "$ALL_NODES" "$NODE_TMP" "$STATUS_TMP"
echo "QIKVRT_SEED_MESH_MAINTENANCE PASS open_registry=true node_count=$count active=$active_count stale=$stale_count suspended=$suspended_count revoked=$revoked_count run_id=$RUN_ID"
