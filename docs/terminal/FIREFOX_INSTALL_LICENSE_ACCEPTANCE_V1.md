<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Firefox installation license acceptance v1

## Scope

This contract governs the repository-supplied installation helper for the QIK-VRT Firefox reference adapter. It does not replace any license text and it does not create a commercial grant.

The controlling order remains the repository licensing order:

1. third-party license or provenance notice;
2. explicit file-level SPDX identifier or specific notice;
3. the current QIK-VRT software rule;
4. the current QIK-VRT non-source rule.

For current QIK-VRT-controlled software identified accordingly, the software license is `PolyForm-Noncommercial-1.0.0`. The standard license includes the personal/noncommercial uses stated in its own text. Ordinary commercial exploitation is outside that grant and requires a separate written commercial license from the rights holder unless another applicable right or statutory exception applies.

QIK-VRT documentation and non-source material identified accordingly remain under `CC-BY-NC-ND-4.0`. Earlier valid grants and third-party licenses are not narrowed by this installation contract.

## Installation gate

The installer MUST:

- carry the exact PolyForm Noncommercial and CC BY-NC-ND legal texts plus the QIK-VRT licensing guide and commercial-use policy in the XPI;
- display the noncommercial boundary and the reason for the gate before profile mutation;
- require explicit acceptance, either by the exact interactive acceptance phrase or the explicit `--accept-license` CLI switch;
- fail closed without acceptance;
- copy the accepted XPI atomically into the Firefox profile and verify the installed bytes against the accepted artifact hash;
- report `commercial_use_licensed=false` and `activation_claimed=false`.

The CLI switch is provided for explicit noninteractive invocation and repository tests. A CI invocation demonstrates the gate mechanics only; it is not an end-user acceptance receipt and not a commercial license.

## Why acceptance is required by this product path

Repository access, a build, a workflow PASS, or possession of an artifact must not be conflated with the scope of the license grant. Installation is the point where the product path creates a concrete local copy and operational use. Requiring acceptance there exposes the applicable terms before the filesystem mutation and makes the noncommercial boundary machine-testable.

This is a QIK-VRT product and evidence rule. It does not assert that a particular click-through mechanism is legally required or sufficient in every jurisdiction, and it does not waive statutory exceptions or limitations.

## Firefox distribution boundary

The repository-produced XPI is an unsigned verification/reference artifact unless separately signed through a supported Mozilla or managed deployment path. Copying it into a profile does not prove Firefox activation, Mozilla distribution approval, public availability, or `EFFECT_ACK_DONE`.

Therefore:

`LICENSE_ACCEPTED != XPI_COPIED != FIREFOX_ACTIVATED != PUBLIC_DISTRIBUTION != EFFECT_ACK_DONE`.
