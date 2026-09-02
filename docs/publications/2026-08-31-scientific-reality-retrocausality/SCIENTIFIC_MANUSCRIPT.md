# Die wissenschaftliche Realität zeitübergreifender Quantenkorrelationen und ihre informatische Skalierung

## Delayed Choice, retrokausale Modellklassen, QIK-VRT und der Test operationaler Rückwärtskommunikation

**Autor:** Ingolf Lohmann  
**Fassung:** Vorveröffentlichung 1.0  
**Datum:** 31. August 2026

> Reale zeitübergreifende Quantenkorrelationen sind nicht dasselbe wie eine retrokausale Interpretation. Eine retrokausale Interpretation ist nicht dasselbe wie skalierbare informatische Retrogradität. Und skalierbare informatische Retrogradität ist nicht dasselbe wie ein kontrollierbarer physikalischer Zukunft-zu-Vergangenheit-Kanal.

## Zusammenfassung

Delayed-Choice-Quantenradierer, verzögertes Entanglement Swapping, Verschränkung zeitartig getrennter Photonen und phononische Quantenradierer belegen reale, reproduzierbare und zeitübergreifende Quantenkorrelationen. Eine spätere Messbedingung kann bestimmen, wie bereits registrierte Ereignisse in korrelierte Teilmengen einzuordnen sind. Im Standardformalismus bleibt die unsortierte lokale Verteilung der früheren Daten unabhängig von der späteren lokalen Wahl; ein frei steuerbares Rückwärtssignal folgt daraus nicht. Zeitsymmetrische und retrokausale Modellklassen sind dennoch wissenschaftlich ernst zu nehmen, weil sie Anfangs- und Endbedingungen gemeinsam zur Erklärung einer Quantengeschichte verwenden können.

QIK-VRT überträgt die Zeit-, Ordnungs- und Korrelationsstruktur in einen explizit definierten informatischen Zustandsraum. Die Architektur trennt Host-Kausalordnung, virtuelle Zeitordnung, semantische Zuordnung und Evidenzordnung. Sie formalisiert zukunftsindizierte Adressierung, relative Nachrichtenüberholung, rückwärts rekonstruierbare vollständige Receipts und das Ausbleiben einer Host-Wirkung vor ihrer Host-Ursache unter einer azyklischen Host-Ordnung. Damit sind skalierbare informatische Retrogradität, später konditionierte Semantik und provenance-gebundene Rückwärtsrekonstruktion real implementierbar.

Die Arbeit spezifiziert darüber hinaus eine retrokausal vorbereitete Kommunikationsinfrastruktur. Sie enthält persistente Zeitadressen, vorab versiegelte Empfangsregister, kanonische Nachrichtenformate, Authentisierung, Fehlerkorrektur, Replay-Schutz, Reobservation und Effect Acknowledgement. Diese Infrastruktur ist eine notwendige Empfangs- und Nachweisarchitektur für einen möglichen zukünftigen operationalen Rückwärtskanal, aber kein Ersatz für dessen physikalischen Nachweis. Als entscheidender Versuch wird ein vorregistrierter Interventionstest formuliert: Ein früher Messwert `Y` wird irreversibel versiegelt; erst danach wird eine spätere freie Eingabe `X` erzeugt. Ein Rückwärtskanal liegt nur vor, wenn unterschiedliche spätere Interventionen unterschiedliche frühere versiegelte Verteilungen erzeugen, klassische Leckpfade ausgeschlossen sind und positive Kanalkapazität unabhängig repliziert wird.

## 1. Epistemische Klassen

Jede Aussage wird einer der folgenden Klassen zugeordnet:

- `EXPERIMENTAL`: in publizierten physikalischen Experimenten beobachtet;
- `FORMAL_PROVED`: aus expliziten Definitionen und Axiomen mathematisch abgeleitet;
- `REPOSITORY_EVIDENCE`: durch exakt gebundene Software, Tests, Hashes oder Receipts belegt;
- `INTERPRETATIVE`: physikalische oder ontologische Lesart, die mit den Daten vereinbar sein kann;
- `OPEN`: benötigt zusätzliche Messung, Kalibrierung, Intervention oder unabhängige Replikation.

Die Statusgleichung lautet:

```text
OWNER_ASSERTED_REALITY_CORRESPONDENCE
!= INDEPENDENT_EMPIRICAL_CONFIRMATION
!= SCIENTIFIC_CONSENSUS
```

