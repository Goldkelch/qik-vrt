<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Immutable inputs, not current language editions

These eight ChatGPT-generated full-text draft blobs were already created in
this repository during the interrupted translation session. They refer to the
539-block German source before the opening Spotify URL was supplied. They are
preserved unchanged here so preparation does not depend on API permissions,
API quotas or the continued availability of otherwise unattached Git objects.

`tools/qikvrt_journey_translation.py` checks each literal Git blob identity,
reconstructs the exact earlier German source, checks the old block structure,
performs only the disclosed editorial corrections and media insertion, and
produces newly source-bound draft sidecars. No former validation or review is
transferred. These input files do not count towards current 47-edition coverage;
only validated files under `docs/reise/translations` do.

The failed native run 34622608306 reported HTTP 403 before producing any draft.
Its old error handler omitted the server reason and rate headers, so a quota
cause versus a permission cause was not established. The repair removes this
unnecessary authenticated read dependency from pure preparation, preserves
live-head checks at the write boundary, and retains failure diagnostics.

Original German source and publication direction: Ingolf Lohmann.
Translation drafts, technical repair and regression tests: ChatGPT assistance.
Independent linguistic review, public website delivery and completion are not
claimed by this archival input surface.
