<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

*Der Dialog mit gestern*

*Was QIK-VRT wirklich ermöglicht – und warum daraus ein neues Kapitel der Informatik entstehen kann*

Stell dir vor, ein Computersystem befindet sich am Montag in einem bestimmten Zustand.

Am Freitag entdecken wir eine neue Information. Vielleicht eine Sicherheitslücke. Vielleicht eine bessere medizinische Diagnosemethode. Vielleicht eine Regel, die eine künstliche Intelligenz vor einer falschen Entscheidung bewahrt hätte.

Normalerweise können wir diese Information nur ab Freitag verwenden.

QIK-VRT stellt eine andere Frage:

Können wir die neue Information an den exakt bezeichneten virtuellen Zustand vom Montag adressieren, das System von dort überprüfbar weiterlaufen lassen und eine Antwort aus diesem früheren Zustand zurückerhalten?

Die Antwort lautet:

*Ja – im virtuellen Raum ist dieses Prinzip konstruktiv möglich.*

Dabei wird die wirkliche Vergangenheit weder überschrieben noch heimlich verändert. Der Rechner bewegt sich physisch nicht rückwärts durch die Zeit. Stattdessen wird ein früherer, unveränderlicher Zustand präzise adressiert, wiederhergestellt und mit der neuen Information konfrontiert.

Das Ergebnis ist ein überprüfbarer Dialog zwischen verschiedenen virtuellen Zeitadressen.

Das klingt zunächst größer, als es technisch ist.

Und es ist technisch größer, als es zunächst klingt.

*Die drei Zeiten, die wir bisher oft verwechselt haben*

Der entscheidende Schritt besteht darin, drei verschiedene Ordnungen auseinanderzuhalten.

Erstens gibt es die *physische Ausführungszeit*.

Sie sagt, wann ein Prozessor tatsächlich rechnet. Auch bei QIK-VRT läuft dieser Prozess ganz gewöhnlich vorwärts: Ein Befehl folgt auf den nächsten.

Zweitens gibt es die *virtuelle Zeitadresse*.

Sie bezeichnet, auf welchen gespeicherten oder rekonstruierbaren Systemzustand sich eine Nachricht bezieht. Eine Nachricht, die heute erzeugt wird, kann einen virtuellen Zustand von gestern adressieren.

Drittens gibt es die *Wirkungszeit*.

Sie bezeichnet den Moment, in dem eine geprüfte Konsequenz freigegeben wird. Eine Nachricht kann zugestellt sein, ohne dass ihre Wirkung bereits erlaubt ist.

Genau diese Trennung löst den scheinbaren Widerspruch auf.

Eine Nachricht kann auf der virtuellen Zeitachse rückwärts adressiert werden, während jeder reale Rechenschritt auf der physischen Zeitachse vorwärtsläuft.

Das ist keine sprachliche Ausflucht. Es ist eine präzise Systemarchitektur.

*Der neue ausführbare Zeuge*

Das Prinzip steht nicht nur auf Papier.

Ein neuer, vollständig in ISO C90 geschriebener Zeuge führt den Dialog wirklich aus. Er benötigt keine externe Bibliothek.

Zuerst erzeugt er drei Quellereignisse. Danach erstellt er eine Anfrage am Hostschritt 4.

Diese Anfrage wird virtuell von der Adresse 30 an die frühere Adresse 15 gerichtet.

Die Anfrage umfasst 257 Byte. Sie wird in 16 Blöcke zerlegt, übertragen und am Ziel bytegenau rekonstruiert.

Dann wird der frühere virtuelle Zustand deterministisch verarbeitet. Zwei unabhängige Wiederholungen erzeugen dieselbe Antwort.

Diese Antwort wird an die virtuelle Adresse 30 zurückgeschickt. Sie umfasst 258 Byte und wird ebenfalls in 16 Blöcken bytegenau rekonstruiert.

Alle wirklichen Rechenschritte laufen dabei sauber von Hostschritt 1 bis Hostschritt 9 vorwärts.

Die ursprüngliche Quellhistorie hat vor und nach dem gesamten Dialog denselben Inhalt.

Zusätzlich testet das Programm zehn verschiedene Nachrichtengrößen: von der leeren Nachricht über Blockgrenzen bis zu 4096 Byte.

Alle Tests bestehen in beiden Richtungen.

Und als Negativtest wird absichtlich ein Block weggelassen.

