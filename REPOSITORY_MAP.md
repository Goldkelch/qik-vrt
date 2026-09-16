# QIK-VRT Repository Mesh Map

This is the shortest safe navigation map for humans and artificial-cognitive clients. Repository evidence is canonical; chat, memory, timestamps, workflow badges and predecessor commits are not authority.

## 0. First rule

Start at `/AI`, then use this map. Never infer a later state from an earlier successful state.

`TRANSPORT_ACK != EFFECT_ACK`

`LOCAL_NOOP != REPOSITORY_NOOP != EFFECT_ACK_DONE`

A head mutation resets successor-local validation/review obligations. Equal trees under different commits do not transfer evidence. A zero-job or `action_required` workflow is not a successful gate.

## 1. Mesh roles

- **Authority:** `Goldkelch/qik-vrt`, canonical integration target `main`.
- **Mirror / administrative counterpart:** `ingolf-lohmann/qik-vrt`; it is not evidence-equivalent merely because content resembles Authority.
- **Candidate:** a PR head identified by literal commit SHA and tree SHA.
- **Runtime / carrier nodes:** workflows, Firefox/HTTP/SSE terminal, Cloud-Transputer/M68000 paths and other execution carriers. Their receipts prove only the scope they actually observe.

## 2. Causal release path

```text
P0  manifest / contract
 ↓
P1  one integration candidate HEAD/TREE
 ↓
P2  fresh exact-head validation
 ↓
P3  native exact-head authority / Code-Owner review
 ↓
P4  fresh post-review reobservation of the same head
 ↓
P5  legitimate promotion to Authority main
 ↓
P6  fresh exact-Main reobservation
 ↓
P7  separately authorized external obligations / publication
 ↓
REAL EFFECT READBACK where the task requires it
```

Never skip an arrow. Never use evidence from a predecessor head to satisfy a successor stage.

## 3. Repository control plane

| Need | Canonical starting point |
|---|---|
| AI/bootstrap semantics | `/AI`, `AI_CONTEXT.json`, `tools/ai_runtime_bootloader.py` |
| Policies and invariants | `policy/` |
| Durable state / authorization / work units | `state/` |
| Executable controllers | `tools/` |
| GitHub event/execution carriers | `.github/workflows/` |
| Regression and contract tests | `tests/` |
| Evidence and receipts | `evidence/` |
| Runtime/public terminal material | `.well-known/`, runtime-specific directories, publication surfaces |
| Human-readable architecture/protocol | `docs/` |
| Canonical repository integrity | `REPOSITORY_FILE_MANIFEST.json`, `REPOSITORY_FILE_MANIFEST.json.sha256`, `SHA256SUMS.txt` |

## 4. Monitor pattern — event driven, not polling

The persistent monitor surface already exists:

- `.github/workflows/qikvrt_live_status_watch.yml`
- `.github/workflows/qikvrt_event_driven_continuation.yml` when present on the candidate/current line
- `.github/workflows/qikvrt_workflow_executor.yml`
- `.github/workflows/qikvrt_workflow_executor_watchdog.yml`
- `tools/qikvrt_workflow_executor.py`
- `state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json`

`qikvrt_live_status_watch.yml` consumes repository events such as PR changes, submitted/edited/dismissed reviews, PR comments and selected `workflow_run` transitions. It projects each causal event into an append-only bounded PR journal marked:

`<!-- qikvrt-universal-terminal-live-surface-v1 -->`

The surface is a projection, not a gate. `OBSERVE`, `CLASSIFY`, `READBACK` and `EFFECT` labels must still be interpreted under exact-subject contracts. In particular, a workflow surface called `EFFECT` does not by itself establish global `EFFECT_ACK_DONE`.

## 5. Autonomous continuation

Repository-native continuation is split deliberately:

1. **Observe an event.**
2. **Rebind the literal PR/head.**
3. **Reject head drift.**
4. **Wake only an allowlisted trusted executor.**
5. **Reobserve the result.**
6. **Persist a successor only when productive bytes actually changed.**
7. **Run fresh successor-local validation.**

No polling belongs in the repository core. Scheduling, where required, is an outer-layer carrier and must not be confused with causal repository continuation.

## 6. Evidence taxonomy

- **Source present:** bytes exist. No execution claim.
- **Executed:** a job/process actually ran. No correctness claim beyond its observation.
- **Gate success:** the applicable check succeeded on the literal subject it checked.
- **Review:** must be a native review bound to the required exact commit and identity/authority contract.
- **Materialization:** generated worktree bytes exist. This is not persistence.
- **Persistence:** changed bytes were committed to an exact successor. Predecessor validation does not transfer.
- **Main:** only Authority `main` after legitimate promotion.
- **Effect:** only an independently read-back external/runtime effect in the scope asserted.

## 7. Fastest verified working method

```text
OBSERVE current literal HEAD/TREE
  → identify FIRST deterministic blocker
  → reuse existing controller/workflow before creating another
  → make the smallest productive repair
  → persist one bounded successor
  → RESET successor-local P2+
  → run independent gates in parallel where causally independent
  → serialize only dependent P2 → P3 → P4 → P5 transitions
  → reobserve after every authority/effect boundary
```

Prefer `REUSE_BEFORE_CREATE` and `FASTEST_VERIFIED_PATH`. Do not create marker commits, empty retriggers, synthetic approvals or duplicate monitors.

## 8. How to classify a PR

For every open PR determine, from its current literal head:

- what productive delta belongs to this candidate;
- what is inherited branch history;
- current HEAD/TREE/PARENT/base;
- first deterministic failing gate;
- submitted native reviews and their `commit_id`;
- requested reviewers separately from submitted reviews;
- whether materialization was persisted;
- whether any runtime/effect receipt is independently read back.

Then classify it as one of `MERGE`, `SUPERSEDE`, `CLOSE_AS_REDUNDANT`, or `REJECT_WITH_EVIDENCE` only when evidence supports that disposition. Do not ignore an open PR.

## 9. How to classify a branch

Every non-Main branch must eventually be regarded against current Authority Main as `MERGED`, `SUPERSEDED`, `REDUNDANT`, or otherwise explicitly evidence-blocked. Branch existence is not progress and branch age is not causality.

## 10. Definition-of-Done guard

Do not say DONE merely because one PR is green. Repository completion requires, at minimum, all target-relevant gates green, no known productive bug cause, all PRs and branches regarded, required review/authority effects established, exact-Main reobservation, and every required runtime/publication effect independently read back.

When uncertain: **HOLD_UNVERIFIED**, identify the missing observation, and continue on the smallest admissible causal edge.
