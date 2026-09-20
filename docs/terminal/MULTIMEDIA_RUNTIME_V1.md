# Local multimedia in the QIK-VRT Firefox terminal

The local terminal serves `/multimedia` on `http://127.0.0.1:8771` in both the
Cloud-Transputer Firefox and the Linux desktop of the Mega-ST distribution.
Inference runs on that Linux host, not on the emulated MC68000. The public nginx
observer remains read-only; use the Firefox inside the existing operator session.
Do not publish the loopback service or the model port through a reverse proxy.

## Runtime

`runtime/toolchains/multimedia.lock.json` pins llama.cpp b6500 (MIT), the official
Qwen2.5-1.5B-Instruct Q4_K_M text model and the SmolVLM2-500M Q8 language/vision
files (both Apache-2.0) by upstream revision, digest and size. The combined model
download is about 1.66 GB; allow additional RAM for both models, context and Firefox.
Qwen handles text questions and repository synthesis. SmolVLM handles images; for
questions with repository context or history, its description is marked unverified
and then passed to Qwen alongside the excerpts. Each call gets its own model,
input and output digest in the receipt. Neither model is a correctness oracle.
The official text-model identity is documented by its
[upstream weight commit](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/commit/dd26da440ef0330c47919d1ecae0966d24022222).
This locked release was selected for the supported model and Debian-compatible
CPU binary; it is not represented as the latest llama.cpp release.

Install and run on Linux x86_64 with Python 3.11+, libcurl, libstdc++ and glibc:

```sh
python3 -B tools/qikvrt_multimedia_runtime.py install
python3 -B tools/qikvrt_multimedia_runtime.py serve
```

In a second terminal, run the existing terminal or the TEMDD ledger:

```sh
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771
```

`tools/bootstrap-runtime.sh --install --accept-third-party --profile multimedia`
uses the same installer. Installation is explicit. Opening a page cannot install
a model. The default container build and ISO build include the verified weights;
startup re-verifies cached inputs. `QIKVRT_ENABLE_MULTIMEDIA=0` disables the
container's model service. `QIKVRT_MULTIMEDIA_CACHE`, `QIKVRT_MODEL_PORT` (8789)
and `QIKVRT_TEXT_MODEL_PORT` (8790) select the local cache and distinct loopback
ports. One supervisor starts both providers and stops both on shutdown or when
either exits. Readiness requires both expected aliases and both health checks.
A missing text model never silently falls back to the vision model.
Existing changed cache files produce HOLD;
remove or quarantine them deliberately before a fresh installation. Interrupted
downloads remove their own staging file and preserve valid existing material.

## Media and authority boundaries

Files are previewed locally first. The browser encodes selected images/frames as
JPEG at at most 768 pixels per side. The backend accepts at most four PNG/JPEG
images of at most 1 MiB and 2048 pixels per side, a 12,000-character prompt and a
256-token response request. Video is represented by manually selected frames and
their selected times, not a claim that the whole movie or its audio was analyzed.
Playback depends on Firefox's installed codecs; HEVC/MOV is not guaranteed.

The original file stays in the browser during image/frame inference. The receipt
binds the actual resized image bytes, not the original file. Its selected time and
label are supplied by the user interface; they are not authenticated camera
metadata. The provider-reported model alias is not remote hardware attestation.
The launcher verifies the weights and runner locally before starting the provider.

Audio uses the existing repository Whisper-base-int8 / sherpa-onnx-node 1.13.4
implementation, Node 24, FFmpeg and FFprobe. The container and ISO build include
these. Local ISO builders first run `npm ci --prefix tools/offline-audio-transcription
--omit=dev` with Node 24 available and preserve `QIKVRT_NODE_BIN` when using sudo.
For separately launched development terminals the page states when ASR is absent.
Only explicitly submitted audio up to 12 MiB / 120 seconds is decoded. The decoder
reads supplied bytes through a pipe and cannot open nested file/network protocols.
A private temporary PCM WAV is passed to ASR and removed with its results after
the response. Exact digital silence produces no transcript. This is not a general
voice-activity detector: non-silent noise can still produce hallucinated words.
The user checks and explicitly includes a transcript in a subsequent question.
The model itself has no audio-input capability. Browser speech synthesis requires
an installed voice and is not a guaranteed feature of every Firefox installation.

Model responses are plain text. No shell, tool calls, event append, release,
publication or remote effect is exposed through this interface. Requests require
the local Host, matching Origin and a random page token; there is one inference
slot, bounded input/output and a timeout. No prompt, media or reply is written to
the event ledger. A response receipt remains `UNVERIFIED_PROPOSAL` with
`effect_ack_done=false`. It does not inherit any earlier formal proof.

## Reproduction

