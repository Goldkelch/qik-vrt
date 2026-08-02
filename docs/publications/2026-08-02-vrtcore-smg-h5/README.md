<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT VRTCore SMG H5 — Planck-Brücke, massive Schließung und virtuelle Kosmogenese

Publication ID: `qikvrt-vrtcore-smg-h5-v1`

Dieses additive H5-Bündel verbindet einen allgemein verständlichen Artikel,
einen Fachartikel in Markdown, XeLaTeX und PDF, eine maschinenlesbare EBNF-
Oberfläche, einen fail-closed Referenzvalidator und einen tatsächlich mit Lean
4.19.0 ausgeführten Modellkern. Leitthese und Rückkehrpunkt sind:

> Kausalität ist Relation, nicht Sequenz.

## Exaktes Ergebnis

| Ebene | Ergebnis |
|---|---|
| Lean-Modellkern | 32 von 32 benannten Theoremen kernelakzeptiert |
| Axiom-Audit | 17 ohne Axiome; 13 nur `propext`; 2 `propext` plus `Quot.sound`; 0 Projektaxiome |
| Lean-Quellgrenze | 0 `sorry`, 0 `admit`, 0 `unsafe` |
| Syntax und Semantik | Referenzinstanz erfüllt S01–S20; 11 von 11 Tests bestanden |
| Planck-Normalform | sechs exakte Monomidentitäten im symbolischen Modell |
| Massive Schließung | `massiveClosure currentH5Candidate = false` |
| Virtuelle Kosmogenese | Monotonie und bedingte Unbeschränktheit im Übergangsmodell bewiesen |
| Physikalische Vereinheitlichung | `OPEN_CANDIDATE`; nicht als Entdeckung oder fertige Quantengravitation beansprucht |
| Wirkung | `EFFECT_ACK_CONTINUE`; kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` |

Die formale Kugel ist damit in ihrem deklarierten endlichen Modellscope massiv:
Definitionen, Syntax, statische Semantik, Kernelbeweise, Axiom-Audit,
Negativtests, Claim-Matrix und Receipt greifen ineinander. Die Brücke von
diesem Modell zur Natur bleibt absichtlich offen. Sie erfordert insbesondere
eine explizite Dynamik, Standardmodell- und Einstein-Grenzfälle, universelle
Kopplung einschließlich Higgs-Sektor, Stabilität/Unitarität, eine
unterscheidende Vorhersage, empirische Korrespondenz und unabhängige
Reproduktion.

## Mathematischer Kern

H5 normalisiert am Planck-Punkt symbolisch

```text
hbar/(m_P*c) = l_P = G*m_P/c^2 = r_g(m_P)
l_P*p_P = t_P*E_P = hbar
l_P/t_P = E_P/p_P = c
```

Dabei ist `G*m/c^2` der Gravitationsradius. Der Schwarzschild-Radius ist
`2*G*m/c^2`; H5 blockiert eine stille Verwechslung dieses Faktors zwei.

Die zwölfteilige Schließung verlangt getrennte Zeugen für Planck-Normalform,
Wave/Record-Identität, Standardmodell- und Einstein-Grenzfall, universelle
Stress-Energie-Kopplung, Quantengravitationskorrespondenz,
Stabilität/Unitarität, kausale Konsistenz, Nichtzirkularität, eine
falsifizierbare Vorhersage, empirische Korrespondenz und unabhängige
Reproduktion.

## Artefaktkarte

| Schicht | Dateien |
|---|---|
| Allgemeinheit / Vorlesen | `QIK-VRT_SMG_Allgemein_WhatsApp_DE_2026-08-02.md` |
| Fachartikel | `QIK-VRT_SMG_Fachartikel_DE_2026-08-02.md`, `.tex`, `.pdf` |
| Lean-Kern | `VRTCore_SMG_PlanckBridge.lean`, `VRTCore_SMG_AxiomAudit.lean` |
| Sprache und Semantik | `VRTCore_SMG_Syntax.ebnf`, `H5_REFERENCE_INSTANCE.vrt`, `validate_h5_instance.py`, `test_validate_h5_instance.py` |
| Vektorgrafik | `VRTCore_SMG_EBNF_Map_DE.svg` |
| Erkenntnisgrenzen | `CLAIM_MATRIX.json`, `SOURCE_EVIDENCE_BINDINGS.json` |
| Reproduktion | `verify_h5_package.py`, `H5_LOCAL_KERNEL_RECEIPT.json`, `MANIFEST.json`, `SHA256SUMS` |
| Zitierung | `CITATION.cff` |

Kompilierte `.olean`-Dateien und XeLaTeX-Hilfsdateien gehören nicht zum
Publikationsumfang. Sie werden bei der Prüfung in temporären Verzeichnissen
erzeugt.

## Reproduktion

Der Prüfer benötigt Python 3, Lean 4.19.0, `pdfinfo` und `pdftotext`. Wegen
einer Restriktion dieser konkreten Laufzeit wurde Lean hier mit einem lokal
hashgebundenen `/proc/self/exe`-Kompatibilitätsshim gestartet; in einer normalen
Lean-Installation entfällt `--preload`.

```text
python3 -B verify_h5_package.py \
  --lean /path/to/lean-4.19.0/bin/lean
