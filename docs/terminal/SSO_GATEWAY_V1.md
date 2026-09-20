# Personal terminal SSO through OIDC

This optional Linux x86_64 gateway places the maintained oauth2-proxy 7.15.4
before an **existing personal noVNC session**. The endpoint browser visits
`https://localhost:8443/vnc.html`; the proxy redirects it to the configured
identity provider, validates the authorization-code response, and permits the
explicitly allowed verified email address to enter the terminal. Applications
registered with that same provider can share its SSO session. Each application
still needs its own registered client and authorization policy.

The Firefox inside the terminal keeps the existing local multimedia and EFFECT_ACK
connections. The gateway never exposes ports 8771, 8789 or 8790. It binds only
127.0.0.1 and does not change the existing public observer or cloud deployment.
This is an optional runnable adapter, not a deployed personal SSO service.

## Reuse and scope

The inspected `browser/firefox/qikvrt-terminal/authenticated_delivery.js` adapts
already authenticated external web sessions for delivery; it does not implement
OIDC login. Existing terminal isolation, noVNC and the pinned-download helper in
`tools/qikvrt_multimedia_runtime.py` are reused. Authentication protocol validation
is delegated to oauth2-proxy instead of a new JWT/password implementation.
The existing Firefox workflow now checks this adapter as a separate job.

| Layer | Implemented connection | Remaining acceptance |
| --- | --- | --- |
| Universal Terminal | TLS/OIDC gateway to one existing loopback noVNC port | Actual configured IdP login and logout |
| Transputer carrier | Host process, explicit install/start, digest-verified cache | Installation on the intended terminal host |
| Metatransistor hardware boundary | Endpoint authenticator through the IdP's WebAuthn/passkey support | Device enrollment and live device verification |
| Speech interface | Existing ASR continues to transcribe submitted audio | Speaker verification, liveness and replay resistance are OPEN |
| Mesh-wide SSO | Reusable OIDC adapter and shared IdP session | Per-service client registration, subject/role mapping and isolation |

No face or voice recognition model is trained by this adapter. No Apple biometric
templates are read. A passkey's authenticator performs local user verification;
it does not disclose a face, fingerprint or biometric template to the application.
User verification may use a device PIN instead of biometrics. Neither this gateway
nor an OIDC login attests which physical person supplied a photo in a conversation.
See [WebAuthn privacy](https://www.w3.org/TR/webauthn-3/#sctn-authenticator-privacy).

## Configure on the terminal host

1. Provision an operator-controlled OIDC provider with HTTPS discovery and a
   confidential authorization-code client. Require PKCE S256; register exactly
   `https://localhost:8443/oauth2/callback`. Set the provider's account policy to
   verify email and require the intended authentication assurance. For Keycloak,
   configure passwordless WebAuthn/passkeys with required user verification and
   enroll the user's own authenticator through the provider's account flow.
2. Keep the existing personal noVNC port reachable only on loopback 6080. Bind
   the gateway to the same host network namespace. For a remote host, use an
   independently authenticated private tunnel with the same localhost port.
   This reference does not create public ingress, DNS or certificates.
3. Outside this repository, create a private operator-owned directory (0700).
   Copy `deploy/universal-terminal/sso.example.json` into it as `settings.json`
   (0600), replace the example issuer/client, and set the five absolute file
   paths. All five files must be regular operator-owned files (0600) in a private
   directory: the IdP client secret, a fresh **32 raw random byte** cookie secret,
   one allowed verified email per line, the trusted localhost TLS certificate
   chain and its private key. Wildcard allowlists, arbitrary upstreams and
   authentication-bypass settings are rejected. The example is not runnable
   until those operator-specific inputs exist.
4. Install, check and start explicitly:

```sh
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B tools/qikvrt_sso_gateway.py install
python3 -B tools/qikvrt_sso_gateway.py check --settings /ABSOLUTE/PRIVATE/settings.json
python3 -B tools/qikvrt_sso_gateway.py serve --settings /ABSOLUTE/PRIVATE/settings.json
```

The existing bootstrap also supports `--install --accept-third-party --profile sso`.
`check` verifies archive/executable bytes, local configuration and TLS key pairing;
it does **not** establish IdP reachability, enrollment or a successful login.
The endpoint browser must trust the TLS certificate for localhost. Do not disable
certificate validation. The IdP session and authenticator ceremony occur in this
endpoint browser **before** entering noVNC: VNC does not automatically forward a
local fingerprint reader or Face ID to the virtual Firefox.

Private authentication files must stay outside Git, model context and caches.
The cache contains only the locked public archive and byte-verified executable.
Changed cache bytes produce HOLD; deliberately quarantine or remove the affected
cache before reinstalling. The installer removes its incomplete staging file,
does not overwrite a changed existing executable, and reports each download and
verification. Stopping the launcher terminates its own proxy child. Failure to
start never falls back to unauthenticated public ingress. QIK-VRT licenses are
unchanged; the upstream proxy retains MIT and its dependency notices.

## Session and authority limits

The gateway requires nonce and issuer validation, S256 PKCE, verified email plus
an exact allowlist, secure HttpOnly host-only cookies and per-request CSRF cookies.
Inherited `OAUTH2_PROXY_*` variables cannot weaken generated settings. It forwards
neither OAuth access tokens nor authorization/user headers as privileges to the
terminal; its request/authentication logging is disabled. OAuth2-proxy implements
the protocol checks; this adapter does not independently prove its correctness.

Cookies expire after 15 minutes, without refresh. `/oauth2/sign_out` clears the
gateway cookie; it does not by itself end the IdP's SSO session or a previously
opened VNC WebSocket. Close the terminal connection and terminate the personal
terminal when immediate revocation is required. Global logout, immediate
revocation of open sessions and back-channel logout remain OPEN. Existing local
host access can still reach the loopback upstream; this gateway is not a security
boundary against the machine's own operator.

Use a separate personal terminal/profile and exact allowlist for each operator.
Adding users to one gateway shares that desktop; it does not create isolated
sessions. Do not use this reference as a multi-tenant public service.
An authenticated session never issues Owner acceptance, native review,
publication, Main promotion or EFFECT_ACK_DONE. Those authorizations retain their
own exact-subject checks. Photos, ASR transcripts and LLM statements never grant
access or those authorities.

## Verification and external handoff

```sh
python3 -B -m unittest tests.test_qikvrt_sso_gateway
QIKVRT_SSO_NATIVE_TEST=1 python3 -B -m unittest tests.test_qikvrt_sso_gateway
```

The native test requires the installed locked proxy. It uses synthetic settings
and placeholders, checks real option parsing with upstream `--config-test`, and
does not contact an identity provider. Tests also reject invalid URLs, bypass
fields, wildcard recipients, secret/symlink exposure, changed cache bytes and
invalid TLS material. The first production blocker is the absent configured IdP
client, trusted TLS material and enrolled endpoint authenticator. Next acceptance:
observe actual code/PKCE login on that configured system, refusal of an unlisted
account, session termination behavior and device verification. Record HEAD/TREE,
provider/client/terminal identities and results without tokens or biometric data.
Hardware biometric and voice recognition acceptance remains OPEN until measured.

Upstream references: [pinned release](https://github.com/oauth2-proxy/oauth2-proxy/releases/tag/v7.15.4),
[proxy configuration](https://oauth2-proxy.github.io/oauth2-proxy/configuration/overview/),
[OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html),
[Keycloak passkeys](https://www.keycloak.org/docs/latest/server_admin/index.html#passkeys).
