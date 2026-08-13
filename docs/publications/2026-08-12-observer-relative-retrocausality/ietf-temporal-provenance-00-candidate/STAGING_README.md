# EAP Temporal-Provenance and Reference Profile -00

This directory is a local staging package for the proposed individual Internet-Draft:

`draft-lohmann-qikvrt-temporal-provenance-00`

It is a companion external-evidence profile for QIK-VRT EFFECT_ACK version 1.
It does not modify any closed V1 wire member, state, DONE predicate, authorization
rule, or IANA registry.

## Exact scope

For one named receiver and one authenticated, comparable source-order domain,
the profile classifies a current locally received evidence object relative to a
designated prior evidence object as:

- `FORWARD_REFERENCE` when the current source-order marker is greater;
- `RETROGRADE_REFERENCE` when it is smaller; or
- `INDETERMINATE` when comparison, authentication, or binding is insufficient.

`RETROGRADE_REFERENCE` is an operational provenance classification.  It is not
evidence of backward signalling, a modified past event, a physical claim, content
truth, a sender's intent, or an authorization for a downstream effect.

## Status

- Local staging candidate only; no IETF Datatracker submission was made.
- Intended eventual stream: individual Internet-Draft, Experimental.
- The base `draft-lohmann-qikvrt-effect-ack-03` is a separate active individual
  Internet-Draft, not an RFC, IETF standard, IETF consensus, endorsement, or
  working-group product.
- Rendering with the exact locked `xml2rfc 3.34.0` toolchain is pending because
  that third-party renderer is not installed in this environment and was not
  installed for this local preparation pass.

## Files

- `draft-lohmann-qikvrt-temporal-provenance-00.xml` - source candidate.
- `TEST_VECTORS.json` - synthetic deterministic classification fixtures.
- `verify_candidate.py` - read-only XML and vector validator.
- `RENDER_STATUS.json` - renderer status and scope boundary.
- `SUBMISSION_MANIFEST.json` - frozen local package inventory and non-effect status.
- `EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md` - form to bind a later, explicit action
  authorization to the final exact artifact hashes.

## Local validation

Run:

```sh
python3 -B verify_candidate.py
sha256sum -c SHA256SUMS
```

No command in this directory submits an Internet-Draft, sends email, invokes
Datatracker, creates a repository ref, or changes a remote system.

## Contribution provenance

Ingolf Lohmann provided the requested research direction, terminology, and
publication objective.  This staging document and its local validation material
were drafted with artificial-intelligence assistance.  It remains a candidate
requiring Ingolf Lohmann's exact-artifact review and any required IETF submission
confirmation before external submission.
