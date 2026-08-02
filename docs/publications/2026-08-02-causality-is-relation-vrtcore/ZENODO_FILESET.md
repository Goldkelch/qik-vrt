<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Intended Zenodo fileset

Publication ID: `qikvrt-causality-is-relation-vrtcore-v1`.

The intended record preserves the German article, WhatsApp/read-aloud version,
XeLaTeX source, rendered PDF, EBNF grammar, exact Lean candidate, axiom-audit
source, claim-transition matrix, source bindings, kernel receipt, evidence
boundary, citation metadata, license notice, reproduction README and an
acyclic checksum manifest.

The local runtime shim binary is excluded.  Its small auditable C source and
the supplemental local execution receipt may be included only as environment
diagnostics; the exact-head GitHub Actions result remains the publication gate.

Repository-side owner authorization, Zenodo access tokens and single-use
consumption locks are control artifacts and MUST NOT enter the uploaded
fileset.

This document describes scope only.  It is not an upload authorization and
does not claim that a Zenodo deposition exists.  The exact manifest is frozen
only after an exact-head kernel result, a prepublication return receipt and the
subsequent hash-bound `AUTHORIZE_EXACT_UPLOAD` event required by the active
publisher policy.
