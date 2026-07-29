<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Denk-Mengenlehre v1.0

## Leitsatz

> Denken ist Mengenlehre und inkludiert die leere Menge!
>
> q.e.d.
>
> Ingolf Lohmann

## Epistemischer Status und Scope

`qikvrt-denk-mengenlehre-v1` ist ein interpretatives, formal präzisiertes
Modell für belegte Denkzustände in QIK-VRT. Es ist keine Behauptung, dass
biologisches oder künstliches Denken ontologisch mit ZF/ZFC-Mengenlehre
identisch sei. Die verwendeten endlichen Mengenoperationen sind ausführbar;
die philosophische Deutung bleibt als `INTERPRETIVE` gekennzeichnet.

Der qualifizierte Alias `DENK-MENGENLEHRE-BATCH-002` ist von
`CONTENT-DISPOSITION-BATCH-002` verschieden. Insbesondere gehört das
historische GitHub-Actions-Artefakt `8696689772` nicht zu diesem Scope.

## Formales Modell

Sei

\[
G = \{G_1,G_2,G_3,G_4,G_5,G_6\}
\]

die Menge der sechs Prüfgatter und

\[
\operatorname{status}(G_i)\in
\{\mathrm{PENDING},\mathrm{FAIL},\mathrm{PASS}\}.
\]

Der leere Anfangszustand ist

\[
E_0=\varnothing.
\]

Evidenz wird nicht durch Veränderung einer Menge „gefüllt“, sondern als
Zustandsfolge akkumuliert:

\[
E_{i+1}=E_i\cup \operatorname{Evidence}(G_{i+1}).
\]

Der Batch-PASS ist eine logische Konjunktion, keine Mengenvereinigung:

\[
\operatorname{BatchPass}
\iff
\bigwedge_{i=1}^{6}
\bigl(\operatorname{status}(G_i)=\mathrm{PASS}\bigr).
\]

Die Evidenzmengen dürfen dagegen vereinigt werden:

\[
E_{\mathrm{gesamt}}=\bigcup_{i=1}^{6}\operatorname{Evidence}(G_i).
\]

## A1–A7

### A1 — Repräsentation

Ein belegter Denkzustand wird als endliche Menge typisierter Claim-,
Anforderungs- und Evidenz-IDs modelliert. Diese Modellentscheidung erzeugt
keinen ontologischen Identitätsbeweis über Denken.

### A2 — Leerer Basiszustand

\(\varnothing\) ist ein zulässiger Initialzustand der Evidenzfolge. Rekursion
benötigt allgemein einen Basisfall; in diesem Modell wird dafür ausdrücklich
\(\varnothing\) gewählt.

### A3 — Vereinigung

Vereinigung akkumuliert Evidenz. Sie ersetzt nicht das logische UND der
PASS-Prädikate.

### A4 — Deckungsrelation

Repo-Dateipfade und Anforderungen werden nicht typfremd geschnitten. Für die
Menge erforderlicher Anforderungs-IDs \(R\) und die Menge verifizierter
Anforderungs-IDs \(I\) gilt:

\[
\operatorname{Gate4Pass}\iff R\subseteq I.
\]

Zusätzliche verifizierte IDs \(I\setminus R\) sind zulässig und werden
gesondert ausgewiesen. Repository-Kanonizität ist Evidenzautorität, nicht
automatisch Wahrheit.

### A5 — Potenzmenge

\[
\mathcal P(G)=\{S\mid S\subseteq G\},
\qquad |\mathcal P(G)|=2^6=64.
\]

Die 64 Elemente sind alle Teilmengen bestandener Gate-IDs. Sie beweisen
Vollständigkeit relativ zur deklarierten Gate-Menge, nicht die Abwesenheit
unerkannter Anforderungen. Für drei unabhängige Zustände je Gate gäbe es
formal \(3^6=729\) Belegungen; Gate-Abhängigkeiten schränken die erreichbaren
Belegungen zusätzlich ein.

### A6 — Relatives Komplement

