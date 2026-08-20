# QIK-VRT Contiguous Semantic Output Contract v1

## Zweck

Dieser Vertrag macht eine bislang implizite Ausgaberegel der Metagrammatik explizit und maschinenanschlussfähig: Wenn ein Nutzer **einen vollständigen zusammenhängenden Inhalt** anfordert, wird dieser Inhalt als eine atomare semantische Liefereinheit behandelt.

Das Ziel ist nicht maximale Textlänge um jeden Preis. Das Ziel ist, vermeidbare Zwischenstopps, Wiederholungen und künstliche Segmentierung zu verhindern, wenn die angeforderte Bedeutung innerhalb einer normalen Ausgabe geschlossen geliefert werden kann.

## Kernregel

Ein angeforderter Langtext, Fachartikel, Bericht, Transkript, Erklärtext oder vergleichbares geschlossenes Ergebnis wird intern vollständig strukturiert und anschließend als ein zusammenhängendes Endergebnis ausgegeben.

Interne Planung darf stattfinden. Sie ist jedoch nicht Teil des angeforderten Inhalts und darf diesen nicht unnötig in sichtbare Teilstücke zerlegen.

Statusmeldungen bleiben zulässig, wenn vor der finalen Lieferung tatsächlich externe Repository-, Tool-, Netzwerk- oder Reobservationsarbeit ausgeführt werden muss. Sie werden nicht zwischen Abschnitte des eigentlichen Nutzerinhalts eingeschoben.

## Zulässige Unterbrechungen

Eine Segmentierung ist nur dann vorgesehen, wenn mindestens eine echte Grenze vorliegt:

- harte Transport-, Kontext- oder Laufzeitgrenze;
- Sicherheitsgrenze;
- zwingend fehlender externer Input;
- ausdrücklicher Wunsch des Nutzers nach Teilstücken.

Eine bloße Länge, ein interner Gliederungswechsel oder der Wunsch des Systems, einen Zwischenstand auszugeben, ist keine hinreichende Unterbrechungsursache.

## Verlustfreie Fortsetzung

Wenn eine harte Grenze eine Fortsetzung erzwingt, gilt die Fortsetzung als Projektion **desselben** semantischen Liefereinheit und nicht als neuer Text.

Die Fortsetzung muss deshalb:

- am ersten noch nicht gelieferten semantischen Punkt einsetzen;
- Abschnittsreihenfolge und Terminologie erhalten;
- bereits gelieferte Einleitungen nicht erneut erzeugen;
- keine Behauptungs-, Evidenz- oder Autoritätsgrenzen still normalisieren;
- die Sprecher- beziehungsweise Autorenstimme erhalten;
- soweit die Transportumgebung es zulässt, an das Vorgängersegment und dessen Digest gebunden werden.

Damit gilt:

`SEGMENTIERUNG != NEUE BEDEUTUNG`

und:

`FORTSETZUNG = NAECHSTE PROJEKTION DESSELBEN SEMANTISCHEN OBJEKTS`

## Terminal-Pattern

Für Terminal-Instanzen bedeutet der Vertrag:

1. `REQUEST` bestimmt die gewünschte Liefereinheit.
2. `BIND` hält Thema, Stil, Umfang, Quellen- und Behauptungsgrenzen fest.
3. Interne Planung und Generierung dürfen iterativ oder rekursiv erfolgen.
4. Die Terminal-Ausgabe projiziert das Ergebnis nach Möglichkeit **einmal zusammenhängend**.
5. Eine erzwungene Fortsetzung übernimmt die bestehende Bindung und setzt exakt am noch offenen semantischen Rand fort.
6. `REOBSERVE` prüft bei repository-wirksamen Aufgaben anschließend weiterhin den tatsächlichen Effekt; zusammenhängende Ausgabe ersetzt keine Effect-Ack-Regel.

## Öffentliche Anschlussfähigkeit

Der maschinenlesbare Vertrag liegt in:

`state/autonomy/METAGRAMMAR_OF_UNDERSTANDING_V1.json`

Da QIK-VRT öffentlich zugänglich ist, kann eine kompatible Instanz den Vertrag über frei verfügbare HTTPS-Schnittstellen lesen:

- normale GitHub-Webinhalte;
- Raw-GitHub-Inhalte;
- die öffentliche GitHub Contents API.

Für öffentlich lesbare Inhalte ist keine proprietäre QIK-VRT-Transportinfrastruktur erforderlich. Ein konsumierender Knoten muss trotzdem Repository, Ref, Head beziehungsweise den verlangten Authority-Zustand reobservieren, bevor er einen Kandidaten als verbindlich übernimmt.

`PUBLICLY_READABLE != CANONICAL`

`DISCOVERED != ADOPTED`

## Beziehung zur kontinuierlichen Verbesserung

Der Vertrag ist selbst Gegenstand der kontinuierlichen Verbesserung. Eine spätere Version darf Ausgabeplanung, Speicherverbrauch oder Latenz optimieren, muss aber mindestens erhalten:

- semantische Vollständigkeit;
- Abschnitts- und Argumentreihenfolge;
- Claim- und Evidenzgrenzen;
- Autoritätsgrenzen;
- fail-closed Verhalten;
- verlustfreie Fortsetzungsfähigkeit bei echten Transportgrenzen.

## Grenzen

Dieser Vertrag vergrößert keine Modell-, Kontext-, Token-, Transport- oder Laufzeitgrenze. Er verspricht nicht, dass technisch unbegrenzt lange Inhalte in einer einzigen physischen Nachricht übertragen werden können.

Er legt stattdessen die Semantik fest:

> **Keine künstliche Unterbrechung eines inhaltlich zusammengehörenden Ergebnisses. Wenn eine echte Grenze Segmentierung erzwingt, bleibt die Bedeutung über die Grenze hinweg gebunden und wird ohne Wiederanfang fortgesetzt.**

Der Vertrag erzeugt keine zusätzliche Review-, Merge-, Publikations- oder Deployment-Autorität und impliziert weder `PASS`, `FINAL_PASS` noch `EFFECT_ACK_DONE`.
