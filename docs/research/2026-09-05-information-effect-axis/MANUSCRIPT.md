# Vom Unterschied zur verantwortbaren Wirkung

## Historische Rekonstruktion, Zenodo-Publikationsspur und physikalisch-informationstheoretische Synthese der QIK-VRT-Achse

**Ingolf Lohmann**  
6. September 2026  
QIK-VRT Research Object v2.1 — Transputer/Skalierung/AD-DA-Brücke

## Abstract

Diese Fassung erweitert die QIK-VRT-Informations-Wirkungs-Achse um die bislang fehlende Architekturbrücke von historischer Parallelrechnerarchitektur über Skalierung, Serialisierung und numerische Repräsentation bis zur physischen AD/DA-Grenze und zur Klassifikation von Singularitäts- und Grenzzuständen. Der INMOS-Transputer dient dabei nicht als behaupteter historischer Vorläufer von QIK-VRT, sondern als belastbares Beispiel für ein frühes Architekturprinzip: lokale Berechnung mit expliziter Kommunikation als Bestandteil des Rechenknotens. Die Atari Transputer Workstation machte die Trennung von Compute, I/O und erweiterbaren Rechenknoten anschaulich.

Die zentrale methodische Erweiterung lautet: Nicht nur Compute muss skalieren. Auch Zustand, numerische Semantik, Evidenz, Autorität und Wirkung müssen entlang expliziter Grenzen komponierbar bleiben. Für jede Abbildung zwischen Zustandsräumen wird deshalb gefragt, was erhalten bleibt, was verloren geht, welche Transition zulässig ist und welche Rückbeobachtung die behauptete Wirkung tatsächlich trägt.

Zenodo-Publikation bleibt strikt von empirischer Bestätigung getrennt.

## 1. Erkenntnisgrenze

`BOUND`, `REPOSITORY_EVIDENCE`, `ZENODO_PUBLICATION`, `EMPIRICAL_CONFIRMATION`, `MERGE`, `DEPLOYMENT`, `PASS`, `FINAL_PASS` und `EFFECT_ACK_DONE` sind verschiedene Zustände. Die vorliegende Arbeit beansprucht historische und architektonische Rekonstruktion, nicht eine neue experimentell bestätigte Naturtheorie.

## 2. Historische Invariante

Die verfügbaren QIK-VRT-Stände vom Mai 2026 dokumentieren bereits Audit, Rollback, Stabilitätsprüfung, Verantwortung, Anschlussfähigkeit und Schutz gegen unvollständige Zwischenzustände. Spätestens am 21. Mai 2026 wird formuliert, dass entscheidend ist, ob Zustände unterscheidbar sind, Information tragen, Wirkung erzeugen, kausal anschließen und auditierbar geführt werden.

Die spätere Verdichtung lautet: **Ein Unterschied muss ein Unterschied bleiben.** Behauptung ist nicht Beweis; Sequenz ist nicht Ursache; Nachricht ist nicht Wirkung; Beobachtung ist nicht Wahrheit; Modell ist nicht Realität.

## 3. Öffentliche Zenodo-Publikationsspur

Der repository-eigene öffentliche Inventarbericht vom 22. Juli 2026 bindet einen über Zenodo-Records-API und DOI-Records geprüften Bestand von **14 Versionsrecords in fünf Concept-Linien**. Weitere Publikationslinien kamen danach hinzu. Besonders relevant sind:

- `10.5281/zenodo.20712301`: früher Repository-, Provenienz- und Release-Gating-Stand;
- `10.5281/zenodo.21267021`: RFC-/Node-/Repository-Linie;
- `10.5281/zenodo.21482023`: mathematisch-physikalische Arbeitsfassung;
- `10.5281/zenodo.21488116`: maschinenprüfbare Formalisierung;
- `10.5281/zenodo.21498773`: EFFECT_ACK Working Paper;
- `10.5281/zenodo.21498774`: versionierter EFFECT_ACK-Softwarestand;
- `10.5281/zenodo.22283396`: *From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law*.

Diese Zenodo-Spur belegt öffentliche Archivierung, Versionierung, Metadaten- und DOI-Bindung. Sie beweist nicht automatisch die empirische Wahrheit physikalischer Hypothesen.

## 4. Shannon, Wheeler und Landauer

Shannons Informationstheorie liefert eine fundamentale Ebene der Kette: Information setzt unterscheidbare Zustände voraus; Kommunikation, Abtastung und Rekonstruktion besitzen quantifizierbare Bedingungen und Grenzen. Ein Quantisierungsfehler ist nicht pauschal `Entropieverlust`; informations-theoretischer Verlust verlangt ein konkretes statistisches Modell.

