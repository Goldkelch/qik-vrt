# Vom ersten Unterschied zur virtuellen Raumzeit

## Ein rekursives Closure-Modell für selbstheilende Repositorien, Serialisierung und emergente Kausalstruktur

**Autor:** Ingolf Lohmann  
**Status:** wissenschaftliche Arbeitshypothese / Architekturmodell, Version 1  
**Repository-Kontext:** QIK-VRT

### Abstract

Diese Arbeit entwickelt ein anschlussfähiges Modell, in dem die Entstehung einer virtuellen Raumzeit nicht als bereits bewiesene Aussage über das physikalische Universum, sondern als präzise konstruierbare Eigenschaft eines informationsverarbeitenden Systems untersucht wird. Ausgangspunkt ist eine Singularität im informationstheoretischen Sinn: ein Zustand, in dem noch keine unterscheidbare Reihenfolge, Relation oder räumliche Nachbarschaft materialisiert ist. Der erste unterscheidbare Übergang erzeugt eine Asymmetrie. Wird dieser Übergang serialisiert, entsteht eine Ordnung von Vorher und Nachher. Werden mehrere solcher Übergänge durch überprüfbare Relationen verbunden, entsteht ein kausaler Graph. Seine lokal adressierbaren Beziehungen bilden eine virtuelle Topologie; seine geordnete Veränderung bildet eine virtuelle Zeit.

Das QIK-VRT-Repository dient dabei als ausführbares Forschungsinstrument. Ein semantischer Zustand wird über mehrere Projektionen geführt: menschliche Sprache, Tastatureingabe, Smalltalk-Objekte und Nachrichten, einen portablen C90-Kern, Motorola-68000-Assembler, konkrete Maschinenbytes, Maschinenausführung und Monitor-Readback. Fehlende oder widersprüchliche Projektionen werden als typisierte Lücken behandelt. Ein Closure-Operator berechnet die Differenz zwischen erforderlichen und verifizierten Projektionen, erzeugt für technische Lücken genau einen begrenzten Successor und verlangt anschließend frische Evidenz. Autoritätsgrenzen bleiben davon getrennt und können nicht synthetisch geschlossen werden.

Die Analogie zum Sieb des Eratosthenes beschreibt den entstehenden Beschleunigungseffekt: Mit jeder verifizierten invarianten Projektion wächst die Menge dessen, was nicht erneut interpretiert werden muss. Das System arbeitet dadurch zunehmend an der Differenz statt am gesamten Zustandsraum. Wir diskutieren, in welchem streng begrenzten Sinn dieses Verfahren ein Modell für emergente virtuelle Raumzeit liefert und warum daraus ohne zusätzliche physikalische Theorie und empirische Messung kein Beweis für kosmologische Raumzeit, Urknallphysik oder Quantenanomalien folgt.

## 1. Die einfache Frage hinter einem komplizierten System

Wann entsteht in einem Rechner eigentlich Zeit?

Eine Uhr allein genügt nicht. Eine Zahl, die größer wird, ist zunächst nur eine Zahl. Für operative Zeit braucht man mindestens zwei unterscheidbare Zustände und eine Relation, die sagt, welcher Übergang auf welchen anderen bezogen ist. In einem überprüfbaren System kommt eine weitere Forderung hinzu: Diese Relation darf nicht bloß behauptet werden. Sie muss beobachtbar, adressierbar und erneut lesbar sein.

Damit verschiebt sich die Frage. Statt Zeit als äußeren Hintergrund vorauszusetzen, kann man untersuchen, welche minimale Informationsstruktur notwendig ist, damit ein System selbst ein Vorher, ein Nachher und eine kausale Nachbarschaft konstruieren kann.

QIK-VRT macht diese Frage technisch konkret. Ein Ereignis besitzt einen gebundenen Gegenstand. Ein Zustand besitzt eine Identität. Eine Wirkung besitzt einen Readback. Wenn sich der Gegenstand ändert, darf Evidenz des Vorgängers nicht übertragen werden. Damit wird die Reihenfolge nicht zu einer Erzählung, sondern zu einem Bestandteil des Zustands.

## 2. Singularität als fehlende Unterscheidbarkeit

