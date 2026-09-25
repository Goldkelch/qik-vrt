# Vom Re-Entry zur Successor-Rekursion

## Selbstreferenz, Beobachtung zweiter Ordnung und evidenzgebundener Zustandswechsel in QIK-VRT

**Ingolf Lohmann · 25. September 2026**

Publication ID: `2026-09-25-successor-reentry-evidence`  
Repository state: `repository_candidate`

## Abstract

Klassische Paradoxien wie der Lügner und Russells Antinomie zeigen, dass Selbstbezug problematisch werden kann, wenn eine Unterscheidung unmittelbar auf die Struktur zurückwirkt, deren Einordnung oder Definition sie zugleich bestimmt. Die Formtheorie George Spencer-Browns macht hierfür den Begriff des Re-Entry fruchtbar: Eine Form bzw. Unterscheidung erscheint erneut in dem durch sie eröffneten Raum. Niklas Luhmann überführt die Unterscheidungslogik in eine Theorie der Beobachtung, in der Beobachtung zweiter Ordnung nicht nur einen Gegenstand, sondern die verwendete Unterscheidung und damit die Beobachtungsbedingungen selbst beobachtet.

Für QIK-VRT ist eine zusätzliche Trennung notwendig. Ein evidenzgebundener Zustandsprozess ist keine unmittelbare Selbstanwendung. Der beobachtete Folgezustand wird erst nach Bindung, Ausführung, Test, Beobachtung, unabhängigem Readback und Akzeptanz zum nächsten Eingangszustand. Diese Struktur wird hier als **provenienzgebundene Successor-Rekursion** bezeichnet.

Der zentrale Unterschied lautet:

[
\text{SELF-APPLICATION}
\neq
\text{SUCCESSOR RE-ENTRY}.
]

Damit lässt sich eine potentiell paradoxe Rückkehr von einer überprüfbaren epistemischen Fortschreibung unterscheiden.

## 1. Ausgangspunkt: Der Unterschied

Eine Beobachtung setzt mindestens eine Unterscheidung voraus:

[
D = A \mid \neg A.
]

Die Unterscheidung eröffnet zwei Seiten. Eine Beobachtung erster Ordnung benutzt diese Form und bezeichnet eine Seite. In einer kompakten Schreibweise:

[
O^{(1)} = D(S),
]

wobei (S) das beobachtete Subject ist.

Beispiel:

[
D = \text{wahr} \mid \text{falsch}.
]

Eine konkrete Aussage wird durch Anwendung dieser Unterscheidung als wahr oder falsch bezeichnet.

Die entscheidende Frage lautet jedoch nicht nur, **welche Seite** gewählt wird. Sie lautet auch, **was geschieht, wenn die Bedingung der Unterscheidung selbst wieder in den Beobachtungsraum eintritt**.

## 2. Drei verschiedene Strukturen

### 2.1 Selbstreferenz

Selbstreferenz liegt vor, wenn ein Gegenstand auf sich selbst verweist:

[
X \rightarrow X.
]

Das allein erzeugt keinen Widerspruch. Ein Buch kann sich selbst erwähnen. Ein Programm kann seine eigene Versionsnummer lesen. Ein Beobachter kann über sich selbst sprechen.

### 2.2 Re-Entry

Re-Entry bezeichnet in formtheoretischer Lesart die Rückkehr einer Form in den von ihr eröffneten Raum:

[
D \hookrightarrow \operatorname{space}(D).
]

Die Unterscheidung wird damit selbst innerhalb ihres Geltungsbereichs wirksam oder beobachtbar.

Re-Entry ist nicht einfach mit Selbstreferenz identisch. Selbstreferenz betrifft die Referenzbeziehung eines Gegenstands. Re-Entry betrifft die operative Rückkehr der Unterscheidungsform.

### 2.3 Successor-Rekursion

