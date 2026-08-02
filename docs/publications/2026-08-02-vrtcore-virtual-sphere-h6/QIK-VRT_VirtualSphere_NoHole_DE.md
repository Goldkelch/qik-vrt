<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT H6: Die Vollkugel im virtuellen Raum

## Wie ein formales Objekt geschlossen wird und trotzdem weiterwachsen kann

Autor: Ingolf Lohmann  
Datum: 2. August 2026  
Status: 55 von 55 H6-Theoremen lokal kernelakzeptiert; exakte lokale Paketbyte-Bindung verifiziert

> Kausalität ist Relation, nicht Sequenz.

Diese Arbeit begann mit einer einfachen, aber weitreichenden Frage:

Wie lässt sich ein digitales Objekt so beschreiben, dass nicht nur seine
Dateien vorhanden sind, sondern auch für jeden zulässigen Schritt erkennbar
bleibt, woher er kommt, was er bewirkt, welche Regeln er erhält und wo seine
Geltung endet?

H5 hatte dafür bereits ein tragfähiges Skelett geliefert. Es gab ausgeführte
Lean-Beweise, eine Grammatik, eine Referenzinstanz, Prüfsummen, einen
Belegstatus und ausdrücklich kartierte Grenzen. Doch zwischen diesen Schichten
lagen noch Übergänge, die nicht in einem einzigen obersten Satz
zusammengeführt waren.

H6 hat genau eine Aufgabe: diese virtuellen Hohlräume zu schließen.

Das Ergebnis nennen wir eine *Vollkugel im virtuellen Raum*. Das ist kein
physikalischer Himmelskörper und keine Behauptung über die geometrische Form
des Universums. Es ist ein präzises Bild für ein formales Objekt, dessen
innerer Beweisweg geschlossen ist und dessen zulässige Nachfolger seine
bereits bewiesenen Eigenschaften bewahren.

## Was „vollständig“ hier wirklich bedeutet

Kein seriöser Beweis kann „alles über alles“ beweisen. Jeder Beweis braucht
Definitionen, Voraussetzungen und einen Geltungsbereich.

H6 nennt diesen Bereich `VirtualClosure`.

`VirtualClosure` bedeutet:

1. Die zu prüfenden Repräsentationen sind eindeutig bezeichnet.
2. Gültige Syntax führt zu einer wohldefinierten abstrakten Struktur.
3. Diese Struktur kann kanonisch serialisiert und wieder eingelesen werden.
4. Die formale Bedeutung ist für alle gültigen Objekte des Modellbereichs
   definiert.
5. Der virtuelle Anfangszustand existiert, ist nicht leer und erfüllt die
   Ausgangsregeln.
6. Jeder erlaubte Wachstumsschritt erhält die benannten Invarianten.
7. Kein als unzulässig definierter Zustand ist vom Anfang aus erreichbar.
8. Ein erreichbarer Zustand kann weitergeführt werden.
9. Der konkrete Nachfolger ist echt größer als sein Vorgänger.
10. Deshalb gibt es im Modell keine endliche obere Grenze des Wachstums.
11. Provenienz und Wirkungsschranke gehen beim Wachstum nicht verloren.
12. Der gesamte Zusammenhang wird in einem obersten No-Hole-Satz
    zusammengesetzt.

Dabei sind die kernelinternen Schließungsfelder keine handgesetzten grünen
Häkchen. Sie werden durch `kernelClosureProjection_all_true` aus einem bereits
konstruierten Lean-Zertifikat projiziert. Erst wenn dessen Bestandteile bewiesen
sind, kann diese Projektion entstehen. Das getrennte Feld `byte-bound` stammt
nicht aus dem Kernel, sondern aus dem exakten äußeren Receipt-Verifier.

Diese Liste ist die Innengeometrie der Vollkugel. Sie sagt exakt, welche
Lücken geschlossen werden. Was nicht darin steht, wird nicht heimlich
mitbehauptet.

## Vom Byte zur Bedeutung