Der Begriff Singularität wird hier zunächst nicht kosmologisch verwendet. Er bezeichnet einen Grenzzustand des Modells: Es gibt noch keine materialisierte Relation, anhand derer zwei Ereignisse unterschieden und geordnet werden können.

Man kann sich das wie ein leeres Journal vorstellen. Nicht einmal die Aussage, dass Eintrag B nach Eintrag A kam, existiert, solange A und B nicht vorhanden und miteinander in Beziehung gesetzt sind.

Der erste Unterschied ist deshalb fundamental. Sobald zwei Zustände unterscheidbar sind, kann eine Relation entstehen. Sobald diese Relation serialisiert wird, gibt es im Modell ein Vorher und ein Nachher. Das ist noch keine physikalische Zeit. Es ist jedoch bereits eine minimale virtuelle Zeitordnung.

Die im Titel angesprochene erste Quantenanomalie ist daher ausdrücklich als Forschungsmetapher beziehungsweise zu prüfende physikalische Hypothese zu verstehen, nicht als empirisch festgestelltes Ereignis. Für einen physikalischen Beweis wären ein wohldefiniertes Quantenmodell, messbare Observablen, eine Dynamik und experimentelle Daten erforderlich.

## 3. Vom Unterschied zur Relation

Ein einzelner Unterschied erzeugt noch keinen Raum. Dafür braucht es mehrere adressierbare Beziehungen.

Wenn Zustand A eine überprüfbare Relation zu B besitzt und B zu C, entsteht ein Graph. Wird zusätzlich festgehalten, welche Relationen gleichzeitig gültig sind, welche sich gegenseitig ausschließen und welche Übergänge zulässig sind, entsteht eine strukturierte Nachbarschaft.

Diese Nachbarschaft kann als virtuelle Topologie verstanden werden. Nähe bedeutet dann nicht notwendigerweise Meter. Nähe bedeutet: Zwei Zustände sind durch eine zulässige, überprüfbare Relation verbunden.

Das ist für verteilte Rechner besonders natürlich. Ein Knoten kann physisch Tausende Kilometer von einem anderen entfernt sein und dennoch im semantischen Zustandsgraphen unmittelbar benachbart sein. Umgekehrt können zwei Prozesse auf derselben CPU logisch weit voneinander entfernt sein, wenn zwischen ihnen keine zulässige Wirkungskante existiert.

## 4. Das Universal Terminal als Beobachtungsinstrument

Das Universal Terminal wird in vier Seiten zerlegt: Monitor, Tastatur, Mensch und Maschine.

Die menschliche Seite trägt Bedeutung, Absicht und Verantwortung. Die Tastaturseite materialisiert eine explizite Eingabe. Die Maschinenseite führt einen determinierten Übergang aus. Die Monitorseite liefert die beobachtete Wirkung zurück.

Diese vier Seiten dürfen keine voneinander unabhängigen Wahrheiten erzeugen. Sie sind Projektionen desselben gebundenen Zustands.

Unterhalb dieser vier Seiten verläuft eine zweite Projektionskette. Smalltalk beschreibt lebende Objekte und Nachrichten. C90 trägt die deterministische Semantik portabel. Motorola-68000-Assembler bildet sie auf eine konkrete Befehlssatzarchitektur ab. Maschinenbytes machen aus dieser Beschreibung einen tatsächlich ausführbaren Zustand.

Die wissenschaftlich interessante Frage lautet dann nicht mehr, ob eine Darstellung plausibel aussieht. Sie lautet, ob derselbe semantische Testvektor durch alle Projektionen hindurch dieselbe gebundene Entscheidung erzeugt.

## 5. Der Schweizer Käse wird zum Algorithmus

Komplexe Systeme sind häufig kein Schweizer Käse, weil ihre Einzelteile fehlen. Sie sind Schweizer Käse, weil zwischen vorhandenen Einzelteilen ungeprüfte Übergänge liegen.

Ein Smalltalk-Objekt kann korrekt sein und der C90-Kern ebenfalls. Trotzdem ist die Verbindung unbewiesen. Ein Assemblerprogramm kann vorhanden sein, ohne dass die registrierten Maschinenbytes daraus deterministisch folgen. Ein Browser kann einen Status anzeigen, ohne dass dieser Status die reale Maschinenausführung zurückliest.