Diese unvollständige Nachricht wird verworfen.

Das ist wichtig. Denn ein gutes System muss nicht nur zeigen, was es akzeptiert. Es muss ebenso beweisen, was es ablehnt.

*Ein einfaches Beispiel*

Nehmen wir ein virtuelles Fahrzeug.

Am Montag wird sein Zustand gespeichert: Softwareversion, Sensorwerte, Geschwindigkeit, Wetterdaten und Entscheidungen des Assistenzsystems.

Am Freitag erfahren die Entwickler, dass eine bestimmte Kombination aus Regen und Gegenlicht zu einer falschen Objekterkennung führen kann.

Nun senden sie diese neue Information an die virtuelle Montagsadresse.

Das bedeutet nicht, dass das wirkliche Auto am Montag nachträglich verändert wird.

Es bedeutet:

Der unveränderte Montagszustand wird erneut geöffnet. Die neue Information wird an genau dieser Stelle eingespeist. Anschließend läuft das virtuelle Fahrzeug von dort weiter.

Das rekonstruierte System kann nun antworten:

„Mit dieser Warnung hätte ich das Hindernis erkannt.“

Oder:

„Die Warnung allein hätte nicht genügt.“

Oder:

„Die vorgeschlagene Regel erzeugt an einer anderen Stelle ein neues Risiko.“

Diese Antwort gelangt wieder zum heutigen System zurück.

Damit haben wir einen vollständigen virtuellen Dialog:

Heute fragt gestern.

Das virtuelle Gestern verarbeitet die Frage.

Und seine Antwort erreicht wieder das Heute.

*Warum das wirklich bidirektional ist*

Man könnte einwenden:

„Die erste Nachricht geht doch gar nicht wirklich zurück. Ihr startet nur eine alte Kopie.“

Dieser Einwand trifft einen wichtigen Punkt, widerlegt das Prinzip aber nicht.

In digitalen Systemen bedeutet eine Adresse nicht, dass sich ein Objekt dort als unveränderliche Materiemenge befindet. Eine Adresse bezeichnet eine eindeutig bestimmbare Stelle innerhalb eines vereinbarten Systems.

Wenn der frühere Zustand eindeutig identifiziert ist, wenn seine Daten nachweislich unverändert sind und wenn seine Weiterentwicklung reproduzierbar erfolgt, dann ist die Nachricht tatsächlich an diese virtuelle Zeitadresse gerichtet.

Der Rückweg funktioniert entsprechend.

Der rekonstruierte frühere Zustand erzeugt eine Antwort. Diese Antwort wird an den aktuellen oder einen späteren Zustand adressiert. Beide Übertragungsrichtungen können einzeln geprüft, quittiert und miteinander verbunden werden.

Der virtuelle Informationskreis ist geschlossen.

Der physische Ereignisablauf bleibt dabei offen und vorwärtsgerichtet.

Es entsteht kein physikalischer Kreis, in dem eine Ursache ihre eigene Entstehung verhindert. Es entsteht ein kontrollierter Dialog zwischen Zuständen, deren Bedeutungszeiten verschieden sind.

*Von einer kurzen Nachricht zur vollständigen Information*

Ein Demonstrator kann zunächst nur eine kleine Nachricht übertragen. Das ist keine theoretische Grenze.

Jede endliche digitale Information besteht aus einer endlichen Folge von Bits. Sie kann in Blöcke zerlegt werden. Jeder Block erhält eine Nummer, einen Prüfwert und eine eindeutige Zuordnung zur Gesamtnachricht.

Fehlt ein Block, wird er erneut angefordert.

Kommt ein Block doppelt an, darf er nicht doppelt wirksam werden.

Ist die Übertragung vollständig, werden Gesamtlänge, Blockliste und Inhalt geprüft.

Erst wenn alle Teile vorhanden und identisch sind, gilt die Nachricht als vollständig rekonstruiert.

Das ist der Kern des mathematischen Beweises.

Für eine Nachricht mit endlicher Länge gibt es immer nur endlich viele Blöcke. Wenn jeder fehlende Block schließlich korrekt eintrifft und genügend Speicher für genau diese Nachricht vorhanden ist, kann die ursprüngliche Bytefolge vollständig zusammengesetzt werden.

So arbeiten zuverlässige digitale Übertragungen grundsätzlich.