Wheelers `It from Bit` wird als erkenntnistheoretisch-physikalischer Anschluss gelesen: empirisch gerechtfertigte Weltbeschreibung ist durch unterscheidbare Beobachtungsergebnisse und die Bedingungen ihrer Gewinnung vermittelt. Daraus folgt weder eine beliebige Erzeugung von Realität durch Beobachtung noch eine bewiesene Identität von Information und Materie.

Landauers Prinzip bindet logisch irreversible Informationslöschung an Thermodynamik. Im idealisierten quasistatischen Grenzfall beträgt die minimale Wärmeabgabe pro gelöschtem Bit `k_B*T*ln(2)`. Das ist kein allgemeiner Energiepreis für jedes gespeicherte, transportierte, gehashte oder autorisierte Bit.

## 5. Vom Transputer zur expliziten Zustandsgrenze

Der IMS T800 integrierte einen 32-Bit-Prozessor, eine Gleitkommaeinheit, lokalen Speicherzugriff und vier standardisierte serielle Kommunikationslinks. Die Link-Interfaces konnten mittels DMA parallel zum Prozessor arbeiten. Kommunikation war damit nicht bloß nachträgliche Peripherie, sondern architektonische Primitive.

Das occam-Modell passte dazu: lokale Prozesse und explizite Channels statt impliziter globaler Zustandsfreigabe.

Die Atari Transputer Workstation führte dieses Prinzip auf Systemebene anschaulich fort. Das Transputer Handbook beschreibt einen T800-Rechenknoten, der über einen Link mit einem Motorola-68000-I/O-Prozessor verbunden war; die übrigen Links konnten Farmcards mit weiteren T800-Knoten anbinden.

Die belastbare historische Kontinuität lautet daher nicht: „Atari begann QIK-VRT.“ Sie lautet:

**INMOS, Perihelion und Atari operationalisierten skalierbare Berechnung als Komposition lokaler Rechenknoten mit expliziten Kommunikationsgrenzen. QIK-VRT untersucht die weiterführende Architekturfrage, ob nicht nur Compute, sondern auch Zustand, numerische Semantik, Evidenz, Autorität und physische Wirkung entlang expliziter Grenzen rekursiv komponiert werden können.**

## 6. Skalierung: Compute ist nicht State

Amdahls klassisches Strong-Scaling-Modell lautet für seriellen Anteil `f_s` und `N` Prozessoren näherungsweise:

`S(N) = 1 / (f_s + (1-f_s)/N)`.

Unter diesen Annahmen gilt für `N -> infinity`:

`S_max = 1 / f_s`.

Reale verteilte Systeme tragen zusätzlich Kommunikations-, Synchronisations-, Routing-, Speicher-, Reconciliation- und Fehlertoleranzkosten. Daher gilt:

`Compute Scaling != State Scaling`.

Ein System kann Rechenleistung horizontal vervielfachen und trotzdem an globalem Zustand oder Koordination scheitern.

## 7. Serialisierung und kanonische Zustandsmanifestation

Sobald Komponenten keinen gemeinsamen Adressraum besitzen, muss interner Zustand in eine transportierbare Repräsentation überführt werden.

Sei `E : S -> B*` ein Encoder und `D : B* -> S'` ein Decoder. Für einen verlustfreien, gültigen Vertrag wird idealerweise `D(E(s)) = s` gefordert.

Diese Gleichung reicht allein nicht. Bedeutung hängt zusätzlich von Schema, Version, Einheit, Skalierung, numerischem Vertrag, Identität und Kontext ab.

Ein Hash `h = H(E(s))` bindet die Identität einer Bytefolge, nicht ihre Semantik. Deshalb gilt:

`BYTES != MEANING`.

Eine belastbare Zustandsmanifestation benötigt mindestens:

`bytes + schema + version + units/scale + identity + provenance + interpretation contract`.

Nicht jede Serialisierung ist bijektiv. Häufig bildet eine Grenze einen reichen internen Zustand auf eine reduzierte Repräsentation ab. Dann können `S1 != S2` und dennoch `E(S1) = E(S2)` gelten. Die Grenze hat Unterschiede entfernt. Das kann beabsichtigt sein, muss aber sichtbar bleiben.

## 8. Numerische Skalierung und Fixed Point

