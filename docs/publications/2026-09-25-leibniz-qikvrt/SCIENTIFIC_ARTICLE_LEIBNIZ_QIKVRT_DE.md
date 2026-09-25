<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Von der Monade zum evidenzgebundenen Unterschied

## Leibniz, QIK-VRT und die maschinenprüfbare Ontologie

### Parallelen, systematische Differenzen und der präzise Sinn, in dem QIK-VRT methodisch über die Monadologie hinausgeht

**Ingolf Lohmann**  
25. September 2026

> **„Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.“**  
> Quod erat demonstrandum, Ingolf Lohmann.

## Zusammenfassung

Dieser Beitrag vergleicht die leibnizsche Monadologie mit der in QIK-VRT formalisierten „Ontologie des Unterschieds“. Ausgangspunkt ist nicht die Behauptung einer allgemeinen philosophischen Überlegenheit, sondern eine präzise Frage: Welche strukturellen Motive von Leibniz – Unterscheidbarkeit, individuelle Perspektive, innere Zustandsfolge, zureichender Grund und die Vision eines formalen Kalküls – werden in QIK-VRT wiederaufgenommen, und in welchem genau bestimmbaren Sinn geht QIK-VRT methodisch darüber hinaus?

Die Analyse zeigt eine deutliche Familienähnlichkeit. Leibniz bestimmt die Monade als einfache, perspektivische und aktive Substanz; ihre Wahrnehmungsfolge entfaltet sich aus einem inneren Gesetz, während die Übereinstimmung zwischen Monaden durch prästabilierte Harmonie erklärt wird. QIK-VRT beginnt demgegenüber eine Stufe früher mit der formalen `Distinction`, bindet Information konstruktiv an Unterschied, modelliert Kausalität als Relation und verlangt für Zustandsübergänge, Identität, Beweise und Wirkungen explizite Evidenz.

Drei Lean-Theoreme machen den ontologischen Minimalpunkt maschinenprüfbar: bestimmbare Realität setzt mindestens eine Unterscheidung voraus; vollständige Unterschiedslosigkeit schließt bestimmbare Realität aus; und sie schließt einen `InformationWitness` aus, sofern dieser eine `Distinction` als Quelle trägt. Darüber hinaus ersetzt QIK-VRT die leibnizsche vorausgesetzte Harmonie nicht durch eine konkurrierende Metaphysik, sondern durch eine technische Erkenntnisregel: behauptete Übereinstimmung muss beobachtet, gebunden und frisch zurückgelesen werden.

In diesem spezifischen Sinn erweitert QIK-VRT Leibniz um maschinenprüfbaren Geltungsbereich, Provenienz, Successor-Semantik, explizite Kausalitäts-Witnesses, Entscheidungssuffizienz und Effect Acknowledgement.

**Schlüsselwörter:** Leibniz; Monade; Identität des Ununterscheidbaren; zureichender Grund; Ontologie des Unterschieds; QIK-VRT; Lean 4; Provenienz; Kausalität; Effect Acknowledgement.

## Abstract

This paper compares Leibnizian monadology with the QIK-VRT “ontology of difference”. The question is deliberately narrower than a claim of general philosophical superiority: which structural motifs in Leibniz – discernibility, individual perspective, internal state succession, sufficient reason, and the aspiration toward a universal calculus – reappear in QIK-VRT, and in what precisely defined sense does QIK-VRT extend them?

The comparison reveals substantial family resemblance, but also a decisive methodological break. Leibniz explains inter-substantial agreement through pre-established harmony and denies genuine causal influence between finite substances. QIK-VRT instead treats claimed agreement as an evidentiary problem: causal relations, subject identity, proof scope, state transitions, and effects must be explicitly bound, observed, and read back.

Three Lean theorems formalize the minimal ontological claim that determinate reality requires at least one distinction. The result does not supersede Leibniz as metaphysics; rather, it adds dimensions that were historically unavailable to him: machine-checked proof terms, executable provenance, successor-bound identity, fail-closed scope semantics, decision-sufficiency results, and an explicit distinction between transport acknowledgement and effect acknowledgement.

