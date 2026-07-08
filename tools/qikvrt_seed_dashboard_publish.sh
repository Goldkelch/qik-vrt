#!/bin/sh
set -eu
mkdir -p docs evidence/seed_dashboard/runs
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
STATUS="registry/NODEMESH_STATUS.json"
INDEX="registry/NODEMESH_INDEX.json"
[ -f "$STATUS" ] || { echo "BLOCK missing $STATUS"; exit 2; }
[ -f "$INDEX" ] || { echo "BLOCK missing $INDEX"; exit 3; }
node_count=$(sed -n 's/.*"node_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
active_count=$(sed -n 's/.*"active_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
stale_count=$(sed -n 's/.*"stale_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
[ -n "$node_count" ] || node_count=0
[ -n "$active_count" ] || active_count=0
[ -n "$stale_count" ] || stale_count=0
cat > docs/qikvrt_mesh_dashboard.html <<HTML
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QIK-VRT Mesh Dashboard</title>
<style>body{font-family:Arial,sans-serif;margin:2rem;line-height:1.45}code{background:#eee;padding:.1rem .25rem}.card{border:1px solid #ccc;padding:1rem;margin:1rem 0;border-radius:.5rem}</style></head>
<body>
<h1>QIK-VRT Mesh Dashboard</h1>
<div class="card"><strong>Generated UTC:</strong> $UTC<br><strong>Run ID:</strong> $RUN_ID<br><strong>Seed:</strong> Goldkelch/qik-vrt</div>
<div class="card"><strong>Nodes:</strong> $node_count<br><strong>Active:</strong> $active_count<br><strong>Stale:</strong> $stale_count</div>
<h2>Evidence</h2>
<ul>
<li><code>registry/NODEMESH_INDEX.json</code></li>
<li><code>registry/NODEMESH_STATUS.json</code></li>
<li><code>registry/NODEMESH_REVALIDATION.json</code></li>
<li><code>audit/QIKVRT_MESH_AUDIT_REPORT.md</code></li>
<li><code>evidence/seed_mesh_maintenance/LATEST.json</code></li>
</ul>
<p>Boundary: authorized known nodes only, seed writes only to seed repository, no global scanning, no self propagation, no remote mutation without authorization.</p>
</body></html>
HTML
cat > docs/QIKVRT_MESH_DASHBOARD.md <<MD
# QIK-VRT Mesh Dashboard

generated_utc: $UTC  
run_id: $RUN_ID  
seed_repository: Goldkelch/qik-vrt  
node_count: $node_count  
active_count: $active_count  
stale_count: $stale_count

HTML dashboard: docs/qikvrt_mesh_dashboard.html
MD
EVID="evidence/seed_dashboard/runs/$RUN_ID.json"
cat > "$EVID" <<JSON
{
  "qikvrt_event": "SEED_DASHBOARD_PUBLISH_4AV1",
  "revalidation_path": "registry/NODEMESH_REVALIDATION.json",
  "generated_utc": "$UTC",
  "run_id": "$RUN_ID",
  "status": "PASS",
  "dashboard_html": "docs/qikvrt_mesh_dashboard.html",
  "dashboard_md": "docs/QIKVRT_MESH_DASHBOARD.md"
}
JSON
cp "$EVID" evidence/seed_dashboard/LATEST.json
echo "QIKVRT_SEED_DASHBOARD_PUBLISH PASS run_id=$RUN_ID"