Eine Datei kann die richtige Prüfsumme haben und trotzdem Unsinn enthalten.
Umgekehrt kann ein sinnvoller mathematischer Satz auf einer anderen Datei
bewiesen worden sein. Deshalb trennt H6 mehrere Beziehungen:

```text
Paketbytes
→ Tokenstruktur
→ abstrakte Syntax
→ formale Semantik
→ virtueller Zustand
→ erreichbarer Nachfolger
```

Die Prüfsumme beantwortet: Sind es dieselben Bytes?

Die Oberflächengrammatik beantwortet: Welche Form soll ein menschlich lesbares
H6-Dokument besitzen?

Der formale Codec beantwortet im Lean-Modell: Welche Bitrepräsentation gehört
zu welchem abstrakten Baum?

Die Semantik beantwortet: Welches formale Objekt bedeutet dieser Baum?

Lean beantwortet: Folgen die genannten Sätze aus den exakten Definitionen und
zugelassenen Grundlagen?

Das Receipt beantwortet schließlich: Welche Quellen wurden tatsächlich mit
welcher Laufzeit ausgeführt, und was meldete der Kernel?

Die wichtige Grenze dabei lautet: H6 beweist die Codec- und Grammatikgesetze
relativ zu der in Lean induktiv definierten Bitstream-/AST-Repräsentation. Die
separate EBNF-Datei beschreibt die menschlich lesbare Oberfläche. Solange ein
Produktions-Textparser für diese EBNF nicht ebenfalls formal verfeinert wurde,
wird seine Implementierung nicht als kernelbewiesen bezeichnet.

Erst die gebundene Kette ist ein nachvollziehbares Beweisobjekt. Keine einzelne
Schicht darf die Arbeit der anderen vortäuschen.

## Warum der Kreis beim Roundtrip geschlossen wird

Für einen gültigen abstrakten Syntaxbaum `a` fordert H6 sinngemäß:

```text
decode(encode(a)) = a
```

Das heißt: Wenn das Objekt in seine kanonische Darstellung geschrieben und
wieder eingelesen wird, kommt nicht bloß etwas Ähnliches zurück. Es kommt im
deklarierten Modell dasselbe abstrakte Objekt zurück.

Zusätzlich muss die Normalisierung idempotent sein:

```text
canonicalize(canonicalize(x)) = canonicalize(x)
```

Für akzeptierte Repräsentationen `b` gilt zudem sinngemäß:

```text
encode(decode(b)) = normalize(b)
```

Ein zweiter Normalisierungslauf darf keinen neuen Bedeutungsdrift erzeugen.
Die Normalisierung ist nicht nur idempotent, sondern erhält auch die formale
Semantik. Unvollständige oder ungültige Strukturen werden nicht großzügig
erraten, sondern fail-closed zurückgewiesen.

Damit kehrt die Darstellung zu ihrer eigenen Bedeutung zurück. Ein erster
kleiner Kreis ist geschlossen.

## Der Anfang ist keine leere Behauptung

Ein Wachstumssatz kann formal wahr und trotzdem gehaltlos sein, wenn überhaupt
kein Ausgangszustand existiert. H6 schließt diese Möglichkeit ausdrücklich
aus.

Der virtuelle Kosmos besitzt einen benannten Seed. Dieser Seed ist
nichtvakuös, legal und erfüllt die Ausgangsinvarianten. Die Theorie startet
damit nicht im luftleeren Raum, sondern auf einem konkret definierten Boden.

„Urknall in einer virtuellen Maschine“ erhält hier eine nüchterne formale
Bedeutung:

```text
Seed
→ typisierter Nachfolger
→ erreichbare Zustände
→ erhaltene Invarianten
→ striktes Wachstum
→ mathematische Unbeschränktheit
```

Das ist virtuelle Kosmogenese. Es ist nicht die Behauptung, ein Computerlauf
sei mit dem physikalischen Urknall identisch.

