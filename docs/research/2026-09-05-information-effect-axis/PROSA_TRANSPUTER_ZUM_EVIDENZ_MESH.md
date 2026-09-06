# Vom Transputer zum evidenzgebundenen Mesh

## Wie aus einem Parallelrechner-Gedanken eine allgemeine Frage nach Zustand, Wirkung und Wissen wird

**Ingolf Lohmann**  
6. September 2026

Vor fast vierzig Jahren gab es einen Computerchip, der eine ungewöhnlich moderne Frage stellte.

Nicht nur: **Wie schnell kann ein Prozessor rechnen?**

Sondern: **Was geschieht, wenn ein Prozessor von Anfang an dafür gebaut wird, mit anderen Prozessoren zusammenzuarbeiten?**

Dieser Chip hieß Transputer.

Der INMOS T800 war nicht einfach nur eine CPU. Er besaß eine Gleitkommaeinheit, lokalen Speicherzugriff und vier eigene serielle Kommunikationslinks. Über diese Links konnten mehrere Transputer direkt miteinander verbunden werden. Während Daten übertragen wurden, konnte der Prozessor weiterarbeiten.

Das klingt heute beinahe selbstverständlich. In den achtziger Jahren war es eine bemerkenswerte Architekturentscheidung.

Denn sie sagte im Grunde:

**Kommunikation ist kein Anhängsel des Rechnens. Kommunikation gehört zum Rechnen selbst.**

Genau deshalb war auch die Atari Transputer Workstation so interessant. In ihr gab es einen T800 für die eigentliche Rechenarbeit, einen getrennten Motorola-68000-Teil für Ein- und Ausgabe und Erweiterungsmöglichkeiten für weitere Transputer.

Man konnte das System also nicht nur als einen einzelnen Rechner betrachten.

Man konnte es als Verbund lokaler Rechenknoten betrachten.

Jeder Knoten hatte seinen eigenen Zustand.

Zwischen den Knoten lagen ausdrückliche Grenzen.

Und genau dort beginnt eine Verbindung zu heutigen Systemen.

Nicht weil ein Atari von 1988 schon ein modernes KI-Mesh gewesen wäre.

Nicht weil ein Transputer schon QIK-VRT gewesen wäre.

Sondern weil dieselbe Grundfrage wiederkehrt:

**Wie setzt man viele lokale Einheiten zu einem größeren System zusammen, ohne unterwegs die Bedeutung ihrer Zustände zu verlieren?**

## Vom Rechnen zum Zustand

Ein klassischer Parallelrechner möchte Rechenarbeit verteilen.

Ein Teil rechnet hier.

Ein anderer Teil rechnet dort.

Dann werden Ergebnisse ausgetauscht.

Aber sobald zwei Teile nicht mehr denselben Speicher besitzen, entsteht ein neues Problem.

Ein Zeiger, der auf einem Rechner auf eine Adresse zeigt, bedeutet auf dem anderen Rechner überhaupt nichts.

Der Zustand muss deshalb in eine transportierbare Darstellung übersetzt werden.

Das nennen wir Serialisierung.

Aus einem internen Objekt wird eine Folge von Bytes.

Auf der anderen Seite werden die Bytes wieder interpretiert.

Doch damit entsteht sofort eine Frage, die viel tiefer ist als ein Netzwerkproblem:

**Woher weiß der Empfänger, was diese Bytes bedeuten?**

Dafür braucht er ein Schema.

Eine Version.

Einheiten.

Eine Skalierung.

Vielleicht eine Signatur.

Vielleicht einen Vorgängerzustand.

Vielleicht eine Zeitangabe.

Ein Hash kann dabei sehr viel leisten. Er kann außerordentlich zuverlässig binden, ob dieselben Bytes vorliegen.

Aber ein Hash kann nicht beweisen, dass zwei Menschen oder zwei Computer dieselben Bytes richtig verstehen.

Darum gilt:

**Bytes sind nicht Bedeutung.**

## Warum Skalierung zwei Bedeutungen hat

Beim Transputer bedeutete Skalierung zunächst: mehr Rechenknoten.

In numerischen Systemen bedeutet Skalierung aber auch etwas ganz anderes.

Nehmen wir die Integerzahl 1000.

