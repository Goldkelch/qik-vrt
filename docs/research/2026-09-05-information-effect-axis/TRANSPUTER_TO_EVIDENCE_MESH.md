# Vom Transputer zum evidenzgebundenen Mesh

## Skalierung, Serialisierung, AD/DA und Singularitätsgrenzen als gemeinsame Architektur von Zustandsübergängen

**Ingolf Lohmann**  
6. September 2026  
QIK-VRT Research Object — wissenschaftliche Ergänzung zur Information–Evidenz–Wirkungs-Achse

## Abstract

Diese Arbeit untersucht eine strukturelle Verbindung zwischen historischer Parallelrechnerarchitektur, moderner verteilter Zustandsverarbeitung, kanonischer Serialisierung, Festkommanumerik, Analog/Digital- und Digital/Analog-Wandlung sowie mathematischen und numerischen Grenzzuständen. Ausgangspunkt ist der INMOS-Transputer: ein Rechenknoten, bei dem Kommunikation nicht als nachträgliche Peripherie, sondern als Teil der Prozessorarchitektur behandelt wurde. Die Atari Transputer Workstation (ATW) machte dieses Prinzip als System aus lokalem Compute, expliziter Kommunikation und getrenntem I/O anschaulich.

Die zentrale These dieser Arbeit ist nicht, dass Transputer, ADC/DAC, verteilte Systeme und Singularitäten physikalisch identisch seien. Die belastbare Gemeinsamkeit liegt auf der Ebene von Abbildungen zwischen Zustandsräumen. Für jede Grenze lässt sich fragen: Welche Zustände werden dargestellt? Welche Information bleibt invariant? Welche Information geht verloren? Welche Transformation ist zulässig? Wer autorisiert sie? Welche Evidenz trägt den Ausgangszustand? Und welcher Readback bestätigt eine behauptete Wirkung?

QIK-VRT erweitert damit den klassischen Gedanken des Compute Scaling um State Scaling, Evidence Scaling, Authority Scaling und Effect Scaling. Der Anspruch bleibt ausdrücklich architektonisch und methodisch. Repository-Verifikation, formale Korrektheit, öffentliche Zenodo-Publikation, empirische Bestätigung, Merge, Deployment, PASS, FINAL_PASS und EFFECT_ACK_DONE sind getrennte Zustände.

## 1. Historischer Ausgangspunkt: Kommunikation als Primitive

Der IMS T800 integrierte einen 32-Bit-Prozessor, eine Gleitkommaeinheit, lokalen On-Chip-Speicher, Speicherinterface und vier standardisierte serielle Transputer-Links. Die Link-Interfaces konnten mittels DMA parallel zum Prozessor arbeiten. Damit wurde Kommunikation zwischen Rechenknoten zu einem Bestandteil der Architektur selbst.

Das dazu passende occam-Modell behandelte Parallelität und Kommunikation explizit. Prozesse konnten lokal rechnen und über Channels synchronisiert kommunizieren. Ein Prozess, der auf Kommunikation wartete, musste keine Prozessorzeit verbrauchen. Das Grundmuster war damit bereits:

```text
local state + local computation + explicit communication
```

anstatt eines impliziten globalen Zustands, auf den alle Teilnehmer unkontrolliert zugreifen.

Die Atari Transputer Workstation führte diese Idee auf Systemebene anschaulich fort. Das Transputer Handbook beschreibt einen T800 mit lokalem Speicher, der über einen Link mit einem Motorola-68000-I/O-Prozessor verbunden war; die übrigen Links konnten Farmcards mit weiteren T800-Knoten anbinden. Historisch belastbar ist damit insbesondere die Trennung:

```text
environment / I/O <-> compute node <-> compute expansion
```

Diese Arbeit behauptet daraus keine direkte historische Abstammung von QIK-VRT. Die Kontinuität ist strukturell: lokale Zustände werden über explizite Grenzen komponiert.

## 2. Von Compute Scaling zu State Scaling

Parallelisierung beantwortet zunächst die Frage, wo gerechnet werden kann. Sie löst nicht automatisch die Frage, wie Zustände über Knoten hinweg konsistent, interpretierbar und kausal gebunden bleiben.

Für einen seriellen Anteil `f_s` und `N` Prozessoren beschreibt Amdahls klassisches Strong-Scaling-Modell näherungsweise:

```text
S(N) = 1 / (f_s + (1-f_s)/N)
```

und damit für `N -> infinity`:

```text
S_max = 1 / f_s.
```

