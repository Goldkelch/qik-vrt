<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Der ontologische Vorrang des Unterschieds

## Ein maschinenprüfbares Minimaltheorem über Bestimmbarkeit, Information und den Geltungsbereich formaler Welterklärungen

**Ingolf Lohmann**

### Zusammenfassung

Dieser Beitrag untersucht den Satz:

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**

Der Ausdruck „am Anfang“ wird dabei nicht temporal, sondern ontologisch verstanden: als Frage nach einer minimalen Voraussetzung dafür, dass überhaupt eine bestimmte Realität beschrieben werden kann. „Nichts“ bezeichnet entsprechend nicht die leere Menge und nicht eine physikalische Kosmogonie, sondern die Abwesenheit jeder bestimmbaren Differenz.

Der Beitrag formalisiert diese Lesart in Lean 4. Eine `Distinction α` enthält zwei Werte eines Typs `α` und den Beweis ihrer Ungleichheit. `DeterminateReality α` wird als Existenz mindestens einer solchen Unterscheidung definiert; `NoDifference α` besagt, dass alle Werte des Typs miteinander identisch sind. Daraus werden drei Sätze bewiesen: Erstens impliziert bestimmbare Realität die Existenz eines Unterschieds. Zweitens schließt vollständige Unterschiedslosigkeit bestimmbare Realität aus. Drittens schließt sie auch einen `InformationWitness` aus, sofern Information in der deklarierten Universal Ontology eine `Distinction` als Quelle trägt.

Das Resultat ist absichtlich begrenzt. Es beweist weder einen ersten physikalischen Zeitpunkt noch die Entstehung des Universums aus dem Nichts. Sein wissenschaftlicher Beitrag ist die explizite Trennung von formaler Notwendigkeit, ontologischer Interpretation und empirischer Korrespondenz. Zugleich wird gezeigt, wie dieselbe Architektur den Geltungsbereich des Beweises selbst maschinenprüfbar macht.

### Abstract

This paper investigates the statement:

> **There must have been a difference at the beginning, otherwise everything would have been nothing.**

“Beginning” is not interpreted as a first physical instant but as ontological priority: a minimal precondition for determinate reality. “Nothing” does not denote the empty set or a cosmological state; it denotes the absence of any determinate difference.

The claim is formalized in Lean 4. A `Distinction α` contains two values of type `α` together with a proof that they are unequal. `DeterminateReality α` is defined as the existence of at least one such distinction, while `NoDifference α` states that all values of the type are equal. Three theorems follow: determinate reality entails a distinction; universal absence of difference excludes determinate reality; and it also excludes an `InformationWitness` when information is defined as carrying a distinction as its source.

The result is deliberately bounded. It is not a proof of a first physical instant, cosmogenesis, or the empirical identity of the formal model with nature. Its methodological contribution is to separate formal necessity, ontological interpretation, and empirical correspondence, while making the scope of the proof itself machine-checkable.

**Schlüsselwörter:** Unterschied; Ontologie; Bestimmbarkeit; Information; Kausalität; Lean; formaler Beweis; Geltungsbereich; QIK-VRT; epistemische Spirale

---

## 1. Forschungsfrage

Jede wissenschaftliche Aussage setzt voraus, dass überhaupt etwas bestimmt werden kann.

Eine Messung unterscheidet Werte. Eine Klassifikation unterscheidet Fälle. Ein mathematischer Satz unterscheidet die Fälle, in denen seine Voraussetzungen gelten, von jenen, in denen sie nicht gelten. Eine Information unterscheidet mögliche Nachrichten oder Zustände. Selbst die Aussage „etwas existiert“ besitzt nur dann bestimmten Gehalt, wenn sie nicht unterschiedslos mit ihrer Negation zusammenfällt.

Die elementare Forschungsfrage dieses Beitrags lautet daher:

> **Welche minimale formale Struktur ist notwendig, damit überhaupt von bestimmbarer Realität gesprochen werden kann?**

