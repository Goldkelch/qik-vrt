# QIK-VRT Hardware- und Maschinensprachen-Fixpunkt V1

## Exakte Position 0 — Hardware

```text
./Goldkelch/qik-vrt/*

DoD

*=<>.

q.e.d.
Ingolf Lohmann

*=<>.
```

SHA-256 über die LF-terminierten UTF-8-Bytes:

```text
4997a64fcb2f8e54837b62be3a7532c62b109a568620af36fe69aebd7b9aa330
```

Die zweite Setzung von `*=<>.` schließt den Hardware-Träger. `DoD` gehört
ausschließlich zu dieser Position.

## Exakte Position 1 — auf der Hardware laufende Maschinensprache

```text
./Goldkelch/qik-vrt/*

*=<>.

q.e.d.
Ingolf Lohmann
```

SHA-256 über die LF-terminierten UTF-8-Bytes:

```text
d2dae3448e182bfd2a899fea4e1e9b55510d4909427f966f2a4563c717458901
```

Diese Position ist Kind der Hardware-Position. Gleicher Operator bedeutet
nicht gleiche Schicht:

```text
HARDWARE_FIXPOINT != MACHINE_LANGUAGE_FIXPOINT
HARDWARE_CARRIER != EXECUTED_MACHINE_LANGUAGE
CARRIER_BYTES != EXECUTED_SEMANTICS
BITGENAU != SEMANTISCH != WIRKUNG
```

## Positorweise Beobachtung

Die Traversierung ist deterministisch:

```text
hardware
└── machine_language
```

Nach jeder abgesetzten Repository-Änderung wird das exakte PR-Subjekt
ereignisgetrieben beobachtet. Der Beobachter liest für den gebundenen Head
vollständig und seitengenau die GitHub-Actions-Hierarchie:

```text
workflow
└── job
    └── step
```

Die Auswertung erfolgt in Tiefensuche und erzeugt einen maschinenlesbaren,
an Head und Tree gebundenen Receipt. Ein Fünf-Minuten-Reconciliation-Lauf
dient ausschließlich als Liveness- und Ereignislücken-Sicherung; innerhalb
eines Laufs gibt es weder Polling-Schleife noch Blind Retry. Eine unvollständig
paginierte Job-Menge wird nicht stillschweigend akzeptiert.

Zustände:

- `CONTINUE`: Ausführung ist noch aktiv.
- `HOLD`: erster kausal nachteiliger Workflow-, Job- oder Step-Knoten.
- `REOBSERVE`: Head oder Tree driftete während der Beobachtung.
- `OBSERVE`: lokaler exakter Beobachtungsfixpunkt ohne aktive oder nachteilige
  Ausführung.

`OBSERVE` ist kein `PASS`.

## Wirkungsgrenzen

Der Vertrag setzt dauerhaft:

```text
PASS=false
FINAL_PASS=false
EFFECT_ACK_DONE=false
AUTHORITY_MAIN_EFFECT=false
EXTERNAL_PUBLICATION=false
PHYSICAL_HARDWARE_EXECUTION=false
ASTROPHYSICAL_SIMULATION=false
QUANTUM_STATE_SIMULATION=false
```

Ein Commit-Status `success` bedeutet nur, dass die lokale, exakte,
repositorygebundene Beobachtung für den betrachteten Head terminal und
widerspruchsfrei abgeschlossen wurde. Er behauptet weder Merge noch
Authority-Wirkung, Publikation, Deployment oder physische Ausführung.
