<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Security policy

## Supported version

Security review currently targets the active runtime on `main` and the latest
public release. Historical delivery artifacts are retained for provenance but
are not supported runtime versions unless [STATUS.md](STATUS.md) says
otherwise.

## Report a vulnerability

Do not publish credentials, exploit payloads, personal data, or a working
attack in a public issue.

1. Prefer GitHub's private **Report a vulnerability** flow in the repository's
   Security tab when it is available.
2. If no private flow is visible, open a minimal public issue titled
   `Private security contact requested`. Include only the affected component
   and a safe contact method; omit exploit details.
3. Preserve the exact version, commit, input, expected result, observed result,
   and any relevant hashes so the report can be reproduced.

Receipt is not acceptance of a finding. The maintainer will first classify the
report as `NACK`, `CONTINUE`, `ISOLATE`, `BLOCK`, or `DONE` for the defined
security-review scope. No response-time or bounty commitment is currently
offered.

## Scope priorities

High-priority areas include unauthorized `DONE`, gate bypass, provenance or
hash-binding failure, replay acceptance, unsafe path or symlink handling,
secret exposure, workflow permission escalation, unbounded execution, and
audit-chain corruption.

The development API is loopback-only by default. Exposing it to an untrusted
network without a separately reviewed deployment boundary is unsupported.

