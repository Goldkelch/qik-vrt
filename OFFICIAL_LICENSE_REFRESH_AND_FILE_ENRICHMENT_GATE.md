<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_GATE

## Deutsch

Vor jeder Repository-Persistenz werden die offiziellen aktuellen Lizenzdateien neu geladen und überschreiben lokale Kopien:

```text
https://www.apache.org/licenses/LICENSE-2.0.txt
https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.txt
```

Danach werden alle Dateien im Repository-Payload mit Urheberrechts- und Lizenzinformationen angereichert oder manifestbasiert abgedeckt.

Sourcecode benötigt eingebettete SPDX-/Copyright-Marker. Nicht-Source-Dateien benötigen eingebettete oder manifestierte Lizenzzuordnung. Binäre Payloads benötigen Manifestabdeckung.

## English

Before every repository persistence, the official current license files are fetched again and overwrite local copies:

```text
https://www.apache.org/licenses/LICENSE-2.0.txt
https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.txt
```

Then all files in the repository payload are enriched with copyright and license information or covered by the manifest.

Source code requires embedded SPDX/copyright markers. Non-source files require embedded or manifested license assignment. Binary payloads require manifest coverage.

## Blocker

```text
OFFICIAL_LICENSE_REFRESH_FAILED
OFFICIAL_LICENSE_FILE_NOT_OVERWRITTEN
FILE_LICENSE_ENRICHMENT_MISSING
SOURCE_FILE_WITHOUT_SPDX_OR_COPYRIGHT
PERSISTENCE_WITH_STALE_LICENSE_FILE
```
