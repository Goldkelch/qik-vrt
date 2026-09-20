# Draft03: full finite snapshot conformance

This extends the four-Boolean demonstration without changing its contract.
The neutral contract was committed first at
`62ce6932adfc5f557034be9b9f5662c52ff02c5c`, with SHA-256
`0c7dc0f5b27d4c7879f56afcfb58c1a64b406ea33a926481490df7142f61186a`.
Its authority is the versioned
[Draft03, sections 3, 4.1 and 4.2](https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03),
not any of the six implementations.

## Domain and boundaries

The core has 18 named Boolean inputs, six risk classes and six decision classes:
9,437,184 cases, of which 6,553,600 use valid enum values. An additional
consumer table has nine validator results, six derived-result classes and six
declared-state classes: 18,432 cases. Every case in both tables is executed in
each carrier and checked byte for byte against the declarative contract.

Result 5 is **REJECTED_NO_RECORD**, a diagnostic outside the five wire states.
One INVALID enum class represents all unsupported encodings. Parsing,
cryptography, evidence retrieval, real timestamps and external facts are not
implemented here: their validator results are explicit Boolean inputs.
The C90 wrapper rejects invalid enums before calling the existing snapshot
core; its diagnostic rejection must not be confused with the raw C API's
defensive BLOCK fallback on an invalid decision argument.

The component product is defined as
`(core(x), admit(core(x), declared, validators))`.
Its equivalence follows from the two exhaustive component equalities by the
Lean substitution theorem. The roughly 29 billion product elements are **not**
individually executed. This proves the stated pure composition, not unmodelled
application wiring or complete mediation of a real protected effect.

## Neutral mapping

Bit positions are fixed in `contract.json`, least significant bit first.
The named required evidence predicate denotes required references being a
subset of validated evidence. Empty questions/checks and presence of an owner
are separate bits.

| Stage | Neutral condition | Result |
| --- | --- | --- |
| Validation | Invalid risk or decision | Reject without a record |
| 1 | Invalid predecessor | BLOCK |
| 2 | Deadline exceeded | BLOCK |
| 3 | Missing identifier or invalid input digest | NACK |
| 4 | Integrity failure | BLOCK |
| 5 | Explicit BLOCK decision | BLOCK |
| 6 | Explicit ISOLATE decision | ISOLATE |
| 7 | All 17 CoreDone conjuncts | DONE |
| 8 | Remaining valid snapshots | CONTINUE |

The positive DONE mask is 61439 (0xEFFF), with risk LOW/MEDIUM/HIGH/CRITICAL and
decision RELEASE: exactly four cases. Clearing any required bit or setting any
of deadline, invalid predecessor and integrity failure removes DONE.
Consumer admission has exactly one positive case: derived DONE, declared DONE,
and all nine supplied checks true. This includes the record's release flag.

## Independent carriers

| Carrier | Semantic source | Execution |
| --- | --- | --- |
| C90 | Existing `src/effect_ack_core.c` plus explicit snapshot/rejection and consumer adapter | Strict C90 compiler |
| MC68000 | `m68000.s`: both decision and consumer routines | Assembler restricted to MC68000; QEMU m68k |
| Smalltalk | `smalltalk.st` | Pinned Pharo 13 |
| TEMDD | `full.temdd` ordered relations | Existing parser/v1 IR plus the bounded profile below |
| Lean | `Full.lean` | Lean 4.19 kernel and executable |
| Ada/SPARK | `ada/full_snapshot.ads` and `.adb` | GNAT execution and GNATprove |

The shared C harness supplies enumeration and ASCII I/O only; it contains no
decision or admission semantics. No carrier reads the neutral oracle at run
time, reads another carrier's output, or is generated from another carrier.
The implementations were prepared by the same assistant from the stated
contract; this is **not** independent human authorship or independent review.
The comparator is infrastructure interpreting declarative cubes, not a seventh
counted implementation or an implementation chosen as the definition.

## TEMDD execution profile

The adapter preserves the TEMDD 0.1 relation fields. This explicit finite
expression profile assigns executable meaning to `first_match_core` and
`first_match_admission`: sort by unique source order, select the first true
source expression and return its target. Every assertion must be TRUE and
FRESH; an uncovered input fails. The grammar permits integer/Boolean literals,
named finite inputs, bitwise AND, equality, inequality, greater-than, AND and
OR. There are no calls, imports, attribute access or arbitrary evaluation.
This is a documented bounded conformance profile, not the entire TEMDD
event/effect runtime. Acceptance of that scope remains part of independent
review.

## Evidence and reproduction

The existing multi-carrier workflow provisions all pinned runtimes, preserves
the 16-case regression and invokes `bash full/run.sh <evidence-directory>`.
See the workflow for exact repository-relative paths and provisioning commands.
The full artifact contains six 9,455,616-byte streams, canonical TEMDD IR,
kernel axiom reports, complete GNATprove output, negative-control logs and an
exact-HEAD/tree report. A failed comparator overwrites any previous PASS report.

Lean proves the DONE guard equivalence, admission equivalence, positive
witnesses, insufficiency of transport acknowledgement and the conditional
composition theorem. It does not claim to have discharged the external table
comparisons inside its kernel. SPARK proves the snapshot and admission
postconditions and absence of runtime errors in the semantic package; its I/O
harness is exercised, not included in the SPARK proof. Proof logs and success
markers are trusted-CI receipts, not independently authenticated proofs.

The forecast remains unresolved until an identified independent reviewer
audits the Draft03-to-contract translation, source independence and profile
scope, and publicly reproduces all six carriers. Repository CI is not that
review. These results make no claim about light cones, physical causality or
empirical scientific truth.
