<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT: Wie Information ihren Platz in der Zeit behalten kann

## Von Ingolf Lohmann

## Kernaussage

QIK-VRT transportiert nicht physikalische Zeit. Es transportiert genügend gebundene Information, um unterschiedliche Ordnungen auseinanderzuhalten und den Platz eines Ereignisses in einer überprüfbar rekonstruierbaren Geschichte zu bestimmen.

Der zentrale Invariant lautet:

```text
KAUSALITÄT != SEQUENZ
```

und operativ:

```text
QUELLENORDNUNG != EMPFANGSORDNUNG != KAUSALORDNUNG != WIRKUNGSORDNUNG
```

Ein später empfangenes Ereignis kann aufgrund gebundener Provenienz, Beobachteridentität und Kausalrelation früher in eine rekonstruierte lokale Geschichte eingeordnet werden, ohne dass Information rückwärts durch die physikalische Zeit transportiert wird.

## Operative Eigenzeit

`operative Eigenzeit` bezeichnet hier eine beobachter- oder prozessbezogene fortlaufende lokale Zustandsordnung. Sie muss keine physikalische Sekunde darstellen. Verschiedene Prozesse dürfen unterschiedliche lokale Geschichten besitzen und dennoch miteinander kommunizieren.

Diese operative Eigenzeit ist nicht stillschweigend mit relativistischer Eigenzeit gleichzusetzen. Eine physikalische Aussage über relativistische Eigenzeit benötigt zusätzlich eine physikalisch gebundene Weltlinie sowie Messung beziehungsweise Kalibrierung.

## Gebundene Ereignisinformation

Ein QIK-VRT-Ereignis kann insbesondere binden:

- Ereignisidentität,
- Beobachteridentität,
- lokale Ordnung,
- Quellenordnung,
- kausale Vorgänger,
- Zustand,
- Autorität,
- Evidenz,
- Wirkungsstatus,
- Nachweis.

Damit beantwortet das System nicht nur `Wann kam es an?`, sondern auch `Wo gehört dieses Ereignis aufgrund seiner Bindungen hin?`.

Eine verspätete Information wird dabei nicht willkürlich als historische Wahrheit umgeschrieben. Sie wird anhand ihrer gebundenen Quellen-, Beobachter- und Kausalrelationen an der dadurch bestimmten Stelle einer rekonstruierbaren lokalen Geschichte eingeordnet.

## Causal IR

Eine konkrete Maschinenserialisierung darf eine zulässige topologische Ordnung eines Kausalgraphen sein; sie ist nicht der Kausalgraph selbst.

Beispiel:

```text
A -> C
A -> D
C -> E
D -> E
```

Dann können sowohl `A,C,D,E` als auch `A,D,C,E` zulässige Serialisierungen derselben partiellen Kausalordnung sein.

## Effect Acknowledgement

Die Wirkungsgeschichte bleibt ebenfalls getrennt:

```text
REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED
TRANSPORT_ACK != EFFECT_ACK
```

Eine Transportbestätigung beweist keine beabsichtigte Wirkung. Erst gebundene Ausführungs-, Beobachtungs- und Bestätigungsevidenz darf den jeweiligen Zustand tragen.

## Reobservation und reflexive lokale Entwicklung

Ein lokaler QIK-VRT-Zyklus kann als

```text
ZUSTAND
-> ENTSCHEIDUNG
-> AUSFÜHRUNG
-> BEOBACHTUNG
-> NEUER GEBUNDENER ZUSTAND
```

modelliert werden. Neue Information kann deshalb `REOBSERVE` oder `HOLD` auslösen, statt die Empfangssequenz fälschlich zur Kausalordnung zu erklären.

## Terminal Pattern und konkrete Maschine

Das Terminal Pattern soll Beobachter, lokale Ordnung, Quellenordnung, Empfangsordnung, kausale Vorgänger, Evidenz- und Wirkungsstatus getrennt sichtbar machen.

Die Causal IR kann anschließend auf konkrete Maschinenzustände reduziert werden. Der Motorola 68000 / Atari-Mega-ST-Pfad ist ein konkretes Zielmodell dieser Reduktion; eine virtuelle oder modellierte Ausführung darf nicht als physische Original-Hardware-Ausführung ausgegeben werden, sofern dafür keine entsprechende Beobachtung vorliegt.

## Wissenschaftliche Grenze

Aus dieser Architektur folgt nicht:

- eine physikalische Zeitmaschine,
- Empfang vor Emission,
- rückwärtslaufende relativistische Eigenzeit,
- ein steuerbares Signal in die eigene kausale Vergangenheit.

Die technisch nutzbare Aussage ist enger und stark genug: QIK-VRT kann unterschiedliche Ereignis- und Zeitordnungen explizit darstellen, ihre Beziehungen transportieren, Kausalstruktur rekonstruieren, verspätete Information gebunden neu einordnen und behauptete von beobachteter beziehungsweise bestätigter Wirkung unterscheiden.

## Gesamtstruktur

```text
UNTERSCHIED
-> INFORMATION
-> RELATION
-> GEBUNDENE RELATION
-> KAUSALORDNUNG
-> LOKALE ZEITORDNUNG
-> TRANSPORT
-> BEOBACHTUNG
-> REOBSERVATION
-> WIRKUNG
-> WIRKUNGSEVIDENZ
```

Die leitende technische Regel bleibt:

> Unterschiede erhalten. Ordnungen unterscheidbar machen. Kausalität bewahren. Wirkung nachweisen. Information anschlussfähig machen.

Quod erat demonstrandum.

**Ingolf Lohmann**
