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

The locally finalized XML, TXT, HTML, and vector identities are prefilled
below.  Before any external action, the destination/account fields and the
final manifest identity must be filled from a fresh observation of the exact
unchanged package.  The author must then issue an unambiguous action-time
statement that names this document and the exact SHA-256 values.

```text
AUTHORIZE_EXACT_IETF_SUBMISSION

I, Ingolf Lohmann, authorize submission of exactly the following final
individual Internet-Draft package to the IETF Datatracker:

  document: draft-lohmann-qikvrt-local-change-time-00
  title: Local Change-Time Provenance Profile for QIK-VRT Effect Acknowledgement
  intended status: Experimental
  author/email: Ingolf Lohmann / [current Datatracker account email]
  destination observed at: [UTC timestamp and safe public destination URL]

  XML:  draft-lohmann-qikvrt-local-change-time-00.xml 34747 sha256:6ca7f8f65d2f04c3db2465c5eaccf37f9cb874900347ab50e41f20b8b31acc95
  TXT:  draft-lohmann-qikvrt-local-change-time-00.txt 38586 sha256:482aeaaa9a2c31a4b985b3789daa604af8b4133d5b238e047bd441ca48c47bae
  HTML: draft-lohmann-qikvrt-local-change-time-00.html 88073 sha256:b565c2248f2ef387071236e4c4954a32bbc460f237391ef295a608bae0506bc0
  manifest: SUBMISSION_MANIFEST.json [bytes] sha256:[digest]
  vectors: TEST_VECTORS.json 7360 sha256:7a1adca587c906f2deddb1824eb7b6d0372c424c53c5b2f961aa28b87fa722f5

I understand that this authorization covers the named external submission only.
It does not assert a physical backwards-signalling channel, a coordinate future
as causal future, a changed past event, payload truth, IETF endorsement, IETF
consensus, an RFC, or independent interoperability.

Signed/confirmed at action time: [name, timestamp, confirmation channel]
```

The external operator must retain the returned submission identifier and any
status/approval receipt without secrets, reobserve the public document after
publication, and record byte identity or documented renderer-induced drift.
