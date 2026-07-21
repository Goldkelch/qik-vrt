<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Two-minute demonstration script

## 0:00–0:15 — Problem

Show the repository and fixed release.

> A network acknowledgement or completed program says that data arrived or a
> computation ended. It does not say whether the resulting real-world effect
> is responsibly authorized.

## 0:15–0:35 — Five states

Show `EffectState` in `src/qikvrt_effect_ack.py`.

> QIK-VRT adds an effect haltpoint with exactly five states: NACK, CONTINUE,
> DONE, ISOLATE, and BLOCK. They classify a specific candidate effect, not just
> transport success.

## 0:35–1:00 — Run the no-network demo

Run:

```bash
python3 examples/effect_haltpoint_demo.py
```

> The same payload first remains at CONTINUE because required checks are open.
> A deliberate containment decision produces ISOLATE. Only the fully bound
> request with evidence, responsibility, policy approval, and a release
> decision produces DONE. Only that result has `ordinary_release=true`.

## 1:00–1:20 — Fail-closed behavior

Show the timeout, integrity, replay, and false-DONE tests.

> Missing evidence, a hash mismatch, timeout, or corrupt predecessor cannot be
> promoted silently. Protective paths remain NACK, CONTINUE, ISOLATE, or BLOCK.

## 1:20–1:40 — Reproducible evidence

Show the `make test` command and successful Actions run.

> The fixed release records 102 passing tests in nine modules, including 41
> protocol and conformance tests. The hosted GitHub Actions job completed
> successfully.

## 1:40–1:55 — Immutable identity

Show the release tag, commit, tree SHA, and document SHA-256.

> Evaluation is tied to a named commit and exact content tree, not an ambiguous
> moving branch.

## 1:55–2:00 — Close

> QIK-VRT makes a simple but consequential distinction executable:
> `TRANSPORT_ACK` is not `EFFECT_ACK`.