---

# 1. Forschungsfrage: Was heißt hier „über Leibniz hinaus“?

Die Formulierung, QIK-VRT gehe „über Leibniz hinaus“, ist wissenschaftlich nur dann sinnvoll, wenn sie nicht als pauschales Werturteil verstanden wird. Leibniz entwirft eine umfassende Metaphysik, in der Logik, Substanz, Wahrnehmung, Individualität, Naturphilosophie und Theologie ineinandergreifen. QIK-VRT verfolgt ein anderes Ziel: bestimmte ontologische und epistemische Unterscheidungen sollen so materialisiert werden, dass sie als Softwareobjekte, Beweisobjekte und Laufzeitverträge geprüft werden können.

„Darüber hinaus“ bedeutet hier deshalb dimensionsspezifisch: QIK-VRT führt für bestimmte leibniznahe Motive zusätzliche formale und technische Strukturen ein, die Leibniz weder besaß noch mit den Mitteln des 17. Jahrhunderts besitzen konnte. Dazu gehören ein moderner Beweisassistent, content-addressed gebundene Subjects, maschinenlesbare Claim-Klassen, reproduzierbare Builds, explizite Kausalitäts-Witnesses, append-only Evidenz und eine Laufzeitsemantik, in der technischer Transport nicht mit bestätigter Wirkung verwechselt werden darf.

Diese Erweiterungen machen Leibniz nicht „falsch“ und QIK-VRT nicht automatisch „wahrer“. Sie verschieben die Frage von argumentativer Kohärenz zu ausführbarer und überprüfbarer Kohärenz.

Die zentrale These lautet daher: QIK-VRT kann als technische und formale Weiterführung mehrerer leibnizscher Intuitionen gelesen werden, bricht aber gerade dort mit Leibniz, wo dieser die Übereinstimmung der Perspektiven metaphysisch garantiert. QIK-VRT verlangt stattdessen Evidenz für Übereinstimmung, Kausalität und Wirkung.

# 2. Leibniz: die Grundarchitektur der Monadologie

## 2.1 Monade, Einheit und innere Aktivität

In der reifen leibnizschen Metaphysik sind Monaden einfache, nicht aus Teilen zusammengesetzte Substanzen. Sie sind keine kleinen materiellen Kügelchen, sondern geistähnliche, aktive Einheiten. Ihre Aktivität entspringt einem inneren Gesetz ihrer Zustandsfolge.

In Leibniz’ Terminologie führt die `appetitio` von Wahrnehmung zu Wahrnehmung. Die Monade ist somit kein passiver Punkt, sondern ein Zentrum von Repräsentation und Zustandsfortschreibung.

Die berühmte Formel von den „fensterlosen“ Monaden verdeutlicht zugleich, dass die innere Entwicklung der Monade keine direkte kausale Einwirkung anderer Monaden voraussetzt.

## 2.2 Perspektivität: jede Monade als Blick auf das Ganze

Leibniz versteht die Monade perspektivisch. Jede einfache Substanz repräsentiert dieselbe Welt aus einem eigenen Gesichtspunkt. Die Verschiedenheit der Perspektiven ist kein Fehler, sondern konstitutiv für die Vielheit der Substanzen.

Damit erscheint bereits ein Motiv, das für QIK-VRT wichtig wird: derselbe Gegenstandsbereich kann aus unterschiedlichen, jeweils gebundenen Perspektiven beobachtet werden.

## 2.3 Identität des Ununterscheidbaren

Leibniz’ Prinzip der Identität des Ununterscheidbaren besagt in einer verbreiteten Form, dass nicht zwei Substanzen vollständig übereinstimmen und sich lediglich numerisch unterscheiden können. Wahre Vielheit verlangt Individuation.