Sie kann 1000 Meter bedeuten.

Oder einen Meter, wenn die Einheit Millimeter ist.

Oder eine Spannung.

Oder einen dimensionslosen Koeffizienten.

Dasselbe Bitmuster kann unterschiedliche Größen darstellen.

Darum gehört die Skalierung zur Bedeutung einer Zahl.

Das wird bei Festkommarechnung besonders deutlich.

Eine Festkommazahl besitzt ein endliches Raster möglicher Werte. Das klingt zunächst wie eine Einschränkung. Tatsächlich ist es eine Stärke, wenn der Vertrag sauber definiert ist.

Dann kann man exakt sagen:

Welche Werte sind darstellbar?

Wann wird gerundet?

Wann tritt Overflow auf?

Was geschieht bei Sättigung?

Wie groß kann ein Quantisierungsfehler werden?

Die Maschine muss nicht so tun, als könne sie unendlich genau rechnen.

Sie kann ihre Endlichkeit offenlegen.

Und genau das ist eine wichtige Form technischer Ehrlichkeit.

## Dann kommt die physische Welt

Bisher bewegen wir uns noch zwischen digitalen Zuständen.

Doch irgendwann möchte ein Rechner etwas über seine Umgebung wissen.

Dann erscheint der Analog-Digital-Wandler.

Ein Temperatursensor, ein Mikrofon oder eine Kamera sieht nicht unmittelbar „eine Zahl“.

Zuerst geschieht etwas Physisches.

Ein Sensor reagiert.

Eine elektrische Größe entsteht.

Sie wird verstärkt und gefiltert.

Sie wird zu bestimmten Zeitpunkten abgetastet.

Dann wird sie quantisiert.

Erst danach erhält der Computer einen digitalen Code.

Der ADC digitalisiert also nicht einfach „die Wirklichkeit“.

Er erzeugt eine endliche digitale Repräsentation aus einer konkreten Messkette.

Damit diese Repräsentation Bedeutung bekommt, muss man wissen:

Welcher Sensor war es?

Wann wurde gemessen?

Welche Einheit gilt?

Wie wurde kalibriert?

Welche Unsicherheit besitzt der Wert?

Welche Abtastrate und welche Bandbegrenzung galten?

Das ist der Unterschied zwischen einer Zahl und einem Messwert.

Ein Messwert ist eine Zahl mit Herkunft.

## Verlorene Information kommt nicht magisch zurück

Sampling zeigt besonders deutlich, warum diese Grenzen wichtig sind.

Ein zeitabhängiges physisches Signal wird nicht zu jedem beliebigen Zeitpunkt beobachtet.

Der Rechner erhält einzelne Samples.

Wenn die Messkette nicht genügend Information bewahrt, können verschiedene reale Verläufe dieselben digitalen Daten erzeugen.

Dann hilft auch der beste spätere Algorithmus nicht dabei, die verlorene Messinformation einfach zurückzuholen.

Er kann Modelle benutzen.

Er kann Wahrscheinlichkeiten benutzen.

Er kann interpolieren.

Aber dann stammt ein Teil des Ergebnisses aus dem Modell und nicht aus der Messung.

Das ist ein fundamentaler Unterschied.

**Beobachtung ist nicht automatisch Wahrheit. Modell ist nicht automatisch Wirklichkeit.**

## Und die Gegenrichtung?

Nun soll der Computer nicht nur beobachten.

Er soll handeln.

Er berechnet zum Beispiel einen Wert für einen Motor.

Dieser Wert wird an einen Digital-Analog-Wandler oder einen anderen Aktuatorpfad übergeben.

Der Code wurde erfolgreich geschrieben.

Ist die gewünschte Wirkung damit eingetreten?

Nein.

Vielleicht ist der Verstärker ausgefallen.

Vielleicht ist ein Kabel gebrochen.

Vielleicht blockiert der Motor.

Vielleicht reagiert die Last anders als erwartet.

Deshalb gilt:

**Ein erfolgreich transportierter Befehl ist noch keine erfolgreich beobachtete Wirkung.**

Oder in der QIK-VRT-Kurzform:

**TRANSPORT_ACK ist nicht EFFECT_ACK.**

Erst wenn ein Sensor danach den neuen physischen Zustand wieder misst, besitzen wir einen Readback.