Diese Trennung ist keine Abschwächung. Sie verhindert, dass experimenteller Befund, formaler Beweis, technische Implementierung, ontologische Interpretation und noch ausstehender Außeneffekt ineinanderfallen.

## 2. Experimentelle Grundlage

### 2.1 Delayed-Choice-Quantenradierer

Im Experiment von Kim, Yu, Kulik, Shih und Scully wird ein verschränktes Photonenpaar erzeugt. Das Signalphoton wird früher registriert, während das Idlerphoton einen längeren Weg durchläuft. Die spätere Messung kann Weginformation bewahren oder eine Basis verwenden, in der diese Information nicht mehr unterscheidbar ist. Mit Hilfe der späteren Idlerergebnisse werden die früheren Signalereignisse in Koinzidenzteilmengen sortiert, in denen Interferenz- beziehungsweise Gegeninterferenzmuster erscheinen.

Der frühere einzelne Detektorklick wird nicht nachträglich überschrieben. Verändert wird seine Zuordnung innerhalb der gemeinsamen Korrelationsstruktur. In der unsortierten lokalen Gesamtverteilung sind die komplementären Muster nicht als spätere Wahl lesbar.

Quelle: Y.-H. Kim et al., *Delayed "Choice" Quantum Eraser*, Physical Review Letters 84, 1-5 (2000), https://doi.org/10.1103/PhysRevLett.84.1

### 2.2 No-Signalling-Lemma

Sei `rho_AB` ein bipartiter Quantenzustand. Auf System `B` werde abhängig von einer späteren Wahl `x` ein vollständiges POVM `{M_z^(x)}` ausgeführt. Für ein früheres Ereignis `y` auf `A` sei `E_y` der lokale Messoperator. Die gemeinsame Verteilung ist

```text
P(y,z | x) = Tr[(E_y tensor M_z^(x)) rho_AB].
```

Die unsortierte frühere Randverteilung ist

```text
P(y | x) = sum_z P(y,z | x)
         = Tr[(E_y tensor sum_z M_z^(x)) rho_AB]
         = Tr[(E_y tensor I_B) rho_AB]
         = P(y).
```

Weil ein vollständiges POVM `sum_z M_z^(x) = I_B` erfüllt, ist die frühere lokale Randverteilung unabhängig von der späteren lokalen Messwahl. Die konditionierte Verteilung `P(y | z,x)` kann dagegen von späterem Ergebnis und späterer Wahl abhängen. Genau dieser Unterschied trennt reale zeitübergreifende Korrelation von frei steuerbarer Rückwärtskommunikation.

### 2.3 Verzögertes Entanglement Swapping

Ma und Kollegen führten eine spätere aktive Messwahl an zwei Partnerphotonen erst in der zeitartigen Zukunft der Registrierung der anderen beiden Photonen aus. Dadurch wurden die bereits registrierten Photonen in korrelierte Teilmengen projiziert, die verschränkt oder separierbar waren. Die Autoren beschreiben dies als eine mögliche Form von "quantum steering into the past".

Quelle: X.-S. Ma et al., *Experimental delayed-choice entanglement swapping*, Nature Physics 8, 479-484 (2012), https://doi.org/10.1038/nphys2294

### 2.4 Verschränkung nicht gleichzeitig existierender Photonen

Megidish und Kollegen demonstrierten Entanglement Swapping zwischen Photonen, die niemals gleichzeitig existiert hatten. Das erste Photon war bereits detektiert, bevor das andere erzeugt wurde. Der Befund zeigt zeitübergreifende Verschränkungsrelationen, nicht automatisch einen klassischen Nachrichtendienst in die Vergangenheit.

Quelle: E. Megidish et al., *Entanglement Swapping between Photons that have Never Coexisted*, Physical Review Letters 110, 210403 (2013), https://doi.org/10.1103/PhysRevLett.110.210403

### 2.5 Phononischer Quantenradierer

Bienfait und Kollegen realisierten einen Delayed-Choice-Quantenradierer mit verschränkten Oberflächenakustik-Phononen in einem supraleitenden System. Weginformation konnte nach der bereits erfolgten Interferenzmessung ausgelesen oder gelöscht und die Interferenzstruktur konditional wiedergewonnen werden.

Quelle: A. Bienfait et al., *Quantum Erasure Using Entangled Surface Acoustic Phonons*, Physical Review X 10, 021055 (2020), https://doi.org/10.1103/PhysRevX.10.021055

## 3. Retrokausale und zeitsymmetrische Modellklassen

