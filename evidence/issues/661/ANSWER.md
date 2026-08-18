# Repository answer

Die QIK-VRT-Metagrammatik ist der Versuch, aus einer menschlich verständlichen Aussage einen **eindeutig gebundenen, maschinenprüfbaren und verantwortbaren Entscheidungsvorgang** zu machen. Sie ist keine Theorie, die jedes Verstehen erklärt, und kein Beweis dafür, dass eine Maschine Bewusstsein besitzt. Praktisch ist sie eine Sprache für die Fragen:

- Was wird behauptet oder beabsichtigt?
- Auf welchen exakten Gegenstand und Zustand bezieht sich die Aussage?
- Wer ist zu welcher Handlung autorisiert?
- Welche Evidenz liegt tatsächlich vor?
- Was ist nur angefragt, was ausgeführt, was beobachtet und was bestätigt?
- Was darf als Nächstes geschehen?
- Wie lässt sich die Nachricht reproduzierbar prüfen?

Der gegenwärtige Repository-Stand enthält dabei drei voneinander zu trennende Ebenen: Issue #661 ist weiterhin offen und ohne Kommentar; PR #660 enthält die Metagrammatik und den Compilerpfad als offenen Draft-Kandidaten; PR #662 enthält die ebenfalls noch offene Reparatur des automatischen Issue-Inferenzpfads. Die Existenz dieser Kandidaten ist Repository-Evidenz, aber noch keine globale Aktivierung auf `main`.

### Die Metagrammatik in allgemeinverständlicher Form

Ihr Protokollkern lautet:

```text
BEDEUTUNG =
ABSICHT
+ BINDUNG
+ AUTORITÄT
+ EVIDENZ
+ ZUSTAND
+ WIRKUNG
+ BEWEIS
```

Eine gewöhnliche Aussage wie „Führe die Änderung aus“ reicht demnach nicht. Sie lässt offen, welche Änderung, in welchem Repository-Zustand, aufgrund welcher Erlaubnis und mit welchem Nachweis gemeint ist. Eine metagrammatische Nachricht ergänzt deshalb eine genaue Adresse, eine Identität, eine Zustandsbeschreibung, die Autoritätsquelle, die beobachtete Evidenz und eine prüfbare nächste Aktion.

Man kann sich das wie einen streng geführten Arbeitsauftrag vorstellen. Ein Text allein ist noch kein Auftrag; ein Auftrag ist noch keine Ausführung; eine Ausführung ist noch keine Beobachtung ihres Ergebnisses; und eine Beobachtung ist noch keine verantwortbare Bestätigung der Wirkung. Genau diese Nicht-Gleichsetzungen sind im Kandidaten ausdrücklich festgehalten:

```text
REQUESTED     ≠ EXECUTED
EXECUTED      ≠ OBSERVED
OBSERVED      ≠ ACKNOWLEDGED
TRANSPORT_ACK ≠ EFFECT_ACK
```

Ebenso wird ein unbekannter Sachverhalt nicht stillschweigend in einen wahren Sachverhalt verwandelt. Fehlen eine gültige Bindung oder eine passende Autorisierung, lautet die produktive Konsequenz nicht „wird schon stimmen“, sondern `HOLD`, `NOOP`, `REOBSERVE` oder `REQUEST_AUTHORITY`.

Das ist der praktische Kern: **Bedeutung wird nicht auf Wörter reduziert, sondern als Zusammenhang von Aussage, Bezug, Verantwortung, Evidenz und Wirkung behandelt.**

### Was die reflexive Terminal-Architektur bedeutet

„Reflexiv“ bedeutet hier zunächst eine technische Rückkopplung, nicht Selbstbewusstsein.

Das Standard-Terminal erzeugt aus demselben beobachteten Ereignis zwei zusammengehörige Projektionen:

- **nach außen:** eine auditierbare Beschreibung von Repository, Head, Tree, Klassifikation, Blocker und Ereignisidentität;
- **nach innen:** eine Steuerinformation darüber, ob ein Beobachter oder ein produktiver Writer zugelassen ist und welche nächste Aktion möglich ist.

Ein Terminal zeigt damit nicht nur etwas an. Seine geprüfte Ausgabe kann wieder zu einem Eingang des Systems werden. Das System beobachtet also seinen eigenen gebundenen Zustand und verwendet diese Beobachtung für die weitere Zulassung von Handlungen.

