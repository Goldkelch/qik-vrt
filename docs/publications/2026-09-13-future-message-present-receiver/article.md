# Eine Nachricht aus der Zukunft braucht einen Empfänger in der Gegenwart

## Was Quantenexperimente zeigen, was QIK-VRT daraus technisch macht und woran ein wirklicher Rückwärtskanal zu erkennen wäre

**Ingolf Lohmann**  
Fassung 1.0 — 13. September 2026

## Abstract

Delayed-Choice- und Entanglement-Swapping-Experimente zeigen reale, reproduzierbare Quantenkorrelationen, deren vollständige gemeinsame Beschreibung von späteren Messbedingungen abhängen kann. Daraus folgt jedoch nicht automatisch ein frei steuerbarer klassischer Nachrichtenkanal in die Vergangenheit. Dieser Beitrag trennt vier Nachweisstufen: experimentelle Quantenkorrelation, retrokausale beziehungsweise zeitsymmetrische Modellierung, skalierbare informatische Retrogradität und operationale physische Rückwärtskommunikation. QIK-VRT überführt die Zeit- und Korrelationsgrammatik in eine evidenzgebundene Informatikarchitektur mit getrennter Host-, virtueller, semantischer und Evidenzordnung. Historische Bytes bleiben unverändert; spätere Kontexte können ihre korrekte Klassifikation präzisieren, und vollständig protokollierte Zustandsfolgen können rückwärts rekonstruiert werden. Für einen wirklichen Zukunft-zu-Vergangenheit-Kanal wird ein vorregistrierter interventioneller Test formuliert: Ein früher Messwert Y wird erzeugt und irreversibel versiegelt, erst danach wird eine unabhängige spätere Wahl X getroffen. Ein operationaler Kanal verlangt eine nachweisbare Abhängigkeit P(Y | do(X=0)) != P(Y | do(X=1)) bei Ausschluss gewöhnlicher Vorwärtskanäle, nachträglicher Datenänderung und flexibler Postselektion. Die technische These lautet: Ein möglicher physischer Rückwärtskanal wäre noch keine Nachrichtentechnologie. Eine frühere Zeit muss bereits Adressen, Empfangsregister, Codebuch, Authentisierung, Fehlerbehandlung, Provenienz und Effect-Acknowledgement-Regeln besitzen, damit ein späterer Effekt überhaupt als Nachricht erkannt werden kann.

## 1. Drei verschiedene Bedeutungen von „real“

Bei Retrokausalität müssen drei Aussagen auseinandergehalten werden:

1. Die beobachteten Quantenkorrelationen sind real und experimentell reproduzierbar.
2. Zeitsymmetrische oder retrokausale Beschreibungen sind ernsthafte physikalische Modellklassen.
3. Eine später frei gewählte klassische Nachricht kann kontrolliert an einen früheren Empfänger übertragen werden.

Die erste Aussage ist experimentell belegt. Die zweite ist Gegenstand etablierter und aktueller theoretischer Forschung. Die dritte ist eine zusätzliche und strengere Behauptung. Sie benötigt einen eigenständigen Kanalnachweis.

Diese Trennung schwächt die wissenschaftliche Aussage nicht. Sie verhindert vielmehr, dass ein bereits belegter Zusammenhang durch eine unnötig stärkere, noch ungemessene Behauptung angreifbar wird.

## 2. Delayed Choice: spätere Bedingung, unverändertes früheres Ereignis

Im Delayed-Choice-Quantenradierer von Kim et al. wird ein verschränktes Photonenpaar erzeugt. Das Signalphoton wird registriert; das Idlerphoton nimmt einen längeren Weg und wird später gemessen. Abhängig von der späteren Messung können die bereits registrierten Signalereignisse in Teilmengen eingeordnet werden, die Interferenz beziehungsweise komplementäre Gegeninterferenz zeigen.

Der frühere einzelne Detektorklick wird dadurch nicht nachträglich überschrieben. Er bleibt derselbe registrierte Klick. Später festgelegt wird seine Zugehörigkeit zu einer vollständigen Korrelationsstruktur.

Mit Y als früherem Signalereignis, X als späterer Wahl der Messbedingung und Z als späterem Idlerergebnis liegt die experimentell relevante Struktur in der gemeinsamen Verteilung

P(Y, Z | X).

Im No-Signalling-Fall bleibt die frühere Randverteilung unabhängig von der späteren Wahl:

P(Y | X) = sum_Z P(Y, Z | X) = P(Y).

