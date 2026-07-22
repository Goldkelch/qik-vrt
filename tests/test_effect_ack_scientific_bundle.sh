#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# Reproducible, local-only checks for the EFFECT_ACK scientific bundle.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BUNDLE="$ROOT/docs/publications/2026-07-22-effect-ack-universal-effect-control"
PROOF="$BUNDLE/effect_ack_universality_proof.py"
REPORT="$BUNDLE/proof-report.json"
DRAFT_TXT="$BUNDLE/inputs/draft-lohmann-qikvrt-effect-ack-01.txt"
DRAFT_XML="$BUNDLE/inputs/draft-lohmann-qikvrt-effect-ack-01.xml"
RUNTIME="$ROOT/src/qikvrt_effect_ack.py"
PYTHON=${PYTHON:-python3}

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/qikvrt-scientific-bundle.XXXXXX")
cleanup() {
    case "$SCRATCH" in
        */qikvrt-scientific-bundle.*) rm -rf -- "$SCRATCH" ;;
        *) printf '%s\n' "refusing unsafe test cleanup: $SCRATCH" >&2 ;;
    esac
}
trap cleanup EXIT HUP INT TERM

fail() {
    printf '%s\n' "FAIL: $*" >&2
    exit 1
}

"$PYTHON" -B "$PROOF" \
    --draft-txt "$DRAFT_TXT" \
    --draft-xml "$DRAFT_XML" \
    --runtime "$RUNTIME" \
    --output "$SCRATCH/proof-report.json" \
    > "$SCRATCH/proof-report.stdout.json"

cmp "$SCRATCH/proof-report.json" "$REPORT" >/dev/null || \
    fail "regenerated proof report differs from the committed report"
cmp "$SCRATCH/proof-report.stdout.json" "$REPORT" >/dev/null || \
    fail "proof stdout differs from the committed report"

set +e
"$PYTHON" -O "$PROOF" \
    --draft-txt "$DRAFT_TXT" \
    --draft-xml "$DRAFT_XML" \
    --runtime "$RUNTIME" \
    > "$SCRATCH/optimized.stdout" \
    2> "$SCRATCH/optimized.stderr"
optimized_rc=$?
set -e
[ "$optimized_rc" -ne 0 ] || fail "optimized Python mode unexpectedly succeeded"
grep -F 'optimized Python mode (-O) is not permitted for this proof run' \
    "$SCRATCH/optimized.stderr" >/dev/null || \
    fail "optimized-mode rejection did not contain the expected diagnostic"

"$PYTHON" -B - "$BUNDLE" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
import sys


bundle = Path(sys.argv[1]).resolve(strict=True)
manifest = bundle / "SHA256SUMS"
line_pattern = re.compile(r"([0-9a-f]{64})  ([^\r\n]+)\Z")
recorded: dict[str, str] = {}

for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
    match = line_pattern.fullmatch(line)
    if match is None:
        raise SystemExit(f"SHA256SUMS:{line_number}: malformed entry")
    expected, relative = match.groups()
    relative_path = PurePosixPath(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts or "\\" in relative:
        raise SystemExit(f"SHA256SUMS:{line_number}: unsafe path {relative!r}")
    if relative in recorded:
        raise SystemExit(f"SHA256SUMS:{line_number}: duplicate path {relative!r}")
    path = bundle.joinpath(*relative_path.parts)
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"SHA256SUMS:{line_number}: missing regular file {relative!r}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"SHA256SUMS:{line_number}: digest mismatch for {relative!r}: "
            f"expected {expected}, got {actual}"
        )
    recorded[relative] = expected

actual_files = {
    path.relative_to(bundle).as_posix()
    for path in bundle.rglob("*")
    if path.is_file() and not path.is_symlink() and path != manifest
}
if set(recorded) != actual_files:
    missing = sorted(actual_files - set(recorded))
    stale = sorted(set(recorded) - actual_files)
    raise SystemExit(
        f"SHA256SUMS coverage mismatch: missing={missing}, stale={stale}"
    )
PY

printf '%s\n' "PASS: EFFECT_ACK scientific proof, optimized-mode guard and bundle SHA-256 index"