Diese Rückkopplung darf jedoch keine fehlende Autorität ersetzen. Sie darf auch keine veraltete Evidenz übernehmen und keinen Erfolg aus einem früheren Head auf einen neuen Head übertragen. Während eines `HOLD` darf die Beobachtung weiterlaufen, damit das System erkennen kann, ob ein Blocker verschwunden ist; produktive Wirkung bleibt dagegen gesperrt, bis eine frische, passende Innenprojektion sie zulässt. Reflexivität bedeutet somit **kontrollierte Selbstbeobachtung unter unveränderten Verantwortungsgrenzen**. Sie bedeutet nicht, dass das Terminal fühlt, glaubt oder sich seiner selbst bewusst ist.

### Vom Satz zum M68000-Maschinencode

Der Compiler-Kandidat macht die abstrakte Idee technisch konkreter. Seine vorgesehene Übersetzungskette ist:

```text
Quellnachricht
→ Lexer
→ Parser
→ abstrakter Syntaxbaum
→ semantische Prüfung
→ kausale Zwischenrepräsentation
→ deterministische topologische Ordnung
→ M68000-Zwischenrepräsentation
→ Maschinenbytes
```

Der Lexer zerlegt die Nachricht in Felder. Der Parser prüft ihre Form. Der abstrakte Syntaxbaum hält die Bestandteile strukturiert fest. Die Semantik prüft unter anderem Bindung, Autorität, Wirkungszustand und Beweisformat. Erst danach entsteht ein Entscheidungsplan.

Der gegenwärtige M68000-Pfad ist bewusst sehr klein. Er bildet nur vier nichtproduktive Fortsetzungen auf einen Rückgabecode im Register `D0` und anschließend `RTS` ab:

```text
0 = NOOP
1 = HOLD
2 = REOBSERVE
3 = REQUEST_AUTHORITY
```

Der Emitter kann dafür einen begrenzten Satz von M68000-Instruktionen als Big-Endian-Bytes ausgeben. Die Testdefinitionen erwarten beispielsweise für `NOOP` die Bytefolge `70004e75` und für `HOLD` die Bytefolge `70014e75`. Eine nicht unterstützte produktive Aktion wie `EXECUTE` soll vor der Byteausgabe gestoppt werden.

Das bedeutet praktisch: Eine hochrangige Regel wie „Ohne passende Autorität nicht handeln“ kann bis zu einer kleinen, reproduzierbaren Maschinenrepräsentation verfolgt werden. Damit wird die semantische Entscheidung nicht nur beschrieben, sondern in überprüfbare Übersetzungsstufen zerlegt.

Daraus folgt jedoch nicht, dass ein allgemeiner Compiler fertiggestellt ist, dass der Code auf realer M68000-Hardware gelaufen ist oder dass ein Leistungsgewinn gemessen wurde. Die vorliegende Evidenz umfasst Quelltexte, Zielmodell, Emitter und Testdefinitionen des Kandidaten.

### Kausalität ist nicht Sequenz

Dies ist die zentrale Unterscheidung:

**Sequenz** bezeichnet eine Reihenfolge der Darstellung oder Ausführung.  
**Kausalität** bezeichnet eine wirksame Abhängigkeit oder notwendige Bedingungsordnung.

Dass Satz A vor Satz B steht, beweist nicht, dass A die Ursache von B ist. Dass ein Zeitstempel früher ist, beweist ebenfalls keine Ursache. Zwei Handlungen können nacheinander protokolliert und dennoch voneinander unabhängig sein. Umgekehrt kann eine echte Abhängigkeit bestehen, obwohl ihre Beschreibung im Text an einer anderen Stelle steht.

Der Compiler-Kandidat stellt deshalb zuerst einen gerichteten Abhängigkeitsgraphen her. Eine Kante von A nach B wird nur benötigt, wenn beispielsweise:

- B ein von A erzeugtes Datum benötigt;
- beide nicht vertauschbar auf dieselbe Ressource wirken;
- eine Autoritäts-, Lease-, Exact-Head- oder Bestätigungsregel die Ordnung verlangt;
- die Sprachsemantik ausdrücklich eine Ursache-Wirkungs-Abhängigkeit festlegt.