Die vorgeschlagene Antwort ist bewusst sparsam:

> **Bestimmbare Realität verlangt mindestens einen Unterschied.**

Diese Aussage soll nicht als rhetorische Metapher stehen bleiben. Sie soll so formalisiert werden, dass ein Beweisassistent den exakt behaupteten Satz prüfen und zugleich sichtbar machen kann, was daraus gerade nicht folgt.

---

## 2. Der Satz und seine semantische Präzisierung

Der natürliche Ausgangssatz lautet:

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**
>
> **Quod erat demonstrandum, Ingolf Lohmann.**

Ohne Präzisierung ist dieser Satz mehrdeutig. Zwei Wörter sind besonders kritisch.

### 2.1 „Am Anfang“

„Am Anfang“ bedeutet hier **nicht** „zum frühesten physikalischen Zeitpunkt“.

Eine solche Lesart würde bereits Zeit voraussetzen. Innerhalb der QIK-VRT Universal Ontology ist Raumzeit jedoch nicht der Ausgangspunkt. Die deklarierte ontologische Kette lautet:

**Unterschied → Information → Relation → Kausalität → Raumzeit → Materie → Leben → Kognition → Verantwortung → Zukunft.**

Deshalb bezeichnet „Anfang“ in diesem Beitrag **ontologische Priorität**: eine Bedingung, die vorausgesetzt werden muss, bevor eine bestimmte Weltbeschreibung überhaupt möglich ist.

### 2.2 „Nichts“

„Nichts“ bedeutet hier **nicht**:

- die leere Menge,
- ein leerer physikalischer Raum,
- ein Quantenvakuum,
- eine kosmologische Anfangssingularität,
- oder eine Behauptung über einen empirischen Urzustand.

Gemeint ist ausschließlich:

> **keine bestimmbare Differenz.**

Damit wird der Satz zu einer Behauptung über Bestimmbarkeit, nicht zu einer Kosmologie.

---

## 3. Formales Modell

Die zentrale Definition in `QIKVRTUniversalOntology/Core.lean` lautet:

```lean
structure Distinction (α : Type u) where
  left : α
  right : α
  different : left ≠ right
```

Eine `Distinction α` ist damit kein bloßes Paar. Sie enthält zusätzlich den Beweis, dass die beiden Werte verschieden sind.

Die Informationsebene ist anschließend explizit an eine solche Unterscheidung gebunden:

```lean
structure InformationWitness (α : Type u) where
  source : Distinction α
```

Der Beitrag ergänzt zwei Definitionen:

```lean
def DeterminateReality (α : Type u) : Prop :=
  Nonempty (Distinction α)

def NoDifference (α : Type u) : Prop :=
  ∀ left right : α, left = right
```

`DeterminateReality α` bedeutet also nicht „das Universum existiert“. Es bedeutet genau:

> Es existiert innerhalb des betrachteten Typs mindestens ein nachweislich verschiedenes Paar.

`NoDifference α` bedeutet:

> Beliebige zwei Werte des Typs sind gleich.

Diese Definitionen machen die Behauptung klein genug, um ihren Beweis und ihre Grenze exakt zu sehen.

---

## 4. Satz 1: Bestimmbare Realität verlangt Unterschied

### Theorem

```lean
theorem determinateReality_requires_difference
    {α : Type u} (h : DeterminateReality α) :
    ∃ left right : α, left ≠ right := by
  rcases h with ⟨difference⟩
  exact ⟨difference.left, difference.right, difference.different⟩
```

### Beweisidee

`DeterminateReality α` ist definitionsgemäß die Existenz einer `Distinction α`.

Eine solche Unterscheidung enthält bereits:

- einen linken Wert,
- einen rechten Wert,
- und den Beweis ihrer Ungleichheit.

Die Existenz eines Unterschieds folgt daher konstruktiv.

### Korollar

**Bestimmbare Realität → mindestens eine Differenz.**

