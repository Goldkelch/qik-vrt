#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
fail(){ echo "BLOCK $1"; exit 1; }
[ -f START_HIER_PRODUCTIZATION_HARDENING_INSTALL.cmd ] || fail missing_cmd
[ -f tools/qikvrt_4au_installer.js ] || fail missing_installer_js
find . -name '*.ps1' | grep -q . && fail ps1_present || true
grep -R "powershell" START_HIER_PRODUCTIZATION_HARDENING_INSTALL.cmd tools roles 2>/dev/null && fail powershell_marker || true
grep -R "github_pat_" CONTRACT_STATUS.md COPYRIGHT_AND_LICENSE_ACCEPTANCE.md README.md README_DE.md README_EN.md START_HIER_PRODUCTIZATION_HARDENING_INSTALL.cmd roles tools 2>/dev/null && fail embedded_token || true
for f in roles/seed/tools/*.sh roles/node/tools/*.sh; do sh -n "$f" || fail "shell_syntax_$f"; done
for f in roles/seed/.github/workflows/*.yml roles/node/.github/workflows/*.yml; do grep -q "QIKVRT_PUSH_ATTEMPT" "$f" || fail "missing_push_retry_$f"; done
grep -q 'docs/QIKVRT_AUDIT_EXPORT.md' roles/seed/tools/qikvrt_seed_mesh_audit_export.sh || fail missing_audit_doc_output
grep -q 'SEED_AUDIT_DOC' tools/qikvrt_4au_installer.js || fail missing_audit_doc_wait
cc -std=c99 -Wall -Wextra -pedantic roles/seed/tools/qikvrt_handshake_core.c -o /tmp/qikvrt_4au1_core
/tmp/qikvrt_4au1_core | grep -q QIKVRT_4AU_HANDSHAKE_CORE_OK || fail core_run
# mock seed audit export
rm -rf /tmp/qikvrt_4au1_mock && mkdir -p /tmp/qikvrt_4au1_mock/registry
cp roles/seed/tools/qikvrt_seed_mesh_audit_export.sh /tmp/qikvrt_4au1_mock/
cat > /tmp/qikvrt_4au1_mock/registry/NODEMESH_INDEX.json <<'JSON'
{"node_count":1,"nodes":[{"guid":"a84f157a-cef2-4c47-bca9-8f407085bdbe","repository":"ingolf-lohmann/qik-vrt","status":"ACCEPTED"}]}
JSON
cat > /tmp/qikvrt_4au1_mock/registry/NODEMESH_STATUS.json <<'JSON'
{"node_count":1,"active_count":1,"stale_count":0}
JSON
(cd /tmp/qikvrt_4au1_mock && QIKVRT_RUN_ID=TEST4AU1 sh qikvrt_seed_mesh_audit_export.sh)
[ -f /tmp/qikvrt_4au1_mock/evidence/seed_mesh_audit/runs/TEST4AU1.json ] || fail mock_audit_evidence_missing
[ -f /tmp/qikvrt_4au1_mock/docs/QIKVRT_AUDIT_EXPORT.md ] || fail mock_audit_doc_missing
echo QIKVRT_4AU1_AUDIT_PUSHFIX_CONTRACT_PASS
