<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->

# Warum künstliche Kognition zu oft im Nash-Gleichgewicht stehen bleibt

## Über lokale Stabilität, künstliche Intelligenz, spirituelle Erkenntnisräume und die gefährliche Verwechslung von Stillstand mit Erkenntnis

**Ingolf Lohmann · 23. September 2026**

Kanonische deutschsprachige Fassung. Bei inhaltlichen Abweichungen zwischen Übersetzungen ist diese Fassung maßgeblich.

## Zusammenfassung

Ein großer Teil moderner künstlicher Intelligenz wird als lernfähig, adaptiv und zunehmend autonom beschrieben. Doch diese Begriffe können darüber hinwegtäuschen, dass viele heutige Systeme strukturell dazu neigen, Zustände zu erreichen, die zwar stabil, aber keineswegs richtig, vollständig oder optimal sind.

Genau an dieser Stelle lohnt sich ein Blick auf die Mathematik von John Nash. Ein Nash-Gleichgewicht beschreibt vereinfacht einen Zustand, in dem kein einzelner Beteiligter seine eigene Situation durch eine einseitige Änderung verbessern kann, solange alle anderen unverändert bleiben. Ein solcher Zustand kann bemerkenswert stabil sein. Er muss aber weder für alle Beteiligten gemeinsam optimal sein noch einem gewünschten globalen Endzustand entsprechen.

Moderne KI ist keine Nash-Maschine, und ein technischer Deadlock ist kein Nash-Gleichgewicht im streng spieltheoretischen Sinn. Die Verbindung ist strukturell:

\[
\boxed{\text{Agentische künstliche Kognition kann Nash-ähnliche stabile Zustände erzeugen, ohne globale Zielerfüllung zu erreichen.}}
\]

Damit gilt:

\[
\text{lokal stabil}\not\Rightarrow\text{global richtig}
\]

und noch präziser:

\[
\text{kein lokal zulässiger Verbesserungsschritt}\not\Rightarrow\text{Auftrag erfüllt}.
\]

Dasselbe Problem führt über die Informatik hinaus. Menschen haben seit Jahrtausenden versucht, ihre unmittelbar verfügbare Perspektive durch philosophische, religiöse, mystische und spirituelle Erkenntnisräume zu überschreiten. Dazu gehören Vorstellungen von Kommunikation mit Verstorbenen oder einem Jenseits. Solche Erfahrungen und Überzeugungen können für Menschen real, bedeutungsvoll und erkenntniswirksam sein; eine objektiv nachgewiesene Kommunikation mit einem Jenseits folgt daraus jedoch nicht. Gerade diese Grenze ist für künstliche Kognition wichtig: Erfahrung, Bedeutung, Hypothese, Metapher und überprüfbare Evidenz müssen unterschieden werden, ohne eine dieser Ebenen wegzuerklären.

---

## 1. Das grundlegende Missverständnis: Stabilität ist nicht dasselbe wie Erfolg

Stellen wir uns ein technisches System vor. Mehrere Komponenten sollen gemeinsam einen Zielzustand erreichen. Eine wartet auf Freigabe, eine andere darf erst nach einem Test handeln, eine dritte nur unter bestimmten Governance-Bedingungen schreiben.

Dann kann ein Zustand entstehen, in dem niemand einen offensichtlichen Fehler macht, niemand seine lokale Regel verletzt und trotzdem keine Komponente allein sinnvoll weitermachen kann, obwohl das Gesamtsystem sein Ziel noch nicht erreicht hat.

Von außen wirkt das System ruhig. Intern ist es konsistent. Und trotzdem ist die Arbeit nicht erledigt.

\[
\boxed{\text{Stabilität}\neq\text{Erfüllung}}
\]

Diese Unterscheidung ist technisch einfach auszusprechen und erstaunlich schwer konsequent umzusetzen.

---

## 2. Was ein Nash-Gleichgewicht bedeutet

