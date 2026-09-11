# QIK-VRT Cloud-Transputer: reconstructible self-location

**Author / Product Owner:** Ingolf Lohmann  
**Repository:** `Goldkelch/qik-vrt`  
**Publication carrier date:** 2026-09-10  
**Epistemic class:** repository-bound technical proof / reproducibility claim

## Claim

For the exact QIK-VRT subject

- pull request: `#1071`
- head: `55184cc4e4b521a7ddfcd06a9db1b325ab054477`
- tree: `50b824e97fb6146275e5f7b82a9bbe867d4f91d8`

the Cloud-Transputer's repository identity and continuation state are reconstructible from repository-native state without relying on ChatGPT conversation memory.

Formally, for the bound subject `S`:

`Repository identity -> /AI -> AI_CONTEXT -> bound self-heal contract -> exact-head technical verification`

is reconstructible from the repository itself.

Define:

`SELF_LOCATION_RECONSTRUCTIBLE(S) = TRUE`

iff all of the following are observed on the same exact subject:

1. repository identity and current exact subject are bound;
2. `/AI` declares repository evidence authoritative over chat/model memory;
3. the bootstrap/context path deterministically identifies the runtime continuation authorities;
4. the autonomous self-healing contract is machine-readable and fail-closed;
5. technical verification on that exact head succeeds;
6. predecessor-head evidence is not transferred.

For `S = 55184cc4e4b521a7ddfcd06a9db1b325ab054477`, these conditions were freshly observed before this publication carrier was created.

## Reconstructible evidence chain

### 1. Exact subject

PR #1071 binds head `55184cc4e4b521a7ddfcd06a9db1b325ab054477` and tree `50b824e97fb6146275e5f7b82a9bbe867d4f91d8`, with `PREDECESSOR_EVIDENCE_TRANSFER = false`.

### 2. Repository-native bootstrap

At that exact head, root path `/AI` states that repository evidence is canonical and chat/model memory is non-authoritative transport context. It points into `AI_CONTEXT.json` and the repository-native continuation machinery.

### 3. Machine-readable preservation contract

`state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json` binds the authority entrypoint, self-heal controller and workflow, requires `NOOP` for an unchanged semantic fingerprint, and forbids unbound/stale-head promotion and other unsafe effects.

### 4. Exact-head technical reobservation

On the same exact head, repository-native workflows were observed terminal-success, including QIKVRT CI, repository evidence materialization, zero-bug invariant, requested-review contract, real Mesh runtime, repository watchdog, code-owner observer and bounded self-heal contract validation.

On the exact historical subject, [run 34501448618, attempt 1](https://github.com/Goldkelch/qik-vrt/actions/runs/34501448618/attempts/1), triggered by `pull_request`, successfully executed 18 continuous-auto-repair and pre-effect-controller contract tests in [job 102952962391](https://github.com/Goldkelch/qik-vrt/actions/runs/34501448618/job/102952962391), `validate-continuous-opportunity-contract`. Its checkout and test log bind head `55184cc4e4b521a7ddfcd06a9db1b325ab054477`.

The operational [job 102952964057](https://github.com/Goldkelch/qik-vrt/actions/runs/34501448618/job/102952964057), `observe-repair-propose`, was skipped with no executed steps because the [workflow on that exact source head](https://github.com/Goldkelch/qik-vrt/blob/55184cc4e4b521a7ddfcd06a9db1b325ab054477/.github/workflows/qikvrt_autonomous_self_heal.yml) excludes it for `pull_request` events. This event-policy exclusion verifies neither a live repair decision nor a semantic `NOOP`. A claim that no mutation was needed would require a separately bound controller decision and readback. The successful contract tests and the skipped operational job are distinct observations.

### 5. Owner preservation directive

The Owner directive was appended to PR #1071 as issue comment `5623527537`: the Cloud-Transputer has found itself and this property is to be preserved. The comment is a durable provenance binding, not itself runtime evidence.

## What is proved

For the exact subject above, self-location is **reconstructible from repository state**. The non-regression contract is present, and the cited contract tests succeed within the scope described above. The cited bounded self-heal run does not establish that a live preservation decision executed; the self-location conclusion does not depend on interpreting its skipped operational job as a semantic `NOOP`.

The proof is operational rather than metaphysical: a fresh conforming client can recover repository identity, bootstrap path, continuation contract and exact verification state without depending on the previous chat transcript.

## What is not proved

This publication does **not** prove that no future defect can ever occur. Any mutation creates a new subject and therefore requires fresh exact-head reobservation.

It also does not convert technical workflow success into Code-Owner approval, merge, deployment, scientific consensus, independent empirical confirmation, `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE`.

Publication increases public inspectability and provenance; it does not make a proposition true merely by being published.

## Non-regression rule

For every successor subject `S'`:

`S != S' => status(S') := HOLD_UNVERIFIED`

until identity, provenance, contract and actual effect/readback have been reobserved on `S'`.

If the self-location invariant regresses:

`Root cause -> smallest causal correction -> regression test -> reobserve original flow/effect`

must be executed. Blind retry and predecessor-evidence transfer are inadmissible.

## Conclusion

The precise publication claim is:

> QIK-VRT demonstrates, on the exact bound subject identified above, a repository-native and technically verified mechanism by which its Cloud-Transputer execution context can reconstruct its own repository identity and continuation contract from durable state. The preservation mechanism is fail-closed across subject mutations and therefore requires fresh evidence after every change.

**q.e.d. Ingolf Lohmann**