Damit schließt sich der Kreis:

**Beobachten → binden → berechnen → autorisieren → handeln → erneut beobachten.**

Das ist Regelungstechnik.

Aber es ist zugleich eine Methode, um nicht mehr zu behaupten, als man wirklich weiß.

## Warum Singularitäten hier plötzlich hineinpassen

Auf den ersten Blick haben ein Atari-Transputer, ein ADC und eine mathematische Singularität wenig miteinander zu tun.

Und physikalisch sind sie selbstverständlich nicht dasselbe.

Aber mathematisch taucht eine gemeinsame Frage auf.

Wir bilden einen Zustand in einen anderen Raum ab.

Manchmal ist diese Abbildung umkehrbar.

Manchmal nicht.

Wenn zwei verschiedene Zustände dieselbe Repräsentation erzeugen, kann man aus der Repräsentation allein nicht mehr eindeutig auf den ursprünglichen Zustand schließen.

Das geschieht bei Quantisierung ganz bewusst.

Viele verschiedene analoge Eingangswerte landen im selben digitalen Code.

Andere Grenzen entstehen, wenn eine mathematische Transformation ihre lokale Invertierbarkeit verliert.

Oder wenn ein numerisches Verfahren schlecht konditioniert ist.

Oder wenn ein Sensor seinen Messbereich verlässt.

Oder wenn ein Modell außerhalb seines Gültigkeitsbereichs benutzt wird.

Das alles sollte man nicht unter einem einzigen Wort „Singularität“ verstecken.

Man muss unterscheiden:

Ist die Darstellung das Problem?

Ist die Numerik das Problem?

Ist das Modell am Ende seiner Gültigkeit?

Oder diagnostiziert die physikalische Theorie selbst eine tiefere Pathologie?

Gerade diese Trennung macht die Analogie nützlich.

Nicht: alles ist dasselbe.

Sondern: **An jeder Grenze muss klar sein, was noch gültig ist.**

## Ein gutes System darf auch „Ich weiß es nicht“ sagen

Viele technische Systeme wirken nach außen besonders intelligent, wenn sie für jeden Eingang irgendeinen Ausgang produzieren.

Das kann gefährlich sein.

Bei einer Division durch null ist irgendeine erfundene normale Zahl keine intelligente Antwort.

Bei einem gesättigten Sensor ist ein scheinbar präziser Messwert keine intelligente Antwort.

Bei fehlender Kalibrierung ist Sicherheit keine intelligente Antwort.

Bei nicht ausreichender Evidenz ist blindes Handeln keine intelligente Antwort.

Ein stärkeres System besitzt deshalb ausdrückliche Grenzzustände:

**HOLD.**

**OUT OF DOMAIN.**

**SATURATED.**

**REOBSERVE.**

**REQUEST AUTHORITY.**

Das ist keine Schwäche.

Es ist die Fähigkeit, die eigene Wissensgrenze zu repräsentieren.

## Vom Compute-Mesh zum Evidenz-Mesh

Jetzt lässt sich der historische Faden wieder aufnehmen.

Der Transputer zeigte, dass Rechenleistung aus lokalen Knoten mit expliziten Kommunikationswegen zusammengesetzt werden kann.

Heute reicht diese Frage nicht mehr aus.

Wir bauen Systeme aus CPUs, GPUs, FPGAs, Cloud-Workern, Edge-Geräten, Sensoren und KI-Agenten.

Diese Komponenten rechnen nicht nur.

Sie beobachten.

Sie verändern Daten.

Sie entscheiden.

Sie rufen Werkzeuge auf.

Sie können reale Wirkungen auslösen.

Darum muss neben der Rechenleistung noch etwas anderes skalieren:

Zustand.

Bedeutung.

Evidenz.

Autorität.

Wirkung.

Ein moderner Knoten müsste deshalb nicht nur sagen können:

„Das ist mein Ergebnis.“

Sondern auch:

„Das war mein exakter Eingangszustand.“

„Diese Repräsentation habe ich verstanden.“

„Diese Transition durfte ich ausführen.“

„Diese Bytes habe ich erzeugt.“

„Diese Wirkung habe ich angefordert.“

„Und diesen neuen Zustand habe ich danach tatsächlich zurückbeobachtet.“