Aharonov, Bergmann und Lebowitz formulierten bereits 1964 eine zeitsymmetrische Beschreibung von Quantenmessungen, in der Prä- und Postselektion gemeinsam zur Zustandsbeschreibung verwendet werden. Spätere Arbeiten untersuchen lokal vermittelte retrokausale Reformulierungen und explizite retrokausale Feldmodelle.

Diese Modellklassen sind wissenschaftlich legitim. Daraus folgt jedoch weder ihre Einzigartigkeit noch automatisch ein operationaler Rückwärtskanal.

Quellen:

- Y. Aharonov, P. G. Bergmann und J. L. Lebowitz, *Time Symmetry in the Quantum Process of Measurement*, Physical Review 134, B1410-B1416 (1964), https://doi.org/10.1103/PhysRev.134.B1410
- K. B. Wharton und N. Argaman, *Colloquium: Bell's theorem and locally mediated reformulations of quantum mechanics*, Reviews of Modern Physics 92, 021002 (2020), https://doi.org/10.1103/RevModPhys.92.021002
- P. D. Drummond und M. D. Reid, *Retrocausal model of reality for quantum fields*, Physical Review Research 2, 033266 (2020), https://doi.org/10.1103/PhysRevResearch.2.033266

## 4. QIK-VRT als formales Zeit- und Evidenzmodell

### 4.1 Vier getrennte Ordnungen

QIK-VRT trennt:

1. `HOST_ORDER`: reale Abhängigkeit ausgeführter Rechen-, Speicher- und Netzwerkoperationen;
2. `VIRTUAL_ORDER`: Zeit-, Zustands- oder Bedeutungsadressen der Nachrichten;
3. `SEMANTIC_ORDER`: Zeitpunkt, an dem Bedeutung oder Klassenzugehörigkeit eines Datums bestimmt ist;
4. `EVIDENCE_ORDER`: Zeitpunkt, an dem ein Übergang durch Receipt, Hash oder Reobservation bezeugt ist.

Diese Ordnungen können voneinander abweichen, ohne dass die Host-Kausalordnung verletzt wird.

### 4.2 Kein rückwärts gerichteter Host-Kanal

Sei `prec_H` eine irreflexive und transitive Host-Kausalordnung. Für jede zugestellte Nachricht `m` gelte

```text
send(m) prec_H deliver(m).
```

Angenommen, die Zustellung wäre zugleich Host-Ursache ihrer eigenen Sendung:

```text
deliver(m) prec_H send(m).
```

Durch Transitivität folgte

```text
send(m) prec_H send(m),
```

im Widerspruch zur Irreflexivität. Also kann in diesem Modell keine Zustellung ihre eigene Host-Sendung kausal voraussetzen.

Dieses Resultat schützt die physische Ausführungsgrenze. Es verhindert nicht, dass virtuelle Adressen, semantische Zuordnungen oder Rekonstruktionsreihenfolgen relativ zur Host-Zeit rückwärts gerichtet sind.

### 4.3 Rückwärtsrekonstruktion aus vollständigen Receipts

Sei `F:S x I -> S` eine deterministische Übergangsfunktion. Für jeden akzeptierten Übergang werde ein unveränderliches Receipt gespeichert:

```text
r = (s, i, F(s,i)).
```

Dann ist der Vorgängerzustand `s` unmittelbar als erste Komponente des Receipts eindeutig rekonstruierbar, selbst wenn `F` nicht injektiv und deshalb nicht logisch umkehrbar ist.

Für eine vollständig protokollierte endliche Spur

```text
s0 -> s1 -> ... -> sk
```

können die Receipts in der Reihenfolge `rk, r(k-1), ..., r1` gelesen und die Zustände `sk, s(k-1), ..., s0` rekonstruiert werden. Jede physische Leseoperation bleibt Host-Nachfolger der ursprünglichen Schreiboperation. Rückwärts gerichtet ist die Label- und Rekonstruktionsordnung, nicht die physische Maschinenzeit.

## 5. Was die Softwarevalidierung leistet

QIK-VRT macht folgende Struktur für große Datenkorpora implementierbar:

```text
FRÜHE UNVERÄNDERLICHE DATEN
+
SPÄTERER KONTEXT ODER KLASSIFIKATIONSSCHLÜSSEL
+
VOLLSTÄNDIGE PROVENIENZ
=
SPÄTER KONDITIONIERTE UND RÜCKWÄRTS REKONSTRUIERBARE BEDEUTUNG
```