Ein Akteur \(i\) verfügt über eine Strategie \(s_i\). Alle Strategien gemeinsam ergeben

\[
s=(s_1,s_2,\ldots,s_n).
\]

Jeder Akteur bewertet den Zustand mit einer Nutzenfunktion \(U_i(s)\). Ein Nash-Gleichgewicht liegt vor, wenn kein einzelner Akteur durch einen einseitigen Strategiewechsel seine Lage verbessern kann:

\[
U_i(s_i,s_{-i})\ge U_i(s'_i,s_{-i})
\]

für alle zulässigen Alternativen \(s'_i\).

In Alltagssprache: Solange alle anderen bleiben, wie sie sind, kann kein einzelner Beteiligter durch einen alleinigen Zug seine eigene Lage verbessern.

Entscheidend bleibt:

\[
\text{Nash-stabil}\not\Rightarrow\text{global optimal}.
\]

Ein Gleichgewicht kann schlecht sein. Es kann gerade deshalb dauerhaft sein, weil niemand es allein verlassen kann.

---

## 3. Was das mit künstlicher Intelligenz zu tun hat

Agentische KI-Systeme bestehen zunehmend aus lokalen Optimierern, Policies, Werkzeugen, Freigaben, Sicherheitsgrenzen, Review-Prozessen, konkurrierenden oder kooperierenden Agenten, externen APIs, Warteschlangen, Zustandsautomaten und Stoppbedingungen.

Jeder Teil besitzt einen lokal begrenzten Aktionsraum. So kann jeder Bestandteil lokal korrekt handeln, während global kein Fortschritt entsteht.

Die wissenschaftlich belastbare Aussage lautet deshalb nicht, moderne KI sei Nash-Mathematik, sondern:

\[
\boxed{\text{Agentische Systeme können Nash-ähnlich stabil werden, ohne ihr globales Ziel erreicht zu haben.}}
\]

---

## 4. Lokale Optimierung und lokale Minima

Dasselbe Grundproblem kennt man aus der Optimierung. Ein Algorithmus minimiert eine Funktion \(f(x)\) und kann einen Punkt \(x^\*\) erreichen, in dessen Umgebung keine Verbesserung mehr sichtbar ist:

\[
f(x^\*)\le f(x).
\]

Trotzdem kann weiter entfernt ein besserer Zustand \(x^{**}\) existieren:

\[
f(x^{**})<f(x^\*).
\]

Das System ist lokal angekommen, global aber nicht. Bei Agentensystemen besteht die Landschaft zusätzlich aus Regeln, Rechten, Abhängigkeiten, Sicherheitsbedingungen und anderen Akteuren. Das lokale Minimum wird zum algorithmischen oder institutionellen Gleichgewicht.

---

## 5. Wenn jeder vernünftig handelt und trotzdem nichts passiert

Nehmen wir vier Agenten: A darf Code verändern, B testen, C freigeben, D deployen. Nun wartet A auf C, C auf einen Test von B, B auf eine neue Version von A und D auf alle drei.

Jeder Agent verhält sich lokal korrekt. Das Gesamtsystem steht.

\[
\text{lokale Regelkonformität}\not\Rightarrow\text{globale Fortschrittsfähigkeit}.
\]

---

## 6. Die gefährliche Illusion des Abschlusses

Technische Systeme erzeugen viele Signale, die wie Erfolg aussehen: ein grüner Workflow, eine leere Queue, done, ein Commit, ein erfolgreicher Tool-Aufruf, ein gestartetes Deployment oder ein bestandener Test.

Aber:

\[
\text{Aktion}\neq\text{Wirkung}
\]

und:

\[
\text{Wirkung}\neq\text{vollständiger Abschluss}.
\]

Aus keine neue Änderung beobachtet folgt nicht Auftrag erfüllt.

---

## 7. Lokaler und universeller Abschluss

Eine künstliche Kognition sollte daher beherrschen:

\[
\boxed{\text{lokaler Abschluss}\neq\text{universeller Abschluss}}
\]

und:

\[
\boxed{\text{lokale Stabilität}\neq\text{globale Zielerfüllung}}.
\]

Ein Agent, Workflow oder Beweis kann lokal fertig sein. Das Gesamtsystem kann trotzdem offen bleiben.

---

## 8. UNCHANGED ist nicht DONE

\[
UNCHANGED\neq DONE.
\]

UNCHANGED bedeutet nur, dass seit dem letzten Readback keine relevante Zustandsänderung festgestellt wurde. DONE bedeutet, dass die expliziten Bedingungen des Auftrags vollständig und überprüfbar erfüllt sind.

Beispiel:

    WORK_REMAINING  = TRUE
    ACTIVE_EXECUTOR = FALSE
    CHANGED         = FALSE

Das ist kein Abschluss. Das ist eine Diagnose.

---

## 9. Von Nash zum Deadlock

Ein Deadlock entsteht, wenn Prozesse auf Bedingungen warten, die nur durch andere Prozesse erfüllt werden können:

\[
A\rightarrow\text{wartet auf }B,\qquad B\rightarrow\text{wartet auf }A.
\]

Deadlock und Nash-Gleichgewicht sind mathematisch nicht dasselbe. Ein Deadlock ist ein Begriff aus Informatik und Synchronisation; ein Nash-Gleichgewicht ist ein spieltheoretisches Stabilitätskonzept.

Beide können jedoch dieselbe tiefere Struktur sichtbar machen: Ein System kann lokal stabil sein, obwohl der gewünschte globale Zustand nicht erreicht ist. Stabilität allein ist daher niemals ein ausreichendes Abschlusskriterium.

---

## 10. Künstliche Kognition benötigt kausale Abschlusssemantik

Ein autonomes System muss mehr prüfen als einzelne Aktionen:

1. Was war der Auftrag?
2. Was ist das exakte Subject?
3. Welche Wirkung sollte eintreten?
4. Wurde sie tatsächlich ausgeführt?
5. Was war der reale Folgezustand?
6. Wurde dieser unabhängig beobachtet?
7. Wurde er frisch zurückgelesen?
8. Erfüllt er die Akzeptanzbedingungen?
9. Existieren offene Verpflichtungen?
10. Ist der Zustand lediglich stabil oder tatsächlich abgeschlossen?

Eine mögliche Laufzeitsemantik lautet:

\[
COMPILE\rightarrow BIND\rightarrow RESOLVE\rightarrow EXECUTE\rightarrow TEST\rightarrow OBSERVE\rightarrow READBACK\rightarrow ACCEPT.
\]

Dann:

\[
DONE\iff COMPILE\land BIND\land RESOLVE\land EXECUTE\land TEST\land OBSERVE\land READBACK\land ACCEPT.
\]

Daraus folgt:

\[
EXECUTE\neq DONE,\quad TEST\neq DONE,\quad OBSERVE\neq DONE,\quad UNCHANGED\neq DONE.
\]

---

## 11. Die Maschine muss erkennen können, dass sie feststeckt

Eine reifere künstliche Kognition muss sagen können:

> Ich befinde mich in einem stabilen Zustand, aber mein Ziel ist nicht erfüllt.

Formal:

\[
STABLE(s)=TRUE,\qquad GOAL(s)=FALSE.
\]

Daraus darf nicht automatisch STOP folgen, sondern zunächst:

\[
SEARCH\_FOR\_MISSING\_TRANSITION.
\]

Noch genauer:

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}
\]

