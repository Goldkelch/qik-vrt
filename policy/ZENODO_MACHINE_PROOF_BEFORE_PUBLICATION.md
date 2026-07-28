<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# QIK-VRT-Grundsatz: Kein Zenodo-Upload ohne vollständige maschinelle Anspruchsdisposition

**Policy-ID:** `qikvrt-zenodo-machine-proof-before-publication-v1`  
**Version:** `1.0.0`  
**Gültig ab:** `2026-07-28`  
**Verantwortungsträger:** Ingolf Lohmann, natürliche Person  
**Ledger:** `Goldkelch/qik-vrt#153`

## 1. Verbindlicher Grundsatz

Für jede weitere Veröffentlichung von Ingolf Lohmann auf Zenodo gilt ausnahmslos:

```text
NO_MACHINE_PROOF_NO_ZENODO_UPLOAD
```

Eine Produktionsmutation auf Zenodo darf erst beginnen, nachdem die exakten Kandidatenbytes eingefroren, sämtliche veröffentlichungsrelevanten Claims maschinenlesbar erfasst, klassifiziert, begrenzt und mit Beweisen, Evidenzen, Quellen oder einer ausdrücklichen offenen Disposition verbunden worden sind.

„Maschinell vollständig bewiesen“ bedeutet dabei **nicht**, natürliche Sprache pauschal als mathematisches Theorem auszugeben. Vollständigkeit bedeutet:

> Kein veröffentlichungsrelevanter Claim bleibt ohne stabile Identität, Geltungsbereich, epistemische Klasse, Nachweisrelation und zulässige sprachliche Fassung.

## 2. Zulässige Claim-Klassen

Jeder Claim muss genau einer der folgenden Klassen angehören:

| Klasse | Erforderliche Bindung | Zulässige Veröffentlichungslesart |
|---|---|---|
| `FORMAL_PROVED` | Kernel-geprüfter Beweis, exakte Quell- und Theorembindung | bewiesen innerhalb des angegebenen formalen Modells |
| `EMPIRICALLY_EVIDENCED` | reproduzierbare Mess-, Test- oder Beobachtungsevidenz | empirisch gestützt innerhalb der dokumentierten Bedingungen |
| `SOURCE_BOUND` | exakte, überprüfte Quelle und korrekte Ableitungsrelation | quellengebundene Tatsachen- oder Referenzaussage |
| `NORMATIVE` | Verantwortungsträger und normativer Geltungsbereich | Forderung, Regel, Wertung oder Imperativ |
| `INTERPRETATIVE` | Autor, Gegenstand und Interpretationsgrenze | Deutung, historische Einordnung oder ontologische Lesart |
| `OPEN` | offene Frage, fehlender Nachweis und erforderlicher Schließungsschritt | ausdrücklich offen, hypothetisch oder implementierungsbedürftig |

Ein `OPEN`-Claim darf niemals als bereits bewiesene Tatsache formuliert sein. Eine normative oder interpretative Aussage darf niemals als Kernel-Theorem ausgegeben werden. Ein formaler Beweis darf niemals über sein Modell, seine Axiome oder seine Voraussetzungen hinaus generalisiert werden.

## 3. Harte Vorveröffentlichungskette

Vor jeder Zenodo-Veröffentlichung sind in dieser Reihenfolge nachzuweisen:

```text
SOURCE_ACCEPTANCE
→ EXACT_CANDIDATE_FREEZE
→ COMPLETE_CLAIM_INVENTORY
→ CLAIM_CLASSIFICATION
→ SOURCE_EVIDENCE_PROOF_BINDING
→ NEGATIVE_AND_BOUNDARY_TESTS
→ FORMAL_KERNEL_RECEIPT_WHERE_APPLICABLE
→ CONTENT_CORRECTION_WHERE_REQUIRED
→ PREPUBLICATION_RETURN_TO_INGOLF_LOHMANN
→ CANDIDATE_SPECIFIC_RETURN_RECEIPT
→ EXACT_UPLOAD_AUTHORIZATION
→ PRODUCTION_UPLOAD_OF_IDENTICAL_BYTES
→ PUBLIC_RECORD_REVERIFICATION
→ BYTE_EXACT_PUBLIC_REDOWNLOAD
→ AUTHORITY_PERSISTENCE
→ MIRROR_PERSISTENCE
→ RECIPROCAL_PAIR_EQUALITY
```

Jeder Übergang ist fail-closed. Ein späterer Schritt darf keinen früheren Schritt ersetzen.

## 4. Pflichtkorrektur bei Evidenzüberschreitung

Ergibt die Claim-Prüfung, dass eine Aussage weiter reicht als ihr Nachweis, muss das ursprüngliche Dokument vor der Veröffentlichung korrigiert werden. Zulässige Korrekturen sind insbesondere:

