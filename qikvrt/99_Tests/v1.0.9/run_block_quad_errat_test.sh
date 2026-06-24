#!/usr/bin/env bash
set -euo pipefail

echo "=== BLOCK-TEST Quad Errat v1.0.15 ==="
TESTFILE="qikvrt/99_Tests/v1.0.9/TEST_BLOCK_QUAD_ERRAT.md"
mkdir -p "$(dirname "$TESTFILE")"

cat > "$TESTFILE" <<'EOF'
# Test BLOCK Quad Errat

Status: TEST = TRUE
Erwartung: BLOCK

Verbotene Muster:
- Das war immer so.
- Weil ich es sage.
- Ohne Strafe keine Gerechtigkeit.

q.e.d. negativ:
Nicht jede q.e.d.-Markierung darf PASS erzeugen,
wenn zugleich Quad Errat erkannt wird.
EOF

git add "$TESTFILE"

if git commit -m "TEST: BLOCK Quad Errat muss scheitern"; then
  echo "FAIL: BLOCK-Test wurde faelschlich committed."
  git reset --soft HEAD~1 >/dev/null 2>&1 || true
  git reset -- "$TESTFILE" >/dev/null 2>&1 || true
  rm -f "$TESTFILE"
  exit 1
else
  echo "PASS: BLOCK-Test wurde korrekt verhindert."
fi

git reset -- "$TESTFILE" >/dev/null 2>&1 || true
rm -f "$TESTFILE"

echo "Cleanup: Testdatei entfernt. Index sauber."
echo "Ergebnis: GATE_JURISTEREI blockiert Quad Errat trotz q.e.d."
