# QIK-VRT Metagrammatik – Zielmodell Motorola 68000

## Zweck

Dieses Zielmodell begrenzt die Compiler-Rückseite bewusst auf einen kleinen, deterministischen Kern für die Motorola-68000-Architektur. Die Begrenzung dient Portabilität, Prüfbarkeit, Parallelisierbarkeit, Ressourcenschonung und reproduzierbarer Synchronisation.

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

## Der geschlossene Vier-Kapsel-Kern

Der gegenwärtige produktionsfreie Zielkern besitzt genau vier zulässige terminale Entscheidungen:

| Semantische Kapsel | ABI-Wert in `D0` | Exakte M68000-Wörter | Exakte Bytes |
|---|---:|---|---|
| `NOOP` | 0 | `MOVEQ #0,D0`; `RTS` | `70 00 4e 75` |
| `HOLD` | 1 | `MOVEQ #1,D0`; `RTS` | `70 01 4e 75` |
| `REOBSERVE` | 2 | `MOVEQ #2,D0`; `RTS` | `70 02 4e 75` |
| `REQUEST_AUTHORITY` | 3 | `MOVEQ #3,D0`; `RTS` | `70 03 4e 75` |

Damit ist präzise gemeint:

- Es existieren **vier semantische Terminalkapseln**.
- Jede Kapsel besteht im M68000-Backend aus einem kapselspezifischen `MOVEQ`-Wort und dem gemeinsamen Rückkehrwort `RTS`.
- Es wird **nicht** behauptet, dass alle modernen Prozessoren dieselben Opcode-Bits besitzen.
- Portabel ist die vierwertige Semantik und ihr beobachtbarer Vertrag, nicht die M68000-Bitkodierung selbst.

Unbekannte, produktive oder nicht gebundene Aktionen gehören nicht zu diesem geschlossenen Kern. Sie werden vor der Binärausgabe fail-closed abgewiesen.

## Vollständige rekursive Komposition

Der Vier-Kapsel-Kern ist unter erneuter Beobachtung geschlossen. Jeder zulässige Zyklus endet in genau einer der vier Kapseln; deren beobachteter Zustand darf anschließend wieder als gebundene Eingabe des nächsten Zyklus dienen:

```text
GEBUNDENER ZUSTAND(n)
→ SEMANTISCHE PRÜFUNG
→ KAUSALGRAPH(n)
→ {NOOP | HOLD | REOBSERVE | REQUEST_AUTHORITY}
→ BEOBACHTUNG UND NACHWEIS
→ GEBUNDENER ZUSTAND(n+1)
```

Rekursion bedeutet hier nicht, dass eine Kapsel sich selbst ungeprüft ausführt. Jeder neue Zyklus muss Bindung, Autorität, Evidenz, Zustand, Kausalordnung und Nachweis erneut prüfen. Damit gilt:

```text
RECURSION != UNBOUNDED AUTHORITY
REOBSERVATION != EFFECT_ACK
PREVIOUS_VALIDATION != CURRENT_VALIDATION
```

Der Zielzustand ist, jede zulässige nichtproduktive Fortsetzung des Metagrammatik-Kerns auf diese vier Kapseln zurückzuführen. Produktive Außenwirkungen bleiben außerhalb dieses v1-Kerns und benötigen einen gesondert gebundenen Effect-Ack- und Autoritätspfad.

## Plattformneutraler Portierungsvertrag

Eine Portierung auf eine andere heutige oder historische Plattform ist konform, wenn sie:

1. dieselben vier semantischen Ergebnisse `0..3` erhält;
2. für dieselbe validierte Eingabe dasselbe Ergebnis liefert;
3. unbekannte oder produktive Aktionen ohne Binärausgabe fail-closed abweist;
4. keine zusätzliche Autorität durch die Zielarchitektur einführt;
5. Beobachtung und Effect-Ack von der bloßen Rückkehr eines Maschinenprogramms getrennt hält;
6. exakte, reproduzierbare Testvektoren für alle vier Ergebnisse bereitstellt.

Andere Zielarchitekturen dürfen andere Instruktionen und Binärkodierungen verwenden. Konformität verlangt semantische Äquivalenz, nicht Opcode-Identität.

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

Die gleiche IR kann auf mehrere Mesh-Knoten partitioniert werden. Parallelisierung ist nur zwischen kausal unabhängigen Teilgraphen zulässig. Synchronisation erfolgt an expliziten Kanten beziehungsweise Effect-Ack-Grenzen, nicht an künstlichen globalen Sequenzpunkten.

## Kontinuierliche Verbesserung

Die kontinuierliche Verbesserung des Mesh-Repositories gilt ebenso für das Terminal Pattern, die Metagrammatik, die Compilersprache, die Causal IR und jedes Zielbackend. Änderungen müssen mindestens eines der folgenden Ziele messbar verbessern:

- Einfachheit;
- Anschlussfähigkeit;
- Nachvollziehbarkeit;
- Performance;
- Ressourcenschonung;
- Verständlichkeit.

Keine Optimierung darf dafür semantische Unterschiede, Autoritätsgrenzen, Evidenzbindungen, Kausalabhängigkeiten oder Nachweise entfernen. Eine Änderung ist nur dann eine Verbesserung, wenn der Vier-Kapsel-Vertrag und die fail-closed Eigenschaften durch Tests und Reobservation erhalten bleiben.

## Fail-closed

Kann der Compiler nicht beweisen, dass zwei Wirkungen unabhängig oder korrekt geordnet sind, erzeugt er keine optimistische Parallelisierung. Der Zustand lautet `HOLD` beziehungsweise die konservative kausale Ordnung bleibt erhalten.

## Status

Dieses Dokument definiert und bindet den gegenwärtigen Vier-Kapsel-Zielkern einschließlich seiner exakten M68000-Testvektoren und seines plattformneutralen Portierungsvertrags. Es behauptet keinen Nachweis einer Ausführung auf physischer Motorola-68000-Hardware und keine vollständige Reduktion beliebiger externer produktiver Wirkungen auf diesen v1-Kern.