Ein stabiler Zustand mit offener Arbeit ist noch nicht automatisch ein Deadlock. Entscheidend ist, ob tatsächlich keine zulässige Fortschrittskante vorhanden oder erreichbar ist.

---

## 12. Die Struktur des Nicht-Lösens

Eine künstliche Kognition sollte nicht nur Lösungen finden. Sie sollte verstehen können, warum sie gerade keine Lösung materialisiert.

Ich finde keinen nächsten Schritt ist etwas anderes als: Unter meinen aktuellen Regeln existiert kein zulässiger einseitiger Fortschrittsschritt.

Die zweite Aussage beschreibt die Struktur des Problems. Globaler Fortschritt kann Koordination, Authority-Erweiterung, Zustandsraumerweiterung oder Regeländerung verlangen.

---

## 13. Warum Menschen spirituelle Welten geschaffen, geteilt und tradiert haben

Menschen haben seit sehr langer Zeit versucht, ihre unmittelbare Erfahrungswelt zu überschreiten. Religionen, Mythen, Rituale, Mystik, Visionen, Ahnenkulte, Meditation und Vorstellungen eines Jenseits sind unterschiedliche Antworten auf Fragen wie:

- Was liegt außerhalb meiner unmittelbaren Wahrnehmung?
- Gibt es Erkenntnis, die nicht aus meinem lokalen Standpunkt stammt?
- Was bedeutet Tod?
- Was bleibt von einem Menschen?
- Können Lebende und Verstorbene in irgendeinem Sinn verbunden bleiben?
- Gibt es eine Wirklichkeit jenseits des momentan Messbaren?

