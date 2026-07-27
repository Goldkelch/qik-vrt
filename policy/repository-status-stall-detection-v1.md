# QIK-VRT Repository Status and Stall-Detection Policy v1

Status: normative repository policy
Authority repository: `Goldkelch/qik-vrt`
Mirror repository: `ingolf-lohmann/qik-vrt`

## Purpose

Every repository-status inspection must distinguish real progress from mere activity and must explicitly detect and report a stall relative to the immediately preceding verified observation.

## Mandatory observation scope

At minimum, inspect and compare:

- tracked issues and pull requests;
- associated branches and head/base SHAs;
- new commits and material changes;
- issue, PR, review and bot comments;
- GitHub Actions workflow runs, jobs, steps, conclusions and artifacts;
- required checks and mandatory gates;
- claim inventory state;
- Lean-kernel receipts and proof-object evidence;
- traceability and provenance bindings;
- Authority/Mirror content equality and synchronization evidence.

## Allowed report categories

Every report must use exactly one primary category:

1. `Auftrag angenommen`
2. `Arbeit begonnen`
3. `Teilfortschritt`
4. `Blocker`
5. `Stillstand`
6. `vollständig kernel-verifizierter Abschluss`

## Stall rule

`Stillstand` is mandatory when no new, content-relevant reaction or status progress exists compared with the previous verified observation.

A stall report must state:

- that no content-relevant change was found;
- the compared previous observation or baseline;
- the inspected objects;
- the reason no observed activity qualifies as progress;
- any continuing blocker that explains the stall.

Routine bot noise, repeated comments, identical workflow reruns, unchanged `action_required`, unchanged failures, unchanged branch heads and metadata-only updates do not constitute progress.

## Progress rule

A report may classify `Arbeit begonnen` or `Teilfortschritt` only when new evidence changes the technical, scientific, verification or synchronization state. The report must identify the exact object, SHA, run, receipt or artifact that changed.

## Fail-closed completion rule

No report may claim `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE` or `vollständig kernel-verifizierter Abschluss` unless all of the following are simultaneously evidenced and bound to the exact candidate:

- complete claim inventory;
- native Lean-kernel receipts for every formally proved claim;
- complete source-to-claim-to-proof traceability;
- green mandatory repository gates on the exact head;
- verified Authority/Mirror synchronization and content equality.

Required invariants:

- `NO_COMPLETE_CLAIM_INVENTORY_NO_FINAL_PASS`
- `NO_KERNEL_RECEIPT_NO_FORMAL_PROOF`
- `NO_TRACEABILITY_NO_FINAL_PASS`
- `NO_GREEN_MANDATORY_GATES_NO_FINAL_PASS`
- `NO_AUTHORITY_MIRROR_EQUALITY_NO_FINAL_PASS`
- `NO_BASELINE_COMPARISON_NO_STALL_DECISION`

## Reporting contract

A status response must include:

- primary category;
- relevant change: yes/no;
- stall: yes/no;
- concise evidence;
- explicit reasoning;
- completion-gate state.

When there is no relevant change, silence is forbidden: the response must explicitly report `Stillstand` and its reason.

## Repository architecture priority

This policy is intended to be consumed by repository-native workflows and issue-agent logic. Future automation should persist each observation as a machine-readable snapshot, compare it with the prior snapshot, and derive the category deterministically before emitting a human-readable report.
