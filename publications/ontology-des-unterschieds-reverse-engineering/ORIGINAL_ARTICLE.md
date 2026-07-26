# DIE ONTOLOGIE DES UNTERSCHIEDS ALS UNIVERSALER REVERSE-ENGINEERING-MECHANISMUS

**Von Ingolf Lohmann**

Die meisten Menschen verstehen unter Reverse Engineering das Zerlegen eines technischen Gegenstands.

Man nimmt ein Programm, ein Gerät, ein Protokoll oder ein Datenformat auseinander und versucht herauszufinden:

Wie funktioniert es?

Doch das ist nur die technische Oberfläche eines sehr viel allgemeineren Vorgangs.

Reverse Engineering bedeutet im Kern:

Aus beobachtbaren Wirkungen die dafür notwendigen Unterschiede, Zustände, Relationen und Übergänge zu rekonstruieren.

Genau dafür habe ich mit QIK-VRT und der Ontologie des Unterschieds einen allgemeinen Mechanismus gebaut.

Er ist nicht auf eine bestimmte Programmiersprache beschränkt.

Er ist nicht auf klassische Computer beschränkt.

Er ist nicht auf künstliche Kognition beschränkt.

Und er ist nicht einmal auf Informatik beschränkt.

Denn jedes Problem, das überhaupt erkannt, beschrieben, gemessen, berechnet oder wissenschaftlich untersucht werden kann, enthält notwendigerweise Unterschiede.

Ohne Unterschied gibt es nichts zu beobachten.

Ohne Beobachtung entsteht keine Information.

Ohne Information lässt sich kein Zustand bestimmen.

Ohne Zustandsunterschied gibt es keinen Übergang.

Ohne Übergang gibt es keine Wirkung.

Und ohne Wirkung gibt es keine Kausalität, die rekonstruiert werden könnte.

Die Grundkette lautet daher:

UNTERSCHIED
→ INFORMATION
→ ZUSTAND
→ RELATION
→ ÜBERGANG
→ WIRKUNG
→ EVIDENZ
→ REKONSTRUKTION

Das ist keine bloße Metapher.

Es ist eine ausführbare Architektur.

---

## 1. Was der Mechanismus tatsächlich leistet

Ein beliebiges informatisches System kann zunächst als Zustandsraum beschrieben werden.

Es besitzt:

* Eingaben,
* interne Zustände,
* Regeln,
* Übergänge,
* Ausgaben,
* Nebenwirkungen,
* Grenzen,
* Fehlerzustände,
* Beobachtungen
* und eine Historie.

Traditionelle Softwareanalyse betrachtet diese Bestandteile häufig getrennt.

QIK-VRT bringt sie in eine gemeinsame Wirkungsordnung.

Die zentrale Frage lautet nicht nur:

Was hat das System berechnet?

Sondern:

Welcher Unterschied wurde wirksam?

Wie kam dieser Unterschied zustande?

Welche Evidenz belegt ihn?

Welcher Zustand ging ihm voraus?

Welche Regel ermöglichte den Übergang?

Welche weiteren Wirkungen folgen daraus?

Darf diese Wirkung verantwortlich weitergegeben werden?

Damit wird ein System nicht bloß als Code betrachtet, sondern als kausaler Wirkraum.

Für einen technischen Vorgang ergibt sich beispielsweise:

EINGABE
→ INTERNE VERARBEITUNG
→ WIRKUNGSKANDIDAT
→ PRÜFUNG
→ FREIGABE / FORTSETZUNG / ISOLATION / BLOCKIERUNG
→ BEOBACHTETE FOLGE

Jede Stufe erzeugt oder erhält Evidenz.

Dadurch wird das System rückwärts lesbar.

Von einer beobachteten Folge kann man zurückgehen zu:

* der freigegebenen Wirkung,
* der Entscheidung,
* den geprüften Bedingungen,
* dem erzeugenden Zustand,
* den Eingaben,
* den verwendeten Regeln
* und den Grenzen der Rekonstruktion.

Das ist Reverse Engineering als allgemeine Kausalinversion.

---

## 2. Warum damit jedes informatische Problem bearbeitbar wird

Jedes informatische Problem ist zunächst ein Unterschied zwischen einem vorhandenen und einem gewünschten Zustand.

Ein Fehler bedeutet:

IST-ZUSTAND ≠ SOLL-ZUSTAND

Eine Sicherheitslücke bedeutet:

ERLAUBTER ÜBERGANG ≠ TATSÄCHLICH MÖGLICHER ÜBERGANG

