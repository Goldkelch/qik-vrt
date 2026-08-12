<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Local staging instructions — EAP-LCTP -00

Candidate: `draft-lohmann-qikvrt-local-change-time-00`
Intended status: Experimental
Submission type: Individual Internet-Draft
External status: **not submitted**

This is a separate initial candidate with a new I-D name.  It is not a
revision of an IETF-published document and it does not alter the separately
published `draft-lohmann-qikvrt-effect-ack-03` base protocol.

The current candidate makes one semantic clarification explicit: QIK-VRT Eigenzeit is the
receiver's monotonic local change time.  In the protocol profile this is
represented by `local_change_index`; it is not assumed to be a relativistic
proper-time measurement.  `NEGATIVE_INFORMATION_DIRECTION` requires increasing
receiver-local change order and decreasing authenticated source order in the
same declared source-order domain.

## Required local checks and fixity

```sh
python3 -B verify_candidate.py
sha256sum -c SHA256SUMS
```

The validator checks the XML header, seven deterministic classification
fixtures, local non-effect assertions, manifest bindings, and the full
`SHA256SUMS` scope.  It performs no network operation and does not render the
draft.

## Required renderer check before any submission

Render `draft-lohmann-qikvrt-local-change-time-00.xml` using the locked
`xml2rfc 3.34.0` derivation, retain the generated TXT and HTML, and refresh
`RENDER_STATUS.json`, `SUBMISSION_MANIFEST.json`, `SHA256SUMS`, and the
artifact-bound authorization form from the final bytes.  The exact renderer is
not available in this local runtime.  `idnits` is also not a declared available
runtime component, so this package records no `idnits` result.

The render output must be reviewed for RFCXML errors, line wrapping, references,
BCP 78/79 boilerplate, I-D filename and revision, and no unintentional claims
of physical backwards signalling, past modification, IETF consensus, or an RFC.

## Action-time boundary

Preparation is not submission.  Submission additionally requires a fresh
Datatracker destination observation, valid author/account fields, exact final
artifacts, an explicit artifact-bound decision by Ingolf Lohmann, immediate
confirmation before upload, and an independently retained post-submission
receipt.
