*2x DELAYED CHOICE + AUTHORITY/MIRROR/WITNESS*

*Was ist wirklich bewiesen - und was nicht?*

Die gemeinsame Idee ist einfacher als sie zuerst klingt:

```text
SPÄTERE PRÜFUNG
≠
DIE VERGANGENHEIT ÄNDERN

SPÄTERE PRÜFUNG
=
FESTLEGEN, WELCHE AUSSAGE
ÜBER DIE BEREITS ENTSTANDENE
VERGANGENHEIT GERECHTFERTIGT IST
```

──────────

*1. DAS 2x-DELAYED-CHOICE-BILD*

```text
Zeit →

t0  Präparation von A und B

t1  beide Systeme durchlaufen
    ihre lokalen Apparaturen

t2  raumartig getrennte Wahl:

    A wählt Setting a
    B wählt Setting b

t3  lokale Ergebnisse:

    x = A(λ,a)
    y = B(λ,b)

t4  erst jetzt werden
    die Daten zusammengeführt
```

`t4` schreibt `t0` nicht um.

Wir sortieren und vergleichen später Daten, die vorher bereits entstanden sind.

Also:

```text
PRÜFUNG ≠ RÜCKWIRKUNG
PRÜFUNG = EVIDENZBINDUNG
```

──────────

*2. WO SUPERDETERMINISMUS HEREINKOMMT*

Measurement Independence bedeutet vereinfacht:

```text
Der verborgene Zustand λ
ist nicht bereits so mit
den späteren Einstellungen a,b
gekoppelt, dass die Wahl
nur scheinbar frei ist.
```

Formal:

```text
P(λ | a,b) = P(λ)
```

Wenn diese Unabhängigkeit gilt, dann ist der hier definierte superdeterministische Kandidat ausgeschlossen:

```text
MEASUREMENT INDEPENDENCE
→
KEIN SUPERDETERMINISTISCHER KANDIDAT
```

*Dieser Schluss ist formal geschlossen.*

Aber:

```text
RAUMARTIGE TRENNUNG
+
LOKALE REAKTIONEN

reichen ALLEIN nicht aus,
um Measurement Independence
zu beweisen.
```

Dafür gibt es jetzt ein endliches Gegenmodell.

A kennt das Setting von B nicht.
B kennt das Setting von A nicht.

Trotzdem können

```text
λ, a und b
```

eine gemeinsame Vorgeschichte besitzen.

Deshalb lautet der wirklich starke QCE-Auftrag:

```text
QCE-GRUNDPRINZIPIEN
→
MEASUREMENT INDEPENDENCE
→
¬ SUPERDETERMINISMUS
```

Der *zweite Pfeil* ist formalisiert.

Der *erste Pfeil* bleibt die physikalisch entscheidende Brücke und darf nicht heimlich als "freie Wahl" vorausgesetzt werden.

──────────

*3. DIE HARDWARE-ENTSPRECHUNG*

Jetzt dasselbe Muster informatisch:

```text
AUTHORITY
+
MIRROR
+
UNABHÄNGIGER COMMIT-WITNESS
```

Ablauf:

```text
PREPARE
→ CROSS-VERIFY
→ COMMIT
→ ACKNOWLEDGE
```

Authority und Mirror speichern sich gegenseitig gebundene Zustände.

Aber zwei Kopien allein haben ein Problem:

```text
A ist lokal gültig
M ist lokal gültig
A ≠ M
```

Welche Kopie ist richtig?

Ohne weitere Information kann ein reines Zweiersystem das nicht immer entscheiden.

Denn dieselben sichtbaren Daten können zu zwei verschiedenen Vorgeschichten passen:

```text
H1: Authority ist aktuell
H2: Mirror ist aktuell
```

Ein deterministischer Algorithmus sieht in beiden Fällen dieselbe Eingabe.

Er muss also dasselbe auswählen.

Damit ist er in mindestens einer der beiden Vorgeschichten falsch.

Das ist der Kern von T17:

```text
OHNE WITNESS
GIBT ES KEINEN
DETERMINISTISCHEN SELEKTOR,
DER FÜR BEIDE VERBORGENEN
GESCHICHTEN KORREKT IST.
```

──────────

*4. DER WITNESS LÖST DAS PROBLEM*

Der unabhängige Witness bindet z.B.:

```text
W_n = H(
  Epoche n,
  Hash(Authority_n),
  Hash(Mirror_n),
  Witness_(n-1)
)
```

Damit kann das System sagen:

