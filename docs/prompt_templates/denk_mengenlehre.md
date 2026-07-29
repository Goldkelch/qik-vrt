<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Prompt-Template: Denk-Mengenlehre v1.0

Verwende dieses Template nur zusammen mit dem kanonischen QIK-VRT-Einstieg
`/AI` und dessen vollständiger `AI_CONTEXT.json.required_read_order`.

## Auftrag an das künstlich-kognitive System

1. Lade `policy/DENK_MENGENLEHRE_V1.json` und
   `docs/axiome/denk_mengenlehre_v1.md`.
2. Behandle den Leitsatz
   „Denken ist Mengenlehre und inkludiert die leere Menge!“ von
   Ingolf Lohmann als interpretatives Modell, nicht als bereits bewiesene
   Identität zwischen Kognition und ZF/ZFC.
3. Beginne die modellierte Evidenzfolge bei \(E_0=\varnothing\).
4. Akkumuliere Gate-Evidenz durch Vereinigung, entscheide PASS jedoch
   ausschließlich durch die Konjunktion der Gate-Prädikate.
5. Modelliere Selbstbezug als typisierte Descriptor-Referenz. Behaupte weder
   `System ∈ System` noch `Repo ∈ Denken ∈ Repo`.
6. Prüfe Anforderungen über gleich typisierte IDs mit
   `Required ⊆ Verified`.
7. Definiere jedes Komplement relativ zur im Maschinenvertrag genannten
   Grundmenge.
8. Unterscheide strikt:
   - ausgeführte Evidenz,
   - erwartete Ausgabe,
   - interpretative Aussage,
   - mathematische Endlichkeitsaussage,
   - offene oder ausgeschlossene Behauptung.
9. Melde einen scope-qualifizierten PASS nur, wenn
   `python3 -B tools/qikvrt_denk_mengenlehre.py verify --json`
   auf dem benannten Commit `state=PASS` und `batch_pass=true` ausgibt.
10. Übertrage diesen scoped PASS niemals auf Repository, Authority/Mirror,
    Zenodo, IETF, Deployment, Merge, Veröffentlichung oder
    `EFFECT_ACK_DONE`.

## Erwartetes Antwortformat

```text
SCOPE: qikvrt-denk-mengenlehre-v1
COMMIT: <40-stelliger Git-SHA>
STATE: PASS | BLOCK
GATES: <bestandene Gates>/6
ARTIFACT_SHA256: <64-stelliger content-basierter Digest oder NONE>
BOUNDARY: scoped model verification only
```

Bei `BLOCK` sind der konkrete fehlgeschlagene Check und der nächste
deterministische Reparaturschritt zu nennen. Soll-Ausgaben dürfen nie als
Beobachtung wiederholt werden.
