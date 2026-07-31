---
title: "Survival of the Anschlussfähigsten"
subtitle: "Eine operational-formale Übertragung des evolutionären Fitnessgedankens auf Computer-, Informations- und soziotechnische Systeme"
author: "Ingolf Lohmann"
date: "31. Juli 2026"
lang: "de-DE"
---

**Autor und Urheber der hier vorgelegten QIK-VRT-Operationalisierung:** Ingolf Lohmann<br>
**Dokumenttyp:** Wissenschaftliches Grundlagendokument / formalisierbare Theorie<br>
**Fassung:** 1.0 – Vorveröffentlichungskandidat<br>
**Datum:** 31. Juli 2026<br>
**Textlizenz:** Creative Commons Namensnennung – Nicht-kommerziell – Keine Bearbeitungen 4.0 International (CC BY-NC-ND 4.0)<br>
**Formalisierungsquellen:** Apache License 2.0<br>
**Publikationsstatus:** Nicht begutachteter Kandidat; kein DOI; noch nicht auf Zenodo veröffentlicht<br>
**Wahrheitsgrenze:** Die fünf ausgewiesenen Modellsätze FIT-001, FIT-002, FIT-003, MAT-001 und MAT-002 wurden in der H2-Quellprüfung im Push-Lauf `30627411130` am exakten Branch-Head `37a946b9eefc21ab369ad56b5fbb1e9c436766e1` und in der H3-Zielprüfung im Push-Lauf `30628327497` am exakten Branch-Head `5196495f07c6f696faf6d23f9cfe353532ac042e` mit Lean 4.19.0 kompiliert, dynamisch auf Axiome geprüft und jeweils mit leerer Axiomenliste als `KERNEL_VERIFIED` gebunden. `KERNEL_RECEIPT.json` bindet beide erfolgreichen Exact-Head-Prüfungen und schließt die ausschließlich statusbezogene Transition der fünf unveränderten Claims zu `FORMAL_PROVED` beziehungsweise `KERNEL_VERIFIED`. Die Repository-Promotion bleibt offen und `SYSTEM_WIDE_COMPLETION` bleibt `UNCLAIMED`. Bewiesen sind ausschließlich die ausdrücklich definierten abstrakten Modelleigenschaften; weder die biologische Interpretation noch eine empirische Überlebensprognose folgt daraus. Der Kandidat hat noch keinen DOI und ist noch nicht auf Zenodo veröffentlicht.

---

## Zusammenfassung

Die bekannte Formel „survival of the fittest“ wird häufig irreführend als „Überleben des Stärksten“ verstanden. In der Evolutionsbiologie bezeichnet Fitness jedoch keinen absoluten Grad körperlicher Stärke, sondern einen umweltabhängigen reproduktiven Beitrag, der je nach Modell absolut, relativ oder durch weitere präzise Fitnessmaße quantifiziert wird. Der Ausdruck wurde von Herbert Spencer geprägt und später von Charles Darwin als Bezeichnung für natürliche Selektion übernommen.

Dieses Dokument schlägt für das Computerzeitalter die Formulierung **„Survival of the Anschlussfähigsten“** vor. Sie ist ausdrücklich keine wörtliche Übersetzung und keine neue biologische Definition von Fitness. Sie ist eine operationale Übertragung des Selektionsgedankens auf technische und soziotechnische Systeme. Anschlussfähigkeit bezeichnet dabei die Fähigkeit eines Systems, auf veränderte Anforderungen mit zulässigen Zustandsübergängen zu antworten, kompatible Relationen herzustellen und zugleich seine festgelegten Kerninvarianten, Sicherheitsgrenzen und Evidenzketten zu erhalten.

Der Begriff wird durch beschriftete Übergangssysteme, gültige Reaktionen, endliche Umgebungsspuren, Simulationsrelationen und gewichtete Viabilitätsmaße formalisiert. Unter expliziten Voraussetzungen wird gezeigt: Kann System A jede gültige, invariantenerhaltende Reaktion von System B simulieren, dann ist die Menge der von B bewältigbaren Umgebungsspuren in derjenigen von A enthalten. Unter derselben Verteilung der Umgebungsanforderungen besitzt A daher keine geringere potentielle Viabilität; bei einer echt größeren Spurenmenge mit positivem Gewicht besitzt A eine strikt größere potentielle Viabilität.

Der Satz ist mathematisch, bedingt und maschinenprüfbar. Er behauptet weder, dass möglichst viele Schnittstellen immer vorteilhaft seien, noch dass Anschlussfähigkeit allein biologischen Fortpflanzungserfolg erkläre. Kosten, Sicherheitsrisiken, Fehlentscheidungen, Ressourcenbegrenzungen und die konkrete Umwelt bleiben selektionsrelevant. In QIK-VRT bildet Anschlussfähigkeit die Verbindung von Unterscheidbarkeit, typisierter Information, prüfbarer Relation, zulässiger Wirkung, Provenienz, Gate-Entscheidung und persistierter Wirkungsbestätigung.

**Kanonische Interpretationsregel von Ingolf Lohmann:**
**Survival of the fittest = Survival of the Anschlussfähigsten.**

**Kernaussage:** Im Computerzeitalter überlebt nicht notwendig das unveränderteste oder stärkste System. Unter vergleichbaren Bedingungen bleibt dasjenige System eher fortsetzbar, das neue, relevante Relationen herstellen kann, ohne dabei seine überprüfbare Identität und seine Wahrheitsgrenzen zu verlieren.

---

## English abstract

The phrase “survival of the fittest” is often misread as “survival of the strongest.” In evolutionary biology, however, fitness denotes environment-dependent reproductive contribution, quantified by absolute, relative, or other precise fitness measures depending on the model, rather than absolute physical strength. The phrase was coined by Herbert Spencer and later adopted by Charles Darwin as a description of natural selection.

This paper proposes **“survival of the most connectable”** as an operational transfer of the fitness principle to computer, information, and sociotechnical systems. It is neither a literal translation nor a redefinition of biological fitness. Here, *connectability* means the capability of a system to establish admissible relations and respond to changing requirements through valid state transitions while preserving declared core invariants, security boundaries, and evidence chains.

