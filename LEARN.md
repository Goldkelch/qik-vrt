<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# LEARN

## Verbindliche Lernregel

Jegliches Finding aus Tests, Audits, Builds oder Prüfberichten ist als Learning einzuordnen und lokal umzusetzen.

Das gilt ausdrücklich auch für:

- Warnungen
- Runtime-Grenzen
- nicht ausführbare Testteile
- fehlende Dependencies
- optionale Pfade
- nicht nachgewiesene GitHub-/Push-/Commit-/Upload-Zustände
- Pfadlängenbefunde
- Hash-/Sidecar-Befunde
- Skriptannahmen

## Aktuelles Learning

Finding:

```text
Windows-PowerShell-Runtime-Test konnte in dieser Linux-Sandbox nicht real ausgeführt werden.
```

Umsetzung:

```text
F001_WINDOWS_RUNTIME_BOUNDARY = IMPLEMENTED_LOCALLY
```

Folge:

```text
Kein echter Windows-Lauf wird behauptet.
Kein GitHub-Erfolg wird behauptet.
Der nächste reale Windows-Lauf muss STATUS.txt und MANIFEST.txt erzeugen.
```


## F002_REPO_QALL_MD_MISSING

Finding:

```text
Original-requirements test found that QALL.md was missing inside nested REPO.zip.
```

Learning:

```text
Repository-internal standard markers must be present, not only generated during runtime.
```

Implementation:

```text
QALL.md added to nested REPO.zip root.
LEARN.json/LEARN.md updated in bundle root and repository.
```


## L003_POWERSHELL_LINUX_SANDBOX_MAPPING

Windows-/PowerShell-Funktionen werden auf Linux-Sandbox-Funktionen gespiegelt.

Umsetzung:

```text
MAP.json
MAP.md
```

Grenze:

```text
Linux-Sandbox-Äquivalenz ersetzt keinen echten Windows-Runtime-Lauf.
GitHub-API-Pfade bleiben BLOCK, solange keine echten Credentials und keine erfolgreiche API-Ausführung vorliegen.
```


## L004_GITHUB_MAPPING_PERSISTENCE

Das Mapping und die Verfahrensweise müssen nach erfolgreicher Windows-Batch-Ausführung mit GitHub-API auch im GitHub-Repository enthalten sein.

Umsetzung:

```text
RUN.ps1 lädt MAP/LEARN/POLICY/Standardmarker per GitHub API hoch.
STATUS.txt enthält bei Erfolg GITHUB_MAPPING_POLICY_LEARNING=OK.
```


## L005_LINUX_MACOS_SYNC_LAYERS_MISSING

Finding:

```text
Linux- und macOS-Reproduktionsschichten waren im gelieferten Repository-Bundle noch nicht integriert.
```

Learning:

```text
Cross-platform sync layers must be included or explicitly blocked before delivery.
```

Implementation:

```text
RUN.sh
LINUX.sh
START.command
SYNC.json
SYNC.md
MAP019
MAP020
MAP021
```


## L006_AUTO_TOKEN_ONLY_GITHUB_PERSISTENCE

Ziel:

```text
Alle Plattformskripte laufen vollautomatisch.
Nur der GitHub-Token wird abgefragt.
Zielrepository: Goldkelch/qik-vrt
Branch: main
```

Erfolg:

```text
GITHUB_AUTO_TOKEN_ONLY=OK
```

nur nach echten API-PUTs und GET-Verifikation.

## L007_TEMPLATE_ADAPTIVE_OWNER_REPO

GitHub-Template-Instanzen müssen Owner/Repo/Branch automatisch aus dem lokalen Repository-Kontext übernehmen. Kein altes Ziel darf stillschweigend weiterverwendet werden.

## L008_TEMPLATE_CLONE_ACCEPTANCE_TEST

Template-adaptive target detection is now an Acceptance-Test before delivery.

## L009_DELIVERY_UX_STRUCTURE

Unnötige Details werden unter `_internal/` verdeckt. Startdateien und `LOGS/` liegen gemeinsam sichtbar im Root.

## L010_ROOT_ONLY_THREE_PLATFORM_SCRIPTS

Root enthält nur noch drei Skriptdateien: `WINDOWS.bat`, `LINUX.sh`, `MACOS.command`. Alles andere liegt unter `_internal/`, `_payload/` oder `LOGS/`.

## L011_INTERNAL_SUBSET_PAYLOAD_README_INI_LICENSE

`_internal/` ist logisch Teil von `_payload/` und liegt jetzt unter `_payload/_internal/`. Root enthält zusätzlich `README.md` für Zweck/Urheber/Lizenz und `QALL.ini` für zentrale Parameter.