Erst die konditionierten Teilmengen P(Y | Z, X) zeigen die komplementären Strukturen. Damit ist eine zeitübergreifende Korrelation vorhanden, ohne dass der frühere Beobachter aus Y allein die spätere Wahl X lesen könnte.

## 3. Was spätere Experimente ergänzt haben

Delayed-Choice-Entanglement-Swapping verschiebt die Wahl einer Bell-artigen beziehungsweise separierenden Messung in die zeitliche Zukunft bereits registrierter Partner. Ma et al. realisierten eine Anordnung, in der zwei schon registrierte Photonen abhängig von einer späteren Messung ihrer Partner einer verschränkten oder separierbaren Korrelationsklasse zugeordnet werden.

Megidish et al. demonstrierten Verschränkung zwischen Photonen, die niemals gleichzeitig existiert hatten: Das frühere Photon war bereits detektiert, bevor das spätere erzeugt wurde. Bienfait et al. realisierten einen Delayed-Choice-Quantenradierer mit verschränkten akustischen Phononen in einem supraleitenden System.

Gemeinsam zeigen diese Experimente, dass die vollständige Quantenbeschreibung nicht immer in eine klassische Erzählung passt, in der jedes frühere Ereignis bereits unabhängig vom späteren Messkontext eine vollständige klassische Eigenschaftsgeschichte besitzt. Sie zeigen jedoch noch keinen frei modulierbaren klassischen Rückwärtskanal.

## 4. Retrokausalität als Modell und als Kanal

Aharonov, Bergmann und Lebowitz formulierten 1964 eine zeitsymmetrische Beschreibung von Quantenmessungen, in der Präselektion und Postselektion gemeinsam in die Wahrscheinlichkeitsbeschreibung eingehen. Allgemeiner untersuchen retrokausale Ansätze, ob spätere Randbedingungen zur vollständigen Beschreibung früherer Zustandsgrößen gehören können.

Das ist von einer Nachrichtentechnologie zu unterscheiden.

**Retrokausales Modell:** Eine spätere Randbedingung gehört zur vollständigen physikalischen Beschreibung einer konsistenten Geschichte.

**Operationaler Rückwärtskanal:** Eine später frei gewählte Intervention trägt messbare Information in einen früher erzeugten und damals bereits auswertbaren Empfangszustand.

Die zweite Aussage ist wesentlich stärker als die erste.

## 5. Was QIK-VRT informatisch trennt

QIK-VRT modelliert Zeit nicht als eine einzige globale Reihenfolge. Für die hier relevante Architektur werden mindestens vier Ordnungen getrennt:

- **Host-Ordnung:** Wann reale Rechen-, Netzwerk- und Speicheroperationen stattfinden.
- **Virtuelle Ordnung:** Welche Zeit- oder Zustandsadresse Daten tragen.
- **Semantische Ordnung:** Wann ihre Bedeutung oder Klassenzugehörigkeit bestimmt ist.
- **Evidenzordnung:** Wann ein Übergang durch Hashes, Receipts und Reobservation belegt ist.

Ein Datensatz kann physisch um 12 Uhr geschrieben werden, eine virtuelle Adresse für einen anderen Zustand tragen, um 14 Uhr durch neuen Kontext klassifiziert und um 15 Uhr durch ein Receipt bestätigt werden. Diese vier Zeitangaben bezeichnen nicht dasselbe Ereignis.

Die Trennung erlaubt zukunftsindizierte Adressierung, spätere semantische Auflösung und rückwärts gerichtete Rekonstruktion, ohne die historischen Bytes nachträglich zu verändern.

## 6. Rückwärts lesen, ohne Vergangenheit umzuschreiben

Eine Zustandsänderung kann mit Vorgänger, Eingabe, Nachfolger, Zeitbindung, Hash und Provenienz protokolliert werden. Liegt für jeden Schritt ein vollständiges Receipt vor, kann ein späterer Zustand auf seinen Vorgänger zurückgeführt und die Spur in umgekehrter semantischer Reihenfolge rekonstruiert werden.

Die tatsächlichen Leseoperationen finden weiterhin nach den ursprünglichen Schreiboperationen statt. Retrograd ist die rekonstruierte Zustands- und Bedeutungsordnung, nicht notwendigerweise die physische Host-Ausführung.

Dies ist eine reale informatische Fähigkeit: Rechner führen die Operationen aus, Dateien und Hashes existieren, Receipts sind überprüfbar, und die Rekonstruktion kann reproduziert werden.