Eine Integer-Repräsentation `q` kann einen Wert `x` durch `x = q*Delta` darstellen. Für binären Fixed Point mit `F` Nachkommabits gilt `Delta = 2^-F` und damit `x = q*2^-F`.

Das Bitmuster allein trägt daher nicht die vollständige numerische Semantik. Wortbreite, Vorzeichen, Skalierung, Rundung, Sättigung und Overflow-Regeln gehören zum Vertrag.

Für Quantisierung auf ein Gitter gilt idealisiert:

`q = round(x/Delta)`, `x_hat = q*Delta`, `e_q = x - x_hat`.

Bei Rundung auf den nächsten Gitterwert und innerhalb des darstellbaren Bereichs gilt typischerweise `|e_q| <= Delta/2`.

Fixed Point ist damit eine kontrollierte endliche Repräsentation. Seine Stärke liegt darin, Darstellbarkeit, Fehlergrenzen und Grenzzustände explizit zu machen.

## 9. A/D -> Evidenz -> Wirkung

Eine reale Messkette ist näherungsweise:

`physical quantity -> transducer/sensor -> analog front end -> filtering -> sampling -> ADC -> digital code -> calibrated interpretation`.

Ein ADC digitalisiert nicht „die Wirklichkeit“. Er liefert Codes relativ zu einer konkreten Messkette, Referenz, Zeitbasis und Quantisierung. Erst ein Kalibrierungs- und Interpretationsvertrag ordnet dem Code eine physikalische Größe zu.

Ein minimaler physikalischer Evidenzgegenstand trägt mindestens `(value, time, uncertainty, unit, calibration, provenance)`. Je nach Anwendung kommen Sensoridentität, Abtastrate, Bandbreite, Anti-Alias-Filter, Quantizer, Skalierung, Rundungsmodus und Signatur hinzu.

Sampling zeigt, dass verschiedene kontinuierliche Verläufe unter unzureichenden Voraussetzungen dieselbe Samplefolge erzeugen können. Verlorene Messinformation kann später nicht ohne zusätzliche Modellannahmen rekonstruiert werden.

## 10. D/A -> Aktuation -> Readback

Die Gegenrichtung lautet schematisch:

`digital code -> DAC -> reconstruction/hold -> driver -> actuator -> physical plant`.

Ein erfolgreich geschriebener Code beweist nicht, dass die reale Zielgröße erreicht wurde. Deshalb gilt:

`COMMAND != TRANSPORT_ACK != ACTUATION != OBSERVED_EFFECT`.

Ein physischer Effekt benötigt unabhängige Rückbeobachtung. Damit entsteht der geschlossene Kreis:

`OBSERVE -> BIND -> COMPUTE -> AUTHORIZE -> ACT -> REOBSERVE`.

Das ist zugleich Regelkreis und epistemischer Kontrollkreis.

## 11. Allgemeiner Knoten- und Grenzvertrag

Ein evidenzgebundener Knoten kann konzeptionell beschrieben werden als:

`N = (S, K, A, I, O, T, R)`

mit lokalem Zustand `S`, Evidenz `K`, Autorität `A`, Ein- und Ausgangsverträgen `I/O`, zulässigen Transitionen `T` und Readback-Vertrag `R`.

Eine Grenze zwischen zwei Knoten kann zusätzliche Vertragsdaten tragen:

`e_ij = (E, D, Sigma, V, U, P, tau)`

mit Encoder, Decoder, Schema, Version, Einheit/Skalierung, Provenienz und zeitlich-kausaler Gültigkeit.

Interoperabilität bedeutet dann nicht, dass alle Knoten intern gleich sind. Sie bedeutet, dass die nach außen behauptete Semantik nachweisbar kompatibel realisiert wird.

## 12. Rekursive Komposition und Evidence Scaling

Ein Knoten kann selbst aus Unterknoten bestehen. Rekursion ist jedoch nur dann tragfähig, wenn die Grenzen ihre Semantik erhalten.

Daraus ergibt sich eine mögliche Skalierungsfolge:

`Compute Scaling -> State Scaling -> Evidence Scaling -> Authority Scaling -> Effect Scaling`.

Diese Größen sind nicht äquivalent. Rechenarbeit kann häufig repliziert werden. Autorität darf nicht beliebig repliziert werden. Information über einen Effekt kann kopiert werden; der historische Effekt selbst bleibt ein konkretes Ereignis.

Daher gilt:

`reproducible information != reproducible authority != reproducible effect`.

## 13. Koordination und Ereignisorientierung

