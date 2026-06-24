#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR=".git/hooks"
POST_COMMIT="$HOOK_DIR/post-commit"
PRE_COMMIT="$HOOK_DIR/pre-commit"
PRE_TARGET="qikvrt/tools/v1.0.15/pre_commit_gate.sh"
POST_TARGET="qikvrt/tools/v1.0.7/post_commit_heiter.sh"

[ -d ".git" ] || { echo "BLOCK: Kein Git-Repository gefunden."; exit 1; }
[ -f "$PRE_TARGET" ] || { echo "BLOCK: $PRE_TARGET nicht gefunden."; exit 1; }
[ -f "$POST_TARGET" ] || { echo "BLOCK: $POST_TARGET nicht gefunden."; exit 1; }

mkdir -p "$HOOK_DIR"

cat > "$PRE_COMMIT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ -x "qikvrt/tools/v1.0.15/pre_commit_gate.sh" ]; then
  ./qikvrt/tools/v1.0.15/pre_commit_gate.sh
else
  echo "BLOCK: pre_commit_gate.sh nicht ausführbar oder nicht vorhanden."
  exit 1
fi
EOF

cat > "$POST_COMMIT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ -x "qikvrt/tools/v1.0.7/post_commit_heiter.sh" ]; then
  ./qikvrt/tools/v1.0.7/post_commit_heiter.sh
else
  echo "QIK-VRT WARNUNG: post_commit_heiter.sh nicht ausführbar oder nicht vorhanden."
fi
EOF

chmod +x "$PRE_COMMIT" "$POST_COMMIT"
echo "PASS: .git/hooks/pre-commit installiert."
echo "PASS: .git/hooks/post-commit installiert."
echo "GRENZE: Hooks dokumentieren/pruefen, erzeugen aber keine Autorität."
