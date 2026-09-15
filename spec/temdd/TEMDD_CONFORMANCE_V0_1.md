# TEMDD v0.1 Conformance

A conforming implementation MUST parse the positive corpus, reject the negative corpus, preserve exact-subject binding, distinguish transport/result/effect acknowledgement, fail closed on stale or unknown critical evidence, and construct DONE only from the complete declared DoD.

The reference implementation is `tools/qikvrt_temdd.py`. Semantic executable checks T01-T12 are in `tools/qikvrt_temdd_conformance.py`. The C90 kernel is compiled under `-std=c90 -pedantic -Wall -Wextra -Werror`. Smalltalk and M68000 are source backends in this bootstrap and MUST become executable runtime gates before a future stable TEMDD 1.0 claim. Lean obligations are source-admitted in v0.1 and MUST be compiled by the repository's Lean/Lake proof lane before stable promotion.

v0.1 therefore distinguishes BOOTSTRAP_CONFORMANT from STABLE_LANGUAGE. The former may be reached by this candidate; the latter is intentionally not claimed.