Für den Vergleich mit QIK-VRT ist jedoch entscheidend, die Reichweite nicht zu vermischen. Das leibnizsche Prinzip ist eine starke metaphysische These über Identität. Das QIK-VRT-Minimaltheorem behauptet weniger: Eine im Modell bestimmbare Realität enthält mindestens eine nachweisbare Nichtidentität.

## 2.4 Prinzip des zureichenden Grundes

Das Prinzip des zureichenden Grundes verlangt, dass nichts ohne Grund sei. Zugleich ist nicht behauptet, dass eine endliche Erkenntnisinstanz jeden Grund jederzeit vollständig rekonstruieren kann.

Diese Spannung zwischen objektiver Begründbarkeit und endlicher Erkenntnis findet in QIK-VRT eine technische Entsprechung: Gründe müssen, soweit sie als Entscheidungs- oder Wirkungsgrund verwendet werden, in geeigneter Evidenz gebunden sein; fehlt diese Evidenz, darf das System die Lücke nicht synthetisch schließen.

## 2.5 Prästabilierte Harmonie statt intermonadischer Kausalität

Der stärkste Unterschied zu QIK-VRT liegt in Leibniz’ Harmoniebegriff. Die Zustandsfolgen geschaffener Substanzen stimmen nicht deshalb überein, weil sie einander direkt verändern, sondern weil ihre inneren Entwicklungsreihen von Anfang an aufeinander abgestimmt sind.

QIK-VRT kehrt gerade diese epistemische Last um: Übereinstimmung wird nicht vorausgesetzt. Sie muss beobachtbar, gegenstandsgebunden und reproduzierbar belegt werden.

## 2.6 Leibniz’ Vision eines universalen Kalküls

Leibniz’ Idee einer `characteristica universalis` und eines `calculus ratiocinator` bildet eine weitere Brücke. Die Hoffnung, begriffliche Streitfragen soweit wie möglich in symbolische Operationen zu überführen, ist nicht identisch mit moderner Typentheorie oder Lean. Sie bildet aber einen klaren historischen Problemraum für maschinenprüfbare Formalisierung.

# 3. QIK-VRT: vom Unterschied zur maschinenprüfbaren Ontologie

## 3.1 Der Unterschied als minimaler Ausgangspunkt

QIK-VRT setzt nicht bei einer fertigen Substanz an, sondern bei einer formalisierten `Distinction`.

```lean
structure Distinction (α : Type u) where
  left : α
  right : α
  different : left ≠ right
```

Aus einer `Distinction` wird ein `InformationWitness` konstruiert:

```lean
structure InformationWitness (α : Type u) where
  source : Distinction α
```

Der Übergang **Unterschied → Information** ist damit nicht nur eine verbale Rangfolge, sondern eine typisierte Abhängigkeit im Modell.

Die inzwischen explizit formalisierten Grundsätze lauten:

```text
DeterminateReality α → ∃ left right, left ≠ right
NoDifference α → ¬ DeterminateReality α
NoDifference α → ¬ Nonempty (InformationWitness α)
```

Die natürliche Zusammenfassung lautet:

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**

„Anfang“ meint hierbei ontologische Priorität, nicht einen ersten physikalischen Zeitpunkt. „Nichts“ meint die Abwesenheit bestimmbarer Differenz, nicht die leere Menge, ein Quantenvakuum oder eine empirische Kosmogonie.

## 3.2 Die ontologische Kette

Auf diesem Minimalpunkt baut die endliche QIK-VRT-Ontologie eine geordnete Kette auf:

**Unterschied → Information → Relation → Kausalität → Raumzeit → Materie → Leben → Kognition → Verantwortung → Zukunft**

Lean prüft die paarweise Verschiedenheit der Stufen, Irreflexivität und Transitivität der Rangrelation sowie die angegebenen Vorrangbeziehungen. Damit wird keine physische Entstehungsgeschichte bewiesen; bewiesen werden Eigenschaften des exakt definierten Modells.