Reale verteilte Systeme tragen zusätzlich Kommunikations-, Synchronisations-, Routing-, Speicher-, Reconciliation- und Fehlertoleranzkosten. Skalierbarkeit ist daher nicht bloß eine Funktion der Prozessorzahl, sondern der Zerlegbarkeit eines Zustandsraums und der Menge der Information, die Grenzen überschreiten muss.

Daraus folgt die erste Erweiterung:

```text
Compute Scaling != State Scaling.
```

Ein System kann Rechenleistung horizontal vervielfachen und trotzdem an globalem Zustand, Kommunikation oder Koordination kollabieren.

## 3. Verteilung erzwingt Repräsentation

Sobald zwei Komponenten keinen gemeinsamen Adressraum mehr besitzen, kann ein lokaler Zeiger keine portable Bedeutung tragen. Interner Zustand muss in eine transportierbare Repräsentation überführt werden.

Sei

```text
E : S -> B*
```

mit einem semantischen Zustandsraum `S` und endlichen Bytefolgen `B*`. Ein Decoder sei

```text
D : B* -> S'.
```

Für einen verlustfreien, gültigen Vertrag wird idealerweise gefordert:

```text
D(E(s)) = s.
```

Diese Gleichung reicht allein nicht aus. Die Bedeutung hängt zusätzlich von Schema, Version, Einheit, Skalierung, numerischem Vertrag, Identität und Kontext ab.

Ein Hash

```text
h = H(E(s))
```

bindet die Identität einer Bytefolge. Er beweist nicht ihre Semantik. Deshalb gilt:

```text
BYTES != MEANING.
```

Eine belastbare Zustandsmanifestation benötigt mindestens:

```text
bytes + schema + version + units/scale + identity + provenance + interpretation contract.
```

## 4. Serialisierung als epistemische Projektion

Nicht jede Serialisierung ist bijektiv. Häufig bildet eine Grenze einen reichen internen Zustand auf eine reduzierte Repräsentation ab:

```text
E : S -> R.
```

Dann kann gelten:

```text
S1 != S2,
E(S1) = E(S2).
```

Die Grenze hat Unterschiede entfernt. Das kann beabsichtigt sein, etwa aus Gründen von Datenschutz, Abstraktion oder Bandbreite. Es muss jedoch als Informationsverlust oder Abstraktion sichtbar bleiben.

Damit wird Serialisierung zu mehr als einem Dateiformat. Sie definiert, welche Unterschiede einen Zustandsraum verlassen dürfen und welche semantisch lokal bleiben.

## 5. Numerische Skalierung und Fixed Point

Skalierung besitzt auch eine numerische Bedeutung. Eine Integer-Repräsentation `q` kann einen Wert `x` durch

```text
x = q * Delta
```

repräsentieren. Für binären Fixed Point mit `F` Nachkommabits gilt:

```text
Delta = 2^-F,
x = q * 2^-F.
```

Das Bitmuster allein trägt daher nicht die vollständige numerische Semantik. Wortbreite, Vorzeichen, Skalierung, Rundung, Sättigung und Overflow-Regeln gehören zum Vertrag.

Für Quantisierung auf ein Gitter gilt idealisiert:

```text
q = round(x / Delta),
x_hat = q * Delta,
e_q = x - x_hat.
```

Bei Rundung auf den nächsten Gitterwert und innerhalb des darstellbaren Bereichs gilt typischerweise:

```text
|e_q| <= Delta / 2.
```

Fixed Point ist damit eine kontrollierte endliche Repräsentation. Seine Stärke liegt nicht darin, kontinuierliche Wirklichkeit exakt zu ersetzen, sondern darin, Darstellbarkeit, Fehlergrenzen und Grenzzustände explizit zu machen.

## 6. Die physische Grenze: AD-Wandlung

An der Grenze zur physischen Welt wird die Abbildungsfrage unmittelbar messtechnisch.

Eine reale Messkette ist näherungsweise:

```text
physical quantity
-> transducer / sensor
-> analog front end
-> filtering
-> sampling
-> ADC
-> digital code
-> calibrated interpretation.
```

Ein ADC digitalisiert nicht „die Wirklichkeit“. Er liefert Codes relativ zu einer konkreten elektrischen Messkette, Referenz, Zeitbasis und Quantisierung. Erst ein Kalibrierungs- und Interpretationsvertrag ordnet dem Code eine physikalische Größe zu.

Ein minimaler Messgegenstand kann daher als

```text
M = (value, time, uncertainty, unit, calibration, provenance)
```