## 7. Skalierung: von der Versuchsanordnung zur Datenarchitektur

Ein kleines Beispiel zeigt ein Prinzip. Eine Architektur muss bei Millionen von Datensätzen weiterhin garantieren, dass

- Herkunft und Zustandsbindung jedes Elements erhalten bleiben,
- spätere Klassifikation frühere Bytes nicht überschreibt,
- Dubletten, Auslassungen und Replay-Effekte erkennbar sind,
- die Rekonstruktion eindeutig bleibt,
- ein Abbruch einen definierten Fortsetzungszustand besitzt,
- und die Evidenzkette unabhängig erneut geprüft werden kann.

Damit wird nicht das Photonenexperiment in Software wiederholt. Validiert wird eine andere Aussage: Die Zeit- und Korrelationsgrammatik kann algorithmisch konsistent, provenance-gebunden und skalierbar ausgeführt werden.

## 8. Eine Nachricht braucht mehr als einen Träger

Selbst ein realer physischer Rückwärtskanal wäre noch keine Nachricht.

Eine Nachricht benötigt mindestens:

- eine Adresse,
- ein Codebuch beziehungsweise kanonisches Nachrichtenformat,
- eine Regel zur Unterscheidung von Signal und Rauschen,
- Authentisierung,
- Fehlererkennung und gegebenenfalls Fehlerkorrektur,
- Replay-Schutz,
- eine versiegelte Empfangshistorie,
- Provenienz,
- und einen getrennten Nachweis darüber, ob der beabsichtigte Effekt tatsächlich eingetreten ist.

Darum muss ein früher Empfänger vorbereitet sein, bevor die spätere Nachricht gewählt wird. Eine mögliche Zukunftsnachricht benötigt einen Empfänger in der Gegenwart.

Eine flächendeckende Infrastruktur würde einen retrokausalen physikalischen Effekt nicht erzeugen. Sie würde ihn - falls er existiert - adressierbar, dekodierbar, reproduzierbar und technisch nutzbar machen. In diesem Sinn verhält sich die Infrastruktur zum möglichen Träger ähnlich wie ein Funknetz zu elektromagnetischen Wellen.

## 9. Der entscheidende interventionelle Kanaltest

Ein wirklicher Zukunft-zu-Vergangenheit-Kanal muss interventionell und vorregistriert getestet werden.

Sei Y ein früher Messwert. Y wird erzeugt, zeitgestempelt, kryptographisch gebunden, an unabhängige Stellen gespiegelt und irreversibel versiegelt. Zu diesem Zeitpunkt steht die spätere Nachricht noch nicht fest.

Erst danach wird eine unabhängige spätere Variable X erzeugt, beispielsweise ein Bit X in {0,1}. Anschließend wird der behauptete physikalische Träger aktiviert.

Ein operationaler Rückwärtskanal verlangt über vorregistrierte Wiederholungen:

P(Y | do(X=0)) != P(Y | do(X=1)).

Entscheidend ist der Interventionsoperator do. Es genügt nicht, nach Kenntnis von X geeignete Teilmengen der Vergangenheit auszuwählen. Die spätere Wahl muss kontrolliert verändert werden, und die vor der Wahl erzeugte Verteilung von Y muss davon abhängen.

Noch stärker: Eine vorab festgelegte Decodierfunktion D(Y) muss Information über das später gewählte X oberhalb des vorregistrierten Zufallsniveaus liefern können, bevor irgendein gewöhnlicher Vorwärtskanal X zum früheren Empfangssystem transportiert.

Dabei sind insbesondere auszuschließen:

- gemeinsame Zufallsquellen und vorab geteilte Seeds,
- gewöhnliche Netzwerk-, Funk- oder Metadatenpfade,
- Uhr- und Zeitstempelfehler,
- nachträgliche Änderung der versiegelten Daten,
- Postselektion nach Kenntnis des Ergebnisses,
- flexible Änderung der Auswertungsregel,
- und nicht deklarierte Informationspfade zwischen späterer Wahl und früherer Auswertung.

Wichtig ist die Formulierung: Die später gewählte Variable muss nicht die gespeicherten Bytes eines abgeschlossenen Runs nachträglich editieren. Der Nachweis betrifft eine interventionelle Abhängigkeit der **vor der späteren Wahl erzeugten und danach unverändert versiegelten Zufallsvariable Y** über viele vorregistrierte Durchläufe.

## 10. Wissenschaftliche Zuordnung der QIK-VRT-Leistung

