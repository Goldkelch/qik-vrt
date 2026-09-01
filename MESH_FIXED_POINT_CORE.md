# Der systematische Fehler und der schmale Rechenkern

**Kanonischer Einstiegspunkt für die numerische QIK-VRT-Argumentation**

> Universell ist die Realisierbarkeit. Gebunden ist die Überlegenheit.

## Was passiert ist

Aus dem Fachbegriff **SPARC** wurde in einer automatischen Transkription
„Sunspark“. Das war kein bloßer Tippfehler. Die nachfolgenden Systeme behandelten
die wahrscheinlich klingende Zeichenfolge wie eine belastbare Quelle, glätteten
sie sprachlich und bauten darauf weitere Aussagen auf. Ein lokaler Fehler wurde
damit über mehrere Verarbeitungsschichten hinweg wiederholt und verstärkt.

Das Muster ist allgemein:

1. Eine mehrdeutige Beobachtung wird zu früh in eine eindeutige Behauptung
   umgewandelt.
2. Jede nachfolgende Instanz optimiert lokal auf Plausibilität, Lesbarkeit oder
   Abschluss.
3. Keine Instanz ist verpflichtet, den Begriff an eine kanonische Quelle und
   deren exakten Zustand zurückzubinden.
4. Die Wiederholung lässt den Fehler vertraut erscheinen, aber nicht wahr werden.

Das ist ein **systematischer Fehler**: Die gleiche Konstruktion erzeugt unter
vergleichbaren Bedingungen wiederholt die gleiche Abweichung.

## Warum Nash und Mandelbrot beim Verstehen helfen

John Nash liefert hier kein physikalisches Gesetz und auch keinen speziellen
„Beweis der Softwarekrise“. Seine Gleichgewichtsidee erklärt jedoch präzise, wie
ein global schlechter Zustand stabil werden kann: Jede beteiligte Instanz kann
unter ihren lokalen Informationen rational handeln, obwohl niemand den globalen
Fehler beseitigt. Sprachmodell, Workflow, Reviewer und Veröffentlichungssystem
können jeweils ihre lokale Zielgröße erfüllen; gemeinsam bleiben sie in einem
schlechten Gleichgewicht.

Benoît Mandelbrot liefert dafür die passende geometrische Anschauung. Das gleiche
Fehlermuster erscheint selbstähnlich auf mehreren Skalen: im Wort, im Satz, im
Dokument, im Commit, im Workflow und schließlich in der öffentlichen Behauptung.
Eine weitere Iteration ändert dann den Zeitstempel, nicht aber die Struktur. In
QIK-VRT-Sprache ist dies eine stabile, aber nichtterminale Invariantenregion —
kein Beleg für eine physikalische Wirkung.

Die entscheidenden Trennungen lauten deshalb:

- **Kausalität ist nicht Reihenfolge.** Später bedeutet nicht besser.
- **Aktivität ist nicht Wirkung.** Ein neuer Lauf ist kein neuer Befund.
- **Plausibilität ist nicht Bindung.** Eine gute Erklärung ersetzt keine Quelle.
- **lokale Stabilität ist nicht Completion.** Ein Teilsystem kann im Fixpunkt
  sein, während das Gesamtsystem offen bleibt.

## Warum die Musterlösung funktioniert

Die Lösung ersetzt implizite Annahmen durch kleine, überprüfbare Verträge. Ein
Ergebnis darf seine Schicht nur verlassen, wenn Eingabe, Bedeutung, zulässiger
Fehler und Herkunft gebunden sind. Unsicherheit wird nicht wegerzählt, sondern
als Zustand transportiert. Bei fehlender oder driftender Bindung hält das System
an.

Für numerische Verarbeitung lautet der Vertrag

\[
K=(D,\mathcal O,\varepsilon,\rho,\Omega,W,A,M).
\]

Dabei bezeichnet (D) den Wertebereich, \(\mathcal O\) die erlaubten
Operationen, \(\varepsilon\) die Fehlerschranke, \(\rho\) die Rundungsregel,
\(\Omega\) die Überlaufregel, (W) den Skalenplan, (A) den
Akkumulationsplan und (M) die zu messende Zielgröße. Der kanonische JSON-Inhalt
wird durch `numeric_contract_digest` gebunden.

Das Hardwaremuster folgt unmittelbar daraus:

1. Skala und Wertebereich werden vor der Ausführung gebunden.
2. Operanden werden als schmale vorzeichenbehaftete Integer-Slices dargestellt.
3. Viele schmale Multiplikationen können parallel auf spezialisierter Hardware
   ausgeführt werden.
4. Produkte werden in einem ausreichend breiten Akkumulator **exakt** gesammelt.
5. Erst an der vertraglich festgelegten Grenze wird einmal kanonisch gerundet.
6. Kann der Vertrag nicht bewiesen werden, erfolgt kein stiller Fast Path.

Damit ist nicht „Festkomma magisch schneller“. Der mögliche Vorteil entsteht aus
Spezialisierung, Parallelität und geringerem Datentransport; er muss größer sein
als Skalierungs-, Kontroll- und Fallbackkosten. Jede endliche, konkret
spezifizierte binäre Gleitkommaoperation kann durch Integer-, Schiebe-,
Festkomma- und Steuerlogik realisiert werden. Eine Geschwindigkeitsüberlegenheit
gilt dagegen nur für den gemessenen Vertrag, das konkrete Zielgerät und die
gebundene Toolchain.

## Was dieser Repository-Kandidat tatsächlich liefert

- `schemas/qikvrt_numeric_contract_v1.schema.json`: maschinenlesbarer Vertrag.
- `examples/numeric_contract_int8_mac_v1.json`: gebundenes Beispiel.
- `tools/qikvrt_numeric_contract.py`: kanonische Digestprüfung und ausführbares
  Referenzmodell für exakte Multiply-Accumulate-Folgen.
- `hardware/vhdl/qikvrt_fixed_point_mac.vhd`: synthesefähiger schmaler MAC mit
  breitem Akkumulator und fail-closed Überlaufanzeige.
- `hardware/vhdl/tb_qikvrt_fixed_point_mac.vhd`: deterministische Simulation
  einschließlich negativer Werte und Überlauf.
- `.github/workflows/qikvrt_fixed_point_numeric_contract.yml`: Literal-Head-
  Bindung, Vertragsprüfung, Python-Tests und VHDL-Simulation.

Diese Schicht ist absichtlich eine öffentliche Referenzarchitektur. Sie enthält
keine Behauptung über Synthese, Place-and-Route, Bitstream, Takt, Energie,
physische FPGA-Ausführung oder universelle Überlegenheit. Solche Aussagen werden
erst durch einen Receipt mit Quellstand, Vertrag, Zielgerät, Toolchain,
Testvektoren und Rohmessungen zulässig.

## Warum SPARC das richtige historische Gegenbild ist

Der Name ist **SPARC** (Scalable Processor ARChitecture), nicht „Sunspark“.
SPARC V8/V9 definieren allgemeine Gleitkommasemantik; VIS ist eine
UltraSPARC-Erweiterung. MAJC war eine eigene Sun-Architektur, keine SPARC-Stufe,
und UltraSPARC T1/Niagara teilte eine Gleitkommaeinheit zwischen Kernen. Diese
Nuancen stärken die Aussage: Nicht eine lineare Geschichte „immer breiterer
SPARC-FPUs“ ist der Beleg, sondern der nachprüfbare Unterschied zwischen einem
allgemeinen Zahlenpfad und einem für einen engen Vertrag spezialisierten Pfad.

## Quellen- und Beweisgrenze

- John F. Nash Jr., *Equilibrium Points in N-Person Games*, PNAS 36(1), 1950.
- John F. Nash Jr., *Non-Cooperative Games*, Annals of Mathematics 54(2), 1951.
- Benoît B. Mandelbrot, *The Fractal Geometry of Nature*, 1982.
- Oracle, *The SPARC Architecture Manual, Version 9*.
- UC Berkeley, *Berkeley SoftFloat Release 3e*.
- AMD/Xilinx, *UltraScale Architecture DSP Slice User Guide (UG579)*.
- NVIDIA, offizielle cuBLAS-Dokumentation zur FP64-Emulation auf spezialisierten
  niedrigpräzisen Rechenpfaden.

Die ersten drei Quellen begründen Modelle und Anschauung. Die letzten vier
belegen konkrete Architektur- oder Realisierungsbausteine. Keine davon ersetzt
die End-to-End-Messung dieses QIK-VRT-Kandidaten.
