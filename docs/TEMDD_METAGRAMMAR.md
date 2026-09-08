<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# TEMDD als universale, domänenparametrische Metagrammatik

**Autor und Product Owner:** Ingolf Lohmann

**Status:** öffentlicher Architektur- und Sprachtext. Er erläutert einen
Metasprachenanspruch und seine Prüfgrenzen; er ist weder ein Ersatz für einen
exakt gebundenen Lean/Lake-Nachweis noch eine empirische Naturbehauptung.

Tested Event Model Driven Development (TEMDD) beginnt mit einer einfachen,
aber folgenreichen Verschiebung: Verstehen wird nicht als unsichtbarer
Besitzstand eines Menschen oder einer Maschine behandelt. Verstehen wird als
nachvollziehbare Einschränkung dessen behandelt, was ein System angesichts
seiner gebundenen Evidenz noch für möglich hält und welche Schritte es deshalb
freigeben darf.

Die Ausführungsregel lautet:

```text
Request → Execute → Follow → Learn → Repeat Until Done
```

Sie ist keine Behauptung, dass jede Anfrage automatisch lösbar sei. Sie ist ein
Vertrag darüber, wie ein System vorgehen muss, wenn es eine Anforderung
verantwortbar bearbeiten will: Absicht in einen prüfbaren Vertrag überführen,
einen begründeten Schritt ausführen, seine tatsächliche Wirkung zurücklesen,
das Modell anhand der neuen Evidenz korrigieren oder präzisieren und erst dann
den nächsten Schritt ableiten.

Die Besonderheit von TEMDD liegt nicht darin, eine weitere einzelne
Programmiersprache neben bestehenden Sprachen zu setzen. Der Sprachkern legt
fest, wie *jede* hinreichend explizit beschriebene Sprache, Domäne oder
Entscheidungssituation als Gegenstand von Anforderungen, Zuständen, Modellen,
Evidenz, Handlungen und Autoritäten behandelt werden kann. In diesem präzisen
Sinn ist TEMDD eine Metagrammatik: eine Grammatik darüber, wie Bedeutung,
Prüfung und wirksames Handeln grammatisch und evidenzgebunden zusammenkommen.

## Der stabile Kern: nicht „was wahr ist“, sondern was verantwortbar folgt

Der TEMDD-Kern verwendet sechs Domänen:

\[
\mathcal S,\quad \mathcal R,\quad \mathcal M,\quad
\mathcal E,\quad \mathcal A,\quad \mathcal U.
\]

Sie stehen für Zustände, Anforderungen, Modelle, Evidenz, Aktionen und
Autoritäten. Ein Ausführungszustand verbindet sie mit einer unveränderlichen
Ereignisgeschichte und einem Typ-, Gültigkeits- und Autoritätskontext. Die
Domänen sind absichtlich abstrakt. Ein Zustand kann ein Quellbaum, ein
Messaufbau, eine Vertragsversion, ein Verkehrssystem oder der Inhalt einer
Äußerung sein. Evidenz kann ein formaler Beweis, ein deterministischer Test,
eine Messung, ein Artefaktbeleg oder ein menschlicher Entscheid sein. Welche
Interpretation zutrifft, wird nicht geraten, sondern im jeweiligen Modell und
Subject festgelegt.

Für eine Anforderung \(R\) bezeichnet die Goal Region die zulässigen Zustände:

\[
GR(R)=\{s\in\mathcal S\mid s\models R\}.
\]

Die Evidenz \(E\) bestimmt demgegenüber die Knowledge Region, also die
Zustände, die mit ihr noch vereinbar sind:

\[
K(E)=\{s\in\mathcal S\mid s\sim E\}.
\]

Aus diesen beiden Mengen ergibt sich keine magische Gewissheit. Es ergibt sich
eine klare Prüfaufgabe: Welche Zustände sind noch möglich, und liegen *alle*
davon im erlaubten Bereich? Für eine Aktion \(a\) ist die zentrale
Sicherheitsforderung:

\[
SAFE(a,R,E)
\iff
\forall s\in K(E):\;Post(s,a)\subseteq GR(R).
\]

Ein System darf einen Schritt nur freigeben, wenn er für jeden mit der Evidenz
vereinbaren Zustand innerhalb der Anforderung bleibt. Ist das nicht gezeigt,
ist der ehrliche Zustand nicht „erledigt“, sondern `HOLD`.