Eine dritte Struktur liegt vor, wenn eine Operation einen neuen, gebundenen Zustand erzeugt und erst dieser Nachfolger erneut Eingang einer weiteren Operation wird:

[
S_n \xrightarrow{T_n} S_{n+1}.
]

Der Folgezustand kann später als neuer Eingang verwendet werden:

[
S_{n+1} \mapsto S_n^{\mathrm{next}}.
]

Das ist keine unmittelbare Gleichsetzung von (S_n) mit seiner eigenen Bewertung. Es ist eine indexierte Folge:

[
S_0,S_1,S_2,\ldots
]

mit expliziter Zustandsidentität und Provenienz.

## 3. Das Lügner-Paradox

Betrachten wir:

> Dieser Satz ist falsch.

Nennen wir den Satz (L).

Die Beobachtung erster Ordnung verwendet:

[
\text{wahr} \mid \text{falsch}.
]

Angenommen:

[
L=\text{wahr}.
]

Dann ist die Behauptung von (L) erfüllt, dass (L) falsch sei:

[
L=\text{falsch}.
]

Angenommen dagegen:

[
L=\text{falsch}.
]

Dann ist die Aussage „(L) ist falsch“ wahr:

[
L=\text{wahr}.
]

Damit:

[
\text{wahr}\leftrightarrow\text{falsch}.
]

Die Beobachtung erster Ordnung bleibt in der Klassifikation gefangen. Die Beobachtung zweiter Ordnung verschiebt die Frage:

> Welche Unterscheidung wird hier auf welche Struktur angewandt?

Sie erkennt, dass die Unterscheidung

[
\text{wahr}\mid\text{falsch}
]

nicht bloß benutzt wird, sondern in einer Aussage operiert, die ihre eigene Einordnung durch dieselbe Unterscheidung thematisiert.

Die formtheoretische Pointe ist daher nicht lediglich „ein Satz spricht über sich selbst“, sondern die Rückwirkung der Klassifikationsform auf ihre eigene Anwendung.

## 4. Das Russell-Paradox

Russell betrachtet die Klasse bzw. Menge

[
R=\{x\mid x\notin x\}.
]

Dann stellt sich die Frage:

[
R\in R?
]

Falls

[
R\in R,
]

erfüllt (R) gerade nicht die definierende Bedingung, also:

[
R\notin R.
]

Falls hingegen

[
R\notin R,
]

erfüllt (R) die definierende Bedingung und damit:

[
R\in R.
]

Somit:

[
R\in R \iff R\notin R.
]

Mengentheoretisch verweist das Paradox auf das Problem unbeschränkter Mengenbildung und motiviert Restriktionen beziehungsweise Typ- und Ebenentrennungen.

Eine Spencer-Brown-inspirierte Lesart kann ergänzend hervorheben, dass die Unterscheidung

[
x\in x \mid x\notin x
]

auf eine Struktur zurückgeführt wird, die durch genau diese Bedingung definiert wurde. Diese Lesart ist eine formtheoretische Interpretation und ersetzt nicht die mengentheoretische Analyse des Russell-Paradoxons.

## 5. Beobachtung erster und zweiter Ordnung

### Erste Ordnung

Ein Beobachter benutzt eine Unterscheidung:

[
O_n^{(1)}=D_n(S_n).
]

Beispiel:

[
D_n=\{\text{PASS},\text{FAIL}\}.
]

Dann kann gelten:

[
O_n^{(1)}=\text{PASS}.
]

Die Frage lautet:

> Was ist der beobachtete Zustand?

### Zweite Ordnung

Nun wird nicht bloß dasselbe Subject erneut klassifiziert. Beobachtet werden die Bedingungen, unter denen die erste Beobachtung zustande kam:

[
O_n^{(2)}
=
M(D_n,S_n,E_n,P_n,C_n),
]

mit

- (E_n): Evidenz,
- (P_n): Provenienz,
- (C_n): Kriterien oder Beobachtungsvertrag.