Ein Datenverlust bedeutet:

ERWARTETE INFORMATION ≠ NOCH REKONSTRUIERBARE INFORMATION

Ein Synchronisationsfehler bedeutet:

ZUSTAND A ≠ ZUSTAND B

Ein KI-Fehler bedeutet:

ERZEUGTE WIRKUNG ≠ DURCH EVIDENZ GETRAGENE WIRKUNG

Ein unverständliches Altsystem bedeutet:

BEOBACHTBARES VERHALTEN
→ UNBEKANNTE INTERNE RELATIONEN

Sobald das Problem als wirksamer Unterschied ausgedrückt ist, kann es zerlegt werden in:

1. beteiligte Zustände,
2. beobachtbare Merkmale,
3. relevante Relationen,
4. mögliche Übergänge,
5. Erhaltungsbedingungen,
6. verlorene Information,
7. vorhandene Evidenz,
8. Rekonstruktionsgrenzen.

Damit wird das Problem nicht zwangsläufig sofort einfach.

Aber es wird formal greifbar.

Es lässt sich in Teilprobleme zerlegen.

Es lässt sich testen.

Es lässt sich versionieren.

Es lässt sich reproduzieren.

Und es lässt sich so lange rückwärts verfolgen, bis entweder die verursachende Struktur rekonstruiert oder die exakte Grenze der Rekonstruierbarkeit bewiesen ist.

Das ist ein wichtiger Unterschied:

Ein universaler Reverse-Engineering-Mechanismus muss nicht jedes Ergebnis erraten.

Er muss für jedes Problem angeben können:

REKONSTRUIERBAR
TEILWEISE REKONSTRUIERBAR
MEHRDEUTIG
EVIDENZ FEHLT
INFORMATION IRREVERSIBEL VERLOREN
WEITERE PRÜFUNG ERFORDERLICH

Gerade diese ehrliche Grenzbestimmung macht den Mechanismus wissenschaftlich und technisch belastbar.

---

## 3. Die mathematische Grundlage

Eine Beobachtung ist mathematisch eine Abbildung vom tatsächlichen Zustand auf einen beobachtbaren Wert.

Vereinfacht:

WIRKLICHER ZUSTAND
→ BEOBACHTUNG

Sind zwei verschiedene Zustände nach außen nicht unterscheidbar, bildet die Beobachtung beide auf denselben Wert ab.

Dann ist die Beobachtung nicht injektiv.

Eine vollständige historische Rückrechnung ist in diesem Fall nicht eindeutig möglich.

Aber daraus folgt nicht, dass keinerlei relevante Erkenntnis gewonnen werden kann.

Entscheidend ist:

Bleibt die gesuchte Bedeutung für alle Zustände gleich, die dieselbe Beobachtung erzeugen?

Ist das der Fall, kann die wirkungsrelevante Semantik trotz unvollständiger Beobachtung rekonstruiert werden.

Beispiel:

Zwei verschiedene interne Algorithmen erzeugen dasselbe freigegebene Ergebnis.

Die exakte historische Ausführung lässt sich möglicherweise nicht unterscheiden.

Aber die für die Außenwirkung entscheidende Aussage kann dennoch eindeutig sein.

Damit unterscheidet QIK-VRT:

EXAKTE HISTORISCHE REKONSTRUKTION

von:

REKONSTRUKTION DER WIRKUNGSRELEVANTEN SEMANTIK

Diese Differenz ist zentral.

Denn Wissenschaft und Technik benötigen häufig nicht jede mikroskopische Einzelheit der Vergangenheit.

Sie benötigen diejenige Information, die für Erklärung, Prüfung, Reproduktion und Verantwortung relevant ist.

---

## 4. Warum sich auch wissenschaftliche Probleme darauf zurückführen lassen

Jede Wissenschaft beginnt mit einer Unterscheidung.

Physik unterscheidet:

* Ort,
* Zeit,
* Energie,
* Impuls,
* Ladung,
* Feldzustände,
* Messergebnisse.

Chemie unterscheidet:

* Elemente,
* Bindungen,
* Konzentrationen,
* Reaktionszustände.

Biologie unterscheidet:

* lebend und nicht lebend,
* Organismus und Umgebung,
* genetische Zustände,
* Regulation,
* Reaktion,
* Reproduktion.

Medizin unterscheidet:

* gesund und krank,
* vorher und nachher,
* Ursache, Symptom und Folge,
* Behandlung und Wirkung.

Rechtswissenschaft unterscheidet:

