# Local multimedia in the QIK-VRT Firefox terminal

The local terminal serves `/multimedia` on `http://127.0.0.1:8771` in both the
Cloud-Transputer Firefox and the Linux desktop of the Mega-ST distribution.
Inference runs on that Linux host, not on the emulated MC68000. The public nginx
observer remains read-only; use the Firefox inside the existing operator session.
Do not publish the loopback service or the model port through a reverse proxy.

## Runtime

`runtime/toolchains/multimedia.lock.json` pins llama.cpp b6500 (MIT) and the
SmolVLM2-500M Q8 language/vision files (Apache-2.0) by upstream digest and size.
The model download is about 546 MB; allow additional RAM for the model, vision
encoder, context and Firefox. The small English-focused model is a CPU reference,
not a general-purpose correctness oracle or a measured German-language solution.
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
container's model child. `QIKVRT_MULTIMEDIA_CACHE` and `QIKVRT_MODEL_PORT` select
the local cache and loopback port. Existing changed cache files produce HOLD;
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