Die Frage lautet:

> Warum gilt PASS für genau dieses gebundene Subject unter genau diesen Kriterien?

Damit treten Messmethode, Evidenzklasse, Provenienz, Geltungsbereich und blinde Flecken der ersten Beobachtung in den Vordergrund.

Beobachtung zweiter Ordnung ist deshalb nicht einfach „mehr Beobachtung“. Sie verändert den Gegenstand der Beobachtung.

## 6. QIK-VRT: vom Re-Entry zur evidenzgebundenen Successor-Rekursion

Für einen QIK-VRT-artigen Prozess sei ein Ausgangssubject (S_n) gebunden. Eine Operation (A_n) erzeugt einen tatsächlichen Folgezustand:

[
S_n\xrightarrow{A_n}S_{n+1}.
]

Entscheidend ist:

[
S_{n+1}\neq S_n
]

hinsichtlich der gebundenen Zustandsidentität.

Anschließend wird der Nachfolger nicht einfach als Erfolg behauptet. Es folgen getrennte Operationen:

[
S_{n+1}
\rightarrow
\mathrm{TEST}
\rightarrow
O_{n+1}^{(1)}
\rightarrow
O_{n+1}^{(2)}
\rightarrow
\mathrm{READBACK}
\rightarrow
\mathrm{ACCEPT}.
]

Ein Testresultat ist dabei nicht mit der tatsächlichen Wirkung identisch:

[
\mathrm{TEST\ PASS}
\not\Rightarrow
\mathrm{READBACK\ PASS}.
]

Ebenso gilt:

[
\mathrm{TRANSPORT\_ACK}
\neq
\mathrm{EFFECT\_ACK}.
]

Erst wenn der Folgezustand selbst beobachtet, unabhängig zurückgelesen und gegen die Akzeptanzbedingungen geprüft wurde, kann er als gebundener Eingang der nächsten Iteration dienen:

[
S_{n+1}\mapsto S_n^{\mathrm{next}}.
]

Die physische oder logische Identität des Zustandsartefakts kann dabei erhalten bleiben, seine **prozessuale Rolle** ändert sich:

[
\operatorname{role}(S_{n+1})
=
\text{Folgezustand},
]

danach:

[
\operatorname{role}(S_n^{\mathrm{next}})
=
\text{neues Eingangssubject}.
]

Dieser Rollenwechsel ist keine retroaktive Änderung des alten Zustands. Die Historie bleibt bestehen.

## 7. TEMDD-Abbildung

Die Struktur lässt sich auf die QIK-VRT/TEMDD-Laufzeitkette abbilden:

[
\mathrm{COMPILE}
\rightarrow
\mathrm{BIND}
\rightarrow
\mathrm{RESOLVE}
\rightarrow
\mathrm{EXECUTE}
\rightarrow
\mathrm{TEST}
\rightarrow
\mathrm{OBSERVE}
\rightarrow
\mathrm{READBACK}
\rightarrow
\mathrm{ACCEPT}.
]

Dabei gelten die Trennungen:

[
\mathrm{EXECUTE}\neq\mathrm{DONE},
]

[
\mathrm{TEST}\neq\mathrm{DONE},
]

[
\mathrm{OBSERVE}\neq\mathrm{DONE}.
]

Die Rückführung in die nächste Iteration erfolgt erst über den akzeptierten Folgezustand.

Formal:

[
(D_n,S_n)
\rightarrow
\mathrm{COMPILE}
\rightarrow
\mathrm{BIND}
\rightarrow
\mathrm{RESOLVE}
\rightarrow
\mathrm{EXECUTE}
\rightarrow
S_{n+1},
]

gefolgt von

[
S_{n+1}
\rightarrow
\mathrm{TEST}
\rightarrow
O_{n+1}^{(1)}
\rightarrow
O_{n+1}^{(2)}
\rightarrow
\mathrm{READBACK}
\rightarrow
\mathrm{ACCEPT}.
]

