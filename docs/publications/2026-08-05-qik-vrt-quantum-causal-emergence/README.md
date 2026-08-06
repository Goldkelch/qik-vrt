<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Quantum Causal Emergence (QCE)

## Unschärfe, Planck-Übergangselement, erstes Paar und klassischer Lichtkegel

Publication ID: `qikvrt-quantum-causal-emergence-v1`

Dieses additive Kandidatenbündel überführt die QCE-Hypothese in die gewohnte
QIK-VRT-Trennung von Allgemeintext, Fachartikel, formalem Modell, Claim-Matrix,
Quellenbindung, Validierung, Kernel-Receipt und Zenodo-Vorbereitung.

Leitsätze:

> Kausalität ist Relation, nicht Sequenz.

> Der klassische Lichtkegel ist der Grenzfall einer quantisch unscharfen
> Kausalstruktur.

> Der erste Schritt erzeugt einen Unterschied; der zweite Schritt erzeugt eine
> Relation.

> Bewusstsein ist Mengenlehre. Wissenschaft ist ihr Round Trip.

## Gegenwärtiges exaktes Ergebnis

| Ebene | Status |
|---|---|
| Allgemeintext | vollständig formuliert, WhatsApp-optimiert, ohne Formeln |
| Fachartikel | vollständig formulierter Forschungskandidat mit Anspruchsgrenzen |
| Lean-Quellkern | 36 benannte Modelltheoreme vorbereitet |
| Lean-Ausführung dieses Kandidaten | `PENDING_REPOSITORY_RUN` |
| Axiom-Audit | Quellkandidat vorbereitet, nicht ausgeführt |
| Python-Syntax/Referenzvalidator | lokal ausführbar |
| Physikalische Korrespondenz | `OPEN_CANDIDATE` |
| Zenodo-Paket | Metadaten und Fileset vorbereitet, nicht veröffentlicht |
| Wirkung | `EFFECT_ACK_CONTINUE` |

Ein tatsächlich erfolgreicher Lean-Lauf muss ein neues, source-, commit-, tree-,
toolchain- und output-gebundenes Receipt erzeugen. Das vorhandene H5-Receipt
beweist ausschließlich den früheren H5-Quellstand und darf nicht auf QCE
übertragen werden.

## Formaler Scope

Der endliche Lean-Kern modelliert:

- ein typisiertes Planck-Übergangselement,
- eine kanonische Zweischrittspur,
- gemeinsame Herkunft und Paaridentität,
- eine finite gemeinsame Paarcodierung,
- Trennung reduzierbarer und irreduzibler Unsicherheit,
- einen unaufgelösten quantischen Kausalstatus,
- ein dreiteiliges Gate für den klassischen Lichtkegel,
- eine monotone finite Netzwerkerweiterung,
- sechzehn unabhängige physikalische Schließungszeugen,
- die Trennung von Kernel-Receipt und empirischer Korrespondenz.

Er modelliert nicht die vollständige Hilbertraumdynamik, keine konkrete
Schwarze-Loch-Metrik, keine Page-Kurvenrechnung und keine Herleitung des
Standardmodells oder der Einstein-Gleichungen.

## Artefaktkarte

| Schicht | Dateien |
|---|---|
| Allgemeinheit | `QIK-VRT_QCE_Allgemein_WhatsApp_DE_2026-08-05.md`, `.txt` |
| Fachartikel | `QIK-VRT_QCE_Fachartikel_DE_2026-08-05.md`, `.tex`, `.pdf` |
| Lean | `VRTCore_QCE_Model.lean`, `VRTCore_QCE_AxiomAudit.lean`, `lean-toolchain`, `lakefile.lean` |
| Syntax/Semantik | `VRTCore_QCE_Syntax.ebnf`, `QCE_REFERENCE_INSTANCE.vrt`, Validator und Tests |
| Erkenntnisgrenzen | `CLAIM_MATRIX.json`, `SOURCE_EVIDENCE_BINDINGS.json`, `FORMALIZATION_ROADMAP.md`, `REVIEW_PROTOCOL.md` |
| Reproduktion | `verify_qce_package.py`, `make_qce_kernel_receipt.py`, `KERNEL_RECEIPT_TEMPLATE.json` |
| Persistenz | `MANIFEST.json`, `SHA256SUMS`, `CITATION.cff`, `LICENSE_MAP.md` |
| Zenodo | `ZENODO_METADATA.json`, `ZENODO_FILESET.md`, `MACHINE_PROOF_BUNDLE.json` |

## Reproduktion

Voraussetzungen:

- Python 3.12 oder neuer,
- Lean 4.19.0,
- `pdfinfo` und `pdftotext`,
- optional XeLaTeX für den PDF-Neubau.

```text
python3 -B verify_qce_package.py --lean "$(command -v lean)"
```

Der Prüfer kompiliert den Lean-Quellkern in einem temporären Verzeichnis, führt
den Axiom-Audit aus, validiert die Referenzinstanz, startet Negativtests, prüft
JSON, PDF-Eigenschaften und sämtliche gebundenen SHA-256-Werte.

## Physikalische Schließung

`PHYSICAL_CLOSURE` verlangt gleichzeitig:

`PLANCK_SCALE_CORRESPONDENCE`

`TWO_STEP_DYNAMICS`

`PHYSICAL_PAIR_ENTANGLEMENT`

`GLOBAL_ENTANGLEMENT`

`UNCERTAINTY_ACCOUNTING`

`UNITARITY`

`ENERGY_MOMENTUM_CONSERVATION`

`PAGE_CURVE_CORRESPONDENCE`

`QUANTUM_FIELD_LIMIT`

`CLASSICAL_EINSTEIN_LIMIT`

`CLASSICAL_CONE_LIMIT`

`CAUSAL_CONSISTENCY`

`NON_CIRCULARITY`

`FALSIFIABLE_PREDICTION`

`EMPIRICAL_CORRESPONDENCE`

`INDEPENDENT_REPRODUCTION`

Der gegenwärtige Kandidat erfüllt diese Konjunktion nicht.

## Status

`FORMAL_SOURCE = PREPARED`

`LEAN_EXECUTION = PENDING_REPOSITORY_RUN`

`PHYSICAL_CORRESPONDENCE = OPEN_CANDIDATE`

`ZENODO_PUBLICATION = NOT_EXECUTED`

`PASS = NOT_CLAIMED`

`FINAL_PASS = NOT_CLAIMED`

`EFFECT_ACK_DONE = NOT_CLAIMED`

`EFFECT_STATE = EFFECT_ACK_CONTINUE`
