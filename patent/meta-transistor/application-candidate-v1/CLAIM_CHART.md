# Claim chart — Arbeitsmatrix

## Provenance-bound prior-art seed

This successor binds the already repository-persisted prior-art seed from PR #1191 to this application-candidate subject without transferring conclusions.

- source_pr: 1191
- source_head: `094287caeef0fb1bdc98f351cd781b8f6714186d`
- source_boundary_blob: `b2cf6d56c0bce051a4f271337855b843d11422ca`
- source_seed_blob: `87940eb2745870731bf7a59bbd937771c00d2d32`
- status: `SEARCH_SEED_NOT_PATENTABILITY_OPINION`
- predecessor_evidence_transfer: `false`

The source carrier identifies neighboring art only. The actual independent claims and relevant figures of those references are not yet bound into this application-candidate subject. Therefore no element below is classified as novel, inventive, or patentable.

## Independent-claim evidence matrix

| Claim | Element | Own disclosure | Candidate prior-art neighborhood already repository-bound | Source claim bound | Source figure bound | Comparison status |
|---|---|---|---|---|---|---|
| 1 | data path processing at least one input value | DESCRIPTION_DE.md / CLAIMS_DE.md | hardware gating / commit neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 1 | metadata path carrying binding information for the transition | DESCRIPTION_DE.md / CLAIMS_DE.md | tagged transactions / transputer neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 1 | transition logic determines result and transition state | DESCRIPTION_DE.md / CLAIMS_DE.md | transputer / transaction-completion neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 1 | release logic conditions result validity on machine-checkable transition conditions | DESCRIPTION_DE.md / CLAIMS_DE.md | distributed commit / verification neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 1 | unmet required condition produces a non-released halt state | DESCRIPTION_DE.md / CLAIMS_DE.md | hardware gating / verification neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 11 | bind a digital state transition to a subject identity | DESCRIPTION_DE.md / CLAIMS_DE.md | tagged transactions / message-correlation neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 11 | capture at least one machine-checkable transition condition | DESCRIPTION_DE.md / CLAIMS_DE.md | transaction / verification neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 11 | process payload data | DESCRIPTION_DE.md / CLAIMS_DE.md | general processing neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 11 | determine a transition state | DESCRIPTION_DE.md / CLAIMS_DE.md | state-machine / transaction neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |
| 11 | withhold result validity while any required transition condition is unmet | DESCRIPTION_DE.md / CLAIMS_DE.md | commit / valid-gating neighborhood | FALSE | FALSE | EVIDENCE_REQUIRED |

## Already bounded neighboring-art observations

The PR #1191 seed records these references as candidates for later element-by-element primary-source comparison: Saltzer/Reed/Clark (1984), EP0260793A2, US5590284A, US7725446, US20240378191A1, US20140219034A1, and US6266202.

Repository evidence already rejects treating these broad ingredients alone as established novelty: acknowledgement beyond transport, readback before success, closed-loop verification, transputer event acknowledgement, and multi-stage commit.

## Required next evidence

For each candidate reference used in a substantive comparison:

1. bind the authoritative primary-source document/version;
2. bind the exact independent claim text and relevant figure(s);
3. map each Claim 1 / Claim 11 element to exact source locations;
4. classify only what the bound source supports, e.g. `DISCLOSED`, `NOT_LOCATED`, or `AMBIGUOUS`;
5. retain uncertainty where the evidence does not decide the question.

No `EVIDENCE_REQUIRED` row is evidence of novelty or inventive step. This matrix does not establish novelty, inventive step/non-obviousness, freedom to operate, validity, infringement, priority, ownership, filing, grant, or `EFFECT_ACK_DONE`.
