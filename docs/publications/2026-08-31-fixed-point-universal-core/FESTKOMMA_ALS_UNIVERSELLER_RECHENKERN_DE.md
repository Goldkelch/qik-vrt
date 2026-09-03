Festkomma als universeller Rechenkern

Wie spezialisierte Hardware endliche Gleitkommasemantik realisiert – und wann sie sie übertreffen kann

Ausgangsgedanke und Architekturperspektive: Ingolf Lohmann
Wissenschaftlich-technische Ausarbeitung: 31. August 2026
Geltungsstatus: formaler Realisierbarkeitssatz, etablierte Rechnertechnik, an konkrete Systeme gebundene empirische Leistungsbelege und klar gekennzeichneter QIK‑VRT-Entwurfsausblick

> **Kernsatz:** Jede vollständig definierte, endliche binäre Gleitkommasemantik kann durch eine endliche digitale Maschine aus Ganzzahl-, Festkomma-, Schiebe-, Vergleichs- und Steuerlogik realisiert werden. Sind Wertebereich, Fehlerbudget und Operationsstruktur eines Problems enger als die Allgemeinheit des Gleitkommaformats, kann die für den Vertrag benötigte Semantik bitgenau oder innerhalb einer festgelegten Fehlergrenze (\varepsilon) spezialisiert und in schmalere, dichtere und stärker parallele Festkommadatenpfade überführt werden. Dass eine solche Realisierung eine bestimmte Gleitkommaimplementierung übertrifft, ist für konkrete Kernel bereits praktisch belegt; eine von Format, Eingaben, Hardware und Arbeitslast unabhängige Überlegenheit wäre dagegen eine andere und nicht haltbare Behauptung.

Abstract

Festkommaarithmetik wird häufig als eingeschränkte Alternative zur Gleitkommaarithmetik dargestellt: weniger Dynamikbereich, mehr Verantwortung für Skalierung, größere Gefahr von Überlauf. Diese Beschreibung ist richtig, aber unvollständig. Sie übersieht, dass jede endliche Gleitkommazahl selbst aus endlich vielen Bits besteht und dass jede vollständig spezifizierte endliche binäre Gleitkommaoperation letztlich durch Operationen auf diesen Bits realisiert wird. Vorzeichen, Exponent und Signifikand werden dekodiert; Signifikanden werden als ganze Zahlen verschoben, addiert oder multipliziert; Ergebnisse werden normalisiert, gerundet und wieder verpackt. Festkomma- und Ganzzahllogik sind daher nicht bloß eine numerisch ärmere Konkurrenz zur Gleitkommarechnung. Sie sind eine mögliche Realisierungsbasis ihrer vollständigen endlichen Semantik.

Der praktische Gewinn entsteht allerdings nicht aus einem Wortspiel und auch nicht automatisch aus dem Datentyp. Er entsteht durch Spezialisierung. Ein allgemeines Gleitkommaformat bezahlt in jedem Operator für großen Dynamikbereich, variable Skalierung, Sonderwerte und Rundungsregeln. Kennt ein System dagegen die realen Wertebereiche, Einheiten, Fehlergrenzen und Operationen eines konkreten Problems, können viele dieser Entscheidungen vor der Ausführung getroffen werden. Der verbleibende Datenpfad wird schmaler; Addierer, Multiplizierer und Akkumulatoren lassen sich häufiger replizieren; weniger Bits müssen gespeichert und transportiert werden; Latenz und Überlaufverhalten werden beweisbar. Shared Exponents, Block-Floating-Point, Integer-Slicing und breite exakte Akkumulatoren verbinden dabei den Dynamikbereich der Gleitkommadarstellung mit der Dichte der Festkommalogik.

Dieser Artikel formuliert den mathematischen Realisierbarkeitssatz, erklärt die Hardwaremechanismen, trennt Funktionsäquivalenz von Leistungsüberlegenheit und ordnet aktuelle Belege ein. NVIDIA cuBLAS 13.3 bietet seit CUDA 13.0 Update 2 einen optionalen, festkommaskalierten und in 8-Bit-Integer-Slices zerlegten Emulationspfad für FP64-Matrixmultiplikation. Ootomo, Ozaki und Yokota zeigten auf untersuchten Consumer-GPUs eine schnellere Double-Precision-Matrixmultiplikation auf Integer-Tensor-Cores und bis zu 4,85-fache Beschleunigung einer gebundenen Quanten-Schaltungssimulation unter dem von den Autoren verwendeten FP64-Genauigkeitskriterium. FPGA-Fallstudien zeigen für geeignete Filterdatenpfade drastisch geringere Latenz und Ressourcenbelegung. Das sind keine universellen Naturgesetze, wohl aber Existenz- und Anwendungsbelege für den zentralen technischen Gedanken.

Der vorgeschlagene QIK‑VRT-Festkommastack ergänzt diese Rechenidee um eine Evidenz- und Wirkungsebene. Wortbreite, Skala, Rundung, Sättigung, Akkumulatorbreite, Quellstand, Zielhardware, Testkorpus und Messung sollen Bestandteile desselben prüfbaren Vertrags werden. Ein Rechenergebnis darf nicht allein deshalb als erfolgreich gelten, weil Aktivität beobachtet wurde; Funktionsäquivalenz, numerische Güte und physische Beschleunigung benötigen jeweils ihre eigene Beobachtung. Auf diese Weise kann aus einer plausiblen Optimierung eine falsifizierbare und reproduzierbare Rechnerarchitektur werden.

1. Das eigentliche Missverständnis

