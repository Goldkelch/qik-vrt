<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Governance

QIK-VRT is currently an author-led research project maintained by Ingolf
Lohmann through the `Goldkelch` repository account.

## Decision authority

The maintainer controls releases, merges, supported scope, policy versions,
security handling, licensing decisions, and the distinction between current
authority and retained historical material. Decisions should remain traceable
to a commit, issue, pull request, release, or other durable record.

## Change path

1. A proposed change identifies its scope, provenance, risk, tests, and claim
   boundary.
2. Automated and manual checks classify whether the change may continue.
3. Contributions require the separate written terms described in
   [CONTRIBUTING.md](CONTRIBUTING.md) before merge.
4. Only a reviewed, authorized change may enter `main` or a release.
5. A release records its commit, tag, integrity data, known limitations, and
   applicable licenses.

## Collective adaptive proposals

The bounded collective-adaptive process may measure repository state, bind
attributable observations by digest, preserve disagreement, and produce a
structured proposal. Its output is advisory evidence only. It may not modify
tracked content or external state and may not commit, push, merge, tag,
release, publish, deploy, change permissions, spawn a recursive agent process,
or alter its own policy or implementation.

Every proposal remains `EFFECT_ACK_CONTINUE` with ordinary release disabled.
Implementation requires the normal contribution path, all required checks,
provenance and rights review, security and scientific-claim review, explicit
approval by the responsible human and a separate, fresh, authenticated
`EFFECT_ACK_DONE`. Distinct observer identifiers, matching proposal content,
workflow success, and human review do not prove organizational or causal
independence, do not establish consensus, and do not individually or
collectively manufacture that protocol state.

Changes to `AGENTS.md`, the collective-adaptive policy, runtime, tests,
workflow, governance text, CODEOWNERS, or the pull-request effect boundary
require review by the designated code owner. No workflow may auto-approve or
auto-merge such a change.

Public feedback does not transfer copyright, create confidentiality, or force
acceptance. Governance may evolve if additional maintainers or an independent
technical body are formally appointed; any such change must be documented
prospectively.