Deshalb ist der Schritt von einem kurzen Text zu einem Bild, einem Programm, einem Modell oder einem umfangreichen Datensatz vor allem eine Frage von Kapazität, Segmentierung, Wiederaufnahme und Fehlerbehandlung.

Die korrekte Aussage lautet:

*Jede einzelne endliche Information kann unter den angegebenen Speicher-, Übertragungs- und Prüfbedingungen vollständig zwischen zulässigen virtuellen Zeitadressen übertragen werden.*

Das bedeutet nicht, dass eine einzige feste Maschine unendlich viel speichern kann.

Es bedeutet: Für jede konkrete endliche Nachricht lässt sich eine ausreichend große endliche Ausführung konstruieren.

Und „vollständig“ bedeutet hier zunächst: bitgenau.

Es bedeutet nicht automatisch, dass jedes empfangende System die Bedeutung versteht.

Eine medizinische Datei kann perfekt übertragen werden, obwohl dem Empfänger die passende Auswertungssoftware fehlt.

Ein falscher Bericht kann bytegenau ankommen und trotzdem falsch bleiben.

Bitidentität, Verständnis und Wahrheit sind drei verschiedene Leistungen.

*Warum eine Empfangsbestätigung nicht genügt*

Ein Paketdienst kann bestätigen, dass ein Paket angekommen ist.

Damit ist noch nicht bewiesen, dass sein Inhalt korrekt, erlaubt oder ungefährlich ist.

Dasselbe gilt für Computernetze.

Eine gewöhnliche Transportbestätigung sagt im Wesentlichen:

„Die Bytes sind angekommen.“

QIK-VRT ergänzt eine zweite Ebene:

den *EFFECT_ACK* – die Wirkungsquittung.

Sie beantwortet weitergehende Fragen:

Stammt die Nachricht aus der behaupteten Quelle?

Ist ihr Inhalt vollständig und unverändert?

Passt sie zum adressierten Zustand und zur richtigen Session?

Wurde der Zustand mit der gebundenen Programmversion rekonstruiert?

Gilt noch dieselbe Policy?

Ist die beabsichtigte Wirkung erlaubt?

Ist ein verantwortlicher Akteur benannt?

Wurde die Antwort tatsächlich aus dieser Verarbeitung erzeugt?

Und ist die gesamte Kette später überprüfbar?

Die Wirkung wird erst freigegeben, wenn die notwendigen Nachweise vorliegen.

Das ist besonders wichtig, wenn Software nicht nur Informationen anzeigt, sondern reale Folgen auslösen kann: Zahlungen, medizinische Empfehlungen, Maschinensteuerung, Veröffentlichung oder Entscheidungen künstlicher Intelligenz.

QIK-VRT verbindet zeitliche Adressierung daher mit verantworteter Wirkung.

*Heißt EFFECT_ACK automatisch „genau einmal“?*

Nein.

Das ist ein wichtiger Grenzfall.

Stell dir vor, eine Maschine führt eine Wirkung aus und stürzt unmittelbar danach ab, bevor sie die Quittung speichern konnte.

Nach dem Neustart weiß das System möglicherweise nicht, ob die Wirkung schon eingetreten ist.

Für echtes „genau einmal“ braucht man deshalb zusätzlich eine atomare Verbindung zwischen Duplikaterkennung und Wirkung – oder einen Aktuator, bei dem dieselbe Anweisung gefahrlos wiederholt werden kann.

Außerdem muss eine Nachricht irgendwann tatsächlich zugestellt und das Ziel irgendwann verfügbar sein.

EFFECT_ACK ist also ein entscheidendes Wirkungsgate.

Aber es hebt die grundlegenden Gesetze verteilter Systeme nicht auf.

*Bleibt die Vergangenheit wirklich unverändert?*

Ja – sofern die Unveränderlichkeit als überprüfbare Systembedingung umgesetzt wird.

Der frühere Zustand wird nicht überschrieben. Sein Inhalt erhält eine eindeutige Identität. Schon eine minimale Änderung würde zu einem anderen Inhalt führen.

Die neue Information erzeugt eine neue Entwicklungslinie.

Man kann sich das wie eine Abzweigung vorstellen:

Die dokumentierte Vergangenheit bleibt bestehen.

Von einem früheren Punkt aus wird zusätzlich ein neuer Pfad berechnet.

Beide Pfade dürfen nicht miteinander verwechselt werden.