Gleitkommaarithmetik wirkt auf der Programmierebene wie eine eigenständige Form des Rechnens. In Hardware ist sie jedoch eine genau definierte Transformation endlicher Bitmuster. Ein binary32- oder binary64-Wert ist kein kontinuierliches Objekt, sondern eine kodierte Kombination aus Vorzeichen, Exponent und Signifikand, ergänzt um Regeln für Null, Subnormalzahlen, Unendlichkeiten und NaNs. Eine Gleitkommaaddition vergleicht Exponenten, verschiebt einen ganzzahligen Signifikanden, addiert oder subtrahiert, normalisiert und rundet. Eine Multiplikation multipliziert ganzzahlige Signifikanden, addiert Exponenten, normalisiert und rundet. Division und Quadratwurzel verwenden iterative oder kombinatorische Verfahren, deren innere Schritte wiederum aus endlicher Ganzzahl-, Vergleichs-, Schiebe- und Auswahl-Logik bestehen.

Dass dies mehr als eine abstrakte Möglichkeit ist, zeigt Berkeley SoftFloat Release 3e. Die Referenzbibliothek implementiert fünf binäre Formate mit 16, 32, 64, 80 und 128 Bits sowie unter anderem Addition, Subtraktion, Multiplikation, Division, Quadratwurzel, Rest, Vergleiche und Konversionen in C auf Basis von Ganzzahlarithmetik; FMA ist für die Formate außer extFloat80 enthalten. SoftFloat implementiert damit einen umfangreichen Kern, aber nicht pauschal sämtliche Operationen von IEEE 754-2019. Es bleibt ein konstruktiver Existenzbeleg dafür, dass binäre Gleitkommasemantik ohne native Gleitkommaeinheit realisiert werden kann. Auch IEEE 754 lässt Implementierungen ausdrücklich vollständig in Software, vollständig in Hardware oder in einer Kombination aus beidem zu. (IEEE 754-2019, Berkeley SoftFloat)

Der wichtige Schluss lautet deshalb nicht: Festkomma und Gleitkomma seien identisch. Der Schluss lautet: Festkomma- und Ganzzahllogik sind ausdrucksstark genug, die endliche Gleitkommasemantik zu tragen. Ob diese Realisierung kleiner, schneller oder sparsamer ist, hängt von ihrer Konstruktion und vom Problem ab.

2. Fixpunkt ist nicht Festkomma

Für QIK‑VRT ist eine terminologische Klärung unverzichtbar. Ein Fixpunkt bezeichnet einen Zustand, der unter einer Transformation invariant bleibt, also etwa (T(S)=S). Festkomma bezeichnet dagegen eine numerische Darstellung mit festgelegter Skalierung, zum Beispiel (x=q,2^{-F}). Beide Begriffe heißen im Englischen „fixed point“, sind mathematisch aber grundverschieden.

Der am 31. August 2026 gegen 20:57 UTC read-only reobservierte Authority-Snapshot main@6c20c80c24fecf7adfa241cdcb1da92a98f74ddf, Tree af1582a26bee7702455a6d632715142b8577f50b, enthält Artefakte zur D3-Projektionsinvarianz, zu endlichen Zustandskodierungen, M68000-Kontrollkernen und simulierter VHDL-Zustandslogik. Die an genau diesen Snapshot gebundene Inventur fand noch keinen numerischen Festkomma-Datenpfad, keine IEEE‑754-Emulation und keinen physischen Festkomma-gegen-Gleitkomma-Benchmark. Der vorhandene Fixpunktbeweis ist daher ein wertvoller Kontroll- und Evidenzbaustein, aber kein bereits ausgeführter Arithmetiknachweis. (D3-Fixpunktdokument, Lean-Beweis)

Gerade die Trennung eröffnet die richtige Verbindung: Die numerische Festkommarechnung soll einen deterministischen Datenpfad liefern; die vorgeschlagene QIK‑VRT-Fixpunkt- und Haltepunktlogik soll prüfen, ob dessen Spezifikation, Ausführung und Wirkung gültig gebunden sind. Rechenkern und Evidenzkern können so ineinandergreifen, ohne miteinander verwechselt zu werden.

3. Das formale Festkommamodell

Ein vorzeichenbehaftetes Zweierkomplement-Festkommawort mit (N) Bits und (F) binären Nachkommabits kodiert die ganze Zahl

[
q\in{-2^{N-1},\ldots,2^{N-1}-1}
]

als

[
\widehat{x}(q)=q,2^{-F}.
]

Die Schrittweite ist (\Delta=2^{-F}), der darstellbare Bereich reicht von

[
x_{\min}=-2^{N-1}\Delta
]

bis

[
x_{\max}=(2^{N-1}-1)\Delta.
]

Wird ein reeller Wert auf den nächsten Gitterpunkt gerundet, ist dieser Gitterpunkt darstellbar und tritt keine Sättigung auf, gilt

[
|x-\widehat{x}|\leq \frac{\Delta}{2}.
]

Damit wird Präzision zu einer expliziten Entwurfsgröße. Ein größerer Wert von (F) verfeinert die Auflösung, verringert bei fester Wortbreite aber den ganzzahligen Bereich. Für einen maximalen Eingangsbetrag (M) ist

[
M2^F\leq 2^{N-1}-1
]

eine konservative Bereichsbedingung. Werden (L) Produkte mit (|p_i|\leq P_{\max}) in einem vorzeichenbehafteten (A)-Bit-Akkumulator gesammelt, genügt entsprechend

[
LP_{\max}\leq 2^{A-1}-1
]

für überlauffreie Akkumulation. Ein seriöser Entwurf muss deshalb nicht nur die Ausgangswerte, sondern auch alle Zwischenwerte begrenzen.

Bei gleicher Skala ist die Addition eine Ganzzahladdition. Für die Multiplikation zweier Werte mit derselben Fraktionsbreite gilt

