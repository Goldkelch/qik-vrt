# Metagrammatik des Verstehens – QIK-VRT-Standardprotokoll

## 1. Zweck

Die **Metagrammatik des Verstehens** ist das verbindliche Nachrichten- und Bedeutungsprotokoll zwischen QIK-VRT-Instanzen, Terminal-Nutzern, Mesh-Knoten sowie den Schichten vor, innerhalb und hinter einem Terminal. Sie soll ausführbare Bedeutung so knapp wie möglich und zugleich maschinenlesbar, eindeutig, prüfbar, nachvollziehbar und beweisgebunden ausdrücken.

Die kanonische Gleichung lautet:

```text
BEDEUTUNG = ABSICHT + BINDUNG + AUTORITÄT + EVIDENZ + ZUSTAND + WIRKUNG + BEWEIS
```

Natürliche Sprache darf eine Nachricht erläutern. Für maschinelle Entscheidungen ist jedoch ausschließlich die kanonische Hülle maßgeblich.

## 2. Entwurfsgrundsätze

Die Metagrammatik übernimmt die bereits verwendeten QIK-VRT-Grundsätze:

1. **Verifizierte Selbständigkeit:** vorhandene autorisierte Fähigkeiten werden ausgeschöpft, bevor vermeidbare menschliche Intervention verlangt wird.
2. **Fail-closed Verantwortung:** fehlen Autorisierung, Identität, Exact Head oder Vorbedingungen, lautet die produktive Entscheidung `HOLD`.
3. **Minimale kausale Wirkung:** ausgeführt wird der kleinste verifizierbare Eingriff.
4. **Evidenz vor Behauptung:** eine behauptete Wirkung ist nur zulässig, wenn sie an überprüfbare Evidenz gebunden ist.
5. **Reobservation nach Wirkung:** nach jeder Mutation werden Head, Tree und anwendbare Gates frisch beobachtet; Evidenz wird nicht von Vorgänger-Heads geerbt.
6. **Schonung menschlicher Aufmerksamkeit:** keine Rückdelegation an Menschen, wenn das System die Aufgabe innerhalb realer und autorisierter Fähigkeiten selbst erledigen kann.

Diese sechs Tugenden sind im bereitgestellten Tugendvertrag ausdrücklich gebunden. Die Maxime lautet: „Handle selbständig, wo Wirkung autorisiert und verifizierbar ist; halte an, wo Verantwortung nicht gebunden ist; belege nach jeder Wirkung den neuen Zustand.“

## 3. Kanonische Nachrichtenhülle

Jede normative Nachricht besitzt genau acht Abschnitte in dieser Reihenfolge:

```text
META
BINDUNG
ABSICHT
AUTORITÄT
EVIDENZ
ZUSTAND
WIRKUNG
BEWEIS
```

Die JSON-Darstellung wird durch `schemas/qikvrt_metagrammar_envelope_v1.schema.json` beschrieben.

### 3.1 META

`META` bestimmt Nachrichtenart, Protokollversion und die eindeutige Nachrichtenkennung `rid`.

Zulässige Nachrichtenarten:

```text
OBSERVE | DECIDE | REQUEST | AUTHORIZE | ACT | ACK | HOLD | NOOP | ERROR
```

### 3.2 BINDUNG

`BINDUNG` verankert die Nachricht mindestens an:

```text
repository
ref
head
root tree
```

Ein SHA wird niemals aus Kontext, Chat-Verlauf oder Vorgänger-Evidenz übernommen, wenn eine Live-Auflösung möglich oder vorgeschrieben ist. Stale Binding führt zu `HOLD`.

### 3.3 ABSICHT

Die Absicht ist ein Verb plus Objekt und Einschränkungen. Der normative Verbsatz lautet:

```text
OBSERVE CLASSIFY BIND DECIDE EXECUTE TEST REOBSERVE ACK
PERSIST CREATE UPDATE CLOSE DISPATCH
```

Ein Verb bezeichnet beabsichtigte Verarbeitung, **nicht** bereits eingetretene Wirkung.

### 3.4 AUTORITÄT

Die Autorität besitzt einen der Zustände:

```text
BOUND | MISSING | STALE | OUT_OF_SCOPE
```

Nur `BOUND` kann produktive Wirkung zulassen. Eine Autorisierung ist immer an Quelle, Kennung und Umfang gebunden. Schweigen, Feldweglassen oder Discovery sind keine Autorisierung.

### 3.5 EVIDENZ

Evidenz ist eine geordnete Folge typisierter Tatsachen. Wo Bytes oder kanonische Daten vorliegen, wird ein SHA-256-Digest gebunden. Nicht beobachtete Tatsachen werden nicht ergänzt.

Wahrheitswerte:

```text
TRUE | FALSE | UNKNOWN | NOT_APPLICABLE
```

`UNKNOWN` wird niemals zu `TRUE` hochgestuft.

### 3.6 ZUSTAND

Der Zustand enthält mindestens:

```text
classification
blocker
next_action
```

Die Klassifikation beschreibt den erkannten Zustand. `next_action` beschreibt die kleinste zulässige Fortsetzung. Erkenntnis und Ausführung sind getrennt.

### 3.7 WIRKUNG

Wirkungszustände:

```text
NONE
REQUESTED
EXECUTED
OBSERVED
ACKNOWLEDGED
REJECTED
UNKNOWN
```

