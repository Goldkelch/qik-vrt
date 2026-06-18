<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# TEMPLATE

## Template-adaptive GitHub target

Dieses Bundle ist so gebaut, dass ein aus dem GitHub-Template erzeugtes neues Repository nicht starr auf das Ursprungsrepository zeigt.

## Zielerkennung

Reihenfolge:

```text
1. QALL_OWNER / QALL_REPO / QALL_BRANCH
2. GITHUB_REPOSITORY / GITHUB_REF_NAME
3. lokale .git/config remote origin URL
4. QALL_TARGET.json
5. interaktive Zielabfrage nur wenn kein Repository-Kontext existiert
```

## Komfortregel

Wenn das Repository als GitHub-Template genutzt, neu erzeugt und dann lokal geklont wird, enthält `.git/config` die neue Remote-URL. Dann muss im Normalfall nur noch der GitHub-Token eingegeben werden.

## ZIP-Grenze

Ein reiner ZIP-Download ohne `.git` enthält keinen sicheren Owner-/Repo-Kontext. Dann wird das Ziel nicht geraten, sondern muss per Umgebungsvariable, `QALL_TARGET.json` oder Abfrage gesetzt werden.

## Sicherheitsregel

Kein altes Zielrepository wird stillschweigend verwendet.

## Acceptance Test

Template-clone auto-target detection is a required release gate.
