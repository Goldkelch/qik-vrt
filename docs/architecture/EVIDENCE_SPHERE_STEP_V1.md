<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Evidence sphere: first finite, witnessed growth step

Concept and task authorization: Ingolf Lohmann. Implementation and test drafting:
AI-assisted work. This review candidate does not assert native approval, merge,
deployment, publication, physical confirmation or general EFFECT_ACK_DONE.

## Reuse and deliberately narrow delta

The inspected base is Goldkelch/qik-vrt at
`b4b0038bcaa8788098ffa529bd5d5b651dd0459c`, tree
`11a27f5813f40b1b0447cac73c103b4323316779`.

`tools/qikvrt_real_mesh.py` already implements `AppendOnlyNodeLedger` and
canonical JSON/hash functions (base blob `a9944096c3583d885b5414c4e30f1404537b9e3e`).
The new adapter subclasses that ledger; it does not replace its wire format,
start a server, introduce another scheduler, or dispatch recursive workflows.
The requested-review ledger has a different subject and writer contract; it
is not silently repurposed. Existing publication/Lean sphere artifacts are not
runtime growth receipts. No claim is made that every remote branch was searched.

The added composition is:

`exact event -> local Git byte witness -> deterministic graph delta -> existing
Mesh append/fsync -> reopen/hash-chain and semantic replay -> growth receipt`.

## Admitted event and meaning

The v1 adapter accepts only `qikvrt_evidence_sphere_git_observation_v1` with exactly
`schema, repository, head, tree, path, blob, sha256, bytes`.
It rereads local Git objects, checks configured origin and the exact checked-out
head before and after observation, rejects symlinks/path traversal and checks
the actual Git blob hash and SHA-256. `GIT_NO_REPLACE_OBJECTS=1` is set. Blob size
is bounded at 16 MiB. No caller-supplied `approved`, `PASS`, truth flag or workflow
success boolean is admitted. The caller owns the checkout during the step.

The relation is **CONTAINS_OBSERVED_BLOB**. It means that these bytes were read
at this path in this exact local Git subject. Reading a JSON file containing a
kernel receipt does not reexecute Lean or prove the file's propositions. Configured
origin is not authenticated remote-ref readback. Those are separate obligations.

## Monotonicity, determinism and invalidation

The graph has content-addressed subject, artifact and contract nodes and typed,
observation-bound relations. Admission is set union: no prior node or edge is
removed. The root hashes the canonical graph and contract. The existing ledger
also carries its independent sequence, time and previous-record digest.

A growth receipt binds `old_root`, `delta_digest`, `new_root`, the exact event,
contract, implementation digest and added counts. Independent event order produces
the same graph root, but need not produce the same append-history digest. A repeated
exact event returns NOOP and changes no ledger byte. A tree-identical new commit
can add a **NEW_SUBJECT_OR_PATH_BINDING**, with zero new content objects. That is
not counted as new content knowledge and transfers no prior-head validation.

Monotonic history does not mean ever-increasing certainty or perpetual validity.
This first adapter has no semantic proof, measurement, contradiction or revocation
adapters. Later adapters must preserve old observations and append explicit
supersession/refutation relations, not promote historical claims to current truth.

## Local persistence and authority boundary

`step` requires an externally supplied expected graph root and explicit `--apply`.
The expected root is compared under a nonblocking POSIX file lock. Cooperating
concurrent writers return HOLD rather than poll. An admitted delta produces one
existing Mesh COMPLETED record; here COMPLETED names a **local graph append**,
not a scientific, publication or physical effect. Reopening the ledger verifies
both the hash chain and the deterministic semantic transition before readback is
reported. Missing/torn/conflicting records fail closed; no repair truncates them.

The storage directory and checkout must be trusted, locally owned POSIX storage.
This is not a hostile-filesystem, power-loss atomicity or distributed-consensus
proof. Preserve the expected root outside the replaceable ledger to detect whole
history rollback. A privileged writer can replace a local file and its checkpoint;
this code cannot confer protection against that authority. No GitHub credentials,
merge, review submission or publication APIs are used by the adapter.

## Invocation

```sh
python3 -B tools/qikvrt_evidence_sphere_step.py observe \
  --ledger /trusted/state/sphere.jsonl --head "$(git rev-parse HEAD)" --path AI > event.json
python3 -B tools/qikvrt_evidence_sphere_step.py inspect --ledger /trusted/state/sphere.jsonl
# Supply the independently retained root from inspect/the previous receipt:
python3 -B tools/qikvrt_evidence_sphere_step.py step --ledger /trusted/state/sphere.jsonl \
  --event event.json --expected-root 'sha256:<64 hex>' --apply
python3 -B -m unittest discover -s tests -p test_qikvrt_evidence_sphere_step.py -v
```

The returned next action is `AWAIT_NEW_EVENT` after a reobserved append or NOOP;
HOLD retains `REOBSERVE`. This is a finite executor, not an autonomous scheduler.
A live event producer and a reviewed persistent hosting/writer policy remain a
separate activation task; no permanent motor service is preclaimed here.

## Executable witness, not illustrative counts

`demo --apply` creates a new ledger, observes `AI`, `src/effect_ack_core.c` and the
QCE receipt file, replays the final observation, then injects an invalid digest.
It asserts real append/readback, byte-preserving NOOP, and HOLD without growth.
All reported roots and counts are computed, not supplied as example numbers.

The initial, narrowly scoped GitHub transport reuses the existing integrity
materializer and `make test`, records a first growth ledger for the exact observed
base in `state/evidence-sphere/first-growth-v1`, and removes its own workflow before
creating and testing the successor. It exists because this connector exposes no
workflow-dispatch action and the existing integrity workflow has a fixed push
branch list. No main writer, existing PR or publication path is replaced.
The retained tests run through ordinary repository test discovery. Historical
first-growth receipts never validate a successor code head.