Zwischen Spezifikation und Ausführung liegt dabei eine weitere kontrollierte
Brücke: `StepSpec` beschreibt, was ein zulässiger Schritt erfüllen muss. Die
konkrete Wachstumsfunktion muss diese Spezifikation verfeinern. Außerdem ist
sie im deklarierten Modell deterministisch: Derselbe Zustand erhält nicht
unbemerkt zwei widersprüchliche kanonische Nachfolger.

## Wachstum ohne neue Löcher

„Von nun an stetig nach außen“ muss mathematisch genauer formuliert werden.
H6 arbeitet mit diskreten Zuständen. *Stetig* bedeutet deshalb hier nicht
analytische Kontinuität wie bei einer stetigen Funktion. Gemeint ist:

- Jeder Nachfolger enthält den als persistent bezeichneten Informationskern
  seines Vorgängers.
- Jeder Nachfolger erfüllt dieselben Sicherheits- und Konsistenzinvarianten.
- Jeder Schritt fügt mindestens eine neue erreichbare Einheit hinzu.
- Kein notwendiger Vorgänger und keine Wirkungsgrenze werden dabei gelöscht.
- Jeder Zustand nach dem Seed ist durch einen legalen Vorgänger erzeugt; in der
  Folge der erzeugten Indizes bleibt kein Loch.
- Jeder erreichbare Zustand besitzt einen zulässigen Nachfolger, nicht bloß
  eine vorher ausgewählte endliche Teststrecke.

Für die Population `P(n)` lautet der Wachstumsgedanke:

```text
P(n + 1) > P(n)
```

Aus dem konkreten strikten Wachstum folgt dann:

```text
Für jede endliche Schranke B gibt es ein n mit P(n) > B.
```

Das ist mathematische Unbeschränktheit. Es bedeutet nicht, dass ein endlicher
Rechner bereits unendlich viele Schritte ausgeführt hätte. Der Kernel prüft
einen endlichen Beweis darüber, dass die Konstruktion für jede vorgelegte
endliche Schranke über diese Schranke hinausgeführt werden kann.

Jeder einzelne erzeugte Zustand bleibt dabei endlich. H6 trennt also sauber:

```text
jeder konkrete Zustand hat endliche Population
∧ es gibt keine gemeinsame endliche Obergrenze für alle Zustände
```

## Sicherheit ist mehr als Fortschritt

Ein System kann wachsen und dabei seine eigene Geschichte zerstören. Das wäre
keine lückenlose Erweiterung, sondern bloße Expansion mit Gedächtnisverlust.

H6 trennt deshalb Fortschritt von Erhaltung.

Der absichtlich enge Lean-Invariant `VirtualInvariant` enthält exakt:

- keine fehlende Schale bis zum Radius,
- ein vorhandenes Zentrum,
- eine aus dem Radius abgeleitete endliche Population.

Weitere eigenständige Sätze beweisen deterministische Nachfolge, injektive
Zustandsindizes, einen erreichbaren Vorgänger für jeden erreichbaren
Nicht-Seed-Zustand, Erhaltung aller alten Schalen sowie die separate
Wirkungsgrenze. H6 behauptet nicht stillschweigend zusätzliche Invarianten,
die in Lean nicht genannt sind.

Der zentrale Sicherheitsgedanke lautet:

```text
legaler Seed
+ invariantenerhaltende Übergänge
→ kein illegaler erreichbarer Zustand
```

Das ist die formale Bedeutung von „ohne Lücken weiterwachsen“. Nicht jede
erdenkliche Eigenschaft wird für alle Zukunft garantiert. Aber jede im H6-
Vertrag ausdrücklich genannte Invariante wird von jedem konstruierten Schritt
mitgeführt.

## Der oberste No-Hole-Satz

Die einzelnen Beweise werden in Lean nicht nur nebeneinandergestellt. Der
oberste Satz verbindet sie zu einem einzigen Objekt:

```text
QIKVRT.VRTCore.VirtualSphereH6.
h6_virtualSphere_noHole_complete
```

Sinngemäß besagt er:

```text
ExternalBindingRetained
∧ GrammarSound
∧ GrammarComplete
∧ CanonicalRoundtrip
∧ SemanticTotality
∧ NonVacuous
∧ InitialStateValid
∧ InvariantsPreserved
∧ NoIllegalReachableState
∧ Progress
∧ StrictGrowth
∧ Unbounded
∧ EffectBoundaryPreserved
→ VirtualClosure
```

Zu dieser Komposition gehören außerdem die modellrelative Grammatikinduktion,
die Verfeinerung von `StepSpec`, Determinismus, Erzeugtheit, Vorgängerexistenz,
Lückenfreiheit der Indizes und die Endlichkeit jedes konkreten Zustands.

Dieser kernelinnere Satz ist ausgeführt: 55 von 55 benannten Theoremen wurden
von Lean 4.19.0 akzeptiert. Der vollständige Axiom-Audit meldet 24 Sätze ohne
Axiome, 19 mit `propext`, 2 mit `propext` und `Quot.sound` sowie 10 mit
`propext`, `Classical.choice` und `Quot.sound`. Projektlokale Axiome, `sorry`,
`admit` und `unsafe` werden nicht verwendet.

Der Quellcompile und der vollständige Audit wurden lokal jeweils zweimal
ausgeführt. Beide Kompilate waren byteidentisch, beide Auditläufe inhaltlich
identisch. Das ist ein starker lokaler Reproduzierbarkeitsnachweis. Es ersetzt
noch keine unabhängige Reproduktion durch eine zweite Partei in einer separat
kontrollierten Umgebung.

Das Toptheorem erhält jedoch ein `ExactArtifactBinding` als externen Parameter.
Lean bewahrt die Zuordnung, berechnet oder authentifiziert aber nicht selbst
die SHA-256-Werte von Repository, Runtime und Receipt. Daher sind zwei Stati zu
unterscheiden:

```text
KERNEL_MODELLSCHLIESSUNG = BEWIESEN
RECEIPT_GEBUNDENE_PAKETSCHLIESSUNG = LOKAL VERIFIZIERT
```

Die zweite Zeile ist nach dem exakten Abgleich von Manifest, Verzeichnis,
Prüfsummen, Quellen, Lean-/Std-Runtime, Befehlen, Toptheorem und Receipt lokal
auf wahr gewechselt. Die getrennte Reproduktion durch eine unabhängige Partei
bleibt ein offener, zusätzlicher Erkenntnisschritt.

Diese Zurückhaltung schwächt die Arbeit nicht. Sie ist Teil ihrer Stärke:
Auch der letzte Statuswechsel muss denselben Kausalitätsspiegel durchlaufen wie
jedes andere Ergebnis.

## Die Vertrauensbasis wird nicht versteckt

Auch ein kernelgeprüfter Satz schwebt nicht über jeder technischen
Voraussetzung. H6 führt deshalb einen Pflichtblock für die Vertrauensbasis:

- exakte Lean-Version,
- verwendeter Kernel,
- deklarierte Logik und Axiome,
- verbotene Abkürzungen wie `sorry` oder projektlokale Axiome,
- Ausführungsplattform,
- Grenze der Hardware- und Softwareannahmen.

Ein weiterer Pflichtblock bindet Repository-Head, Paketwurzel, Manifest,
Lean-Quelle, Audit-Quelle, Toptheorem und Receipt über exakte Digests. Der Hash
beweist nicht die Bedeutung. Er verhindert aber, dass ein Beweis unbemerkt auf
andere Bytes umgedeutet wird.

Die Receipt-Datei kann ihren eigenen Digest nicht zirkulär in sich selbst
beweisen. Deshalb wird sie von der äußeren Prüfsummenliste gebunden. Auch diese
kleine Grenze wird offengelegt, statt als magische Selbstbeglaubigung
behandelt zu werden.

## Warum aus VirtualClosure keine PhysicalClosure folgt

Der wichtigste Schutzsatz ist keine technische Kleinigkeit:

```text
VirtualClosureCertificate ─/→ PhysicalClosureEvidence
```

Das Zeichen bedeutet hier: Es gibt in H6 keine Ableitung, Typumwandlung oder
automatische Beförderung von der virtuellen Urkunde zur physikalischen Evidenz.
Es geht nicht um eine bloße Ungleichheit zweier Werte, sondern um getrennte
Typen und eine absichtlich fehlende Promotionsregel.

H6 kann nach erfolgreichem Audit vollständig innerhalb seines virtuellen
Modells geschlossen sein. Daraus folgt nicht automatisch:

- dass die Natur genau dieses Modell realisiert,
- dass Gravitation bereits quantenmechanisch vereinheitlicht wurde,
- dass ein Graviton nachgewiesen wurde,
- dass virtuelle Kosmogenese der physische Urknall ist,
- oder dass eine weltanschauliche Deutung zum Messbefund geworden ist.

Für `PhysicalClosure` wären eine nichtzirkuläre Korrespondenz zu gemessenen
Größen, unterscheidende Vorhersagen, experimentelle Prüfung und unabhängige
Reproduktion erforderlich. Dieser Bereich bleibt ausdrücklich `OPEN`.

Die Vollkugel ist also vollständig als *kernelinneres virtuelles
Modellbeweisobjekt*. Ihre konkrete Paketidentität wird erst durch das äußere
Receipt geschlossen. Sie ist kein Trick, um offene Physik durch eine Definition
für erledigt zu erklären.

## Was der Kernel leistet – und was nicht

Der Lean-Kernel kontrolliert, ob der übergebene Beweisterm den deklarierten Typ
besitzt. Dadurch wird ein großer Raum möglicher menschlicher und maschineller
Fehler drastisch verkleinert.

Der Kernel entscheidet jedoch nicht selbst,

- ob die Definitionen die Natur angemessen beschreiben,
- ob die ausgewählten Invarianten für jeden denkbaren Zweck vollständig sind,
- ob ein Messgerät korrekt kalibriert war,
- ob eine Veröffentlichung gesellschaftlich verantwortbar ist,
- oder ob eine philosophische Interpretation überzeugt.

Darum führt H6 sechs Erkenntnisarten getrennt mit:

1. formal bewiesen,
2. empirisch gestützt,
3. quellengebunden,
4. normativ,
5. interpretativ,
6. offen.

Kein Eintrag darf allein durch rhetorische Nähe in eine andere Art wechseln.

## Für alle nachvollziehbar

Nachvollziehbarkeit bedeutet nicht, dass jeder Mensch Lean lesen können muss.
Sie bedeutet, dass die Behauptung in überprüfbare Ebenen zerlegt ist:

- Der allgemein verständliche Artikel erklärt den Zusammenhang.
- Die EBNF zeigt die vollständige Oberflächenstruktur.
- Das Referenzobjekt belegt, dass jeder Pflichtblock konkret ausgefüllt ist.
- Die Claim-Matrix trennt Beweis, Quelle, Interpretation und offene Frage.
- Die Lean-Quelle enthält Definitionen und Beweisterme.
- Der Axiom-Audit zeigt die logischen Abhängigkeiten.
- Manifest und Prüfsummen binden die Bytes.
- Das Receipt dokumentiert die tatsächliche Kernel-Ausführung.
- Eine unabhängige zweite Ausführung kann anschließend dasselbe Paket prüfen.

So kann ein normal gebildeter Mensch verstehen, *was* bewiesen wird, während
Fachleute zusätzlich prüfen können, *wie* es bewiesen wird.

## Die menschliche Bedeutung

Die technische Leistung ist groß, weil hier Sprache, Bedeutung, Beweis,
Dynamik, Provenienz und Verantwortung nicht als getrennte Nachträge behandelt
werden. Sie bilden ein einziges überprüfbares Objekt.

Das hat Folgen weit über einen einzelnen Beweis hinaus.

