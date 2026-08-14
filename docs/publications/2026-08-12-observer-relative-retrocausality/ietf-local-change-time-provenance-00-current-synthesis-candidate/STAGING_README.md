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

The profile does not encode coordinate-time assignments between
spacelike-separated physical events.  A coordinate assignment of a source
observer's local-present event to another observer's coordinate future is not
a causal-future relation and does not make a source-bound object available
before future-directed delivery reaches the receiver.

## Required local checks and fixity

```sh
python3 -B verify_candidate.py
sha256sum -c SHA256SUMS
```

The validator checks the XML header, seven deterministic classification
fixtures, local non-effect assertions, manifest bindings, retained TXT/HTML
structure, and the full `SHA256SUMS` scope.  It performs no network operation
and does not submit the draft.

## Required renderer check before any submission

The exact source has been rendered twice using the locked `xml2rfc 3.34.0`
derivation on Python 3.12.13 with networking disabled, configuration files
skipped, and independent isolated caches.  The retained TXT and HTML are
byte-identical across both runs and are bound by `RENDER_STATUS.json`,
`SUBMISSION_MANIFEST.json`, and `SHA256SUMS`.

The renderer reported no warning or error.  The text line width, BCP 78/79
boilerplate, I-D filename and revision, Security Considerations, IANA
Considerations, and claim boundaries were checked locally.  `idnits` is not a
declared runtime component, so this package records no `idnits` result.

## Action-time boundary

Preparation is not submission.  Submission additionally requires a fresh
Datatracker destination observation, valid author/account fields, exact final
artifacts, an explicit artifact-bound decision by Ingolf Lohmann, immediate
confirmation before upload, and an independently retained post-submission
receipt.
