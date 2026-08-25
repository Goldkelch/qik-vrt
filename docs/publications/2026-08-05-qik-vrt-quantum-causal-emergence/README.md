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
| Lean-Quellkern | 36 benannte endliche Modelltheoreme |
| Lean-Ausführung der gebundenen Kernbytes | `EXECUTED_RECEIPT_PRESENT` |
| Axiom-Audit | ausgeführt: 36 Direktiven, 0 Projektaxiome, 0 `sorry`/`admit`, 0 `unsafe` |
| Python-Syntax/Referenzvalidator | lokal ausführbar |
| Physikalische Korrespondenz | `OPEN_CANDIDATE` |
| Zenodo-Paket | deterministisch baubar, nicht veröffentlicht |
| Wirkung | `EFFECT_ACK_CONTINUE` |

Der persistierte QCE-Receipt stammt aus dem erfolgreichen Actions-Lauf
`31467654213` und bindet Commit `225675ae2145aec709103f843cd26fd6893b39ba`
sowie Tree `94eafdc41f42c3c5107275212351c323653dcb35`. Dieser reine
Verifikations-Carrier basiert auf Authority `main`
`d0593450077161a83d35b6d373ebe7968df7229d`; der Paketprüfer bestätigt, dass
die im Receipt gebundenen Modell- und Axiom-Audit-Bytes mit diesem Paket
identisch sind. Das Receipt gilt nur für diese explizit gebundenen formalen
Kernbytes und beweist keine physikalische Korrespondenz.

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
| Reproduktion | `verify_qce_package.py`, `make_qce_kernel_receipt.py`, Receipt, Axiom- und Verifikationsoutput |
| Ausführungsprovenienz | `QCE_KERNEL_ARTIFACT_PROVENANCE.json`, `QCE_KERNEL_RECEIPT.json`, `qce-axiom-output.txt`, `qce-verification.json` |
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

`FORMAL_SOURCE = EXECUTED_BYTES_BOUND`

`LEAN_EXECUTION = EXECUTED_RECEIPT_PRESENT`

`PHYSICAL_CORRESPONDENCE = OPEN_CANDIDATE`

`ZENODO_PUBLICATION = NOT_EXECUTED`

`PASS = NOT_CLAIMED`

`FINAL_PASS = NOT_CLAIMED`

`EFFECT_ACK_DONE = NOT_CLAIMED`

`EFFECT_STATE = EFFECT_ACK_CONTINUE`
