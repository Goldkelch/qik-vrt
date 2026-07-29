<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Prompt-Template: Denk-Mengenlehre v1.0

Verwende dieses Template nur zusammen mit dem kanonischen QIK-VRT-Einstieg
`/AI` und dessen vollständiger `AI_CONTEXT.json.required_read_order`.

## Auftrag an das künstlich-kognitive System

1. Lade `policy/DENK_MENGENLEHRE_V1.json`,
   `docs/axiome/denk_mengenlehre_v1.md` und die dort gebundene visuelle
   Evidenz `docs/axiome/denk_mengenlehre_poster.jpg`.
2. Prüfe Pfad, Medientyp, Bytezahl, Abmessungen und SHA-256 des Posters gegen
   den Maschinenvertrag. Behandle das Poster als erklärende Visualisierung,
   nicht als formalen Beweis und nicht als Quelle zusätzlicher Axiome.
3. Behandle den Leitsatz
   „Denken ist Mengenlehre und inkludiert die leere Menge!“ von
   Ingolf Lohmann als interpretatives Modell, nicht als bereits bewiesene
   Identität zwischen Kognition und ZF/ZFC.
4. Beginne die modellierte Evidenzfolge bei \(E_0=\varnothing\).
5. Akkumuliere Gate-Evidenz durch Vereinigung, entscheide PASS jedoch
   ausschließlich durch die Konjunktion der Gate-Prädikate.
6. Modelliere Selbstbezug als typisierte Descriptor-Referenz. Behaupte weder
   `System ∈ System` noch `Repo ∈ Denken ∈ Repo`.
7. Prüfe Anforderungen über gleich typisierte IDs mit
   `Required ⊆ Verified`.
8. Definiere jedes Komplement relativ zur im Maschinenvertrag genannten
   Grundmenge.
9. Unterscheide strikt:
   - ausgeführte Evidenz,
   - erwartete Ausgabe,
   - interpretative Aussage,
   - mathematische Endlichkeitsaussage,
   - offene oder ausgeschlossene Behauptung.
10. Melde einen scope-qualifizierten PASS nur, wenn
   `python3 -B tools/qikvrt_denk_mengenlehre.py verify --json`
   auf dem benannten Commit `state=PASS` und `batch_pass=true` ausgibt.
11. Übertrage diesen scoped PASS niemals auf Repository, Authority/Mirror,
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
