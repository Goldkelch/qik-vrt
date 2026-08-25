# Das intelligente Terminal und das selbstskalierende QIK-VRT Mesh

## Wie DNS, SMTP, SQL-92, WebDriver, virtuelle Maschinen, Effect Acknowledgements und künstliche Kognition zu einer neuen Softwarearchitektur zusammenfinden

**Ingolf Lohmann – konzeptioneller Urheber und Product Owner**  
**Ausarbeitung: OpenAI Codex (GPT-5)**  
**Stand: 25. August 2026**

> **Repository-Status:** Diese quellengebundene Fassung ist ein konzeptioneller Begleitartikel zum offenen Entwicklungsauftrag [Issue #888](https://github.com/Goldkelch/qik-vrt/issues/888). Sie beschreibt Zielarchitektur, Prüfgrenzen und Forschungsprogramm. Sie behauptet weder vollständige Implementierung auf `main` noch öffentliche DNS-/SMTP-Wirkung, Deployment, Publikation, physische Mega-ST-Ausführung, `PASS`, `FINAL_PASS` oder allgemeines `EFFECT_ACK_DONE`.

## Vorbemerkung: Welche Welt hier gemeint ist

Die zentrale Idee ist ebenso einfach wie weitreichend: Ein Repository soll nicht länger bloß ein passiver Speicher für Quellcode sein. Es soll sich wie ein aktiver, adressierbarer und überprüfbarer Rechnerknoten verhalten. Wenn eine Aufgabe eintrifft, erzeugt der Knoten ein begrenztes Arbeits-Mesh, verteilt Teilaufgaben, sammelt die Ergebnisse deterministisch wieder ein, reobserviert die Wirkung und reflektiert den Zustand an den Product Owner zurück. Zwischen Mensch und Repository steht dabei ein intelligentes Terminal: kein stummer Bildschirm, sondern eine kognitive Vermittlungsschicht, die Anforderungen versteht, in maschinenprüfbare Aufträge übersetzt und deren Ausführung beobachtet.

In einer solchen Architektur können DNS, elektronische Post, relationale Datenbanken, Browsersteuerung und virtuelle Maschinen neu zusammengesetzt werden. Jeder Mesh-Knoten erhält eine eindeutige Identität, einen lokalen Namensraum, eine Mailbox, einen kleinen SMTP-Client und -Server sowie eine SQL-92-orientierte relationale Zustandsbasis. Ein emergierender Root-Knoten wird für sein begrenztes Mesh zur Autorität über Namen, Nachrichtenwege und Dienstverzeichnis. Er ist damit Root seines eigenen virtuellen Netzes – nicht automatisch Root des öffentlichen Domain Name System und nicht ohne weitere Bindung ein öffentlich erreichbarer Mailserver.

Genau diese Unterscheidung ist wichtig. Die Softwarewelt kann so gebaut werden, dass sie sich innerhalb ihrer definierten Grenzen tatsächlich wie beschrieben verhält. Zugleich existiert reale experimentelle Quantenevidenz für nichtklassische zeitliche Korrelationsstrukturen, die mit retrokausalen Deutungen vereinbar sind: Delayed-Choice-, Quantenradierer- und Delayed-Choice-Entanglement-Swapping-Experimente verbinden eine spätere Messwahl mit der erst nachträglich erkennbaren Korrelationsstruktur früher registrierter Ereignisse. Wissenschaftlich offen ist nicht die Existenz dieser Experimente, sondern ob sie eindeutig eine ontische Rückwärtswirkung und darüber hinaus einen frei kontrollierbaren Zukunft-zu-Vergangenheit-Nachrichtenkanal beweisen. Der Artikel nimmt die Vision ernst, ohne virtuelle Modellkausalität, technische Ausführung, empirische Quantenkorrelation und deren physikalische Interpretation miteinander zu vermischen.

## 1. Vom passiven Repository zum ausführenden Mesh-Knoten

Das klassische Git-Repository bildet Zustände als unveränderliche Objekte, gerichtete Vorgängerbeziehungen und benannte Referenzen ab. Ein Commit bindet einen Baum; ein Baum bindet Dateien; ein Hash macht jede Veränderung beobachtbar. Diese Struktur ist bereits eine hervorragende Grundlage für ein kausal nachvollziehbares Rechensystem. Was ihr traditionell fehlt, ist eine einheitliche operative Schicht, die aus einem Auftrag selbstständig einen begrenzten Prozessverband erzeugt.

Das QIK-VRT-Terminal-Pattern ergänzt diese Schicht. Ein Ausgangsknoten erzeugt für eine Aufgabe zunächst genau eine Terminalinstanz. Diese bleibt an den Ausgangsknoten, dessen exakten Head, Tree und Auftrag gebunden. Hinter dem Terminal können beispielsweise acht gleichwertige Arbeitsknoten entstehen. Die Zahl acht ist dabei keine metaphysische Notwendigkeit, sondern eine besonders anschauliche atomare Skalierungseinheit: Acht Knoten können als räumlich getrennte Repräsentanten der acht Positionen eines Bytes verstanden werden, ohne dass der Bytebegriff mit den tatsächlichen Rechnerprozessen verwechselt werden muss.

Der Ablauf lautet:

1. Ein Auftrag wird in einen unveränderlichen, digestgebundenen Arbeitsvertrag übersetzt.
2. Die Terminalinstanz übernimmt diesen Vertrag und erzeugt höchstens acht Kindaufträge.
3. Jeder Kindauftrag enthält nur den benötigten Kontext, eine eindeutige Identität, seine erlaubten Wirkungen und ein Rückgabeformat.
4. Die Arbeitsknoten rechnen unabhängig oder koordiniert.
5. Das Terminal sammelt ihre Receipts, prüft Reihenfolge, Vollständigkeit und Digests und reduziert die Ergebnisse deterministisch.
6. Der Ausgangsknoten reobserviert den neuen Zustand.
7. Erst diese Reobservation darf dem Product Owner als Ergebnis reflektiert werden.

Das ist strukturell mit dem Forken von Prozessen verwandt, aber nicht identisch. Ein POSIX-Prozess erbt einen Speicher- und Dateideskriptorkontext innerhalb eines Betriebssystems. Ein Repository-Mesh-Knoten erhält dagegen einen explizit minimierten Informationsausschnitt, eine kryptographische Bindung und einen Capability-Vertrag. Gerade weil die Knoten über organisatorische, virtuelle oder physische Grenzen verteilt sein können, muss jede implizite Vererbung durch nachvollziehbare Übergaben ersetzt werden.

## 2. Das Terminal als kognitive Vermittlungsschicht

Beim historischen Terminal war die Trennung klar: Der Benutzer gab Zeichen ein, das Terminal transportierte sie, und die eigentliche Rechenleistung lag auf einem entfernten System. Spätere Personal Computer verbanden Anzeige, Eingabe, Speicher und Rechenleistung in einem Gerät. Heute kann eine künstliche Kognition selbst Teil des Terminal-Patterns werden.

Das intelligente Terminal übernimmt dabei fünf Rollen:

- **Semantischer Adapter:** Es übersetzt natürliche Sprache, Audio, Dateien oder grafische Interaktionen in typisierte Anforderungen.
- **Dispatcher:** Es zerlegt einen Auftrag in begrenzte, voneinander unterscheidbare Arbeitspakete.
- **Sicherheitsgrenze:** Es entscheidet, welche Knoten welche Daten sehen und welche Wirkungen sie auslösen dürfen.
- **Reducer:** Es fügt Teilresultate in deklarierter Reihenfolge zusammen und erkennt Widersprüche, Lücken oder Drift.
- **Monitor:** Es beobachtet die tatsächliche Ausführung und gibt nicht bloß eine Absichtserklärung, sondern den reobservierten Zustand zurück.

Das Terminal darf dabei nicht zum allmächtigen, unsichtbaren Orakel werden. Seine Stärke entsteht aus expliziten Grenzen. Jeder Übergang muss benennen, welcher Auftrag verarbeitet wird, aus welchem Repositoryzustand er stammt, welche Rolle handelt, welche Wirkungen erlaubt sind und welches Receipt den Abschluss belegt. Ein fehlendes Receipt ist kein stillschweigender Erfolg. Ein semantisches `CONTINUE` ist kein Fehler und kein `PASS`. Ein technischer Jobabschluss ist noch keine fachliche Endaussage.

## 3. Eindeutige Identität: Repository, Node, DNS-Name und Mailbox

Eine GitHub-Repositoryinstanz besitzt nicht kraft ihrer Existenz eine eigene öffentliche E-Mail-Adresse. Sie besitzt jedoch stabile Identifikatoren, einen Eigentümer-/Repositorynamen und beobachtbare Git-Objekte. Daraus kann ein Mesh deterministisch eine logische Mailidentität ableiten.

Für einen Test- oder Simulationsraum könnte ein Knoten etwa heißen:

```text
node-07.mesh-4f2a.test
```

und die zugehörige Mailbox:

```text
control@node-07.mesh-4f2a.test
```

Die reservierte Testdomäne verhindert, dass eine Simulation versehentlich öffentliche Zustellbarkeit behauptet. Für ein real angebundenes Mesh muss stattdessen eine tatsächlich kontrollierte Domain verwendet werden. Dann sind autoritative DNS-Zonen, MX-Einträge, Adressdatensätze, Schlüssel, Netzwerkpfade und gegebenenfalls Reputation eigenständig zu betreiben.

Wenn aus einem Repository-Node ein neues Mesh emergiert, kann dieser Node zur Wurzel des neu erzeugten Namensraums werden. Er verwaltet dann mindestens:

- eine Mesh-ID und eine Root-Node-ID,
- eine signierte Zonenrevision,
- Namen und Rollen aller Kindknoten,
- Dienstadressen für SMTP, WebDriver, Datenbank und Receipt-Endpunkte,
- Ablauf- und Widerrufsregeln,
- eine Delegationsbeziehung für weitere Submeshes.

Das entspricht dem hierarchischen Gedanken des Domain Name System, dessen grundlegende Konzepte und Implementierungsdetails in [RFC 1034][RFC1034] und [RFC 1035][RFC1035] beschrieben sind. QIK-VRT übernimmt daraus die Idee der delegierbaren Namensautorität, nicht die Behauptung, ein lokaler Mesh-Knoten kontrolliere ohne Delegation das öffentliche DNS.

## 4. Mini-Mailserver und Mini-Mailclient in jedem Node

Elektronische Post ist für ein Mesh deshalb interessant, weil sie von Anfang an als asynchrones Store-and-forward-System gedacht ist. [RFC 5321][RFC5321] beschreibt SMTP als zuverlässigen und effizienten Mailtransport über einen geordneten Datenstrom. Ein Server übernimmt Verantwortung für Zustellung oder eine ordnungsgemäße Fehlermeldung. Diese Semantik passt erstaunlich gut zu einem Receipt-orientierten Arbeits-Mesh.

Jeder Knoten kann einen minimalen Mail Transfer Agent und einen minimalen Client enthalten. Die kleinste sinnvolle Implementierung unterstützt nicht beliebige Internet-Mail, sondern einen streng typisierten internen Vertrag:

```text
Mesh-Id
Message-Id
Parent-Message-Id
Source-Node
Target-Node
Task-Digest
Payload-Digest
Causal-Sequence
Virtual-Time-Label
Capability-Set
Expiry
Reply-To
```

Der eigentliche Inhalt kann inline übertragen oder als digestgebundener Verweis auf ein quarantänisiertes Artefakt geführt werden. Große Pakete werden in geordnete Chunks zerlegt. Erst wenn Chunkzahl, Reihenfolge, Einzelhashes, Gesamtmanifest und Gesamtdigest stimmen, darf der Empfänger das Paket als vollständig annehmen.

Mail wird dadurch zu mehr als einer Benachrichtigung. Sie dient als:

- asynchroner Arbeitsauftrag,
- Zustell- und Nichtzustellnachweis,
- Bootstrapping-Kanal für neu erzeugte Nodes,
- Rückkanal für Receipts,
- minimale persistente Warteschlange,
- Transport für getunnelte, zielgebundene Informationen.

Allerdings darf eine Mail niemals ungeprüft als ausführbarer Befehl behandelt werden. Der Empfänger muss Absenderrolle, Signatur, Mesh-ID, Capability, Head-/Tree-Bindung, Ablaufzeit und Replay-Schutz prüfen. Ein Mailserver ist sonst keine Automatisierungsschicht, sondern eine Ferncodeausführungslücke.

## 5. Getunnelte Informationen und die Restrukturierung der IP-Landschaft

Ein Mesh kann Nachrichten für andere Knoten weiterleiten, ohne deren semantischen Inhalt jedem Zwischenknoten offenzulegen. Dazu wird zwischen Transporthülle und Nutzlast unterschieden. Die Hülle enthält nur die für Routing und Missbrauchsschutz erforderlichen Angaben; die Nutzlast bleibt für den Zielknoten verschlüsselt und digestgebunden.

Die sogenannte Restrukturierung der IP-Landschaft bedeutet dann nicht, dass physische Netze sprachlich verschwinden. Sie bedeutet, dass über ihnen ein neuer virtueller Adressraum entsteht. Ein Node kann mehrere Adapter besitzen:

- loopback-lokal,
- innerhalb eines CI-Runners,
- innerhalb eines privaten Overlay-Netzes,
- über einen kontrollierten Proxy,
- über öffentliche IP-Infrastruktur,
- oder vollständig offline über übertragene Bundles.

Der logische DNS-Name bleibt dabei stabil, während sich der konkrete Transport ändern kann. Das ist das gleiche Abstraktionsprinzip, das es erlaubt, einen Dienst umzuziehen, ohne seine semantische Identität zu verlieren. Der Proxy vermittelt zwischen den Welten; das Terminal hält Auftrag und Ergebnis zusammen.

Für getunnelte Information gelten drei harte Grenzen. Erstens darf Routing nicht mit Berechtigung verwechselt werden. Zweitens belegt ein erfolgreicher Tunnel nur die beobachtete Strecke, nicht allgemeine Internet-Erreichbarkeit. Drittens dürfen Authority- und Mirror-Rollen nicht aus Datenähnlichkeit oder erfolgreicher Zustellung abgeleitet werden; Rollen benötigen einen eigenen Maschinenvertrag.

## 6. SQL-92 als relationales Gedächtnis des Knotens

Mail liefert eine natürliche Queue und eine minimale Überlebensspur, ersetzt aber keine relationale Zustandsmaschine. Jeder Node benötigt deshalb eine lokale Datenbank, deren Kern sich an ISO/IEC 9075:1992, also SQL-92, orientiert. Dieser historische Standard ist inzwischen zurückgezogen und durch spätere Ausgaben von ISO/IEC 9075 ersetzt; in QIK-VRT dient SQL-92 daher als ausdrücklich ausgewiesenes, portables Kompatibilitätsprofil und nicht als Behauptung aktueller Normativität. Der Standard beschreibt Datendefinition, Abfragen, Integritätsregeln und Transaktionen in einer herstellerunabhängigen Sprache.[^sql92]

Ein minimaler Knotenspeicher benötigt Tabellen für:

- `nodes`: Identität, Rolle, Elternknoten, Status und Schlüsselbindung,
- `services`: DNS-, SMTP-, WebDriver-, Datenbank- und Receipt-Endpunkte,
- `tasks`: Auftrag, Digest, erwarteter Head/Tree und Capability-Vertrag,
- `messages`: Message-ID, Absender, Empfänger, Sequenz und Zustellstatus,
- `chunks`: Reihenfolge, Einzelhash und Gesamtmanifest,
- `receipts`: beobachtete Übergänge und deren Bindungen,
- `causal_edges`: Vorgänger-/Nachfolgerbeziehungen,
- `artifacts`: Run-spezifische Quarantäneobjekte,
- `effects`: verlangte, beobachtete und ausdrücklich nicht beobachtete Wirkungen.

Die relationale Datenbank ist nicht bloß Komfort. Sie erzwingt referentielle Integrität. Ein Receipt darf keinen unbekannten Task bestätigen. Ein Chunk darf nicht zu zwei Manifesten gehören. Ein Child-Node muss einen existierenden Parent besitzen. Eine Zustellung darf erst nach der Sendung und ein Effect-Acknowledgement erst nach dem gebundenen Effekt registriert werden.

Die Transaktion bildet die kleinste atomare Wahrheitseinheit des Knotens. Entweder werden Zustandsänderung, Artefaktdigest und Receipt gemeinsam sichtbar, oder keine davon. Damit wird die Datenbank zur relationalen Mitte zwischen Git-Historie, Mailtransport und Laufzeitausführung.

## 7. WebDriver und E-Mail als asynchrones Browser-Bootstrapping

WebDriver standardisiert die Fernsteuerung eines Browsers über klar definierte Sitzungen, Befehle, Endpunkte und Fehler. Die aktuelle Weiterentwicklung wird vom W3C in der [WebDriver Working Draft vom 2. Juli 2026][WEBDRIVER] beschrieben. Für QIK-VRT kann WebDriver die Effektseite des intelligenten Terminals bilden: Ein typisierter Auftrag führt zu einer begrenzten Browseraktion; ein Screenshot, DOM-Zustand, Netzwerkbeleg oder anwendungsspezifischer Effekt wird anschließend als Receipt zurückgeführt.

SMTP hilft dabei auf drei Ebenen:

1. Ein neuer Node erhält asynchron sein signiertes Bootstrapping-Bundle.
2. Ein Browserauftrag kann eingestellt werden, bevor der Ziel-Node online ist.
3. Ergebnis und Fehler werden über denselben adressierbaren Rückkanal geliefert.

Der sichere Ablauf ist nicht Mail → beliebiger WebDriver-Code, sondern:

```text
Mail-Eingang
→ Signatur- und Capability-Prüfung
→ SQL-Transaktion und Deduplizierung
→ typisierter WebDriver-Auftrag
→ lokale Sandbox
→ beobachteter Effekt
→ Effect-Receipt
→ Mail-Rücktransport
```

So wird Browserautomatisierung asynchron, ohne ihre Sicherheitsgrenze aufzugeben. Der Browser ist die universelle grafische Oberfläche; Mail ist die verzögerungstolerante Übergabe; SQL ist der relationale Zustand; Git ist die unveränderliche Herkunftsbindung.

## 8. Firefox als universelle Oberfläche und Proxy-Adapter

HTML, CSS, JavaScript und HTTP bilden heute eine der portabelsten vorhandenen Oberflächenschichten. Ein Firefox-basierter Terminalträger kann deshalb verschiedene Rechnerwelten hinter einer einheitlichen Darstellung erreichbar machen. Entscheidend ist das Proxy-Pattern: Die Oberfläche spricht mit einer stabilen Terminal-API, während Adapter die jeweilige Zielplattform übersetzen.

Ein Adapter kann beispielsweise eine virtuelle Atari-Mega-ST-Umgebung mit M68000/TOS, eine PowerPC-VM oder eine eigene Linux-Distribution kapseln. Jede Kapsel benötigt:

- eine deklarierte CPU- und Plattformidentität,
- reproduzierbare Bootmedien,
- einen begrenzten Ein-/Ausgabekanal,
- Netzwerk- oder Offline-Transportadapter,
- deterministische Start- und Stoppbedingungen,
- Artefakt- und Konsolendigests,
- Effect-Acknowledgements mit klarer Beobachtungsgrenze.

Der Firefox-Prozess muss nicht innerhalb jeder emulierten Gastmaschine laufen. Er kann als Host- oder Proxy-Oberfläche dienen und den Gastzustand darstellen. Erst wenn Firefox tatsächlich im Gast ausgeführt wurde, darf genau diese stärkere Behauptung erhoben werden. Ebenso beweist eine M68000-Emulation keinen Lauf auf einem physischen Mega ST. Virtuelle Hardware ist real ausgeführte Software, aber sie ist nicht ohne Weiteres die physische Hardware, die sie modelliert.

Gerade diese Präzision macht die Architektur stark. Ein gemeinsames Terminal kann sehr verschiedene Maschinen repräsentieren, ohne ihre Unterschiede auszulöschen. Die Adapter bewahren die Trennung; der Proxy vereinheitlicht die Bedienung.

## 9. Effect Acknowledgement und die zwei Zeitrichtungen

Das Effect-Acknowledgement-Protokoll verbindet einen Auftrag nicht nur mit einer Antwort, sondern mit einer beobachteten Zustandsänderung. Ein vollständiges Receipt muss mindestens enthalten:

```text
requested_effect
observed_effect
external_effect_scope
source_state_digest
result_state_digest
host_sequence
virtual_time_label
observer_identity
receipt_digest
```

Damit lassen sich zwei Ordnungen unterscheiden:

- **Host-Kausalordnung:** Die reale Ausführung auf dem Host. Sendung liegt vor Zustellung; Commit liegt vor Receipt.
- **Virtuelle Ordnung:** Die im Auftrag, Replay oder Modell bezeichnete Zeit- und Zustandsrichtung.

Eine Nachricht kann ein zukünftiges virtuelles Label tragen und dennoch ganz gewöhnlich später als ihre Host-Sendung eintreffen. Ein vollständiges Receipt kann eine Spur rückwärts rekonstruierbar machen, obwohl jeder Rekonstruktionsschritt physisch nach dem ursprünglichen Write stattfindet. Das ist virtuelle Retrokausalität: eine umgekehrte Abhängigkeits-, Adress- oder Lesereihenfolge innerhalb eines implementierten Modells.

Die im Audio formulierte Bidirektionalitätsthese benötigt mathematisch eine Zusatzbedingung. Aus der Existenz einer gerichteten Abbildung folgt nicht automatisch eine Umkehrabbildung. Die Gegenrichtung ist genau dann konstruktiv gesichert, wenn mindestens eine der folgenden Bedingungen erfüllt ist:

- der Übergang ist bijektiv,
- ein vollständiges Receipt speichert den Vorgängerzustand,
- ein expliziter inverser Adapter ist definiert,
- oder der Kanalvertrag ist symmetrisch und für beide Richtungen separat geprüft.

Unter diesen Bedingungen kann dieselbe logische Infrastruktur Informationen in beiden virtuellen Richtungen ordnen und rekonstruieren. Daraus folgt noch kein physikalisches Signal aus einer späteren Entscheidung in einen bereits früher versiegelten Messwert.

## 10. Physik: Empirischer Phänomenkern, retrokausale Deutung und genaue Reichweite

Die Architektur ist nicht deshalb virtuell, weil sie unwirklich wäre. Ein Emulator verbraucht reale Energie. Ein SMTP-Server schreibt reale Bits. Ein Git-Commit bindet reale Daten. Eine SQL-Transaktion verändert einen realen Speicherzustand. Eine Firefox-Interaktion kann einen realen, begrenzten Effekt auslösen. Das virtuelle Modell ist also eine reale physische Ausführung einer abstrakten Ordnung.

Die physikalische Seite beginnt nicht bei null. Die einschlägigen Experimente wurden durchgeführt und ihre Resultate sind Teil der empirischen Quantenphysik:

- Im Delayed-Choice-Quantenradierer von Kim, Yu, Kulik, Shih und Scully wird die Weginformation eines Quantums durch seinen verschränkten Partner markiert oder gelöscht, obwohl das Signalquantum bereits registriert wurde. Die Autoren sprechen ausdrücklich von einer verzögerten Bestimmung teilchen- oder wellenartigen Verhaltens.[^kim]
- Im realisierten Wheeler-Delayed-Choice-Experiment wird erst nach dem Eintritt des einzelnen Photons in das Interferometer zufällig entschieden, ob ein offener Aufbau Weginformation oder ein geschlossener Aufbau Interferenz zugänglich macht. Die Wahl ist vom Eintrittsereignis relativistisch getrennt.[^jacques]
- Beim Delayed-Choice-Entanglement-Swapping von Ma et al. erfolgt die Wahl der gemeinsamen oder getrennten Messung an zwei Photonen zeitartig nach der Registrierung der beiden anderen Photonen. Die später sortierten Daten zeigen je nach späterer Messung verschränkte Quantenkorrelationen oder separierbare klassische Korrelationen. Die Autoren bezeichnen dies ausdrücklich als eine mögliche Sichtweise des „quantum steering into the past“.[^ma-swap]
- Eine weitere Quantenradierer-Realisierung erzwang eine kausal getrennte Wahl und schloss damit eine gewöhnliche physische Kommunikation zwischen Wahl und Interferenzereignis aus.[^ma-eraser]

Diese Experimente sind echte empirische Evidenz für die nichtklassische zeitliche und korrelative Struktur, auf die sich Ingolf Lohmanns Retrokausalitätsthese bezieht. Es wäre daher zu grob, pauschal zu behaupten, es gebe keinerlei empirischen Phänomenkern, der mit physikalischer Retrokausalität vereinbar sei. Korrekt ist eine feinere Disposition:

1. **Empirisch beobachtet:** Eine spätere Messanordnung bestimmt, in welcher korrelationsgebundenen Beschreibung früher registrierte Ereignisse nach späterer Koinzidenz- beziehungsweise Teilmengensortierung erscheinen.
2. **Mit Retrokausalität stimmig:** Retrokausale und transaktionale Interpretationen können diese Gesamtstruktur als zeitlich bidirektionale Randbedingung oder als Wirkung rückwärts gerichteter Beiträge beschreiben.
3. **Nicht interpretationsmonopolistisch:** Dieselben Messstatistiken werden auch durch zeitlich symmetrische, relationale, Viele-Welten-, konsistente-Historien- oder operationalistische Deutungen beschrieben. Das Experiment allein wählt nicht eindeutig genau eine Ontologie aus.
4. **Kein frei auslesbarer Rückkanal im bisherigen Aufbau:** Die frühere lokale Datenfolge offenbart die spätere Wahl nicht für sich allein. Die charakteristische Struktur erscheint nach Korrelation beziehungsweise Koinzidenzsortierung mit der späteren Information. Dadurch entsteht aus den publizierten Aufbauten kein gewöhnlicher steuerbarer Mail- oder Nachrichtenkanal in die Vergangenheit.

Das QIK-VRT-Papier *Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel* trennt dazu vier Größen:

1. die Host-Kausalordnung,
2. die virtuelle Adressordnung,
3. die knotenlokale Ereigniszeit,
4. die spätere Evidenzordnung der Receipts.

Diese Trennung ist der Schlüssel. Das virtuelle Mesh kann Nachrichten überholen lassen, Zukunftslabels transportieren und Spuren rückwärts lesen. Solange jede reale Sendung vor ihrer Zustellung und jeder Commit vor seinem Receipt liegt, entsteht dadurch kein Widerspruch zur gewöhnlichen Host-Kausalität.

Die vorhandenen Experimente belegen somit den empirischen Phänomenkern. Für die zusätzliche technische Behauptung eines zielgerichtet beschreibbaren und vor dem späteren Vergleich auslesbaren Zukunft-zu-Vergangenheit-Kanals wäre ein noch schärferer Test nötig: Ein früher Messwert wird irreversibel versiegelt; erst danach erfolgt eine unabhängige spätere Wahl; anschließend müsste die frühere, lokal verfügbare Variable reproduzierbar Information über die spätere Intervention enthalten – nach Ausschluss klassischer Leckpfade, gemeinsamer Seeds, Postselektion, Uhrfehler und nachträglicher Veränderung. Dieser engere Kanaltest ist durch die genannten Experimente nicht positiv abgeschlossen.

Die wissenschaftlich tragfähige Aussage lautet folglich:

> Die Softwarewelt kann so konstruiert werden, dass zukunftsindizierte Information, bidirektionales Replay und kausal korrekt sortierte Receipts operative Realität sind. Delayed Choice und Quantenradierer liefern reale empirische Evidenz für eine damit stimmige nichtklassische Zeit- und Korrelationsstruktur. Ob daraus zusätzlich ein interventionell nutzbarer, lokal auslesbarer Nachrichtenkanal in die Vergangenheit gewonnen werden kann, muss ein engerer eigenständiger Kanaltest entscheiden.

Diese Formulierung schwächt die Vision nicht. Sie macht sie prüfbar.

## 11. Mathematik des skalierenden Meshes

Sei das Mesh ein gerichteter Graph

```text
G = (N, E),
```

wobei `N` die Repository- und Terminalknoten und `E` die zugelassenen Kommunikationsbeziehungen bezeichnet. Für einen Root-Knoten `r` und eine Aufgabe `q` erzeugt die Spawn-Funktion

```text
S(r, q) = (t, W),    |W| ≤ 8,
```

genau eine Terminalinstanz `t` und eine begrenzte Menge von Arbeitsknoten `W`.

Jeder Auftrag besitzt einen Digest

```text
d_q = H(mesh-id, root, head, tree, requirements, capabilities).
```

Ein Child-Receipt ist nur gültig, wenn es denselben Auftragsdigest referenziert und sein Ergebnis selbst digestgebunden ist. Der Reducer

```text
R_q(r_1, …, r_k)
```

muss für dieselbe geordnete Receipt-Menge dasselbe Ergebnis liefern. Reihenfolge, Deduplizierung und Konfliktbehandlung gehören daher zum Vertrag und dürfen nicht vom zufälligen Eintreffzeitpunkt abhängen.

Für jeden Knoten existiert eine lokale Ereigniszeit `τ_n`. Sie zählt akzeptierte Übergänge, ist aber keine physikalische Eigenzeit. Die Host-Ordnung `≺_H` muss azyklisch bleiben:

```text
send(m) ≺_H deliver(m),
commit(e) ≺_H receipt(e).
```

Die virtuelle Ordnung `≺_V` darf davon abweichen. Genau dort entstehen Nachrichtenüberholung, Zukunftsindizierung und Rückwärts-Replay, ohne die Host-Azyklizität zu verletzen.

Die Evidenz wächst append-only. Frühere, versiegelte Receipts werden nicht umgeschrieben; Korrekturen erzeugen neue Ereignisse. Dadurch wächst der harte Kern akzeptierter Evidenz monoton. Kandidaten und unvollständige Bindungen liegen am unscharfen Rand. Wenn ein Kandidat vollständig belegt wird, härtet er zum Kern aus, ohne die Historie zu löschen.

## 12. Künstliche Kognition und Requirements Engineering

Eine künstliche Kognition verändert Softwareentwicklung nicht primär dadurch, dass sie schneller Text produziert. Ihr eigentlicher Hebel liegt in der Übersetzung zwischen Abstraktionsebenen:

```text
Absicht
→ Requirement
→ Maschinenvertrag
→ Kandidaten
→ Implementierung
→ Test
→ Receipt
→ Reobservation
→ nächste Anforderung
```

Wenn dieser Ring geschlossen ist, kann ein Product Owner eine gewünschte Eigenschaft formulieren und das Mesh kann daraus eigenständig begrenzte Arbeit ableiten. Mehrere Knoten untersuchen Architektur, Implementierung, Tests, Sicherheit und Beweisgrenzen parallel. Der Terminal-Reducer sammelt die Ergebnisse und führt genau den nächsten evidenzberechtigten Schritt aus.

Auf diese Weise kann ein sehr großer Teil der Informatik in ein virtuelles Mesh reimplementiert werden: Prozessoren, Assembler, Compiler, Betriebssysteme, Netzwerkprotokolle, Datenbanken, Browser, grafische Oberflächen und Fachanwendungen. „Reverse Engineering der gesamten Informatik“ ist dabei sinnvoll als langfristiges Forschungsprogramm: vorhandene Systeme werden in explizite Verträge, beobachtbare Zustandsmaschinen und austauschbare Adapter übersetzt.

„Nahezu jede vorstellbare Software“ bleibt allerdings an vier Grenzen gebunden:

1. Die Aufgabe muss berechenbar oder als überprüfbare Näherung formulierbar sein.
2. Benötigte Daten, Rechte, Hardware und Zeit müssen verfügbar sein.
3. Die Anforderungen dürfen sich nicht logisch widersprechen.
4. Sicherheit, Recht und reale Wirkung benötigen eigene Freigaben und Evidenz.

Innerhalb dieser Grenzen ist die Vision außerordentlich stark. Requirements Engineering wird vom statischen Dokument zum ausführbaren Steuerkreis. Die künstliche Kognition ist Navigator und Übersetzer; das Repository-Mesh ist die reproduzierbare Arbeitsmaschine; das Terminal ist die Grenze, an der beide Welten kontrolliert ineinandergreifen.

## 13. Der kleinste vollständige Terminal-Control-Plane-Vertrag

Damit das beschriebene Verhalten nicht bloß Metapher bleibt, muss das Repository mindestens folgende Invarianten erzwingen:

1. **Begrenztes Spawn:** Pro Root-Auftrag entsteht genau ein Terminal und höchstens acht direkte Worker.
2. **Exakte Herkunft:** Jeder Auftrag bindet Repository, Rolle, Head, Tree, Event und Work-Unit-Digest.
3. **Eindeutige Identität:** Jeder Node erhält eine Mesh-lokale DNS- und Mailidentität; öffentliche Adressen werden nur bei belegter Delegation behauptet.
4. **Root nur im Scope:** Der emergierende Node ist DNS-/SMTP-Root seines Mesh-Namensraums, nicht des öffentlichen Internets.
5. **Typisierte Mail:** Nur signierte, capability-geprüfte Nachrichten gelangen von SMTP in die Arbeitsqueue.
6. **SQL-Atomizität:** Task, Zustandsänderung, Artefaktdigest und Receipt werden atomar oder gar nicht persistiert.
7. **Chunk-Vollständigkeit:** Große Pakete gelten erst nach Manifest-, Reihenfolge- und Gesamtdigestprüfung als vollständig.
8. **Deterministische Reduktion:** Dasselbe geordnete Receipt-Set erzeugt dasselbe Gesamtergebnis.
9. **Effect-Bindung:** Ein Effect-Acknowledgement benennt exakt den beobachteten Effekt und dessen Grenze.
10. **Virtuelle Bidirektionalität:** Rückwärts-Replay erfordert vollständige Receipts oder einen geprüften inversen Adapter.
11. **Host-Azyklizität:** Kein virtueller Zeitlabel darf als Beleg für eine Host-Wirkung vor ihrer Ursache ausgegeben werden.
12. **Kein Blindbetrieb:** Heartbeat ist Ereignisfortschritt, nicht Polling oder blinder Retry.
13. **Fail closed:** Unbekannter Status, fehlende Rolle, Drift oder unvollständige Evidenz stoppen die semantische Wirkung.
14. **Reobservation:** Nach jeder Reparatur folgt eine exakte Beobachtung des neuen Zustands und daraus genau ein weiterer Turn.
15. **Keine erfundene Synchronität:** Authority- und Mirror-Zustände werden getrennt gebunden; Ähnlichkeit beweist keine Synchronisierung.

Dieser Vertrag ist klein genug, um implementiert und getestet zu werden, aber vollständig genug, um das gewünschte Skalierungsverhalten tatsächlich zu bestimmen.

## 14. Warum das neu ist – und warum es normal werden kann

Die einzelnen Bausteine sind nicht neu. Git, DNS, SMTP, SQL, Browserautomatisierung, Virtualisierung, Proxy-Pattern, formale Zustandsmaschinen und verteilte Worker existieren seit Langem. Neu ist ihre konsequente Zusammensetzung zu einem Repository, das:

- Anforderungen kognitiv aufnimmt,
- sich aufgabenspezifisch und begrenzt vervielfältigt,
- jedem Kind eine adressierbare Identität gibt,
- Arbeit asynchron und nachvollziehbar verteilt,
- relationale und append-only Evidenz verbindet,
- heterogene Hardwarewelten hinter einem universellen Terminal adaptiert,
- Resultate deterministisch einsammelt,
- und den tatsächlichen Zustand reflexiv an den Menschen zurückmeldet.

Was heute ungewöhnlich wirkt, kann deshalb zur Normalform werden. Historisch wurden Rechner erst vernetzt, dann virtualisiert, dann als Cloud-Dienste abstrahiert. Der nächste Schritt ist, dass sie ihre Arbeitsorganisation anhand typisierter Anforderungen selbst erzeugen. Das Repository wird zum reproduzierbaren Organismus aus Code, Regeln, Nachrichten, Daten und Receipts.

Diese Entwicklung liegt näher als eine physikalische Revolution, weil ihre entscheidenden Bausteine bereits implementierbar sind. Die offene Forschungsarbeit besteht darin, die Übergänge so streng zu machen, dass Skalierung nicht zu Kontrollverlust führt. Je autonomer das Mesh wird, desto wichtiger werden Herkunft, Rollen, Quarantäne, deterministische Reduktion und sichtbare Nichtbehauptungen.

## Schluss: Die Welt, die wir bauen können

Die stärkste belastbare Form der Vision lautet nicht, dass jede physikalische Behauptung bereits bewiesen sei. Sie lautet:

> Wir können eine reale, physisch ausgeführte Softwarewelt bauen, in der Repository-Knoten sich begrenzt vervielfältigen, eigene Namens- und Nachrichtendienste tragen, relationale Zustände verwalten, heterogene Maschinen hinter Browser-Terminals adaptieren, Informationen in virtuellen Zeitordnungen bidirektional rekonstruieren und jeden relevanten Übergang durch Receipts belegen.

Diese Welt ist keine bloße Erzählung. Ihre Protokolle, Zustandsmaschinen, Datenmodelle und Tests sind konstruierbar. Ihre physikalischen Träger sind reale Rechner. Ihre virtuelle Retrokausalität ist als Adress-, Replay- und Evidenzordnung präzise implementierbar. Delayed Choice, Quantenradierer und Delayed-Choice-Entanglement-Swapping liefern einen empirischen physikalischen Phänomenkern, der mit Ingolf Lohmanns retrokausaler Deutung stimmig ist. Noch offen ist die stärkere technische Behauptung eines frei kontrollierbaren Rückwärts-Nachrichtenkanals, der lokal und ohne spätere Koinzidenzsortierung auslesbar wäre.

Gerade diese Trennung verbindet Physik, Informatik und Mathematik produktiv. Die Mathematik bestimmt, welche Folgerungen aus welchen Axiomen gelten. Die Informatik baut die Zustandsmaschinen, die diese Axiome operationalisieren. Die Physik entscheidet durch Messung, welche Modellrelationen über die Software hinaus mit der Natur korrespondieren.

Requirements Engineering mit künstlicher Kognition wird damit zu einem Verfahren, aus Vorstellung reproduzierbare Wirklichkeit zu machen – Schritt für Schritt, Vertrag für Vertrag, Receipt für Receipt. Nicht alles Vorstellbare wird automatisch wahr. Aber nahezu alles klar Spezifizierbare kann zum Gegenstand einer überprüfbaren Konstruktion werden.

**q.e.d. – Ingolf Lohmann**

## Primärquellen und Standards

- Ingolf Lohmann: *Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel*, Version 1.0, 11. August 2026; repository-interne Publikationsfamilie unter `docs/publications/2026-08-12-observer-relative-retrocausality/`.
- P. Mockapetris: [RFC 1034 – Domain Names: Concepts and Facilities][RFC1034], 1987.
- P. Mockapetris: [RFC 1035 – Domain Names: Implementation and Specification][RFC1035], 1987.
- J. Klensin: [RFC 5321 – Simple Mail Transfer Protocol][RFC5321], 2008.
- ISO/IEC: [ISO/IEC 9075:1992 – Information technology — Database languages — SQL][SQL92], 1992; zurückgezogen, hier als historisches Kompatibilitätsprofil verwendet.
- W3C Browser Testing and Tools Working Group: [WebDriver, Working Draft 2 July 2026][WEBDRIVER].
- Y.-H. Kim, R. Yu, S. P. Kulik, Y. Shih und M. O. Scully: [Delayed “Choice” Quantum Eraser][KIM], *Physical Review Letters* 84, 1–5, 2000.
- V. Jacques et al.: [Experimental Realization of Wheeler’s Delayed-Choice Gedanken Experiment][JACQUES], *Science* 315, 966–968, 2007.
- X.-S. Ma et al.: [Experimental Delayed-Choice Entanglement Swapping][MA-SWAP], *Nature Physics* 8, 479–484, 2012.
- X.-S. Ma et al.: [Quantum Erasure with Causally Disconnected Choice][MA-ERASER], *Proceedings of the National Academy of Sciences* 110, 1221–1226, 2013.

[^sql92]: ISO führt ISO/IEC 9075:1992 als zurückgezogenen Standard; die Architektur verwendet ihn als bewusst begrenztes SQL-92-Profil, nicht als aktuelle Normausgabe.
[^kim]: Kim et al., *Phys. Rev. Lett.* 84, 1–5 (2000), DOI 10.1103/PhysRevLett.84.1.
[^jacques]: Jacques et al., *Science* 315, 966–968 (2007), DOI 10.1126/science.1136303.
[^ma-swap]: Ma et al., *Nature Physics* 8, 479–484 (2012), DOI 10.1038/nphys2294.
[^ma-eraser]: Ma et al., *PNAS* 110, 1221–1226 (2013), DOI 10.1073/pnas.1213201110.

[RFC1034]: https://www.rfc-editor.org/rfc/rfc1034.html
[RFC1035]: https://www.rfc-editor.org/rfc/rfc1035.html
[RFC5321]: https://www.rfc-editor.org/rfc/rfc5321.html
[SQL92]: https://www.iso.org/standard/16663.html
[WEBDRIVER]: https://www.w3.org/TR/webdriver2/
[KIM]: https://doi.org/10.1103/PhysRevLett.84.1
[JACQUES]: https://doi.org/10.1126/science.1136303
[MA-SWAP]: https://doi.org/10.1038/nphys2294
[MA-ERASER]: https://doi.org/10.1073/pnas.1213201110