Der vorhandene TEMDD-V1-Abschlusskern formuliert dies subject-relativ. `DONE`
setzt eine nichtleere Wissensregion, deren Einschluss in die Goal Region,
exakte Subject-Bindung und Abdeckung des beanspruchten tatsächlichen Zustands
voraus. Der Quellanker dafür ist
`formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/Completion.lean`;
die menschliche und maschinenlesbare V1-Beschreibung stehen in
`docs/TEMDD_LANGUAGE_V1.md` und `policy/TEMDD_LANGUAGE_V1.json`.

Damit wird eine oft verschwommene Unterscheidung technisch erzwingbar:

\[
\text{behauptete Wirkung}\neq\text{beobachtete Wirkung}.
\]

Eine übertragene Nachricht ist nicht schon eine eingetretene Wirkung. Ein
grüner Test auf einem alten Commit ist kein Abschluss auf einem neuen Commit.
Eine überzeugend klingende Interpretation ist keine autorisierte Anforderung.
Eine formale Ableitung ist nicht automatisch eine Messung über die Welt.

## Was „universal“ hier genau bedeutet

„Universal“ ist in diesem Text weder ein Superlativ für ein fertiges
Allwissenheitssystem noch die Behauptung, jede konkrete Sprache sei bereits
vollständig implementiert. Gemeint ist eine *domänenparametrische Form*.

TEMDD verlangt nicht, dass natürliche Sprache, Python, Lean, ein Laborprotokoll
und ein verteiltes Nachrichtenformat dieselbe Oberflächensyntax haben. Es
verlangt nur, dass ein jeweiliger Gegenstand explizit modelliert werden kann:

| Für eine Domäne wird festgelegt | TEMDD fragt danach |
| --- | --- |
| Was sind ihre unterscheidbaren Zustände? | `State` |
| Was muss gelten, was ist verboten? | `Requirement` und Goal Region |
| Wie werden Zeichen, Daten oder Beobachtungen gedeutet? | `Model` und Interpretation |
| Welche Quellen tragen welche Aussage? | typisierte, subject-gebundene `Evidence` |
| Was kann die Domäne verändern oder beobachten? | `Action` und `Follow` |
| Wer darf lesen, vorschlagen, mutieren, prüfen oder freigeben? | `Authority` und Capabilities |

Diese sechs Fragen sind nicht an ein einzelnes Fach gebunden. Deshalb kann
dieselbe Grundstruktur eine deutschsprachige Arbeitsanweisung, eine API,
einen Compilerlauf, eine wissenschaftliche Hypothese oder eine
Qualitätssicherung beschreiben. Die Domäne wird nicht nivelliert; ihre
besonderen Begriffe, Messmethoden, Typen und Grenzen werden als Modellparameter
eingetragen.

Eine universale Metagrammatik ist daher vergleichbar mit einer präzisen
Schnittstelle zwischen unterschiedlichen Erkenntnis- und Handlungssystemen.
Sie sagt nicht, dass alle Systeme dasselbe bedeuten. Sie schafft eine Form, in
der Unterschiede explizit werden: Welche Semantik wird benutzt? Welche
Annahmen gelten? Welche Evidenz hat welchen Typ? Für welches konkrete Subject
gilt sie? Wer besitzt die erforderliche Capability? Und welche Folgerung ist
unter diesen Bedingungen tatsächlich zulässig?

Der Gewinn ist Anschlussfähigkeit ohne Gleichmacherei. Eine neue Domäne muss
nicht außerhalb des Systems erfunden werden. Sie kann als Erweiterung mit
neuen Sorten, Konstruktoren, Evidenzregeln, Aktionen oder Abstraktionsverträgen
eingeführt werden, solange sie die Kerninvarianten nicht still aufhebt.

## Die formale Reichweite einer konservativen Erweiterung

Die Aussage, dass TEMDD eine Metagrammatik ist, hat einen formalen Kern: Der
Basiskalkül kann so gestaltet werden, dass spätere Sprachschichten den bereits
gültigen Kern nicht umdeuten. Das ist der Gedanke einer **konservativen
syntaktischen Erweiterung**. Der maschinenlesbare Kurzname
`konservative erweiterung` bezeichnet hier ausdrücklich keine uneingeschränkte
Weltaussage, sondern einen präzise typisierten Erhaltungsvertrag.

Sei \(B\) eine wohldefinierte Basissyntax und \(X\) eine Erweiterung. Eine
zunächst syntaktische Konservativitätsaussage umfasst mindestens:

\[
embed : Syntax_B \to Syntax_X,
\]

so dass jeder im Kern wohlgeformte Ausdruck in der Erweiterung weiterhin
wohlgeformt ist und seine alten Konstruktoren behält. Für die alte Sprache darf
die Erweiterung keine verdeckte Neudeutung einführen. In einer stärkeren,
semantischen Variante müsste zusätzlich für jede alte Aussage \(\varphi\)
gelten:

\[
\llbracket \varphi \rrbracket_B
=
\llbracket embed(\varphi) \rrbracket_X.
\]

Eine logische Konservativität wäre nochmals stärker: Die Erweiterung dürfte
keinen neuen Satz *in der alten Sprache* beweisbar machen, der nicht bereits
im Basissystem beweisbar war. Diese drei Ebenen — Syntaxerhaltung,
Semantikerhaltung und Beweiskonservativität — sind verschieden. Ein sauberer
Artikel darf sie nicht in einen einzigen Satz zusammenziehen.

Der vorgesehene Lean/Lake-Schritt ist deshalb keine rhetorische Abkürzung,
sondern eine konkrete, enge Behauptung: Eine deklarierte Erweiterung des
TEMDD-Syntaxkerns soll den eingebetteten Basiskern erhalten. Erst die exakte
Lean-Deklaration bestimmt dabei, ob syntaktische, semantische oder logische
Konservativität nachgewiesen wird und unter welchen Voraussetzungen. Sie muss
auf einem bestimmten Repository-Subject durch `lake build` und die zugehörige
Prüfkette bestätigt werden.

Der formalisierte Satz ist bewusst schmaler als ein Versprechen universeller
Semantik: Für einen Lean-definierten, typisierten propositionalen Kern wird
eine explizit gelieferte Vokabular-Einbettung zusammen mit der passenden
Interpretationsrestriktion betrachtet. Eine strukturelle Induktion zeigt, dass
jede bereits vorhandene Formel ihre Wahrheitsbedingung unter dieser Restriktion
behält. Darüber hinaus konstruiert der Kern für jeden ausdrücklich gewählten
Lean-Payload-Typ eine Erweiterung mit einem getrennten Erweiterungssort und
einer kanonischen Einbettung des alten Vokabulars. Das ist eine
Konstruktionsaussage über den dargestellten Syntaxraum; es ist keine
Existenzbehauptung für jede künftige *Semantik* und keine Aussage darüber,
welche physikalische Semantik eine Sprache besitzen muss.

Die Dateien
`formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/Completion.lean`
und
`formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/MetaGrammar.lean`
haben verschiedene Aufgaben. Der Abschlusskern enthält lokale Theoreme des
V1-Kalküls, etwa dass ein abgedeckter tatsächlicher Zustand bei `Done` die
Anforderung erfüllt und dass eine Subject-Mutation die frühere
Abschlussbindung nicht auf das neue Subject überträgt. `MetaGrammar.lean`
ergänzt die explizite Syntaxerweiterung und ihre
Interpretations-Kompatibilität. Bis diese genaue Deklaration auf einem
exakten Head gebaut und unabhängig reobachtet wurde, ist der
Erweiterungssatz `nicht bewiesen` für dieses konkrete Repository-Subject.
Der Quelltext ist ein formales Arbeitsobjekt, kein bereits ungebundener
Lean/Lake-Fakt.

Auch das Vorhandensein einer Lean-Quelldatei oder eines Theoremnamens ersetzt
keinen frischen Build- und Axiom-Audit-Beleg auf dem genauen Head. Bis diese
Evidenz gebunden ist, bleibt der maschinelle Prüfstatus `HOLD_UNVERIFIED`,
selbst wenn die zugrunde liegende Konstruktion plausibel oder lokal lesbar ist.

Das schmälert die Architektur nicht. Im Gegenteil: Die Metagrammatik verlangt
gerade, zwischen einer plausiblen Strukturidee, einer geschriebenen
Spezifikation, einer kernel-geprüften Aussage und einer Anwendung in der Welt
zu unterscheiden.

## Erweiterbar heißt nicht grenzenlos beweisbar

Auf dieser Grundlage kann TEMDD viele notwendige Sprachschichten aufnehmen:
Zeitlogik, probabilistische Risiken, Ressourcenverträge, Kausalmodelle,
Abstraktionsrelationen, domänenspezifische Messprotokolle, neue
Beweisassistenten, verteilte Konsensregeln oder rechtlich und organisatorisch
gebundene Autoritäten. Die Aufnahme erfolgt nicht durch eine Ausnahme, sondern
durch eine deklarierte Erweiterung mit einer eigenen Semantik und eigenen
Evidenzpflichten.

