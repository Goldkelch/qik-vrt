# TEMDD v0.1 IDE Contract

Status: BOOTSTRAP_CONFORMANT_UI

The TEMDD IDE is the editable local-analysis surface embedded in the Universal Terminal. It preserves the same fail-closed language boundary as the reference parser.

## Required behavior

- edit TEMDD v0.1 source in the browser;
- load the repository-bound reference program;
- derive local typed diagnostic IR for version, authority, exact subject, request, handlers and DoD;
- reject unsupported versions, missing exact binding, duplicate DoD predicates and incomplete `QIKVRT_DOD`;
- keep local analysis distinct from execution and effects;
- never POST TEMDD events from the browser editor;
- native execution remains behind repository/runtime admission and fresh Effect-Ack readback;
- copying source or IR is transport only: `TRANSPORT_ACK != EFFECT_ACK`.

This UI contract does not claim Main adoption, production extension delivery, repository-wide PASS, FINAL_PASS or EFFECT_ACK_DONE.
