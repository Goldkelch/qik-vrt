# QIKVRT AI Terminal for Firefox

This directory is the Firefox reference client for the QIK-VRT EFFECT_ACK HTTP terminal profile.

## What it is

The client is a Manifest V3 WebExtension rather than a forked Firefox binary. That is intentional: it preserves compatibility with normal Firefox releases while adding the QIKVRT terminal as an isolated, reviewable adapter.

When installed, the content script is injected on the configured QIKVRT AI surfaces and presents a source-bound terminal with repository observation, text input, explicit microphone recording, explicit camera preview/snapshot, Prepare/Commit gating and local personalization.

Read-only GitHub observation is explicitly allowlisted for both repository roles: `Goldkelch/qik-vrt` (Authority) and `ingolf-lohmann/qik-vrt` (Mirror). The periodic background frame remains anchored to the Authority, while a terminal opened on either repository observes that page's repository and pull request. The owner-authenticated review-effect helper remains separately Authority-bound and is not generalized by the read-only observer allowlist.

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