```

In der dokumentierten lokalen Laufzeit:

```text
python3 -B verify_h5_package.py \
  --lean /tmp/qik-vrt-lean-4.19.0/extracted-clean/lean-4.19.0-linux/bin/lean \
  --preload /tmp/qikvrt-lean-selfexe-compat.so
```

Der Prüfer kompiliert in ein neues temporäres Verzeichnis, führt alle 32
`#print axioms`-Abfragen aus, validiert die H5-Instanz, führt die elf Tests aus,
prüft JSON, SVG, PDF-Eigenschaften und sämtliche in `SHA256SUMS` gebundenen
Bytes.

Der Fachartikel wurde zweimal mit XeLaTeX gebaut:

```text
xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_SMG_Fachartikel_DE_2026-08-02.tex
xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_SMG_Fachartikel_DE_2026-08-02.tex
```

Das resultierende PDF umfasst 11 A4-Seiten. Alle Seiten wurden nach dem finalen
Neubau als PNG gerendert und visuell auf Beschnitt, Überlagerungen und
unleserliche Formeln geprüft; die Textentnahme enthält keine Unicode-
Ersatzzeichen.

## Wissenschaftliche und menschliche Grenze

Higgs- und Gravitationswellenbefunde sind starke empirische Anker. Sie sind
kein direkter Gravitonnachweis und liefern allein keine fertige Theorie der
Quantengravitation. Deshalb heißt der Arbeitsrahmen `SMG_VRT`: eine zu
prüfende Erweiterung, nicht das unveränderte Standardmodell.

Es ist zugleich sachlich gerechtfertigt, die geleistete Integration als große
formale und konzeptionelle Leistung zu würdigen. Diese Würdigung wird nicht zur
Behauptung eines bestätigten Naturgesetzes aufgebläht. Weltanschauliche und
spirituelle Folgerungen dürfen bedeutsame Deutungen sein; sie bleiben getrennt
von Kernelbeweis und Messbefund.

## Persistenz- und Wirkungsstatus

Das Bündel ist ein lokaler, uncommitteter Kandidat auf Basis des ausgewiesenen
Repository-Heads. Dieser Arbeitsschritt hat weder GitHub noch Zenodo noch den
IETF Datatracker mutiert. Ein technischer Exitcode 0 ist keine externe
Freigabe.

`GLOBAL_PASS = NOT_CLAIMED`  
`FINAL_PASS = NOT_CLAIMED`  
`EFFECT_ACK_DONE = NOT_CLAIMED`  
`EFFECT_STATE = EFFECT_ACK_CONTINUE`

