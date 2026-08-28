# QIKVRT AI Terminal for Firefox

This directory is the Firefox reference client for the QIK-VRT EFFECT_ACK HTTP terminal profile.

## What it is

The client is a Manifest V3 WebExtension rather than a forked Firefox binary. That is intentional: it preserves compatibility with normal Firefox releases while adding the QIKVRT terminal as an isolated, reviewable adapter.

When installed, the content script is injected on the configured QIKVRT AI surfaces and presents a source-bound terminal with repository observation, text input, explicit microphone recording, explicit camera preview/snapshot, Prepare/Commit gating and local personalization.

Repository observation is edge-triggered by an explicit UI/client message. The extension does not create an alarm, timer, startup fetch, periodic scan or blind retry.

## Security boundary

- Public GitHub observation is read-only.
- The reference EFFECT_ACK bridge is loopback-only on port 8771.
- Audio/video access requires an explicit browser permission and user gesture.
- Captured media remains local until explicit Prepare.
- Prepare never authorizes or executes the protected effect.
- Commit remains disabled until the exact full responsibility record has been re-fetched and validated as `EFFECT_ACK_DONE`.
- Commit transports token and record hash only through the specified `Effect-Ack-Request` Structured Field.
- The exact prepared text/audio/video payload is frozen and reused for Commit.
- The reference backend has `external_effect = NONE`.

## Development loading

Firefox can load the unpacked reference client for development and verification:

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on**.
3. Select this directory's `manifest.json`.
4. Open the configured QIKVRT AI page.

A temporary development load is not an AMO signature or distribution approval.

## Reproducible package artifact

The repository workflow `.github/workflows/qikvrt_effect_ack_http_terminal.yml` creates a deterministic file-set ZIP with the `.xpi` suffix and a SHA-256 sidecar after all syntax, RFCXML and E2E checks have passed. The workflow artifact is a verification/build artifact; normal persistent Firefox installation can still require Mozilla signing or an appropriate managed/development configuration.

## Counterpart

Run the loopback reference bridge from the repository root:

```text
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771
```

The bridge demonstrates the complete local prepare/commit/reobserve shape but deliberately cannot perform repository writes, releases, deployments, publication or actuator effects.

For the durable local two-peer V2 reference, start each daemon with a distinct private ledger directory and stable logical node/endpoint IDs. This remains loopback HTTP only; TLS/mTLS, remote deployment and external effects are open:

```text
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771 \
  --state-dir /private/qikvrt-terminal/node-a --node-id peer-a --endpoint-id terminal-a
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8772 \
  --state-dir /private/qikvrt-terminal/node-b --node-id peer-b --endpoint-id terminal-b
```

## Explicit V2 Firefox peer request

The extension contains a source-level V2 local-peer client. It is disabled by
default. In the extension options, an operator must explicitly enable it and
enter a source node, a different target node, target endpoint and responsibility
owner. Its target selector is deliberately limited to its own
`127.0.0.1:8771` daemon; it never accepts a remote URL, a second port or a
hostname supplied by a page. Each terminal endpoint configures its own local
daemon before explicitly sending to it.

The terminal renders separate **V2 Peer Prepare** and **V2 Peer Commit**
controls. A click on Prepare derives the closed
`qikvrt_terminal_input_v2` descriptor, canonicalizes it with Unicode-scalar key
ordering and fixed escapes, hashes it with WebCrypto SHA-256, derives an exact
Idempotency-Key, discovers the named local daemon and submits one V2 Prepare.
Commit stays disabled until the returned record has been fetched and checked
against the frozen configuration, input hash, policy hash, node binding and
request fingerprint. A Commit click re-fetches that record before transmitting
the one exact V2 Commit envelope.

No alarm, timer, startup request, storage listener, polling or blind retry is
used. The local durable-ledger receipt is shown as `PEER_LOCAL_COMMITTED`; it is
not promoted to a repository write, TLS-authenticated peer identity, remote
deployment, browser-runtime interoperability proof or external effect.