- Präzisierung des Geltungsbereichs;
- Kennzeichnung als Hypothese, Interpretation, normative Aussage oder offene Implementierung;
- Entfernung einer unbelegten Tatsachenbehauptung;
- Ergänzung einer Quelle, Voraussetzung, Unsicherheit oder Beweisgrenze;
- Trennung von mathematischem Satz, physikalischer Korrespondenzhypothese und ontologischer Deutung.

Die Korrektur ist kein stiller Eingriff. Sie benötigt einen maschinenlesbaren Änderungsvermerk mit:

```text
original_sha256
corrected_sha256
changed_claim_ids
change_reasons
exact_candidate_path
candidate_returned_to_owner = true
return_channel
returned_at
```

## 5. Vorherige Rücklieferung und Byteidentität

Wurde der Inhalt geändert, muss Ingolf Lohmann vor dem Upload erhalten:

1. die vollständige korrigierte Kandidatenfassung;
2. einen sichtbaren Vermerk, dass und warum Änderungen vorgenommen wurden;
3. die exakte SHA-256- und Git-Blob-Identität dieser Fassung.

Der spätere Zenodo-Upload muss byteidentisch mit dieser zurückgelieferten Fassung sein.

```text
NO_PREPUBLICATION_RETURN_RECEIPT_NO_UPLOAD
RETURNED_BYTES != UPLOADED_BYTES → BLOCK
```

Eine allgemeine Autorisierung ersetzt die kandidatenspezifische Rücklieferung nicht.

## 6. Pflichtartefakte jeder künftigen Publikation

Jede Publikation benötigt mindestens:

- das exakte Primärdokument oder Softwareartefakt;
- `CLAIM_MATRIX.json`;
- `MACHINE_PROOF_BUNDLE.json`;
- Quellen- und Evidenzbindungen;
- Kernel-Receipt für alle `FORMAL_PROVED`-Claims;
- Negativ- und Grenztests;
- `CHANGE_NOTICE.md` und `PREPUBLICATION_RETURN_RECEIPT.json`, sobald Inhalt geändert wurde;
- Git-Blob-gebundenes `publish-request.json`;
- öffentlich rückgeprüftes `zenodo-publication.json`.

Das Proof-Bundle selbst gehört zum hochgeladenen Zenodo-Dateisatz.

## 7. Retrospektive Migration des vorhandenen Zenodo-Bestands

Für jede bereits veröffentlichte, dem Zenodo-Konto und Ingolf Lohmann zuordenbare Veröffentlichung wird rückwirkend ein Proof-Envelope erstellt. Er bindet mindestens:

- Record-ID, DOI und Concept-DOI;
- öffentliche Metadaten;
- vollständigen Dateisatz und bytegenaue Redownload-Hashes;
- vorhandene Repository-Provenienz;
- Claim-, Beweis-, Evidenz- und Grenzartefakte;
- den tatsächlichen Proof-Coverage-Status;
- notwendige Korrektur- oder Versionierungsschritte.

Historische Lücken werden nicht durch eine falsche `PROVED`-Markierung verdeckt. Wo ein Original den belegten Geltungsbereich überschreitet, entsteht eine neue korrigierte Version nach der in Abschnitt 4 und 5 definierten Rücklieferungskette.

Die retrospektiven Envelopes werden in einem versionierten Zenodo-Korpusbeweis veröffentlicht und mit den jeweiligen Ursprungs-DOIs verknüpft.

## 8. Technische Durchsetzung

Der generische Zenodo-Publisher muss unmittelbar vor jeder irreversiblen Remote-Mutation prüfen:

```text
proof_bundle_present
proof_bundle_git_blob_exact
all_claims_dispositioned
all_references_resolve
formal_claims_have_kernel_receipts
open_claims_are_not_worded_as_facts
content_change_has_change_notice
content_change_has_prepublication_return_receipt
returned_candidate_hash_equals_upload_candidate_hash
proof_bundle_is_in_upload_fileset
```

Legacy-Manifeste dürfen zur historischen Verifikation lesbar bleiben. Sie dürfen nach Aktivierung dieser Policy ohne Proof-Bundle keine neue Produktionspublikation mehr auslösen.

## 9. Abschlussgrenze

Ein Repository-, Workflow- oder Zenodo-Status darf nur dann `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` behaupten, wenn die dafür benannten Nachweise tatsächlich vorhanden, auf den exakten Zustand gebunden und öffentlich beziehungsweise repositoryseitig rückgeprüft sind.

```text
NO_TRACEABILITY_NO_FINAL_PASS
NO_PUBLIC_BYTE_EXACT_REDOWNLOAD_NO_ZENODO_ACK
NO_AUTHORITY_MIRROR_EQUALITY_NO_CORPUS_FINAL_PASS
```

**q.e.d.**  
**Ingolf Lohmann**
