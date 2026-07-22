<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# EFFECT_ACK release automation

This contract automates the already authorized EFFECT_ACK universality release
without a `workflow_dispatch`, a GitHub Release object, a Datatracker
submission, or another interactive sign-in exercise. It consumes the existing
repository secret `ZENODO_ACCESS_TOKEN` only inside the two Zenodo client
steps. The token is never a command-line argument, artifact, state-branch
value, job output, or log value.

The automation is deliberately separate from the bounded adaptive runtime.
Adaptive evidence cannot activate it. Only a reviewed, single-file marker
commit with the exact state, confirmation phrase, source commit, source tree,
schema digest, client digest, manifest digest, and canonical authorization
digest can reach an external-effect job.

## Fixed release identity

| Field | Exact value |
|---|---|
| Version | `2026.07.22-effect-ack-universality-1.0.0` |
| Annotated tag | `v2026.07.22-effect-ack-universality-1.0.0` |
| Tagger | `Ingolf Lohmann <ingolf.lohmann@live.com>` |
| Tagger timestamp | `2026-07-22T00:00:00Z` |
| Authority repository | `Goldkelch/qik-vrt` |
| Mirror repository | `ingolf-lohmann/qik-vrt` |
| Public evidence branch | `qikvrt/zenodo-state` |

The full fixed tag message is in
`release/effect-ack-universality-request.json` and in both workflows. GitHub's
Git database API creates an annotated tag object directly. The finalize
workflow performs one read-only `GET /releases/tags/<tag>` check and blocks
unless GitHub returns `404`; it never creates, edits, deletes, or publishes a
GitHub Release object.

## Immutable two-commit authorization

Both phases use the same pattern. The automation branch must first point to
commit A. Commit A contains the complete reviewed candidate and the inert
marker. Commit B must have A as its sole parent and must change exactly one
path: `release/effect-ack-universality-request.json`. The push of B is the
triggering event.

The workflow blocks unless all of the following are simultaneously true:

1. the event repository and exact automation ref are allowed;
2. the push is not forced, the remote branch still points to B, and the event's
   `before` value is A;
3. B has exactly one parent, and the only A-to-B change is the marker;
4. `expected_source_commit` equals A and `expected_source_tree` equals A's Git
   tree through `git show -s --format=%T HEAD^` and the GitHub API; the marker
   HEAD tree is separately required to differ, preventing accidental use of
   `HEAD^{tree}` in place of the authorized parent tree;
5. the marker has the closed key set and fixed constants, the checked-in JSON
   Schema digest matches, and the canonical authorization digest matches;
6. the hash-bound Zenodo client and the phase-specific Zenodo manifest are
   regular, non-symlink files with the authorized SHA-256 values;
7. `make test` passes in a detached worktree of A, including the canonical
   repository-integrity gate.

This construction avoids a self-referential commit hash in the marker. The
effect targets parent A, never marker commit B. The active marker therefore
stays outside `main`.

The canonical authorization digest is SHA-256 over UTF-8 JSON after removing
only `authorization_payload_sha256`, sorting keys, and using `,` and `:` as
separators without ASCII escaping. The digest detects any change to every
other marker field. It is a byte-binding mechanism; repository review and the
exact confirmation phrase supply authorization.

## Phase 1: reserve, never publish

The reserve workflow listens only on:

`refs/heads/automation/effect-ack-universality-reserve-20260722`

It runs only in `Goldkelch/qik-vrt`. The active marker must use:

- `state`: `reserve`
- `confirm`: `RESERVE_ZENODO_DRAFT_ONLY_NO_PUBLISH`
- exact A commit/tree and current client/reserve-manifest digests
- zero reservation-evidence digest and null DOI fields

After the full release-candidate gate, the workflow invokes:

```text
python -B tools/qikvrt_zenodo_actions.py reserve \
  --manifest release/effect-ack-universality-zenodo.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The client may create or resume drafts and reserve identifiers, but this phase
does not publish. The workflow rejects a result containing the secret, a
secret-shaped field, or an affirmative publication/submission flag.

The exact non-secret reservation result is uploaded as a 30-day Actions
artifact and committed to this stable public path on the dedicated state
branch:

`release-state/effect-ack-universality/zenodo-reservation.json`

That branch is an automation evidence channel, not a source branch. It must
remain writable by the repository `GITHUB_TOKEN` and must not be merged into
`main`. Its history preserves replaced evidence. The state writer creates an
orphan root commit when the branch is absent and otherwise appends a
non-forced commit. Repeating a completed run with identical bytes is a no-op.

The reservation binds the immutable release identity and repository/tag
authorization envelope. The later final manifest may add the reserved DOI to
metadata and rebuild file hashes; it is not incorrectly required to retain a
pre-DOI full-file fingerprint.

The software draft versions the credential-owned QIK-VRT concept
`10.5281/zenodo.21488115` from source record `10.5281/zenodo.21488116`.
Legacy QIKVRT V8.33 record `10.5281/zenodo.20712301` remains an explicit
historical reference; this automation does not claim or rewrite its separately
owned version chain.

## Phase 2: tag both repositories, then publish on Goldkelch

After the reserved DOI values have been embedded, rendered, verified and
merged, both `main` branches must have the same final tree. In each repository,
create the branch below at its own exact `main` commit A, then add only active
marker commit B:

`refs/heads/automation/effect-ack-universality-finalize-20260722`

The active marker must use:

- `state`: `finalize`
- `confirm`: `FINALIZE_TAGS_AND_ZENODO_PUBLICATION`
- that repository's exact main commit A and the shared final tree
- the final client and manifest SHA-256 values
- the SHA-256 of the public reservation result
- both DOI values from that reservation

The finalize workflow additionally proves that A is still the current `main`
head. It then creates the fixed annotated tag at A. If the tag already exists,
the workflow succeeds only when its annotated-object type, target commit,
target tree, tagger identity, timestamp and message all match exactly. A
lightweight, moved or differently annotated tag blocks the run.
Immediately after tag verification, a read-only GitHub API lookup must also
prove that no GitHub Release object exists for that tag.

Run the mirror authorization first. `ingolf-lohmann/qik-vrt` performs only the
tag and public tag verification. The Goldkelch job creates or verifies its own
tag, polls the public mirror tag, and requires the mirror target to have the
same authorized final tree and fixed annotation.

Immediately before publication, the checked-in hash-bound template is expanded
outside the tagged tree:

```text
python -B tools/qikvrt_build_zenodo_manifest.py \
  --repository-root . \
  --template release/effect-ack-universality-zenodo.json \
  --source-commit <authorized-main-commit> \
  --source-tree <authorized-main-tree> \
  --output-directory .qikvrt/release/effect-ack-universality \
  --result .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json
```

The helper reads every blob path from the exact authorized parent commit,
verifies its tree, and emits a normalized deterministic `tar.gz`, a checksum,
provenance, and a transient final manifest. The checked-in reserve template
contains an explicit non-upload sentinel; the final client rejects that
sentinel. The generated manifest replaces it with the exact archive,
checksum, and provenance hashes. Because those derived bytes live under the
integrity-transient `.qikvrt/` prefix and are not inside the tagged tree, the
archive contains the complete tagged tree without asking that tree to contain
the digest of an archive that contains itself.

Only then does Goldkelch call:

```text
python -B tools/qikvrt_zenodo_actions.py finalize \
  --manifest .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json \
  --reservation .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-finalization.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The hash-bound client provides the idempotent Zenodo reservation/finalization
semantics. A retry verifies the existing tag rather than moving it and resumes
the bound Zenodo records rather than creating unrelated records.

Each repository writes public tag evidence to
`release-state/effect-ack-universality/tag-verification.json`. Goldkelch also
writes a non-secret finalization envelope—with both DOI results, the generated
manifest digest, every deposited filename/size/MD5/SHA-256, and the tag target
commit/tree—to
`release-state/effect-ack-universality/zenodo-finalization.json`. Matching
Actions artifacts are retained for 30 days.

## Permissions and trigger boundary

Validation jobs have `contents: read`. Only jobs that create a tag or append
public evidence have `contents: write`. The repository-scoped `GITHUB_TOKEN`
is used only in its own repository; no cross-repository write token is needed.
Goldkelch reads the public mirror tag but does not modify the mirror.

There is deliberately no `environment:` gate and no interactive login or SSO
step. The immutable two-commit marker is the explicit reviewed authorization,
and Goldkelch consumes its already configured repository secret directly.

All external Actions are pinned by full commit SHA. Both workflows share one
non-cancelling per-repository concurrency group so reserve, tag and state
writes cannot overlap in the same repository.

GitHub documents that events created with `GITHUB_TOKEN` generally do not
start a new workflow run. Accordingly, tag creation is the terminal GitHub
effect here; correctness does not depend on a tag-triggered follow-up workflow
or on a GitHub Release object. Zenodo finalization is an explicit job in the
same Goldkelch workflow.

No step calls the IETF Datatracker. The existing `-01` XML/TXT/HTML validation
remains evidence only and is not submitted by this release automation.