* erlaubt und unerlaubt,
* Handlung und Unterlassung,
* Behauptung und Beleg,
* Verantwortung und Nichtverantwortung.

Auch Mathematik beginnt mit Unterscheidbarkeit:

* gleich und ungleich,
* Element und Menge,
* wahr und falsch,
* Struktur und Abbildung,
* Invarianz und Veränderung.

Die Ontologie des Unterschieds ersetzt diese Wissenschaften nicht.

Sie liefert die gemeinsame Grundgrammatik, auf der sie operieren.

Für jedes wissenschaftliche Problem kann gefragt werden:

Was wird unterschieden?
Wie wird es gemessen?
Welche Information entsteht daraus?
Welche Relationen bestehen?
Welche Übergänge sind möglich?
Was bleibt invariant?
Welche Wirkung wird beobachtet?
Welche Kausalstruktur erklärt sie?
Welche Evidenz trägt diese Erklärung?

Damit lässt sich ein Problem aus seinem disziplinären Spezialvokabular in eine gemeinsame relationale Struktur überführen.

Danach kann es wieder in die jeweilige Fachsprache zurückübersetzt werden.

Das schafft Anschlussfähigkeit zwischen Disziplinen.

---

## 5. Bedeutung für die Quantenphysik

Die Quantenphysik ist eine Physik der unterscheidbaren Möglichkeiten und der beobachtbaren Wirkungen.

Vor einer Messung beschreibt der Quantenzustand nicht einfach einen klassischen Gegenstand mit bereits vollständig bekannten Eigenschaften.

Er beschreibt eine Struktur möglicher Messergebnisse und ihrer Relationen.

Eine Messung erzeugt einen wirksamen Unterschied:

VORHER:
MENGE KOHÄRENTER MÖGLICHKEITEN
NACHHER:
UNTERSCHEIDBARES, REGISTRIERTES ERGEBNIS

Die Ontologie des Unterschieds erlaubt es, diesen Vorgang ohne unnötige mystische Zusatzannahmen zu ordnen:

* Ein Zustand definiert mögliche Unterschiede.
* Eine Wechselwirkung koppelt Systeme.
* Eine Messanordnung legt fest, welche Unterschiede überhaupt beobachtbar werden.
* Das Ergebnis ist ein stabilisierter, anschlussfähiger Unterschied.
* Dieser Unterschied wird als Information wirksam.
* Die Wirkung besitzt eine kausale und experimentelle Provenienz.

Damit wird das Messproblem nicht durch ein Wortspiel „gelöst“.

Aber seine Bestandteile werden sauber getrennt:

ZUSTAND
MÖGLICHKEITSSTRUKTUR
WECHSELWIRKUNG
BEOBACHTUNG
STABILISIERTER UNTERSCHIED
INFORMATION
FOLGEWIRKUNG

Die gleiche Struktur lässt sich auf Interferenz, Dekohärenz, Verschränkung und Quantenzustandsrekonstruktion anwenden.

Der entscheidende Punkt ist:

Quantenphysik handelt nicht von einer Welt ohne Unterschiede, sondern von den Bedingungen, unter denen Unterschiede möglich, noch nicht unterscheidbar, korreliert oder tatsächlich wirksam registriert sind.

---

## 6. Die Planck-Skala und das Wirkungsquantum

Auf der Planck-Skala treffen die fundamentalen Größen zusammen:

PLANCK-LÄNGE      ℓP
PLANCK-ZEIT       tP
PLANCK-ENERGIE    EP
PLANCK-IMPULS     pP
LICHTGESCHWINDIGKEIT c
WIRKUNGSQUANTUM   ℏ

Zwischen ihnen gelten:

\[
\frac{\ell_P}{t_P}=c
\]

\[
\frac{E_P}{p_P}=c
\]

\[
\ell_Pp_P=\hbar
\]

\[
t_PE_P=\hbar
\]

Damit verbindet c die Verhältnisstruktur:

RAUM / ZEIT
=
ENERGIE / IMPULS

Und ℏ verbindet die Wirkungsstruktur:

RAUM × IMPULS
=
ZEIT × ENERGIE
=
WIRKUNG

Die Planck-Skala ist damit der natürliche gemeinsame Maßstab von:

* Raum,
* Zeit,
* Energie,
* Impuls
* und Wirkung.

In der von mir entwickelten Lesart ist die elementare Raumzeiteinheit durch Planck-Länge und Planck-Zeit bestimmt, und ihre elementare Übertragungskapazität entspricht einem Wirkungsquantum.

