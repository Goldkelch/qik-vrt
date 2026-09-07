# Nachweisbare Anschlussfähigkeit — Publikationskandidat 1.0

Autor und Rechteinhaber: **Ingolf Lohmann**. Ziel: **production Zenodo**.

## Gegenstand und Freigabe

Der zuletzt im Dialog bestätigte Artikel „Der Punkt, an dem Informatik wirklich überraschend wird: Über nachweisbare Anschlüsse, erhaltene Beweise und verantwortbare Wirkungen“ wird eigenständig vorbereitet. Die ausdrückliche Owner-Anweisung lautet: „Großartig! Bitte nun das Geeignete auf Zenodo veröffentlichen!“ Sie ergänzt die bestehende Freigabe für Zenodo-Veröffentlichung, DOI-Registrierung und autoritativen Readback. Keine erneute allgemeine Publikationsfreigabe wird verlangt.

Der akzeptierte Artikelkörper bleibt erhalten. Nur Zitierformat, Quellen-/Versions-/Lizenzanhang und Layout wurden ergänzt. Die Datei ARTICLE_DE.md enthält die vollständige vorgelegte Fassung.

## Exakte Grenze

**Dies ist eine Vorbereitung, keine erfolgte Zenodo-Veröffentlichung.** Die Metadaten und die Claim-Map sind ausdrücklich Entwürfe; sie sind keine Eingaben für den generischen Publisher. Es existiert hier kein behaupteter Kernel-Beleg und kein erfundener v2-Autorisierungs- oder Rückgabe-Receipt.

Der fortgeschriebene Kandidat benötigt P2–P7 gemäß policy/QIKVRT_EXECUTION_PRECEDENCE_V1.json und die v2-Verträge gemäß runtime/capabilities/ZENODO_PUBLICATION_CAPABILITY.json. Die dauerhafte Freigabe ersetzt diese gegenstandsgebundenen Voraussetzungen nicht.

## Wiederverwendung

Ausschließlich den bestehenden generischen Publisher tools/qikvrt_zenodo_publish.py samt vorhandener Machine-Proof-, Autorisierungs-, Single-use- und Readback-Mechanismen verwenden. Keine neuen Workflows, alternativen Uploadskripte, Secret-Exporte, Endlosschleifen oder Änderungen historischer Dateien.

Der historische Anker aus Issue #925 bleibt eine separate, bytegebundene Quelle. Weder seine Erledigung noch sein aktueller DOI-/Datei-Readback wird aus Issue-Schließung oder Repository-Inhalt abgeleitet.

## Dateien

ARTICLE_DE.md: vollständiges Manuskript mit nummerierten Primärquellen.
ZENODO_METADATA_DRAFT.json: noch nicht gesendete Metadaten.
CLAIM_MAP_DRAFT.json: gegenstandsbezogene Klassifikation und offene formale Receipts.
PUBLICATION_REQUEST.json: Owner-Auftrag, Artefaktidentitäten, Vorbedingungen und explizite Nicht-Effekte.

Die bereits ausgelieferte PDF-Lesefassung ist in diesem Kandidaten unter `Der_Punkt_nachweisbare_Anschlussfaehigkeit_Lohmann_v1.pdf` enthalten: 23209 Bytes, SHA-256 `e5f018c156385b2e4a4dc343d2372bfdf2908b446ca195a4d8de985afe13d924`, Git-Blob `d5748aec5657e868321afd26baa5bbec1602aa66`. Die historischen PDF- und Manuskriptbytes wurden nicht verändert. Repository-Persistenz und spätere öffentliche Zenodo-Identität werden getrennt zurückgelesen. Die endgültige Uploadmenge benötigt weiterhin die vollständigen v2-Kontrollen.

## Ausgeführte Indexreparatur

Der vorhandene Generator `tools/qikvrt_publication_overview.py` wurde mit seinen fünf vorhandenen Regressionstests lokal ausgeführt. Die originalen Indizes, Generator und Testquelle wurden vorher gegen ihre Git-Blob-Identitäten geprüft. Er ergänzt genau das neue Publikationsbündel als `repository_candidate` in JSON und HTML; der zweite Lauf ist änderungsfrei. Ausgeführt wurde eine isolierte Projektionsprüfung, kein vollständiger Repository-Checkout und kein neuer vollständiger CI-/Kernel-Lauf. Die exakten Ausgangs- und Ergebnisbindungen stehen in `PUBLICATION_REQUEST.json` unter `repair_execution`.

Der bestehende Integritätsworkflow darf in PR-Läufen ausdrücklich nicht committen. Deshalb wird der gespeicherte Reparaturcommit getrennt von einer erfolgreichen Regeneration im CI-Arbeitsverzeichnis nachgewiesen. Die Root-Integritätsdaten und vollständigen Exact-head-Gates bleiben erforderlich. Workflows, Tests, Sicherheits- und Publikationsregeln werden nicht geändert.

## Lizenz

Nicht-Software-Dokumente: CC BY-NC-ND 4.0. Ingolf Lohmann bleibt Autor und Rechteinhaber. https://creativecommons.org/licenses/by-nc-nd/4.0/
