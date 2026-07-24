"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const toolRoot = path.resolve(__dirname, "..");
const installer = path.join(toolRoot, "scripts", "install-model.sh");

function writeExecutable(file, value) {
  fs.writeFileSync(file, value, { encoding: "utf8", mode: 0o755 });
  fs.chmodSync(file, 0o755);
}

test("model checksums execute inside both attested directories", () => {
  const value = fs.readFileSync(installer, "utf8");
  const extractedCheck = value.indexOf('cd "$extracted"');
  const persistentInstall = value.indexOf('install -m 0644 "$extracted/base-decoder.int8.onnx"');
  const destinationCheck = value.indexOf('cd "$MODEL_DIR"');

  assert.ok(extractedCheck >= 0, "missing extracted-directory checksum gate");
  assert.ok(persistentInstall > extractedCheck, "persistent installation must follow extracted-byte verification");
  assert.ok(destinationCheck > persistentInstall, "destination verification must follow installation");
  assert.doesNotMatch(value, /\)\s*\|\s*sha256sum\s+-c/u, "sha256sum must not escape the cd subshell through a pipeline");
});

test(
  "production installer preserves checksum cwd scope under an executable fixture",
  { skip: process.platform === "win32" },
  () => {
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "qikvrt-install-model-"));
    try {
      const fixtureParent = path.join(temporary, "fixture");
      const fixtureModel = path.join(fixtureParent, "sherpa-onnx-whisper-base");
      const archive = path.join(temporary, "model.tar.bz2");
      const modelDir = path.join(temporary, "installed-model");
      const stubBin = path.join(temporary, "bin");
      fs.mkdirSync(fixtureModel, { recursive: true });
      fs.mkdirSync(stubBin, { recursive: true });

      const expected = new Map([
        ["base-decoder.int8.onnx", "decoder-fixture\n"],
        ["base-encoder.int8.onnx", "encoder-fixture\n"],
        ["base-tokens.txt", "tokens-fixture\n"],
      ]);
      for (const [name, content] of expected) {
        fs.writeFileSync(path.join(fixtureModel, name), content, "utf8");
      }

      const tar = spawnSync(
        "tar",
        ["-cjf", archive, "-C", fixtureParent, "sherpa-onnx-whisper-base"],
        { encoding: "utf8" },
      );
      assert.equal(tar.status, 0, `failed to create fixture archive: ${tar.stderr}`);

      writeExecutable(
        path.join(stubBin, "curl"),
        `#!/usr/bin/env bash
set -euo pipefail
output=""
while (( $# )); do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    --output=*) output="\${1#*=}"; shift ;;
    *) shift ;;
  esac
done
: "\${output:?missing --output}"
cp "$QIKVRT_TEST_ARCHIVE" "$output"
`,
      );
      writeExecutable(
        path.join(stubBin, "sha256sum"),
        `#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "-c" ]]; then
  source="\${2:--}"
  [[ "$source" == "-" ]] && source=/dev/stdin
  failed=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    file="\${line#*  }"
    if [[ -f "$file" ]]; then
      printf '%s: OK\\n' "$file"
    else
      printf '%s: FAILED open or read\\n' "$file" >&2
      failed=1
    fi
  done < "$source"
  exit "$failed"
fi
exec /usr/bin/sha256sum "$@"
`,
      );

      const run = spawnSync("bash", [installer], {
        cwd: toolRoot,
        encoding: "utf8",
        env: {
          ...process.env,
          PATH: `${stubBin}:${process.env.PATH}`,
          QIKVRT_AUDIO_MODEL_DIR: modelDir,
          QIKVRT_TEST_ARCHIVE: archive,
        },
      });
      assert.equal(run.status, 0, `installer failed\nstdout:\n${run.stdout}\nstderr:\n${run.stderr}`);

      for (const [name, content] of expected) {
        assert.equal(fs.readFileSync(path.join(modelDir, name), "utf8"), content);
      }
    } finally {
      fs.rmSync(temporary, { recursive: true, force: true });
    }
  },
);
