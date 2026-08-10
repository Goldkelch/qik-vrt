# Product-Owner Voice Single Sign-On

`PRODUCT_OWNER_VOICE_SSO_V1` makes a successful local biometric voice session
the Product Owner's single interaction key for QIK-VRT commands. It is not an
ASR inference: a local verifier must bind a fresh spoken challenge, speaker
match and presentation liveness to a short-lived signed session.

The repository verifies the local verifier's public signature so that the
voice result can be checked and revoked across Authority and Mirror. This is a
transport-verifiability mechanism, not a second user interaction: the Product
Owner uses voice to open and operate the SSO session.

## Privacy boundary

Raw recordings, voice templates, embeddings and mutable authentication state
must remain in a Product-Owner-controlled local encrypted verifier. They must
not enter Git, Actions artifacts, logs, ordinary caches or pull-request text.
The repository stores only opaque enrollment identifiers, hashes, verifier
versions, verdicts and signed receipts.

## Command boundary

Every spoken command becomes a canonical command envelope, signed by the local
verifier and bound to repository, exact ref, exact head, exact tree, embedded
canonical parameters and their digest, session digest, nonce and expiry. Ref,
head or tree drift invalidates it. Unknown operations are conservatively
classified as external effects; the signed caller cannot downgrade that class.
The `ALL_PRODUCT_OWNER_COMMANDS` scope grants the desired SSO reach; it does
not silently weaken repository gates.

For an external effect the same voice SSO channel may create the Product Owner
authorization, but the envelope must also bind the existing exact artifact and
single-use authorization requirements. The verifier reports those gates as
pending; the existing effect executor must independently resolve and consume
the authorization reference and verify the actual artifact bytes.

This is a Product-Owner-specific authentication channel. It does not change
the separate collective-adaptive-cognition rule that observer identifiers do
not establish human identity, independence or consensus.

## Local enrollment and verification

Before production use, the Product Owner enrolls only into a local verifier,
protects its signing key, and registers its public key through a reviewed
policy change. The initial policy therefore has no active issuer and fails
closed until this registration is present.

The repository-side verifier derives its canonical policy, GitHub repository,
ref, head and tree from the checked worktree. Session, command and nonce-ledger
files must be outside that worktree in an owner-only directory (for example
mode `0700`, with input files mode `0600`). A verifier invocation is:

```sh
node tools/offline-audio-transcription/bin/verify-voice-sso \
  --session /private/session.json \
  --command /private/command.json \
  --nonce-ledger /private/consumed-nonces.json
```

The JSON inputs are intentionally private. A successful command verification
only returns authenticated Product Owner identity and exact intent with the
remaining gate class; an executor still performs its ordinary repository and
effect checks and must execute the embedded parameters rather than a separately
rendered command.

The local verifier, rather than GitHub Actions, retains consumed nonces and
short-lived session state. The CLI holds an exclusive lock and persists the
owner-only private ledger durably before returning success. A stateless
workflow cannot use this authorization path. The current CLI is verifier-only:
its stdout is not an execution credential. A later executor integration must
verify, consume and dispatch atomically inside one protected local broker, or
consume a protected one-time receipt bound to the same command and target.
