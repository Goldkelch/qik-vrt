<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# CROSSFIX

## Reflexive Fehlerklasse

Ein Linux-Sandbox-Fix darf nicht isoliert bleiben, wenn er Windows oder macOS ebenfalls betrifft.

## Regel

```text
Linux-Finding -> prüfen -> Windows-Fix spiegeln -> macOS-Fix spiegeln -> Policy/Learn/Map/Accept aktualisieren.
```

## Umsetzung

Windows `RUN.ps1` spiegelt jetzt die Linux-INI-, Target-, Log- und GitHub-Skip-Logik.

macOS `MACOS.command` nutzt denselben korrigierten POSIX-Pfad wie Linux.