[
q_z=\operatorname{round}_{\rho}!\left(\frac{q_xq_y}{2^F}\right).
]

Das Produkt wird zunächst in doppelter oder anderweitig ausreichend verbreiterter Wortbreite berechnet und erst anschließend entsprechend dem Rundungsmodus (\rho) zurückskaliert. Für die Division gilt, sofern (q_y\neq0),

[
q_z=\operatorname{round}_{\rho}!\left(\frac{q_x2^F}{q_y}\right).
]

Wrap-around, Sättigung, Trap und formal ausgeschlossener Überlauf sind verschiedene Semantiken. Sie dürfen nicht implizit bleiben. Sättigung kann in Signalverarbeitung sinnvoll sein, zerstört aber im Allgemeinen die Assoziativität. Wrap-around ist für modulare Algebra geeignet, aber nicht automatisch für physikalische Größen. Ein fail-closed Trap ist sicher, kann jedoch einen Echtzeitdatenpfad unterbrechen. Die Wahl gehört deshalb zum numerischen Vertrag.

4. Der Realisierbarkeitssatz

Sei (F) die endliche Menge aller Bitmuster eines festgelegten Gleitkommaformats und sei

[
\operatorname{op}:F^k\times\Theta\rightarrow F\times\Phi
]

eine vollständig definierte Operation einschließlich der Statusflags (\Phi). Die endliche Parametermenge (\Theta) bindet unter anderem Rundungsmodus, Tininess-Erkennung und die gewählte NaN-Policy, soweit der Standard Implementierungswahl zulässt. Weil Definitions- und Wertebereich endlich sind, existiert grundsätzlich eine endliche digitale Schaltung, welche diese Abbildung implementiert. Dieser Existenzbeweis über eine endliche Wahrheitstabelle wäre praktisch unbrauchbar, ist aber logisch vollständig.

Die konstruktive Realisierung ist stärker. Ein endlicher normaler Binärwert lässt sich schreiben als

[
x=(-1)^s M,2^{e-(p-1)},
]

wobei (M) ein ganzzahliger Signifikand mit (p) Bits ist. Subnormalzahlen verwenden denselben ganzzahligen Grundgedanken mit festem Minimalexponenten. Daraus folgt ein konkreter Datenpfad:

1. Felder und Wertklasse dekodieren.
2. Exponenten vergleichen oder kombinieren.
3. Signifikanden durch Ganzzahlverschiebung ausrichten.
4. Ganzzahladdition, -subtraktion, -multiplikation oder ein iteratives Ganzzahlverfahren ausführen.
5. Das breite Ergebnis normalisieren.
6. Guard-, Round- und Sticky-Bits bilden.
7. Den vorgeschriebenen Rundungsmodus anwenden.
8. Überlauf, Unterlauf, Division durch Null, Inexact und Invalid behandeln.
9. Ergebnis und Flags wieder kodieren.

Damit ist die funktionale Realisierbarkeit gezeigt. Für transzendente Funktionen kommen Bereichsreduktion, Polynome, Tabellen oder CORDIC sowie gegebenenfalls eine Korrektrundungsprüfung hinzu. Auch diese Verfahren sind endlich implementierbar, doch ihr Aufwand kann den Vorteil einer Spezialisierung aufheben.

Ein extremes Gedankenexperiment macht sowohl Universalität als auch Grenze sichtbar. Alle endlichen binary32-Werte lassen sich in ein einziges global skaliertes Zweierkomplement-Festkommawort mit 278 Bits und 149 Fraktionsbits einbetten. Für binary64 wären 2.099 Bits mit 1.074 Fraktionsbits nötig. NaN, Unendlichkeit und negatives Null benötigen zusätzliche Kodierungsinformation; Exception-Flags sind ein separater Operationszustand und kein Teil des Festkommawertes. Die Abbildung existiert, ist aber für gewöhnliche Rechenwerke offensichtlich unökonomisch. Praktische Systeme verwenden daher keine einzige globale Skala, sondern lokale oder blockweise Skalen, Integer-Slices und breite Akkumulatoren.

5. Wo die Geschwindigkeit tatsächlich entsteht

Der Geschwindigkeitsgewinn entsteht nicht dadurch, dass ein Binärpunkt auf dem Papier festgeschrieben wird. Er entsteht, wenn allgemeine Entscheidungen aus dem heißen Datenpfad entfernt oder über viele Werte amortisiert werden.

Erstens kann ein fester oder blockweise geteilter Exponent die laufende Exponentenausrichtung und Normalisierung pro Element ersetzen. Zweitens reduzieren kleinere Wortbreiten den Aufwand von Multiplizierern und Addierern und erlauben mehr parallele Rechenbahnen pro Chipfläche. Drittens verringern sie Register-, Cache- und Speicherbandbreite. Viertens können Multiply-Accumulate-Pipelines mit breiten Akkumulatoren viele Produkte ohne Zwischenrundung sammeln. Fünftens lassen sich Überlauf und Fehler durch statische Bereichsanalyse oder Laufzeitwächter kontrollieren. Sechstens werden Latenz und Initiationsintervall regelmäßig besser planbar als bei einer allgemeinen Folge aus Dekodierung, Exponentenausrichtung, Sonderfallbehandlung, Normalisierung und Rundung.