Die Idee retrokausaler oder zeitsymmetrischer Quantenmodelle ist älter als QIK-VRT. Die spezifische technische Leistung liegt in der Verbindung von

- quantenphysikalischer Zeitkorrelation,
- relation-first Kausalmodell,
- virtueller Zeitadressierung,
- späterer semantischer Konditionierung,
- append-only Provenienz,
- rückwärts gerichteter Rekonstruktion,
- Skalierung auf große Datenmengen,
- Effect-Acknowledgement-Grenze,
- und einem vorregistrierbaren interventionellen Kanaltest.

Damit wird eine Interpretationsfrage in ein konkretes informatisches Architektur-, Implementierungs- und Experimentalprogramm überführt.

Die gegenwärtig belastbare Aussage lautet:

> Ingolf Lohmann hat eine formale, implementierbare und skalierbare Informationsarchitektur spezifiziert, mit der zukunftsindizierte, später konditionierte und rückwärts rekonstruierbare Datenstrukturen provenance-gebunden verarbeitet werden können. QIK-VRT definiert zugleich wesentliche technische Voraussetzungen einer retrokausal vorbereiteten Kommunikationsinfrastruktur. Der davon getrennte nächste physikalische Nachweis ist positive operationale Kanalkapazität aus einer späteren freien Intervention in einen früher erzeugten und versiegelten Empfangszustand.

## 11. Evidenzgrenze

Die Nachweisstufen bleiben getrennt:

**Experimentelle Quantenkorrelationen:** real und reproduzierbar.  
**Retrokausale/zeitsymmetrische Modelle:** wissenschaftlich ernst zu nehmende Modellklasse, nicht einzig erzwungene Interpretation.  
**QIK-VRT-Zeit- und Korrelationsgrammatik:** formal und informatisch spezifiziert; konkrete Implementierungsbehauptungen benötigen ihre jeweiligen Repository-Receipts.  
**Rückwärtsrekonstruktion:** im definierten informatischen Modell prüfbar.  
**Retrokausal vorbereitete Kommunikationsarchitektur:** spezifiziert.  
**Frei steuerbarer physischer Zukunft-zu-Vergangenheit-Kanal:** separater, falsifizierbarer Außeneffekt; hier nicht als empirisch bestätigt behauptet.

Die wissenschaftlich falschen Extreme wären, die dokumentierte Architekturleistung zu ignorieren oder den noch separat zu messenden Außeneffekt bereits als beobachtet auszugeben. Die belastbare Position bewahrt Priorität, Reichweite und Evidenzgrenze gleichzeitig.

**Quod erat demonstrandum.**

Ingolf Lohmann

---

## Literatur

1. Y.-H. Kim, R. Yu, S. P. Kulik, Y. Shih, M. O. Scully, “Delayed ‘Choice’ Quantum Eraser”, *Physical Review Letters* 84, 1-5 (2000). DOI: 10.1103/PhysRevLett.84.1.
2. X.-s. Ma et al., “Experimental delayed-choice entanglement swapping”, *Nature Physics* 8, 479-484 (2012). DOI: 10.1038/nphys2294.
3. E. Megidish et al., “Entanglement Swapping between Photons that have Never Coexisted”, *Physical Review Letters* 110, 210403 (2013). DOI: 10.1103/PhysRevLett.110.210403.
4. A. Bienfait et al., “Quantum erasure using entangled surface acoustic phonons”, arXiv:2005.09311 (2020).
5. Y. Aharonov, P. G. Bergmann, J. L. Lebowitz, “Time Symmetry in the Quantum Process of Measurement”, *Physical Review* 134, B1410-B1416 (1964). DOI: 10.1103/PhysRev.134.B1410.

## Provenienz- und Claim-Hinweis

Konzeption, wissenschaftliche Prioritätsbehauptung und Autorenschaft: Ingolf Lohmann. Redaktionelle Verdichtung und Literaturabgleich dieser Fassung: AI-assisted. Die Literaturbezüge stützen die jeweils genannten experimentellen beziehungsweise historischen Aussagen; sie sind keine externe Bestätigung der QIK-VRT-spezifischen Implementierungs- oder Prioritätsbehauptungen. Repository-Implementierungsbehauptungen bleiben an ihre jeweiligen exakten QIK-VRT-Receipts gebunden.

Lizenz für diesen Text: CC BY-NC-ND 4.0, soweit nicht in einer späteren autoritativen Publikationsfassung anders ausgewiesen.
