#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/formalization/QIKVRT_Formalization_v1.0"
SOURCE="$PROJECT/source"
RECORD="https://zenodo.org/records/21482023/files"

mkdir -p "$SOURCE"

download_exact() {
  local name="$1"
  local expected="$2"
  local target="$SOURCE/$name"
  curl --fail --location --silent --show-error \
    "$RECORD/$name?download=1" --output "$target"
  printf '%s  %s\n' "$expected" "$target" | sha256sum --check --status
}

download_exact \
  "Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf" \
  "b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f"
download_exact \
  "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex" \
  "c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf"
download_exact \
  "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.bib" \
  "1994e495af8c3f85e9e85fb77346539855abec16ce8ec6d68a3d3ebe9b5957b8"

(
  cd "$PROJECT"
  sha256sum --check --strict SHA256SUMS
  python3 scripts/package_release.py
  unzip -t release/QIKVRT_Formalization_v1.0_2026-07-22.zip >/dev/null
  printf '%s  %s\n' \
    "d1a7ebc3abbfa0bb107f82ac24d4c740940944ee7f381961e51d7f617c9e46a5" \
    "release/QIKVRT_Formalization_v1.0_2026-07-22.zip" | sha256sum --check --strict
  test "$(stat -c '%s' release/QIKVRT_Formalization_v1.0_2026-07-22.zip)" = "697667"
)

echo "Exact formalization release reconstructed and verified."
