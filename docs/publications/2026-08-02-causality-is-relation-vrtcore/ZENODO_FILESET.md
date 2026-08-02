<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Intended Zenodo fileset

Publication ID: `qikvrt-causality-is-relation-vrtcore-v1`.

The frozen record candidate preserves the German article,
WhatsApp/read-aloud versions, XeLaTeX source, rendered PDF, EBNF grammar, exact
Lean candidate, axiom-audit source, claim-transition matrices, source
bindings, exact-head CI evidence, kernel receipt, evidence boundary, citation
metadata, license notice, reproduction README, visible change notice,
prepublication return receipt, canonical Zenodo metadata and an acyclic
checksum manifest.  It also preserves the related IETF revision -03 XML, TXT,
HTML and fail-closed Datatracker submission receipt as supplementary context.

The local runtime shim binary is excluded.  Its small auditable C source and
the supplemental local execution receipt may be included only as environment
diagnostics; the exact-head GitHub Actions result remains the publication gate.

Repository-side owner authorization, Zenodo access tokens and single-use
consumption locks are control artifacts and MUST NOT enter the uploaded
fileset.

`ZENODO_SHA256SUMS` binds every candidate and artifact except itself and
`MACHINE_PROOF_BUNDLE.json`; this deliberate exclusion keeps the derivation
acyclic.  The proof bundle binds the checksum file and is itself identified by
the later owner-authorization event.

This document describes scope only.  It is not an upload authorization and
does not claim that a Zenodo deposition exists.  Exact-head kernel evidence and
the prepublication return are frozen at H3.  Production publication remains
blocked until the natural person supplies the subsequent exact hash-bound
`AUTHORIZE_EXACT_UPLOAD` statement required by the active publisher policy.