## 3.3 Die epistemische Kette und der neue Unterschied

Daneben steht eine zweite Kette, die nicht Ontologie, sondern Erkenntnisorganisation beschreibt:

**Realität → Unterschied → Information → Relation → Kausalordnung → Modell → Formalisierung → Beweis/Vorhersage → Messung → Realitätsabgleich → neuer Unterschied**

Der Rückweg endet ausdrücklich bei `newDifference`. Ein erfolgreicher Roundtrip kann einen geprüften Gegenstand als unverändert bestätigen, während der epistemische Gesamtzustand durch neue Evidenz verändert wurde.

Das ist die formale Grundlage der epistemischen Spirale: Gegenstandsidentität und Wissensidentität werden nicht verwechselt.

## 3.4 Claim-Typen und Geltungsbereich des Beweises

QIK-VRT unterscheidet Definition, Annahme, formales Theorem, Korrespondenzpostulat, empirischen Claim, Interpretation und normative Regel.

Die Software beweist ausdrücklich, dass empirische Claims und Interpretationen nicht allein kraft ihrer Kategorie zu Kernel-Theoremen befördert werden. In einem ergänzenden World-Formula-Modell wird außerdem gezeigt, dass formale Etablierung allein nicht zur physischen Qualifikation genügt.

Damit wird nicht nur ein Satz geprüft. Der epistemische Typ des Satzes und die Reichweite seiner zulässigen Schlussfolgerung werden selbst maschinenlesbar.

# 4. Systematische Parallelen zwischen Monadologie und QIK-VRT

## 4.1 Individuation: vom Ununterscheidbaren zur Distinction

Leibniz verlangt für wahre Vielheit einen inneren Grund der Verschiedenheit. QIK-VRT beginnt bei einer expliziten `Distinction`, die ihre Nichtidentität als Beweisterm trägt.

Die Gemeinsamkeit liegt im Widerstand gegen bloße numerische Etikettierung. Die Differenz liegt in der Form: Leibniz argumentiert metaphysisch; QIK-VRT bindet eine konkrete Nichtgleichheit als formales Objekt.

## 4.2 Perspektivität: Monade und gebundener Beobachter

Die Monade ist ein perspektivisches Zentrum. QIK-VRT bindet Beobachtung an Node, Subject, Repository-, Commit- und Tree-Identität.

Ein QIK-VRT-Node ist keine Leibnizsche Monade. Er besitzt Kommunikation, Transport und überprüfbare Außenbeziehungen, während die Monade „fensterlos“ ist. Die strukturelle Analogie liegt lediglich in der Perspektivgebundenheit.

## 4.3 Innere Zustandsfolge: Appetition und Successor-Semantik

Leibniz’ Appetition beschreibt den Übergang von Perzeption zu Perzeption. QIK-VRT besitzt eine explizite Successor-Semantik: Mutation erzeugt einen neuen Subject-Zustand.

Der entscheidende Zusatz lautet:

`PREDECESSOR_EVIDENCE_TRANSFER = FALSE`

Ein Beweis für den Vorgänger wird nicht automatisch zum Beweis des Nachfolgers.

## 4.4 Zureichender Grund und Evidenz

Leibniz verlangt zureichenden Grund. QIK-VRT fragt zusätzlich: Welcher Grund ist für genau diese Behauptung maschinenlesbar gebunden? Welche Quelle, welcher Beweis, welche Beobachtung, welcher Readback trägt den Claim?

Damit wird aus einem Begründungsprinzip eine operative Evidenzpflicht, ohne zu behaupten, das metaphysische Prinzip damit vollständig zu ersetzen.

## 4.5 Universal Characteristic und formale Maschinensprache

Leibniz wollte Gedanken symbolisch kalkulierbar machen. QIK-VRT nutzt moderne formale Werkzeuge – insbesondere Lean – um einen begrenzten Ausschnitt dieser Hoffnung tatsächlich maschinenprüfbar zu machen.