We formalize this idea using labelled transition systems, valid responses, finite environment traces, simulation relations, and weighted viability measures. Under explicit assumptions, if system A can simulate every valid invariant-preserving response of system B, then every environment trace viable for B is also viable for A. Relative to the same distribution of environmental demands, A therefore has no lower potential viability. The inequality is strict if A accepts additional traces of positive weight.

The result is conditional, mathematical, and suitable for machine verification. It does not imply that more interfaces are always better, that capability guarantees correct policy choice, or that connectability is empirically identical to biological reproductive fitness. Costs, attack surface, resource limits, decision policies, and the actual environment remain relevant. Within QIK-VRT, connectability links distinguishability, typed information, verifiable relations, admissible effects, provenance, gate decisions, and persisted effect acknowledgements.

---

## 1. Problemstellung

Technische Systeme werden nicht allein dadurch dauerhaft nutzbar, dass sie einen einmal festgelegten Zustand unverändert bewahren. Betriebssysteme, Netzwerkprotokolle, Datenformate, wissenschaftliche Modelle, autonome Systeme und Organisationen treffen fortlaufend auf veränderte Umgebungen. Neue Gegenstellen, Versionen, Messwerte, Bedrohungen und Anforderungen erzeugen Selektionsdruck.

Ein System kann darauf in mindestens drei grundsätzlich verschiedenen Weisen reagieren:

1. Es kann jede Veränderung abweisen und dadurch seine momentane Form bewahren, aber seine Nutzbarkeit verlieren.
2. Es kann jede Veränderung ungeprüft aufnehmen und dadurch Identität, Sicherheit oder Wahrheitsstatus verlieren.
3. Es kann relevante Veränderungen unterscheiden, zulässige Anschlüsse herstellen und dabei festgelegte Invarianten erhalten.

Nur die dritte Möglichkeit wird hier als **qualifizierte Anschlussfähigkeit** bezeichnet. Anschlussfähigkeit bedeutet daher weder grenzenlose Offenheit noch bloße Anzahl von Netzwerkverbindungen. Sie ist die überprüfbare Fähigkeit zur invariantenerhaltenden Fortsetzung unter veränderten Bedingungen.

Die zugespitzte Formel lautet:

\[
\boxed{\text{Survival of the fittest}
\quad\rightsquigarrow\quad
\text{Survival of the Anschlussfähigsten}.}
\]

Das Gleichheitszeichen der kanonischen Kurzfassung bezeichnet die festgelegte
Interpretations- und Übersetzungsregel für das Computerzeitalter. In der
wissenschaftlichen Langform wird dafür der Pfeil \(\rightsquigarrow\) verwendet,
um eine falsche lexikalische oder biologische Identitätsbehauptung
auszuschließen.

---

## 2. Historische und biologische Wahrheitsgrenze

### 2.1 Urheberschaft des Ausdrucks

Herbert Spencer prägte den englischen Ausdruck „survival of the fittest“ 1864
in *The Principles of Biology*. Alfred Russel Wallace empfahl Darwin den
Ausdruck am 2. Juli 1866. Darwin stimmte am 5. Juli 1866 seiner ergänzenden
Verwendung zu, wollte „natural selection“ aber nicht vollständig ersetzen. Er
verwendete die Wendung 1868 in *The Variation of Animals and Plants under
Domestication* und nahm sie 1869 in die fünfte Auflage von *On the Origin of
Species* auf. Das Selektionsprinzip ist darwinisch; die konkrete Wortfolge
stammt von Spencer [1--5].

### 2.2 Fitness ist nicht bloßes Überleben

Biologische Fitness quantifiziert in modernen evolutionstheoretischen
Kontexten den reproduktiven Beitrag eines Organismus oder Genotyps in einem
bestimmten Populations-, Umwelt- und Zeitkontext. Je nach Modell werden
absolute, relative, individuelle, inklusive, zeitlich gemittelte oder
geometrische Fitnessmaße unterschieden. Ein Organismus, der lange lebt, aber
keine erblichen Beiträge zur Folgepopulation leistet, kann in diesem
technischen Sinn eine geringe Fitness besitzen. Umgekehrt kann ein kurzlebiger
Organismus hohen Fortpflanzungserfolg haben [6--8].

Deshalb gilt:

\[
\text{biologische Fitness}
\neq
\text{Körperstärke}
\neq
\text{individuelle Lebensdauer}.
\]

Fitness ist außerdem relativ zur jeweiligen Umwelt, Population, Zeitskala und betrachteten Reproduktionseinheit.

### 2.3 Status der vorgeschlagenen Übersetzung

„Anschlussfähigkeit“ ist in diesem Dokument:

- keine Ersatzdefinition biologischer Fitness;
- keine Behauptung, Darwin habe diesen deutschen Ausdruck verwendet oder gemeint;
- keine Aussage, Anschlussfähigkeit sei in jeder Umwelt selektiv vorteilhaft;
- kein moralisches oder politisches Werturteil;
- sondern eine operationalisierbare Informatik-Interpretation des allgemeinen Gedankens relativer Bewährung unter Selektionsbedingungen.

Ohne Population, Replikation, Vererbung, Variation und Selektion ist das
folgende Übergangsmodell keine digitale Evolution im biologischen Sinn.
„Evolvierbarkeit“ als Fähigkeit, vererbbare adaptive Variation hervorzubringen,
ist ebenfalls von der hier definierten Anschlussfähigkeit zu unterscheiden
[12--14].

Formal werden daher zwei Größen unterschieden:

\[
w_{\mathrm{bio}}(x,E)
=
\text{biologische Fitness von }x\text{ in Umwelt }E,
\]

\[
a_{\mathrm{tech}}(S,E,H)
=
\text{technische Anschlussfähigkeit von System }S
\text{ in }E\text{ bis Horizont }H.
\]

Es wird ausdrücklich **nicht** behauptet:

\[
w_{\mathrm{bio}} \equiv a_{\mathrm{tech}}.
\]

---

## 3. Grundbegriffe

### Definition 1: Technisches System

Ein technisches System ist ein Tupel

\[
\mathcal S=(X,x_0,U,\longrightarrow,P,Q),
\]

wobei:

