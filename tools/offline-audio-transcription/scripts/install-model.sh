#!/usr/bin/env bash
set -euo pipefail
umask 077

readonly MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.tar.bz2"
readonly ARCHIVE_SHA256="911b2083efd7c0dca2ac3b358b75222660dc09fb716d64fbfc417ba6c99ff3de"
MODEL_DIR="${QIKVRT_AUDIO_MODEL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/transcribe-audio-offline/model}"

if [[ "${1:-}" == "--model-dir" ]]; then
  MODEL_DIR="${2:?missing value for --model-dir}"
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--model-dir DIR]" >&2
  exit 2
fi

for command in curl tar sha256sum install mktemp; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
archive="$temporary_dir/sherpa-onnx-whisper-base.tar.bz2"
extracted="$temporary_dir/extracted"
checksums="$temporary_dir/model.sha256"
mkdir -p "$extracted"
install -d -m 0700 "$MODEL_DIR"

cat > "$checksums" <<'EOF'
9759d217388a01b3a4c7c15533201067b48ae819c4daafc8624e64b9409dc02d  base-decoder.int8.onnx
0b8fb1304b6109976038efff5ace81720e00386f3ff6b54ee8c75291ca0a1e11  base-encoder.int8.onnx
b34b360dbb493e781e479794586d661700670d65564001f23024971d1f2fa126  base-tokens.txt
EOF

echo "Downloading model archive only; no audio is transmitted." >&2
curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 --max-time 600 \
  --output "$archive" "$MODEL_URL"
printf '%s  %s\n' "$ARCHIVE_SHA256" "$archive" | sha256sum -c -

tar --no-same-owner -xjf "$archive" -C "$extracted" --strip-components=1 \
  sherpa-onnx-whisper-base/base-decoder.int8.onnx \
  sherpa-onnx-whisper-base/base-encoder.int8.onnx \
  sherpa-onnx-whisper-base/base-tokens.txt

# Verify the extracted bytes before any persistent installation. The checksum
# file contains relative names, so sha256sum must execute inside the directory
# whose contents are being attested.
(
  cd "$extracted"
  sha256sum -c "$checksums"
)

install -m 0644 "$extracted/base-decoder.int8.onnx" "$MODEL_DIR/base-decoder.int8.onnx"
install -m 0644 "$extracted/base-encoder.int8.onnx" "$MODEL_DIR/base-encoder.int8.onnx"
install -m 0644 "$extracted/base-tokens.txt" "$MODEL_DIR/base-tokens.txt"

# Re-attest the persisted destination. Keeping both cd and sha256sum in the
# same subshell prevents pipeline process scope from silently changing cwd.
(
  cd "$MODEL_DIR"
  sha256sum -c "$checksums"
)

echo "Model installed at: $MODEL_DIR" >&2
