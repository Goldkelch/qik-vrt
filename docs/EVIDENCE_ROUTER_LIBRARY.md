<!-- Copyright 2026 Ingolf Lohmann. SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Evidence Router: standalone library candidate 0.1.0

This is the bounded routing core of phase C in
`QIKVRT_THREE_PHASE_MESH_SEED_MVP_V1`, not a completed three-phase Mesh.
It can be copied independently of QIK-VRT and run without pip, credentials,
Firefox, a cloud service, a model, a compiler, or third-party Python modules.
It requires Python 3.10+ with the standard-library `sqlite3` module.
The delivered receipt records the Python version actually exercised.

## Transfer and instantiate

Copy `src/qikvrt_evidence_router.py`, the test file, this document, and the
example, preserving the shown directories. Preserve the repository license
notices and license texts. A source ZIP is sufficient; installation is not
required. From its extracted root:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B examples/evidence_router_sieve.py \
  --head YOUR_EXACT_40_HEX_HEAD --tree YOUR_EXACT_40_HEX_TREE \
  --directory /tmp/router-new-instance
```

The directory must not already exist. The example produces ten primes below
31 with a sieve, independently checks this payload with trial division, reads
local fixture files, selects two edges, commits a receipt, and reads it back.
It is deliberately labelled `LOCAL_FIXTURE_ONLY`. Supplying Git hashes to the
example does not turn its fixture files into live GitHub or deployment evidence.

Import the library directly from the supplied source directory:

```python
import sys
sys.path.insert(0, "src")
from qikvrt_evidence_router import Router, Subject, Relation, ReceiptJournal
```

Construct a `Subject(repository, head, tree)` and explicit `Relation` objects.
Supply an observer implementing `read_subject()` and
`read_relation(relation, challenge) -> Observation`, plus a semantic validator
`validator(relation, payload_bytes) -> bool`. The caller supplies these adapters;
there is no hidden network access. The sieve example is a complete working
adapter, not a production evidence source.

## What a decision means

`Router.route(source, target)` reobserves the exact subject, validates the
address, identity, invocation challenge and SHA-256 of each observed receipt,
runs the semantic validator, and selects a minimum-cost validated route in the
observed graph. It then rereads every selected relation, rereads the subject,
appends a receipt transaction, reads the committed record through a new database
connection, and checks the subject once more before returning a `Decision`.

Relation identities, addresses, every selected underlying relation, complete
declared provenance, exact HEAD/TREE, validator/observer identifiers, rejected
edge reasons and invocation challenge remain in the receipt. A shorter route
must carry its own freshly validated receipt: A->B and B->C never manufacture
an evidence assertion A->C. Costs are calculated from immutable relations,
not trusted candidate totals. Ties are deterministic. Zero-cost cycles are
bounded; an empty route is not successful work.

The graph contains at most 256 supplied edges; payloads and journal records are
limited to 1 MiB; journals to 10,000 rows. These are candidate bounds, not a
production scale claim. Selection minimizes traversal cost, not the number of
validation reads. Candidate validity is recomputed on every invocation; no
previous decision or `valid=True` cache is accepted as current evidence.

## Trust, persistence and limits

The observer must genuinely read the intended source. The validator must check
all semantic/proof/provenance requirements of its application. This core checks
and preserves declared provenance identifiers; it does not resolve arbitrary
provenance URLs or verify mathematical proofs. An adapter that lies about
freshness is not made trustworthy by echoing a challenge. Distinct identifier
strings do not prove independent observers. There is no global atomic snapshot
of multiple remote services and no guarantee of validity after the final read.

SQLite transactions serialize writers. The library exposes append/read/verify,
not update/delete. Its hash chain is not a signature, an authorization proof,
or tamper-proof storage. Privileged database edits remain possible; externally
retain a receipt digest and call `verify(expected_tip)` to detect tip drift or
rollback. Back up or rotate a journal through a separately designed process
before reaching its bound; this candidate does not silently truncate it.

A subject drift before persistence produces no success receipt. Drift detected
after persistence returns HOLD but leaves the old decision addressable as
history. A `Decision` and a stored `ROUTE_VALIDATED` receipt are historical
records, not renewable admission tokens. Call `route()` again for fresh checks.
No route is automatically traversed by dispatching external work.

The caller owns the supplied scratch/database paths and must enforce filesystem
permissions. This library does not provide a hostile-filesystem sandbox,
remote attestation, an approval system, a production GitHub adapter or service
availability guarantees. Adapter deadlines belong to the invoking runtime.

## Scope and ancestry

The implementation reuses the `Relation`, `CandidateRoute`, composition and
non-transitive-evidence design inspected in PR #1096, with a new typed subject,
readback and persistence boundary. It imports no source-branch test result or
old evidence. #1110 supplies the three-phase contract. Tests using fixed hashes
are fixtures; they are not GitHub validation receipts for those hashes.

Repository integrity remains owned by `tools/qikvrt_integrity.py`. This source
slice neither edits nor bypasses that gate. Integration must regenerate and
persist the canonical manifest and hashes, read the resulting HEAD/TREE, and
run fresh repository-wide P2. The source binding and test report for a delivery
are generated outside the committed source to avoid a self-referential
HEAD-in-its-own-tree claim.

Not established by this library: complete phase C production integration,
Terminal/Firefox interaction, Transputer guest execution, the closed three-edge
seed cycle, full P2, native Code-Owner review, Main promotion, deployment,
publication, or `EFFECT_ACK_DONE`.

Source software retains PolyForm-Noncommercial-1.0.0; this document retains
CC-BY-NC-ND-4.0. This candidate does not relicense the repository implementation.