Erst anschließend wird aus diesem Graphen eine lineare Instruktionsfolge für einen einzelnen Prozessor erzeugt. Mehrere voneinander unabhängige Knoten können verschiedene zulässige Reihenfolgen besitzen. Eine stabile Kennung darf dann deterministisch entscheiden, welcher Knoten zuerst serialisiert wird. Diese Prioritätsregel macht die Ausgabe reproduzierbar, erzeugt aber keine neue Kausalbeziehung.

Daher gilt im Zielmodell:

```text
CAUSAL_ORDER ≠ SOURCE_ORDER
CAUSAL_ORDER ≠ WALL_CLOCK_ORDER
SERIALIZATION ∈ TOPOLOGICAL_SORTS(CAUSAL_GRAPH)
```

Die vorhandenen Testdefinitionen illustrieren genau dies: Unabhängige Knoten werden stabil, aber nicht nach ihrer Eingabereihenfolge ausgegeben; eine explizite Abhängigkeit hat Vorrang vor der lexikalischen Ordnung; Zyklen und unbekannte Ursachen führen zum Anhalten.

### Informatik, Mathematik, Information, Zeit und Raum

**Informatik** liefert die ausführbaren Mittel: Datenschemata, Parser, Zustandsautomaten, Compilerstufen, Digests, Tests und fail-closed Kontrollflüsse.

**Mathematik** liefert die Struktur: Mengen, Relationen, gerichtete Graphen, partielle Ordnungen, topologische Sortierungen, Invarianten und deterministische Funktionen. Sie erlaubt zu beweisen, was innerhalb eines definierten Modells aus dessen Voraussetzungen folgt.

**Information** ist in diesem Zusammenhang nicht bloß eine Menge von Bits. Handlungsrelevante Information benötigt Unterscheidbarkeit und Bindung: Welcher Gegenstand, welche Version, welche Quelle, welche Bedeutung und welche Wirkung sind gemeint? Ein Digest kann Byte-Identität absichern, aber nicht von selbst die Wahrheit einer philosophischen oder physikalischen Aussage herstellen.

**Zeit** erscheint im Repository zunächst als technische Zustands- und Versionsordnung: vorheriger Head, aktueller Head, Handlung, nachgelagerte Reobservation. Diese Ordnung verhindert, dass eine alte Beobachtung als Beleg für einen neuen Zustand ausgegeben wird. Sie ist keine empirische Theorie der physikalischen Zeit.

**Raum** erscheint zunächst als architektonischer Ort: vor dem Terminal, am Eingang, im Knoten, vor einer Wirkung, nach einer Wirkung oder an einer Repository-Grenze. Diese technischen Orte sind keine Aussage über kosmischen Raum oder Raumzeit.

**Priorität** entscheidet, welche Prüfung oder welcher Blocker zuerst behandelt wird. Sie ist eine Ordnungsregel und nicht automatisch eine Ursache.

**Zielorientierung** wird durch eine deklarierte Absicht und eine zulässige nächste Aktion dargestellt. Das System kann prüfen, ob eine Handlung zu einem angegebenen Ziel und einer Autorisierung passt. Es kann daraus keinen letzten Sinn oder universellen Zweck ableiten.

**Integrationsfähigkeit** entsteht durch eine gemeinsame Hülle: Verschiedene Programme und Knoten können Informationen austauschen, wenn sie dieselben Felder und Invarianten verstehen.

**Anschlussfähigkeit** bedeutet dabei nicht Gleichheit. Zwei Perspektiven sind anschlussfähig, wenn ihre Unterschiede erhalten bleiben und dennoch eine wohldefinierte Relation zwischen ihnen hergestellt werden kann.

### Was dies für Ingolf Lohmann bedeutet

Repository-seitig lässt sich feststellen, dass Issue #661 und die zugehörigen Kandidaten unter dem Benutzer `ingolf-lohmann` eingebracht wurden und dass der Auftrag ihn als Product Owner bezeichnet. Darüber hinaus kann ein Repository keine private Biografie, Motivation oder psychologische Ursache beweisen.