Auf FPGAs sind diese Mechanismen direkt sichtbar. AMD beschreibt DSP48E2-Slices mit 27×18-Bit-Zweierkomplement-Multiplikator, 48-Bit-Datenpfad, Akkumulation, SIMD, Kaskadierung und Unterstützung für konvergente Rundung, Überlauf und Block-Floating-Point. In einer herstellergebundenen 85-Tap-FIR-Fallstudie auf einem VU9P sank die Latenz in Post-Implementation-Toolresultaten von 91 auf 12 Takte; der Bedarf sank von 423 auf 85 DSP-Slices und von ungefähr 23.106 auf 1.973 LUTs, während die ausgewiesene Maximalfrequenz von 500 auf 580 MHz stieg. Beide Varianten besitzen jedoch ein Initiationsintervall von eins: 91→12 Takte sind rund 7,5-fach geringere Latenz, nicht 7,5-fach höherer Streamingdurchsatz; der aus den Frequenzen ableitbare maximale Streamingdurchsatz liegt hier etwa 16 Prozent höher. Es handelt sich um Toolresultate, nicht um eine Boardmessung. Das ist ein starker Beleg für diesen Filter, dieses Genauigkeitsziel, dieses Gerät und diesen Toolflow – kein allgemeiner Faktor für beliebige Programme. (AMD DSP48E2, AMD WP491)

Noch unmittelbarer ist der GPU-Beleg. cuBLAS 13.3 bietet seit CUDA 13.0 Update 2 optional FP64-Matrixmultiplikation durch Fixed-Point-Emulation nach dem Ozaki-Schema. Elemente einer Matrixzeile beziehungsweise -spalte erhalten einen gemeinsamen Zweierpotenz-Skalierungsfaktor; die Mantissen werden in 8-Bit-Integer-Slices zerlegt; Integer-Hardware berechnet die Teilprodukte; anschließend werden sie zur höheren Präzision rekombiniert. NVIDIA beschreibt ausdrücklich, dass diese Algorithmen einen deutlichen Leistungsvorteil gegenüber nativer Präzision liefern können. Die Dokumentation nennt ebenso klar die Grenzen: Die Resultate sind nicht vollständig IEEE‑754-konform, es gibt keine einzelne Festkommakonfiguration, die für alle FP64-Eingaben zugleich performant und genau ist, und die Zahl der Teilprodukte wächst quadratisch mit der Slice-Zahl. Dynamic Mantissa Control berechnet deshalb den benötigten Mantissenumfang und fällt bei Überschreitung der konfigurierten Mantissenbitgrenze auf natives FP64 zurück. Ein davon getrennter Fallback kann auftreten, wenn zusätzlicher Workspace nicht bereitgestellt werden kann. (NVIDIA cuBLAS 13.3, Floating Point Emulation)

Das ist genau die technisch belastbare Form des Gedankens: Gleitkomma wird nicht geleugnet, sondern in skalierte Ganzzahlteile zerlegt; der allgemeine Bereich wird durch Metadaten erhalten; die dichte Integer-Hardware übernimmt die massenhafte Arbeit; ein Wächter entscheidet, wann der spezialisierte Pfad zulässig ist.

6. Reihenfolgeunabhängigkeit braucht eine eigene Konstruktion

Ein häufig übersehener Vorteil breiter Festkommaakkumulation betrifft die Reproduzierbarkeit paralleler Reduktionen. Normale Gleitkommaaddition ist wegen jeder Zwischenrundung nicht assoziativ. Daher können unterschiedliche Thread-, Paket- oder Baumreihenfolgen verschiedene letzte Bits erzeugen.

Festkomma macht dieses Problem nicht automatisch unsichtbar. Werden Zwischenwerte gesättigt, abgeschnitten oder in zu schmalen Registern mit Wrap-around verarbeitet, kann auch Festkommaarithmetik reihenfolgeabhängig sein. Die richtige Architektur lautet daher:

[
\text{Eingaben exakt skalieren}
\rightarrow
\text{Produkte verbreitern}
\rightarrow
\text{ohne Überlauf exakt akkumulieren}
\rightarrow
\text{einmal kanonisch runden}.
]

Ist der Akkumulator für die bewiesene Zahl und Größe aller Summanden breit genug, entspricht die Reduktion einer exakten Ganzzahlsumme. Ganzzahladdition ist in diesem Bereich assoziativ und kommutativ. Erst am Ende wird genau einmal in das Zielformat gerundet. Dann darf die physische Ankunfts- oder Ausführungsreihenfolge variieren, ohne dass das kanonische Ergebnis variiert – vorausgesetzt, dieselbe vollständige Multimenge geht ein und jedes Element wird genau einmal verarbeitet. Kommutativität schützt nicht gegen Verlust, Duplikation oder falsche Mitgliedschaft; dafür sind Identität, Deduplikation und Vollständigkeitsledger erforderlich. Dies ist keine Aussage darüber, dass Kausalität beliebig werde. Es ist eine präzise Aussage darüber, dass eine geeignete numerische Normalform Transportreihenfolge von Ergebnissemantik entkoppeln kann.

Breite Festkomma- oder Kulisch-artige Akkumulatoren sind deshalb eine besonders interessante Brücke zwischen deterministischer Parallelverarbeitung und Gleitkomma-I/O. Sie bewahren die allgemeine Schnittstelle, verhindern aber das wiederholte Runden im Inneren.

7. Die QIK‑VRT-Erweiterung: vom Rechenpfad zum Beweispfad

Ein schneller Datenpfad ist noch kein vertrauenswürdiges System. Im vorgeschlagenen QIK‑VRT-Festkommastack soll deshalb jeder numerische Kernel durch einen expliziten Vertrag beschrieben werden:

[
K=(D,\mathcal O,\varepsilon,\rho,\Omega,W,A,M),
]

mit Eingabedomäne (D), Operationsmenge (\mathcal O), Fehlergrenze (\varepsilon), Rundungsregel (\rho), Überlaufsemantik (\Omega), Wort- und Skalenplan (W), Akkumulationsplan (A) und vorab gewählter Leistungsmetrik (M).