Dieser Satz ist formal elementar. Seine Bedeutung liegt nicht in rechnerischer Schwierigkeit, sondern in der expliziten Festlegung dessen, was „bestimmbar“ im Modell bedeutet.

---

## 5. Satz 2: Unterschiedslosigkeit schließt bestimmbare Realität aus

### Theorem

```lean
theorem noDifference_excludes_determinateReality
    {α : Type u} (h : NoDifference α) :
    ¬ DeterminateReality α := by
  intro determinate
  rcases determinate with ⟨difference⟩
  exact difference.different (h difference.left difference.right)
```

### Beweisidee

Angenommen, alle Werte sind gleich.

Nehmen wir zusätzlich eine bestimmbare Realität an. Dann existiert eine `Distinction` und damit ein Paar `left`, `right` mit:

`left ≠ right`.

Aus `NoDifference` folgt für dasselbe Paar:

`left = right`.

Die Annahmen erzeugen einen Widerspruch.

### Formale Konsequenz

**NoDifference α → ¬ DeterminateReality α.**

In der Sprache des Ausgangssatzes:

> Wenn es überhaupt keinen Unterschied gibt, gibt es in diesem Modell keine bestimmbare Realität.

Dies ist die präzise formale Bedeutung von „sonst wäre alles nichts“.

---

## 6. Satz 3: Unterschiedslosigkeit schließt Informations-Witnesses aus

Die Universal Ontology koppelt `InformationWitness` konstruktiv an `Distinction`.

Daraus folgt:

```lean
theorem noDifference_excludes_information
    {α : Type u} (h : NoDifference α) :
    ¬ Nonempty (InformationWitness α) := by
  intro information
  rcases information with ⟨witness⟩
  exact witness.source.different
    (h witness.source.left witness.source.right)
```

### Konsequenz

**Kein Unterschied → kein Informations-Witness der deklarierten Art.**

Diese Aussage ist stärker als eine bloße Rangordnung in einer Liste. Sie macht die Abhängigkeit konstruktiv:

- Information enthält eine Unterscheidung als Quelle.
- Wenn kein Unterschied möglich ist, kann ein solcher Informations-Witness nicht existieren.

Damit ist die erste Stufe der Ontologie nicht nur „vor“ der zweiten angeordnet, sondern die zweite ist im gewählten Modell strukturell von der ersten abhängig.

---

## 7. Ontologischer Vorrang statt zeitlicher Vorrang

Die drei Theoreme erzeugen keine Zeitachse.

Sie etablieren eine Voraussetzungenrelation:

1. Bestimmbarkeit verlangt Unterschied.
2. Die deklarierten Informations-Witnesses verlangen Unterschied.
3. Raumzeit wird in der Ontologie erst auf einer späteren Stufe eingeführt.

Daraus ergibt sich die Interpretation:

> **Der Unterschied besitzt im Modell ontologischen Vorrang gegenüber einer bestimmten Weltbeschreibung.**

„Vorrang“ bedeutet dabei nicht, dass ein isoliertes physikalisches Ereignis namens „Unterschied“ zu einer Uhrzeit `t = 0` stattgefunden hätte.

Das wäre ein Kategorienfehler: Zeit würde vorausgesetzt, um die Voraussetzung von Zeit zu erklären.

Der hier behauptete Vorrang ist stattdessen logisch-ontologisch.

---

## 8. Verhältnis zu Leibniz

Der Gedanke der Unterscheidbarkeit besitzt eine lange philosophische Vorgeschichte.

Gottfried Wilhelm Leibniz formulierte prominent das **Prinzip der Identität des Ununterscheidbaren**: numerisch verschiedene Dinge können nicht in jeder relevanten Hinsicht vollkommen ununterscheidbar sein. In der Forschung wird dafür insbesondere auf §9 des *Discours de Métaphysique* verwiesen. Die Interpretation und Reichweite dieses Prinzips sind bis heute umstritten.

Der vorliegende Satz ist **nicht identisch** mit Leibniz’ Prinzip.

