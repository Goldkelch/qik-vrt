# Common Roundtrip publication executor

Explicit owner instruction and the frozen single HTML artifact are bound in `docs/publications/2026-09-20-qikvrt-roundtrip-unified/AUTHOR_AUTHORIZATION.json`.

Reuse assessment: the existing PowerShell publisher is fixed to an ODU PDF and bundle; the existing July effect-ack finalizer forbids GitHub Release objects. This narrowly scoped Python executor reuses their exact-source, separate-activation, scoped-token and public-readback patterns for the separately authorized HTML publication. It introduces no general release service and changes no existing gate or rule.

Each repository publishes using only its own Contents-write GITHUB_TOKEN. No administration token, cross-repository write, main change, auto-merge, tag replacement, asset replacement or direct Zenodo operation is used. A read of the other repository proves equality of this publication only. The source commit contains no workflow changes relative to current main; the executor is never the release target.

Three subjects remain distinct: C is the complete publication source; E has C as sole parent and adds the inactive executor; M has E as sole parent and activates only the request plus the canonical integrity trio. The request binds both exact C commit/tree pairs, publication bytes, release notes, owner instruction and publisher code. M is accepted only on the fixed publication branch after a non-forced E-to-M push and a fresh remote-head read.

Before any external write, the executor verifies canonical integrity, the other repository's exact source bytes, the frozen static validator and a full fresh make test on C. The personal repository's existing historical test fixture may be fetched by its manifest-bound SHA if checkout did not include it; no test is altered or skipped.

The tag is create-only at C. A conflicting existing tag, release metadata or asset blocks the operation. New content is first uploaded to a draft. Publication is followed by anonymous release and exact HTML-byte readback. The receipt is retained as a workflow artifact and subsequently persisted with the publication handoff. An interruption can resume only the matching release identity; it never overwrites a conflicting publication.
