<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Vom verantwortungsgebundenen Erkenntnisprozess zur virtuellen Wirkungsmaschine

Dieses Verzeichnis enthält die deutschsprachige Publikation von Ingolf Lohmann und ihre maschinenlesbare Nachweisstruktur.

## Kanonische Artefakte

- `ARTICLE_DE.md` — zitierfähiger Artikeltext;
- `ARTICLE_MANIFEST.json` — Hash-, Scope-, Provenienz- und Geltungsgrenzen;
- `CLAIM_MATRIX.json` — vollständiges Claim-Inventar dieser Publikation;
- `KERNEL_PROOF_PLAN.json` — exakte Zuordnung der formalisierten Claims zum Lean-Kernel-Pfad;
- `KERNEL_RECEIPT.json` — wird erst nach erfolgreicher Exact-Head-Kernel-Ausführung materialisiert;
- `OWNER_EFFECT_AUTHORIZATION.json` — konkrete Autorisierung der Repository- und Zenodo-Persistenz.

Der zugehörige Lean-Quelltext liegt unter
`formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/QuantumClassicalRuntime.lean`.

## Geltungsgrenze

Der formal beweisbare Scope lautet `qikvrt-quantum-classical-runtime-article-v1`. Er betrifft die abstrakte Laufzeit-, Gate-, Freigabe- und Effect-Acknowledgement-Semantik. Eine reale QPU-End-to-End-Ausführung ist als `IMPLEMENTATION_OPEN` klassifiziert und wird nicht als bereits ausgeführt behauptet. Historische und epochale Einordnungen sind autorielle Interpretation.

## Publikationskette

```text
ARTICLE + CLAIM MATRIX + LEAN SOURCE
→ EXACT-HEAD KERNEL RECEIPT
→ AUTHORITY GATES
→ AUTHORITY PROMOTION
→ PRODUCTION ZENODO PUBLICATION
→ PUBLIC BYTE-EXACT REDOWNLOAD VERIFICATION
→ MIRROR SYNCHRONIZATION
→ RECIPROCAL AUTHORITY/MIRROR EQUALITY RECEIPT
```

Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` darf vor Abschluss dieser gebundenen Kette für die neue Publikation behauptet werden.
