<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# STRICT_COUNTERPARTY_TYPE_GATE

## Strikte Gegenstellentyp-Einstufung

Jede fehlende, freie, abweichende, unklare oder mehrdeutige Angabe zum Typ der Gegenstelle führt zu BLOCK.

Zulässig sind nur exakt:

```text
NATURAL_PERSON
ARTIFICIAL_COGNITIVE_SYSTEM
LEGAL_PERSON
ORGANIZATION
OTHER
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
AMBIGUOUS_COUNTERPARTY_TYPE_INPUT
MISSING_COUNTERPARTY_TYPE
STRICT_COUNTERPARTY_TYPE_GATE_MISSING_IN_CLONE
MERGE_WITHOUT_STRICT_COUNTERPARTY_TYPE_GATE
```
