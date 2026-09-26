#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Recovery packaging only. Never accepts or uploads a user recording.
set -euo pipefail
umask 077
[[ $# == 1 ]] || { echo 'Usage: build-recovery-bundle.sh OUTPUT_DIRECTORY' >&2; exit 2; }
TOOL="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(realpath -m -- "$1")"
[[ "$OUT/" != "$TOOL/"* ]] || { echo 'Output must be outside the source tool' >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo 'Output already exists' >&2; exit 2; }
[[ "$(uname -s)/$(uname -m)" == Linux/x86_64 ]] || { echo 'Linux x86_64 required' >&2; exit 1; }
for cmd in node npm ffmpeg ffprobe python3 sha256sum tar espeak-ng; do command -v "$cmd" >/dev/null; done
node -e 'if(Number(process.versions.node.split(".")[0])<24)process.exit(1)'
mkdir -p "$OUT"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
BUNDLE="$WORK/qikvrt-audio-runtime"
mkdir -p "$BUNDLE"/{bin,lib,tool,model,licenses}
(cd "$TOOL"; npm ci; npm test)
cp -a "$TOOL/." "$BUNDLE/tool/"
cp -L "$(command -v node)" "$BUNDLE/bin/node"
node_prefix="$(dirname "$(dirname "$(command -v node)")")"
if [[ -f "$node_prefix/LICENSE" ]]; then cp "$node_prefix/LICENSE" "$BUNDLE/licenses/node-LICENSE"; fi
QIKVRT_AUDIO_MODEL_DIR="$BUNDLE/model" bash "$TOOL/scripts/install-model.sh"
# Keep the host's glibc loader/libc, but carry the addon's other resolved libraries.
python3 - "$BUNDLE" <<'PY'
import pathlib,re,shutil,subprocess,sys
root=pathlib.Path(sys.argv[1])
exclude={'libc.so.6','libm.so.6','libpthread.so.0','libdl.so.2','librt.so.1','libresolv.so.2'}
binaries=[root/'bin/node']+[p for p in (root/'tool/node_modules').rglob('*') if p.is_file() and (p.suffix=='.node' or '.so' in p.name)]
for binary in binaries:
    result=subprocess.run(['ldd',str(binary)],capture_output=True,text=True)
    if 'not found' in result.stdout: raise SystemExit(result.stdout)
    for match in re.finditer(r'=> (/\S+)',result.stdout):
        p=pathlib.Path(match.group(1))
        if p.name not in exclude: shutil.copy2(p,root/'lib'/p.name)
PY
cat > "$BUNDLE/transcribe" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for command in ffmpeg ffprobe; do command -v "$command" >/dev/null || { echo "Missing host prerequisite: $command" >&2; exit 1; }; done
export LD_LIBRARY_PATH="$ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$ROOT/bin:$PATH"
exec "$ROOT/bin/node" "$ROOT/tool/src/transcribe.cjs" --model-dir "$ROOT/model" "$@"
SH
cat > "$BUNDLE/verify" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
sha256sum --strict --quiet -c SHA256SUMS.txt
SH
chmod 0755 "$BUNDLE/transcribe" "$BUNDLE/verify"
# Synthetic fixture, not user audio and not a human-acoustically-verified golden corpus.
printf '%s\n' 'Guten Tag. Dies ist ein Test der Spracherkennung.' > "$BUNDLE/smoke-reference.txt"
espeak-ng -v de -s 130 -f "$BUNDLE/smoke-reference.txt" -w "$BUNDLE/smoke.wav"
export BUNDLE
python3 - <<'PY'
import hashlib,json,os,pathlib,platform,subprocess
r=pathlib.Path(os.environ['BUNDLE'])
def text(*args): return subprocess.check_output(args,text=True).strip()
pkg=json.loads((r/'tool/node_modules/sherpa-onnx-node/package.json').read_text())
manifest={'schema':'qikvrt_audio_recovery_bundle_v1','repository':os.environ.get('GITHUB_REPOSITORY'),
 'source_head':text('git','rev-parse','HEAD'),'source_tree':text('git','rev-parse','HEAD^{tree}'),
 'run_id':os.environ.get('GITHUB_RUN_ID'),'run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
 'node':text(str(r/'bin/node'),'--version'),'sherpa_onnx_package':pkg['version'],
 'model_manifest_sha256':hashlib.sha256((r/'tool/models/whisper-base-int8/MODEL.json').read_bytes()).hexdigest(),
 'build_platform':platform.platform(),'build_libc':list(platform.libc_ver()),
 'host_prerequisites':['Linux x86_64 with compatible glibc','bash','ffmpeg','ffprobe','sha256sum'],
 'ffmpeg_build_host':text('ffmpeg','-version').splitlines()[0],
 'fixture_type':'SYNTHETIC_ESPEAK_NG; not human acoustic verification',
 'includes_user_audio':False,'artifact_retention_days':90,
 'boundary':'Bundle presence is not ASR execution, human verbatim verification, Main integration, or permanent platform capability.'}
(r/'BUNDLE.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
cat > "$BUNDLE/README.txt" <<'TXT'
QIK-VRT audio runtime recovery bundle (Linux x86_64)

1. Verify the outer archive digest against its workflow artifact receipt.
2. Extract, run ./verify, then ./transcribe --input /path/file.m4a --output-dir /path/new-output --language de.
The included Node, installed npm tree and model need no network for inference.
Host prerequisites: compatible glibc, bash, FFmpeg/FFprobe and sha256sum.
BUNDLE.json binds the source HEAD/TREE, resolved runtime and model metadata.
The smoke fixture is synthetic. It does not establish accuracy on human speech.
Workflow artifact retention is finite (90 days). Save the archive before expiry.
No user recording is accepted by the builder, included here, or published.
TXT
(cd "$BUNDLE"; find . -type f ! -name SHA256SUMS.txt -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > SHA256SUMS.txt; ./verify)
tar -czf "$OUT/qikvrt-audio-runtime-linux-x64.tar.gz" -C "$WORK" qikvrt-audio-runtime
(cd "$OUT"; sha256sum qikvrt-audio-runtime-linux-x64.tar.gz > qikvrt-audio-runtime-linux-x64.tar.gz.sha256)
cp "$BUNDLE/BUNDLE.json" "$OUT/BUNDLE.json"
echo 'Recovery archive materialized; inference and cold-restore gates still required.'