## L012_CROSS_PLATFORM_FIX_MIRROR_REQUIRED

Linux-Sandbox-Bugfixes müssen für Windows und macOS gespiegelt werden, sofern der Fehler plattformübergreifend relevant ist. Unterlassung ist die reflexive Fehlerklasse `UNMIRRORED_LINUX_SANDBOX_FIX`.

## L014_RENEWED_LICENSE_ACCEPTANCE_BEFORE_EACH_PERSISTENCE

Vor jeder Repository-Persistenzänderung müssen Urheberrecht/Lizenzbedingungen erneut angezeigt und akzeptiert werden. Das gilt für künstlich-kognitive Systeme, natürliche Personen und juristische Personen gleichermaßen.

## L015_AMBIGUOUS_ACCEPTANCE_INPUT_BLOCKS

Jede zweifelhafte Akzeptanzeingabe blockiert. Akzeptiert wird nur exakt `ICH AKZEPTIERE`. Diese Eigenschaft muss bei Clone, Download, Nutzung und Merge erhalten bleiben.

## L016_AMBIGUOUS_COUNTERPARTY_TYPE_BLOCKS

Jede fehlende, freie, abweichende, unklare oder mehrdeutige Gegenstellentyp-Angabe blockiert. Zulässig sind nur exakt NATURAL_PERSON, ARTIFICIAL_COGNITIVE_SYSTEM, LEGAL_PERSON, ORGANIZATION oder OTHER.

## L017_OTHER_COUNTERPARTY_REQUIRES_DESCRIPTION

Bei Gegenstellentyp `OTHER` muss zusätzlich abgefragt und persistiert werden, was darunter konkret zu verstehen ist. Die vier Standardtypen bleiben als Vorbelegung/Auswahlwerte geführt.

## L018_USER_TEST_FINDING_REFLEXIVE_WORKFLOW_STANDARD

Jedes Nutzer-Test-Finding wird als reflexive Fehlerklasse behandelt und durch alle relevanten Schichten korrigiert. Keine isolierten Hotfixes.

## L019_BILINGUAL_UI_AND_USER_INFO_DE_EN

Alle interaktiven Benutzeroberflächen und alle nutzergerichteten Bundle-Informationen werden zweisprachig Deutsch/Englisch geführt.

All interactive user interfaces and all user-facing bundle information are maintained bilingually in German/English.

## L020_BILINGUAL_UI_INHERITANCE_REQUIRED

Alles aus Bundle, Repository oder GitHub Abgeleitete muss die zweisprachige DE/EN-UI-/Nutzerinformationspflicht erben.

Everything derived from the bundle, repository, or GitHub must inherit the bilingual DE/EN UI/user-information requirement.

## L021_OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_BEFORE_PERSISTENCE

Vor jeder Repository-Persistenz werden die offiziellen Lizenzdateien von Apache-2.0 und CC-BY-NC-ND-4.0 neu geladen und lokale Kopien überschrieben. Alle Dateien werden mit Lizenz-/Urheberrechtsinformationen angereichert oder manifestiert.

Before every repository persistence, official Apache-2.0 and CC-BY-NC-ND-4.0 license files are refreshed and local copies overwritten. All files are enriched with license/copyright information or manifested.

## L022_GITHUB_DOMAIN_FACTORY_AND_INHERITANCE

Deutsch: Eine neue GitHub-Domäne ist eine reale Repository-/GitHub-Persistenzwirkung. Deshalb muss die Erstellung trockenlauf-fähig, streng akzeptanzpflichtig, gegenstellentyp-geprüft, zweisprachig, auditierbar und in Klonen/Ableitungen vererbbar sein.

English: A new GitHub domain is a real repository/GitHub persistence effect. Therefore creation must support dry-run, strict acceptance, counterparty validation, bilingual UI, auditability, and inheritance in clones/derivatives.

## OFFICIAL_LICENSE_PLACEHOLDER_AND_HEADER_FIX

Deutsch: Offizielle Lizenztexte und Datei-Header/-Notices müssen vor Delivery materialisiert sein. Platzhalter oder bloße spätere Fetch-Versprechen sind BLOCK.

English: Official license texts and file headers/notices must be materialized before delivery. Placeholders or mere later-fetch promises are BLOCK.

## RECURSIVE_LICENSE_AND_UMLAUT_LAYER

Deutsch: Sourcecode bleibt ohne deutsche Umlaute. Nicht-Software-Dokumente verwenden deutsche Umlaute korrekt. Lizenz- und Urheberrechtsinformationen werden rekursiv in allen Repository-Dateien ergänzt oder manifestiert.

English: Source code remains free of German umlauts. Non-software documents use German umlauts correctly. License and copyright information is recursively added to or manifested for all repository files.