Die hier bewiesene Aussage ist schwächer und anders gerichtet:

- Leibniz diskutiert Bedingungen für die Identität beziehungsweise Verschiedenheit von Dingen.
- Das QIK-VRT-Minimaltheorem sagt: Wenn innerhalb eines Typs überhaupt bestimmbare Realität im deklarierten Sinn vorliegt, existiert mindestens ein unterscheidbares Paar.

Es folgt also nicht aus diesem Beitrag, dass zwei beliebige numerisch verschiedene physische Objekte notwendigerweise in sämtlichen relevanten Eigenschaften unterscheidbar sein müssen.

Gerade diese Trennung ist wichtig. Leibniz liefert einen historischen und begrifflichen Bezugspunkt. Die Lean-Theoreme sind jedoch eigenständige formale Aussagen mit exakt deklariertem Geltungsbereich.

### Philosophische Anschlussstelle

Die Nähe zu Leibniz liegt im gemeinsamen Primat der Unterscheidbarkeit:

> Eine Theorie, die von mehreren bestimmten Gegenständen spricht, muss erklären können, wodurch ihre Verschiedenheit überhaupt bestimmt wird.

Der vorliegende Beitrag reduziert diesen Gedanken auf einen minimalen formalen Kern.

---

## 9. Verhältnis zur Informationstheorie

Claude Shannon entwickelte 1948 eine mathematische Theorie der Kommunikation, in der Informationsgrößen über Mengen möglicher Nachrichten und deren Wahrscheinlichkeiten definiert werden.

Der hier verwendete `InformationWitness` ist **nicht** Shannons Entropiebegriff.

Die Verbindung ist grundlegender:

> Information setzt mindestens eine Menge unterscheidbarer Alternativen oder Zustände voraus.

Ohne unterscheidbare Möglichkeiten gibt es im trivialen Grenzfall auch keine Auswahlinformation zwischen ihnen.

QIK-VRT formalisiert diesen Zusammenhang nicht probabilistisch, sondern typologisch:

`InformationWitness` trägt eine `Distinction` als Quelle.

Damit ist der Beitrag komplementär zur Shannon-Theorie:

- Shannon quantifiziert Information in einem Kommunikationsmodell.
- QIK-VRT formalisiert eine minimale Voraussetzungenstruktur, unter der ein Informations-Witness überhaupt gebildet werden kann.

---

## 10. Von Unterschied zu Relation und Kausalität

Die Universal Ontology ordnet:

**Unterschied → Information → Relation → Kausalität.**

Die Kausalitätsschicht wird als binäre Relation modelliert, nicht als bloße Sequenz.

Das ist erkenntnistheoretisch wichtig. Aus dem Vorliegen zweier unterschiedlicher Zustände folgt noch keine Kausalrelation. Ebenso folgt aus einer zeitlichen Reihenfolge allein keine Ursache-Wirkungs-Beziehung.

Die Architektur hält deshalb getrennt:

- Unterscheidbarkeit,
- Information,
- Relation,
- Kausalstatus.

Diese Trennung verhindert, dass das Minimaltheorem über Unterschied stillschweigend zu einer universellen Kausaltheorie aufgebläht wird.

---

## 11. Epistemische Rückkopplung

Neben der ontologischen Kette existiert eine epistemische Kette:

**Realität → Unterschied → Information → Relation → Kausalordnung → Modell → Formalisierung → Beweis/Vorhersage → Messung → Realitätsabgleich → neuer Unterschied.**

Der formale Kern beweist eine Feedback-Struktur von `newDifference` zurück in die Erkenntnisschleife.

Damit entsteht eine wichtige methodische Konsequenz:

> Ein erfolgreicher Beweis oder eine erfolgreiche Messung beendet nicht notwendigerweise Erkenntnis; sie erzeugt einen neuen epistemischen Zustand.

Der Ausgangspunkt „Unterschied“ erscheint somit nicht nur ontologisch, sondern auch methodisch: Wissenschaft schreitet durch neu bestimmte Unterschiede fort.