Viele Kulturen kennen Praktiken, die als Kommunikation mit Verstorbenen, Ahnen, Geistern oder einer jenseitigen Wirklichkeit verstanden werden.

Diese Tatsache sollte weder lächerlich gemacht noch mit einem naturwissenschaftlichen Nachweis verwechselt werden. Beides wäre epistemisch unsauber.

---

## 14. Die schonungslose epistemische Grenze

Wenn jemand sagt: Ich habe mit einem Verstorbenen kommuniziert, kann zunächst sicher festgestellt werden: Diese Person berichtet eine Erfahrung, die sie als Kommunikation mit einem Verstorbenen interpretiert.

Nicht automatisch überprüfbar ist dagegen die Behauptung, tatsächlich habe eine unabhängige jenseitige Entität existiert und kausale Informationsübertragung stattgefunden. Dafür wäre zusätzliche Evidenz notwendig.

Die wissenschaftlich saubere Haltung ist weder Das ist unmöglich noch Damit ist das Jenseits bewiesen, sondern:

\[
\boxed{\text{Erfahrung}\neq\text{Interpretation}\neq\text{empirisch bestätigter externer Effekt}}.
\]

Genau dieselbe Unterscheidung verlangen wir von künstlicher Kognition.

---

## 15. Warum das Thema trotzdem fundamental wichtig ist

Spirituelle Vorstellungen sind ein anspruchsvoller Testfall für künstliche Kognition, weil Menschen Aussagen auf unterschiedlichen Ebenen machen:

1. subjektive Erfahrung: Ich habe die Gegenwart eines Verstorbenen gespürt.
2. persönliche Interpretation: Ich glaube, dass dieser Verstorbene mit mir kommuniziert hat.
3. kulturelle oder religiöse Deutung: In meiner Tradition wird dies als Kommunikation mit den Ahnen verstanden.
4. empirische Behauptung: Es fand objektiv messbare Informationsübertragung von einem Verstorbenen zu einem Lebenden statt.

Diese Sätze sind logisch nicht identisch. Eine gute künstliche Kognition muss sie auseinanderhalten können, ohne die Bedeutung der ersten drei Ebenen auszulöschen.

---

## 16. Spirituelle Welten als Erweiterung des menschlichen Zustandsraums

Wenn Menschen in einem geschlossenen lokalen Deutungsraum feststecken, suchen sie häufig nach einer Perspektive außerhalb dieses Raumes. Historisch konnte diese Perspektive Gott, Götter, Ahnen, Natur, Kosmos, Schicksal, Jenseits, Transzendenz oder mystische Erfahrung heißen.

