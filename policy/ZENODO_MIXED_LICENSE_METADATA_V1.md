<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zenodo Mixed-License Metadata Policy v1

## Status

`VALIDATE_ONLY`. Diese Policy autorisiert weder einen Zenodo-Effekt noch eine
Änderung eines bestehenden Records. Sie ergänzt die bestehende v1/v2-
Publikationsstrecke, ohne deren Bytes oder Verhalten zu ändern.

## Zweck

Ein Upload mit unterschiedlichen dateibezogenen Rechten darf nicht durch ein
einziges Record-Lizenzfeld als einheitlich lizenziert dargestellt werden. Vor
einer zukünftigen Publikation muss deshalb jede Upload-Datei genau einem Recht
zugeordnet und diese Zuordnung an ihre Bytes gebunden sein.

## Verbindlicher Offline-Vertrag

Ein Kandidat verwendet:

- `qikvrt_zenodo_publication_manifest_v3`;
- `qikvrt_zenodo_file_license_map_v1` in `FILE_LICENSE_MAP.json`;
- das für den Kandidaten geltende `LICENSE_NOTICE.md`;
- Pfad, Upload-Name, Bytezahl, SHA-256 und Git-Blob-SHA-1 für jede Datei;
- `metadata.rights` als exakte Projektion aller tatsächlich verwendeten Rechte;
- `state = validate_only`, `confirm = NO_REMOTE_EFFECT` und
  `transport = NATIVE_RDM_MULTI_RIGHTS_NOT_IMPLEMENTED`.

Globs, Default-Lizenzen, überlappende Zuordnungen, fehlende oder zusätzliche
Dateien und unbenutzte Rechte sind verboten. `FILE_LICENSE_MAP.json` und
`LICENSE_NOTICE.md` gehören selbst zum exakten Upload-Set und erhalten jeweils
eine explizite Zuordnung zu `cc-by-nc-nd-4.0`, entsprechend der in diesen
Kontrollartefakten deklarierten Lizenz.

## Rechteklassen

| Artefaktklasse | Vertragliche Repräsentation |
| --- | --- |
| Publikation und wissenschaftliche Nicht-Software-Artefakte | Zenodo-ID `cc-by-nc-nd-4.0`, SPDX `CC-BY-NC-ND-4.0` |
| ausdrücklich Apache-lizenzierte Formal-/Softwaredateien | Zenodo-ID `apache-2.0`, SPDX `Apache-2.0` |
| aktuelle QIK-VRT-Software unter PolyForm | benutzerdefiniertes Recht `LicenseRef-PolyForm-Noncommercial-1.0.0` mit gebundenem Lizenztext |

PolyForm wird bis zur separat nachgewiesenen Zenodo-Vokabular-Unterstützung
nicht als Standard-ID behauptet. Die Definition muss den offiziellen URL
`https://polyformproject.org/licenses/noncommercial/1.0.0/` und den exakten,
hochgeladenen Lizenztext binden.

## CFF-Grenze

Bei einem heterogenen Fileset darf `CITATION.cff` kein Top-Level-Feld
`license` enthalten. Ein CFF-Lizenzarray bezeichnet alternative Lizenzen für
das zitierte Werk und ist keine Datei-zu-Lizenz-Zuordnung. `LicenseRef-*` wird
im CFF-Lizenzfeld ebenfalls nicht verwendet.

## Effektgrenze

`tools/qikvrt_zenodo_mixed_license_contract.py` ist ausschließlich ein lokaler
Validator. Er besitzt keine Token-, Netzwerk-, Git-Ref- oder Zenodo-Funktion.
Der bestehende Produktionspublisher unterstützt nur v1/v2 und lehnt v3 als
unbekanntes Schema ab, bevor ein Client erzeugt oder eine Autorisierung
verbraucht werden kann.

Eine spätere Aktivierung erfordert kumulativ:

1. einen separaten nativen Multi-Rights-Transport;
2. Sandbox-Create/Read/Public-Roundtrip-Evidenz ohne Rechteverlust;
3. einen neuen bytegenauen Proof-Bundle-/Return-Receipt-Kandidaten;
4. eine neue, kandidatgebundene schriftliche Owner-Autorisierung.

Bis dahin gilt `EFFECT_PERMITTED = false`.

## Historische Grenze

Die veröffentlichte Survival-v1, ihre 31 Upload-Dateien, ihre Proof-Artefakte
und ihr Zenodo-Record bleiben unverändert. Die drei `FORMAL_*.lean`-Dateien
bleiben Apache-2.0; die übrigen 28 Upload-Dateien bleiben CC-BY-NC-ND-4.0.
Im v1-Upload befinden sich keine Runtime-, Build-, API- oder Tooling-Dateien der
aktuellen PolyForm-lizenzierten Repository-Software.