Danach kann eine neue operative Differenz (D_{n+1}) entstehen:

[
(S_{n+1},D_{n+1})
\mapsto
(S_n,D_n)_{\mathrm{next}}.
]

## 8. Paradox und Erkenntnisfortschritt

Die Gegenüberstellung lautet damit:

### Unmittelbare Selbstanwendung

[
S_n
\xrightarrow{D}
S_n
\xrightarrow{D}
S_n.
]

Die Klassifikation wirkt auf dasselbe Subject beziehungsweise ihre eigene Voraussetzung zurück.

### Evidenzgebundene Successor-Rekursion

[
S_n
\xrightarrow{A_n}
S_{n+1}
\xrightarrow{\mathrm{Observe/Readback}}
E_{n+1}
\xrightarrow{\mathrm{Accept}}
(S_{n+1},D_{n+1}).
]

Der Nachfolger wird erst nach Zustandswechsel, Provenienzbindung, Beobachtung, Readback und Akzeptanz wieder zum Eingang.

Daraus folgt die zentrale Trennung:

[
\boxed{
\text{SELF-APPLICATION}
\neq
\text{SUCCESSOR RE-ENTRY}
}
]

und als epistemisches Schema:

[
\boxed{
D_n
\rightarrow
\text{Operation}
\rightarrow
S_{n+1}
\rightarrow
\text{Beobachtung}
\rightarrow
\text{Evidenz}
\rightarrow
D_{n+1}
}
]

Der Prozess kehrt zum Unterschied zurück, aber **nicht zum selben epistemischen Zustand**.

## 9. Wissenschaftliche Statusgrenze

Dieser Text ist eine philosophisch-informatische Synthese und Begriffspräzisierung. Er behauptet insbesondere nicht:

- dass Spencer-Brown QIK-VRT vorweggenommen habe,
- dass Luhmanns Beobachtungstheorie und QIK-VRT identisch seien,
- dass die hier vorgeschlagene Bezeichnung „provenienzgebundene Successor-Rekursion“ ein etablierter Fachterminus sei,
- dass die Interpretation der Paradoxien eine neue Lösung der klassischen logischen Probleme darstelle,
- dass Repository-Persistenz allein wissenschaftliche Wahrheit, Peer Review, empirische Bestätigung oder Konsens etabliere.

Die QIK-VRT-spezifische Terminologie ist hier als expliziter Architektur- und Analysevorschlag ausgewiesen.

## 10. Beitragsprovenienz

Der konzeptionelle Ausgangspunkt „Ontologie des Unterschieds“, die QIK-VRT-Architektur und die Publikationsautorisierung sind Ingolf Lohmann zugeordnet.

Die vorliegende formale und redaktionelle Synthese entstand am 25. September 2026 in Interaktion mit OpenAI ChatGPT (GPT-5.6 Sol). Die maschinelle Ausarbeitung wird dadurch nicht rückwirkend zu einer ausschließlich menschlichen Textleistung. Repository-Review und spätere Änderungen bleiben separat nachvollziehbar.

## Literatur

- George Spencer-Brown, *Laws of Form*, Allen & Unwin, 1969.
- Bertrand Russell, *The Principles of Mathematics*, Cambridge University Press, 1903.
- Bertrand Russell, “Mathematical Logic as Based on the Theory of Types”, *American Journal of Mathematics* 30(3), 1908, 222–262.
- Niklas Luhmann, *Die Gesellschaft der Gesellschaft*, Suhrkamp, 1997.

*q.e.d.*  
**Ingolf Lohmann**

```text
REPOSITORY_CANDIDATE = true
ZENODO_PUBLISHED = false
PEER_REVIEWED = false
INDEPENDENT_EMPIRICAL_CONFIRMATION = false
SCIENTIFIC_CONSENSUS = false
GLOBAL_EFFECT_ACK_DONE = false
```