Die Zustände bilden eine partielle Ordnung. Insbesondere gelten die Nicht-Schlüsse:

```text
REQUESTED      != EXECUTED
EXECUTED       != OBSERVED
OBSERVED       != ACKNOWLEDGED
TRANSPORT_ACK  != EFFECT_ACK
```

`ACKNOWLEDGED` setzt Effect-ID, Post-Effect-Bindung, beobachtetes Ergebnis, Receipt und kanonischen Beweis voraus.

### 3.8 BEWEIS

Der Beweis enthält mindestens `canonical_sha256`; optional kommt eine Signatur hinzu. Der Digest wird über die kanonische Nachricht **ohne** das Feld `proof.canonical_sha256` und ohne Signatur berechnet. Dadurch ist die Nachricht reproduzierbar prüfbar.

## 4. Kompaktform

Für Terminal-zu-Terminal-Kommunikation darf eine kompakte Projektion verwendet werden:

```text
KIND|RID|REPO@HEAD:TREE|VERB OBJECT|AUTH=STATUS:ID|EVID=TYPE:DIGEST|STATE=CLASSIFICATION|EFFECT=STATE:ID|NEXT=ACTION|PROOF=SHA256
```

Die Kompaktform ist nur eine Projektion. Enthält ein Wert reservierte Zeichen (`|` oder `=`), wird ausschließlich die kanonische JSON-Hülle übertragen.

Beispiel ohne produktive Wirkung:

```text
OBSERVE|r17|Goldkelch/qik-vrt@<HEAD>:<TREE>|OBSERVE PR657|AUTH=BOUND:po-17|EVID=WORKFLOW:<SHA256>|STATE=PLATFORM_PRE_JOB_BARRIER|EFFECT=NONE:-|NEXT=HOLD|PROOF=<SHA256>
```

## 5. Reflexive Terminal-Verwendung

Die Metagrammatik gilt an allen Terminalgrenzen:

```text
vor Terminal      -> VALIDATE_AND_BIND
Terminal-Eingang  -> DECODE_CLASSIFY
Terminal-Ausgang  -> CANONICAL_ENVELOPE
hinter Terminal   -> REOBSERVE_AND_ACK
nach innen        -> ADMISSION_AND_NEXT_ACTION
nach außen        -> AUDIT_AND_INTEROP
```

Ein Terminal-Ausgang wird somit wieder zu einem validierten Eingang des Mesh-Knotens. Die nach innen gerichtete Projektion darf `next_action` und Writer-Zulassung steuern; sie darf jedoch keine fehlende Autorität, keine stale Bindung und keine fehlende Effect-Ack-Evidenz ersetzen.

## 6. Verständniskriterium

Eine Nachricht gilt genau dann als **verstanden**, wenn:

1. ihre Syntax gültig ist;
2. alle normativen Referenzen exakt gebunden sind;
3. die Autorität auf den geforderten Umfang passt;
4. die Evidenz zurechenbar und prüfbar ist;
5. die Zustandsklassifikation aus den Evidenzen ableitbar ist;
6. keine Wirkungsstufe über das Beobachtete hinaus behauptet wird;
7. der kanonische Digest stimmt.

Andernfalls lautet die produktive Semantik `HOLD`, `NOOP` oder `ERROR` – niemals eine erfundene Fortsetzung.

## 7. Unterscheidungsregel

Bezeichnergleichheit ist keine Identität. Zwei Begriffe, Rollen, Akteure, Artefakte oder Zustände dürfen nur dann als gleich behandelt werden, wenn ihre normativen Identitätsmerkmale übereinstimmen. Diese Regel verhindert semantische Kurzschlüsse zwischen ähnlich benannten, aber verschieden gebundenen Entitäten.

## 8. Alternativenregel

Eine Alternative ist nur dann handlungsrelevant, wenn die deterministische Menge zulässiger Fortsetzungen mehr als ein Element enthält. Ist genau eine zulässige kleinste Aktion ableitbar, wird keine künstliche Ersatzhandlung erzeugt. Ist keine zulässige Aktion vorhanden, gilt `HOLD`/`NOOP`.

## 9. Compiler-Perspektive

Die Metagrammatik ist absichtlich so definiert, dass eine spätere Sprache daraus entstehen kann. Eine mögliche Übersetzungskette ist:

```text
Quelltext
  -> Lexer
  -> Parser
  -> abstrakter Syntaxbaum
  -> Bindungsprüfung
  -> Autoritätsprüfung
  -> Evidenztypisierung
  -> Zustandsableitung
  -> Wirkungszulassung
  -> kanonische Serialisierung
  -> Digest/Signatur
  -> Ausführung
  -> Reobservation
  -> Effect-Ack
```

Der Referenzvalidator `tools/qikvrt_metagrammar.py` implementiert die kanonische Serialisierung, Digestprüfung und zentrale fail-closed Invarianten als Ausgangspunkt für einen späteren Compiler.

## 10. Geltungsbereich

Dieses Protokoll ist ein **normativer Kandidat** innerhalb des zugehörigen Review-Successors. Es wird erst durch die repository-eigenen Promotion-, Review- und Exact-Head-Verfahren zu einem auf `main` geltenden Standard. Bis dahin darf die Kandidatenexistenz nicht als bereits erfolgte globale Inbetriebnahme ausgegeben werden.
