# QIKVRT Firefox EFFECT_ACK Terminal Proxy V2

V2 hardens the already merged Firefox reference terminal without widening browser privileges or repository-write authority.

## Normative distinction

`Kausalität != Sequenz` is an execution and evidence invariant.

Message order, wall-clock order, source-text order, HTTP completion and transport acknowledgement do not by themselves establish a causal dependency or authority. If protected work is represented as a causal graph, serial execution is only a deterministic topological projection. Parallel execution may use a different topological projection when all explicit dependency edges, non-commutative effects, leases, exact-version bindings, authority bindings and EFFECT_ACK dependencies are preserved.

## HTTP and HTML

The companion candidate remains the first Internet-Draft revision `draft-lohmann-qikvrt-effect-ack-http-00`. It uses RFC 9651 Structured Fields and RFC 8288 Web Linking. `Effect-Ack-Request` and `Effect-Ack` are Structured Dictionaries. The `effect-ack` relation may be advertised by HTTP `Link` or an ordinary HTML `<link rel="effect-ack">` element.

HTML discovery is advisory. It cannot authorize, execute or acknowledge an effect. No new HTML element or parser rule is required, preserving compatibility with clients that do not implement the extension.

## Modern terminal

The Firefox WebExtension remains the reference client presented on the canonical QIKVRT AI page. Text, explicit microphone recording, explicit camera preview/snapshot and local personalization remain available. Media stays local until explicit Prepare. Prepare never performs the protected effect. Commit requires a separately validated exact-bound DONE preparation and is followed by reobservation.

The five-minute browser watchdog is recreated on extension installation, browser startup and initial background activation. Browser state is observation evidence; it is not repository authority.

## Generic client-rendering proxy

`proxy.js` turns Firefox into a bounded renderer for another client-side representation. A same-origin page adapter can provide a transport-neutral frame by posting:

```javascript
window.postMessage({
  kind: "QIKVRT_TERMINAL_FRAME",
  frame: {
    schema: "qikvrt_terminal_frame_v1",
    observed_at: new Date().toISOString(),
    source: {
      repository: "example/source",
      ref: "refs/heads/main",
      head: "0123456789abcdef0123456789abcdef01234567",
      tree: "89abcdef0123456789abcdef0123456789abcdef"
    },
    terminal_semantics: {rendering_is_authorization: false}
  }
}, location.origin);
```

The proxy accepts only same-window, same-origin messages, requires the canonical frame schema and source binding, validates optional Git head/tree identifiers, bounds the serialized frame to 256 KiB and JSON-clones it before rendering.

Every imported frame is forcibly marked `display_only=true`. The renderer also forces `rendering_is_authorization=false`, `proxy_frame_can_prepare=false` and `proxy_frame_can_commit=false`. Importing a frame disables the visible Commit control. The proxy code does not call the repository backend, Prepare or Commit APIs.

Therefore another UI, agent adapter, CLI bridge or browser-side representation can reuse Firefox as the common display surface without inheriting effect authority.

## Reflexive boundary

A rendered observation may become input evidence for a later autonomous QIKVRT decision only through the separately governed repository/terminal reflection path. Rendering does not create authority. A productive follow-up is a new protected operation with a new exact binding and EFFECT_ACK lifecycle.

## Implementation form

This reference implementation is intentionally a Firefox Manifest V3 WebExtension rather than a maintained fork of Gecko. That is the smallest backward-compatible browser adaptation: unmodified Firefox can load it, ordinary HTTP/HTML remains valid, and the implementation does not require changes to the HTML parser or HTTP method semantics.

A future browser-core implementation may expose the same semantics natively, but it must preserve the same protocol and fail-closed invariants.

## Claim boundary

Passing these tests proves the repository implementation contract for this candidate. It does not establish IETF consensus, IANA allocation, deployment to all QIKVRT users, an independent human review, `PASS`, `FINAL_PASS`, or system-wide `EFFECT_ACK_DONE`.
