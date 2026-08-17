# Bounded Elastic Resource Delegation

QIK-VRT may consume environment-provided compute elastically to reduce wall-clock latency, but only where parallel execution is semantically safe.

The invariant is simple: observation may fan out; productive mutation remains serialized.

The repository-native implementation is `.github/workflows/qikvrt_bounded_elastic_observers.yml`. A deterministic planner partitions independent read-only work across up to eight observer lanes. GitHub's scheduler remains the authority for actual runner availability: a requested lane may queue rather than execute immediately, and queueing is not treated as a correctness failure.

Parallel lanes may inspect repository state, workflows, integrity, terminal contracts, Effect-ACK conformance, mesh contracts and caches. Each lane binds its exact Git head and tree and emits a receipt. The reducer succeeds only when every lane succeeds. A successful lane can never mask another failed gate.

The delegation does not authorize credential or permission escalation, platform-quota bypass, use of unauthorised third-party systems, force updates, competing productive writers, merge, release, deployment, publication or another external effect. Cached data accelerates computation but is never proof authority.

Repository-content writes, branch/ref mutation, pull-request mutation and all consequential effects remain under the existing single-writer, lease, exact-head, integrity, review and Effect-ACK contracts.

The policy authority is `state/autonomy/BOUNDED_ELASTIC_RESOURCE_DELEGATION_V1.json`; the deterministic planner is `tools/qikvrt_elastic_resource_planner.py`; structural regression coverage is `tests/test_qikvrt_bounded_elastic_resource_delegation.py`.
