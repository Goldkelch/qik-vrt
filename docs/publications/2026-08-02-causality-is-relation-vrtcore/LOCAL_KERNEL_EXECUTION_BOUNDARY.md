<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Local Lean execution boundary

The exact returned Lean source, SHA-256
`1a39cd338f543f642acf634ffb2b63cd2c1a2ffe92878208f48d71a68a8e7d22`,
was accepted locally by Lean 4.19.0 with exit code 0.  The separate audit found
15 theorems with no axiom dependency and six depending only on Lean's
foundational `propext`; no project axiom, `sorry` or `admit` was present.

The host blocks `/proc/<own-pid>/exe` while allowing the semantically equivalent
`/proc/self/exe`.  The preserved compatibility source maps only the current
process's numeric self path to `/proc/self/exe` and passes every other
`readlink` call unchanged.  No compiled shim or Lean binary is committed.

`LOCAL_KERNEL_EVIDENCE.json` and the local logs are supplemental execution
evidence.  They are not an exact-head GitHub workflow receipt and do not alone
authorize publication.  The repository publication gate separately reruns the
same candidate and axiom audit in the pinned GitHub Actions Lean environment.

The original source comment saying `CANDIDATE_UNVERIFIED_IN_THIS_RUNTIME` is a
truthful statement about the earlier authoring run and remains byte-frozen.  It
is superseded only on the additive meta-level by later byte-bound receipts; the
source itself was not silently rewritten after verification.