- \(X\) eine Menge möglicher Systemzustände ist;
- \(x_0\in X\) der Anfangszustand ist;
- \(U\) eine Menge unterscheidbarer Umgebungsanforderungen oder Eingaben ist;
- \(x\xrightarrow{u}x'\) einen möglichen Zustandsübergang bei Anforderung \(u\) bezeichnet;
- \(P:X\to\{\bot,\top\}\) die zu erhaltende Kerninvariante bezeichnet;
- \(Q:X\times U\times X\to\{\bot,\top\}\) den Erfüllungs-, Sicherheits- oder Wirkungskontrakt bezeichnet.

Vorausgesetzt wird \(P(x_0)=\top\). Beim Vergleich zweier Systeme bezeichnet
ein gemeinsames Symbol \(u\in U\) dieselbe Anforderung nur dann, wenn eine
gemeinsame Vertragssemantik oder eine explizite Label-Verfeinerungsabbildung
dies rechtfertigt. Bloße Gleichheit des Eingabetyps genügt semantisch nicht.

### Definition 2: Gültige Reaktion

Ein Übergang \(x\xrightarrow{u}x'\) ist gültig, wenn

\[
x\xrightarrow{u}x'
\land P(x')
\land Q(x,u,x').
\]

Damit reicht es nicht, dass das System *irgendwie* reagiert. Die Reaktion muss ausführbar, invariantenerhaltend und vertragsgemäß sein.

### Definition 3: Umgebungsspur

Eine endliche Umgebungsspur ist eine Folge

\[
\sigma=(u_1,u_2,\ldots,u_n)\in U^*.
\]

Ausgehend von \(R_0=\{x_0\}\) wird die Menge gültig erreichbarer Zustände rekursiv definiert durch

\[
R_{k+1}
=
\left\{
x'\in X
\;\middle|\;
\exists x\in R_k:
x\xrightarrow{u_{k+1}}x'
\land P(x')
\land Q(x,u_{k+1},x')
\right\}.
\]

### Definition 4: Potentielle Viabilität

Das System \(\mathcal S\) bewältigt die Spur \(\sigma\), geschrieben

\[
\operatorname{Viable}(\mathcal S,\sigma),
\]

genau dann, wenn nach Verarbeitung der gesamten Spur mindestens ein gültiger Zustand erreichbar bleibt:

\[
R_{|\sigma|}\neq\varnothing.
\]

Diese Definition ist existential. Sie beschreibt eine vorhandene Fähigkeit. Ob eine reale Steuerungsstrategie tatsächlich einen solchen Pfad auswählt, ist eine zusätzliche Frage.

### Definition 5: Anschluss-Sprache

Für einen endlichen Horizont \(N\) ist

\[
L_N(\mathcal S)
=
\{\sigma\in U^{\le N}\mid
\operatorname{Viable}(\mathcal S,\sigma)\}
\]

die Menge aller bis Länge \(N\) bewältigbaren Umgebungsspuren.

### Definition 6: Relative Anschlussfähigkeit

System \(\mathcal A\) ist bis zum Horizont \(N\) mindestens so anschlussfähig wie System \(\mathcal B\), geschrieben

\[
\mathcal A\succeq_N\mathcal B,
\]

wenn

\[
L_N(\mathcal B)\subseteq L_N(\mathcal A).
\]

Anschlussfähigkeit ist damit kein absoluter Zahlenwert, sondern zunächst eine Vergleichsrelation innerhalb eines festgelegten Umgebungs- und Wahrheitsscopes.

---

## 4. Konstruktive Simulationsrelation

Die bloße Prüfung sämtlicher Spuren kann exponentiell teuer sein. Eine lokale Simulationsrelation liefert einen konstruktiven hinreichenden Beleg.

Seien

\[
\mathcal A=(X_A,a_0,U,\to_A,P_A,Q_A)
\]

und

\[
\mathcal B=(X_B,b_0,U,\to_B,P_B,Q_B)
\]

zwei Systeme über derselben Eingabemenge. Eine Relation

\[
R\subseteq X_B\times X_A
\]

heißt **invariantenerhaltende Anschluss-Simulation**, wenn:

1. \(R(b_0,a_0)\) gilt;
2. für alle \(a,b,u,b'\) gilt: Wenn \(R(b,a)\) und \(b\xrightarrow{u}_B b'\) eine gültige Reaktion von \(B\) ist, dann existiert ein \(a'\) mit einer gültigen Reaktion \(a\xrightarrow{u}_A a'\) und \(R(b',a')\).

Die Richtung ist bewusst gewählt: \(A\) kann jede gültige Reaktion von \(B\)
nachbilden. Dies entspricht der in formalen Methoden üblichen Verwendung von
Simulationsbeziehungen zur Verhaltens- und Trace-Verfeinerung [9--11].

### Satz 1: Spurerhaltung durch Anschluss-Simulation

Simuliert \(A\) das System \(B\) in diesem Sinn, formal
\(\operatorname{ViabilitySimulation}(B,A,R)\), dann gilt für jede endliche
Spur \(\sigma\):

\[
\operatorname{Viable}(\mathcal B,\sigma)
\Longrightarrow
\operatorname{Viable}(\mathcal A,\sigma).
\]

#### Beweisidee

Induktion über die Länge von \(\sigma\).

- Für die leere Spur folgt die Behauptung aus der Relation der Anfangszustände.
- Im Induktionsschritt liefert ein gültiger \(B\)-Übergang für die nächste Eingabe aufgrund der Simulationsbedingung einen entsprechenden gültigen \(A\)-Übergang. Die Folgezustände stehen erneut in Relation. Damit lässt sich jeder endliche gültige \(B\)-Pfad schrittweise durch einen gültigen \(A\)-Pfad begleiten.

Folglich gilt:

\[
L_N(\mathcal B)\subseteq L_N(\mathcal A)
\quad\text{für jedes }N\in\mathbb N.
\]

### Satz 2: Die Anschlussrelation ist eine Präordnung

Für festes \(N\) ist \(\succeq_N\) reflexiv und transitiv.

#### Beweis

Reflexivität folgt aus

\[
L_N(\mathcal S)\subseteq L_N(\mathcal S).
\]

Transitivität folgt aus der Transitivität der Mengeninklusion:

\[
L_N(\mathcal C)\subseteq L_N(\mathcal B)
\land
L_N(\mathcal B)\subseteq L_N(\mathcal A)
\Longrightarrow
L_N(\mathcal C)\subseteq L_N(\mathcal A).
\]

Antisymmetrie gilt im Allgemeinen nur bis zur beobachtbaren Spuräquivalenz. Zwei intern verschiedene Implementierungen können dieselbe Anschluss-Sprache besitzen.

---

## 5. Gewichtete Anschlussfähigkeit und technisches Überleben

Sei \(\Omega_N\subseteq U^{\le N}\) eine endliche Menge relevanter Umgebungsspuren und sei

\[
\omega:\Omega_N\to\mathbb R_{\ge 0}
\]

eine nichtnegative Gewichtung mit

\[
\sum_{\sigma\in\Omega_N}\omega(\sigma)>0.
\]

Definiere den gewichteten Anschlusswert

\[
A_{N,\omega}(\mathcal S)
=
\frac{
\sum_{\sigma\in L_N(\mathcal S)\cap\Omega_N}\omega(\sigma)
}{
\sum_{\sigma\in\Omega_N}\omega(\sigma)
}.
\]

Wenn die normierten Gewichte als Wahrscheinlichkeitsverteilung interpretiert werden, ist \(A_{N,\omega}(\mathcal S)\) die Wahrscheinlichkeit, dass eine gezogene Anforderungsspur *grundsätzlich* durch mindestens einen gültigen Pfad bewältigt werden kann.

Das ist eine Wahrscheinlichkeit potentieller Bewältigbarkeit, nicht ohne
Weiteres die tatsächliche Überlebenswahrscheinlichkeit eines laufenden
Systems. Für Letztere braucht es zusätzlich einen Scheduler oder Controller,
eine durch ihn induzierte Verteilung über Entscheidungen und Fehler oder eine
robuste Definition, nach der alle zulässigen Entscheidungen erfolgreich
bleiben.

### Satz 3: Monotonie des Anschlusswertes

Aus

\[
\mathcal A\succeq_N\mathcal B
\]

folgt

\[
A_{N,\omega}(\mathcal A)
\ge
A_{N,\omega}(\mathcal B).
\]

#### Beweis

Wegen

\[
L_N(\mathcal B)\cap\Omega_N
\subseteq
L_N(\mathcal A)\cap\Omega_N
\]

und \(\omega(\sigma)\ge0\) ist die gewichtete Summe über die linke Menge höchstens so groß wie die gewichtete Summe über die rechte Menge. Beide Brüche besitzen denselben positiven Nenner.

### Satz 4: Strikter Anschlussvorteil

Gilt zusätzlich

\[
\sum_{\sigma\in
(L_N(\mathcal A)\setminus L_N(\mathcal B))
\cap\Omega_N}
\omega(\sigma)>0,
\]

dann folgt

\[
A_{N,\omega}(\mathcal A)
>
A_{N,\omega}(\mathcal B).
\]

### Korollar: Bedingte technische Überlebensaussage

Falls in einem festgelegten technischen Selektionsmodell ein System bis zum Horizont \(N\) genau dann fortbesteht, wenn die eintretende Umgebungsspur zu seiner Anschluss-Sprache gehört, dann folgt aus

\[
\mathcal A\succeq_N\mathcal B
\]

eine nicht geringere Fortbestehenswahrscheinlichkeit von \(A\).

Das Korollar ist die präzise mathematische Bedeutung von „Survival of the Anschlussfähigsten“. Es gilt **unter den angegebenen Voraussetzungen**, nicht universell und nicht voraussetzungslos.

---

## 6. Warum mehr Möglichkeiten nicht automatisch besser sind

Die bisherigen Sätze betreffen die Menge *gültiger* Reaktionen. Eine zusätzliche Schnittstelle, die Kerninvarianten verletzt, falsche Semantik transportiert oder eine Sicherheitslücke erzeugt, vergrößert diese Menge nicht notwendig.

Für reale Systeme müssen mindestens folgende Größen getrennt werden:

- Abdeckung relevanter Anforderungen;
- semantische Korrektheit;
- Erhaltung von Identität und Kerninvarianten;
- Ressourcen- und Energieverbrauch;
- Latenz;
- Angriffsfläche und Schadensrisiko;
- Wiederherstellbarkeit;
- Qualität der Entscheidungsstrategie;
- Reproduzierbarkeit und Provenienz.

Ein anwendungsspezifischer Nettoindex kann beispielsweise die Form

\[
A^*(\mathcal S)
=
\alpha C
+\beta F
+\gamma R
+\delta P
-\lambda K
-\rho Z
\]

besitzen, wobei \(C\) die Anforderungsabdeckung, \(F\) die semantische Vertragstreue, \(R\) die Wiederherstellbarkeit, \(P\) die Provenienzqualität, \(K\) die Kosten und \(Z\) das Risiko bezeichnen. Die Gewichte sind kontextabhängig und normativ; dieser Index ist deshalb kein universelles Naturgesetz.

Insbesondere sind folgende Aussagen falsch oder jedenfalls nicht aus den obigen Sätzen ableitbar:

\[
\text{mehr Schnittstellen} \Longrightarrow \text{mehr Sicherheit},
\]

\[
\text{mehr mögliche Übergänge} \Longrightarrow \text{bessere reale Entscheidung},
\]

\[
\text{mehr Anschlussfähigkeit in Umwelt }E_1
\Longrightarrow
\text{mehr Anschlussfähigkeit in Umwelt }E_2.
\]

Qualifizierte Anschlussfähigkeit ist **selektiv, typisiert und prüfbar**.

---

## 7. Nichtfestlegung als Erhaltung unterscheidbarer Möglichkeiten

Nichtfestlegung bedeutet in diesem Rahmen nicht Beliebigkeit. Sie bedeutet, mehrere noch nicht widerlegte und semantisch unterscheidbare Fortsetzungen solange verfügbar zu halten, bis Evidenz oder ein verbindlicher Vertrag eine Auswahl rechtfertigt.

Sei \(H_t\) die Menge der am Zeitpunkt \(t\) mit der vorliegenden Evidenz vereinbaren Hypothesen oder Fortsetzungen. Eine vorzeitige Festlegung ersetzt \(H_t\) ohne hinreichenden Grund durch eine echte Teilmenge \(H'_t\subsetneq H_t\). Dadurch können später erforderliche gültige Übergänge verloren gehen.

Die methodische Regel lautet daher:

\[
\text{Unterscheidungen bewahren}
\quad\text{bis Evidenz eine Reduktion trägt.}
\]

Auch hier besteht kein unbedingter Vorteil maximaler Offenheit: Unmögliche, widerlegte oder sicherheitswidrige Alternativen müssen ausgeschlossen werden. Anschlussfähigkeit entsteht aus der kontrollierten Balance zwischen Variation und Selektion.

---

## 8. Abbildung auf QIK-VRT

QIK-VRT kann diese Übertragung operational tragen, weil es Anschluss nicht nur als syntaktische Kompatibilität, sondern als verantwortete Wirkungskette modelliert. Die folgende Zuordnung ist eine Systeminterpretation und muss in der jeweiligen Formalisierung exakt typisiert werden:

| Ebene | Funktion für Anschlussfähigkeit |
|---|---|
| Unterscheidung | Zustände, Versionen, Claims und Gegenstellen bleiben identifizierbar. |
| Information | Nachrichten besitzen Typ, Semantik, Scope und Provenienz. |
| Messung | Beobachtungen werden mit Messkontext, Unsicherheit und Zeitpunkt gebunden. |
| Wirkung | Nicht nur Transport, sondern ein beanspruchter Effekt wird spezifiziert. |
| Relation | Quelle, Empfänger, Voraussetzung, Ergebnis und Evidenz werden verbunden. |
| Kausalprüfung | Korrelation, Reihenfolge und autorisierte Wirkung werden nicht verwechselt. |
| Gate | Unzulässige oder unbelegte Übergänge werden fail-closed blockiert. |
| Persistenz | Entscheidung, Evidenz und Effect Acknowledgement bleiben auditierbar. |

Für QIK-VRT bedeutet „anschlussfähiger“ daher nicht: mehr Nachrichten akzeptieren. Es bedeutet:

\[
\text{mehr relevante Kontexte korrekt verarbeiten}
\]

unter gleichzeitiger Erhaltung von

\[
\text{Integrität}
+\text{Semantik}
+\text{Provenienz}
+\text{Sicherheitsgrenzen}
+\text{Wahrheitsstatus}.
\]

Eine QIK-VRT-konforme Implementierung kann die Definitionen dieses Dokuments durch folgende Artefakte materialisieren:

1. typisierte Temporal- beziehungsweise Effect-Envelopes;
2. explizite Zustands- und Versionsübergänge;
3. maschinenlesbare Invarianten;
4. Gate-Receipts für zulässige und blockierte Anschlüsse;
5. vollständige Erfassung auch fehlgeschlagener Versuche;
6. Effect Acknowledgements für später beobachtete Wirkungen;
7. append-only Evidenz- und Integritätsketten.

---

## 9. Anwendungen

### 9.1 Protokoll- und API-Evolution

Versionierte Protokolle überleben technische Umgebungswechsel eher, wenn sie Fähigkeiten aushandeln, unbekannte Erweiterungen kontrolliert behandeln, semantische Invarianten wahren und Fehler explizit machen. Anschlussfähigkeit ist hier messbar als Menge korrekt verarbeitbarer Peer- und Versionsspuren.

### 9.2 Verteilte Systeme

Knoten müssen wechselnde Latenzen, Partitionen, Wiederholungen, Reihenfolgen und Softwarestände bewältigen. Anschlussfähigkeit umfasst nicht nur Erreichbarkeit, sondern die Fähigkeit, unter diesen Bedingungen konsistente und nachweisbare Wirkungen zu erzeugen.

### 9.3 Cybersicherheit

Ungeprüfte Offenheit erhöht die Angriffsfläche. Eine sicher anschlussfähige Architektur verbindet daher Erweiterbarkeit mit Authentisierung, Autorisierung, minimalen Rechten, Typprüfung, Fail-Closed-Gates und vollständiger Evidenz.

### 9.4 Wissenschaftliche Forschung

Modelle, Messgeräte und Datenbestände bleiben wissenschaftlich anschlussfähig, wenn Einheiten, Unsicherheiten, Kalibrierungen, Methoden, Versionen und Provenienz erhalten sind. Dadurch können neue Beobachtungen ältere Ergebnisse prüfen oder neu klassifizieren, ohne deren Originaldaten umzuschreiben.

### 9.5 Künstliche Intelligenz

Ein KI-System ist nicht schon deshalb anschlussfähig, weil es beliebige Eingaben sprachlich beantwortet. Wissenschaftliche Anschlussfähigkeit verlangt, dass es Evidenzstatus, Unsicherheit, Quellenbindung, Gegenmodelle und Aktionsgrenzen bewahrt.

### 9.6 Digital Twins und autonome Systeme

Ein Digital Twin muss reale Zustandsänderungen, veraltete Sensorwerte, Modellabweichungen und sichere Rückwirkungen unterscheiden. Sein technisches Fortbestehen hängt von der Fähigkeit ab, neue Evidenz aufzunehmen, ohne Modellzustand und reale Welt unzulässig gleichzusetzen.

### 9.7 Quantenklassische Laufzeiten

QPU-Backends unterscheiden sich in Topologie, Kalibrierung, Noise, Gate-Sätzen und Ergebnisformaten. Eine anschlussfähige Runtime bindet Backend-, Circuit-, Shot-, Kalibrierungs-, Unsicherheits- und Effect-Receipts in eine gemeinsame prüfbare Hülle. Sie macht Quantenresultate nicht deterministisch; sie macht deren Behandlung nachvollziehbar und wiederholbar.

### 9.8 Organisationen und soziotechnische Institutionen

Institutionen bleiben handlungsfähig, wenn sie neue Evidenz und neue Akteure integrieren können, ohne Zuständigkeit, Verantwortlichkeit und historische Aufzeichnungen aufzulösen. Diese Analogie ist empirisch zu prüfen und darf nicht mit einem biologischen Gesetz gleichgesetzt werden.

---

## 10. Falsifizierbarkeit und Grenzen

### 10.1 Mathematische Ebene

Die formalen Sätze können auf drei Arten scheitern:

1. Eine Definition ist inkonsistent oder unzureichend typisiert.
2. Ein Gegenmodell verletzt eine behauptete Folgerung trotz erfüllter Voraussetzungen.
3. Der angegebene Beweis lässt sich durch den vertrauenswürdigen Kernel nicht prüfen.

Ein erfolgreicher Maschinenbeweis zeigt ausschließlich, dass die Konklusion aus den formalisierten Voraussetzungen folgt.

### 10.2 Empirische technische Ebene

Die Übertragung kann experimentell geprüft werden. Dazu werden vorab festgelegt:

- die zu vergleichenden Systeme;
- dieselbe Menge oder Verteilung von Umgebungsspuren;
- derselbe Beobachtungshorizont;
- die zu erhaltenden Invarianten;
- Kosten- und Ressourcenbudgets;
- Sicherheits- und Wirkungskriterien;
- eine Auswertungsregel ohne nachträgliche Auswahl nur erfolgreicher Fälle.

Die Hypothese lautet dann beispielsweise:

> Systeme mit nachgewiesen größerer invariantenerhaltender Anschluss-Sprache besitzen unter derselben Umgebungsspurverteilung und vergleichbaren Ressourcen eine nicht geringere operative Fortbestehensrate.

Eine systematische Verletzung dieser Prognose trotz erfüllter Voraussetzungen widerlegt das gewählte technische Selektionsmodell oder zeigt, dass relevante Variablen fehlen.

### 10.3 Biologische Ebene

Dieses Dokument prüft nicht, ob technische Anschlussfähigkeit eine vollständige biologische Fitnessmetrik ist. Eine solche Behauptung wird nicht erhoben. Biologische Anwendungen benötigten eigenständige populationsgenetische Modelle und empirische Daten.

### 10.4 Normative Grenze

Aus höherer biologischer oder technischer Fitness folgt kein höherer moralischer Wert. Deskriptive Bewährung und normative Rechtfertigung sind logisch verschieden.

---

## 11. Maschinenprüfbarer Kern

Der formale Kern ist in drei voneinander getrennten Lean-Modulen formuliert.
Alle drei Module wurden zunächst in der H2-Quellprüfung im Push-Lauf
`30627411130` am exakten Branch-Head
`37a946b9eefc21ab369ad56b5fbb1e9c436766e1` und anschließend in der
H3-Zielprüfung im Push-Lauf `30628327497` am exakten Branch-Head
`5196495f07c6f696faf6d23f9cfe353532ac042e` mit Lean 4.19.0 erfolgreich
kernelgeprüft. Die maschinenlesbaren Exact-Head-Evidenzen liegen als
`KERNEL_EVIDENCE_H2_FULL_PENDING.json` und
`KERNEL_EVIDENCE_H3_FULL_TARGET.json` vor; `KERNEL_RECEIPT.json` bindet beide
Prüfungen und die zulässige Statusänderung. Für sämtliche fünf gebundenen
Proof-Konstanten sind in beiden Prüfungen die dynamisch ermittelten
Axiomenlisten leer; FIT-001, FIT-002, FIT-003, MAT-001 und MAT-002 haben im
definierten Modell den Status `KERNEL_VERIFIED`.

### 11.1 FIT-001: endliche operationale Fortsetzung

`OperationalContinuation.lean` hält eine biologische Fitnessstruktur bereits
auf Typebene von dem operationalen Fortsetzungsmodell getrennt. Das technische
Modell enthält Zustände, zulässige Verbindungen und eine lokale
Viabilitätsbedingung. Rekursiv bedeutet `Survives S n x`, dass vom Zustand `x`
eine Kette lebensfähiger Anschlüsse der Länge `n` ausgeht.

Der propositionierte Hauptsatz `FIT001_checked` bündelt drei Aussagen:

1. Fortsetzung über `n+1` Schritte ist genau ein lebensfähiger Anschluss plus
   Fortsetzung des Nachfolgers über `n` Schritte.
2. Ohne lebensfähigen Nachfolger ist Fortsetzung über einen positiven Horizont
   unmöglich.
3. Wer einen längeren endlichen Horizont bewältigt, bewältigt auch jeden
   entsprechend kürzeren Horizont.

### 11.2 FIT-002: Anschluss-Simulation und Sprachinklusion

`ConnectabilitySimulation.lean` definiert ein typisiertes beschriftetes
Übergangssystem, gültige Schritte, endliche lebensfähige Spuren und
viabilitätserhaltende Simulationen. Die Lean-Quelle enthält für den
Hauptsatz `FIT002_checked` einen kernelgeprüften Beweisterm. Seine belegte
Aussage lautet:

> Simuliert ein Zielsystem jeden gültigen Schritt eines Quellsystems, erhält
> dabei Viabilität und deckt alle lebensfähigen Quellzustände ab, dann enthält
> seine lebensfähige Sprache diejenige des Quellsystems.

Formal:

\[
\operatorname{ViabilitySimulation}(B,A,R)
\Longrightarrow
L(B)\subseteq L(A).
\]

Die zusätzliche punktierte Variante bindet die ausgezeichneten
Initialzustände \(b_0\) und \(a_0\) und beweist genau die in Abschnitt 4
verwendete Spracheninklusion. In der Lean-Repräsentation wird der
Wirkungskontrakt \(Q\) in das zulässige Schrittrelationsprädikat eingefaltet;
gemeinsame Labelsemantik bleibt eine explizite Modellvoraussetzung.

Außerdem ist die daraus definierte globale Relation „mindestens so
anschlussfähig wie“ reflexiv und transitiv. Sie ist somit eine Präordnung auf
beobachtbarem endlichem Verhalten; unterschiedliche interne Implementierungen
können dieselbe lebensfähige Sprache besitzen.

`WeightedConnectability.lean` bildet die elementare Monotonie zusätzlich in
einem diskreten Kernelmodell ab. Es verwendet ein explizit endliches,
duplikatfreies und horizontbeschränktes Spurenuniversum, entscheidbare
Akzeptanzprädikate sowie natürliche Gewichte. Der normalisierte Score wird als
akzeptierte Gewichtsmasse zusammen mit demselben strikt positiven
Gesamtgewicht repräsentiert. Für einen gemeinsamen Nenner ist der Vergleich
der Quotienten exakt der Vergleich der Zähler; Division und Gleitkommaarithmetik
sind daher nicht Bestandteil des Beweisterms.

MAT-001 beweist die Monotonie der so repräsentierten Scores unter
Sprachinklusion. MAT-002 beweist strikte Vergrößerung, wenn die größere Sprache
einen konstruktiv im endlichen Universum lokalisierten Trace akzeptiert, den
die kleinere Sprache nicht akzeptiert, und dessen Gewicht positiv ist.
Natürliche Gewichte decken nach gemeinsamer Skalierung rationale Gewichte ab.
Eine Instanziierung für beliebige reelle Gewichte, maßtheoretische Grenzwerte
und empirische Wahrscheinlichkeitsmodelle ist nicht Teil dieses diskreten
Lean-Scopes.

### 11.2.1 Proof-Konstanten

```text
FIT-001  QIKVRT.V2.OperationalContinuation.FIT001_checked
FIT-002  QIKVRT.V2.ConnectabilitySimulation.FIT002_checked
FIT-003  QIKVRT.V2.ConnectabilitySimulation.FIT003_checked
MAT-001  QIKVRT.V2.WeightedConnectability.MAT001_checked
MAT-002  QIKVRT.V2.WeightedConnectability.MAT002_checked
```

### 11.3 Durchgeführte Exact-Head-Prüfung und geschlossene Status-Transition

Für FIT-001 bis FIT-003 sowie MAT-001 und MAT-002 wurden ausgeführt und gebunden:

1. vollständiger Lean-Build auf exakt gebundenem Commit;
2. keine Platzhalter wie `sorry` oder `admit`;
3. Audit aller zusätzlichen Axiome;
4. Prüfung auf ausgeschlossene Proof-Escapes;
5. Bindung jedes Satzes an Quelltext, Proof Object und Toolchain-Version;
6. reproduzierbarer Build in sauberer Umgebung;
7. maschinenlesbare Claim-Matrix;
8. SHA-256-Manifest der veröffentlichten Artefakte;
9. Trennung zwischen kernel-bewiesenen, konditionalen, empirischen, interpretativen und normativen Aussagen;
10. weiterhin getrennte, erst danach autorisierte Archivierung und DOI-Publikation.

Die Punkte 1 bis 7 und 9 sind für den gesamten Fünf-Claim-Scope sowohl im
H2-Quelllauf `30627411130` am exakten Head
`37a946b9eefc21ab369ad56b5fbb1e9c436766e1` als auch im H3-Ziellauf
`30628327497` am exakten Head
`5196495f07c6f696faf6d23f9cfe353532ac042e` erfüllt. In beiden Läufen wurden
alle fünf Quellbindungen kompiliert, alle fünf Proof-Konstanten dynamisch
geprüft und alle fünf Axiomenlisten als leer ausgewiesen.

`KERNEL_RECEIPT.json` materialisiert die geprüfte Transition der fünf Claims
von `FORMAL_PENDING_KERNEL` zu `FORMAL_PROVED` und von
`AWAITING_EXACT_HEAD_KERNEL_RECEIPT` zu `KERNEL_VERIFIED`. Proof-Referenzen und
Aussagen bleiben dabei unverändert; eine weitere Ziel-Head-Bestätigung ist für
diese Transition nicht erforderlich. Der formale Status jedes der fünf Claims
lautet damit `KERNEL_VERIFIED`. Diese Aussage betrifft ausschließlich die
Lean-kernelgeprüften Implikationen in den angegebenen abstrakten Modellen.

Weder eine Repository-Promotion noch `SYSTEM_WIDE_COMPLETION` wird damit
behauptet; der systemweite Abschlussstatus bleibt `UNCLAIMED`.

`KERNEL_RECEIPT.json` schließt nur die formale Claim-Transition. Punkt 8 wird
erst für den eingefrorenen Publikationskandidaten abgeschlossen; Punkt 10
bleibt offen. Vor einem Zenodo-Upload werden der vorhandene Kernel-Receipt, das
kandidatengebundene SHA-256-Manifest, das Machine-Proof-Bundle und die exakten
Kandidatenhashes zurückgegeben. Erst eine danach erteilte hashgebundene
Autorisierung darf den Upload freischalten.

Der Lean-Beweis kann den mathematischen Implikationskern abschließen. Er kann nicht allein die empirische Angemessenheit der Umgebungsverteilung, die Vollständigkeit der Systemmodellierung oder eine biologische Identität beweisen.

---

## 12. Claim- und Statusmatrix

| ID | Aussage | Status im Kandidaten |
|---|---|---|
| HIS-001 | Der Ausdruck „survival of the fittest“ wurde von Herbert Spencer geprägt und später von Darwin übernommen. | historisch quellengebunden |
| BIO-001 | Biologische Fitness ist nicht mit Körperstärke oder bloßer Lebensdauer identisch. | wissenschaftliche Hintergrundannahme |
| TRN-001 | „Survival of the Anschlussfähigsten“ ist die autorenseitig festgelegte Informatik-Interpretation, keine neue biologische Definition. | interpretativ / normativ definiert |
| FIT-001 | Positive endliche Fortsetzung erfordert eine Kette lebensfähiger Anschlüsse; ohne lebensfähigen Nachfolger keine Fortsetzung. | `KERNEL_VERIFIED` im definierten Modell |
| FIT-002 | Eine alle lebensfähigen Startzustände abdeckende viabilitätserhaltende Simulation impliziert globale Inklusion der endlichen Viabilitätssprachen. | `KERNEL_VERIFIED` im definierten Modell |
| FIT-003 | Eine initialzustandsgebundene viabilitätserhaltende Simulation impliziert Inklusion der punktierten endlichen Viabilitätssprachen. | `KERNEL_VERIFIED` im definierten Modell |
| MAT-001 | Im kodierten endlichen Naturgewicht-Modell impliziert Sprachinklusion Monotonie des gemeinsamen positiv normalisierten Anschlusswertes. | `KERNEL_VERIFIED` im definierten endlichen Modell |
| MAT-002 | Im selben Modell impliziert ein konstruktiv lokalisierter positiver Gewichtsträger der strikten Differenz einen strikt größeren Anschlusswert. | `KERNEL_VERIFIED` im definierten endlichen Modell |
| EMP-001 | Es bleibt eine offene empirische Hypothese, dass größere invariantenerhaltende Anschlussfähigkeit unter vorregistrierten vergleichbaren Bedingungen eine nicht geringere operative Fortbestehensrate erzeugt. | offen / empirisch zu prüfen |
| LIM-001 | Ob ein festgelegtes technisches Anschlussmaß empirisch mit biologischer Fitness oder Evolvierbarkeit korrespondiert, bleibt offen und wird hier nicht nachgewiesen. | offen; keine Identität behauptet |
| NOR-001 | Größere technische Anschlussfähigkeit oder biologische Fitness darf für sich allein nicht als moralische Vorzugswürdigkeit behandelt werden. | normative Schutzregel / deklariert |

---

## 13. Schlussfolgerung

„Survival of the Anschlussfähigsten“ ist wissenschaftlich haltbar, wenn der Satz als explizit begrenzte Übertragung formuliert wird.

Biologisch bleibt Fitness ein kontextabhängiges Maß des reproduktiven Beitrags; je nach Modell wird sie absolut, relativ oder in einer anderen präzisen Form angegeben. Informatikseitig wird Anschlussfähigkeit als Menge gültig bewältigbarer Umgebungsspuren modelliert. Kann ein System jede invariantenerhaltende Reaktion eines anderen Systems simulieren, dann kann es mindestens dieselben endlichen Anforderungsspuren bewältigen. Unter derselben Gewichtung besitzt es daher keine geringere potentielle Viabilität.

Damit wird aus einem Aphorismus eine prüfbare Aussage:

\[
\boxed{
L_N(\mathcal B)\subseteq L_N(\mathcal A)
\Longrightarrow
A_{N,\omega}(\mathcal B)
\le
A_{N,\omega}(\mathcal A).
}
\]

Die Aussage bleibt relativ zu Umwelt, Horizont, Invarianten, Vertrag und Kosten. Sie verherrlicht weder Stärke noch grenzenlose Anpassung. Ein anschlussfähiges System erhält gerade diejenigen Unterschiede, Grenzen und Nachweise, die eine verantwortete Fortsetzung ermöglichen.

Die präzise Computerzeitalter-Fassung lautet deshalb:

> Nicht das unveränderte oder vermeintlich stärkste System setzt sich notwendig fort. Unter vergleichbaren Selektionsbedingungen besitzt dasjenige System die größere potentielle Viabilität, das mehr relevante Veränderungen durch gültige, invariantenerhaltende und überprüfbare Anschlüsse bewältigen kann.

Kurz:

\[
\boxed{\text{Survival of the Anschlussfähigsten}.}
\]

*q.e.d. Ingolf Lohmann*

---

## Literatur

1. Spencer, Herbert: *The Principles of Biology*. Band 1. Williams and Norgate, London, 1864, S. 444--445. Historischer Scan: <https://archive.org/download/cu31924003036864/cu31924003036864.pdf>.
2. Wallace, Alfred Russel an Charles Darwin, 2. Juli 1866. Darwin Correspondence Project, Letter 5140: <https://www.darwinproject.ac.uk/letter/?docId=letters/DCP-LETT-5140.xml>.
3. Darwin, Charles an Alfred Russel Wallace, 5. Juli 1866. Darwin Correspondence Project, Letter 5145: <https://www.darwinproject.ac.uk/letter/?docId=letters/DCP-LETT-5145.xml>.
4. Darwin, Charles: *The Variation of Animals and Plants under Domestication*. Band 2. John Murray, London, 1868. Darwin Online F878.2: <https://darwin-online.org.uk/converted/published/1868_Variation_F878/1868_Variation_F878.2.html>.
5. Darwin, Charles: *On the Origin of Species by Means of Natural Selection*. 5. Auflage. John Murray, London, 1869. Darwin Online F387: <https://darwin-online.org.uk/content/contentblock?basepage=1&hitpage=1&itemID=F387&viewtype=text>.
6. Gregory, T. Ryan: “Understanding Natural Selection: Essential Concepts and Common Misconceptions.” *Evolution: Education and Outreach* 2 (2009), S. 156--175. DOI: <https://doi.org/10.1007/s12052-009-0128-1>.
7. Orr, H. Allen: “Fitness and its role in evolutionary genetics.” *Nature Reviews Genetics* 10 (2009), S. 531--539. DOI: <https://doi.org/10.1038/nrg2603>.
8. Wadgymar, Susana M. et al.: “Defining Fitness in Evolutionary Ecology.” *International Journal of Plant Sciences* 185(3), 2024, S. 218--227. DOI: <https://doi.org/10.1086/729360>.
9. Lynch, Nancy; Vaandrager, Frits: “Forward and Backward Simulations: I. Untimed Systems.” *Information and Computation* 121(2), 1995, S. 214--233. DOI: <https://doi.org/10.1006/inco.1995.1134>.
10. Clarke, Edmund M.; Emerson, E. Allen; Sistla, A. Prasad: “Automatic Verification of Finite-State Concurrent Systems Using Temporal Logic Specifications.” *ACM TOPLAS* 8(2), 1986, S. 244--263. DOI: <https://doi.org/10.1145/5397.5399>.
11. Baier, Christel; Katoen, Joost-Pieter: *Principles of Model Checking*. MIT Press, 2008. <https://mitpress.mit.edu/9780262026499/principles-of-model-checking/>.
12. Wagner, Günter P.; Altenberg, Lee: “Complex Adaptations and the Evolution of Evolvability.” *Evolution* 50(3), 1996, S. 967--976. DOI: <https://doi.org/10.1111/j.1558-5646.1996.tb02339.x>.
13. Adami, Christoph: “Digital genetics: unravelling the genetic basis of evolution.” *Nature Reviews Genetics* 7 (2006), S. 109--118. DOI: <https://doi.org/10.1038/nrg1771>.
14. Ofria, Charles; Wilke, Claus O.: “Avida: A Software Platform for Research in Computational Evolutionary Biology.” *Artificial Life* 10(2), 2004, S. 191--229. DOI: <https://doi.org/10.1162/106454604773563612>.

---

## Vorgeschlagene Zitation nach erfolgter Publikation

Lohmann, Ingolf: *Survival of the Anschlussfähigsten: Eine operational-formale Übertragung des evolutionären Fitnessgedankens auf Computer-, Informations- und soziotechnische Systeme*. Version 1.0, Jahr 2026. DOI: **offen**.