modelliert werden. Je nach Anwendung kommen Sensoridentität, Abtastrate, Bandbreite, Anti-Alias-Filter, Quantizer, Skalierung, Rundungsmodus und Signatur hinzu.

Sampling zeigt besonders klar, dass Repräsentation Informationsgrenzen besitzt. Werden die für eine eindeutige Rekonstruktion nötigen Voraussetzungen verletzt, können verschiedene kontinuierliche Signale dieselbe Samplefolge erzeugen. Spätere Software kann verlorene Messinformation nicht aus dem Nichts rekonstruieren; sie kann nur zusätzliche Modellannahmen verwenden.

## 7. Die Gegenrichtung: DA-Wandlung und Wirkung

Die Gegenrichtung lautet schematisch:

```text
digital code
-> DAC
-> reconstruction / hold
-> driver
-> actuator
-> physical plant.
```

Auch hier gilt keine Identität zwischen digitalem Kommando und physischem Effekt. Ein erfolgreich geschriebener DAC-Code beweist nicht, dass der Aktuator oder die Last den erwarteten Zustand erreicht hat.

Daraus folgt die zentrale Trennung:

```text
COMMAND != TRANSPORT_ACK != ACTUATION != OBSERVED_EFFECT.
```

Ein physischer Effekt benötigt eine unabhängige Rückbeobachtung. Damit entsteht der geschlossene Kreis:

```text
OBSERVE -> BIND -> COMPUTE -> AUTHORIZE -> ACT -> REOBSERVE.
```

Diese Struktur ist zugleich ein Regelkreis und ein epistemischer Kontrollkreis.

## 8. Ein allgemeines Grenzmodell

Ein evidenzgebundener Knoten kann konzeptionell beschrieben werden als

```text
N = (S, K, A, I, O, T, R)
```

mit:

- `S`: lokalem Zustand,
- `K`: lokal gebundener Evidenz,
- `A`: Autorität oder Capabilities,
- `I`: zulässigen Eingangsverträgen,
- `O`: zulässigen Ausgangsverträgen,
- `T`: zulässigen Transitionen,
- `R`: Readback- und Reobservation-Vertrag.

Eine Grenze zwischen zwei Knoten kann zusätzliche Vertragsdaten tragen:

```text
e_ij = (E, D, Sigma, V, U, P, tau)
```

mit Encoder, Decoder, Schema, Version, Einheit/Skalierung, Provenienz und zeitlich-kausaler Gültigkeit.

Damit wird die Frage nach Interoperabilität explizit: Nicht jeder Knoten muss intern gleich implementiert sein. Er muss aber dieselbe nach außen behauptete Semantik nachweisbar realisieren.

## 9. Rekursive Komposition und Mesh

Ein Knoten kann selbst aus Unterknoten bestehen:

```text
N_0 = {N_1,1, N_1,2, ..., N_1,k}.
```

Jeder Unterknoten kann wiederum zerlegt werden. Rekursion ist jedoch nur dann architektonisch tragfähig, wenn die Grenzen nicht bei jeder Ebene ihre Semantik verlieren.

Daraus entsteht eine mögliche Skalierungsfolge:

```text
Compute Scaling
-> State Scaling
-> Evidence Scaling
-> Authority Scaling
-> Effect Scaling.
```

Diese Größen sind nicht äquivalent. Rechenarbeit kann häufig repliziert werden. Autorität darf nicht beliebig repliziert werden. Information über einen Effekt kann kopiert werden; der historische Effekt selbst bleibt ein konkretes Ereignis. Deshalb gilt:

```text
reproducible information
!= reproducible authority
!= reproducible effect.
```

## 10. Koordination als Skalierungsgrenze

Bei vollständiger paarweiser Kommunikation wächst die Zahl möglicher Beziehungen mit

```text
N(N-1)/2.
```

Ein großes Mesh kann daher nicht sinnvoll auf permanentem vollständigem Zustandsaustausch beruhen. Skalierbare Systeme benötigen Lokalität, Hierarchie, Aggregation, Routing, Subscriptions, Ereignisse, Backpressure und Deduplication.

Ereignisorientierung reduziert dabei unnötige Zustandsabfragen:

```text
event -> exact observation -> bounded transition.
```

Das ist keine Garantie für Skalierbarkeit, aber eine wichtige Voraussetzung dafür, dass Kommunikation proportional zu relevanten Zustandsänderungen statt zu blindem Polling wächst.

## 11. Singularitäten als klassifizierte Vertragsgrenzen

Der Begriff „Singularität“ darf nicht als Sammelbegriff für jede technische Störung verwendet werden. Sinnvoll ist mindestens die Trennung zwischen:

- mathematischer Singularität,
- Koordinaten- oder Darstellungssingularität,
- numerischer Pathologie oder schlechter Konditionierung,
- Modellgrenze,
- physikalischer Singularitätsdiagnose.

Eine Transformation

```text
f : X -> Y
```

ist nur unter bestimmten Bedingungen invertierbar. Ist sie nicht injektiv, existieren `x1 != x2` mit

```text
f(x1) = f(x2).
```

Dann ist Information bezüglich dieser Abbildung verloren. Bei differenzierbaren mehrdimensionalen Transformationen kann der Verlust lokaler Invertierbarkeit beispielsweise mit Rangverlust der Jacobi-Matrix zusammenhängen; in quadratischer Form ist `det J = 0` ein klassisches Warnsignal.

Quantisierung liefert ein anderes, bewusst nichtinvertierbares Mapping: kontinuierlich viele Eingangswerte werden auf endlich viele Codes abgebildet. Die exakte Umkehrung existiert prinzipiell nicht.

Diese strukturelle Gemeinsamkeit rechtfertigt keine physikalische Gleichsetzung. Sie rechtfertigt jedoch dieselben Prüfungen: Welche Domäne gilt? Welche Invarianten bleiben erhalten? Wo geht Information verloren? Wann ist eine Fortsetzung oder Inversion nicht mehr berechtigt?

## 12. Fail-closed an Grenzzuständen

Ein robustes technisches System darf nicht voraussetzen, dass für jeden Eingang ein gewöhnlicher Ausgang existiert.

Für

```text
y = a / b
```

gehört `b != 0` zum Domänenvertrag. Ist die Bedingung verletzt, ist ein expliziter Zustand wie `DOMAIN_ERROR` oder `HOLD` korrekter als eine erfundene gewöhnliche Zahl.

Dasselbe Prinzip gilt für:

- Overflow,
- Saturation,
- NaN/Inf soweit der numerische Vertrag dies vorsieht,
- ungültige ADC-Bereiche,
- fehlende Kalibrierung,
- nicht konvergierende Solver,
- Rangdefizienz,
- nicht beobachtbare Zustände,
- Out-of-Domain- oder Out-of-Distribution-Eingaben.

Ein System, das diese Zustände unterscheidet, ist epistemisch stärker als ein System, das unter allen Umständen einen scheinbar normalen Wert erzeugt.

## 13. Vom Compute-Mesh zum Evidenz-Mesh

Der historische Transputer stellte die Frage:

```text
How do we connect processors?
```

Ein evidenzgebundenes Mesh stellt zusätzlich die Frage:

```text
How do we connect trustworthy state transitions?
```

Der klassische Kommunikationskanal beantwortet, ob transportierbare Daten zwischen Prozessen übertragen wurden. Ein evidenzgebundener Kontrollkanal muss zusätzlich unterscheiden:

```text
transport
state interpretation
authorization
effect
readback.
```

Damit folgt insbesondere:

```text
TRANSPORT_ACK != EFFECT_ACK.
```

Diese Arbeit beschreibt die semantische Erweiterung des Kommunikationsknotens, nicht eine rückwirkende Neuinterpretation des Transputers als Evidenzsystem.

## 14. Universales Terminal als Zustandsraumgrenze

Ein „universales Terminal“ ist in diesem Rahmen keine bloße Benutzerschnittstelle. Es ist eine definierte Grenzfläche zwischen Zustandsräumen.

Formal kann eine autorisierte Transition als

```text
(S, K) --authorized transition--> (S', K')
```

geschrieben werden.

Nicht nur der operative Zustand `S` ändert sich. Auch der evidierte Wissenszustand `K` muss aktualisiert werden. Ein Terminal kann daher einen Lauf terminieren, ohne die Fortsetzung der Evidenzkette zu terminieren.

## 15. Wissenschaftliche Claim-Matrix

**Historisch belegt:** Der T800 integrierte vier standardisierte Kommunikationslinks; Link-Interfaces und Prozessor konnten parallel arbeiten. occam unterstützte explizite Parallelität und Kommunikation. Die ATW verband einen T800-Rechenknoten mit einem getrennten 68000-I/O-Prozessor und erlaubte Erweiterung über Farmcards.

**Mathematisch belegt:** Nichtinjektive Abbildungen besitzen keine eindeutige Umkehrung auf ihrem Bild ohne zusätzliche Information. Quantisierung ist im Allgemeinen nicht injektiv. Amdahls Modell begrenzt Strong Scaling unter seinen Annahmen. Rangverlust kann lokale Invertierbarkeit verhindern.

