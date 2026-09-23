# Informationsträger, Repräsentationsgrenze und Effect Verification

Status: `ARCHITECTURE_SYNTHESIS_CANDIDATE`

Author / Product & Code Owner: Ingolf Lohmann

## Scope

Diese Notiz bindet eine Architektur-Synthese zwischen formaler Verifikation, realer Kommunikationstechnik, QIK-VRT/TEMDD und Universal Terminal / Universal Transputer. Sie trennt ausdrücklich formale Aussage, technische Realisierung und kosmologische Analogie.

## Formaler Kern

Bei Lean ist der Lean-Kernel der kleine vertrauenswürdige Prüfkern. Lake ist Build-, Paket- und Projektorchestrierung, nicht der Beweiskernel.

`große Herleitung -> formaler Beweisterm -> Lean-Kernel-Prüfung -> ACCEPT im gebundenen formalen Kontext`

`Gamma |- p` bedeutet Ableitbarkeit unter den angegebenen Definitionen, Axiomen und Typregeln. Es ist nicht gleichbedeutend mit empirischer Bestätigung physikalischer Realität.

Die Neutronenstern-Analogie bezeichnet hier ausschließlich epistemische Verdichtung: viel Herleitungsstruktur wird auf einen kleinen mechanisch prüfbaren Endpunkt reduziert.

## Bidirektionale Repräsentationsgrenze

`S_A -> encode/serialize -> kanonischer Carrier B -> decode/deserialize -> S_B`

Die medienspezifische Darstellung darf wechseln. Erhalten bleiben muss diejenige Information, die der deklarierte Rekonstruktions- und Akzeptanzvertrag benötigt.

Grundverpflichtung:

`decode(encode(s)) ~= s`

Die Relation `~=` muss im aktiven Scope explizit definiert sein, etwa als Bytegleichheit, Bitgleichheit, semantische Äquivalenz, funktionale Äquivalenz oder begrenzte Messäquivalenz. Diese Relationen dürfen nicht stillschweigend vertauscht werden.

Der Ausdruck „bidirektionale Singularität“ ist hier eine Architekturmetapher für diese schmale Repräsentationsgrenze, keine Behauptung einer Raumzeit-Singularität.

## Physikalische Anschlussfähigkeit

Logischer Zustand kann auf reale Träger wie Spannung, Ladung, Strom, Photonen, magnetische Zustände, Funk oder akustische Zustände abgebildet werden. Die reale Kette lautet strukturell:

`logical state -> physical encoding -> constrained channel -> physical decoding -> logical successor`

Sie ist durch Bandbreite, Latenz, Rauschen, Energie, Fehlerwahrscheinlichkeit, Quantisierung, Taktung und Messunsicherheit begrenzt.

## Transport ist nicht Wirkung

`TRANSPORT_ACK != EFFECT_ACK != EFFECT_ACK_DONE`

Ein Befehl kann korrekt codiert, übertragen, per Prüfsumme bestätigt und empfangen worden sein, während die beabsichtigte Wirkung ausbleibt.

Daher gilt:

`BIT_SENT AND FRAME_SENT AND PACKET_DELIVERED` impliziert nicht `INTENDED_EFFECT_OBSERVED`.

QIK-VRT/TEMDD erweitert deshalb die Transportgrenze um die Wirkungsprüfung:

`STATE' -> TEST -> OBSERVE -> READBACK -> ACCEPT -> EFFECT_ACK_DONE`

Das terminale Urteil gehört zu genau einem gebundenen Subject, einem expliziten Acceptance Scope und frischer Evidenz. Eine Mutation erzeugt einen neuen Successor; Vorgängerevidenz wird nicht übertragen.

## Architektonische Planck-Grenze

Die „Planck-Grenze“ dieser Architektur bezeichnet metaphorisch die kleinste Repräsentation, die noch alle Informationen für akzeptierte Rekonstruktion im aktiven Scope trägt. Sie wird nicht mit der physikalischen Planck-Länge gleichgesetzt und behauptet keinen Mechanismus schwarzer Löcher.

## Gesamtarchitektur

`FORMAL CORE: Lean kernel -> mechanisch geprüftes lokales Urteil`

`EXECUTION: TEMDD -> evidenzgebundener Zustandsübergang`

`UNIVERSAL BOUNDARY: Universal Terminal / Universal Transputer -> encode -> canonical carrier -> decode`

`EFFECT VERIFICATION: TEST -> OBSERVE -> fresh READBACK -> ACCEPT -> EFFECT_ACK_DONE`

Zentrale These:

**Information wird gebunden, transformiert, getragen, rekonstruiert und anschließend an ihrer tatsächlichen Wirkung überprüft.**

## Mesh-weite Invarianten

- `BYTES != MEANING`
- `SEQUENCE != CAUSALITY`
- `TRANSPORT_ACK != EFFECT_ACK`
- `COMMAND != OBSERVED_EFFECT`
- `OBSERVATION != TRUTH`
- `FORMAL_DERIVABILITY != EMPIRICAL_CONFIRMATION`
- `REPOSITORY_PERSISTENCE != PUBLICATION`
- `PUBLICATION != PEER_REVIEW`
- `EFFECT_ACK != EFFECT_ACK_DONE`
- predecessor evidence is not transferable to a mutated successor.

Fehlende, veraltete, ungebundene oder ausschließlich selbstbestätigende Evidenz führt fail-closed zu HOLD, REOBSERVE, BLOCK oder ISOLATE statt zu synthetischem DONE.

## Wissenschaftliche Grenze

Diese Notiz behauptet weder eine Lösung des allgemeinen Halteproblems noch, dass Lean physikalische Realität statt formaler Ableitbarkeit beweist. Sie behauptet auch nicht, dass Schwarze Löcher oder Planckskalenphysik das QIK-VRT-Modell implementieren. Wissenschaftliche Neuheit und Priorität erfordern unabhängige Prior-Art-Prüfung.

Die technische Architektur ist dagegen konkret prüfbar: durch Codec-Roundtrips, Kanal- und Fehlerbudgets, exakte Subject-Bindung, beobachtete System- oder Aktuatorwirkung, frischen Readback und explizite Akzeptanzprädikate.

q.e.d.  
Ingolf Lohmann