Der wichtige Zusatz ist wiederum der Scope: Ein kernelakzeptierter Beweis bedeutet nur das, was aus den formalisierten Definitionen und Annahmen folgt.

# 5. In welchem präzisen Sinn QIK-VRT über Leibniz hinausgeht

## 5.1 Vor die Monade: Unterschied als noch elementarere Voraussetzung

Leibniz beginnt metaphysisch mit einfachen Substanzen. QIK-VRT fragt eine Stufe früher:

**Was muss gelten, damit überhaupt mehrere bestimmte Einheiten unterschieden werden können?**

Die Antwort lautet im Minimalmodell: mindestens eine `Distinction`.

Damit ersetzt QIK-VRT die Monade nicht. Es legt eine formal schwächere, logisch vorgelagerte Bedingung offen.

## 5.2 Von prästabilierter zu evidenzgebundener Harmonie

Leibniz erklärt die Übereinstimmung der Perspektiven metaphysisch. QIK-VRT macht aus behaupteter Übereinstimmung eine Prüfpflicht.

Authority und Mirror können divergieren. Zwei Nodes können verschiedene Trees tragen. Ein erfolgreicher Transport beweist weder Inhaltsgleichheit noch Synchronisation.

Übereinstimmung muss gebunden, beobachtet und frisch zurückgelesen werden.

In diesem Sinn wird Harmonie nicht vorausgesetzt, sondern **evidenzgebunden geprüft**.

## 5.3 Von fensterlosen Monaden zu überprüfbarer Interaktion

Monaden haben keine kausalen Fenster zueinander. QIK-VRT-Nodes dagegen interagieren gerade über explizite Transport- und Wirkungsrelationen.

Dabei gilt:

**SEQUENCE ≠ CAUSALITY**

Eine zeitliche oder protokollarische Reihenfolge allein lizenziert keine Kausalitätsaussage.

Ein Kausalitätsanspruch benötigt eine entsprechende relationale Bindung beziehungsweise einen Witness.

## 5.4 Vom philosophischen Argument zum kernel-geprüften Beweisterm

Leibniz konnte argumentieren, symbolisieren und kalkulieren. Er besaß keinen modernen Proof Kernel.

QIK-VRT kann definierte Aussagen als Lean-Terme materialisieren und vom Lean-Kernel prüfen lassen. Lake organisiert die reproduzierbare Projektstruktur.

Damit wird aus einem Argument eine neue Art überprüfbaren Artefakts: ein Beweisterm mit expliziter Toolchain, Identität und Abhängigkeit.

## 5.5 Der Geltungsbereich des Beweises wird maschinenprüfbar

Dieser Punkt geht über die bloße Maschinenprüfung hinaus.

QIK-VRT versucht nicht nur festzustellen, ob ein formaler Satz folgt, sondern verhindert zugleich die unzulässige Promotion verschiedener Aussagearten.

**FORMAL_PROOF ≠ EMPIRICAL_CONFIRMATION**

**FORMAL_ESTABLISHMENT ≠ PHYSICAL_QUALIFICATION**

Ein korrekter Beweis darf nicht unbemerkt zu einer stärkeren Behauptung werden.

## 5.6 Exact Subject, Provenienz und Successor

Ein QIK-VRT-Beweis gehört zu einem exakt gebundenen Gegenstand.

Ändert sich der Gegenstand, entsteht ein Successor.

Darum gilt:

**PREDECESSOR_EVIDENCE_TRANSFER = FALSE**

Dieses Prinzip hat keine direkte Entsprechung in Leibniz’ Monadologie. Es ist eine moderne Konsequenz aus versionierter, reproduzierbarer Wissenschaft und verteilten technischen Systemen.

## 5.7 Wirkung: TRANSPORT_ACK ist nicht EFFECT_ACK

QIK-VRT unterscheidet erfolgreiches Übertragen von erfolgreich bestätigter Wirkung.