Das bedeutet:

Pro elementarer Raumzeiteinheit kann genau ein elementarer Wirkungsunterschied übertragen werden.

Makroskopische Raumzeit, Felder, Materie und Information sind danach nicht voneinander getrennte Grundsubstanzen.

Sie sind zusammengesetzte Ordnungen elementarer Wirkung.

---

## 7. Bedeutung für das Quantencomputing

Ein klassischer Computer verarbeitet stabile, klassisch unterscheidbare Zustände:

0 oder 1

Ein Quantencomputer verarbeitet dagegen kohärente Relationen zwischen möglichen Messergebnissen.

Ein Qubit ist nicht einfach „gleichzeitig 0 und 1“.

Es ist ein Zustand, dessen mögliche Unterschiede und Phasenrelationen kontrolliert entwickelt werden, bevor eine Messung daraus ein klassisch unterscheidbares Ergebnis erzeugt.

Die eigentliche Ressource des Quantencomputings ist daher nicht bloß Parallelität.

Sie besteht in:

* Superposition,
* Phase,
* Interferenz,
* Verschränkung,
* kontrollierter Unterscheidbarkeit,
* gezielter Verstärkung gewünschter Messergebnisse.

In der Ontologie des Unterschieds lässt sich ein Quantenalgorithmus so lesen:

AUSGANGSUNTERSCHIED
→ KOHÄRENTE MÖGLICHKEITSSTRUKTUR
→ KONTROLLIERTE RELATIONEN
→ INTERFERENZ
→ VERSTÄRKUNG RELEVANTER UNTERSCHIEDE
→ MESSUNG
→ KLASSISCH ANSCHLUSSFÄHIGE INFORMATION

Das hat erhebliche Konsequenzen für die Entwicklung von Quantencomputern.

### Erstens: Quantenprogramme werden als Wirkungsgraphen beschreibbar

Nicht nur Gates und Qubits sind relevant, sondern:

* welcher Unterschied vorbereitet wird,
* welche Relation erzeugt wird,
* welche Phase verändert wird,
* welche Information erhalten bleiben muss,
* welche Messung welchen Unterschied materialisiert.

### Zweitens: Fehlerkorrektur wird als Erhaltung relevanter Unterschiede verständlich

Ein Quantenfehler ist ein unerwünschter Unterschied im Zustand oder in seiner Phase.

Quantenfehlerkorrektur erhält nicht einfach „das Qubit“.

Sie schützt eine logisch relevante Relationsstruktur gegen physikalische Störungen.

### Drittens: Quantensoftware benötigt eine Wirkungskontrolle

Ein Quantenrechner kann ein Ergebnis erzeugen.

Aber das bedeutet noch nicht:

* dass die Schaltung korrekt war,
* dass die Kalibrierung gültig war,
* dass das Messergebnis reproduzierbar ist,
* dass die Übersetzung in eine klassische Entscheidung verantwortbar ist.

Hier greift QIK-VRT:

QUANTENERGEBNIS
→ PROVENIENZ
→ KALIBRIERUNGSSTATUS
→ FEHLERMODELL
→ REPRODUZIERBARKEIT
→ WIRKUNGSBEWERTUNG
→ EFFECT_ACK

Damit liefert die Ontologie des Unterschieds nicht nur eine Interpretation des Quantencomputings.

Sie liefert eine mögliche Governance-, Prüf- und Runtime-Schicht für reale Quantencomputer und hybride Quanten-Klassik-Systeme.

---

## 8. Bedeutung für künstliche Kognition

Ein künstlich kognitives System verarbeitet Unterschiede.

Es erkennt Muster.

Es ordnet Informationen.

Es verändert interne Zustände.

Es erzeugt Antworten.

Und diese Antworten können in der Welt wirken.

Die entscheidende Schwäche heutiger Systeme liegt darin, dass die Erzeugung einer Ausgabe häufig von der verantwortlichen Freigabe ihrer Wirkung getrennt ist.

Ein System kann sprachlich überzeugend antworten, obwohl:

* die Evidenz fehlt,
* der Kontext unvollständig ist,
* die Quelle falsch zugeordnet wurde,
* der Schluss nicht trägt,
* eine Handlung nicht autorisiert ist.

QIK-VRT trennt daher:

OUTPUT ERZEUGT

von:

WIRKUNG VERANTWORTBAR FREIGEGEBEN

Das Repository bezeichnet dies als Unterschied zwischen Transportbestätigung und Wirkungsbestätigung:

TRANSPORT_ACK ≠ EFFECT_ACK

Eine Information kann technisch erfolgreich:

* übertragen,
* berechnet,
* gespeichert
* oder veröffentlicht

worden sein, ohne deshalb wahr, sicher oder verantwortbar zu sein.

Für künstliche Kognition bedeutet das:

Intelligenz besteht nicht nur darin, Unterschiede zu erzeugen oder zu klassifizieren.

Verantwortbare Kognition besteht darin, ihre Herkunft, Bedeutung, Unsicherheit und mögliche Wirkung anschlussfähig zu prüfen.

---

## 9. Warum dies eine universelle Architektur ist

Die Universalität liegt nicht darin, dass jedes Fachproblem durch dieselben wenigen Wörter vollständig gelöst wird.

Sie liegt darin, dass sich jede wirksame Problemlösung auf dieselben strukturellen Fragen zurückführen lässt:

WAS IST DER UNTERSCHIED?
WELCHE INFORMATION TRÄGT ER?
WELCHER ZUSTAND WIRD VERÄNDERT?
WELCHE RELATION VERURSACHT DEN ÜBERGANG?
WELCHE WIRKUNG FOLGT?
WELCHE EVIDENZ BELEGT SIE?
WELCHE GRENZEN HAT DIE REKONSTRUKTION?
DARF DIE WIRKUNG WEITERWIRKEN?

Der interne Rechenweg kann beliebig sein:

* klassischer Algorithmus,
* neuronales Netz,
* symbolische Logik,
* numerische Simulation,
* Quantenalgorithmus,
* menschliche Entscheidung,
* wissenschaftliches Experiment.

QIK-VRT setzt an dem Punkt an, an dem daraus ein Wirkungskandidat entsteht.

BELIEBIGER RECHENWEG
→ WIRKUNGSKANDIDAT
→ PRÜFUNG
→ FREIGABE / FORTSETZUNG / ISOLATION / BLOCKIERUNG

Das Repository beschreibt dies zutreffend nicht als universelle Programmiersprache und nicht als automatischen Wahrheitsfinder, sondern als universalisierbare Verfassungsschicht der Wirkung.

---

## 10. Was damit gebaut wurde

Ich habe nicht einfach eine weitere Softwarebibliothek gebaut.

Ich habe eine Verbindung hergestellt zwischen:

* Ontologie,
* Informatik,
* Reverse Engineering,
* Kausalität,
* Evidenz,
* Audit,
* Wissenschaft,
* künstlicher Kognition,
* Quantenphysik,
* Quantencomputing
* und Verantwortung.

Die gemeinsame operative Einheit ist der wirksame Unterschied.

Der Mechanismus lautet:

UNTERSCHIED ERKENNEN
→ INFORMATION ORDNEN
→ RELATIONEN BESTIMMEN
→ ÜBERGÄNGE REKONSTRUIEREN
→ WIRKUNG PRÜFEN
→ EVIDENZ PERSISTIEREN
→ VERANTWORTUNG ZUORDNEN
→ WIRKUNG FREIGEBEN ODER BLOCKIEREN

Damit kann jedes informatische Problem in einen prüfbaren Wirkungsraum überführt werden.

Und jedes wissenschaftliche Problem kann auf seine elementaren Unterschiede, Relationen, Übergänge und Erhaltungsbedingungen zurückgeführt werden.

Nicht weil alle Probleme gleich wären.

Sondern weil kein Problem überhaupt als Problem erscheinen könnte, wenn es keinen Unterschied gäbe.

---

## Schlusssatz

Die Ontologie des Unterschieds behauptet nicht, dass alle Dinge dasselbe sind.

Sie zeigt das Gegenteil:

Alles Erkennbare beginnt damit, dass etwas nicht dasselbe ist.

Aus Unterschied entsteht Information.

Aus Information entsteht gerichtete Wirkung.

Aus Wirkung entsteht Kausalität.

Aus Kausalität wird Rekonstruktion möglich.

Aus Rekonstruktion entsteht Verständnis.

Und erst aus geprüftem Verständnis kann verantwortbare Freigabe entstehen.

UNTERSCHIED
→ INFORMATION
→ KAUSALITÄT
→ EVIDENZ
→ VERANTWORTUNG
→ WIRKUNG

Das ist die gemeinsame Grammatik von Informatik und Wissenschaft.

Das ist der Reverse-Engineering-Mechanismus.

Das ist QIK-VRT.

q.e.d.
Ingolf Lohmann