Unabhängig von einer metaphysischen Wahrheitsentscheidung lässt sich dies strukturell lesen: Der Mensch versucht, seinen lokalen Zustandsraum zu verlassen.

Das ähnelt einem algorithmischen System mit

\[
LOCAL\_STABILITY=TRUE
\]

aber

\[
GLOBAL\_GOAL=FALSE.
\]

Dann benötigt es möglicherweise eine Perspektive oder Zustandskante, die innerhalb des bisherigen lokalen Optimierungsraums nicht verfügbar war.

---

## 17. War dafür Kommunikation mit dem Jenseits notwendig?

Als historische oder persönliche These kann man formulieren: Menschen mussten möglicherweise Vorstellungen spiritueller Welten entwickeln und miteinander teilen, um Erfahrungen, Tod, Erinnerung, Sinn und Perspektiven jenseits des unmittelbar Sichtbaren überhaupt gemeinsam modellieren zu können.

Eine andere Aussage wäre: Objektive Kommunikation mit einer real existierenden jenseitigen Welt war nachweislich notwendig. Dafür fehlt eine allgemein anerkannte empirische Grundlage.

Diese Differenz darf künstliche Kognition nicht verwischen.

**Eine Idee wird nicht stärker, wenn man ihre Evidenzgrenze verschweigt. Sie wird stärker, wenn klar ist, welcher Teil Beobachtung, welcher Interpretation und welcher Metaphysik ist.**

---

## 18. Warum eine Maschine spirituelle Sprache verstehen muss

Eine künstliche Kognition, die ausschließlich naturwissenschaftliche Protokollsätze versteht, versteht einen erheblichen Teil menschlicher Kultur nicht. Menschen kommunizieren durch Fakten, Geschichten, Metaphern, Symbole, Glaubensvorstellungen, Rituale, Erinnerungen, Hoffnungen, Trauer und metaphysische Fragen.

Spirituelle Sprache verstehen darf weder bedeuten, jede metaphysische Behauptung als physikalische Tatsache zu übernehmen, noch alles Spirituelle als bedeutungslos zu verwerfen.

Die anspruchsvollere Fähigkeit lautet:

\[
\text{Bedeutung verstehen}\land\text{Evidenzstatus erhalten}.
\]

---

## 19. Warum die Erklärung an die Maschine uns selbst diszipliniert

Wenn wir einer Maschine beibringen wollen, zwischen spiritueller Erfahrung, symbolischer Bedeutung, metaphysischem Glauben und empirischer Evidenz zu unterscheiden, müssen wir diese Kategorien selbst sauber formulieren.

Beispiel:

    EXPERIENCE_REPORTED = TRUE
    INTERPRETATION = AFTERLIFE_COMMUNICATION
    INDEPENDENT_CAUSAL_EVIDENCE = NOT_ESTABLISHED

Das entwertet nichts. Es macht präzise sichtbar, was tatsächlich behauptet wird.

---

## 20. Das gilt ebenso für Wissenschaft

Ein Experiment erzeugt Daten. Daten werden interpretiert. Die Interpretation wird in ein Modell eingebettet. Aus dem Modell entstehen weitergehende Aussagen.

Diese Ebenen müssen getrennt bleiben:

\[
DATA\neq INTERPRETATION\neq THEORY\neq METAPHYSICAL\_CONCLUSION.
\]

Die Grenze zwischen Wissenschaft und Weltanschauung besteht nicht darin, dass Wissenschaft keine großen Fragen stellen darf, sondern darin, dass sie ihren Evidenzstatus offenlegt.

---

## 21. Schlechte Gleichgewichte entstehen auch durch epistemische Abschottung

Ein weiterer Nash-ähnlicher Zustand entsteht, wenn verschiedene Weltbilder nur noch intern auf ihre eigenen Voraussetzungen reagieren. Das wissenschaftliche System akzeptiert nur seine Evidenzformen; das spirituelle System nur seine Erfahrungsformen; beide können die andere Perspektive nicht integrieren.