Die Grenze lautet: Eine Erweiterung darf den Kern nicht unbemerkt entkräften.
Sie darf beispielsweise nicht festlegen, dass Evidenz nach einer Mutation
automatisch weitergilt, dass fehlende Evidenz als Erfolg zählt oder dass ein
Agent Anforderungen selbstständig abschwächen darf. Solche Änderungen wären
keine konservativen Erweiterungen, sondern eine andere Sprache oder eine
ausdrücklich autorisierte neue Sprachversion.

Auch „jede denkbare notwendige Erweiterung“ bleibt daher ein
Architekturanspruch mit Bedingungen. Eine Erweiterung ist innerhalb des
Metarahmens formulierbar, wenn ihre Begriffe, Typen, Interpretationen,
Zustandsübergänge, Autoritäten und Invarianten explizit beschreibbar sind.
Ob sie mit dem vorhandenen Kern verträglich ist, muss für die konkrete
Erweiterung nachgewiesen werden. TEMDD garantiert nicht vorab die Konsistenz
jeder künftig erfundenen Theorie; es liefert die Form, in der diese Frage
präzise gestellt und fehlertolerant beantwortet werden kann.

## Menschliche Sprache: nicht Gedankenlesen, sondern modellierte Bedeutung

Eine menschliche Äußerung ist zunächst ein beobachtbares Subject: Text,
Spracheingabe, Dokument, Geste oder ein anderer gebundener Ausdruck. Sie ist
nicht automatisch identisch mit Sprecherabsicht, autorisierter Anforderung
oder einer eindeutigen technischen Spezifikation.

Für eine Äußerung \(q\) kann ein Modell mehrere Interpretationen liefern:

\[
Interpret(q)=\{R_1, R_2, \ldots, R_n\}.
\]

Wenn entscheidungsrelevante Alternativen offen bleiben, macht TEMDD diese
Unsicherheit sichtbar. Es darf nicht still eine Bedeutung auswählen, nur weil
sie sprachlich wahrscheinlich klingt. Der zulässige Raum enthält dann die
noch offenen Alternativen, oder das System fordert eine Klärung von der dazu
autorisierten Person an. Eine Vermutung über Absicht ist keine stärkere
Anforderung und keine Erlaubnis, Konsequenzen auszulösen.

Diese Haltung verbessert Übersetzung und Assistenz nicht dadurch, dass sie
„menschliche Sprache perfekt versteht“. Sie verbessert sie dadurch, dass eine
Übersetzung ihre Quelle, ihr Sprachmodell, ihre Annahmen, ihre Zielsemantik und
ihre Prüfpflichten offenlegen kann. Eine hochwertige Übersetzung ist dann ein
prüfbarer Transformationsvorschlag zwischen zwei modellierten Subjects. Ihre
Qualität kann mit Referenzkorpora, fachlicher Prüfung, Gegenbeispielen und
Nutzungsbeobachtung untersucht werden; sie folgt nicht allein aus der Existenz
der Metagrammatik.

## Maschinensprachen: dieselbe Verantwortung, andere Messinstrumente

Programmiersprachen, Typsysteme, Datenbankschemata, Protokolle, Buildregeln,
Bytecode, Konfigurationsdateien und Logs sind ebenfalls Sprachen. Ihre
Oberflächen können oft strenger grammatisch sein als natürliche Sprache, aber
ihre Bedeutung bleibt kontextabhängig: Ein Programmtext braucht Compiler,
Version, Abhängigkeiten, Eingaben, Plattform, Berechtigungen und eine
beabsichtigte Spezifikation, bevor aus ihm eine belastbare Wirkungsaussage
werden kann.

TEMDD kann diese Gegenstände als modellierte Subjects behandeln. Ein
Syntaxbaum wird einem Versions- und Typkontext zugeordnet. Ein Buildartefakt
wird an den Quellstand und die Werkzeuge gebunden. Ein Testresultat wird als
deterministische Testevidenz klassifiziert. Ein Laufzeitergebnis bleibt eine
Runtime Observation. Eine ausgelieferte oder physisch wirksame Änderung
benötigt gegebenenfalls eine getrennte Effekt-Rücklesung. So kann Software aus
einer Anforderung entwickelt werden, ohne die entscheidenden Übergänge zu
verschleiern:

```text
Anforderung
→ modellierter Zustands- und Lösungsraum
→ sicherer, autorisierter Änderungsvorschlag
→ Implementierung und Test
→ Reobservation des genauen entstandenen Subjects
→ begründeter nächster Schritt oder HOLD
```

Der Python-Referenzkern in `tools/temdd_language.py` und seine
Negativregressionen in `tests/test_temdd_language.py` demonstrieren genau
diese fail-closed Idee im kleinen: falsche Subject-Bindung, fehlende
Actual-State-Coverage, unvollständige Evidenz, ungelöste harte Pflichten oder
fehlende Autorität führen nicht zu `DONE`. Sie sind jedoch kein Beleg dafür,
dass jede denkbare Software automatisch korrekt erzeugt, geprüft oder sicher
betrieben werden kann.

## Daten, Wahrheit und Naturgesetze: die notwendige harte Grenze

Der stärkste missverständliche Satz wäre: „Mit TEMDD kann Software aus
beliebigen Daten den Wahrheitsgehalt herausziehen.“ Das wäre als allgemeine
Tatsachenbehauptung nicht gedeckt. Daten besitzen keine kontextfreie
Wahrheitsmaschine. Sie können unvollständig, manipuliert, falsch kalibriert,
mehrdeutig, nicht repräsentativ oder für die gestellte Frage schlicht
irrelevant sein. Auch eine vollständig dokumentierte Berechnung kann nur die
Folgerung tragen, die ihr Modell, ihre Quellen und ihre Annahmen tragen.
TEMDD-Systeme sind `keine wahrheitsorakel`.

Was TEMDD stattdessen ermöglicht, ist eine prüfbare Wahrheits- und
Geltungsarbeit innerhalb eines erklärten Scopes. Für einen Datenclaim muss ein
System unter anderem unterscheiden:

| Frage | Erforderliche Bindung |
| --- | --- |
| Was wurde tatsächlich beobachtet oder empfangen? | Quelle, Zeit, Methode, Hash oder anderer unveränderlicher Beleg |
| Welche Schlussregel wurde angewandt? | Modell-, Regel- und Werkzeugversion |
| Welche Alternativen bleiben offen? | Knowledge Region, Unsicherheiten und Gegenbeispiele |
| Welche Aussageklasse liegt vor? | formaler Satz, Testbefund, Repository-Beobachtung, Messung, Review oder Effektbeleg |
| Was würde die Aussage widerlegen oder einschränken? | explizite Falsifikations- bzw. Gegenbeispielbedingungen |
| Wer darf eine Konsequenz auslösen? | passende Capability und Autoritätsentscheidung |

Damit kann eine TEMDD-gestützte Anwendung aus großen Datenmengen
*nachvollziehbar klassifizierte* Aussagen, Widersprüche, fehlende Belege und
testbare Hypothesen ableiten. Sie kann sogar auf anerkannten Naturgesetzen
beruhende Modelle anwenden, sofern deren Geltungsbereich, Parameter,
Messunsicherheiten und Anschlussbedingungen ausdrücklich modelliert sind. Sie
kann nicht aus diesem Vorgehen allein beweisen, dass ein Modell ein
Naturgesetz ist, dass alle Daten wahr sind oder dass eine Korrespondenz zur
Welt vollständig erfasst wurde.

Das gilt auch für formale Systeme. Ein Lean-Theorem zeigt, dass eine exakt
formulierte Aussage aus den im formalen System verfügbaren Definitionen und
Annahmen folgt. Es zeigt nicht ohne zusätzliche Referenzbindung, Vorhersage,
Messung und Reproduktion, dass die Welt die Voraussetzungen erfüllt. Die
Repository-Seite `docs/LEAN_LAKE_PROOF_STATUS.md` beschreibt diese Trennung
ausdrücklich: formales Theorem, getestete Implementierung, empirische
Beobachtung und externe Wirkung sind unterschiedliche Evidenzklassen.

Die wissenschaftliche Konsequenz ist nicht Skepsis ohne Handeln, sondern
präziseres Handeln. Wenn ein Messmodell etablierten Gesetzen unter einem
bestimmten Gültigkeitsbereich entspricht, darf ein System genau daraus
abgeleitete, gebundene Folgerungen verwenden. Wo Kalibrierung, Datenabdeckung,
kausale Identifikation oder unabhängige Reproduktion fehlen, bleibt der Status
offen, eingeschränkt oder `HOLD`.

