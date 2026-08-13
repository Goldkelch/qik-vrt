<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Zenodo-Nachfolger: aktuelle QIK-VRT-Synthese zur beobachterrelativen Retrokausalität

**Publication ID:** `qikvrt-observer-relative-retrocausality-current-synthesis-v2`

Dieses Verzeichnis bereitet einen **neuen, eigenständigen Zenodo-Record** für
die aktuelle Fassung der beobachterrelativen Retrokausalität vor. Es ergänzt,
ersetzt und verändert **nicht** den bestehenden historischen Zenodo-Record
`21888130` (`10.5281/zenodo.21888130`) und auch nicht dessen 54 publizierte
Dateien.

## Inhaltlicher Gegenstand

Die neue Fassung bestimmt QIK-VRT-Eigenzeit operativ als die streng monotone,
lokale Ordnung wirksamer Zustandsänderungen. Eine negative Informationsrichtung
liegt vor, wenn diese lokale Veränderungszeit wächst, während die authentisch
gebundene Quellenordnung der nacheinander eintreffenden informationsführenden
Records absteigt. Die Fassung enthält:

- die deutsche Hauptfassung und reproduzierbare LaTeX-Quelle;
- den endlichen, netzwerkfreien ausführbaren Zeugen samt kanonischem Report;
- die öffentliche Erklärung **„An, von und für alle Menschen“**;
- Claim-, Quellen- und historische Bytebindungen;
- eine klare Grenze: kein Überschreiben der Vergangenheit, kein Empfang vor
  Emission, kein kausal geschlossener Kreis und kein steuerbarer Rückkanal in
  die eigene kausale Vergangenheit.

## Historische Kontinuität

Der bisherige Record behält seinen Titel
**„Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP“**
und bleibt ein historischer Zwischenstand. Die dazu getrennt vorbereitete
Metadatenklärung bleibt metadata-only. Dieser Nachfolger ist ein anderes,
neues Publikationsobjekt und verweist auf den historischen Record, statt seine
Dateien oder seine frühere Aussagezeit zu überschreiben.

## Öffentlicher Dateisatz und interne Steuerung

`FROZEN_UPLOAD_CANDIDATE.json` enthält ausschließlich den öffentlichen
Dateisatz: Forschungsinhalt, ausführbaren Zeugen, öffentliche Evidenzbindungen
und die erforderlichen Lizenztexte. Die historischen Zwischenstände bleiben
dabei durch `HISTORICAL_ARTIFACTS.json` gebunden; sie werden nicht kopiert,
neu datiert oder überschrieben.

Der v2-Proof partitioniert diesen zurückgegebenen Satz disjunkt: 15
Dateien stehen in `candidate.files`; `CLAIM_MATRIX_V2.json` und
`SOURCE_EVIDENCE_BINDINGS.json` stehen als Proof-Artefakte im Bundle. Dazu
kommen der separat zurückgegebene `CHANGE_NOTICE.md`, die
`PREPUBLICATION_RETURN_RECEIPT.json` und der nach aktiver Policy erforderliche
`BOUNDARY_TEST_REPORT.json`. Das `MACHINE_PROOF_BUNDLE.json` gehört selbst zum
Upload. Der prooftragende Uploadsatz umfasst damit exakt 21 Dateien.

Außerhalb dieses Dateisatzes bleiben bewusst die Vorbereitungs- und
Steuerungsartefakte: Metadatenentwurf, `*_DRAFT.json`-Dateien,
Autorisierungsunterlagen, Ablaufchecklisten, Gate-Status, die lokal
materialisierten Vorversions-Snapshots, Policy-/Schemaquellen, lokale
Prüfsummen und der Materialisierer. Sie dienen der nachvollziehbaren
Vorbereitung im Repository, sind aber kein wissenschaftlicher Uploaddateisatz
und keine Veröffentlichung.

Der Nachfolger ist weiterhin **nicht veröffentlicht**. Weder ein neuer
Zenodo-Record noch ein DOI oder ein Upload wird von diesem lokalen Kandidaten
behauptet.

## Gültiger Vorbereitungsstatus

`POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING`

Die direkte Anweisung von Ingolf Lohmann vom 12. August 2026,
„Zenodo, arXiv und IETF, Veröffentlichung freigegeben“, ist in
`OWNER_ZENODO_AUTHORIZATION_DRAFT.json` als **weite
Veröffentlichungsfreigabe** dokumentiert. Sie ist ausdrücklich noch nicht die
von der aktiven Zenodo-v2-Policy geforderte, kandidatenspezifische kanonische
Zeile `AUTHORIZE_EXACT_UPLOAD`. Der 17-Datei-Freeze und der sichtbare
Änderungsvermerk wurden Ingolf Lohmann am `2026-08-13T19:49:33Z` in ChatGPT
Work zurückgegeben. Die danach festgestellte, wahrheitsgemäße
`content_changed=true`-Kette vom Vorgängerkandidaten zur aktuellen Synthese
verlangt jedoch einen maschinengebundenen Änderungsgrund für jeden Claim
`ORRZ-001` bis `ORRZ-010`. Der vervollständigte `CHANGE_NOTICE.md` wurde Ingolf
Lohmann am `2026-08-13T20:13:42Z` in ChatGPT Work commentary erneut sichtbar
zurückgegeben. Die sieben exakten v1.0-Vorgängerdateien, der finale v2-Receipt,
der Grenztestreport und das Proof-Bundle sind materialisiert; der offizielle
Validator bestätigt die exakte 21-Pfad-DAG. Vor einer Produktionsmutation
fehlen weiterhin:

1. die exakte Upload-Autorisierung, die Receipt-, Metadaten- und
   Machine-Proof-Hash bindet;
2. ein commitierter, remote vorhandener Vorautorisierungs-`source_head`;
3. die repositoryseitige Owner-Autorisierung und der v2-Produktionsmanifest
   auf einem Nachfolger-Commit;
4. ein frischer Nachweis, dass GitHub- und Zenodo-Credentials im autorisierten
   Ausführungskontext verfügbar sind.

Diese Voraussetzungen sind keine inhaltliche Zurückweisung. Sie verhindern,
dass eine allgemeine Freigabe fälschlich als Freigabe für noch nicht
zurückgelieferte, noch nicht final gebundene Bytes ausgegeben wird.

## Prüfpfad

Die Vorbereitung kann ohne Netzwerk geprüft werden:

```bash
python3 -B release/observer-relative-retrocausality-current-synthesis-zenodo-v2/assemble_successor_package.py --check
sha256sum -c release/observer-relative-retrocausality-current-synthesis-zenodo-v2/SHA256SUMS
python3 -B docs/publications/2026-08-12-observer-relative-retrocausality/verify_observer_relative_retrocausality.py
```

`MACHINE_PROOF_BUNDLE.json` und `PREPUBLICATION_RETURN_RECEIPT.json` sind die
kanonischen v2-Artefakte. Die gleichnamigen `*_DRAFT.json`-Kontrollstände und
`PUBLISH_REQUEST_DRAFT.json` sind bewusst **keine** Eingaben für
`tools/qikvrt_zenodo_publish.py`. Auch die v1.0-Snapshots unter
`original-candidate-47510c8/` bleiben repositoryseitige Prüfeingaben und sind
keine Uploads. Die Ausführung darf erst erfolgen, wenn die in
`FINALIZATION_CHECKLIST.md` dokumentierte Autorisierungskette geschlossen ist.