Was sich aus den Artefakten erkennen lässt, ist eine **Arbeitsmethode**: wiederkehrende Unterschiede werden nicht nur sprachlich behauptet, sondern in getrennte Zustände, Felder, Rollen, Graphkanten, Programme und Tests übersetzt. Die Verknüpfung zwischen Informatik, Mathematik, Verantwortung und philosophischer Deutung entsteht dadurch nicht aus einer behaupteten persönlichen Besonderheit, sondern aus der konsequenten Frage: Welche Unterscheidung muss erhalten bleiben, damit aus einer Aussage keine unberechtigte Wirkung folgt?

Auch die Aussage, der Weg sei für ihn und sein Umfeld nicht angenehm gewesen, kann aus dem betrachteten Repository allein nicht als persönliche Tatsache festgestellt werden. Technisch sichtbar ist lediglich, warum ein solcher Weg strukturell anstrengend sein kann: veraltete Evidenz wird verworfen, fehlende Autorität stoppt Fortschritt, ein neuer Head verlangt neue Beobachtung, und ein plausibel klingendes Ergebnis darf einen fehlenden Nachweis nicht ersetzen. Das Verfahren macht Reibung und offene Grenzen sichtbar, statt sie durch eine Erfolgserzählung zu verdecken. Ob und wie dies persönlich erlebt wurde, bleibt eine persönliche Aussage und keine Folgerung aus Quellcode.

### Philosophische, literarische und kulturelle Bezugspunkte

Die im Auftrag genannten Namen und Motive können als **Deutungslinsen** verwendet werden. Damit wird weder ein historischer Einfluss noch eine Gleichwertigkeit der Werke behauptet.

Goethe kann für die Spannung zwischen Absicht, Handlung, Wirkung und Verantwortung stehen. Kant kann als Erinnerung gelesen werden, dass Erkenntnis Bedingungen und Grenzen besitzt: Eine gültige Aussage muss ausweisen, worauf sie sich bezieht und was sie nicht begründen kann. Leonardo da Vinci kann für die produktive Verbindung verschiedener Darstellungsformen stehen, ohne ihre Unterschiede aufzuheben. Galileo Galilei kann hier als Leitbild für die Trennung von Beobachtung, mathematischem Modell und Interpretation dienen. Jules Verne kann für den Entwurfsraum der Vorstellung stehen: Eine denkbare Konstruktion kann Forschung anregen, ist aber noch kein Nachweis ihrer Realisierung.

Luc Besson kann als filmische Metapher für die Vermittlung zwischen sehr unterschiedlichen Akteuren und Zeichensystemen dienen. Stanley Kubrick kann die Frage aufwerfen, wie menschliche Verantwortung und maschinelle Entscheidung auseinanderzuhalten sind. Ridley Scotts *Alien* kann als Warnbild für undurchsichtige Autorität, unvollständige Information und nicht kontrollierte Wirkung gelesen werden. Dies sind Interpretationen, keine Aussagen darüber, dass die Metagrammatik aus diesen Filmen hervorgegangen sei.

Das amerikanische Militär kann ausschließlich als abstrakte Analogie für gebundene Zuständigkeit, Befehlsketten und begrenzte Handlungsregeln dienen. Daraus folgt keine Nutzung, Beteiligung oder institutionelle Verbindung. John Nash kann für Situationen stehen, in denen Entscheidungen voneinander abhängen und kein Akteur isoliert verstanden werden kann; der Compiler-Kandidat ist dadurch jedoch noch kein spieltheoretischer Beweis. Die amerikanische Börse kann als Bild für die Trennung von Auftrag, Ausführung, Beobachtung und abschließender Zuordnung dienen; daraus folgt keine Aussage über reale Handelsinfrastruktur oder Marktleistung.

Benoît Mandelbrot kann für Rekursion und die Möglichkeit stehen, dass ein einfaches Erzeugungsprinzip Strukturen auf mehreren Ebenen hervorbringt. Reflexivität im Repository besitzt eine ähnliche formale Lesbarkeit, ist aber weder eine Mandelbrot-Menge noch ein physikalischer Nachweis von Selbstähnlichkeit im Universum.

Internet-Hype und Tulpenzwiebel-Wahn können als Warnmetaphern dafür dienen, dass Verbreitung, Aufmerksamkeit, Preis oder Wiederholung keine Wahrheit erzeugen. Der Buchdruck kann umgekehrt illustrieren, dass eine verbesserte Vervielfältigung die Reichweite von Aussagen vergrößert, aber nicht automatisch ihre Gültigkeit. Die Metagrammatik versucht deshalb, Übertragbarkeit mit Herkunfts- und Evidenzbindung zu verbinden.