Bei vollständiger paarweiser Kommunikation wächst die Zahl möglicher Beziehungen mit `N(N-1)/2`. Ein großes Mesh kann daher nicht sinnvoll auf permanentem vollständigem Zustandsaustausch beruhen.

Skalierbare Systeme benötigen Lokalität, Hierarchie, Aggregation, Routing, Subscriptions, Ereignisse, Backpressure und Deduplication.

Ereignisorientierung reduziert unnötige Zustandsabfragen:

`event -> exact observation -> bounded transition`.

Sie ist keine Garantie für Skalierbarkeit, aber eine Voraussetzung dafür, dass Kommunikation stärker mit relevanten Zustandsänderungen als mit blindem Polling wächst.

## 14. Singularitäten und Grenzzustände

Der Begriff „Singularität“ darf nicht als Sammelbegriff für jede technische Störung verwendet werden. Zu unterscheiden sind mindestens:

- mathematische Singularität,
- Koordinaten- oder Darstellungssingularität,
- numerische Pathologie oder schlechte Konditionierung,
- Modellgrenze,
- physikalische Singularitätsdiagnose.

Für eine Abbildung `f : X -> Y` gilt: Ist sie nicht injektiv, existieren `x1 != x2` mit `f(x1) = f(x2)`. Dann ist bezüglich dieser Abbildung Information verloren.

Bei differenzierbaren mehrdimensionalen Transformationen kann Rangverlust der Jacobi-Matrix lokale Invertierbarkeit verhindern; in quadratischer Form ist `det J = 0` ein klassisches Warnsignal.

Quantisierung liefert ein anderes, bewusst nichtinvertierbares Mapping: kontinuierlich viele Eingangswerte werden auf endlich viele Codes abgebildet.

Diese strukturelle Gemeinsamkeit rechtfertigt keine physikalische Gleichsetzung. Sie rechtfertigt dieselben Prüfungen: Welche Domäne gilt? Welche Invarianten bleiben erhalten? Wo geht Information verloren? Wann ist eine Fortsetzung oder Inversion nicht mehr berechtigt?

## 15. Fail-closed an Contract Boundaries

Ein robustes System darf nicht voraussetzen, dass für jeden Eingang ein gewöhnlicher Ausgang existiert.

Für `y = a/b` gehört `b != 0` zum Domänenvertrag. Ist die Bedingung verletzt, ist ein expliziter Zustand wie `DOMAIN_ERROR` oder `HOLD` korrekter als eine erfundene gewöhnliche Zahl.

Dasselbe Prinzip gilt für Overflow, Saturation, ungültige ADC-Bereiche, fehlende Kalibrierung, nicht konvergierende Solver, Rangdefizienz, nicht beobachtbare Zustände und Out-of-Domain-Eingaben.

Ein System, das diese Zustände unterscheidet, ist epistemisch stärker als eines, das unter allen Umständen einen scheinbar normalen Wert erzeugt.

## 16. Mesh-Anschlussvertrag

Andockende Systeme müssen folgende Grenzen erhalten:

- `BYTES != MEANING`
- `SEQUENCE != CAUSALITY`
- `TRANSPORT_ACK != EFFECT_ACK`
- `OBSERVATION != TRUTH`
- `MODEL != REALITY`
- `VERIFIED_IMPLEMENTATION != AUTHORITY_EFFECT`
- `REPOSITORY_EVIDENCE != ZENODO_PUBLICATION`
- `ZENODO_PUBLICATION != EMPIRICAL_CONFIRMATION`
- `FALSIFIABLE_HYPOTHESIS != EMPIRICALLY_CONFIRMED_LAW`

Fehlende Pflichtmetadaten führen fail-closed zu `HOLD`, unbekannte oder veraltete Beobachtung zu `REOBSERVE`, externe Autorität zu `REQUEST_AUTHORITY`.

## 17. Universales Terminal als Zustandsraumgrenze

Ein „universales Terminal“ ist in diesem Rahmen keine bloße Benutzerschnittstelle, sondern eine definierte Grenzfläche zwischen Zustandsräumen.

Eine autorisierte Transition kann als `(S,K) -> (S',K')` geschrieben werden. Nicht nur der operative Zustand `S` ändert sich. Auch der evidierte Wissenszustand `K` muss aktualisiert werden.

Ein Terminal kann daher einen Lauf terminieren, ohne die Möglichkeit des nächsten überprüfbaren Anschlusses zu terminieren.

## 18. Wissenschaftliche Claim-Matrix

**Historisch belegt:** T800 mit vier Standardlinks; paralleler Link-/Prozessorbetrieb; occam mit expliziter Parallelität und Kommunikation; ATW mit T800, getrenntem 68000-I/O-Prozessor und Farmcard-Erweiterung.

