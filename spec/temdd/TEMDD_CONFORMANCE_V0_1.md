# TEMDD v0.1 Conformance

A conforming implementation MUST parse the positive corpus, reject the negative corpus, preserve exact-subject binding, distinguish transport/result/effect acknowledgement, fail closed on stale or unknown critical evidence, and construct DONE only from the complete declared DoD.

The reference implementation is `tools/qikvrt_temdd.py`. Semantic executable checks T01-T12 are in `tools/qikvrt_temdd_conformance.py`. The C90 kernel is compiled under `-std=c90 -pedantic -Wall -Wextra -Werror`.

The bootstrap defines executable CI gates for the same bounded semantic kernel in all declared backend classes:

- Smalltalk: the hash-locked Pharo 13 image and VM execute `TEMDDRuntime.st` against positive and fail-closed vectors.
- M68000: the GNU m68k cross-toolchain builds the fixed relation and a C-ABI vector harness; `qemu-m68k` executes the resulting M68000 Linux binary.
- Lean: the pinned Lean 4.19 / Lake project is freshly built and `formalization/TEMDDCore.lean` is kernel-checked through `lake env lean`.
- C90 and Python remain executable differential/reference gates.

Successful execution establishes an exact-head backend receipt; it does not establish physical M68000 execution, independent review, Main adoption, public deployment, or `EFFECT_ACK_DONE`.

v0.1 still distinguishes BOOTSTRAP_CONFORMANT from STABLE_LANGUAGE. The PR description refers to additional normative T13-T16 closure, but numbered repository definitions for those obligations are not yet materialized. They are therefore retained as an explicit semantic HOLD rather than invented by the backend gate.