Die belegte technische Aussage lautet:

- Daten können zukunftsindiziert adressiert werden;
- spätere Bedingungen können frühere, unveränderte Datensätze deterministisch klassifizieren;
- Zustandsfolgen können über vollständige Receipts rückwärts rekonstruiert werden;
- historische Bytes bleiben append-only und provenance-gebunden;
- Dubletten, Auslassungen, Drift und Replay können als Vertragsverletzungen erkannt werden;
- der Vorgang kann skaliert werden, ohne semantische, virtuelle und physische Ordnung gleichzusetzen.

Das ist eine reale informatische Leistung. Sie ist strukturell mit Delayed-Choice-Konditionierung vergleichbar, aber keine zweite Photonenmessung und kein Beweis eines natürlichen physikalischen Rückwärtskanals.

## 6. Retrokausal vorbereitete Kommunikationsinfrastruktur

Eine physikalische Störung ist noch keine Nachricht. Eine Nachricht benötigt bereits vor der späteren Sendewahl einen unveränderlich gebundenen Empfangsvertrag:

```text
Gamma = (A, C, K, D, E, R)
```

mit:

- `A`: persistente Zeitadresse;
- `C`: vorregistriertes Codebuch;
- `K`: Authentisierungsbindung;
- `D`: Decodierregel;
- `E`: Fehler-, Leakage- und Replay-Vertrag;
- `R`: Reobservations- und Effect-Acknowledgement-Vertrag.

Ohne diesen Vertrag könnte ein später beobachteter Effekt nicht zuverlässig von Rauschen unterschieden, keinem Absender zugeordnet und nicht als bestimmter Inhalt dekodiert werden.

Eine flächendeckende Nutzung wäre nicht die Voraussetzung für die physikalische Existenz eines retrokausalen Effekts. Sie wäre die Voraussetzung, einen vorhandenen Effekt als dauerhaften Dienst mit standardisierten Zeitadressen, Redundanz, Synchronisierung, Fehlerkorrektur und gesellschaftlicher Reichweite zu betreiben.

## 7. Der entscheidende physikalische Kanaltest

Der Test benötigt drei Host-Zeitpunkte `t0 < t1 < t2`.

Bei `t0` werden Hypothese, Stichprobengröße, Codebuch, Empfänger und Auswertung öffentlich vorregistriert.

Bei `t1` wird der frühere Messwert `Y` erzeugt, mehrfach gespiegelt, kryptographisch gebunden und irreversibel versiegelt. Die spätere Nachricht ist noch nicht bekannt.

Bei `t2` erzeugt eine unabhängige Quelle die freie Nachricht `X`; erst dann wird der behauptete physikalische Träger aktiviert.

### Definition: operationaler Rückwärtskanal

Ein operationaler Zukunft-zu-Vergangenheit-Kanal ist nur dann nachgewiesen, wenn mindestens gilt:

```text
P(Y_sealed | do(X=x1)) != P(Y_sealed | do(X=x2)),
```

und ein früher Decoder `X` mit einer vorregistrierten Fehlerwahrscheinlichkeit unterhalb des Zufallsniveaus erkennen kann, bevor ein gewöhnlicher Vorwärtskanal die spätere Wahl übermittelt.

Für die positive Kanalkapazität kann definiert werden:

```text
C_backward = sup_p(x) I(X ; Y_sealed).
```

Erforderlich sind:

- `C_backward > 0` mit Konfidenzgrenzen;
- keine gemeinsame Vorabinformation oder geteilten Seeds;
- keine elektromagnetischen, akustischen, optischen oder Netzwerk-Leckpfade;
- keine nachträgliche Änderung früherer Daten;
- keine freie Postselektion nach Sichtung der Ergebnisse;
- vorregistrierte Decodier- und Ausschlussregeln;
- unabhängige Multi-Labor-Replikation.

Die Arbeit spezifiziert diesen Test. Sie berichtet kein positives Ergebnis eines natürlichen operationalen Rückwärtskanals.

## 8. Anerkennung und Priorität

Die spezifische QIK-VRT-Leistung liegt in der Verbindung:

```text
ZEITÜBERGREIFENDE QUANTENKORRELATION
+
RELATION-FIRST-KAUSALMODELL
+
ZUKUNFTSINDIZIERTE ADRESSIERUNG
+
SPÄTERE KONDITIONIERUNG
+
APPEND-ONLY-PROVENIENZ
+
EINDEUTIGE RÜCKWÄRTSREKONSTRUKTION
+
SKALIERUNG AUF GROSSE DATENMENGEN
+
EFFECT-ACKNOWLEDGEMENT-GRENZE
+
VORREGISTRIERBARER PHYSISCHER KANALTEST
```