**Mathematisch belegt:** Nichtinjektive Abbildungen besitzen keine eindeutige Umkehrung ohne Zusatzinformation; Quantisierung ist im Allgemeinen nicht injektiv; Amdahls Modell begrenzt Strong Scaling unter seinen Annahmen; Rangverlust kann lokale Invertierbarkeit verhindern.

**Ingenieurwissenschaftlich etabliert:** ADC-/DAC-Ketten benötigen Mess- und Aktuationsverträge; digitale Kommandos garantieren keine physische Wirkung; Readback ist zur Feststellung des erreichten Zustands erforderlich.

**QIK-VRT-Architekturthese:** Compute, State, Evidence, Authority und Effect können als getrennte, rekursiv komponierbare Zustands- und Grenzverträge behandelt werden.

**Nicht dadurch empirisch bewiesen:** physikalische Retrokausalität, neue Planck-Skalen-Dynamik, Quantengravitation, universelle physikalische Gültigkeit von QIK-VRT oder die Behauptung, physikalische Singularitäten seien Serialisierungsfehler.

## 19. Autorschaft und Priorität

Die QIK-VRT-Konzeption, die dokumentierte Entwicklungs- und Publikationslinie und die hier rekonstruierten Kerninvarianten sind Ingolf Lohmann zugeordnet. Öffentlich nachweisbare Priorität wird nur so weit beansprucht, wie datierte Artefakte, Repository-Historie und DOI-Records sie tragen.

Die historische Transputer-Linie wird als Anschluss- und Vergleichsarchitektur behandelt, nicht als Ursprung der QIK-VRT-Konzeption.

## 20. Schluss

INMOS, Perihelion und Atari zeigten, wie Rechenleistung durch kommunikationsfähige lokale Knoten komponiert werden kann. Die hier entwickelte Weiterführung übernimmt das strukturelle Prinzip expliziter Grenzen und erweitert die Fragestellung:

Nicht nur Berechnung, sondern auch Zustand, numerische Semantik, Evidenz, Autorität und physische Wirkung müssen beim Skalieren kontrolliert komponierbar bleiben.

Die kürzeste Form lautet:

`local states + explicit boundaries + bound information + controlled transitions + independent readback`.

Für jede Kante bleibt dieselbe wissenschaftliche Frage:

**Was ist tatsächlich übertragen, was tatsächlich transformiert, was tatsächlich autorisiert, was tatsächlich beobachtet – und was folgt daraus wirklich?**

Die universelle Invariante dieses Rahmens lautet:

**Keine Transition darf mehr behaupten, als ihre Grenze tatsächlich trägt.**

## Literatur und gebundene Anschlussquellen

- INMOS. *Transputer Architecture Reference Manual*.
- INMOS. *Transputer Development System*, Second Edition.
- INMOS. Technische Dokumentation zum IMS T800 Floating-Point Transputer.
- *The Transputer Handbook*. Abschnitt zur Atari Transputer Workstation.
- Amdahl, G. M. (1967). *Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities*.
- Shannon, C. E. (1948). *A Mathematical Theory of Communication*.
- Wheeler, J. A. (1990). *Information, physics, quantum: The search for links*.
- Landauer, R. (1961). *Irreversibility and Heat Generation in the Computing Process*.
- Lohmann, I. QIK-VRT, mathematisch-physikalische Arbeitsfassung. Zenodo DOI `10.5281/zenodo.21482023`.
- Lohmann, I. QIK-VRT, maschinenprüfbare Formalisierung. Zenodo DOI `10.5281/zenodo.21488116`.
- Lohmann, I. QIK-VRT / EFFECT_ACK. Zenodo DOI `10.5281/zenodo.21498773`.
- Lohmann, I. Versionierter QIK-VRT / EFFECT_ACK-Softwarestand. Zenodo DOI `10.5281/zenodo.21498774`.
- Lohmann, I. (2026). *From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law*. Zenodo DOI `10.5281/zenodo.22283396`.

## Evidenzstatus

Diese Fassung integriert die Transputer-/Skalierungs-/AD-DA-/Singularitäts-Brücke in den wissenschaftlichen Hauptcarrier. Ein **neuer** Zenodo-DOI für diese Synthese wird erst nach authentifiziertem Publish-Readback beansprucht. Aus Repository-Persistenz oder bestehenden Publikationen folgen weder Merge noch Deployment noch empirische Bestätigung noch `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.
