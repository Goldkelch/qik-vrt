# QIKVRT Firefox EFFECT_ACK Terminal Proxy V1

This document describes the Firefox reference client for the repository-side EFFECT_ACK terminal. It is an implementation profile, not a claim of IETF consensus or standards status.

## Boundary

The browser terminal separates four states that must remain visually and mechanically distinct:

1. **Local observation** — repository state, camera preview, microphone recording and personalization can exist locally without being submitted.
2. **Submitted input / Prepare** — explicitly selected text or media is serialized and sent to the configured EFFECT_ACK backend in `prepare` mode. Prepare must not execute the protected effect.
3. **Prepared DONE** — the client has received a compact `Effect-Ack` assertion and the corresponding exact record/token binding required by the deployment profile. This still is not the protected effect.
4. **Commit and reobservation** — only a valid DONE preparation enables Commit. After Commit, the terminal reobserves the authoritative state and treats the post-effect observation as new evidence.

`HTTP success != EFFECT_ACK_DONE != independently observed external effect`.

## Firefox reference extension

The implementation lives under `browser/firefox/qikvrt-terminal/` and uses a Manifest V3 event-page background script. The content script is injected only into the configured QIKVRT Authority AI page and GitHub Pages surface. The background script has the narrow host permissions required for public Authority observation and the loopback reference backend.

The extension provides:

- source-bound `main` head/tree observation;
- explicit user/client-message-triggered repository observation stored in local extension state;
- no browser alarm, startup fetch, timer, periodic repository scan or blind retry;
- latest Self-Heal, reflexive Watchdog and terminal-monitor workflow observations;
- text interaction;
- explicit microphone recording via a user gesture;
- explicit camera preview and still-image snapshot via a user gesture;
- local-only media state until Prepare;
- Prepare / DONE-gated Commit;
- post-commit repository reobservation;
- local personalization for accent, font scale, density and position.

## Proxy model

Firefox is the reference renderer and proxy, not a privileged truth source. Other clients and backends map their observations to `qikvrt_terminal_frame_v1` while retaining provenance.

Supported adapter classes are:

- public GitHub repository observation;
- HTTP backend;
- loopback QIKVRT bridge;
- MCP/agent observation;
- another client snapshot with an explicit source identifier.

A proxy may display NACK, CONTINUE, ISOLATE or BLOCK. It may never translate those states into ordinary release. Rendering a DONE record does not itself execute an effect.

## Repository-side reference bridge

`src/qikvrt_effect_ack_http_terminal.py` is loopback-only and deliberately has `external_effect = NONE`. Its V1 profile demonstrates capability discovery, bounded Prepare, a short-lived single-use exact-bound token, Commit, replay refusal and post-effect observation of a local terminal event.

It is not a replacement for `src/qikvrt_effect_ack.py`, and it must not be represented as proof of complete wire or deployment conformance. A write-capable repository, publication, deployment or actuator backend needs a separately authorized adapter and must preserve the same EFFECT_ACK gate.

## HTTP / HTML integration

The companion Internet-Draft candidate is `external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml`. It defines:

- `Effect-Ack-Request` as a Structured Dictionary;
- `Effect-Ack` as a Structured Dictionary;
- `effect-ack` as a Web Linking relation;
- two-phase Prepare / Commit;
- the same relation in an ordinary HTML `link` element without a new HTML element or parser feature.

Legacy HTTP/HTML remains unchanged. A fail-closed client that requires EFFECT_ACK protection must discover support before sending the protected operation.

## Local two-peer terminal profile V2

`policy/QIKVRT_HTTP_TERMINAL_PEER_V2.json`, `docs/terminal/QIKVRT_HTTP_TERMINAL_PEER_V2.schema.json` and the V2 branch of the reference daemon add a local two-daemon profile without changing V1. It is a reference for sessionless HTTP requests with explicit durable receipts; it does **not** claim that the complete system has no retained state. Replay prevention necessarily retains the minimal node-local prepare/commit/idempotency lifecycle.

