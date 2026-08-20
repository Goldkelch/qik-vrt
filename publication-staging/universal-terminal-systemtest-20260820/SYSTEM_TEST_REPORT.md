# QIK-VRT Universal Terminal - System Test and Integration Report

Date: 2026-08-20
Repository: Goldkelch/qik-vrt
Source PR: 737 (closed unmerged after supersession)
Trusted carrier PR: 738 (merged)
Trusted carrier head: 4788de28eb3ea49b163be594fafc51f7f3406976
Integrated merge commit: fbcced967a205573b85cc457959ca3527f92ff99
Integrated tree: 00b5754b6ee8cd8a5c66194dca559207cff256e5

## Scope

The tested work unit implements the Firefox-based QIK-VRT Universal Terminal send/receive surface and its repository-wide continuation bindings. The terminal accepts schema-valid information envelopes without treating claimed temporal relation, sender identity, or destination identity as a receipt/display blocker. Temporal relation values include PAST, PRESENT, FUTURE, UNKNOWN, and UNBOUND. Source and destination values may remain opaque or unknown. These values are preserved rather than erased.

The implementation keeps the mandatory distinction boundaries: received is not trusted; displayed is not authorized; stored is not executed; forwarded is not effect-acknowledged; transport acknowledgement is not effect acknowledgement; causality is not sequence. A FUTURE label is observer/context metadata and does not by itself establish physical signalling into a causal past.

## Recovery and exact-tree verification

The repository-native integrity materializer produced source materialization head 7241a45947b457cc700bd258212bcce0ddf06fff with tree 00b5754b6ee8cd8a5c66194dca559207cff256e5. Direct workflows on that bot-authored head terminated as action_required before job execution.

A history-preserving exact-tree carrier was therefore created. Carrier head 4788de28eb3ea49b163be594fafc51f7f3406976 has the same tree 00b5754b6ee8cd8a5c66194dca559207cff256e5. The carrier changes no candidate bytes.

## Exact-head workflow results

On carrier head 4788de28eb3ea49b163be594fafc51f7f3406976, QIKVRT CI run 5796, Collective Proposal Review run 2148, global claim completion run 1296, EFFECT_ACK HTTP Firefox terminal run 43, universal terminal continuation run 12, terminal continuation rollout run 12, adaptive stacked successor integrity materialization run 137, and code-owner review observer run 465 completed successfully.

After transition to review-ready state, continuation, rollout, observer, and requested-review workflows were re-triggered and also completed successfully. No independent code-owner approval is claimed in this report.

The Firefox E2E workflow completed contract parsing, RFCXML rendering, Python syntax checking, Firefox JavaScript syntax checking, HTTP terminal contract and E2E tests, verified Firefox reference-client packaging, and artifact preservation successfully.

The global completion workflow completed canonical repository integrity verification before the full suite, the complete mandatory repository suite, and integrity re-verification after the full suite successfully.

## Integration result

Trusted carrier PR 738 was merged with expected-head binding to 4788de28eb3ea49b163be594fafc51f7f3406976. GitHub produced signed merge commit fbcced967a205573b85cc457959ca3527f92ff99. The merge commit preserves tree 00b5754b6ee8cd8a5c66194dca559207cff256e5, establishing byte identity with the tested exact-tree candidate.

Source PR 737 was then closed unmerged as superseded by the trusted exact-tree promotion path.

## System-test disposition

For the tested repository scope, the Universal Terminal implementation is integrated into its intended stack base with a tested, exact-tree-preserving history. The report does not claim repository-wide PASS, FINAL_PASS, EFFECT_ACK_DONE, physical retrocausal signalling, release, deployment, Zenodo publication, IETF publication, or arXiv acceptance.

## Publication boundary

External publication is a separate effect. Repository policy requires an exact artifact hash plus subsequent natural-person authorization before Zenodo creation/upload/publication or other external publication effects may be executed. The exact publication artifacts and hashes are frozen by PUBLICATION_FREEZE_MANIFEST.json in this work unit.