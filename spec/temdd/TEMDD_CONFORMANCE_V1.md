# TEMDD v1 Conformance

TEMDD v1 conformance is an exact-subject candidate property. It is not native
review, Main promotion, deployment acceptance or general Effect-Acknowledgment.

A PASS report is emitted only when the separated runner:

1. binds a clean exact HEAD/TREE;
2. invokes the v1 IR adapter through a process boundary;
3. accepts the positive corpus and rejects every negative case;
4. checks T13 causal binding, T14 evidence non-transfer and T15 Effect-Ack construction;
5. checks the v1 Event/Evidence IR schemas and exact-subject report schema;
6. verifies the five-view IDE contract without granting browser effect authority;
7. executes parser, semantic-IR and persistent-ledger/browser regressions;
8. observes a same-HEAD/TREE backend receipt covering C90, Smalltalk,
   M68000 under QEMU and Lean/Lake;
9. binds the formal theorem source compiled by that receipt;
10. hashes implementation and suite inventories and emits
    `temdd_conformance_report_v1`.

Any HEAD/TREE mutation invalidates the report and requires a fresh run.

`PREDECESSOR_EVIDENCE_TRANSFER = false`.

`TEMDD_V1_CONFORMANCE_PASS != P3 != MAIN != EFFECT_ACK_DONE`.