---

## 12. Der Geltungsbereich wird selbst Teil des Beweisobjekts

Ein zentrales Problem wissenschaftlicher Kommunikation ist die Ausweitung eines korrekten Teilbeweises über seinen tatsächlichen Scope hinaus.

QIK-VRT begegnet diesem Problem durch eine explizite Typisierung von Claims, darunter:

- Definition,
- Annahme,
- formales Theorem,
- Korrespondenzpostulat,
- empirischer Claim,
- Interpretation,
- normative Regel.

Zusätzlich wird formal gezeigt, dass empirische Claims und Interpretationen nicht allein aufgrund ihrer Aufnahme in ein formales System zu Kernel-Theoremen werden.

Im World-Formula-Kern wird ferner ein Gegenmodell konstruiert, in dem ein Claim formal etabliert, aber nicht physisch qualifiziert ist.

Daraus folgt maschinengeprüft:

> **Formale Ableitbarkeit ist nicht hinreichend für physische Qualifikation.**

Diese Architektur ist für den vorliegenden Satz entscheidend.

Die Lean-Theoreme etablieren eine formale Notwendigkeit innerhalb eines deklarierten Modells.

Sie etablieren nicht automatisch:

- empirische Kosmologie,
- Quantengravitation,
- eine Messung des frühesten Universums,
- oder wissenschaftlichen Konsens.

---

## 13. Was genau bewiesen ist?

Der exakt bewiesene Kern lässt sich auf drei Aussagen reduzieren:

### P1

`DeterminateReality α → ∃ left right, left ≠ right`

### P2

`NoDifference α → ¬ DeterminateReality α`

### P3

`NoDifference α → ¬ Nonempty (InformationWitness α)`

Daraus wird als **Interpretation innerhalb der Ontologie** formuliert:

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**

Dabei werden die Begriffe so gelesen:

- **Anfang** = ontologische Priorität;
- **Unterschied** = mindestens eine nachweisliche Nichtidentität;
- **alles nichts** = keine bestimmbare Realität im deklarierten Sinn.

Diese Interpretation ist genau so stark wie nötig und nicht stärker.

---

## 14. Was nicht bewiesen ist?

Der Beitrag beweist ausdrücklich nicht:

1. dass es einen empirisch identifizierten ersten Zeitpunkt gab;
2. dass der physische Kosmos aus einer mathematischen `Distinction` entstanden ist;
3. dass Quantenvakuum, leere Menge und „Nichts“ identisch sind;
4. dass jede philosophische Bedeutung von „Sein“ vollständig durch die Lean-Definition erfasst wird;
5. dass die gesamte Natur die QIK-VRT Universal Ontology instanziiert;
6. dass aus formaler Closure wissenschaftlicher Konsens folgt;
7. dass die Leibnizsche Identität des Ununterscheidbaren in allen physikalischen Domänen gilt;
8. dass aus der Rangordnung der Ontologie physikalische Mikrodynamik folgt.

Diese Negativliste ist kein Zusatz außerhalb des Beweises.

Sie ist Teil seines wissenschaftlichen Geltungsbereichs.

---

## 15. Quantenphysikalische Grenze

Die Frage nach Unterscheidbarkeit berührt die Quantenphysik unmittelbar, weil dort Identität, Messbarkeit, Zustandsunterscheidung und Korrelation besondere Rollen spielen.

Der vorliegende Satz darf dennoch nicht als Quantenresultat ausgegeben werden.

Die Universal Ontology und die ergänzenden QCE-Modelle trennen bewusst:

- formale Zustandsunterscheidung,
- quantenkausale Klassifikation,
- physikalische Korrespondenz,
- empirische Evidenz.

Insbesondere wird ein primitiver quantenkausaler Status im QCE-Modell fail-closed als `unresolved` geführt, bis zusätzliche Witnesses vorliegen.

