#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="qikvrt/05_Evidenz/PRAEZEDENZ_LOG.md"
DATE_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
COMMIT_HASH="$(git rev-parse HEAD 2>/dev/null || echo "UNBEKANNT")"
COMMIT_TITLE="$(git log -1 --pretty=%s 2>/dev/null || echo "UNBEKANNT")"

mkdir -p "$(dirname "$LOG_FILE")"

if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<'EOF'
# QIK-VRT PRAEZEDENZ_LOG

Status: DAUERHAFT_GEFÜHRT = TRUE  
Zweck: Heitere Präzedenzfälle nach Unterschied, Daten, Verantwortung und q.e.d. dokumentieren.  
Grenze: Das Log erzeugt keine Autorität. Es dokumentiert geprüfte Anschlussfälle.

---

EOF
fi

SCAN_TEXT="$(git show --name-only --pretty=format:%s HEAD 2>/dev/null || true)"

if echo "$SCAN_TEXT" | grep -qi "HEITER\|q.e.d.\|Quad Errat\|GATE_JURISTEREI\|33°\|zwei helme"; then
  {
    echo "## $DATE_UTC — $COMMIT_TITLE"
    echo
    echo "- Commit: \`$COMMIT_HASH\`"
    echo "- Gate: \`GATE_JURISTEREI v1.0.7\`"
    echo "- Status: \`HEITER = TRUE\`"
    echo "- Präzedenzart: Unterschied statt Autorität"
    echo "- Unterschied: Präzedenz / Autorität / Emotion / Rache wurden gegen Prüfung geführt"
    echo "- q.e.d.: Quad Errat gebrochen"
    echo
    echo "---"
    echo
  } >> "$LOG_FILE"
  echo "HEITER: Präzedenzfall in $LOG_FILE eingetragen."
else
  echo "Kein HEITERer Präzedenzfall erkannt. Kein Logeintrag."
fi