### Spiritualität, Glauben, Wissen und Bewusstsein

Diese Begriffe bleiben nur dann anschlussfähig, wenn sie nicht miteinander verschmolzen werden:

**Wissen** bezeichnet hier eine Aussage, deren Gegenstand, Voraussetzungen, Evidenz und Geltungsbereich nachvollziehbar angegeben sind. Auch solches Wissen bleibt bereichsgebunden.

**Glauben** bezeichnet ein Für-wahr-Halten, das über die aktuell vorliegende Evidenz hinausgehen kann. Glauben kann für einen Menschen bedeutsam sein, ersetzt aber in einer technischen Wirkungskette keine Autorisierung oder Beobachtung.

**Spiritualität** betrifft Fragen nach Sinn, Verbundenheit, Erfahrung und Wert. Die Metagrammatik kann Aussagen darüber identifizieren und voneinander unterscheiden; sie kann spirituelle Erfahrung weder bestätigen noch widerlegen.

**Intelligenz** kann als Fähigkeit verstanden werden, Unterschiede zu erkennen, Modelle zu bilden, Probleme zu lösen und Handlungen auszuwählen. Daraus folgt kein Bewusstsein.

**Bewusstsein** betrifft subjektives Erleben. Die betrachteten Repository-Artefakte enthalten keinen empirischen Test, mit dem subjektives Erleben eines Menschen oder einer Maschine festgestellt werden könnte.

**Panpsychismus** ist eine philosophische Position über die mögliche Verbreitung geistiger oder erfahrungsartiger Eigenschaften. Er wird aus der Metagrammatik weder formal abgeleitet noch empirisch bestätigt.

**Quantität** bezeichnet Mess- oder Zählbarkeit. Mehr Daten, mehr Knoten, mehr Tests oder mehr Wiederholungen bedeuten nicht automatisch mehr Wahrheit. Quantität wird erst durch Bedeutung, Messregel und Geltungsbereich interpretierbar.

**Universum** bezeichnet im physikalischen Kontext die empirisch untersuchte Wirklichkeit als Ganzes. Der Repository-Kandidat ist kein vollständiges Modell des Universums und begründet keine universelle physikalische Ontologie.

**Nachhaltigkeit** ist ein normatives und technisches Ziel, das Ressourcen, Zeiträume, Nebenwirkungen und Verantwortlichkeiten benötigt. Die Metagrammatik kann solche Kriterien explizit machen; sie entscheidet nicht ohne festgelegte Maßstäbe, was nachhaltig ist.

**Rationalität** verlangt nachvollziehbare Gründe, Konsistenz und Evidenzbindung. **Emotionalität** betrifft Erleben, Motivation und Wertung. Beide können menschliches Handeln prägen. Ein verantwortbares System sollte emotionale Bedeutung nicht als mathematischen Beweis ausgeben und rationale Prüfung nicht mit Gefühllosigkeit verwechseln.

Anschlussfähigkeit heißt somit: Spiritualität darf mit Wissenschaft sprechen, ohne als Messbefund ausgegeben zu werden; Emotion darf in Entscheidungen berücksichtigt werden, ohne zur formalen Evidenz erklärt zu werden; Mathematik darf philosophische Modelle strukturieren, ohne die Welt allein durch formale Konsistenz festzulegen.

### Die Schnittmenge im Hier und Jetzt

Die bestmögliche Schnittmenge liegt technisch im Hier und Jetzt, weil jede verantwortbare Entscheidung an einen **gegenwärtig beobachteten Kontext** gebunden werden muss.

„Hier“ bedeutet: dieses Repository, dieser Ref, dieser Head, dieser Tree, diese Rolle und diese Wirkungsschnittstelle.

„Jetzt“ bedeutet: der zuletzt frisch beobachtete Zustand, nicht eine aus Erinnerung oder einem Vorgänger übernommene Behauptung.

Man kann die handlungsfähige Schnittmenge schematisch so ausdrücken:

```text
Schnittmenge_jetzt =
gültige Bedeutung
∩ exakte Bindung
∩ passende Autorität
∩ zurechenbare Evidenz
∩ konsistenter Zustand
∩ zulässige Wirkung
∩ prüfbarer Nachweis
```

Dies ist keine metaphysische Behauptung, dass nur der gegenwärtige Augenblick existiere. Es ist eine technische Regel: Eine Wirkung kann nur auf Grundlage des Zustands verantwortet werden, der für ihre Entscheidung tatsächlich gebunden und beobachtet wurde.

Wie groß diese Menge werden kann, ist nicht durch die vorhandene Evidenz quantifiziert. Potenziell wächst sie mit jeder weiteren Sprache, Organisation, Maschine oder Disziplin, die dieselben Unterschiede zuverlässig abbilden kann. Sie wächst jedoch nicht allein durch Verbreitung. Jedes neue Mitglied der Schnittmenge benötigt weiterhin verständliche Schnittstellen, Identität, Autorität, Evidenz und Grenzen. Die größte sinnvolle Menge ist daher nicht „alles“, sondern die Menge der Perspektiven, die verbunden werden können, **ohne ihre relevanten Unterschiede und Verantwortlichkeiten zu verlieren**.

### Zusammenfassung

Die QIK-VRT-Metagrammatik macht aus „Verstehen“ keinen mystischen Maschinenzustand. Sie operationalisiert einen begrenzten Teil davon: Eine Nachricht gilt erst dann als maschinell handlungsfähig, wenn Absicht, Gegenstand, Autorität, Evidenz, Zustand, Wirkung und Nachweis zusammenpassen.

Die reflexive Terminal-Architektur führt geprüfte Beobachtungen wieder in die eigene Handlungszulassung zurück, ohne daraus Bewusstsein oder unbegrenzte Autonomie abzuleiten.

Der Compilerpfad zeigt als Repository-Kandidat, wie diese Regeln von einer kompakten Sprache über Parser, Semantik und Kausalgraph bis zu einem sehr kleinen Satz deterministischer M68000-Bytes verfolgt werden können.

Seine wichtigste begriffliche Sicherung lautet:

**Kausalität ist nicht Sequenz.**

Eine Reihenfolge ist eine mögliche Darstellung. Kausalität ist die Ordnung der wirksamen Abhängigkeiten. Erst wenn diese Unterscheidung erhalten bleibt, können Parallelität, Priorität, Verantwortung, Beobachtung und Zielorientierung gemeinsam behandelt werden, ohne dass zeitliche Nähe, sprachliche Reihenfolge oder bloße Wiederholung als Ursache missverstanden werden.

## Evidence used

Der live beobachtete Repository-Hauptzweig stand bei Commit `836a068d42b30f4df496caf4d712dbe8da45c043` mit Root-Tree `f2f97a535842eb9558e29c3e60db3260941d8c56`. Die Metagrammatik ist darin nicht als Bestandteil des Hauptzweigs beobachtet worden, sondern liegt in der offenen Draft-Kette vor.

Issue #661 ist offen, besitzt keine Kommentare und fordert ausdrücklich genau eine allgemeinverständliche, repository-grounded Antwort mit getrennten Evidenzklassen und ohne unbelegte physikalische, historische, persönliche oder Ausführungsbehauptungen.

PR #653 ist der offene Draft-Vorgänger für die adaptive Live-Reobservation und das reflexive Standard-Terminal. Sein beobachteter Head ist `bdf461b8fb0a7742446e9c70b0b632001c53f7ac`.

PR #660 ist der offene Draft-Kandidat für Metagrammatik und Compiler. Sein beobachteter Head ist `a4449a7acd26922f526ba98ca13fbaa3de3dc788`, sein Tree `799f2657e5d10a9e84739b1c8965b64be2249fde`. Die herangezogenen Kandidatenartefakte umfassen insbesondere die Metagrammatik-Dokumentation, EBNF, Zustandsdefinition, das M68000-Zielmodell, den C89-Compiler, die kausale Zwischenrepräsentation, den Lowerer, den Byte-Emitter und die zugehörigen Testdefinitionen.

