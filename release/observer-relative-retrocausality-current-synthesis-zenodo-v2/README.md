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

Außerhalb dieses Dateisatzes bleiben bewusst die Vorbereitungs- und
Steuerungsartefakte: Metadatenentwurf, `*_DRAFT.json`-Dateien,
Rückgabe- und Autorisierungsunterlagen, Ablaufchecklisten, Gate-Status,
Policy-/Schemaquellen, lokale Prüfsummen und der Materialisierer. Sie dienen
der nachvollziehbaren Vorbereitung im Repository, sind aber kein
wissenschaftlicher Uploaddateisatz und keine Veröffentlichung.

Der Nachfolger ist weiterhin **nicht veröffentlicht**. Weder ein neuer
Zenodo-Record noch ein DOI oder ein Upload wird von diesem lokalen Kandidaten
behauptet.

## Gültiger Vorbereitungsstatus

`PREPUBLICATION_PACKAGE_PREPARED_NOT_EXECUTABLE`

Die direkte Anweisung von Ingolf Lohmann vom 12. August 2026,
„Zenodo, arXiv und IETF, Veröffentlichung freigegeben“, ist in
`OWNER_ZENODO_AUTHORIZATION_DRAFT.json` als **weite
Veröffentlichungsfreigabe** dokumentiert. Sie ist ausdrücklich noch nicht die
von der aktiven Zenodo-v2-Policy geforderte, kandidatenspezifische kanonische
Zeile `AUTHORIZE_EXACT_UPLOAD`. Vor einer Produktionsmutation fehlen daher
noch:

1. die sichtbare Rückgabe der vollständigen, eingefrorenen Kandidatenbytes an
   Ingolf Lohmann;
2. der daraus erzeugte v2-Rückgabe-Receipt;
3. die exakte Upload-Autorisierung, die Receipt-, Metadaten- und
   Machine-Proof-Hash bindet;
4. ein auf den dann aktuellen, remote vorhandenen Quell-Commit gebundener
   Produktionsmanifest;
5. ein frischer Nachweis, dass GitHub- und Zenodo-Credentials im autorisierten
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

`MACHINE_PROOF_BUNDLE_DRAFT.json`,
`PREPUBLICATION_RETURN_RECEIPT_DRAFT.json` und
`PUBLISH_REQUEST_DRAFT.json` sind bewusst **keine** Eingaben für
`tools/qikvrt_zenodo_publish.py`. Die Ausführung darf erst erfolgen, wenn die
in `FINALIZATION_CHECKLIST.md` dokumentierte Kette geschlossen ist.