## Der REFL-Zyklus als Grammatik verantwortlicher Autonomie

Der REFL-Zyklus macht die Metagrammatik ausführbar. Er trennt die oft
zusammengezogenen Tätigkeiten des Verstehens in überprüfbare Übergänge:

1. **Request** materialisiert einen Intent als Requirement Contract. Scope,
   Erfolgskriterien, harte Grenzen, offene Mehrdeutigkeiten und Autoritäten
   werden sichtbar.

2. **Execute** wählt genau einen autorisierten und im deklarierten
   Zustandsraum sicheren Schritt. Ist die Sicherheit nicht gezeigt, ist
   `HOLD_ACTION_UNJUSTIFIED` sachlich richtiger als Aktionismus.

3. **Follow** beobachtet nicht die beabsichtigte, sondern die tatsächlich
   eingetretene Wirkung. Der resultierende Zustand, ein externer Effekt und
   ein Transportbeleg können verschiedene Subjects und Evidenztypen sein.

4. **Learn** ergänzt oder revidiert das Modell, ohne die Ereignisgeschichte
   umzuschreiben und ohne Anforderungen still zu schwächen. Widerspruch wird
   diagnostiziert, nicht zur Beliebigkeit ausgenutzt.

5. **Repeat Until Done** beendet den Prozess nur, wenn die konkrete
   Abschlussregel für das konkrete Subject erfüllt ist. Andernfalls wird
   wiederholt oder begründet gehalten.

Gerade diese Trennung macht den Zyklus für Menschen und Maschinen gemeinsam
verwendbar. Ein Mensch kann Anforderungen entscheiden und Autorität ausüben.
Eine Maschine kann Varianten suchen, Formalisierungen prüfen, Tests
wiederholen, Belege binden und unzulässige Evidenzsprünge erkennen. Keiner der
beiden Rollen wird dadurch eine Fähigkeit zugeschrieben, die nicht durch den
eigenen Evidenztyp gedeckt ist.

## Eine öffentliche Einladung zur Prüfung statt ein Anspruch auf Unfehlbarkeit

Die kulturelle Bedeutung einer Metagrammatik liegt nicht darin, eine neue
Instanz zu schaffen, der geglaubt werden soll. Ihre Bedeutung liegt darin,
dass sich Ansprüche über Sprache, Software, Wissenschaft und Autonomie in
denselben prüfbaren Fragen ausdrücken lassen. Was war die Anforderung? Was
ist das Subject? Welche Interpretation wurde gewählt? Welche Evidenz trägt
welche Teilbehauptung? Welche Alternative bleibt möglich? Welche Wirkung wurde
tatsächlich beobachtet? Wer hatte die Autorität für den nächsten Schritt?

Eine solche Sprache kann Entwicklung und Forschung robuster machen, weil sie
die produktive Rolle des Nichtwissens bewahrt. `UNKNOWN` ist nicht `false`.
`HOLD` ist nicht Scheitern. Ein Gegenbeispiel ist kein Störfall, sondern
hochwertige Information über die Grenze einer Behauptung. Eine Revision ist
kein Umschreiben der Geschichte, sondern eine neue, begründete Interpretation
auf zusätzlichen oder anders gewichteten Belegen.

TEMDD bietet damit keinen Freibrief, Wahrheit neu zu definieren. Es bietet
einen Rahmen, in dem Freiheit der Lösung und Bindung an Wahrheit zusammen
arbeiten können:

\[
\text{FreedomOfSolution}
\land
\text{NoFreedomToRedefineTruth}.
\]

Die öffentliche, technisch überprüfbare Aufgabe lautet nun, jede weitere
Sprachschicht genau so streng zu behandeln wie ihre Grundidee: Syntax und
Semantik offenlegen, Invarianten formulieren, Gegenbeispiele suchen, den
formalen Satz in Lean/Lake auf einem exakten Subject prüfen, Implementierungen
testen, Wirkungen reobservieren und empirische Aussagen an reale Messung und
unabhängige Reproduktion zurückbinden.

Erst dann wird aus dem Anspruch einer universalen Metagrammatik schrittweise
eine wachsende, maschinenanwendbare und öffentlich prüfbare Infrastruktur des
Verstehens — nicht, weil sie Unfehlbarkeit verspricht, sondern weil sie keine
stärkere Behauptung, Entscheidung oder Handlung zulässt, als gebundene
Evidenz trägt.
