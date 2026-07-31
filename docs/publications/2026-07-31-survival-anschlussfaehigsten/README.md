<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Survival of the Anschlussfähigsten

Dieses Verzeichnis enthält den wissenschaftlichen
Vorveröffentlichungskandidaten
`qikvrt-survival-of-the-anschlussfaehigsten-v1`.

Die von Ingolf Lohmann festgelegte Computerzeitalter-Fassung lautet:

> **Survival of the fittest = Survival of the Anschlussfähigsten.**

Der Fachartikel operationalisiert diese Interpretation durch endliche
Fortsetzungshorizonte, lebensfähige Anschlüsse, invariantenerhaltende
Übergänge, Anschluss-Sprachen und relative Viabilität. Er trennt ausdrücklich:

- biologische Fitness als je nach Modell absolut oder relativ gemessenen
  reproduktiven Beitrag im jeweiligen Umwelt-, Populations- und Zeitkontext;
- die autorenseitige Interpretationsregel für das Computerzeitalter;
- die kernel-prüfbare Eigenschaft des definierten Übergangsmodells;
- empirische Hypothesen über reale technische oder soziotechnische Systeme.

## Artefakte

| Datei | Rolle |
|---|---|
| `ARTICLE_DE.md` | lesbare wissenschaftliche Langfassung |
| `Survival_der_Anschlussfaehigsten_2026-07-31.tex` | reproduzierbare XeLaTeX-Quelle |
| `Survival_der_Anschlussfaehigsten_2026-07-31.pdf` | visueller Publikationskandidat |
| `CANONICAL_STATEMENT.md` | kanonische Kurzfassung und operationale Ausfaltung |
| `ORIGINAL_THESIS_TRANSCRIPT.md` | wortgetreue autorenseitige Ausgangsthese |
| `CHANGE_NOTICE.md` | wissenschaftliche Präzisierungen gegenüber der Kurzform |
| `EVIDENCE_BOUNDARY.md` | Beweis-, Anwendungs- und Publikationsgrenzen |
| `CLAIM_MATRIX.json` | maschinenlesbare Klassifikation aller Hauptaussagen |
| `CLAIM_MATRIX_H0_PENDING.json` | unveränderter Status-Snapshot vor der ersten Exact-Head-Prüfung |
| `CLAIM_MATRIX_H1_FIT_VERIFIED.json` | bytegenauer FIT-Status-Snapshot des ersten Ziel-Heads |
| `SOURCE_EVIDENCE_BINDINGS.json` | Quellen- und Versionsbindungen |
| `KERNEL_PROOF_PLAN.json` | Exact-Head-, Toolchain- und Axiomvertrag |
| `KERNEL_EVIDENCE_H0_PENDING.json` | originale CI-Evidenz des ersten erfolgreichen Exact-Head-Kernellaufs |
| `KERNEL_EVIDENCE_H1_TARGET.json` | originale CI-Evidenz des FIT-statusmaterialisierten Ziel-Heads |
| `FORMAL_OperationalContinuation.lean` | bytegleicher Zenodo-Snapshot des FIT-001-Moduls |
| `FORMAL_ConnectabilitySimulation.lean` | bytegleicher Zenodo-Snapshot der FIT-002/3-Module |
| `FORMAL_WeightedConnectability.lean` | bytegleicher Snapshot des MAT-001/2-Moduls |
| `FORMAL_SOURCE_SNAPSHOT.json` | Identitätsbeleg zwischen Repository- und Archivquellen |
| `BOUNDARY_TEST_REPORT.json` | lokale positive und negative Vorprüfungen; ausdrücklich kein Kernel-Receipt |
| `PDF_RENDER_VALIDATION.json` | reproduzierbarer PDF- und Sichtprüfbeleg |
| `CITATION.cff` | Zitiermetadaten ohne vorweggenommenen DOI |
| `LICENSE_NOTICE.md` | dateibezogene Lizenzgrenzen |
| `ZENODO_FILESET.md` | vorgesehener, noch nicht autorisierter Upload-Scope |

Der formale Kandidat liegt in:

- `formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Process/OperationalContinuation.lean`
- `formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Process/ConnectabilitySimulation.lean`
- `formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Process/WeightedConnectability.lean`

## Maschinenbeweisstatus

```text
FORMAL_SOURCE          = PRESENT
LEAN_TOOLCHAIN         = leanprover/lean4:v4.19.0
LOCAL_KERNEL_RESULT    = UNAVAILABLE
FIT_001_TO_003_RESULT  = KERNEL_VERIFIED
CI_EXACT_HEAD_H0       = d9734302efaf3c79110ceb32f8987822b864a6dd
CI_RUN_H0              = 30624247534
CI_EXACT_HEAD_H1       = a3d9c2509182d8ac34b69d7dced0b652b6aecdba
CI_RUN_H1              = 30625183041
FULL_5_CLAIM_SCOPE     = AWAITING_EXACT_HEAD_KERNEL_RECEIPT
AXIOM_AUDIT            = PASS_EMPTY_FOR_FIT001_FIT002_FIT003; MAT_PENDING
PUBLICATION_STATUS     = CANDIDATE_PREPUBLICATION
ZENODO_MUTATION        = false
```

Die ersten beiden grünen Exact-Head-Läufe sind als H0- und H1-Evidenz
bytegenau persistiert. Sie binden die FIT-Quellen, Proof-Konstanten, Toolchain,
Objekte und leeren Axiomenlisten. Der Scope wird nun um MAT-001 und MAT-002
erweitert. Bis der erweiterte Fünf-Claim-Head selbst geprüft und sein
statusmaterialisierter Nachfolger bestätigt ist, bleibt die aktive Matrix
`AWAITING_EXACT_HEAD_KERNEL_RECEIPT`. Zenodo bleibt zusätzlich hinter der
hashgebundenen Autorisierung fail-closed.

## Reproduktion

Der vorgesehene Kernelbefehl lautet:

```sh
cd formalization/QIKVRT_Formalization_v2.0
lake env lean QIKVRTFormalization/Process/OperationalContinuation.lean
lake env lean QIKVRTFormalization/Process/ConnectabilitySimulation.lean
python3 scripts/audit_lean_axioms.py
python3 scripts/audit_proof_escapes.py
```

Der PDF-Kandidat wird dreimal mit XeLaTeX und festem
`SOURCE_DATE_EPOCH` gebaut und anschließend vollständig mit Poppler
gerendert und visuell geprüft.

## Veröffentlichungsstatus

Es wird derzeit weder ein DOI noch eine Zenodo-Publikation, ein Peer Review,
biologischer Konsens oder repository-weite Vollständigkeit behauptet. Vor dem
Upload sind erforderlich:

1. Exact-Head-Receipt der statusmaterialisierten Nachfolgefassung;
2. unveränderte Claim-Matrix und PDF-Kandidatenbytes;
3. kandidatengebundenes Machine-Proof-Bundle;
4. Rückgabe genau dieser Bytes an Ingolf Lohmann;
5. eine danach erteilte, hashgebundene `AUTHORIZE_EXACT_UPLOAD`-Erklärung.

Jede Inhaltsänderung nach der Rückgabe macht diese Autorisierung ungültig.