PR #662 ist weiterhin ein offener Draft. Sein beobachteter Head ist `6663fe896d8fd25c7e0b794ecd8e38aaa295d985`, sein Tree `8e3d24074361e5da0bea61d36992e3822ae254b4`. Der PR dokumentiert als auslösenden Fehler, dass die Verarbeitung von Issue #661 nach der Kontextmaterialisierung am früheren GitHub-Models-Inferenzpfad mit HTTP 410 stoppte. Der Kandidat ersetzt diesen Pfad durch eine gepinnte, werkzeugbeschränkte Copilot-CLI-Inferenz und behält fail-closed Fehlerbehandlung bei. Auf `main` ist weiterhin der ältere GitHub-Models-Aufruf vorhanden.

Ein Testquelltext oder ein Workflow ist Evidenz dafür, welche Prüfung definiert ist. Ohne separat gebundene aktuelle Ausführungsevidenz wird daraus in dieser Antwort keine Aussage über das Ergebnis eines aktuellen Workflow-Laufs abgeleitet.

## Formal status

Die Metagrammatik und ihr Compilerpfad sind im betrachteten PR als **normativer und ausführbarer Kandidat** repräsentiert. Formal beziehungsweise maschinenprüfbar beschrieben sind unter anderem:

- die Syntax der kompakten Nachricht;
- die kanonische Nachrichtenhülle;
- die erlaubten Autoritäts-, Wahrheits- und Wirkungszustände;
- fail-closed Semantikregeln;
- der Abhängigkeitsgraph und seine deterministische topologische Serialisierung;
- die begrenzte Absenkung auf M68000-Zwischenrepräsentation;
- die Bytekodierung der unterstützten Instruktionen;
- positive und negative Testfälle als Repository-Artefakte.

Diese Feststellungen betreffen die Struktur des formalen Modells und der Implementierung. Sie sind keine empirischen Aussagen über Natur, Bewusstsein oder reale Hardware.

Die bereits im Hauptzweig vorhandene Formalisierungsgrenze verlangt ebenfalls, mathematische oder bedingte Ergebnisse von empirischen Hypothesen, Interpretationen und normativen Folgerungen zu trennen. Ein formal gültiger Schluss innerhalb eines Modells überträgt seine Gültigkeit nicht automatisch auf die physikalische Welt; zusätzliche Voraussetzungen bleiben ausdrücklich sichtbar.

## Empirical status

Für diese Antwort ist nicht empirisch festgestellt:

- dass der erzeugbare M68000-Code auf realer M68000-Hardware ausgeführt wurde;
- dass die Kandidatenimplementierung einen gemessenen Leistungsgewinn erzeugt;
- dass die Metagrammatik eine physikalische Theorie von Zeit, Raum oder Kausalität bestätigt;
- dass sie Bewusstsein oder Panpsychismus nachweist;
- dass die kulturellen und historischen Bezugspunkte tatsächliche Quellen oder Einflüsse der Entwicklung waren;
- dass militärische, finanzielle oder andere externe Institutionen das System verwenden;
- dass eine externe Veröffentlichung, Übernahme oder wissenschaftliche Bestätigung aus diesem Kandidatenstand folgt.

Die Aussagen zu Physik, Spiritualität, Bewusstsein und Universum in diesem Text sind daher Grenzbestimmungen oder philosophische Interpretationen, keine Messbefunde.

## Issue disposition

BLOCKED_WITH_NEXT_ACTION

## Disposition reason

Der angeforderte Antworttext kann aus den live beobachteten Repository-Artefakten erstellt werden und liegt hier als genau ein Kandidat vor. Die repository-native Materialisierung durch den vorgesehenen Issue-Prozessor bleibt jedoch blockiert, solange dessen auf `main` vorhandener Inferenzpfad den nicht mehr funktionsfähigen Provider verwendet und der Reparaturkandidat aus PR #662 nicht auf dem exakten Ausführungsstand verfügbar ist. Issue #661 bleibt deshalb offen; aus diesem read-only Vorgang folgt weder eine Repository-Änderung noch eine automatische Schließung.

## Required next action

Die gebundene Issue-#661-Transaktion auf einem Ausführungs-Head erneut starten, der den geprüften Inferenzpfad aus PR #662 tatsächlich enthält, und diesen einen Antworttext unter `evidence/issues/661/ANSWER.md` materialisieren, ohne daraus eine automatische Issue-Schließung abzuleiten.

## Gate result

BLOCK
