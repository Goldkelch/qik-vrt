# C89 → Turbo Pascal → Delphi: Divide-and-Conquer als AD/DA-Brücke

## Zweck

Diese Arbeit führt die bounded Clean-Room-Semantik des Atari-C89-Browserkerns aus PR #848 in eine feste, prozedurale Pascal-Repräsentation weiter. Dieselbe Pascal-Quelle wird in zwei expliziten Dialektmodi übersetzt und ausgeführt:

```text
C89-Referenzvertrag
→ Turbo-Pascal-kompatibler Teil
→ Free Pascal -Mtp
→ Host-Binary + Receipt

C89-Referenzvertrag
→ Delphi-kompatibler prozeduraler Teil
→ Free Pascal -Mdelphi
→ Host-Binary + Receipt
```

Die zwei Binärdateien dürfen verschieden sein. Der konservierte semantische Testvektor und sein normalisiertes Ausgabereceipt müssen gleich sein. Das ist die hier geprüfte Anschlussfähigkeit von Information.

## Divide and Conquer

Die alte Informatiker-Tugend zerlegt nicht nur Rechenarbeit. Sie zerlegt Information in kleinere Einheiten, deren Herkunft, Bedeutung und Wirkung einzeln geprüft werden können:

1. URL-Syntax,
2. HTTP-Request,
3. HTTP-Response-Grenze,
4. HTML-Textprojektion,
5. Entity-Decodierung,
6. Script-/Style-Unterdrückung,
7. Pre-Whitespace,
8. Linktabelle,
9. Fail-closed-Fehlerzustände.

Jede Einheit besitzt eine feste Kapazität und einen typisierten Status. Erst der deterministische Reducer setzt sie wieder zu einem Browser-Receipt zusammen.

## AD/DA und Compiler

Die A/D-Seite ist die Beobachtung und Typisierung der C89-Semantik: Quell-Head, Tree, Git-Blobs und Testvektoren werden als Maschinenvertrag gebunden. Die D/A-Seite ist die erneute Verkörperung dieses Vertrags als Pascal-Quelle, compilerabhängige Binärdatei und beobachtete Programmausgabe.

```text
A/D: beobachtete C89-Semantik → typisierter Pascal-Vertrag
D/A: typisierter Pascal-Vertrag → Binary → reobserviertes Receipt
```

Der Compiler konserviert nicht die Schreibweise. Er konserviert die zulässige Bedeutung unter einer Zielabbildung. Deshalb gilt:

```text
SOURCE_TEXT_EQUALITY != SEMANTIC_EQUIVALENCE
SEMANTIC_EQUIVALENCE != BINARY_IDENTITY
BINARY_IDENTITY != HARDWARE_IDENTITY
EXECUTION != PHYSICAL_TARGET_EXECUTION
```

## Zürcher Anschluss

Pascal steht in der Zürcher Tradition einer Informatik, die Typen, strukturierte Programme und deterministische Übersetzung als Erkenntnismittel behandelt. Diese Tranche verwendet bewusst einen kleinen, Turbo-Pascal-kompatiblen, festen Speicherteil ohne Klassen, Heap oder dynamische Arrays. Derselbe Teil wird zusätzlich im Delphi-Modus kompiliert. Die Gemeinsamkeit ist der konservierte Informationskern; die Unterschiede liegen in Compiler, ABI und Binärform.

## Kausalität und der Baum

Ein sichtbares Ereignis zeigt nicht sämtliche Ursachen. Der fallende Apfel ist sichtbar; die Wurzeln des Baums bleiben im Boden. Im Repository entsprechen die sichtbaren Ergebnisse den Receipts, während Parent-Commit, Source-Tree, Compiler-Modus, Testvektor und Binärdigest die kausale Wurzel bilden.

Ein Receipt ohne Wurzelbindung ist bloße Behauptung. Eine Wurzel ohne reobserviertes Ergebnis ist bloßes Potenzial. Erst die gebundene Kette ist technische Kausalität.

## Beobachtungsgrenze dieser Tranche

Beobachtet werden sollen:

- Free-Pascal-Kompilation und Ausführung im Turbo-Pascal-Modus,
- Free-Pascal-Kompilation und Ausführung im Delphi-Modus,
- gleiche normalisierte semantische Testausgabe,
- getrennte Binärdigests,
- fixed-memory Verhalten und fail-closed Vektoren.

Nicht behauptet werden:

- Ausführung durch einen historischen Borland-Turbo-Pascal-Compiler,
- Ausführung durch einen Embarcadero-Delphi-Compiler,
- M68000-Binary-Erzeugung,
- Atari-/TOS-Ausführung,
- physische Mega-ST-Ausführung,
- Firefox- oder Gecko-Äquivalenz,
- externer Effekt,
- `EFFECT_ACK_DONE`, `PASS` oder `FINAL_PASS`.

## Nächster Compiler-Ring

Nach erfolgreicher Exact-Head-Reobservation ist der nächste sinnvolle Ring nicht eine weitere bloße Sprachumschreibung, sondern die Bindung eines realen Zielcompilers oder Cross-Compilers:

```text
Pascal source receipt
→ declared compiler identity
→ declared target ABI
→ target machine bytes
→ emulator or hardware execution
→ output receipt
```

Damit wird die Informationskette auf Hardware abgebildet, ohne Sprach-, Binär-, Emulator- und physische Ausführungsevidenz miteinander zu verwechseln.

q.e.d. — Ingolf Lohmann