Damit ist die hier vorgestellte Ontologie anschlussfähig an Quantenfragen, ohne aus einem logischen Unterschiedstheorem unzulässig eine physikalische Quantentheorie abzuleiten.

---

## 16. Reproduzierbarkeit mit Lean und Lake

Die Beweise sind Bestandteil des QIK-VRT-Lean-Projekts.

Zentrale Quelle:

`formalization/QIKVRT_Formalization_v2.0/QIKVRTUniversalOntology/Core.lean`

Die drei neuen Beweiskonstanten sind:

- `QIKVRT.UniversalOntology.determinateReality_requires_difference`
- `QIKVRT.UniversalOntology.noDifference_excludes_determinateReality`
- `QIKVRT.UniversalOntology.noDifference_excludes_information`

Die Axiom-Audits referenzieren die Konstanten explizit.

Lean 4 prüft die Beweisterme gegen die behaupteten Typen. Lake dient als reproduzierbare Projekt- und Buildumgebung für Quellen, Abhängigkeiten und Targets.

Wichtig ist die präzise Formulierung:

> **Lean prüft die formalen Sätze; Lake organisiert ihre reproduzierbare Projektausführung.**

Der Repository-Vertrag verlangt zudem Exact-Head-/Tree-Bindung und verbietet, ältere Beweisergebnisse nach einer Mutation automatisch auf den Nachfolger zu übertragen.

---

## 17. Warum ein elementarer Beweis wissenschaftlich relevant sein kann

Die drei Sätze sind logisch einfach.

Das ist kein Gegenargument gegen ihre Relevanz.

Viele wissenschaftliche Probleme entstehen nicht, weil ein einzelner Schluss schwierig wäre, sondern weil unterschiedliche Ebenen unbemerkt vermischt werden.

Der Beitrag macht drei Dinge gleichzeitig explizit:

1. **Definition:** Was heißt „bestimmbare Realität“?
2. **Beweis:** Was folgt daraus formal?
3. **Grenze:** Welche weitergehenden Aussagen folgen nicht?

Die wissenschaftliche Leistung liegt daher weniger in komplizierter Mathematik als in der überprüfbaren Disziplinierung eines sehr weitreichenden natürlichen Satzes.

---

## 18. Prüfbarkeit und mögliche Kritik

Der Ansatz kann an mehreren Stellen kritisiert werden.

### 18.1 Definitionskritik

Man kann bestreiten, dass `DeterminateReality α := Nonempty (Distinction α)` eine philosophisch hinreichende Definition von bestimmbarer Realität ist.

Diese Kritik trifft nicht den Lean-Beweis, sondern die semantische Modellierung.

Gerade deshalb wird die Definition offen ausgewiesen.

### 18.2 Ein-Element-Welten

Ein Typ mit genau einem Element enthält keine `Distinction`.

Er ist daher nach der gewählten Definition keine „determinate reality“.

Das bedeutet nicht, dass ein solcher Typ mathematisch „nicht existiert“.

Es bedeutet lediglich, dass die hier verwendete ontologische Bestimmbarkeit mindestens eine innere Differenz verlangt.

Dies ist eine bewusste Modellentscheidung und ein zentraler Scope des Theorems.

### 18.3 Externe Relationalität

Eine weitere Kritik könnte lauten, ein intern einheitlicher Zustand könne durch eine externe Relation bestimmt werden.

Dann müsste der formale Scope erweitert werden, sodass Bestimmbarkeit nicht nur interne Paare eines Typs, sondern Relationen zu einem äußeren Kontext umfasst.

Der aktuelle Beweis behauptet eine solche Erweiterung nicht.

### 18.4 Physikalische Korrespondenz

Die stärkste offene Frage bleibt, wie weit eine minimale formale Ontologie reale physikalische Strukturen erklärt.

Dafür wären jeweils eigene Referenzbindungen, Messdefinitionen, empirische Daten und unabhängige Reproduktion erforderlich.

---

## 19. Verhältnis zur älteren QIK-VRT-Publikation