Ein Komplement ist nur relativ zu einer ausdrücklich deklarierten Grundmenge
\(U\) definiert:

\[
\operatorname{Excluded}=U\setminus\operatorname{Allowed}.
\]

Für die tatsächlich geladenen Inputklassen \(L\) gilt:

\[
\operatorname{Gate5Pass}
\iff
L\cap\operatorname{Excluded}=\varnothing.
\]

### A7 — Typisierter Selbstbezug

Selbstbezug wird als Referenzrelation modelliert:

\[
\operatorname{descriptor}(S)\in\operatorname{RepoArtifacts}
\quad\land\quad
\operatorname{references}(\operatorname{descriptor}(S),S).
\]

Nicht behauptet wird \(S\in S\). Eine solche Selbstmitgliedschaft ist unter
der Fundierungsannahme von ZF/ZFC ausgeschlossen und würde weder
Selbstkenntnis noch Konsistenz beweisen. Der Validator prüft lediglich, dass
sein Descriptor und sein eigener Pfad im integritätsgebundenen Repository
enthalten sind. Die Korrektheit des Validators bleibt Teil des Trust-Modells.

## Die sechs Gates

| Gate | Prüfaussage | PASS-Evidenz |
|---|---|---|
| `G1` | Kernartefakte und AI-Kontextbindung sind vorhanden. | Pfade, Bytes und SHA-256 |
| `G2` | Der typisierte Selbstdescriptor referenziert den Scope und der Validator ist im Integritätsmanifest gebunden. | Descriptor- und Manifestprüfung |
| `G3` | Die kanonische Potenzmenge enthält genau 64 eindeutige Teilmengen von `G1` bis `G6`. | `POTENZMENGE.json` |
| `G4` | Alle erforderlichen Anforderungs-IDs sind durch ausführbare Checks gedeckt. | \(R\setminus I=\varnothing\) |
| `G5` | Die Input-Grundmenge ist vollständig partitioniert und kein ausgeschlossener Input wurde geladen. | \(L\cap\mathrm{Excluded}=\varnothing\) |
| `G6` | `G1`–`G5`, Repository-Integrität und Exact-Checkout-Bindung sind gemeinsam erfüllt. | Konjunktion plus Git-/Integrity-Evidenz |

`G6` nimmt seinen eigenen PASS nicht als Voraussetzung. Es prüft die fünf
vorherigen Gates plus einen unabhängigen Finalcheck. Erst `G6=PASS` setzt den
scope-qualifizierten `batch_pass=true`.

## Kanonische Ausführung

```bash
python3 -B tools/qikvrt_denk_mengenlehre.py materialize
python3 -B tools/qikvrt_integrity.py generate
python3 -B tools/qikvrt_integrity.py verify
python3 -B tools/qikvrt_denk_mengenlehre.py verify --json
```

Vor dem Commit muss die exakt beabsichtigte Dateiliste geprüft werden. Nach
jeder nachträglichen Änderung — auch an einem Poster — sind Integrität und alle
Gates neu auszuführen.

## No-false-PASS-Grenze

- Erwartete Ausgaben sind keine ausgeführten Nachweise.
- Fehlende oder nicht parsebare Evidenz ergibt `BLOCK`, niemals implizit
  `PASS`.
- `AXIOMS_PRESENT` bedeutet Präsenz, nicht Konsistenzbeweis.
- Ein Poster ist erklärende Visualisierung, kein Beweis.
- Chat, Modellgedächtnis, ungebundene externe Quellen und nicht
  materialisierte Soll-Ausgaben sind keine kanonische Evidenz.
- Der scope-qualifizierte Gate-PASS ist kein Repository-weiter
  `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Merge-, Sync- oder
  Publikationsnachweis.

## Prüfbarkeit

Der Maschinenvertrag ist
`policy/DENK_MENGENLEHRE_V1.json`. Der Validator ist
`tools/qikvrt_denk_mengenlehre.py`; seine Negativ- und
Nichtregressionstests stehen in `tests/test_denk_mengenlehre.py`.