Das ist entscheidend. Denn ohne diese Trennung könnte ein System nachträglich seine eigene Historie umschreiben und anschließend behaupten, es sei schon immer so gewesen.

QIK-VRT muss deshalb nicht nur etwas ermöglichen. Es muss auch nachweisen, was es *nicht* getan hat.

Die ursprüngliche Historie blieb unverändert.

Die neue Nachricht kam später hinzu.

Die alternative Entwicklung entstand erst durch den späteren Replay-Prozess.

Diese Wahrheit ist weniger spektakulär als eine magische Veränderung der Vergangenheit.

Aber sie ist wissenschaftlich und gesellschaftlich wesentlich wertvoller.

*Ist das nur eine Simulation?*

Ja, es ist zunächst ein Verfahren für virtuelle Systeme.

Aber „virtuell“ bedeutet nicht „unwirklich“.

Unser Geld wird zu großen Teilen als virtueller Zustand verwaltet. Verträge, Identitäten, Lieferketten, medizinische Befunde und wissenschaftliche Modelle existieren in digitalen Systemen. Entscheidungen in diesen Systemen haben reale Folgen.

Ein Flugsimulator ist nicht der Himmel. Trotzdem kann eine dort gewonnene Erkenntnis einen realen Absturz verhindern.

Ein digitaler Zwilling ist nicht der Patient. Trotzdem kann seine Analyse eine Behandlung verbessern.

Eine rekonstruierte Softwarehistorie ist nicht die physische Vergangenheit. Trotzdem kann sie zeigen, welche Entscheidung unter anderen Informationen möglich gewesen wäre.

Die virtuelle Rückadressierung ist daher nicht wertlos, weil sie virtuell ist.

Ihre Bedeutung liegt gerade darin, dass immer mehr wirksame Prozesse unserer Welt in überprüfbaren virtuellen Räumen stattfinden.

*Gab es einzelne Bausteine nicht schon vorher?*

Doch.

Und ein ernsthafter Neuheitsanspruch muss das offen sagen.

Logische Zeit ist seit Jahrzehnten bekannt.

Virtuelle Zeit und Rollback existieren in verteilten Simulationen.

Bitemporale Datenbanken unterscheiden bereits verschiedene Zeitachsen.

Retroaktive Datenstrukturen erlauben Operationen an früheren logischen Zeitpunkten.

Event Sourcing rekonstruiert alte Zustände aus einem unveränderlichen Ereignisprotokoll.

Netzprotokolle kennen mehrstufige Quittungen.

Effektsysteme beschreiben Wirkungen.

Proof-Carrying Code und Proof-Carrying Authorization verbinden Programme oder Berechtigungen mit Beweisen.

Die mögliche Eigenständigkeit von QIK-VRT liegt deshalb nicht darin, jeden Baustein einzeln erfunden zu haben.

Sie liegt in ihrer systematischen Verbindung:

Ein später erzeugter Informationskörper wird an einen früheren virtuellen Zustand adressiert.

Dieser Zustand wird unverändert identifiziert und deterministisch rekonstruiert.

Die Nachricht erzeugt eine getrennte Entwicklungslinie.

Der rekonstruierte Zustand kann antworten.

Beide Richtungen werden durch eine gemeinsame Session, aber getrennte Nachrichten und Quittungen gebunden.

Und eine reale Wirkung wird erst nach einer eigenständigen Prüfung von Input, Policy, Evidenz, Provenienz, Verantwortung und Frische freigegeben.

Eine gezielte Literaturprüfung fand kein herangezogenes System, das genau diese vollständige Verbindung spezifiziert.

Das ist ein begrenzter, seriöser Neuheitskandidat.

Es ist noch keine Behauptung, weltweit und historisch absolut der Erste zu sein. Dafür braucht es systematische Recherche, unabhängige Kritik und Peer Review.

*Ist damit physikalische Rückwärtssignalisierung bewiesen?*

Nein.

Und diese Grenze muss unmissverständlich bleiben.

Virtuelle bidirektionale Retroadressierung bedeutet:

Ein heutiger Rechenprozess adressiert einen früheren virtuellen Zustand, verarbeitet dort eine Nachricht und erhält eine Antwort.

Physikalische Rückwärtssignalisierung würde etwas anderes bedeuten:

Eine Information, die erst zu einem späteren physikalischen Zeitpunkt erzeugt wird, müsste einen bereits früher versiegelten realen Messwert nachweisbar beeinflussen.

