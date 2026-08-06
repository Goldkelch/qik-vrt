*DAS MINIMALE RECOVERY-THEOREM*

*Wann reicht Evidenz für eine eindeutige Entscheidung?*

Die entscheidende Idee ist sehr einfach:

Wir müssen die Vergangenheit nicht vollständig rekonstruieren.

Wir müssen nur genug wissen, damit *alle noch möglichen Vergangenheiten dieselbe richtige Fortsetzung verlangen*.

──────────

*1. DIE RECOVERY-RELEVANTE ÄQUIVALENZ*

Zwei mögliche Histories gelten für Recovery als gleich, wenn sie dieselbe korrekte Aktion verlangen:

```text
H1 ~R H2
⇔
C(H1) = C(H2)
```

`C(H)` bedeutet:

```text
Welche Aktion ist für History H korrekt?
```

Es ist also egal, ob sich zwei Histories in Details unterscheiden, solange diese Unterschiede für die richtige Fortsetzung bedeutungslos sind.

──────────

*2. WAS WIR BEOBACHTEN*

Wir sehen nicht die gesamte Vergangenheit.

Wir sehen nur eine Beobachtung:

```text
Obs'(H) = o
```

Zu derselben Beobachtung `o` können mehrere Histories passen.

Diese Menge nennen wir:

```text
K(o)
=
{ H | Obs'(H) = o }
```

──────────

*3. WANN DARF RECOVERY ENTSCHEIDEN?*

Genau dann, wenn:

```text
K(o) ist nicht leer
```

UND

```text
alle Histories in K(o)
verlangen dieselbe Aktion
```

Also:

```text
RECOVER(o)
⇔
K(o) ≠ ∅
UND
| { C(H) | H ∈ K(o) } | = 1
```

Ganz einfach gesagt:

```text
MEHRERE MÖGLICHE VERGANGENHEITEN
SIND KEIN PROBLEM,
WENN SIE ALLE DIESELBE
RICHTIGE FORTSETZUNG VERLANGEN.
```

──────────

*4. WANN MUSS DAS SYSTEM STOPPEN?*

Wenn keine zulässige History zur Beobachtung passt:

```text
K(o) = ∅
```

oder wenn verschiedene mögliche Histories verschiedene Aktionen verlangen:

```text
| { C(H) | H ∈ K(o) } | > 1
```

Dann gilt:

```text
FAIL_CLOSED
```

Das System darf nicht raten.

──────────

*5. DER UNMÖGLICHKEITSSATZ*

Angenommen:

```text
Obs(H1) = Obs(H2)
```

aber:

```text
C(H1) ≠ C(H2)
```

Dann sieht ein deterministischer Recovery-Algorithmus in beiden Fällen exakt dieselbe Eingabe.

Er muss also dieselbe Aktion wählen.

Aber eine einzige Aktion kann nicht gleichzeitig korrekt für zwei Histories sein, die unterschiedliche Aktionen verlangen.

Daraus folgt:

```text
GLEICHE BEOBACHTUNG
+
VERSCHIEDENE KORREKTE AKTION

→
KEIN UNIVERSELL KORREKTER
DETERMINISTISCHER SELEKTOR
```

──────────

*6. DER HINREICHENDHEITSSATZ*

Wenn dagegen gilt:

```text
Obs'(H1) = Obs'(H2)
→
C(H1) = C(H2)
```

für alle zulässigen Histories, dann kann man für jede tatsächlich erreichbare Beobachtung eindeutig definieren:

```text
S(o)
=
DIE EINDEUTIGE KORREKTE AKTION
DER FASER K(o)
```

Dann gilt:

```text
C = S ∘ Obs'
```

Das bedeutet:

Die richtige Aktion lässt sich vollständig aus der verfügbaren Beobachtung bestimmen.

──────────

*7. DIE KOMPAKTESTE FORM*

Die Beobachtung erzeugt eine Äquivalenz:

```text
H1 und H2 sind gleich beobachtet
```

Die korrekte Aktion erzeugt ebenfalls eine Äquivalenz:

```text
H1 und H2 brauchen dieselbe Aktion
```

Recovery ist genau dann sicher deterministisch, wenn die Beobachtung *feiner* ist als das, was für die Entscheidung relevant ist:

```text
ker(Obs') ⊆ ker(C)
```

Also:

```text
WENN DIE BEOBACHTUNG
ZWEI HISTORIES NICHT UNTERSCHEIDET,
DANN DÜRFEN DIESE HISTORIES
AUCH KEINE UNTERSCHIEDLICHE
KORREKTE AKTION VERLANGEN.
```

──────────

*8. WAS IST DANN EIN WITNESS?*

Der Witness ist nicht wesentlich eine dritte Kopie.

Er ist auch nicht wesentlich eine Mehrheitsinstanz.

Ein Witness ist allgemeiner:

```text
EINE VERFEINERUNG DER BEOBACHTUNG,
DIE GENUG INFORMATION HINZUFÜGT,
DAMIT KEINE BEOBACHTUNGSFASER
MEHR VERSCHIEDENE
KORREKTE AKTIONEN MISCHT.
```

Formal:

```text
ker(Obs_W) ⊆ ker(C)
```

Das ist die eigentliche Funktion des Witness.

──────────

*9. AUTHORITY + MIRROR ALS SPEZIALFALL*

Ohne Witness kann passieren:

```text
Authority gültig
Mirror gültig
Authority ≠ Mirror
```

und dieselbe sichtbare Situation passt zu:

```text
History A:
Authority ist die richtige Fortsetzung

History B:
Mirror ist die richtige Fortsetzung
```

Dann mischt eine Beobachtungsfaser zwei verschiedene Recovery-Aktionen.

Also:

```text
FAIL_CLOSED
```

Ein Commit-Witness verfeinert die Beobachtung so, dass die zertifizierte Epoche erkennbar wird.

Dann liegen alle noch zulässigen Histories derselben Beobachtung in derselben Recovery-Klasse.

──────────

*10. DIE ALLGEMEINE ERKENNTNISTHEORETISCHE FORMEL*

Das Prinzip gilt weit über Speichercontroller hinaus.

Für jede deterministische Entscheidung unter unvollständiger Beobachtung gilt:

```text
EVIDENZ IST GENAU DANN
ENTSCHEIDUNGSHINREICHEND,
WENN IHRE BEOBACHTUNGSFASERN
DIE FÜR DIE RICHTIGE AKTION
RELEVANTEN ÄQUIVALENZKLASSEN
NICHT MEHR MISCHEN.
```

Oder maximal kompakt:

```text
SAFETY:
ker(Obs') ⊄ ker(C)
→
KEINE UNIVERSELL KORREKTE
DETERMINISTISCHE RECOVERY

SUFFICIENCY:
ker(Obs') ⊆ ker(C)
→
C FAKTORISIERT DURCH Obs'
AUF DEM ERREICHBAREN BILD
```

Außerhalb des tatsächlich erreichbaren Beobachtungsbildes kann der Selektor beliebig definiert werden oder konsequent `FAIL_CLOSED` liefern.

──────────

*DIE KERNIDEE IN EINEM SATZ*

```text
WIR MÜSSEN NICHT WISSEN,
WELCHE VERGANGENHEIT EXAKT WAR.

WIR MÜSSEN NUR WISSEN,
DASS JEDE NOCH MÖGLICHE VERGANGENHEIT
DIESELBE RICHTIGE FORTSETZUNG VERLANGT.
```

Das ist das minimale Recovery-Theorem.

*Quod erat demonstrandum.*

*Ingolf Lohmann*