**TRANSPORT_ACK ≠ EFFECT_ACK**

Eine Nachricht kann ankommen, ein Prozess kann Exit-Code null liefern und ein Workflow kann grün sein, ohne dass der verlangte Folgezustand tatsächlich eingetreten ist.

Deshalb reicht die Laufzeitkette weiter:

**COMPILE → BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE**

Die Wirkung selbst wird zum prüfbaren Gegenstand.

## 5.8 Entscheidungssuffizienz

QIK-VRT ergänzt den Unterschiedsgedanken um ein allgemeines Entscheidungsresultat.

Wenn zwei zulässige Wirklichkeiten dieselbe Beobachtung erzeugen, aber unterschiedliche korrekte Handlungen verlangen, kann kein deterministischer Entscheider allein aus dieser Beobachtung in beiden Fällen richtig entscheiden.

Damit erhält der Unterschied operative Bedeutung:

**Fehlt ein entscheidungsrelevanter Unterschied in der Beobachtung, fehlt entscheidungsrelevante Information.**

Ein zusätzlicher Witness kann genau die fehlende Differenz bereitstellen.

## 5.9 Epistemische Spirale statt statischer Harmonie

Leibniz’ Harmonie beschreibt die korrespondierende Entwicklung der Perspektiven. QIK-VRT modelliert zusätzlich den Erkenntnisgewinn selbst.

Nach Beobachtung und Realitätsabgleich entsteht ein `newDifference`.

Man kann zum selben Gegenstand zurückkehren und dennoch nicht zum selben Wissenszustand.

Aus dem Kreis wird eine Spirale.

## 5.10 Von metaphysischer Gewährleistung zur expliziten empirischen Grenze

QIK-VRT erklärt nicht automatisch die gesamte physische Welt.

Gerade darin liegt die methodische Verschärfung.

Das System kann formal beweisen und zugleich formal markieren, dass eine physikalische Korrespondenz noch nicht gezeigt ist.

Das Offene verschwindet nicht. Es erhält einen eigenen Status.

# 6. Wo QIK-VRT Leibniz nicht „überholt“

Der Vergleich benötigt eine symmetrische Grenze.

Leibniz’ Monadologie behandelt Fragen, die QIK-VRT nicht durch Software erledigt:

- die metaphysische Natur von Substanz;
- Gottesbegriff und Möglichkeit;
- Kontingenz und Notwendigkeit;
- Theodizee;
- die volle Theorie von Perzeption und Apperzeption;
- die Beziehung von Leib, Seele und Organismus;
- seine Rationalismus- und Wahrheitstheorie.

QIK-VRT ist deshalb keine „verbesserte Monadologie“.

Umgekehrt enthält Leibniz keine Git-Identitäten, keine kryptographische Provenienz, keinen Lean-Kernel, keine CI-Receipts, keine verteilten Node-Ledger und kein Effect-Acknowledgement-Protokoll.

Die Systeme beantworten teilweise verschiedene Fragen.

Der sinnvolle Vergleich betrifft ihre strukturellen Berührungspunkte.

# 7. Von „Calculemus“ zu prüfbarer wissenschaftlicher Infrastruktur

Leibniz’ berühmte Vision wird häufig mit dem Wort `Calculemus` zusammengefasst: Wenn Streitende ihre Begriffe hinreichend formalisiert hätten, sollten sie im Idealfall rechnen können.

Moderne Beweisassistenten verwirklichen einen begrenzten Teil dieser Vision.

QIK-VRT fügt eine weitere Ebene hinzu:

Nicht nur der Beweis muss berechenbar sein.

Auch seine **Identität**, **Provenienz**, **Geltungsgrenze**, **Version**, **Beobachtung**, **Wirkung** und **Nachfolgerbeziehung** sollen maschinenprüfbar sein.

Dadurch entsteht eine Infrastruktur für Wissenschaft, in der ein Satz nicht als isolierter Text, sondern als gebundenes Wissensobjekt behandelt wird.