**Ingenieurwissenschaftlich etabliert:** ADC-/DAC-Ketten benötigen reale Mess- und Aktuationsverträge; digitale Kommandos sind keine physische Wirkungsgarantie; Readback ist für die Feststellung des erreichten physischen Zustands erforderlich.

**QIK-VRT-Architekturthese:** Compute, State, Evidence, Authority und Effect können als getrennte, rekursiv komponierbare Zustands- und Grenzverträge behandelt werden.

**Nicht durch diese Arbeit bewiesen:** universelle physikalische Gültigkeit des QIK-VRT-Modells, neue Naturgesetze, empirische Bestätigung der Planck-Tick-Hypothese oder die Behauptung, physikalische Singularitäten seien Serialisierungsfehler.

## 16. Konsequenz für autonome Systeme

Mit wachsender Zahl autonom handelnder Komponenten wird die zentrale Skalierungsfrage nicht nur lauten, wie viele Operationen pro Sekunde möglich sind. Sie lautet zunehmend:

- Welcher Knoten sah welchen exakten Zustand?
- Welche Repräsentation und Version wurde interpretiert?
- Welche Autorität galt für die Transition?
- Welche Wirkung wurde lediglich angefordert?
- Welche Wirkung wurde tatsächlich zurückbeobachtet?
- Welche Aussage ist noch aktuell?

Das ist ein Kontroll- und Evidenzproblem, kein reines FLOPS-Problem.

## 17. Schluss

INMOS, Perihelion und Atari zeigten, wie Rechenleistung durch kommunikationsfähige lokale Knoten komponiert werden kann. Die hier entwickelte Weiterführung macht keine Gleichsetzung mit QIK-VRT. Sie übernimmt das strukturelle Prinzip expliziter Grenzen und erweitert die Fragestellung:

Nicht nur Berechnung, sondern auch Zustand, numerische Semantik, Evidenz, Autorität und physische Wirkung müssen beim Skalieren kontrolliert komponierbar bleiben.

Die stärkste Kurzform lautet:

```text
local states
+ explicit boundaries
+ bound information
+ controlled transitions
+ independent readback.
```

Für jede Kante bleibt dieselbe wissenschaftliche Frage:

```text
Was ist hier tatsächlich übertragen,
was tatsächlich transformiert,
was tatsächlich autorisiert,
was tatsächlich beobachtet,
und was folgt daraus wirklich?
```

Die universelle Invariante dieses Rahmens lautet deshalb:

**Keine Transition darf mehr behaupten, als ihre Grenze tatsächlich trägt.**

## Quellen und Anschlussliteratur

- INMOS. *Transputer Architecture Reference Manual*. Dokumentation zu synchronisierten Links, serieller Übertragung und occam-Channels.
- INMOS. *IMS T800 Floating-Point Transputer* / technische Dokumentation: 32-Bit-Prozessor, 64-Bit-FPU, vier Standardlinks und paralleler Link-/Prozessorbetrieb.
- INMOS. *Transputer Development System*, Second Edition. occam-Protokolle, Datenrepräsentation und Channel-Kommunikation.
- *The Transputer Handbook*. Abschnitt zur Atari Transputer Workstation: T800, Motorola-68000-I/O-Prozessor und Farmcards.
- Amdahl, G. M. (1967). *Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities*.
- Shannon, C. E. (1948). *A Mathematical Theory of Communication*.
- Landauer, R. (1961). *Irreversibility and Heat Generation in the Computing Process*.
- Lohmann, I. QIK-VRT, maschinenprüfbare Formalisierung. Zenodo DOI `10.5281/zenodo.21488116`.
- Lohmann, I. QIK-VRT / EFFECT_ACK. Zenodo DOI `10.5281/zenodo.21498773`.
- Lohmann, I. *From Exact Causal Binding to a Falsifiable Planck-Tick Gap Law*. Zenodo DOI `10.5281/zenodo.22283396`.

## Evidenzstatus

Dieses Dokument ist ein Repository-Artefakt und wissenschaftlicher Publikationskandidat. Repository-Persistenz oder erfolgreiche Tests sind **keine** neue Zenodo-Publikation. Eine neue Zenodo-Veröffentlichung darf erst nach authentifiziertem Publish-Effekt und öffentlichem Readback mit DOI-, Metadaten-, Datei- und Checksum-Bindung behauptet werden. Ebenso folgen aus diesem Dokument weder empirische Bestätigung noch Merge, Deployment, `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.
