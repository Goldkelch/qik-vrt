# Local verification and publication-readiness summary

**Snapshot date:** 2026-07-22

**Public repository heads inspected:**

- `Goldkelch/qik-vrt`: `a37cc450447d8095df71c07ecef6dd13d242dd8c`
- `ingolf-lohmann/qik-vrt`: `41e1ee0b31dcfad15fd35c6c68d221ba9d926ea5`
- common content tree: `c2fb00c593baea2652092c454e60161e7cf2b56f`

**Verified object:** the unpublished 2026-07-22 working-tree repair set based on
the common public content tree above

## Result

```text
LOCAL_COMPONENT_RESULT = PASS
PYTHON_TEST_FILES_MATCHED = 10
PYTHON_TEST_MODULES_WITH_CASES = 9
PYTHON_TESTS_RUN = 102
PYTHON_TESTS_PASSED = 102
PYTHON_TESTS_FAILED = 0
PYTHON_TESTS_SKIPPED = 0
C90_VALID_SNAPSHOTS = 2,621,440
C90_ORACLE_CHECKS = 7,864,387
C90_EFFECT_ACK_CORE = PASS
ADAPTIVE_COGNITION = PASS
ADAPTIVE_RUNTIME_POSIX = PASS
ADAPTIVE_RUNTIME_POWERSHELL = PENDING_WINDOWS_CI
SCIENTIFIC_PROOF = PASS
XML2RFC_3_34_0_RENDER_VALIDATION = PASS
SCIENTIFIC_PDF = PASS (6 A4 pages)
CANONICAL_INTEGRITY = PASS
MAKE_TEST = PASS
AUTHORIZATION_BEHAVIOR = TEST_COVERED
EXTERNAL_AUTHORIZATION_MASTER_GATE_EXECUTION = NOT_CLAIMED
GITHUB_PUBLICATION = PENDING_AUTHORIZED_REMOTE_AUTOMATION
ZENODO_PUBLICATION = PENDING_AUTHORIZED_REMOTE_AUTOMATION
IETF_DATATRACKER_SUBMISSION = NOT_PERFORMED
```

The reproducible Python test command is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
  python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

The discovery pattern matches ten Python files. Nine contain the following 102
test cases; `tests/test_ietf_offline_render.py` is a command-line verifier
exercised separately with the locked renderer:

| Module | Tests |
|---|---:|
| API client | 4 |
| five-state effect protocol and conformance | 41 |
| handler security | 17 |
| handler unit behavior | 6 |
| repository-integrity generator | 1 |
| launcher and publication planner | 15 |
| license transition and exact official text | 5 |
| seed/import workflows | 12 |
| TCP/IP end-to-end adapter | 1 |

The strict ANSI-C90 test independently compares the implementation with an
oracle across all 2,621,440 valid abstract snapshots. Including its additional
release and conjunct checks, it performs 7,864,387 checks and passes.

## Additional local evidence

- The bounded collective-adaptive runtime remains fail closed. It emits
  reviewable evidence and proposals in `EFFECT_ACK_CONTINUE`; it cannot approve,
  merge, tag, release, publish, write to a network, or mutate its own policy.
- Automatic runtime acceleration is limited to reuse of an exact-key verified
  cache. Performance observations may produce a reviewable proposal; they do
  not autonomously reorder work or skip a mandatory gate.
- The POSIX bootstrap, cache-manipulation, cleanup, and platform-simulation
  tests pass. The PowerShell implementation has been checked statically but
  remains pending execution in Windows CI.
- The scientific finite-model proof passes with explicit limits: it does not
  prove a universal decoder, information recovery from non-injective
  observations, eventual DONE, or unconditional cyberphysical safety.
- The aggregate test gate regenerates the scientific proof report byte-for-byte,
  verifies the optimized-mode refusal, and requires complete SHA-256 coverage
  of the scientific bundle.
- Python 3.12.13 with `xml2rfc` 3.34.0 validates the Draft-01 XML and reproduces
  its clean TXT and HTML artifacts. No normative Draft-01 change is required.
- The adaptive-runtime CI contract executes that offline render comparison on
  Linux x64, macOS Intel, and Windows x64 pull requests.
- The associated scientific PDF has six A4 pages and passed local render and
  visual inspection.

The canonical integrity files are current for this snapshot, and the final
aggregate `make test` passes against them. Authorization behavior is covered by
local tests; this summary does not claim that a real externally authorized
publication master gate was run.

## External state

The two public repository heads above contain the same tree but have different
commit identities. The 2026-07-22 work in this summary has not yet been pushed,
merged, or tagged in either repository. The connected GitHub authorization and
the existing `ZENODO_ACCESS_TOKEN` Actions secret have been verified; GitHub
publication and Zenodo deposition remain pending execution by the bound remote
automation.

No IETF Datatracker submission has been performed or requested. The local
Draft-01 XML, TXT, and HTML validation is a preview and preservation step only.

Remote commits, tags, CI runs, Zenodo records and DOIs require separate remote
evidence after their authorized execution. They are outside this local result.

See `STATUS.md`, `EVIDENCE_BOUNDARY.md` in the scientific bundle, and
`HISTORICAL_ARTIFACT_BOUNDARIES.md` for the exact claim boundaries.
