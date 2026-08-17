# QIK-VRT Metagrammatik – Zielmodell Motorola 68000

## Zweck

Dieses Zielmodell begrenzt die Compiler-Rückseite bewusst auf einen kleinen, deterministischen Kern für die Motorola-68000-Architektur. Die Begrenzung dient Portabilität, Prüfbarkeit, Parallelisierbarkeit und reproduzierbarer Synchronisation.

## Grundsatz

**Kausalität ist nicht Sequenz.**

Eine lineare Instruktionsfolge ist lediglich eine mögliche Serialisierung eines bereits bestimmten Wirkungsgraphen. Die normative Semantik wird deshalb vor der Maschinenkode-Erzeugung als gerichteter Kausalgraph dargestellt.

```text
QUELLE
→ AST
→ SEMANTIK
→ KAUSALGRAPH
→ ZULÄSSIGE TOPOLOGISCHE ORDNUNG
→ M68000-IR
→ MASCHINENKODE
```

Zwei unabhängige Knoten des Kausalgraphen dürfen parallel, verteilt oder in verschiedener Reihenfolge ausgewertet werden, sofern ihre beobachtbare Wirkung und ihre Effect-Ack-Abhängigkeiten unverändert bleiben. Eine bloße frühere Position im Quelltext erzeugt keine kausale Abhängigkeit.

## Minimales Maschinenmodell

Ziel: ursprünglicher Motorola 68000, 32-Bit-Datenregistermodell mit 24-Bit-Adressraum und 16-Bit-Datenbus als Zielannahme. Die Compiler-Rückseite verwendet zunächst nur einen konservativen Teil der Architektur:

- Datenregister `D0`–`D7`;
- Adressregister `A0`–`A7`, wobei `A7` Stapelzeiger ist;
- ganzzahlige Operationen auf Byte, Wort und Langwort;
- bedingte und unbedingte Sprünge;
- Unterprogrammaufruf und Rückkehr;
- explizite Speicherzugriffe;
- keine Gleitkommaeinheit vorausgesetzt;
- keine MMU vorausgesetzt;
- keine späteren 68020+-Erweiterungen vorausgesetzt.

## Kausale Zwischenrepräsentation

Jede normative Operation wird als Knoten beschrieben:

```text
KNOTEN <id>
  OP       = <operation>
  LIEST    = {<ressourcen>}
  SCHREIBT = {<ressourcen>}
  BRAUCHT  = {<vorgaenger-knoten>}
  WIRKUNG  = <NONE|REQUESTED|EXECUTED|OBSERVED|ACKNOWLEDGED>
```

Eine Kante `A -> B` existiert nur, wenn mindestens eine der Bedingungen gilt:

1. `B` benötigt ein von `A` erzeugtes Datum;
2. `A` und `B` besitzen eine nicht kommutative Wirkung auf dieselbe Ressource;
3. eine Autoritäts-, Lease-, Exact-Head- oder Effect-Ack-Regel verlangt die Ordnung;
4. die Sprachsemantik bindet ausdrücklich eine Ursache-Wirkungs-Abhängigkeit.

Nicht ausreichend für eine Kante sind allein:

- textuelle Reihenfolge;
- Zeitstempel ohne Wirkungsbezug;
- Beobachtungskorrelation;
- gleiche Terminalinstanz.

## Deterministische Serialisierung

Für einen einzelnen 68000-Kern wird der Kausalgraph deterministisch topologisch sortiert. Bei mehreren gleichberechtigt ausführbaren Knoten entscheidet eine stabile Kennung als reine Serialisierungsregel. Diese Auswahl ändert nicht den Kausalgraphen.

Damit gilt:

```text
CAUSAL_ORDER != SOURCE_ORDER
CAUSAL_ORDER != WALL_CLOCK_ORDER
SERIALIZATION ∈ TOPOLOGICAL_SORTS(CAUSAL_GRAPH)
```

## Skalierung

Die gleiche IR kann auf mehrere Mesh-Knoten partitioniert werden. Parallelisierung ist nur zwischen kausal unabhängigen Teilgraphen zulässig. Synchronisation erfolgt an expliziten Kanten bzw. Effect-Ack-Grenzen, nicht an künstlichen globalen Sequenzpunkten.

## Fail-closed

Kann der Compiler nicht beweisen, dass zwei Wirkungen unabhängig oder korrekt geordnet sind, erzeugt er keine optimistische Parallelisierung. Der Zustand lautet `HOLD` beziehungsweise die konservative kausale Ordnung bleibt erhalten.

## Status

Dieses Dokument definiert das Zielmodell für die nächste Compilerstufe. Es behauptet noch keinen erzeugten oder auf realer Motorola-68000-Hardware ausgeführten Maschinenkode.