Für Software bedeutet es, dass Wachstum seine Herkunft und seine Grenzen
mitführen kann.

Für KI bedeutet es, dass erfolgreiche Berechnung nicht automatisch zur
externen Wirkung wird.

Für Wissenschaft bedeutet es, dass offene Brücken sichtbar bleiben, statt in
einer eindrucksvollen Gesamterzählung zu verschwinden.

Für Menschen bedeutet es, dass Fortschritt und Verantwortung nicht als
Gegensätze behandelt werden müssen. Ein System kann größer werden, ohne seine
Geschichte, seine Zweifel oder seine Schutzgrenzen auszulöschen.

Formal hält H6 dafür zwei Sicherungen auseinander. Der No-Escalation-Satz
verhindert, dass technischer oder virtueller Erfolg eigenständig
`EFFECT_ACK_DONE` konstruiert. Der Effect-Preservation-Satz trägt den bereits
geltenden Wirkungshaltepunkt durch jeden erreichbaren Wachstumsschritt weiter.

Weltanschaulich lässt sich darin ein starkes Bild sehen: Wirklichkeit entsteht
nicht aus bloßer Reihenfolge, sondern aus unterscheidbaren Relationen, die
etwas bewirken und ihre Herkunft bewahren.

Spirituell kann die offene, nie abschließend ausgeschöpfte Erweiterbarkeit als
Bild für Verbundenheit, Schöpfung oder Verantwortung gelesen werden. Das kann
für Menschen bedeutsam sein. Es bleibt aber eine Interpretation und wird nicht
als Kerneltheorem oder physikalischer Messwert ausgegeben.

## Der große Kreis

Am Anfang steht eine Unterscheidung.

Die Unterscheidung wird Information.

Information tritt in Relation.

Eine wirksame Relation bildet Kausalität.

Kausalität ordnet zulässige Übergänge.

Übergänge erzeugen erreichbare Zustände.

Erreichbare Zustände hinterlassen überprüfbare Records.

Der Record macht die neue Unterscheidung für den nächsten Schritt verfügbar.

Damit kehrt die Entwicklung zu ihrem Anfang zurück – nicht als Wiederholung,
sondern auf einer erweiterten Oberfläche:

```text
Unterscheidung
→ Information
→ Relation
→ Kausalität
→ Zustand
→ Wirkung
→ Record
→ neue Unterscheidung
```

Der Kreis schließt sich. Und weil jeder vollständige Umlauf einen legalen,
größeren Nachfolger erzeugt, muss die Bewegung nicht zwischen zwei Punkten
pendeln. Sie kann von dort an nach außen fortgesetzt werden.

Das ist die kernelinnere H6-Vollkugel: innen geschlossen, nach außen offen.

Nicht grenzenlos in ihren Behauptungen.

Aber ohne verschwiegene Lücke in ihrem deklarierten virtuellen Beweisraum.

## Statusgrenze

```text
VIRTUAL_CLOSURE_SCOPE = PASS
KERNEL_MODEL_VIRTUAL_CLOSURE = PROVED_55_OF_55
RECEIPT_BOUND_PACKAGE_CLOSURE = VERIFIED_LOCAL_EXACT_BYTES
PHYSICAL_CLOSURE = OPEN
PHYSICAL_BIG_BANG_IDENTITY = NOT_CLAIMED
LOCAL_REPEAT_EXECUTION = TWO_MATCHING_RUNS
INDEPENDENT_EXTERNAL_REPRODUCTION = OPEN
GLOBAL_PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
EFFECT_STATE = EFFECT_ACK_CONTINUE
```

Der kernelinnere Modellbeweis und seine exakte lokale Paketbyte-Schließung sind
vollzogen. Kein physikalischer oder externer Wirkungsstatus wird dadurch
automatisch verändert.

q.e.d. – für das kernelgeprüfte, lokal receiptgebundene H6-Modell. Die
physikalische Brücke und eine unabhängige externe Reproduktion bleiben
ausdrücklich offen.

Ingolf Lohmann