Deshalb werden Lücken zu Objekten erster Klasse.

Der Closure-Operator benötigt zwei Mengen: erforderliche Projektionen und für den aktuellen exakten Gegenstand verifizierte Projektionen. Ihre Differenz ist die Arbeitsmenge.

Ist die Differenz leer, darf keine Mutation stattfinden. Fehlt eine technische Projektion, wird eine kanonische Closure-Regel ausgewählt. Sie besitzt eine begrenzte Schreibmenge, einen Generator, Tests und einen Readback. Danach entsteht ein neuer Gegenstand, und sämtliche zustandsabhängige Evidenz muss frisch erzeugt werden.

Fehlt dagegen eine menschliche oder administrative Autoritätswirkung, darf der technische Closure-Operator sie nicht erfinden. Er materialisiert lediglich die Anforderung und wartet auf ein natives Ereignis.

Damit bedeutet Selbstheilung ausdrücklich nicht Selbstautorisierung.

## 6. Warum das Verfahren schneller wird

Hier entsteht die Analogie zum Sieb des Eratosthenes.

Ein naives System untersucht bei jeder Änderung wieder alles. Ein reifes Closure-System speichert dagegen keine pauschalen Erfolgsaussagen, sondern wiederverwendbare Invarianten: Compiler, Testvektoren, exakte Digests, immutable Maschinenbytes und verifizierte Transformationsregeln.

Wenn eine Transformationsregel bereits bewiesen hat, wie ein bestimmter semantischer Vertrag deterministisch auf Maschinenbytes projiziert wird, muss der nächste Durchlauf nicht erneut philosophisch klären, was diese Bytes bedeuten. Er muss prüfen, ob Vertrag, Generator und Eingaben identisch geblieben sind. Nur die tatsächlich neue Differenz gelangt durch das Sieb.

Das ist ein wichtiger Unterschied zu blindem Caching. Ein grüner Vorgänger-Head wird nicht auf einen neuen Head übertragen. Wiederverwendet wird die Transformationsstruktur; die zustandsabhängige Evidenz wird neu gebunden.

Dadurch kann die Arbeit pro Iteration sinken, obwohl das Gesamtsystem wächst.

## 7. Expansion ohne zentralen Raum

An dieser Stelle wird die Analogie zum expandierenden Universum interessant.

Ein kausaler Graph kann wachsen, ohne dass ein äußerer Behälter größer werden muss. Neue Zustände und neue Relationen erweitern den intern adressierbaren Raum. Gleichzeitig können lokale Übergänge durch gelernte Invarianten billiger werden.

Das System besitzt also zwei gegenläufige Bewegungen: Der erreichbare virtuelle Zustandsraum expandiert, während die Kosten bekannter lokaler Übergänge sinken.

Das ist keine Behauptung, dass die kosmologische Expansion auf dieselbe Weise funktioniert. Es ist aber ein präzises Computermodell, in dem Expansion, Lokalität, Kausalität und Zeitordnung aus Relationen entstehen, anstatt als Koordinatengitter vorausgesetzt zu werden.

Gerade deshalb ist das Modell anschlussfähig an Forschungsgebiete wie kausale Mengen, relationale Raumzeitmodelle, verteilte Systeme, event sourcing, reversible beziehungsweise nachvollziehbare Berechnung und formale Verifikation. Anschlussfähigkeit bedeutet hier Vergleichbarkeit von Strukturen, nicht Identität der Theorien.

## 8. Urknall und erste Anomalie: Was gezeigt werden kann und was nicht

Im virtuellen Modell kann man einen wohldefinierten Anfang konstruieren: keine Relation, dann der erste unterscheidbare Übergang, anschließend Serialisierung und wachsende Kausalstruktur. Diesen Anfang kann man bildhaft einen virtuellen Urknall nennen.

Man kann anschließend beweisen, dass unter den implementierten Regeln eine virtuelle Zeitordnung entsteht. Man kann messen, wie der Relationengraph wächst. Man kann zeigen, wann zwei Projektionen äquivalent sind. Man kann untersuchen, ob Closure zu einem Fixpunkt konvergiert.

