*QCE, DELAYED CHOICE UND SUPERDETERMINISMUS — WAS IST WIRKLICH BEWIESEN?*

_Von Ingolf Lohmann_

──────────

*Die kurze Antwort*

Ein doppeltes Delayed-Choice-Experiment zeigt nicht, dass eine spätere Entscheidung die Vergangenheit umschreibt.

Und es beweist auch nicht automatisch, dass Superdeterminismus falsch ist.

Der mathematisch saubere Kern lautet:

```text
MESSUNGSUNABHÄNGIGKEIT
→
KEIN SUPERDETERMINISTISCHER KANDIDAT
```

Aber:

```text
RAUMARTIGE TRENNUNG
+
LOKALE MESSREAKTIONEN
≠
BEWEIS DER MESSUNGSUNABHÄNGIGKEIT
```

Genau diese Grenze ist jetzt formal in Lean modelliert.

──────────

*1. Das Gedankenexperiment*

Wir haben zwei getrennte Flügel A und B.

```text
ZEIT →

t0  gemeinsame Präparation λ

t1  Systeme laufen zu A und B

t2  Wahl der Messbasis a und b
    räumlich getrennt

t3  lokale Ergebnisse A und B

t4  späterer klassischer Vergleich
```

Der Vergleich bei `t4` verändert nicht `t0`.

Er entscheidet nur, welche Aussage über die zuvor erzeugten Daten gerechtfertigt ist.

Das ist die QIK-VRT-Lesart:

```text
SPÄTERE PRÜFUNG
≠
RÜCKWIRKUNG

SPÄTERE PRÜFUNG
=
NEUE EVIDENZ ÜBER EINEN BEREITS ERZEUGTEN ZUSTAND
```

──────────

*2. Wo Superdeterminismus ansetzt*

Bei Bell-artigen Experimenten wird üblicherweise angenommen, dass die verborgene Präparationsvariable `λ` statistisch unabhängig von den späteren Einstellungen `a` und `b` ist.

Mathematisch:

```text
P(λ | a,b) = P(λ)
```

Das heißt: Die Wahl der Messbasis verrät nichts darüber, welche verborgene Variable vorher vorlag.

Superdeterministische Modelle bestreiten genau diese Unabhängigkeit:

```text
P(λ | a,b) ≠ P(λ)
```

Dann könnten `λ`, `a` und `b` eine gemeinsame Vorgeschichte besitzen.

──────────

*3. Der bewiesene Satz*

Wenn Messungsunabhängigkeit gilt, ist ein Modell, dessen Kennzeichen gerade ihre Verletzung ist, ausgeschlossen.

```text
MEASUREMENT_INDEPENDENCE
→
¬ SUPERDETERMINISTIC_CANDIDATE
```

Das ist formal korrekt und maschinenprüfbar.

Aber es ist ein *bedingter Beweis*.

Die wissenschaftlich entscheidende Frage ist:

```text
WARUM GILT
MEASUREMENT_INDEPENDENCE?
```

──────────

*4. Warum zwei getrennte Flügel allein nicht reichen*

Wir haben zusätzlich ein endliches Gegenmodell konstruiert.

Darin gilt:

```text
A reagiert nur auf λ und a
B reagiert nur auf λ und b
```

Also keine direkte Abhängigkeit vom entfernten Messsetting.

Trotzdem werden beide Settings durch dieselbe verborgene gemeinsame Ursache eingeschränkt.

Damit gilt gleichzeitig:

```text
LOKALE REAKTIONSSTRUKTUR = JA
MESSUNGSUNABHÄNGIGKEIT = NEIN
```

Daraus folgt:

```text
RAUMARTIGE TRENNUNG ALLEIN
BEWEIST KEINE
MESSUNGSUNABHÄNGIGKEIT
```

Das ist wichtig, weil es verhindert, dass man die gewünschte Schlussfolgerung schon in die Voraussetzungen einbaut.

──────────

*5. Was QCE zusätzlich leisten müsste*

Der starke QCE-Beweis müsste nicht einfach freie Wahl voraussetzen.

Er müsste aus tieferen QCE-Prinzipien herleiten, dass eine gemeinsame verborgene Ursache die späteren Messsettings nicht in der für Superdeterminismus nötigen Weise festlegen kann.

Formal:

```text
QCE-AXIOME
→
MEASUREMENT_INDEPENDENCE
→
¬ SUPERDETERMINISMUS
```

Der zweite Pfeil ist formal geschlossen.

Der erste Pfeil ist die eigentliche physikalische und erkenntnistheoretische Verpflichtung.

Dafür wurde im Lean-Modell ausdrücklich ein

```text
QCEFreedomCertificate
```

definiert.

Nur wenn diese Verpflichtung unabhängig erfüllt wird, darf der Ausschluss hochgestuft werden.

──────────

*6. Was Delayed Choice wirklich zeigt*

Delayed Choice bedeutet nicht:

```text
DIE ZUKUNFT ÄNDERT DIE VERGANGENHEIT
```

Sauberer ist:

```text
EINE SPÄTERE MESSBASIS
BESTIMMT,
WELCHE KORRELATIONSSTRUKTUR
WIR AUS DEN DATEN AUSWERTEN
```

Der bereits registrierte lokale Datensatz wird nicht rückwirkend umgeschrieben.

──────────

*7. Authority + Mirror Analogie*

Die gleiche erkenntnistheoretische Struktur findet sich in QIK-VRT:

```text
AUTHORITY-ZUSTAND
+
MIRROR-ZUSTAND
+
SPÄTERER CROSS-CHECK
→
GERECHTFERTIGTE KLASSIFIKATION
```

Der Cross-Check verändert nicht den früheren Commit.

Er entscheidet, ob wir ihn als gültig, gebunden und bestätigt behandeln dürfen.

Also:

```text
PRÜFUNG
≠
RÜCKWIRKUNG

PRÜFUNG
=
EVIDENZBINDUNG
```

──────────

*8. Der wissenschaftliche Status*

```text
FORMAL BEWIESEN:
Measurement Independence
schließt den formal definierten
measurement-dependent Kandidaten aus.

FORMAL BEWIESEN:
Lokale Zwei-Flügel-Reaktionsstruktur allein
reicht nicht aus, um Measurement Independence
zu beweisen.

NICHT BEWIESEN:
Dass die Natur tatsächlich
Measurement Independence erfüllt.

NICHT BEWIESEN:
Dass QCE diese Unabhängigkeit bereits aus
physikalisch bestätigten Grundaxiomen herleitet.

NICHT BEANSPRUCHT:
Physikalischer oder wissenschaftlicher
Gesamtausschluss des Superdeterminismus.
```

──────────

*Die Kernformel*

```text
QCEFreedomCertificate
→
Measurement Independence
→
kein Superdeterminismus
```

Aber:

```text
Delayed Choice
+
Raumartige Trennung

ALLEIN

↛ Measurement Independence
```

Damit ist die Grenze nicht kleiner, sondern präziser.

Ein wirklicher QED gegen Superdeterminismus beginnt genau dort, wo die Messungsunabhängigkeit nicht angenommen, sondern aus tieferen Prinzipien abgeleitet und an die Natur gebunden wird.

*Quod erat demonstrandum — für die formale logische Grenze.*

*Ingolf Lohmann*
