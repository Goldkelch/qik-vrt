<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# REFLEXIVE_FINDING_WORKFLOW_STANDARD

## Standard

Wenn ein ausgeliefertes Bundle beim Nutzer nicht auf Anhieb funktioniert, ist jedes Finding als reflexive Fehlerklasse zu behandeln.

## Geltung

```text
Download
Entpacken
Start
Konfiguration
Lizenzakzeptanz
Gegenstellentyp
OTHER-Beschreibung
Logging
lokale Reproduktion
GitHub-Persistenz
Template-Nutzung
Clone
Merge
Wiederverwendung
```

## Korrekturpflicht

Ein Finding darf nicht isoliert gefixt werden.

Pflichtschichten:

```text
Root-/Delivery-Struktur
Payload
interne Skripte
Windows
Linux
macOS
GitHub-Persistenzpfad
Template-/Clone-/Download-/Use-/Merge-Erhaltung
Lizenz-/Urheberrechts-Guard
Strict-Acceptance-Gate
Strict-Counterparty-Type-Gate
OTHER-Description-Gate
Policy
Map
Learn
Accept
Sync
Reports
Tests
```

## Verbotene Fixklassen

```text
ISOLATED_HOTFIX
LINUX_ONLY_FIX_WHEN_CROSS_PLATFORM_RELEVANT
UNMIRRORED_WINDOWS_MACOS_GITHUB_CLONE_FIX
FALSE_PASS_AFTER_LOCAL_ONLY_PATCH
UNPERSISTED_LEARNING
```

## Blocker

```text
USER_TEST_FINDING_NOT_REFLEXIVELY_CORRECTED
```

## Freigaberegel

Kein neues Bundle nach Nutzer-Finding ohne persistierte reflexive Fehlerklasse, Schichtenkorrektur und erneute Tests.