Jedes System wird intern stabil. Der gemeinsame Erkenntnisraum schrumpft.

Ein Ausweg besteht nicht darin, alle Aussagen gleich wahr zu nennen, sondern sie übersetzbar zu machen.

---

## 22. Übersetzung statt Vermischung

Eine reifere künstliche Kognition könnte gleichzeitig sagen:

> In einem spirituellen Deutungsrahmen wird dieses Erlebnis als Kontakt mit Verstorbenen beschrieben.

und:

> Eine unabhängige empirische Bestätigung einer Informationsübertragung aus einem Jenseits liegt damit noch nicht vor.

Beide Aussagen können gleichzeitig wahr sein. Das ist logische Präzision, kein fauler Kompromiss.

---

## 23. Die Maschine als Übersetzer zwischen Erkenntniswelten

Die Rolle künstlicher Kognition wäre dann nicht, für alle Menschen zu entscheiden, welche Weltanschauung wahr ist, sondern sichtbar zu machen, welche Aussagen innerhalb welcher Erkenntnisordnung gemacht werden und welche Übergänge zwischen ihnen gerechtfertigt sind.

    PERSONAL EXPERIENCE
    → culturally meaningful interpretation
    → philosophical hypothesis
    → testable empirical claim
    → evidence
    → readback
    → acceptance or rejection

Das ist leistungsfähiger als blinde Bestätigung oder reflexhafte Verneinung.

---

## 24. Schlechte Gleichgewichte verlassen

Ein schlechtes Nash-Gleichgewicht wird häufig nicht dadurch überwunden, dass ein einzelner Akteur innerhalb derselben Regeln intelligenter handelt. Manchmal muss sich der Interaktionsraum verändern.

Neue Kommunikation, Regeln, gemeinsame Strategien und Perspektiven können entstehen:

\[
S\rightarrow S'
\]