```sh
python3 -B -m unittest tests.test_qikvrt_multimedia tests.test_qikvrt_effect_ack_http_terminal
node --check docs/terminal/multimedia/app.js
python3 -B tests/run_multimedia_model_smoke.py --output /tmp/multimedia-smoke.json
```

Add `--audio` when the repository audio dependencies and the model selected by
`QIKVRT_AUDIO_MODEL_DIR` are installed. The silence fixture checks decoder behavior,
not recognition accuracy. The live smoke test launches the pinned model and the
actual HTTP backend in the same process/network environment and terminates its
own children. It records source-byte identities and actual responses; it is not
a whole-system acceptance test.

For the optional browser check, run `npm ci` in
`runtime/toolchains/multimedia-browser`, then its `node_modules/.bin/agent-browser
install`. The package lock fixes the Apache-2.0 CLI and its transitive dependencies;
the downloaded Chromium version is reported separately by the browser check.
Run `python3 -B tests/run_multimedia_browser_smoke.py --output-dir /tmp/media-browser`
only in an isolated test session, never with an authenticated profile.
An environment that prohibits Unix sockets may block the CLI/ledger; retain that
as a runtime limitation rather than changing the protected boundary.

Full Firefox/container and network-boot ISO acceptance, independent native review,
protected Main promotion and external effect readback remain separate gates.

## Repository conversation and direct capture

The page now selects repository context by default. The existing integrity
manifest bounds the local corpus: README/STATUS, the two cognition policies, and
UTF-8 Markdown/text/JSON/Lean/Python/VHDL below docs, formalization, src and hardware.
Only immutable regular files of at most 128 KiB are eligible; at most 32 MiB are
scanned per question. Retrieval ranks literal word overlap deterministically and
sends at most four 1,200-character excerpts. It is a lexical retrieval baseline,
not semantic search over all Mesh nodes. Untracked files, private runtime state,
credentials and arbitrary network URLs are not source inputs. Missing packaged
files and limited coverage are reported explicitly; no match does not establish
that the repository lacks evidence.

The adapter checks each read file against its manifest digest, and rechecks the
selected source bytes and manifest after inference. A mismatch returns HOLD,
without a successful answer receipt. Sources carry file and excerpt hashes,
paths and starting lines; the receipt binds the provider request and local
manifest. A separately observed Git HEAD/TREE is not a claim that all working
files equal that commit. Exported ISO installations can use manifest-bound
sources without Git. The ISO recipe reuses `export-context` in the existing
model runtime to carry these public sources and the integrity reader.

The latest three question/answer pairs, shortened to at most 4,000 characters,
are sent as untrusted conversation data. The page retains at most twenty full
turns in memory and can download their receipts. Reloading or starting a new
conversation discards that in-memory state. Context does not certify citations
or factual correctness, execute Lean/Lake, run arbitrary repository tools,
contact another Mesh node, or turn an answer into accepted evidence. Context
and image tokens can exceed the provider's 8,192-token capacity; the provider
then returns an explicit error. Reduce the prompt, images or conversation.

Mikrofon starten asks the browser for microphone access and records at most
115 seconds / 12 MiB. Aufnahme beenden stops the tracks and prepares an audio
file; the existing explicit transcription/review path follows. Kamera starten
opens a preview without audio; only deliberately captured frames enter a model
request. Stop buttons and page exit release tracks. Browser/device permissions,
codecs and available hardware remain prerequisites. These are discrete capture
interactions, not continuous bidirectional audio/video streaming. Speech output
selects only a voice marked local by the browser; unavailable local voices are
reported. No license or external-effect authority changes are introduced.

The current question alone selects source excerpts, so unrelated earlier turns
do not displace the new topic. Identifier components (including JSON/Lean names
with underscores) are searchable. The adapter reports missing or unknown [R…]
references separately. Existing reference IDs never imply that the source
entails the answer. The UI displays that distinction beside the model text.
The first actual grounded smoke at 633a28b exposed repetitive, inaccurate
explanations and absent citations from the compact model. It established the
transport path, not adequate scientific answer quality. This motivated the
separate text model. The live smoke checks three finite proof-versus-physical-
evidence questions (English, German and an image) and existing source references.
Those checks do not establish general scientific answer quality, which remains
OPEN and needs separate task evaluation; the original excerpts stay visible.

The model-bundled ISO produced a 2115.20 MiB compressed root filesystem on the
633a28b build. The receiver's former 2 GiB ceiling rejected it after ISO boot.
The added text weights occupy 1065.56 MiB before filesystem compression. Large
files now use the shared transfer-parts implementation: the standard is still
2048 MiB per part, with a configurable sender size and receiver maximum. Per-part
hashes, offsets, lengths and the complete file hash are checked before the
reassembled image becomes usable. Already verified parts survive an interruption.
This changes transport granularity, not the RAM needed to boot the assembled image.
See [distribution transfer profiles](../../distribution/qikvrt-megast/README.md#transfer-parts-and-line-profiles).
