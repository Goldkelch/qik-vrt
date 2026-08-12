<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# EAP-LCTP -00 current-synthesis candidate

Status: **`LOCAL_CURRENT_CANDIDATE_NOT_SUBMITTED`**.

This directory is a new local candidate for the individual Internet-Draft
`draft-lohmann-qikvrt-local-change-time-00`.  It is a separate current
preparation for the QIK-VRT observer-relative local-change-time synthesis.  It
does **not** report an IETF Datatracker submission, acceptance, announcement,
endorsement, RFC, standard, working-group adoption, or independent
interoperability result.

## Historical preservation

The earlier directory `../ietf-temporal-provenance-00-candidate/` remains a
byte-preserved local candidate for a different, unpublished Internet-Draft
name.  It is neither edited nor reinterpreted as this candidate.  That
historical candidate used a local receipt sequence and the labels
`RETROGRADE_REFERENCE` and `FORWARD_REFERENCE`; this new -00 candidate uses a
distinct draft name and a distinct profile identifier.

## What is revised here

The profile evidence object has version `eap-lctp-1`.  It represents the
receiver-local effective-change order as `local_change_index`.  In QIK-VRT
terminology this is the receiver's **operational Eigenzeit**: a strictly
increasing local change order.  It is not a global clock and is not, by
itself, a claim about relativistic metric proper time.

For a validated comparison, the profile reports
`NEGATIVE_INFORMATION_DIRECTION` precisely when:

```
delta(local_change_index) > 0
delta(source_order_marker) < 0
```

and the receiver identity, designated baseline, authenticated source and
receiver assertions, and source-order domain all remain comparable.  The
classification is an authenticated relation between local change order and
source order.  It is not evidence of backwards signalling, a message from the
future, changed past records, payload truth, sender intent, physical or ontic
retrocausality, or authorization of a downstream effect.

## Contents

| File | Role |
|---|---|
| `draft-lohmann-qikvrt-local-change-time-00.xml` | RFCXML source for the separate current candidate. |
| `TEST_VECTORS.json` | Synthetic deterministic classification fixtures. |
| `verify_candidate.py` | Offline XML and vector validator. |
| `RENDER_STATUS.json` | Renderer observation; it is not a Datatracker receipt. |
| `SUBMISSION_MANIFEST.json` | Exact local candidate inventory and non-effect status. |
| `SOURCE_PROVENANCE.json` | Links the historical candidate and current synthesis inputs without replacing either. |
| `EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md` | A non-authorizing form for a later action-time decision. |
| `SHA256SUMS` | Fixity index for this local package. |

## Local validation and fixity

```sh
python3 -B verify_candidate.py
sha256sum -c SHA256SUMS
```

The validator checks the XML header, seven deterministic classification
fixtures, the declared local non-effect state, the manifest-to-file bindings,
and the complete `SHA256SUMS` scope.  It does not render, submit, send email,
or authenticate a real principal.

The locked `xml2rfc 3.34.0` renderer is not available in this runtime; `idnits`
is likewise not available as a declared runtime component.  Thus this package
intentionally contains no locally generated TXT or HTML artifacts and makes no
`idnits` result claim.  Before any external upload, the exact final source must
be rendered and reviewed with the required renderer, the artifact manifest and
fixity index must be refreshed, and the author must confirm the exact bytes and
destination state at action time.

No command in this directory submits a document, sends email, calls the
Datatracker, creates a repository reference, or mutates an external system.
