<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Round-Trip Zenodo metadata clarification — v2 preparation

This directory is an append-only successor to
`round-trip-canonical-publication-zenodo-metadata-clarification-v1`.
It does not alter the historical v1 preparation or any byte in the already
published Zenodo record `21888130`.

## Scope

The intended operation is metadata-only for the existing public record:

- exact title remains `Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP`;
- the 54 deposited files, DOI, concept DOI and version remain unchanged;
- only `description`, `keywords`, `notes` and, if still appropriate after a
  fresh remote observation, `related_identifiers` may change;
- no new record, no new version and no file upload, replacement or deletion is
  permitted by this work unit.

The searchable terms identify topics treated by the corpus. They do not by
themselves change the epistemic status of any scientific claim.

## Why this is not an executable manifest yet

The v1 preparation has a `prereserve_doi` field in its after-metadata payload.
That field is correct for record creation but forbidden for a same-DOI metadata
edit. The v1 directory remains historical evidence of that blocked preparation.

`METADATA_AFTER_DRAFT.json` removes that field. Before it becomes an execution
candidate, a fresh public Zenodo observation must bind the record revision,
ETag, normalized public metadata response and every immutable file identity.
Only then may the repository produce the metadata-edit manifest, machine proof,
v2 return receipt and a new single-use owner authorization.

## Local v2 scaffolds

The following files are deliberately **not** inputs accepted by
`tools/qikvrt_zenodo_metadata_edit.py`.  They make the missing inputs and their
normalization rules explicit without fabricating a current remote observation:

- `FRESH_PUBLIC_RECORD_CAPTURE_TEMPLATE.json` — records exactly what a new
  unauthenticated public GET must capture, including response bytes, ETag,
  revision and the public metadata object.  Its small historical context is
  evidence of an earlier observation only and is expressly not reusable as an
  execution baseline.
- `METADATA_BEFORE_NORMALIZATION_TEMPLATE.json` — defines the fail-closed
  extraction of `record.metadata`.  In particular, `prereserve_doi` is a
  blocking condition for a same-DOI edit, not a field to silently remove.
- `IMMUTABLE_FILE_INVENTORY_TEMPLATE.json` — specifies the 54-file public
  listing and byte-redownload check required before the controller may receive
  a file inventory.  The known historical count and aggregate digest are a
  cross-check only, not a substitute for that new observation.
- `PROOF_RETURN_AND_AUTHORIZATION_SCAFFOLD.json` — lists the artifacts that
  must be materialized in dependency order after the fresh baseline.  It is not
  a v2 proof bundle, return receipt, authorization or execution manifest.
- `METADATA_EDIT_EXECUTION_MANIFEST_TEMPLATE.json` — is intentionally tagged
  with a different schema and an ineligible state.  Passing it to the metadata
  editor must fail before any network operation.

`LOCAL_PREPARATION_MANIFEST.json` binds those scaffolds into one
`PREPARATION_NOT_EXECUTABLE` local state.  It is a plan and audit aid; it cannot
authorize an external operation.

`CURRENT_SYNTHESIS_AND_SUCCESSOR_STRATEGY.md` records the current editions
decision: keywords may make the preserved historical corpus discoverable, but
the current synthesis remains a separate successor preparation until its own
fresh artifact and authorization boundary are materialized.

`SHA256SUMS` binds this local preparation set.  It intentionally excludes
itself; run `sha256sum -c release/round-trip-canonical-publication-zenodo-metadata-clarification-v2/SHA256SUMS`
from the repository root to check it.

## Scientific and historical boundary

The existing record is preserved as a historical intermediate state. A new
primary scientific synthesis belongs in a linked Zenodo successor version, not
in this metadata-only edit. In particular, no metadata phrase is permitted to
turn a model theorem, a technical realization, an authorial reality
correspondence thesis, independent empirical confirmation and scientific
consensus into the same claim.

Status: `PREPARATION_NOT_EXECUTABLE_PENDING_FRESH_PUBLIC_BASELINE`.
