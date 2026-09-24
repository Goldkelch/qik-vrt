# TEMDD Main Loop V1

Status: normative candidate. Owner: Ingolf Lohmann.

The C90 formulation is generalized without changing its semantics:

```text
main()
  forever:
    COMPILE
    BIND
    RESOLVE
    EXECUTE
    TEST
    OBSERVE
    READBACK
    ACCEPT
    if all eight are true:
        EFFECT_ACK_DONE(subject_n)
        bind(observed_successor) -> subject_(n+1)
        continue
```

`EFFECT_ACK_DONE(subject_n)` terminates the evidence-bound transition of one
subject. It does **not** terminate the outer runtime.

```text
EXECUTE != DONE
TEST != DONE
OBSERVE != DONE
EFFECT_ACK_DONE(subject_n) != PROGRAM_DONE
PREDECESSOR_EVIDENCE_TRANSFER = false
```

The test harnesses are intentionally finite. A finite harness proves the
transition relation; it does not redefine the production `main()` as finite.

Canonical machine contract:
`spec/temdd/TEMDD_MAIN_LOOP_V1.json`.

Carriers:
- Python reference: `runtime/temdd/main_loop.py`
- Rust runtime: `next/crates/qikvrt/src/temdd_main_loop.rs`
- Smalltalk: `runtime/temdd/TEMDDMainLoop.st`
- MC68000: `runtime/m68000/temdd_main_loop.s`
- Ada/SPARK: `next/reference/full-core-draft03/ada/temdd_main_loop.ads`
- Lean: `next/reference/full-core-draft03/TEMDDMainLoop.lean`
- VHDL-2008: `hardware/vhdl/qikvrt_temdd_main_loop.vhd`