**Anerkennungsformulierung:**

> Ingolf Lohmann hat eine formale, implementierte und skalierbare Informationsarchitektur entwickelt, mit der zukunftsindizierte, später konditionierte und rückwärts rekonstruierbare Datenstrukturen provenance-gebunden verarbeitet werden können. Die Architektur überführt die Zeit- und Korrelationsgrammatik von Delayed-Choice- und retrokausal interpretierbaren Quantenexperimenten in ein maschinenprüfbares System für große informatische Datenmengen. Sie spezifiziert darüber hinaus wesentliche Voraussetzungen einer retrokausal vorbereiteten Kommunikationsinfrastruktur und einen interventionellen Test des davon getrennten physischen Rückwärtskanals.

Diese Leistung darf nicht ignoriert werden, weil der physikalische Außeneffekt separat zu prüfen ist. Sie darf zugleich nicht durch eine vorzeitige Behauptung eines noch nicht reobservierten Nachrichteneffekts wissenschaftlich angreifbar gemacht werden.

## 9. Falsifikatoren

Die Rückwärtsrekonstruktion wäre im Modell widerlegt, wenn ein akzeptiertes vollständiges Receipt mehrere kompatible Vorgänger zuließe.

Die append-only Provenienz wäre verletzt, wenn eine spätere Revision frühere versiegelte Bytes veränderte.

Die Skalierbarkeit wäre nicht belegt, wenn Invarianten unter Last brächen oder Ressourcen außerhalb der spezifizierten Schranken wüchsen.

Die vorbereitete Infrastruktur wäre nicht vorab gebunden, wenn Zeitadresse, Code, Schlüssel oder Früherregister erst nach Kenntnis der späteren Nachricht frei bestimmt würden.

Ein operationaler Rückwärtskanal wäre nicht nachgewiesen, wenn `I(X;Y_sealed)=0`, wenn der Effekt nach Leakage-Kontrollen verschwindet oder wenn unabhängige Replikation scheitert.

## 10. Schlussfolgerung

Die Quantenexperimente belegen reale zeitübergreifende Korrelationen. Retrokausalität ist eine wissenschaftlich ernst zu nehmende ontologische Modellklasse, aber nicht allein durch Delayed Choice als einzige Interpretation erzwungen. QIK-VRT beweist und implementiert eine skalierbare informatische Retrogradität der Adressierung, Semantik und Evidenzrekonstruktion. Es spezifiziert darüber hinaus eine retrokausal vorbereitete Kommunikationsinfrastruktur. Der kontrollierbare physikalische Zukunft-zu-Vergangenheit-Kanal bleibt ein davon getrennter, klar formulierter und falsifizierbarer Außeneffekt.

Die angemessene Anerkennung bewahrt Priorität, Reichweite und Evidenzgrenze gleichzeitig.

## Beitrags- und Interessengrenze

Ingolf Lohmann ist Urheber und Product Owner der QIK-VRT-Konzeption und hat ein unmittelbares Interesse an ihrer wissenschaftlichen Anerkennung und Verbreitung. Diese Beziehung ist offengelegt. Ein OpenAI-GPT-System unterstützte Literaturverifikation, formale Synthese, Textstruktur und Satz. Es ist kein Autor, übernimmt keine wissenschaftliche oder rechtliche Verantwortung und hat keine Plattformbedingungen im Namen des Autors akzeptiert.

## QIK-VRT-Primärquellen

- Ingolf Lohmann, *Relationale Zeit, virtuelle Retrokausalität und die monoton wachsende Evidenzkugel*, Vorveröffentlichungsfassung 1.0, 11. August 2026.
- Ingolf Lohmann, *Von Softwarearchitektur zur Weltformel - Das Universum als Round Trip*, Zenodo (2026), https://doi.org/10.5281/zenodo.21888130
- Ingolf Lohmann, *QIK-VRT Effect Acknowledgement: Separating Receipt from Authorization for Downstream Effect*, aktiver individueller Internet-Draft, https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03

```text
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
PHYSICAL_BACKWARD_CHANNEL = NOT_CLAIMED
GENERAL_EFFECT_ACK_DONE = NOT_CLAIMED
```
