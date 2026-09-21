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

## QIKVRT-Standard: evidenzbasierte Fehlerbehebung ohne Downgrade

Dies ist die Standard-Arbeitsregel von QIKVRT. Die Einordnung als persönliche
Präferenz oder bloße Chat-Regel ist unzulässig. Product und Code Owner Ingolf
Lohmann hat diesen Geltungsbereich am 21. September 2026 ausdrücklich
klargestellt. Die technische Speicherung in einem Client oder Skill begrenzt
den Geltungsbereich nicht.

Der Standard gilt für menschliche Mitwirkende, KI-Clients, Agenten, Tools,
Workflows, Authority, Mirror, autorisierte Übergaben und abgeleitete
Mesh-Artefakte bei Fehleranalyse und Reparatur:

1. Software-Downgrades als Fehlerbehebung weder empfehlen noch ausführen.
   Begründete Reparaturen, Patches oder kompatible Upgrades verfolgen.
2. Beobachtete Fehlermeldung, fremden Nutzerbericht, vom Hersteller bestätigten
   Defekt und am betroffenen System belegte Ursache ausdrücklich unterscheiden.
   Ein übereinstimmender Fehlercode und der Ort eines Berichts in einem
   offiziellen Tracker beweisen keine identische Ursache.
3. Relevante Version, Build, Umgebung und verfügbare Log- oder
   Reproduktionsevidenz binden; Repository-Aussagen an den aktuellen HEAD/TREE
   binden. Hypothesen und unbekannte Informationen kenntlich machen.
4. Autorisierte, begrenzte Diagnoseschritte zur Ursachenklärung ausführen.
   Einen spekulativen Workaround nicht als bestätigte Reparatur darstellen.
5. Die ursprünglich fehlgeschlagene Operation nach einer Änderung prüfen.
   Eine höhere Versionsnummer allein belegt keine Fehlerbehebung. Geplante,
   vorbereitete, ausgeführte und nachgewiesene Wirkungen getrennt berichten.
6. Den Standard bei Clone, Fork, Template, Download, Build, Repackage, Merge,
   Wiederverwendung und autorisierter Mesh-Übergabe erhalten. Die tatsächliche
   Übernahme in jedes Ziel separat durch aktuellen Readback belegen.

TEMDD T1–T16 und bestehende Autorisierungs- und Wirkungsgrenzen bleiben
maßgeblich. Die normative Festlegung beweist weder eine konkrete
Laufzeitreparatur noch Main-Promotion oder bereits erfolgte Übernahme in alle
Mesh-Knoten. Änderungen des Standards benötigen zuständige ausdrückliche
Autorisierung; Ausnahmen sind nicht wiederholt zur Bestätigung vorzulegen.

## QIKVRT standard: evidence-based repair without downgrades

Apply this as the standard working rule of QIKVRT, explicitly clarified by
Product and Code Owner Ingolf Lohmann on 2026-09-21. Do not classify it as a
personal preference or a chat-only rule. Its storage in a client or skill does
not narrow its normative scope.

For human contributors, AI clients, agents, tools, workflows, Authority, Mirror,
authorized handoffs and derived Mesh artifacts:

1. Do not recommend or perform software downgrades as error correction. Pursue
   justified repairs, patches or compatible upgrades.
2. Distinguish the observed symptom, a third-party report, a maintainer-confirmed
   defect and a cause established for the affected system. A matching error
   code or an issue in an official tracker does not establish the same cause.
3. Bind the actual version/build, environment and available log or reproduction;
   bind repository claims to current HEAD/TREE. Label hypotheses and unknowns.
4. Use authorized, bounded diagnostics to establish causality. Do not present a
   speculative workaround as a verified repair.
5. Verify the originally failing operation after a change. A larger version
   number alone does not establish a repair. Separate planned, prepared,
   executed and verified effects.
6. Preserve the standard through clone, fork, template, download, build,
   repackage, merge, reuse and authorized Mesh handoff. Establish adoption in
   each destination through a fresh readback.

Retain TEMDD T1–T16 and all existing authorization and effect boundaries.
Normative persistence does not establish runtime repair, Main promotion or
propagation to unobserved Mesh nodes. A standard revision requires explicit
competent authority; do not repeatedly solicit exceptions.

The machine-readable contract is the `evidence_based_repair_standard` section
of `REFLEXIVE_FINDING_WORKFLOW_STANDARD.json`; the bundle carries the same
standard. The originating clarification corrects the assistant's attribution,
not the history of previously observed system behavior.