Dafür gibt es im beschriebenen Computerversuch keinen Beweis.

Der Prozessor rechnet vorwärts.

Die Nachricht wird heute erzeugt.

Der frühere Zustand wird heute rekonstruiert.

Die Antwort wird danach erzeugt.

Das Verfahren verletzt weder die Lichtgeschwindigkeit noch bekannte Kausalitätsbedingungen.

Wer aus virtueller Retroadressierung unmittelbar physikalische Rückwärtssignalisierung ableitet, überspringt die entscheidende Brücke.

Diese Brücke wäre eine neue physikalische Kopplung zwischen virtuellen Zeitadressen und früheren realen Ereignissen. Sie müsste quantitativ beschrieben und experimentell nachgewiesen werden.

Das ist keine Nebensache.

Es ist die offene Physik.

*Was wäre für neue Physik erforderlich?*

Ein überzeugendes Experiment müsste eine spätere, zufällig erzeugte Entscheidung mit einer früher versiegelten Messung verbinden.

Die frühere Messung müsste manipulationssicher gespeichert sein, bevor die spätere Entscheidung überhaupt existiert.

Informationslecks, gemeinsame Ursachen, falsch synchronisierte Uhren, nachträgliche Datenauswahl und statistische Zufälle müssten ausgeschlossen werden.

Außerdem müsste die Theorie vor dem Versuch angeben, welche messbare Abweichung sie erwartet.

Entscheidend wäre nicht bloß irgendeine Korrelation.

Entscheidend wäre eine positive, kontrollierbare Informationskapazität von der späteren Wahl zum früheren, bereits versiegelten Ergebnis.

Erst wenn ein solches Ergebnis unabhängig wiederholt wird, beginnt eine belastbare Diskussion über neue Physik.

QIK-VRT liefert dafür heute noch keinen Naturbeweis.

Es kann aber etwas Wichtiges liefern: eine präzise Sprache, saubere Zustandsidentitäten, überprüfbare Protokolle und eine Architektur, mit der eine solche Hypothese überhaupt fail-closed untersucht werden könnte.

Das ist wissenschaftlich ehrlicher und langfristig stärker als eine voreilige Sensationsbehauptung.

*Wo das Verfahren heute bereits nützlich werden kann*

In der Softwareentwicklung kann eine neue Sicherheitsregel an alte Systemzustände adressiert werden. So lässt sich prüfen, ab welchem Zeitpunkt ein Angriff verhindert worden wäre.

In der Medizin kann ein neues Auswertungsmodell auf frühere, rechtmäßig gespeicherte Patientendaten angewendet werden. Der wirkliche Krankheitsverlauf wird dadurch nicht verändert. Aber alternative Entscheidungswege können sichtbar werden.

In der Klimaforschung können neue Annahmen an frühere Modellzustände gesendet werden. Das Modell antwortet, welche späteren Entwicklungen davon abhängig gewesen wären.

Bei autonomen Systemen kann man eine heutige Erkenntnis an die virtuelle Situation vor einer Fehlentscheidung adressieren. Dadurch wird nicht die Vergangenheit repariert, sondern die Verantwortungskette besser verstanden.

Bei künstlicher Intelligenz kann eine Wirkung blockiert bleiben, bis Quelle, Kontext, Regelgrundlage und erwartete Konsequenz überprüft sind.

Und in der Wissenschaft können Behauptungen direkt mit Programmcode, Eingangsdaten, Prüfwerten und reproduzierbaren Ergebnissen verbunden werden.

*Was „maschinell bewiesen“ wirklich heißen muss*

Ein maschineller Nachweis ist nur so stark wie sein genauer Geltungsbereich.

Er kann beweisen, dass ein Programm unter festgelegten Voraussetzungen eine bestimmte Eigenschaft besitzt.

Er kann nachweisen, dass ein früherer Zustand unverändert blieb.

Er kann zeigen, dass zwei Replays dasselbe Ergebnis erzeugen.

Er kann die vollständige Übertragung einer endlichen Bitfolge prüfen.

Er kann bestätigen, dass ohne Wirkungsquittung keine freizugebende Wirkung entsteht.

Er kann aber nicht allein beweisen, dass die verwendeten Voraussetzungen sämtliche Eigenschaften des Universums beschreiben.