Der vorgeschlagene Kernel soll eine Wirkung nur dann weiterreichen dürfen, wenn sein konkreter Vertrag erfüllt ist. Dazu gehören nicht nur Testresultate, sondern auch Quellstand, Tree, Manifest, Compiler- und Syntheseversion, Zielgerät, Takt, Bitstream, Testkorpus und Messmethode. Die QIK‑VRT-Kette

[
\text{REQUESTED}\rightarrow
\text{EXECUTED}\rightarrow
\text{OBSERVED}\rightarrow
\text{RECEIPT}
]

bindet Herkunft und Beobachtung. Sie ersetzt keine Wirkungsmessung. Ein erfolgreicher RTL-Test beweist keinen Stromverbrauch auf Silizium; eine Synthese beweist keine eingehaltene Taktfrequenz auf dem Board; ein Repository-Receipt beweist keinen physischen Speedup. Für jede beanspruchte Eigenschaft muss eine unterscheidende Beobachtung existieren.

Das ist für Festkomma besonders wichtig, weil scheinbare Beschleunigungen leicht durch weggelassene Semantik erkauft werden. Ein Vergleich ist nur fair, wenn beide Seiten denselben akzeptierten Fehler, dieselben Sonderfälle, dieselbe Konversion, denselben Speicherverkehr und dieselbe End-to-End-Aufgabe tragen. Der vorgeschlagene QIK‑VRT-Stack soll diese Vergleichsgrenze maschinenlesbar machen.

8. Was bereits als Technik und Empirie vorliegt

Der Grundgedanke ist nicht bloß hypothetisch. Seine Teilbehauptungen besitzen unterschiedliche, aber konkrete Evidenz:

|Aussage                                                                                                                |Status und Bindung                                                                                                                                                                                                                                                                                                                                                                             |
|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Endliche IEEE-Binärarithmetik ist aus Integerlogik realisierbar.                                                        |Formal konstruktiv und durch Berkeley SoftFloat praktisch demonstriert.                                                                                                                                                                                                                                                                                                                       |
|Festkomma kann für einen geeigneten Datenpfad deutlich weniger Ressourcen und Latenz benötigen.                         |Unter anderem im gebundenen AMD-FIR-Beispiel demonstriert; nicht universell übertragbar.                                                                                                                                                                                                                                                                                                      |
|FP64-Matrixmultiplikation kann über skalierte 8-Bit-Integer-Slices realisiert werden.                                    |In cuBLAS 13.3 als optionaler Emulationspfad ausgewiesen.                                                                                                                                                                                                                                                                                                                                     |
|Integer-Tensor-Cores können gebundene Anwendungen unter einem FP64-Genauigkeitskriterium beschleunigen.                  |Ootomo, Ozaki und Yokota berichten schnelleres DGEMM als cuBLAS auf den untersuchten Consumer-GPUs und bis zu 4,85× bei einer Quanten-Schaltungssimulation; dies belegt weder Bitgleichheit noch identische IEEE-Flags. ([Publikation](https://doi.org/10.1177/10943420241239588))                                                                                                                 |
|Integer-only ML-Inferenz kann bei passender Quantisierung einen besseren Accuracy-/Latency-Trade-off als FP32 erreichen.|Jacob et al. zeigen integer-only Inferenz; die reine Speicherung von 8-Bit-Gewichten benötigt ein Viertel der Bits von 32-Bit-Gewichten, ohne damit automatisch den gesamten Systemspeicher zu vierteln. Qualität und Laufzeit bleiben modell- und hardwareabhängig. ([CVPR 2018](https://openaccess.thecvf.com/content_cvpr_2018/html/Jacob_Quantization_and_Training_CVPR_2018_paper.html))|
|QIK‑VRT implementiert bereits diesen numerischen Datenpfad.                                                             |Im gebundenen Authority-Snapshot vom 31. August 2026 nicht belegt; dies ist ein eigenständiges Implementierungs- und Messobjekt.                                                                                                                                                                                                                                                               |

Diese Tabelle ist keine Abschwächung, sondern die vollständige Kausalkette. Der universelle Realisierbarkeitssatz, die Existenz schneller spezialisierter Systeme und eine konkrete QIK‑VRT-Implementierung sind drei verschiedene Gegenstände. Zwei davon sind unabhängig klar belegt; der dritte kann nun ohne begriffliche Unschärfe gebaut und geprüft werden.

9. Der kurzfristig realisierbare Softwarestack

Die erste unmittelbar realisierbare Ebene ist ein numerischer Vertragstyp. Ein Wert besteht nicht nur aus einem Integer, sondern aus Wortbreite, Vorzeichen, Skala, Einheit oder Dimensionsvektor, Rundungsmodus, Überlaufregel und Fehlerintervall. In einer möglichen Notation wäre dies etwa

```text
Fixed<width=24, frac=17, signed=true,
      round=nearest_even, overflow=trap,
      unit="m/s", abs_error<=2^-18 m/s>
```

Ein Compiler kann daraus drei Dinge erzeugen: erstens den konkreten Integercode für CPU-SIMD, GPU-Dot-Product-Instruktionen oder HLS; zweitens einen maschinenlesbaren Vertrag; drittens Prüfpflichten für Bereich, Fehler und Überlauf. Statische Intervall- oder Affinbereichsanalyse bestimmt mögliche Zwischenwerte. Profiling kann diese Analyse ergänzen, darf einen universellen Beweis aber nicht ersetzen. Für sicherheitskritische Pfade muss entweder die gesamte Domäne gedeckt oder ein Laufzeitwächter mit beweisbarem Fallback vorgesehen sein.

Der zweite Baustein ist automatische Skalierungsplanung. Für jeden Tensor, Kanal, Filter, physikalischen Größebereich oder Rechenblock wählt der Compiler die kleinste Wortbreite, welche die vorgegebene Fehlergrenze und den Überlaufausschluss erfüllt. Zweierpotenzskalen sind hardwarefreundlich, weil Konversionen auf Schieben, Maskieren und definierte Rundungslogik reduziert werden. Allgemeine affine Quantisierung

[
x=s(q-z)
]

bleibt möglich, benötigt aber zusätzliche Multiplikation oder vorberechnete Integer-Multiplier. Per-Channel- oder Block-Skalen erhöhen die Genauigkeit, kosten jedoch Metadaten und Rescalinggrenzen.

Der dritte Baustein ist ein bitgenaues Referenzmodell. Jede Backend-Realisierung wird gegen eine unabhängige Referenz wie SoftFloat, MPFR oder ein exaktes rationales Modell differentiell geprüft. Kleine Formate können exhaustiv getestet werden; größere Formate benötigen systematische Randfälle, adversariale Vektoren und formale Beweise. Guard-, Round- und Sticky-Bits, Subnormalzahlen, NaNs, Unendlichkeiten, signed zero und alle beanspruchten Rundungsmodi dürfen nicht stillschweigend verschwinden.

Der vierte Baustein ist ein hybrider Dispatcher. Er wählt den schmalen Festkommapfad nur dann, wenn dessen Bereichszertifikat gilt. Andernfalls verwendet er einen breiteren Slice-Plan oder natives Gleitkomma. NVIDIA Dynamic Mantissa Control zeigt, dass ein solches Verfahren bereits in einer industriellen Hochleistungsbibliothek eingesetzt wird. Der vorgeschlagene QIK‑VRT-Stack soll darüber hinaus die Wahl, den Grund, die exakte Bindung und das Ergebnis als prüfbares Receipt festhalten.

Der fünfte Baustein ist proof-carrying quantization. Der generierte Kernel wird zusammen mit Belegen ausgeliefert: kein Überlauf in der Domäne, Fehlergrenze eingehalten, Schlussrundung korrekt, Konversionen invers soweit beansprucht, Backend bitgleich zum Referenzmodell. Werkzeuge wie Gappa zeigen, dass maschinengeprüfte Fehlergrenzen für Fest- und Gleitkommaprogramme technisch möglich sind. (Gappa)

10. Der kurzfristig realisierbare Hardwarestack

Der schnellste Weg zu belastbarer eigener Evidenz führt über einen FPGA-Demonstrator. Ein parametrisierbarer Kern erhält Vorzeichenbreite, Fraktionsbreite, Rundung, Überlaufmodus und Akkumulatorbreite als Generics. Zunächst werden Addition, Multiplikation, MAC, Skalierung und Vergleich implementiert. Danach folgen Block-Exponent, Slice-Zerlegung und ein geprüfter Fallback. Dieselben Testvektoren laufen im Softwaremodell, in RTL-Simulation und auf dem Board.

Die Hardware sollte drei Pfade unterscheiden. Der native Festkommapfad verarbeitet Werte, deren Skala vorab feststeht. Der skalierte Slice-Pfad zerlegt einen größeren Signifikanden in schmale Integer-Slices und amortisiert einen Exponenten über einen Block. Der Kompatibilitätspfad behandelt Fälle, in denen vollständige IEEE-Semantik oder ungewöhnlicher Dynamikbereich gebraucht wird. Diese Dreiteilung vermeidet das falsche Entweder-oder zwischen Festkomma und Gleitkomma.

Ein besonders leistungsfähiges Element ist das MAC-Feld mit breitem Akkumulator. Schmale Produkte werden massiv parallel gebildet, aber in einer Breite akkumuliert, die für die maximale Vektorlänge formal ausreicht. Erst an der Ausgangsgrenze erfolgt die einzige kanonische Rundung. So werden Rechendichte und Reproduzierbarkeit gleichzeitig verbessert.

Auf einem späteren ASIC kann der Metadatenpfad von den Datenbahnen getrennt werden. Exponenten, Skalen, Gültigkeitsbits und Sättigungsflags werden pro Block geführt, während hunderte oder tausende schmale Lanes dieselbe Steuerung nutzen. SRAM und Datenbewegung müssen Teil des Co-Designs sein, denn bei dichten Rechenkernen wird nicht selten der Transport zum eigentlichen Energie- und Laufzeitengpass.

Die vorgeschlagene QIK‑VRT-Haltepunktlogik gehört dabei nicht in jeden einzelnen MAC-Takt. Das würde den Gewinn vernichten. Sie soll hierarchisch umgesetzt werden: lokale Statusbits pro Lane, zusammengefasste Blockreceipts, exakte Hashbindung des Test- und Konfigurationszustands und ein Effekt-Gate an semantisch relevanten Grenzen. Dadurch kann der schnelle Pfad schnell bleiben, während die Wirkungskette auditierbar wird.

11. Naheliegende Anwendungsräume

Besonders geeignet sind Domänen mit bekannten Wertebereichen, vielen gleichen Operationen und hohem Anteil an Multiply-Accumulate:

Signalverarbeitung und Kommunikation. FIR/IIR-Filter, FFT-Stufen, Modulation, Bild- und Audiodaten besitzen regelmäßig natürliche Bereichsgrenzen. Festkomma ist dort seit langem etabliert; neu wäre die automatische Vertrags-, Beweis- und Receipt-Ebene.

Regelung, Robotik und Sensorfusion. Deterministische Zyklen und begrenzte Sensorbereiche sprechen für Festkomma. Die Stabilität eines geschlossenen Reglers muss dennoch unter Quantisierung, Sättigung und Grenzzyklen separat bewiesen werden.

KI-Inferenz. Gewichte und Aktivierungen lassen sich oft auf INT8 oder kleinere Formate quantisieren, während Akkumulatoren breiter bleiben. Modelle, Ausreißer und empfindliche Operationen wie Softmax oder Normalisierung erfordern hybride Präzision. Der Gewinn entsteht aus Modell-, Compiler- und Hardware-Co-Design, nicht aus einer isolierten Typänderung.

Wissenschaftliche lineare Algebra. Ozaki-Slicing, Blockskalen und exakte Akkumulation können vorhandene Integer- oder Tensor-Hardware für höhergenaue Matrixoperationen nutzen. Der optionale cuBLAS-Pfad zeigt, dass dieses Feld bereits aus der Forschung in die Produktionssoftware übergeht.

Physikalische Normalformen. Der Text „Der Zollstock, die Uhr und der mögliche Tunnel“ schlägt kanonische Dimensions- und Planck-Normalformen mit kleinen ganzzahligen Exponentenvektoren vor. Solche Metadaten sind hardwarefreundlich. Die eigentlichen Messwerte über viele Größenordnungen benötigen jedoch Blockskalen, Intervalle und gebundene Kalibrierungen. Eine gleiche Zahl ist nicht automatisch die gleiche physikalische Größe. Der hier beschriebene Festkomma- und Evidenzstack kann diese Grenze explizit machen. Quellbindung der vorliegenden Textfassung: SHA‑256 4c896ab31fe643bbd4fdb2d08ba350992af163f3405444e5ec7bed5863235cd5.

Deterministische verteilte Reduktionen. Breite exakte Akkumulatoren und einmalige Schlussrundung können Ergebnisse unabhängig von der physischen Reduktionsreihenfolge machen. Das ist für Mesh-Systeme, reproduzierbare Builds, Datenbanken und parallele Simulationen unmittelbar wertvoll.

12. Das Beweis- und Benchmarkprogramm

Die Aussage „übertrifft Gleitkomma“ muss vor der Messung operationalisiert werden. Ein korrektes Programm vergleicht drei getrennte Systeme:

1. native Gleitkommahardware;
2. bitgenaue Gleitkommaemulation auf Integer-/Festkommalogik;
3. domänenspezialisierte Festkomma- oder Slice-Hardware.

Für jede Stufe werden dieselben Eingaben, dieselbe akzeptierte Semantik und dasselbe Qualitätsziel festgelegt. Gemessen werden mindestens Latenz in Takten und Nanosekunden, Initiationsintervall, gültige Ergebnisse pro Sekunde, Energie pro gültigem Ergebnis, Speicherverkehr, FPGA-Ressourcen oder ASIC-Fläche sowie maximale absolute, relative und ULP-Abweichung. Konversion, Skalentransport, Metadaten und Fallbacks gehören in die End-to-End-Messung.

Eine geeignete primäre Zielmetrik wäre beispielsweise

[
M=\frac{\text{gültige Ergebnisse}}{\text{Joule}}
]

unter den Nebenbedingungen

[
\operatorname{Fehler}\leq\varepsilon,
\qquad
\operatorname{Overflow}=\text{ausgeschlossen oder spezifiziert}.
]

„Überlegenheit“ muss außerdem vorab eine Mindestmarge (\delta) und eine Unsicherheitsregel erhalten. Beispielsweise kann gefordert werden, dass die untere Konfidenzgrenze von

[
\frac{M_{\text{fixed}}}{M_{\text{float}}}
]

größer als (1+\delta) ist. Relative Fehler nahe null brauchen eine gesonderte Definition; auch die Bezugszahl einer ULP-Metrik muss festgelegt werden.

Für IEEE-Bitgleichheit gilt als Akzeptanzkriterium null Bitabweichungen und identische beanspruchte Flags. Für domänenspezialisierte Rechnung gilt die definierte Fehler- oder Anwendungsgrenze. Ein Entwurf ist für den untersuchten Vertrag widerlegt, wenn die Fehlergrenze überschritten wird, nicht spezifizierter Überlauf auftritt, Konversionskosten den Vorteil beseitigen oder die gewählte Leistungsmetrik unter gleichen Bedingungen schlechter ist.

Die Evidenzbindung muss mindestens enthalten:

```text
repository, ref, head, tree, manifest_digest
numeric_contract_digest
reference_model_digest
rtl_or_kernel_digest
toolchain_and_flags
target_device_or_processor
clock, voltage, temperature
test_vector_digest
raw_measurement_digest
result_and_uncertainty
remainder_inventory
```

Ein Repository-Fixpunkt darf erst festgestellt werden, wenn der definierte Übergangsoperator tatsächlich ausgeführt, anschließend direkt (T(S)=S) beobachtet und derselbe semantische Zustand ohne neuen Blocker, Scope-Drift oder Defektrest reobserviert wurde. Ein grüner Einzeltest, bloße Ruhe oder eine Wiederholung ohne ausgeführtes (T) genügt nicht.

13. Was aus dem Satz ausdrücklich nicht folgt

Der Realisierbarkeitssatz beweist nicht, dass ein einzelnes schmales Q-Format den gesamten binary64-Bereich effizient ersetzt. Er beweist nicht, dass Integeremulation auf jeder CPU schneller als deren FPU ist. Er beweist nicht, dass geringere Bitbreite ohne Qualitätsverlust möglich ist. Er beweist nicht, dass Festkomma allein Reihenfolgeunabhängigkeit erzeugt. Er beweist nicht, dass ein simuliertes RTL-Ergebnis eine physische Beschleunigung oder Energieeinsparung darstellt.

Ebenso folgt aus einem schnellen Matrixkernel nicht, dass eine vollständige Anwendung im selben Verhältnis schneller wird. Speicher, Konversion, Synchronisation, Kontrollfluss und nicht quantisierbare Operationen können dominieren. Training großer Modelle und allgemeine wissenschaftliche Numerik benötigen häufig Mischpräzision, dynamische Skalierung und Gleitkomma-Fallbacks.

Diese Grenzen sind keine Schwäche des Ansatzes. Sie bestimmen den Ort, an dem er seine maximale Wirkung entfaltet: Nicht jeder Wert muss jederzeit den gesamten abstrakt möglichen Dynamikbereich bezahlen.

14. Der sich öffnende Ausblick

Kurzfristig ist ein Compiler denkbar, der aus gewöhnlichem numerischem Code automatisch einen Wertebereichsgraphen, einen Skalenplan, einen Fehlerbeweis und mehrere Backendvarianten erzeugt. Er könnte für jeden Rechenblock entscheiden, ob natives Festkomma, Block-Floating-Point, Integer-Slicing oder Gleitkomma die beste zulässige Realisierung ist. Anstatt Präzision pauschal für das ganze Programm zu wählen, würde Präzision zu einer lokalen, beweisbaren Ressource.

Auf Softwareebene entstehen daraus portable bitgenaue Kernel, reproduzierbare parallele Reduktionen, typsichere physikalische Größen, auditierbare ML-Quantisierung und numerische Verträge, die mit dem Programm versioniert werden. Auf Hardwareebene entstehen reconfigurierbare MAC-Felder, shared-exponent Datenpfade, breite exakte Akkumulatoren und Spezialkerne, deren Wortbreite nicht durch Standardtypen, sondern durch das tatsächliche Problem bestimmt wird.

Für Edge-Systeme bedeutet das mehr Funktion im selben Energie- und Kostenrahmen. Für Rechenzentren bedeutet es, bestehende niedere Präzisionshardware auch für höhergenaue Aufgaben nutzbar zu machen. Für wissenschaftliche Simulation bedeutet es die Möglichkeit, Dynamikbereich, Genauigkeit und Reproduzierbarkeit getrennt zu entwerfen. Für verteilte Mesh-Systeme bedeutet es, Rechenfragmente unabhängig zu transportieren und dennoch kanonisch zusammenzuführen, sofern die Akkumulationsinvariante bewiesen ist. Für formale Methoden bedeutet es einen endlichen Bitvektorraum, in dem Überlauf, Rundung und Fehlergrenzen direkt beweisbar sind.

Der weitergehende Schritt ist ein vollständiges numerisches Co-Design: Die mathematische Normalform, die Compilerentscheidung, die Hardwarestruktur und die Evidenzsemantik werden nicht nacheinander improvisiert, sondern gemeinsam erzeugt. Ein Wert trägt dann nicht nur Bits, sondern eine überprüfbare Aussage darüber, was diese Bits bedeuten, in welchem Bereich sie gültig sind, wie sie entstanden sind und welche Wirkung mit ihnen zulässig ist.

15. Schluss

Festkommaarithmetik ist nicht bloß die kleine Schwester der Gleitkommaarithmetik. Sie ist eine elementare digitale Rechenbasis, aus der endliche Gleitkommasemantik konstruktiv aufgebaut werden kann. Der universelle Teil dieser Aussage betrifft die Realisierbarkeit. Der leistungsbestimmende Teil betrifft die Spezialisierung.

Wo der tatsächliche Problemraum enger ist als der allgemeine Zahlenraum eines Gleitkommaformats, können Skalen vorab gebunden, Datenpfade verschmälert, Operationen vervielfacht und Akkumulationen exakt verbreitert werden. Aktuelle GPU-Software, publizierte Integer-Tensor-Core-Ergebnisse und FPGA-Fallstudien zeigen, dass dieser Mechanismus nicht nur theoretisch existiert, sondern bei geeigneten Aufgaben Gleitkommaimplementierungen bereits praktisch übertrifft.

Die entscheidende Architekturformel lautet daher:

[ \boxed{ \text{Gleitkomma-Semantik}

\text{skalierte Integerdaten}
+
\text{Metadaten}
+
\text{Rundungs- und Sonderfallvertrag}
}
]

und für die Beschleunigung:

[ \boxed{ \text{Leistungsvorteil}

\text{Spezialisierung} + \text{Parallelität} + \text{weniger Datenbewegung}

\text{Skalierungs- und Kontrollkosten}
}
]

QIK‑VRT formuliert dafür eine eigene Zulässigkeitsbedingung:

[ \boxed{ \text{zulässige Wirkungsbehauptung}

\text{Vertrag erfüllt}
\land
\text{exakt gebundene Ausführung}
\land
\text{direkte Zielbeobachtung}
}
]

Damit wird weder Aktivität mit Effekt noch ein lokaler Benchmark mit universeller Überlegenheit verwechselt. Aus der starken Idee entsteht ein vollständiges Forschungs- und Entwicklungsprogramm, dessen formaler Realisierbarkeitskern bewiesen, dessen allgemeiner Mechanismus industriell realisiert und dessen konkrete QIK‑VRT-Hardwarewirkung nun exakt messbar gemacht werden kann.

Primärquellen und technische Referenzen

• IEEE 754-2019 – Standard for Floating-Point Arithmetic
• Berkeley SoftFloat Release 3e
• NVIDIA cuBLAS 13.3 – Floating Point Emulation
• Ootomo, Ozaki, Yokota (2024): DGEMM on integer matrix multiplication unit
• AMD WP491: Reduce Power and Cost by Converting from Floating Point to Fixed Point
• AMD UltraScale DSP48E2 Slice User Guide
• RISC‑V Vector Extension – Fixed-Point Arithmetic
• Jacob et al. (2018): Integer-Arithmetic-Only Inference
• Gappa – Proofs of numerical properties