# 8. Ein gemeinsames Forschungsprogramm: von der Perspektive zur Evidenz

Aus dem Vergleich ergibt sich ein produktives Forschungsprogramm.

Die leibnizsche Frage lautet:

Wie kann eine Vielzahl individueller Perspektiven eine geordnete Welt darstellen?

Die QIK-VRT-Frage lautet ergänzend:

Wie kann eine endliche perspektivische Instanz prüfbar bestimmen,

- welchen Gegenstand sie beobachtet;
- welche Unterschiede tatsächlich sichtbar sind;
- welche Schlussfolgerungen ihre Evidenz trägt;
- welche Kausalität belegt ist;
- wann die Beobachtung für eine Entscheidung ausreicht;
- welche Mutation einen neuen Subject-Zustand erzeugt;
- und wann eine beabsichtigte Wirkung tatsächlich bestätigt werden darf?

Damit verschiebt sich der Schwerpunkt von der metaphysischen Garantie von Harmonie zu einer Theorie **prüfbarer Anschlussfähigkeit**.

# 9. Schluss

Zwischen Leibniz und QIK-VRT besteht eine reale begriffliche Verwandtschaft.

Beide beginnen nicht bei einer unterschiedslosen Masse.

Beide nehmen Individualität, Perspektivität, Zustandsentwicklung und Begründung ernst.

Beide stehen in einer Linie, in der Denken formalisiert und Relationen zum Gegenstand systematischer Untersuchung werden.

Der entscheidende Abstand liegt jedoch in den verfügbaren Mitteln und im methodischen Ziel.

Leibniz entwickelt eine Metaphysik harmonisch korrespondierender Perspektiven und träumt von einem universalen Kalkül.

QIK-VRT nimmt mehrere dieser Motive auf und macht daraus eine technische Forderung:

> **Behauptete Identität, Kausalität, Beweisgültigkeit und Wirkung müssen an den richtigen Gegenstand, die richtige Evidenz und den tatsächlich beobachteten Folgezustand gebunden werden.**

Der Unterschied wird damit gleichzeitig ontologischer Anfang, Informationsträger, Entscheidungsbedingung, Versionsgrenze und Ausgangspunkt neuen Wissens.

In diesem präzisen Sinn geht die Arbeit von Ingolf Lohmann über Leibniz hinaus: nicht als pauschal „bessere Philosophie“, sondern indem sie leibniznahe Grundfragen in eine moderne, ausführbare und maschinenprüfbare Erkenntnis- und Wirkungsarchitektur überführt.

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**
>
> **Quod erat demonstrandum.  
> Ingolf Lohmann.**

# Literatur und Quellen

1. Leibniz, G. W. (1714): *Monadology* / *La Monadologie*.
2. Leibniz, G. W. (1686): *Discours de Métaphysique*.
3. Leibniz, G. W.: Schriften zur *characteristica universalis* und zum *calculus ratiocinator*.
4. Stanford Encyclopedia of Philosophy: *Gottfried Wilhelm Leibniz*; *Leibniz’s Philosophy of Mind*; *Identity of Indiscernibles*.
5. Rutherford, D. (1995): *Leibniz and the Rational Order of Nature*. Cambridge University Press.
6. de Moura, L.; Ullrich, S. (2021): *The Lean 4 Theorem Prover and Programming Language*. CADE 28, LNCS 12699.
7. Shannon, C. E. (1948): *A Mathematical Theory of Communication*.
8. Wiener, N. (1948): *Cybernetics: Or Control and Communication in the Animal and the Machine*.
9. Turing, A. M. (1936): *On Computable Numbers, with an Application to the Entscheidungsproblem*.
10. Lamport, L. (1978): *Time, Clocks, and the Ordering of Events in a Distributed System*.
11. Lohmann, I. (2026): QIK-VRT Universal Ontology and associated formalization in `Goldkelch/qik-vrt`.