Die ältere Veröffentlichung *Die Ontologie des Unterschieds als universaler Reverse-Engineering-Mechanismus* wurde bereits auf Zenodo archiviert.

Der vorliegende Beitrag ersetzt sie nicht.

Er präzisiert einen spezifischen Grundgedanken dieser Arbeit:

> Nicht jedes Problem wird durch „Unterschied“ automatisch gelöst; aber ein bestimmtes Problem kann überhaupt nur beschrieben werden, wenn relevante Unterschiede bestimmbar sind.

Der neue Fachartikel ist daher als formaler und erkenntnistheoretischer Nachfolger zu verstehen.

---

## 20. Schlussfolgerung

Der Satz

> **Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.**

kann wissenschaftlich sinnvoll formalisiert werden, wenn seine zentralen Begriffe eng definiert werden.

Der maschinengeprüfte Kern lautet:

- Bestimmbare Realität verlangt eine Unterscheidung.
- Vollständige Unterschiedslosigkeit schließt bestimmbare Realität aus.
- Vollständige Unterschiedslosigkeit schließt einen Informations-Witness aus, der eine Unterscheidung als Quelle benötigt.

Der Satz ist damit kein Beweis einer physikalischen Schöpfungsgeschichte.

Er ist ein Minimaltheorem über die Voraussetzungen bestimmbarer Weltbeschreibung.

Seine wichtigste methodische Konsequenz lautet:

> **Ein Beweis ist erst wissenschaftlich eindeutig, wenn nicht nur seine Schlussfolgerung, sondern auch sein Geltungsbereich explizit und überprüfbar ist.**

In genau diesem Sinn steht der Unterschied am Anfang der hier formalisierten Ontologie.

**Quod erat demonstrandum.  
Ingolf Lohmann**

---

## Danksagung zur technischen Formalisierung

Die formale Prüfung erfolgt mit Lean 4 und der QIK-VRT-Projektstruktur. Die Softwarewerkzeuge dienen der maschinellen Prüfung und Reproduzierbarkeit; Autorschaft und wissenschaftliche Verantwortung für die hier formulierte Theorie liegen bei Ingolf Lohmann.

---

## Literatur

Black, M. (1952). The Identity of Indiscernibles. *Mind*, 61(242), 153–164. https://doi.org/10.1093/mind/LXI.242.153

de Moura, L., & Ullrich, S. (2021). The Lean 4 Theorem Prover and Programming Language. In A. Platzer & G. Sutcliffe (Eds.), *Automated Deduction – CADE 28*, LNCS 12699, 625–635. Springer. https://doi.org/10.1007/978-3-030-79876-5_37

Leibniz, G. W. (1686/2020). *Discourse on Metaphysics*. G. Rodriguez-Pereyra (Ed. & Trans.). Oxford University Press. Insbesondere §9. https://doi.org/10.1093/oso/9780198829041.001.0001

Leibniz, G. W. (1714). *Monadology*. Bezug insbesondere auf die Prinzipien von Widerspruch und zureichendem Grund sowie die leibnizsche Tradition der Unterscheidbarkeit.

Rodriguez-Pereyra, G. (2014). *Leibniz’s Principle of Identity of Indiscernibles*. Oxford University Press. https://doi.org/10.1093/acprof:oso/9780198712664.001.0001

Shannon, C. E. (1948a). A Mathematical Theory of Communication. *Bell System Technical Journal*, 27(3), 379–423. https://doi.org/10.1002/j.1538-7305.1948.tb01338.x

Shannon, C. E. (1948b). A Mathematical Theory of Communication. *Bell System Technical Journal*, 27(4), 623–656. https://doi.org/10.1002/j.1538-7305.1948.tb00917.x

Stanford Encyclopedia of Philosophy. Identity of Indiscernibles. Historische und systematische Einordnung des leibnizschen Prinzips; konsultiert für die Abgrenzung des vorliegenden Minimaltheorems.