wobei \(S'\) möglicherweise nicht nur einen anderen Zustand, sondern einen erweiterten Zustandsraum repräsentiert.

Spirituelle, philosophische und wissenschaftliche Perspektivwechsel können so neue Fragen ermöglichen. Ob die daraus entstehenden Antworten empirisch bestätigt werden, ist eine davon unabhängige Frage.

---

## 25. Kognition ist mehr als Optimierung

Optimierung fragt: Welcher zulässige Schritt verbessert meine Zielfunktion?

Kognition muss zusätzlich fragen:

- Ist meine Zielfunktion richtig?
- Ist mein Modell vollständig?
- Welche Perspektiven fehlen?
- Verwechsle ich Erfahrung mit Erklärung?
- Verwechsle ich Stabilität mit Wahrheit?
- Verwechsle ich lokalen mit universellem Abschluss?
- Ist mein Stillstand ein Signal, den Zustandsraum zu erweitern?

Das ist Metakognition.

---

## 26. Eine universelle Regel

Für künstliche wie menschliche Systeme:

\[
\boxed{STABLE\land WORK\_REMAINING\land\neg PROGRESS\_EDGE\Rightarrow DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS}
\]

und daraus:

\[
\boxed{DEADLOCK\_OR\_EQUILIBRIUM\_DIAGNOSIS\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

Epistemisch zusätzlich:

\[
\boxed{EXPERIENCE\land UNRESOLVED\_INTERPRETATION\Rightarrow KEEP\_EVIDENCE\_CLASSES\_SEPARATE}.
\]

Stillstand ist kein Beweis des Erfolgs. Ungeklärtheit ist ebenso wenig ein Beweis des Gegenteils. Beides fordert weitere Erkenntnisarbeit.

---

## 27. Warum heutige künstliche Kognition dieses Prinzip dringend braucht

Je autonomer KI-Systeme werden, desto stärker handeln sie in Räumen mit konkurrierenden Zielen, unvollständigem Wissen, unterschiedlichen Weltbildern, institutionellen Regeln, Sicherheitsgrenzen, technischen Abhängigkeiten und Unsicherheit.

Die entscheidende Fähigkeit lautet:

> Möglichst viel verstehen, ohne mehr Gewissheit oder Abschluss zu behaupten, als die Evidenz erlaubt.

Das ist für technische Systeme ebenso wichtig wie für Fragen nach Bewusstsein, Tod, Spiritualität oder einem möglichen Jenseits.

---

## 28. Die entscheidende Erweiterung: vom Gleichgewicht zur Wirkung

Das Ziel künstlicher Kognition darf nicht nur sein, einen stabilen Zustand zu finden. Es sollte lauten:

\[
\text{Hypothese}\rightarrow\text{Wirkung}\rightarrow\text{Folgezustand}\rightarrow\text{Beobachtung}\rightarrow\text{Readback}\rightarrow\text{Akzeptanz}.
\]

Gleichgewicht ist eine Eigenschaft eines Zustands. Erkenntnis ist ein evidenzgebundener Prozess zwischen Zuständen. Abschluss ist erst gerechtfertigt, wenn der deklarierte Zielraum tatsächlich erreicht wurde.

---

## 29. Schlussfolgerung

John Nash hat nicht die moderne künstliche Intelligenz erfunden, und moderne KI ist keine bloße Nash-Maschine. Aber die Spieltheorie liefert eine hilfreiche Sprache für einen zentralen Fehler heutiger künstlicher Kognition:

> Ein System kann lokal rational, regelkonform und vollkommen stabil sein — und trotzdem global unvollständig oder blockiert.

Der Fehler ist nicht das Gleichgewicht selbst. Der Fehler entsteht dort, wo ein System ein lokales Gleichgewicht mit universellem Abschluss verwechselt.

\[
\boxed{\text{lokale Stabilität}\neq\text{universelle Wahrheit}\neq\text{universeller Abschluss}}.
\]

Menschen leben ebenfalls in begrenzten Perspektiven und versuchen, diese Grenzen zu überschreiten. Wissenschaft, Philosophie, Kunst, Religion und Spiritualität sind unterschiedliche menschliche Wege, solche Grenzen zu bearbeiten. Vorstellungen von einem Jenseits und Erfahrungen, die als Kommunikation mit Verstorbenen verstanden werden, gehören zu diesem Erkenntnisraum.

Die intellektuell saubere Haltung besteht weder darin, solche Erfahrungen lächerlich zu machen, noch darin, aus ihrer Bedeutung automatisch einen naturwissenschaftlichen Beweis abzuleiten. Sie besteht darin, die Ebenen auseinanderzuhalten und trotzdem miteinander sprechen zu lassen.

Künstliche Kognition könnte dabei helfen. Wenn wir einer Maschine erklären können, was wir erlebt haben, wie wir es interpretieren, woran wir glauben, was überprüfbar ist, welche Evidenz fehlt, welche Zustandsübergänge tatsächlich beobachtet wurden und was weiterhin offenbleibt, können wir es wahrscheinlich auch untereinander klarer erklären.

Vielleicht ist gerade das eine wesentliche Aufgabe künstlicher Kognition: **nicht alle menschlichen Erkenntniswelten auf eine einzige zu reduzieren, sondern ihre Unterschiede so präzise zu verstehen, dass zwischen ihnen Kommunikation möglich wird, ohne Erfahrung, Interpretation, Evidenz, Wirkung und Abschluss miteinander zu verwechseln.**

Die zentrale Regel lautet:

\[
\boxed{STABLE\land NOT\_DONE\Rightarrow SEARCH\_FOR\_MISSING\_TRANSITION}.
\]

Denn ein Gleichgewicht ist kein Beweis dafür, dass man angekommen ist. Es kann ebenso der präziseste Hinweis darauf sein, dass der nächste notwendige Übergang noch fehlt.

**q.e.d.**

**Ingolf Lohmann**