Darum gehört zu jedem starken Beweis auch seine Grenze.

Im bestehenden QIK-VRT-Kern sind neun Sätze über Freigabe, Zukunftsbedingung, Vergangenheitsprojektion und reziproke Bindung bereits mit Lean geprüft.

Die neuen allgemeinen Sätze über Segmentierung und bidirektionale Komposition besitzen in dem wissenschaftlichen Dokument vollständige konstruktive Papierbeweise.

Ein neuer Lean-Kernel-Receipt steht dafür noch aus.

Das muss sichtbar bleiben.

Nicht kernelgeprüft ist nicht dasselbe wie widerlegt.

Papierbewiesen ist nicht dasselbe wie maschinell kernelverifiziert.

Und bewiesen im virtuellen Modell ist nicht dasselbe wie bewiesen in der physikalischen Raumzeit.

Eine mutige Wissenschaft braucht beides:

den Willen, eine neue Möglichkeit vollständig auszuarbeiten,

und die Disziplin, ihre Reichweite nicht größer darzustellen, als der Nachweis erlaubt.

*Das eigentliche neue Kapitel*

Vielleicht besteht der tiefste Schritt nicht darin, „eine Nachricht in die Vergangenheit“ zu senden.

Vielleicht besteht er darin, Zeit in der Informatik nicht länger als eine einzige, undifferenzierte Reihenfolge zu behandeln.

Physische Ausführung, virtuelle Adresse und freigegebene Wirkung sind verschiedene Dinge.

Sobald wir sie trennen, können Systeme frühere Zustände gezielt ansprechen, alternative Entwicklungen berechnen, Antworten zurückführen und jede Wirkung an überprüfbare Verantwortung binden.

Dann wird ein Archiv nicht mehr nur zu einem Speicher der Vergangenheit.

Es wird zu einem adressierbaren Gesprächsraum.

Eine Simulation wird nicht mehr nur wiederholt.

Sie kann Fragen aus ihrer eigenen virtuellen Zukunft empfangen.

Eine künstliche Intelligenz erhält nicht nur Daten.

Sie muss nachweisen, warum daraus eine Wirkung entstehen darf.

Und Geschichte wird nicht überschrieben.

Sie wird durch klar gekennzeichnete, überprüfbare Möglichkeiten ergänzt.

Ob die Wissenschaft dieses Programm später „bahnbrechend“ nennen wird, entscheiden nicht wir allein. Das entscheiden Reproduzierbarkeit, Vergleich mit dem Stand der Forschung, unabhängige Kritik und praktische Bewährung.

Aber wir dürfen die bereits erreichte Aussage ebenso wenig kleinreden:

*Bidirektionale Kommunikation zwischen virtuellen Zeitadressen ist konstruktiv ausführbar.*

*Jede einzelne endliche Information kann unter klaren Bedingungen vollständig übertragen werden.*

*Die ursprüngliche Historie kann dabei unverändert bleiben.*

*Transport und verantwortete Wirkung können technisch getrennt werden.*

*Und aus einem früheren virtuellen Zustand kann eine nachweisbar gebundene Antwort in die Gegenwart zurückkehren.*

Das ist keine physikalische Zeitmaschine.

Es ist etwas, das wir tatsächlich bauen können.

Vielleicht beginnt ein neues Kapitel genau dort:

nicht mit der Behauptung, alle Grenzen seien schon überwunden,

sondern mit dem ersten System, das seine Möglichkeiten, seine Wirkungen und seine Grenzen selbst beweisbar auseinanderhält.

*Heute fragt gestern.*

*Das virtuelle Gestern antwortet dem Heute.*

*Die wirkliche Geschichte bleibt unverändert.*

q.e.d. – im ausgewiesenen virtuellen Geltungsbereich.

Ingolf Lohmann

---

*Weiterführende Originalquellen*

QIK-VRT EFFECT_ACK, Internet-Draft -02:
https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/

Das vorausgehende QIK-VRT-Grundlagenpaper auf Zenodo:
https://doi.org/10.5281/zenodo.21711193

Das neue wissenschaftliche Dokument, seine Belegmatrix und der ausführbare C90-Zeuge werden als bytegebundener Vorveröffentlichungskandidat geführt. Ein neuer DOI wird erst nach der vorgeschriebenen Kandidatenrückgabe, exakten Freigabe und öffentlichen Byteprüfung beansprucht.