Each daemon receives a separate private state directory, stable logical node ID and stable logical endpoint ID. The local test profile uses only loopback HTTP:

```text
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771 \
  --state-dir /private/qikvrt-terminal/node-a --node-id peer-a --endpoint-id terminal-a
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8772 \
  --state-dir /private/qikvrt-terminal/node-b --node-id peer-b --endpoint-id terminal-b
```

V2 requires the same `Idempotency-Key` in the HTTP header and JSON envelope, and binds source node, target node, target endpoint, `POST /terminal/commit`, canonical terminal-input SHA-256, policy SHA-256, responsibility owner, record hash and expiry into the single-use token. The node-local append-only ledger records `RECORD`, `PREPARED` and `COMMITTED` entries so an exact retry after restart returns the original local receipt; reuse of an idempotency key with different canonical input is blocked. One daemon holds an exclusive private state-directory lock; a redirected state path, duplicate binding/framing header or unterminated ledger record is `HOLD`.

The V2 envelope uses `qikvrt_terminal_input_v2`, not the permissive V1 input object. Its terminal input is a closed domain: bounded valid UTF-8 strings, `null` media, or a `qikvrt_terminal_media_descriptor_v1` with exact kind, lowercase media type, IEEE-754-safe integer byte length, SHA-256 and canonical padded Base64 that decode to the same bytes. Floating point, arrays, untyped nested objects, duplicate JSON member names, non-canonical Base64 and invalid UTF-8 are rejected before canonical JSON or SHA-256. Canonical JSON is an explicit UTF-8 algorithm: object keys sort by Unicode scalar value, separators are `,`/`:`, quote/backslash and the JSON control escapes have one fixed spelling, and no host JSON-library float rendering participates. V1 Prepare/Commit remains unchanged for the existing Firefox reference client.

The Firefox reference extension also contains a source-level V2 local-peer client.
It remains disabled unless a local operator explicitly stores a complete peer
configuration. That configuration has an exact source node, a different target
node, target endpoint and responsibility owner, and its backend selector is
limited to its own `http://127.0.0.1:8771` daemon. A page cannot supply another
host, port or endpoint through the terminal input. Each terminal endpoint
configures and explicitly invokes its own daemon.

The separate **V2 Peer Prepare** button serializes only the closed
`qikvrt_terminal_input_v2` domain with a browser implementation of
`QIKVRT_CLOSED_JSON_V2`: Unicode-scalar key order, fixed JSON string escapes,
compact separators, safe integers only and no float/array/untyped input value.
It derives a deterministic request ID from the frozen node/policy/input binding,
uses that same ID in the envelope and `Idempotency-Key`, verifies the target
daemon capability, and makes one local HTTP request. **V2 Peer Commit** remains
disabled until the exact full record is checked; the click causes one explicit
record reobservation and one exact commit request. There is no alarm, timer,
startup request, storage watcher, periodic scan or blind retry.

This is source-level client coverage, not browser-runtime interoperability
evidence. TLS/mTLS peer authentication, remote/public deployment, Firefox
runtime operation and any external effect are `OPEN`; a local V2 ledger receipt
is not converted into `PASS`, `FINAL_PASS`, repository authority or
`EFFECT_ACK_DONE` beyond that receipt's local protocol scope.

## Security and privacy

- Device acquisition requires explicit browser permission and a user gesture.
- Media remains local until explicit Prepare.
- Personalization remains local by default.
- The reference backend is loopback-only.
- V2 keeps only an explicit private node-local receipt ledger; HTTP request sessions are not retained.
- Commit tokens are single-use and time-bounded.
- V2 transport is not authenticated by TLS/mTLS in this local reference; those deployment controls remain open.
- Old exact-head evidence is never transferred to a new head.
- A browser permission is not effect authorization.
- No PASS, FINAL_PASS or EFFECT_ACK_DONE claim follows merely from installing the extension or passing repository tests.