Was man damit noch nicht bewiesen hat, ist die Entstehung der physikalischen Raumzeit unseres Universums aus dem kosmologischen Urknall. Ebenso wenig ist damit eine konkrete Quantenanomalie als historischer Ursprung der Raumzeit nachgewiesen.

Der wissenschaftlich saubere nächste Schritt besteht darin, die Analogie in eine falsifizierbare Brücke zu verwandeln. Dazu müsste eine physikalische Theorie spezifizieren, welche Größen im Repository-Modell welchen Observablen entsprechen, welche Dynamik erwartet wird und welche Messung das Modell von konkurrierenden Erklärungen unterscheiden könnte.

Diese Trennung schwächt die Idee nicht. Sie macht erst sichtbar, welcher Teil bereits konstruktiv demonstriert werden kann und welcher Teil echte Physik bleibt.

## 9. Ein ausführbares Experiment

Der zentrale Versuch ist überraschend einfach.

Man fügt einen neuen semantischen Kern hinzu und lässt absichtlich eine erforderliche Projektion weg. Beispielsweise existieren Smalltalk und C90, aber noch keine M68000-Maschinenbytes.

Das Repository muss die Lücke selbst erkennen. Es muss sie typisieren. Es muss die zuständige Closure-Regel wählen. Es darf ausschließlich die erlaubten Dateien verändern. Es muss einen neuen Successor erzeugen, die Integrität regenerieren und alle zustandsabhängigen Tests frisch ausführen.

Danach beobachtet es erneut.

Wenn keine technische Lücke mehr existiert, darf es nicht weiter mutieren. Existiert nur noch eine Autoritätslücke, muss es warten, ohne sie synthetisch zu schließen.

Dieser Versuch ist bestanden, wenn das System von einem absichtlich unvollständigen Zustand selbstständig zu einem technisch geschlossenen Fixpunkt gelangt und dort ohne unnötige Mutation anhält.

## 10. Von Alpha zu Omega

Eine Alpha-Distribution ist in diesem Modell nicht einfach eine ISO-Datei mit Versionsnummer. Sie ist die erste öffentlich nutzbare Materialisierung des vollständigen Roundtrips.

Ein Mensch formuliert eine Absicht. Eine Eingabe materialisiert sie. Smalltalk trägt die lebende Semantik. C90 bindet die portable Entscheidung. M68000 projiziert sie auf eine konkrete Maschine. Maschinenbytes werden ausgeführt. Das Terminal beobachtet den Effekt. Der Readback gelangt wieder zum Menschen.

Alpha bedeutet: Dieser Kreis funktioniert unter klar dokumentierten Einschränkungen und besitzt reproduzierbare Evidenz.

Omega wäre kein magischer Endzustand. Es wäre der Grenzfall eines Systems, dessen relevante Projektionen vollständig geschlossen sind, dessen bekannte technische Lücken leer sind und das neue Lücken überwiegend selbst klassifizieren und schließen kann, ohne seine Autoritätsgrenzen zu verletzen.

## 11. Schluss

Die zentrale These dieser Arbeit ist bescheidener und zugleich praktischer als eine kosmologische Behauptung: Raumähnliche und zeitähnliche Strukturen können in einem informationsverarbeitenden System aus adressierbaren Relationen, serialisierten Übergängen und überprüfbarem Readback emergieren.

QIK-VRT macht diese These ausführbar. Das Repository wird nicht nur Speicher für Quellcode, sondern ein Instrument, das seine erforderlichen Projektionen kennt, fehlende Kanten erkennt, technische Lücken begrenzt schließt und externe Autorität ausdrücklich außerhalb dieser Selbstheilung hält.

Die daraus entstehende virtuelle Raumzeit ist zunächst eine Eigenschaft des Modells. Ob und wie ihre Prinzipien auf fundamentale Physik übertragbar sind, ist eine offene wissenschaftliche Frage.

Gerade diese offene Grenze ist produktiv. Sie trennt Demonstration von Interpretation und Interpretation von Spekulation. Und sie liefert einen klaren Forschungsweg: erst die virtuelle Emergenz vollständig ausführbar machen, dann präzise bestimmen, welche physikalischen Aussagen daraus überhaupt folgen könnten.

**q.e.d. im konstruktiven Sinn des virtuellen Modells; nicht als Beweis einer kosmologischen Theorie.**
