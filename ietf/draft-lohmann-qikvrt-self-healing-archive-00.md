# draft-lohmann-qikvrt-self-healing-archive-00

## Status

Individual Internet-Draft candidate. Repository text only. Not submitted to the IETF Datatracker and not an IETF standard.

## Abstract

This document defines an interoperable receipt model for bounded autonomous repair of versioned archives. It separates failure observation, repair intent, execution capability, exact-state binding, verification and external effects.

## 1. Requirements language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY and OPTIONAL are to be interpreted as described by BCP 14 when, and only when, they appear in all capitals.

## 2. Receipt model

A repair receipt MUST contain:

- `receipt_id`;
- `repository_id`;
- `observed_head` and `observed_tree`;
- `failure_class` and deterministic `failure_signature`;
- `repair_rule_id`;
- `changed_path_allowlist`;
- `execution_attempt` and retry budget;
- `successor_head` and `successor_tree`, when produced;
- terminal gate results;
- external-effect flags;
- cryptographic digests for every bound object;
- a completion boundary that forbids unsupported success claims.

## 3. Safety

An implementation MUST fail closed when the observed state does not match the receipt preconditions. It MUST NOT force-update protected history, broaden credentials, disclose secrets, or perform a public external effect merely because a repository-local repair is authorized.

## 4. Replay and race resistance

A repair intent MUST bind the exact observed head and failure signature. Reuse against another head MUST be rejected. A non-fast-forward race SHOULD be resolved by reobservation and a history-preserving successor rather than force.

## 5. Failure taxonomy

Initial interoperable values are:

- `transient_runner_or_network_failure`;
- `stale_generated_integrity`;
- `stale_repository_projection`;
- `non_fast_forward_materialization_race`;
- `base_lease_drift`;
- `missing_optional_runtime_component`;
- `substantive_test_or_claim_regression`;
- `external_effect_unavailable_or_unauthorized`.

Unknown values MUST remain unresolved unless an explicitly installed extension defines their semantics.

## 6. Security considerations

Self-healing mechanisms are privileged automation. Implementations MUST minimize token scope, prevent untrusted repository text from becoming executable authority, cap retries, preserve attributable logs, and distinguish repository success from publication or deployment success.

## 7. IANA considerations

This candidate requests no IANA action.