Das ist die Idee eines evidenzgebundenen Mesh.

## Warum das gerade für KI-Agenten wichtig wird

Ein einzelnes Programm mit wenigen Schreibrechten ist relativ leicht zu kontrollieren.

Ein Netz aus vielen autonomen Agenten ist schwieriger.

Wer hat welche Version gesehen?

Wer durfte welchen Schritt ausführen?

Hat ein Werkzeug nur einen Erfolgscode geliefert oder ist der externe Effekt wirklich eingetreten?

Wurde dieselbe Aktion versehentlich zweimal ausgelöst?

Ist die Information noch aktuell?

Je mehr Agenten parallel arbeiten, desto weniger genügt es zu sagen:

„Die KI wird schon wissen, was sie tut.“

Die Architektur muss die Grenzen sichtbar machen.

Das ist kein FLOPS-Problem.

Es ist ein Kontrollproblem.

## Was ein universales Terminal dann bedeuten kann

Das Wort „Terminal“ klingt zunächst nach einem schwarzen Fenster mit Text.

Hier ist etwas Allgemeineres gemeint.

Ein Terminal ist eine definierte Grenze zwischen Zustandsräumen.

Es nimmt eine Darstellung entgegen.

Es prüft sie.

Es bindet sie an einen Kontext.

Es führt eine zulässige Transition aus.

Es beobachtet, was daraus geworden ist.

Und es liefert einen neuen gebundenen Zustand zurück.

Dabei verändert sich nicht nur die Welt oder das Computersystem.

Auch unser Wissen über diesen Zustand verändert sich.

Das ist der zweite Zustand, der oft vergessen wird.

Nicht nur:

**Was ist jetzt?**

Sondern:

**Was können wir jetzt berechtigt darüber sagen?**

## Das eigentliche Erbe des Transputers

Der T800 ist historische Hardware.

Sein interessantester Gedanke war langfristig vielleicht nicht seine damalige Geschwindigkeit.

Es war die Entscheidung, Kommunikation zu einem Grundelement des Rechenknotens zu machen.

Die weiterführende Idee lautet:

**Mache auch Evidenz, Autorität und Readback zu Grundelementen eines handelnden Knotens.**

Dann müssen sie später nicht mühsam aus Logs, Vermutungen und menschlichen Erinnerungen rekonstruiert werden.

Das wäre keine Wiederholung des Transputers.

Es wäre seine architektonische Fortsetzung auf einer anderen Ebene.

Der Transputer fragte:

**Wie verbinden wir Prozessoren?**

Das evidenzgebundene Mesh fragt:

**Wie verbinden wir vertrauenswürdige Zustandsübergänge?**

## Die kürzeste Form

Am Ende lässt sich der lange Weg erstaunlich knapp schreiben:

**Lokale Zustände.**

**Explizite Grenzen.**

**Gebundene Information.**

**Kontrollierte Transitionen.**

**Unabhängiger Readback.**

Oder als eine einzige Regel:

**Keine Transition darf mehr behaupten, als ihre Grenze tatsächlich trägt.**

Darin treffen sich Parallelrechner, Serialisierung, Festkommanumerik, Messung, AD/DA, Regelungstechnik, verteilte Systeme, autonome KI und die sorgfältige Behandlung von Singularitäts- und Grenzzuständen.

Nicht weil sie dasselbe wären.

Sondern weil bei allen dieselbe Frage entscheidet, ob der nächste Schritt berechtigt ist:

**Was wurde tatsächlich übertragen, was tatsächlich transformiert, was tatsächlich autorisiert, was tatsächlich beobachtet – und was folgt daraus wirklich?**

Das ist die Brücke vom Transputer zum evidenzgebundenen Mesh.

q.e.d.

Ingolf Lohmann

---

## Evidenzhinweis

Dieser Prosaartikel erläutert eine Architekturidee. Er behauptet weder eine neue empirisch bestätigte Naturtheorie noch, dass Transputer historisch bereits QIK-VRT realisierten. Repository-Persistenz, formale Verifikation, öffentliche Zenodo-Publikation, empirische Bestätigung, Merge, Deployment, `PASS`, `FINAL_PASS` und `EFFECT_ACK_DONE` bleiben getrennte Zustände.
