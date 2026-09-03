# QIKVRT AI Terminal for Firefox

This directory is the Firefox reference client for the QIK-VRT EFFECT_ACK HTTP terminal profile and the repository-bound authenticated web delivery adapter.

## What it is

The client is a Manifest V3 WebExtension rather than a forked Firefox binary. That is intentional: it preserves compatibility with normal Firefox releases while adding the QIKVRT terminal as an isolated, reviewable adapter.

When installed, the ordinary QIKVRT content script is injected on configured QIKVRT AI surfaces and presents a source-bound terminal with repository observation, text input, explicit microphone recording, explicit camera preview/snapshot, Prepare/Commit gating and local personalization.

`authenticated_delivery.js` is the external-delivery content adapter for exact repository-bound web obligations. Its first explicit production surfaces are arXiv and Wikipedia/Wikimedia. Additional HTTPS hosts may be admitted only through Firefox optional host permission plus a repository-bound delivery request; the existence of a host permission alone is never external-effect authorization.

## Authenticated delivery sequence

For an eligible arXiv or Wikipedia surface the adapter performs:

1. fresh observation of the exact `Goldkelch/qik-vrt` `main` head and tree;
2. exact-head fetch and validation of the platform delivery request;
3. exact-head validation of `state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json` and its `QIKVRT_FIREFOX_TERMINAL_PROXY_V1` binding;
4. same-origin form observation with secret fields excluded from values and receipts;
5. a non-effecting **Prepare** that freezes the request digest, exact Main binding, page binding and form digest;
6. an explicit **Commit** only if Main, request, page and form are unchanged;
7. immediate post-navigation readback that searches for the authoritative arXiv submission identifier/status or Wikipedia revision identifier;
8. a local non-secret readback receipt whose completion flags remain false unless a separate repository transition consumes authoritative evidence.

A form mutation, Main mutation, delivery-request mutation, platform drift, expired prepare token or missing authoritative readback fails closed.

## Credential and session isolation

The authenticated delivery adapter deliberately does **not** become a password manager.

- Password, file-upload, token, secret, OTP/TOTP and CAPTCHA controls are marked secret and their values are never copied into the QIKVRT snapshot.
- Secret controls have `value_sha256 = null`; no secret value is persisted or emitted in a receipt.
- The adapter does not read or write `document.cookie` and does not write credentials into `localStorage`.
- Authentication cookies and account sessions remain owned by Firefox and the destination platform.
- The prepare token is ephemeral in extension memory. Only the non-secret pending readback binding crosses navigation through page-session storage.
- A browser-native credential manager, SSO flow, MFA prompt or explicit human CAPTCHA action may supply authentication without exposing the secret to QIKVRT.

This means a Digital Twin can drive the mechanical browser sequence while the browser/platform retains its normal authentication boundary.

## Security boundary

- Public GitHub observation is read-only.
- The reference EFFECT_ACK bridge is loopback-only on port 8771.
- Audio/video access requires an explicit browser permission and user gesture.
- Captured media remains local until explicit Prepare.
- Prepare never authorizes or executes the protected effect.
- Commit remains disabled until its exact responsibility binding is revalidated.
- For the local HTTP demonstration, Commit transports token and record hash only through the specified `Effect-Ack-Request` Structured Field.
- The exact prepared text/audio/video payload is frozen and reused for local Commit.
- The loopback reference backend still has `external_effect = NONE`.
- Separately authorized authenticated web effects are executed only by `authenticated_delivery.js` from an exact bound delivery request and require authoritative post-effect readback.
- Neither HTTP success nor a browser click alone constitutes `EFFECT_ACK_DONE`.

## Development loading

Firefox can load the unpacked reference client for development and verification:

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on**.
3. Select this directory's `manifest.json`.
4. Open the configured QIKVRT AI page, arXiv page or Wikipedia page.

A temporary development load is not an AMO signature or distribution approval.

## Reproducible package artifacts

The repository workflow `.github/workflows/qikvrt_effect_ack_http_terminal.yml` verifies the original HTTP terminal profile. The workflow `.github/workflows/qikvrt_authenticated_web_delivery_proxy.yml` additionally validates the authenticated delivery bindings, JavaScript syntax and credential-isolation contract, and creates a deterministic `.xpi`-named ZIP plus SHA-256 sidecar containing `authenticated_delivery.js` and all files referenced by the extension manifest.

Workflow artifacts are verification/build artifacts; normal persistent Firefox installation can still require Mozilla signing or an appropriate managed/development configuration.

## Counterpart

Run the loopback reference bridge from the repository root:

```text
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771
```

The loopback bridge demonstrates the complete local prepare/commit/reobserve shape but deliberately cannot perform repository writes, releases, deployments, publication or actuator effects. Authenticated web delivery is a distinct, request-bound Firefox adapter path and must not be inferred from the loopback backend.
