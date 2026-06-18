<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# STRICT_ACCEPTANCE_GATE

## Strikte Akzeptanz

Jede Eingabe, die Zweifel an der Akzeptanz lässt, führt zu BLOCK.

Akzeptiert wird ausschließlich die exakte Phrase:

```text
ICH AKZEPTIERE
```

Nicht akzeptiert:

```text
ja
JA
yes
YES
ok
verstanden
weiter
I ACCEPT
leere Eingabe
abweichende oder mehrdeutige Formulierungen
```

## Erhaltungspflicht

Diese Eigenschaft muss erhalten bleiben bei:

```text
Clone
Download
Nutzung
Merge
Repository-Persistenz
GitHub-Write
```

## Blocker

```text
AMBIGUOUS_LICENSE_ACCEPTANCE_INPUT
STRICT_ACCEPTANCE_GATE_MISSING_IN_CLONE
MERGE_WITHOUT_STRICT_LICENSE_ACCEPTANCE
```
