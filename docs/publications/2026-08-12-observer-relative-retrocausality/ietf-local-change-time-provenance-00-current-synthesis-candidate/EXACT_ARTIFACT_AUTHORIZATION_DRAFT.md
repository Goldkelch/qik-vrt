<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Draft only — exact-artifact IETF submission authorization

**Status:** `NOT_AN_AUTHORIZATION`
**Candidate:** `draft-lohmann-qikvrt-local-change-time-00`
**Target:** IETF Datatracker, individual Internet-Draft, intended status
Experimental

This file is a template.  It grants no submission authority and records no
submission, email, acceptance, publication, RFC, or IETF consensus.

Before any external action, replace every bracketed value using the final
rendered package and a fresh destination observation.  The author must then
issue an unambiguous action-time statement that names this document and the
exact SHA-256 values.

```text
AUTHORIZE_EXACT_IETF_SUBMISSION

I, Ingolf Lohmann, authorize submission of exactly the following final
individual Internet-Draft package to the IETF Datatracker:

  document: draft-lohmann-qikvrt-local-change-time-00
  title: Local Change-Time Provenance Profile for QIK-VRT Effect Acknowledgement
  intended status: Experimental
  author/email: Ingolf Lohmann / [current Datatracker account email]
  destination observed at: [UTC timestamp and safe public destination URL]

  XML:  [final filename] [bytes] sha256:[digest]
  TXT:  [final filename] [bytes] sha256:[digest]
  HTML: [final filename] [bytes] sha256:[digest]
  manifest: SUBMISSION_MANIFEST.json [bytes] sha256:[digest]
  vectors: TEST_VECTORS.json [bytes] sha256:[digest]

I understand that this authorization covers the named external submission only.
It does not assert a physical backwards-signalling channel, changed past event,
payload truth, IETF endorsement, IETF consensus, an RFC, or independent
interoperability.

Signed/confirmed at action time: [name, timestamp, confirmation channel]
```

The external operator must retain the returned submission identifier and any
status/approval receipt without secrets, reobserve the public document after
publication, and record byte identity or documented renderer-induced drift.
