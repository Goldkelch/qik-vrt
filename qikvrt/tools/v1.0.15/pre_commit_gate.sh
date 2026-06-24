#!/usr/bin/env bash
set -euo pipefail

echo "=== QIK-VRT MESH-GATE AKTIV v1.0.15 ==="

[ -f "qikvrt/protocol/v1.0.7/GATE_CHECKLIST.md" ] || {
  echo "BLOCK: GATE_CHECKLIST.md fehlt."
  exit 1
}

STAGED_FILES="$(mktemp)"
trap 'rm -f "$STAGED_FILES"' EXIT

git diff --name-only --cached > "$STAGED_FILES"

# BLOCK schlägt PASS.
while IFS= read -r file; do
  [ -f "$file" ] || continue
  grep -qi "immer so\|weil ich\|weint\|strafe\|liebe.*verzicht\|liebe.*hass" "$file" && {
    echo "BLOCK: Quad Errat erkannt in $file"
    exit 1
  }
done < "$STAGED_FILES"

HAS_QED=0
while IFS= read -r file; do
  [ -f "$file" ] || continue
  grep -q "q.e.d." "$file" && HAS_QED=1
done < "$STAGED_FILES"

HAS_FORBIDDEN_OPEN_WORK=0
while IFS= read -r file; do
  [ -f "$file" ] || continue
  case "$file" in
    *.md|*.sh)
      grep -qi "TODO\|FIXME\|hack\|später" "$file" && HAS_FORBIDDEN_OPEN_WORK=1
      ;;
  esac
done < "$STAGED_FILES"

if [ "$HAS_FORBIDDEN_OPEN_WORK" -eq 1 ]; then
  echo "BLOCK: Offene Arbeitsmarker in staged files erkannt."
  exit 1
fi

if [ "$HAS_QED" -eq 1 ]; then
  echo "🕳️ ! ¡ : . ¿"
  echo "PASS: Unterschied + Daten + Verantwortung + q.e.d. geführt."
  echo "HEITER: PASS = 33. Beweiskette geschlossen."
  echo "LOG: post_commit_heiter.sh protokolliert nach Commit."
  exit 0
fi

echo "PASS: PASS = 33. Push freigegeben."
echo "LOG: Kein q.e.d. → post_commit_heiter.sh überspringt."
exit 0
