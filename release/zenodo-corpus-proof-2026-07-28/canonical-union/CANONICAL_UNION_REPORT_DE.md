<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Kanonischer Zenodo-Vereinigungsbestand und Beginn der Inhalts-Claim-Disposition

Beobachtungszeitpunkt: `2026-07-28T16:20:00+02:00`

## Vereinigungsbestand

- Authentisiert beobachtete Records: **11**
- Öffentlich rekonsilierte historische Records: **13**
- Kanonische Record-Identitäten: **24**
- Concept-Linien: **12**
- Payload-Cluster: **19**
- Bytegleiche Mehrfach-Cluster: **2**
- Einmalig zu prüfende Claim-Subjects: **19**

Die zwei Quellmengen sind disjunkt. Bytegleiche Veröffentlichungen werden nicht mehrfach als unabhängige Inhaltsgegenstände behandelt, sondern über ihren Payload-Multiset-Hash zu einem Claim-Subject zusammengeführt.

## Inhalts-Claim-Disposition

Die Disposition wurde gestartet, aber noch nicht abgeschlossen. Jeder Record und jedes byteäquivalente Claim-Subject besitzt nun einen terminal benannten nächsten Prüfschritt.

| Priorität | Subject | Record-IDs | Zustand | Nächster Effekt |
|---:|---|---|---|---|
| 0 | `SUBJECT-187cfda66d1eda16` | `21636774` | `EXISTING_CLAIM_GRAPH_REVALIDATION_PENDING` | `VERIFY_EXISTING_CLAIM_GRAPH_AND_NO_CONTENT_CHANGE` |
| 1 | `SUBJECT-45b9d1b677568ae7` | `21640160,21640173` | `MACHINE_PROOF_BUNDLE_BINDING_PENDING` | `VALIDATE_EXISTING_MACHINE_PROOF_BUNDLE_AND_BIND_CONTENT_CLAIMS` |
| 2 | `SUBJECT-2beab714d1dc6019` | `21482023` | `CLAIM_EXTRACTION_PENDING` | `EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS` |
| 2 | `SUBJECT-51a0cfc51bcbd722` | `21488116` | `CLAIM_EXTRACTION_PENDING` | `EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS` |
| 2 | `SUBJECT-685123cd60e2fd7b` | `21498773` | `CLAIM_EXTRACTION_PENDING` | `EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS` |
| 2 | `SUBJECT-d2dad396615a4c7c` | `21498774` | `CLAIM_EXTRACTION_PENDING` | `EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS` |

## Wahrheitsgrenze

- Der Vereinigungsbestand und die Queue sind maschinenlesbar gebunden.
- Noch nicht jede natürliche oder technische Inhaltsbehauptung ist dispositioniert.
- Ob eine historische Veröffentlichung korrigiert werden muss, bleibt bis zur Claim-Prüfung `UNDETERMINED_PENDING_CLAIM_REVIEW`.
- Es wurde kein neuer Zenodo-Upload ausgeführt.
- Mirror-Synchronisation und reziproke Equality-Quittung stehen aus.

Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird behauptet.

Nächster deterministischer Effekt:

```text
EXECUTE_CONTENT_DISPOSITION_BATCH_001
```