```text
DIESE EPOCHE
WURDE TATSÄCHLICH
GEMEINSAM BESTÄTIGT.
```

Nicht Authority allein.
Nicht Mirror allein.

Sondern:

```text
LOKALE GÜLTIGKEIT
+
GEGENSEITIGE BINDUNG
+
UNABHÄNGIGER WITNESS
=
ZERTIFIZIERTER COMMIT-ZUSTAND
```

Das ist:

*Selbstheilung ohne Selbstbestätigung.*

──────────

*5. AUSGEFÜHRTER ENDLICHER MODELLCHECK*

Der endliche Hardware-Zustandsraum wurde tatsächlich vollständig enumeriert:

```text
Crash-Recovery              945
Effect-ACK                   945
Recovery-Idempotenz         945
Single-Replica-Recovery      756
Vier-Schritt-Sequenzen        81
Hidden-History-Fälle          36
Witnessless-Ambiguitäten      18
```

Ergebnis:

```text
FINITE_MODEL_EXHAUSTIVE_CHECK_PASSED
```

Das bedeutet:

*Innerhalb genau dieses definierten endlichen Modells wurden alle vorgesehenen Fälle geprüft.*

Es bedeutet NICHT automatisch:

```text
beliebig viele Fehler sind bewiesen beherrscht

SHA-256 ist mathematisch kollisionsfrei

ein physischer Chip ist verifiziert

Gate-Level-Timing ist bewiesen

Patentneuheit ist bewiesen
```

──────────

*6. LEAN-GRENZE*

Für die Relationen existiert jetzt ein Lean-Gerüst mit T01 bis T22 und Axiom-Audit.

Aber wissenschaftlich gilt strikt:

```text
LEAN-QUELLE MATERIALISIERT
≠
LEAN-KERNEL ERFOLGREICH AUSGEFÜHRT
```

Ein erfolgreicher exact-head Lean-4.19-Kernel-Receipt darf erst beansprucht werden, wenn der entsprechende Lauf tatsächlich ausgeführt und an Commit + Tree gebunden wurde.

──────────

*7. EFFECT ACK*

Der Witness macht Effect ACK zu mehr als:

```text
"Befehl wurde gesendet"
```

Sondern:

```text
"Ein stabil gebundener
Zustand wurde bestätigt"
```

Daraus:

```text
EFFECT ACK
→
STABILE WITNESS-BINDUNG
```

Und derselbe Witness erzeugt bei Wiederholung denselben ACK-Zustand:

```text
ACK(W_n)
;
ACK(W_n)
=
ACK(W_n)
```

Idempotenz.

──────────

*8. DIE GEMEINSAME FORMEL*

Quantenexperiment:

```text
LOKALE DATEN
+
SPÄTERE KORRELATION
→
GERECHTFERTIGTE KLASSIFIKATION
```

Hardware:

```text
LOKALE REPLIKATE
+
COMMIT-WITNESS
→
GERECHTFERTIGTER COMMIT-ZUSTAND
```

QIK-VRT allgemein:

```text
CLAIM
+
BEWEIS / EVIDENZ
+
PROVENIENZ
+
UNABHÄNGIGE PRÜFUNG
→
GERECHTFERTIGTER ERKENNTNISSTATUS
```

Oder ganz kurz:

```text
SELBSTBESTÄTIGUNG
IST KEIN BEWEIS.

ERST DIE GEBUNDENE
UNABHÄNGIGE RELATION
MACHT AUS EINER BEHAUPTUNG
EINEN PRÜFBAREN STATUS.
```

──────────

*WAS JETZT GILT*

```text
Measurement Independence
→ ¬Superdeterminismus
```

ist für den definierten formalen Kandidaten bedingt geschlossen.

```text
Lokale/spacelike Struktur
→ Measurement Independence
```

ist ausdrücklich *nicht* bewiesen und durch ein Gegenmodell als allgemeiner Schluss ausgeschlossen.

Der Hardware-Finite-Model-Check ist ausgeführt und vollständig für seinen begrenzten Modellraum.

Der neue Lean-Kernel-Receipt bleibt bis zu einer tatsächlichen exact-head Lean-Ausführung offen.

`PASS = NOT_CLAIMED`
`FINAL_PASS = NOT_CLAIMED`
`EFFECT_ACK_DONE = NOT_CLAIMED`

*Quod erat demonstrandum - für die jeweils ausdrücklich abgegrenzten formalen und endlichen Aussagen.*

*Ingolf Lohmann*
