<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zenodo-Dateigrenze für QIK-VRT Formalization 2.0.0-alpha.2

> **Manifeststatus:** `FORMAL_RELEASE_CANDIDATE`
>
> **Zenodo-Konzept:** `10.5281/zenodo.21488115`
>
> **Quellrecord:** `21501365`

Versions-DOI und neuer Record werden nicht selbstreferenziell in die gebundenen
Uploadbytes geschrieben. Maßgeblich sind die nachgelagerte
Publikationsevidenz und die öffentlich abgerufenen Zenodo-Metadaten.

Dieses Dokument definiert den beabsichtigten vollständigen Uploadsatz der
neuen Version im bestehenden Formalisierungs-Konzept
`10.5281/zenodo.21488115`.

Die neue Version muss aus dem zum Veröffentlichungszeitpunkt aktuellen
öffentlichen Quellrecord `21501365` erzeugt werden. Weder Record `21498774`
noch `21488116` darf als aktuelles `newversion`-Ziel behandelt werden.

## Exakte Uploadnamen

1. `QIKVRT_Formalization_v2.0-alpha.2.zip`
2. `QIKVRT_Formalization_v2.0-alpha.2.zip.sha256`
3. `README.md`
4. `FORMALIZATION_SCOPE.md`
5. `VERIFICATION_REPORT.md`
6. `STATUSERKLAERUNG_WHATSAPP_DE.md`
7. `EVIDENCE_BOUNDARY.md`
8. `MANUSCRIPT_PROOF_MAP.md`
9. `CLAIM_GRAPH.json`
10. `DRAFT01_SOURCE_PROVENANCE.json`
11. `DRAFT01_CLAIM_MATRIX.json`
12. `CITATION.cff`
13. `ZENODO_FILESET.md`
14. `ZENODO_SHA256SUMS`
15. `LICENSE_NOTICE.md`
16. `LICENSE-CODE`
17. `CC-BY-NC-ND-4.0.txt`
18. `ALPHA2_INPUT.json`
19. `ALPHA2_EFFECT_ACK_DONE.json`

`ZENODO_SHA256SUMS` bindet die übrigen achtzehn Uploads und enthält keinen
Selbsteintrag.

Nicht zum vorab hashgebundenen Zenodo-Dateisatz gehören
`LEAN_CI_EVIDENCE.json` und `ZENODO_PUBLICATION_EVIDENCE.json`.
`LEAN_CI_EVIDENCE.json` entsteht nach dem finalen Quellencommit und nach den
lokalen/CI-Prüfgates, aber vor der Zenodo-Publikation; sie wird ausschließlich
auf dem Evidenz-State-Branch und als Workflow-Artefakt persistiert.
`ZENODO_PUBLICATION_EVIDENCE.json` entsteht erst nach der anonymen Prüfung
des veröffentlichten Records und wird in einem nachgelagerten
Evidenz-Folgecommit gespiegelt. Diese Zwei-Phasen-Trennung verhindert
unmögliche Zeit- und Hash-Selbstbezüge.

## Inhalt des Softwarearchivs

Das deterministische ZIP muss mindestens enthalten:

- `formalization/QIKVRT_Formalization_v2.0/**`, mit Ausnahme des unten
  ausdrücklich genannten Verzeichnisses `release_authorization/`;
- die Lean-Bibliotheken `QIKVRTFormalization` und `QIKVRTEffectAck`;
- Lake-Dateien und das gepinnte `lean-toolchain`;
- Source-, Claim-, Axiom-, Escape- und Proof-Object-Prüfer;
- positive und negative Tests;
- die exakten Draft-01-TXT- und XML-Eingaben;
- den bestehenden endlichen `proof-report.json`;
- die für die Manuskriptquellenbindung erforderlichen TeX-/PDF-Quellen;
- `.github/workflows/qikvrt_manuscript_proof.yml`;
- dieses additive Publikationsverzeichnis;
- eine maschinenlesbare Archiv-Provenienz und Einschlussliste.

Nicht in das Archiv gehören:

- `.git`;
- `.lake`;
- `__pycache__`, `.pyc` oder andere Laufzeitcaches;
- Zugangstoken, Cookies oder Authentisierungszustand;
- GitHub-Actions-Artefakte mit nichtöffentlichen Metadaten;
- `formalization/QIKVRT_Formalization_v2.0/release_authorization/`; dessen
  Alpha-2-Nachweise werden stattdessen als Uploads 18 und 19 einzeln gebunden;
- das frühere Alpha-1-ZIP als verschachteltes Archiv;
- Audioaufnahmen oder Transkripte.

## Zweiphasige Wirkung

### Phase 1: Reservierung

Nach erfolgreicher CI und identischem finalem Git-Tree beider Repositories
wird genau ein neuer Versionsentwurf aus Record `21501365` reserviert. Diese
Phase darf nicht publizieren. Sie persistiert lediglich die von Zenodo
gelieferte Draft-ID, DOI und nicht geheime Reservierungsevidenz.

Die Reservierung bindet bereits das endgültige Dateimanifest und seine
Hashwerte. Die Versions-DOI wird nur in der nachgelagerten
Reservierungsevidenz festgehalten; die gebundenen Uploadbytes werden dadurch
nicht verändert. Ändert sich ein gebundenes Byte, darf diese Reservierung nicht
finalisiert werden.

### Phase 2: Finalisierung

Die Finalisierung darf nur den eindeutig reservierten Entwurf verwenden. Vor
der Veröffentlichung müssen:

1. Manifest und sämtliche vorab gebundenen Uploadbytes unverändert sein;
2. der gebundene CI-Ausgang `success` lauten;
3. Commit und Tree noch den autorisierten Repository-Refs entsprechen;
4. beide Repository-Trees identisch sein;
5. alle geerbten Draft-Dateien entfernt sein;
6. exakt die neunzehn oben genannten Dateien hochgeladen sein;
7. jedes Upload-Byte nach Download gegen Größe, MD5 und SHA-256 bestehen;
8. Metadaten, Version, Konzept, DOI und Record-ID exakt passen.

Erst danach darf der Entwurf publiziert werden. Anschließend sind der
öffentliche Record, seine `latest`-Beziehung und alle Dateien ohne
Zugangstoken erneut zu prüfen.

## Lizenzgrenze

Das Softwarearchiv ist ein gemischt lizenziertes Aggregat. Maßgeblich bleiben
die Hinweise jeder einzelnen Datei:

- Dokumentation überwiegend CC BY-NC-ND 4.0;
- neu erstellter Formalisierungscode gemäß `LICENSE-CODE`;
- IETF-Material gemäß seinen IETF-Trust-Hinweisen;
- bestehende Dritt- und historische Inhalte gemäß ihren eigenen Hinweisen.

Die Zenodo-Metadaten dürfen diese unterschiedlichen Rechte nicht durch eine
pauschale Relizenzierung überschreiben.

## Fail-closed Publikationssprache

Vor erfolgreicher anonymer öffentlicher Nachprüfung darf nur von einem
„Release-Kandidaten“ oder einer „reservierten DOI“ gesprochen werden.

Die Formulierungen „auf Zenodo veröffentlicht“, „öffentlicher Record“,
„neueste Version des Konzepts“ und eine endgültige Dateizahl mit verifizierten
Hashes sind erst nach dieser Nachprüfung zulässig.
