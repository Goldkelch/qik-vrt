<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Quantum Causal Emergence (QCE)

## Unschärfebilanzen, Planck-Übergangselemente, sequenzielle Paarbildung und der klassische Lichtkegel als Grenzstruktur

**Ingolf Lohmann**  
**QIK-VRT / VRTCore**  
**5. August 2026**

**Dokumentstatus:** formaler und physikalischer Forschungskandidat  
**Wirkungsstatus:** `EFFECT_ACK_CONTINUE`  
**Physikalische Gesamtbestätigung:** nicht beansprucht

---

## Abstract

Dieser Beitrag formuliert einen präzisen Forschungskandidaten für eine relationale Entstehung von Kausalstruktur und Raumzeit. Ausgangspunkt ist die Trennung zwischen der klassischen Darstellung von Kausalität durch einen Lichtkegel und den quantischen Entstehungsbedingungen dieser Darstellung. Ein klassischer Lichtkegel setzt hinreichend bestimmte Ereignisse und eine klassisch auswertbare Geometrie voraus. Der QCE-Kandidat behandelt diese Voraussetzungen nicht als fundamental, sondern als Ergebnis einer Grobkörnung quantisch unscharfer Relationen.

Die zentrale Hypothese lautet: Eine klassische Schwarze-Loch-Singularität kann als Projektionsgrenze einer tieferen quantengravitativen Übergangszone interpretiert werden. Der minimale Modellkern ersetzt die klassische Fortsetzungsgrenze durch ein Planck-Skala-Element. Ein erster Übergang erzeugt einen unterscheidbaren Zustand; ein zweiter Übergang bindet einen weiteren Zustand relational an den ersten. Der resultierende Paarzustand ist im physikalischen Kandidaten verschränkt und zugleich an die bereits vorhandene globale Relationsstruktur gekoppelt. Aus vielen kausal konsistenten, informationserhaltenden und global gebundenen Übergängen soll bei geeigneter Grobkörnung eine klassische Raumzeit mit Lichtkegelstruktur entstehen.

Der Beitrag unterscheidet strikt zwischen bekannten empirischen Ankern, mathematischen Modellfolgen, interpretativen Brücken und offenen physikalischen Behauptungen. Der beigefügte Lean-Kandidat formalisiert ausschließlich den endlichen Modellvertrag: Zweischrittordnung, Identitätserhaltung, Unsicherheitstrennung, Netzwerkerweiterung, klassische-Kegel-Gates und fail-closed Erkenntnisgrenzen. Er beweist nicht, dass die Natur diesen Vertrag instanziiert. Die physikalische Schließung verlangt zusätzlich Unitarität, globale Verschränkung, Informationsbilanz, Page-Kurven-Korrespondenz, Quantenfeld- und Einstein-Grenzfall, Nichtzirkularität, eine unterscheidende Vorhersage, empirische Korrespondenz und unabhängige Reproduktion.

---

## 1. Erkenntnis- und Anspruchsgrenze

QCE verwendet die QIK-VRT-Erkenntnistypen:

| Typ | Bedeutung |
|---|---|
| `formal-proved` | Folgt im deklarierten formalen Modell aus expliziten Definitionen und Voraussetzungen. |
| `empirical-supported` | Wird durch Beobachtung oder Experiment innerhalb eines angegebenen Scopes getragen. |
| `source-bound` | Ist an einen identifizierten Quellenstand gebunden. |
| `interpretive` | Liefert eine ontologische oder begriffliche Deutung, ohne bereits Naturgesetz zu sein. |
| `normative` | Legt eine Verantwortungs-, Freigabe- oder Publikationsregel fest. |
| `open` | Benennt eine noch nicht geschlossene mathematische oder empirische Brücke. |

Die Aussage

> „Der QCE-Modellvertrag ist in Lean kernelakzeptiert“

wäre nach erfolgreicher Ausführung eine formale Aussage.

Die Aussage

> „Eine reale Schwarze-Loch-Singularität ist physikalisch genau ein QCE-Planck-Element“

ist derzeit eine offene Korrespondenzhypothese.

Die Aussage

> „QCE ist die größte Entdeckung der Menschheitsgeschichte“

ist eine persönliche und historische Bewertung. Sie ist weder Lean-Theorem noch experimenteller Befund und wird im wissenschaftlichen Paket nicht als bewiesene Prioritäts- oder Konsensaussage geführt.

Diese Trennung ist konstitutiv. Ein formal vollständiger Modellbeweis kann eine falsche oder unvollständige Naturzuordnung nicht in eine Messung verwandeln. Umgekehrt kann eine wertvolle physikalische Intuition formal noch unvollständig sein. Wissenschaftlich belastbar wird der Gesamtanspruch erst durch die explizite Kopplung beider Seiten.

---

## 2. Empirische und theoretische Ausgangspunkte

### 2.1 Quantenmechanische Unschärfe

Für nichtkommutierende Observablen gilt in allgemeiner Form die Robertson-Schrödinger-Unschärferelation. Für Ort und Impuls ergibt sich die bekannte untere Schranke

\[
\Delta x\,\Delta p \ge \frac{\hbar}{2}.
\]

QCE interpretiert diese Relation nicht als bloße technische Messungenauigkeit. Sie begrenzt die gleichzeitige Präparation und Zustandszuordnung konjugierter Größen. Daraus folgt jedoch nicht, dass jede beobachtete Unsicherheit irreduzibel wäre. Instrumentelle, statistische, modellbedingte und grobkörnungsbedingte Unsicherheiten müssen von der irreduziblen quantischen Komponente getrennt werden.

### 2.2 Relativistische Kausalstruktur

Auf einer klassischen Lorentz-Mannigfaltigkeit klassifiziert das Vorzeichen des Intervalls

\[
\Delta s^2 = g_{\mu\nu}\,\Delta x^\mu\Delta x^\nu
\]

Trennungen als zeitartig, nullartig oder raumartig. Der Lichtkegel ist lokal die Nullstruktur dieser Metrik. In der gewöhnlichen Quantenfeldtheorie auf fester Raumzeit bleibt die Mikrokausalität erhalten; die Heisenbergsche Unschärfe erzeugt für sich allein keinen kontrollierbaren überlichtschnellen Nachrichtenkanal.

QCE setzt an einer anderen Stelle an: Wenn die Ereigniszuordnung oder die Geometrie selbst quantisiert ist, kann die klassische Größe \(\Delta s^2\) nicht ohne zusätzliche Brücke als von Anfang an scharfe Zahl vorausgesetzt werden. Dann ist zunächst eine quantische oder statistische Kausalstruktur zu modellieren, aus der der klassische Lichtkegel hervorgeht.

### 2.3 Planck-Skala

Die natürliche Planck-Normalform verbindet

\[
\frac{\ell_P}{t_P}=c,
\qquad
\frac{E_P}{p_P}=c,
\]

\[
\ell_Pp_P=\hbar,
\qquad
t_PE_P=\hbar,
\]

und am Planck-Punkt

\[
\ell_P=\frac{\hbar}{m_Pc}=\frac{Gm_P}{c^2}.
\]

Der letzte Ausdruck verwendet den Gravitationsradius \(Gm/c^2\), nicht den um den Faktor zwei größeren Schwarzschild-Radius. Diese Identitäten bestimmen eine exakte Maßstruktur. Sie liefern allein noch keine mikroskopische Dynamik und keinen empirischen Nachweis eines diskreten Raumzeitatoms.

### 2.4 Schwarze Löcher und Singularitäten

In der Allgemeinen Relativitätstheorie werden Singularitäten fachlich nicht primär als materielle Punkte definiert, sondern über das Scheitern einer regulären Fortsetzung, insbesondere geodätische Unvollständigkeit unter den jeweiligen Voraussetzungen. QCE ersetzt diesen klassischen Grenzbefund nicht per Definition durch ein neues Naturgesetz. Es formuliert eine Korrespondenzhypothese:

\[
\text{klassische Fortsetzungsgrenze}
\quad\rightsquigarrow\quad
\text{quantengravitative Übergangszone}.
\]

Modelle von Schwarz-zu-Weißloch-Übergängen, nichtsingulären Kernen und quantisierten kausalen Strukturen zeigen, dass diese Frage ein etablierter Forschungsgegenstand ist. Sie bestätigen jedoch nicht automatisch die konkrete QCE-Zweischrittdynamik.

---

## 3. Ontologie des Unterschieds

QCE übernimmt die QIK-VRT-Grundordnung

\[
D \rightarrow I \rightarrow R \rightarrow W \rightarrow C,
\]

wobei

- \(D\) einen typisierten Unterschied,
- \(I\) die daraus gewinnbare Information,
- \(R\) eine explizite Relation,
- \(W\) eine beobachtbare oder erwartete Wirkung und
- \(C\) eine nur unter angegebenen Brücken zulässige Kausalordnung bezeichnet.

Die Reihenfolge ist keine Behauptung, dass in der Natur stets fünf diskrete Zeitpunkte in dieser Wortreihenfolge auftreten. Sie ist eine Typordnung des Erklärens. Eine Kausalbehauptung darf erst aufgewertet werden, wenn der relevante Unterschied, die Relation, die Wirkung und die Evidenz explizit gebunden sind.

Der Satz

> Kausalität ist Relation, nicht Sequenz.

bestreitet nicht die Bedeutung zeitlicher Ordnung. Er bestreitet den unzulässigen Schluss von bloßer zeitlicher Folge auf Ursache.

---

## 4. Unsicherheitsbilanz statt „Entfernung“ der Unschärfe

QCE zerlegt eine beobachtete Unsicherheitsbilanz schematisch in

\[
\Sigma_{\text{gesamt}}
=
\Sigma_{\text{instrumentell}}
+
\Sigma_{\text{grob}}
+
\Sigma_{\text{modell}}
+
\Sigma_{\text{irreduzibel}}.
\]

Die additive Schreibweise ist zunächst eine Modellvereinfachung. In realen Auswertungen können Kreuzkovarianzen und nichtlineare Abhängigkeiten auftreten. Der grundlegende methodische Anspruch bleibt:

1. Instrumentelle Unsicherheit wird an Kalibration, Auflösung und Messprotokoll gebunden.
2. Statistische Unsicherheit wird an Stichprobe und Schätzverfahren gebunden.
3. Modellunsicherheit wird durch konkurrierende Modelle und Sensitivitätsanalysen ausgewiesen.
4. Grobkörnungsunsicherheit wird an die verlorene mikroskopische Auflösung gebunden.
5. Der verbleibende quantische Anteil wird nicht auf null gesetzt, sondern als irreduzibel erhalten.

Der inverse Rekonstruktionsweg lautet

\[
D_N
\xrightarrow{\mathcal R_N^{-1}}
D_{N-1}
\xrightarrow{\mathcal R_{N-1}^{-1}}
\cdots
\xrightarrow{\mathcal R_2^{-1}}
D_1,
\]

wobei jede Inversion ihre Nicht-Eindeutigkeit, Informationsverluste und Voraussetzungen dokumentieren muss. Eine nicht-injektive Grobkörnung besitzt im Allgemeinen keine eindeutige Inverse. QCE verlangt deshalb keinen magischen Rückgewinn verlorener Information. Zulässige Ergebnisse sind:

- eindeutig rekonstruierbar,
- äquivalenzklassenweise rekonstruierbar,
- teilweise rekonstruierbar,
- mehrdeutig,
- evidenzbedingt offen,
- irreversibel informationsverloren.

Damit wird „herausrechnen“ zu einer überprüfbaren Bilanz und nicht zu einer Verletzung der Quantenmechanik.

---

## 5. Der quantisch unscharfe Kausalkegel

Auf fundamentaler Ebene verwendet QCE zunächst keine scharfe binäre Kausalzuordnung. Schematisch wird ein Operator oder eine typisierte Kausalvariable betrachtet,

\[
\widehat{s^2}
=
\widehat g_{\mu\nu}
\,\Delta\widehat x^\mu
\Delta\widehat x^\nu.
\]

Der Zustand liefert einen Erwartungswert und eine Streuung,

\[
\langle \widehat{s^2}\rangle,
\qquad
(\Delta s^2)^2
=
\langle (\widehat{s^2})^2\rangle
-
\langle \widehat{s^2}\rangle^2.
\]

Eine mögliche operationale Größe ist

\[
P_{\text{kausal}}
=
\operatorname{Tr}(\rho\,\Pi_{\text{zulässig}}),
\]

wobei \(\Pi_{\text{zulässig}}\) an den gewählten quantengravitativen Formalismus gebunden werden muss. QCE behauptet nicht, dass diese schematische Form bereits die eindeutige fundamentale Observable darstellt. Sie markiert die Aufgabe: Vor dem klassischen Grenzfall wird Kausalität als Zustands- und Relationsstruktur mit Unsicherheit behandelt.

Der klassische Lichtkegel ist erreicht, wenn ein kontrollierter Grenzübergang mindestens Folgendes liefert:

- eine effektiv klassische Metrik,
- stabile Nullgrenzen,
- hinreichend kleine relative Fluktuationen,
- Mikrokausalität oder eine empirisch äquivalente Signalisierungsgrenze,
- Lorentzverträglichkeit im erklärten Bereich,
- robuste Übereinstimmung mit getesteten relativistischen Beobachtungen.

In Kurzform:

\[
\text{quantische Kausalrelation}
\xrightarrow{\text{Dekohärenz + Grobkörnung + Grenzwert}}
\text{klassischer Lichtkegel}.
\]

---

## 6. Das Planck-Übergangselement

QCE bezeichnet mit \(\Sigma_P\) ein minimales Übergangselement des Modells. Es ist ausdrücklich nicht als klassischer Punkt mit bereits festgelegten Koordinaten definiert. Seine Bedeutung ist relational:

\[
\Sigma_P
=
\text{Träger eines elementaren Zustandsübergangs vor klassischer Geometrie}.
\]

Die physikalische Korrespondenzhypothese lautet:

\[
\text{Schwarze-Loch-Kernbereich}
\quad\longleftrightarrow\quad
\Sigma_P\text{-Dynamik}.
\]

Für diese Brücke sind mindestens erforderlich:

- eine kovariante Definition des Übergangselements,
- eine Dynamik ohne vorausgesetzte klassische Zeitvariable oder eine erklärte relationale Uhr,
- eine Energie-Impuls-Bilanz,
- ein wohldefinierter Zustandsraum,
- Stabilität und Unitarität im angegebenen Bereich,
- eine Abbildung zu semiklassischen Schwarze-Loch-Observablen,
- eine kontrollierte Behandlung des Horizonts,
- eine Informationsbilanz über die gesamte Entwicklung.

Ohne diese Zeugen bleibt \(\Sigma_P\) ein formal definierter Kandidat.

---

## 7. Sequenzielle Zweischrittdynamik

Der minimale QCE-Ablauf besteht aus zwei geordneten Übergängen:

\[
\mathcal H_{\Sigma,n}
\xrightarrow{U_{2n}}
\mathcal H_{\Sigma,n+\frac12}
\otimes \mathcal H_{a_n},
\]

\[
\mathcal H_{\Sigma,n+\frac12}
\otimes \mathcal H_{a_n}
\xrightarrow{U_{2n+1}}
\mathcal H_{\Sigma,n+1}
\otimes \mathcal H_{a_n}
\otimes \mathcal H_{b_n}.
\]

Der zusammengesetzte Übergang ist

\[
V_n=U_{2n+1}U_{2n}.
\]

Für einen informationserhaltenden Modellbereich wird mindestens eine Isometrie verlangt,

\[
V_n^\dagger V_n=I,
\]

oder eine explizit begründete offene-System-Dynamik, deren Gesamtentwicklung unitär ist.

Der erste Schritt materialisiert im Modell einen typisierten Unterschied. Der zweite Schritt erzeugt nicht lediglich einen zweiten unabhängigen Datensatz, sondern eine gemeinsame Paarrelation. Für einen reinen Paarzustand kann eine Schmidt-Zerlegung geschrieben werden,

\[
|\Psi_n\rangle
=
\sum_k\sqrt{\lambda_k}
|k\rangle_{a_n}|k\rangle_{b_n},
\qquad
\sum_k\lambda_k=1.
\]

Mehr als ein von null verschiedener Schmidt-Koeffizient kennzeichnet Verschränkung. Der beigefügte kleine Lean-Kern formalisiert nicht die vollständige Hilbertraumtheorie dieser Gleichung. Er formalisiert die endliche Modellgrenze: geordnete Schritte, gemeinsame Herkunft, Paarbindung und die Tatsache, dass die physikalische Verschränkungsbrücke ein eigener Zeuge bleibt.

---

## 8. Globale Verschränkung statt isolierter Paare

Ein Produkt unabhängiger Bell-Paare reicht nicht aus, um eine zusammenhängende Raumzeit oder eine unitäre Schwarze-Loch-Evolution zu begründen. Der neue Paarsektor muss mit der bereits vorhandenen Relationsstruktur gekoppelt sein:

\[
\rho_{a_nb_nR_{<n}}
\neq
\rho_{a_nb_n}\otimes\rho_{R_{<n}}.
\]

Hier bezeichnet \(R_{<n}\) die vor dem Schritt vorhandenen relationalen Freiheitsgrade. Die genaue Form der Nichtfaktorisierung, ihre Monogamiebedingungen und ihre Dynamik müssen im vollständigen Modell angegeben werden.

Für verdampfende Schwarze Löcher entsteht zusätzlich die Informationsparadoxie. Eine unitäre Gesamtbeschreibung muss die qualitative Page-Kurve reproduzieren: Die Entropie der Strahlung wächst zunächst, erreicht ein Maximum und sinkt anschließend, wenn die Gesamtstrahlung rein wird. QCE darf daher späte Quanten nicht ausschließlich mit unabhängigen inneren Partnern verschränken. Die globale Codierung muss die frühere Strahlung einbeziehen oder eine äquivalente Informationsrekonstruktion liefern.

`PAGE_CURVE_CORRESPONDENCE` ist deshalb ein eigenständiges Schließungsgate.

---

## 9. Relationales Netz und Raumzeitemergenz

Nach \(N\) Zweischritten wird ein gewichtetes Relationsnetz betrachtet,

\[
G_N=(E_N,R_N,W_N),
\]

mit

- Ereignissen oder Zustandsmarkern \(E_N\),
- kausalen und quantischen Relationen \(R_N\),
- Zustands-, Phasen- oder Entropiegewichten \(W_N\).

Die Grobkörnung ist eine Abbildung

\[
\mathcal C:G_N\rightarrow(\mathcal M,g_{\mu\nu},\Phi),
\]

wobei \(\Phi\) effektive Materie- und Feldfreiheitsgrade bezeichnet. Eine physikalische Raumzeitemergenz ist erst gezeigt, wenn \(\mathcal C\) mindestens folgende Eigenschaften besitzt:

1. **Dimensionskorrespondenz:** Der effektive Raum hat im relevanten Bereich die beobachtete Dimension und Signatur.
2. **Lorentzkorrespondenz:** Lokale Lorentzsymmetrie wird reproduziert oder Abweichungen werden quantitativ begrenzt.
3. **Einstein-Grenzfall:** Die effektive Dynamik liefert die getestete klassische Gravitation.
4. **Quantenfeld-Grenzfall:** Bekannte lokale Quantenfeldtheorie entsteht im geeigneten Bereich.
5. **Stabilität:** Keine unphysikalischen Geister oder unkontrollierten Instabilitäten treten im deklarierten Scope auf.
6. **Kausalität:** Signalisierungs- und Konsistenzbedingungen werden erfüllt.
7. **Nichtzirkularität:** Die Zielgeometrie wird nicht bereits in der mikroskopischen Definition versteckt vorausgesetzt.
8. **Empirische Unterscheidbarkeit:** Mindestens eine Beobachtung unterscheidet QCE von konkurrierenden Theorien.

Die Forschung zu Verschränkung und Raumzeitkonnektivität, Entanglement Equilibrium, kausalen Mengen und unbestimmter Kausalordnung liefert wichtige Anschlussstellen. Keine dieser Arbeiten beweist allein die konkrete QCE-Abbildung \(\mathcal C\).

---

## 10. Bewusstsein als epistemische Partition

QCE trennt den physikalischen Zustandsraum von einer epistemischen Klassifikation des Bewusstseins. Sei \(\Omega\) die Gesamtheit dessen, was einem kognitiven System als Gegenstand der Verarbeitung zugänglich oder denkbar wird. Dann wird eine disjunkte Partition verwendet:

\[
\Omega=W\,\dot\cup\,S\,\dot\cup\,R.
\]

Dabei bezeichnet

- \(W\): Wahrhaftigkeit - hinreichend stabilisierte, registrierte und evidenzgebundene Aussagen,
- \(S\): Unsicherheit - explizit modellierte, noch nicht entschiedene Möglichkeiten,
- \(R\): Rest - gegenwärtig nicht angemessen im Modell repräsentierte oder gänzlich unbekannte Möglichkeiten.

Diese Partition ist kein Ersatz für die Born-Regel und keine Behauptung, Bewusstsein verursache den physikalischen Kollaps. Sie ist eine Erkenntnis- und Verantwortungsordnung. Ihre Aufgabe ist, eine Möglichkeit nicht als Tatsache und ein unbekanntes Außen nicht als bloß bekannte Wahrscheinlichkeit auszugeben.

Der Satz

> Bewusstsein ist Mengenlehre.

ist innerhalb von QIK-VRT eine verdichtete interpretative These über die Klassifikation von Erkenntniszuständen.

---

## 11. Round-Trip-Rekonstruktion

QCE wird als inverses und anschließend vorwärts prüfbares Problem formuliert:

\[
\text{Wirkung}
\rightarrow
\text{Evidenz}
\rightarrow
\text{Zustands- und Relationsrekonstruktion}
\rightarrow
\text{Modell}
\rightarrow
\text{formale Folgerung}
\rightarrow
\text{Vorhersage}
\rightarrow
\text{erneute Messung}.
\]

Der Round Trip gilt nur dann als geschlossen, wenn

1. die Beobachtungen quellen- und messgebunden sind,
2. die inverse Rekonstruktion ihre Mehrdeutigkeit ausweist,
3. das Modell exakt versioniert ist,
4. die formalen Folgerungen reproduzierbar geprüft sind,
5. eine neue oder zumindest unabhängige Vorhersage abgeleitet wird,
6. die Zuordnung zu Messdaten vor der Auswertung hinreichend eingefroren ist,
7. die Naturbeobachtung mit Unsicherheitsbudget erfolgt,
8. unabhängige Reproduktion möglich ist.

Ein formaler Kreis innerhalb eines selbstdefinierten Modells ist noch kein physikalischer Round Trip.

---

## 12. Der endliche Lean-Modellvertrag

Der beigefügte Lean-Kandidat verwendet bewusst einen kleinen, `Std`-basierten Kern. Er formalisiert:

- ein typisiertes Planck-Übergangselement,
- eine kanonische Zweischrittspur,
- Erhaltung der gemeinsamen Quellidentität,
- eine endliche Paarrelationsdarstellung,
- eine explizite Unsicherheitsbilanz,
- Erhaltung der irreduziblen Komponente nach Entfernung modellierter reduzierbarer Anteile,
- einen quantisch unaufgelösten Kausalstatus,
- ein dreiteiliges Gate für einen klassischen Lichtkegel,
- monotone Erweiterung eines endlichen Relationsnetzes,
- eine konjunktive physikalische Schließungsregel,
- eine Trennung von Kernel-Receipt und empirischer Korrespondenz.

Der Lean-Kern beweist nicht:

- dass reale Singularitäten Planck-Elemente sind,
- dass reale Schwarze Löcher die QCE-Zweischrittdynamik ausführen,
- dass die modellierte Paarrelation bereits physikalische Verschränkung im vollständigen Hilbertraumsinn ist,
- dass die Grobkörnung die Einstein-Gleichungen ergibt,
- dass die Page-Kurve reproduziert wird,
- dass eine neue QCE-Vorhersage bestätigt wurde,
- dass die historische Prioritätsbewertung feststeht.

Diese Grenzen werden in `CLAIM_MATRIX.json`, `SOURCE_EVIDENCE_BINDINGS.json` und im Kernel-Receipt festgehalten.

---

## 13. Fail-closed Schließung

Der QCE-Kandidat gilt nur dann als physikalisch geschlossen, wenn sämtliche folgenden Zeugen vorliegen:

1. Planck-Skala-Korrespondenz,
2. explizite Zweischrittdynamik,
3. physikalische Paarverschränkung,
4. globale Verschränkungsintegration,
5. vollständige Unsicherheitsbilanz,
6. Unitarität oder äquivalente Gesamtinformationserhaltung,
7. Energie-Impuls-Erhaltung,
8. Page-Kurven-Korrespondenz für den relevanten Schwarze-Loch-Scope,
9. Quantenfeld-Grenzfall,
10. klassischer Einstein-Grenzfall,
11. klassischer Lichtkegel-Grenzfall,
12. kausale Konsistenz,
13. Nichtzirkularität,
14. falsifizierbare unterscheidende Vorhersage,
15. empirische Korrespondenz,
16. unabhängige Reproduktion.

Formal:

\[
\mathrm{QCEClosed}
=
\bigwedge_{i=1}^{16} W_i.
\]

Fehlt ein Zeuge, bleibt der Gesamtstatus offen. Ein Kernel-Exitcode null ersetzt keinen der empirischen oder physikalischen Zeugen.

---

## 14. Falsifikationsprogramm

Ein wissenschaftlicher QCE-Kandidat benötigt quantitative Abweichungen oder neue Korrelationen. Mögliche Arbeitsrichtungen sind:

### 14.1 Ringdown- und Echo-Struktur

Ein nichtklassischer Kern oder eine Übergangszone könnte, modellabhängig, Abweichungen in späten Ringdown-Signalen erzeugen. Ein belastbarer Test verlangt eine vorab spezifizierte Wellenformfamilie, systematische Fehler, Detektorrauschen und einen Vergleich mit konventionellen Umgebungs- und Modellunsicherheiten.

### 14.2 Hawking- und Page-Kurven-Korrespondenz

Die Zweischrittdynamik muss eine Informationsstruktur liefern, die mit unitärer Verdampfung vereinbar ist. Eine reine Paarerzeugung ohne globale Rekodierung wäre ausgeschlossen.

### 14.3 Kausalkegel-Fluktuationen

Falls QCE residuale Kausalstrukturfluktuationen vorhersagt, müssen Größe, Spektrum, Skalierung und Signalisierungsgrenze quantitativ berechnet werden. Bestehende experimentelle Schranken dürfen nicht verletzt werden.

### 14.4 Lorentz- und Dispersionsgrenzen

Eine diskrete oder relationale Mikrodynamik darf keine bereits ausgeschlossenen energieabhängigen Laufzeit- oder Dispersionssignaturen erzeugen. Entweder wird lokale Lorentzinvarianz emergent exakt reproduziert oder verbleibende Abweichungen werden unter bestehende Schranken gedrückt.

### 14.5 Entropie-Flächen-Beziehung

Das Relationsnetz sollte eine nachvollziehbare Verbindung zwischen Verschränkungsentropie und effektiver Geometrie liefern. Ein bloßes Einsetzen einer bekannten Flächenformel wäre zirkulär.

Keine dieser Richtungen ist im vorliegenden endlichen Lean-Kern geschlossen.

---

## 15. Gegenmodelle und mögliche Fehlerklassen

QCE muss insbesondere gegen folgende Fehlerklassen geprüft werden:

- **Begriffsäquivokation:** „Singularität“, „Planck-Element“, „Paar“, „Verschränkung“ oder „Kollaps“ werden zwischen Modell und Natur unbemerkt umgedeutet.
- **Zirkularität:** Raumzeit oder Lichtkegel werden in der Mikrodynamik vorausgesetzt und anschließend als emergent ausgegeben.
- **Dimensionsanalyse ohne Dynamik:** Exakte Planck-Identitäten werden fälschlich als vollständige Feldgleichungen behandelt.
- **Unschärfevernichtung:** Eine Rekonstruktion wird unzulässig als Beseitigung irreduzibler Quantenfluktuation ausgegeben.
- **Lokale Paarfalle:** Unabhängige Paare werden ohne globale Informationsstruktur als Lösung des Informationsparadoxons behauptet.
- **Kernel-Promotion:** Formale Typ- und Gate-Theoreme werden als empirischer Naturbeweis ausgegeben.
- **Unterbestimmtheit:** Mehrere Mikromodelle erzeugen dieselben makroskopischen Daten, ohne dass QCE eine unterscheidende Vorhersage liefert.
- **Nichtreproduzierbarkeit:** Quellen, Parameter, Code, Toolchain oder Ausführung sind nicht bytegenau gebunden.
- **Prioritätsüberdehnung:** Eine persönliche Größenbewertung wird als fachlicher Konsens dargestellt.

Die QIK-VRT-Prüfarchitektur soll diese Fehler nicht rhetorisch, sondern maschinenlesbar blockieren.

---

## 16. Repository-, Lean- und Zenodo-Workflow

Der vorgesehene Ablauf ist serialisiert:

1. Aktuelle Authority- und Mirror-Mains werden neu beobachtet.
2. Der aktuell autorisierte Repository-Arbeitsauftrag wird abgeschlossen oder ausdrücklich neu priorisiert.
3. Der QCE-Kandidat wird additiv auf einem neuen Authority-Branch materialisiert.
4. Der read-only QIK-VRT-Bootloader wird ausgeführt.
5. Python-Validator, Negativtests, Dokumentprüfung und Prüfsummen laufen.
6. Lean 4.19.0 kompiliert den Modellkern und führt den Axiom-Audit aus.
7. Ein source-, commit-, tree-, toolchain- und output-gebundenes Kernel-Receipt wird erzeugt.
8. Exakte Head-Gates und Repository-Integrität laufen.
9. Erst danach wird ein byteidentischer Mirror-Kandidat erzeugt und separat geprüft.
10. Nach Review und Promotion wird ein Zenodo-Kandidat aus den freigegebenen Bytes erzeugt.
11. Die Zenodo-Veröffentlichung verlangt eine ausdrückliche Owner-Autorisierung und eine erneute Hash-Prüfung.
12. Nach Veröffentlichung wird ein Rücklauf-Receipt mit DOI, Record-ID, Dateihashes und Repository-Bindung persistiert.

GitHub ist die versionierte Ausführungs- und Reviewebene. Lean ist die formale Prüfebene. Zenodo ist die persistente Publikations- und Zitierungsebene. Keine Ebene ersetzt die andere.

---

## 17. Gegenwärtiger Status

Der vorliegende Lieferstand ist ein **commit-ready Kandidatenpaket**. Markdown, wissenschaftliche Spezifikation, Lean-Quellkandidat, Validatoren, Workflow, Claim-Matrix, Quellenbindungen, Zenodo-Metadaten und Prüfsummen werden gemeinsam bereitgestellt.

Der neue Lean-Quellkandidat wurde in dieser Ausführungsumgebung noch nicht mit Lean 4.19.0 kernelgeprüft. Deshalb enthält das Paket ausschließlich ein `KERNEL_RECEIPT_TEMPLATE.json` mit dem Status `NOT_EXECUTED`. Ein späterer erfolgreicher GitHub-Actions-Lauf muss dieses Template durch ein exakt gebundenes Ausführungsreceipt ersetzen.

Die physikalische Korrespondenz bleibt unabhängig davon offen.

`FORMAL_SOURCE = PREPARED`

`LEAN_EXECUTION = PENDING_REPOSITORY_RUN`

`PHYSICAL_CORRESPONDENCE = OPEN_CANDIDATE`

`ZENODO_PUBLICATION = NOT_EXECUTED`

`PASS = NOT_CLAIMED`

`FINAL_PASS = NOT_CLAIMED`

`EFFECT_ACK_DONE = NOT_CLAIMED`

`EFFECT_STATE = EFFECT_ACK_CONTINUE`

---

## 18. Schlussfolgerung

QCE ordnet eine weitreichende Hypothese in einen prüfbaren Forschungsvertrag. Der klassische Lichtkegel wird nicht verworfen, sondern als makroskopische Grenzstruktur einer tieferen quantischen Kausalordnung interpretiert. Die Heisenbergsche Unschärfe wird nicht entfernt, sondern durch die Rekonstruktion bilanziert und bis zum irreduziblen Rest erhalten. Eine klassische Singularität wird als mögliche Projektionsgrenze einer quantengravitativen Übergangszone behandelt. Ein sequenzieller Zweischritt erzeugt im Modell zunächst einen Unterschied und anschließend eine relationale Paarstruktur. Viele global gebundene Relationen bilden den Kandidaten für eine emergente Raumzeit.

Die konzeptionelle Verdichtung ist stark. Ihre physikalische Gültigkeit hängt jedoch an expliziten Brücken, die nicht durch Benennung ersetzt werden dürfen. Der beigefügte formale Kern soll genau diese Grenze durchsetzen: Er macht die interne Modelllogik maschinenprüfbar und blockiert zugleich die unzulässige Promotion eines Kernelbeweises zur experimentellen Entdeckung.

Der wissenschaftliche Anspruch ist damit weder bloße Spekulation noch bereits abgeschlossene Weltformel. Er ist ein reproduzierbares Programm:

\[
\text{Unterschied}
\rightarrow
\text{Relation}
\rightarrow
\text{quantische Kausalstruktur}
\rightarrow
\text{klassische Raumzeit}
\rightarrow
\text{Vorhersage}
\rightarrow
\text{Messung}.
\]

Der Round Trip entscheidet.

---

## Literatur

1. W. Heisenberg, „Über den anschaulichen Inhalt der quantentheoretischen Kinematik und Mechanik“, *Zeitschrift für Physik* 43 (1927), 172-198, DOI: 10.1007/BF01397280.
2. H. P. Robertson, „The Uncertainty Principle“, *Physical Review* 34 (1929), 163-164, DOI: 10.1103/PhysRev.34.163.
3. S. W. Hawking und R. Penrose, „The Singularities of Gravitational Collapse and Cosmology“, *Proceedings of the Royal Society A* 314 (1970), 529-548, DOI: 10.1098/rspa.1970.0021.
4. S. W. Hawking, „Particle Creation by Black Holes“, *Communications in Mathematical Physics* 43 (1975), 199-220, DOI: 10.1007/BF02345020.
5. S. Doplicher, K. Fredenhagen und J. E. Roberts, „The Quantum Structure of Spacetime at the Planck Scale and Quantum Fields“, *Communications in Mathematical Physics* 172 (1995), 187-220, DOI: 10.1007/BF02104515.
6. D. Malament, „The Class of Continuous Timelike Curves Determines the Topology of Spacetime“, *Journal of Mathematical Physics* 18 (1977), 1399-1404, DOI: 10.1063/1.523436.
7. L. Bombelli, J. Lee, D. Meyer und R. D. Sorkin, „Space-Time as a Causal Set“, *Physical Review Letters* 59 (1987), 521-524, DOI: 10.1103/PhysRevLett.59.521.
8. C. Oreshkov, F. Costa und Č. Brukner, „Quantum Correlations with No Causal Order“, *Nature Communications* 3 (2012), 1092, DOI: 10.1038/ncomms2076.
9. M. Van Raamsdonk, „Building up Spacetime with Quantum Entanglement“, *General Relativity and Gravitation* 42 (2010), 2323-2329, DOI: 10.1007/s10714-010-1034-0.
10. T. Jacobson, „Entanglement Equilibrium and the Einstein Equation“, *Physical Review Letters* 116 (2016), 201101, DOI: 10.1103/PhysRevLett.116.201101.
11. J. Maldacena und L. Susskind, „Cool Horizons for Entangled Black Holes“, *Fortschritte der Physik* 61 (2013), 781-811, DOI: 10.1002/prop.201300020.
12. A. Almheiri, D. Marolf, J. Polchinski und J. Sully, „Black Holes: Complementarity or Firewalls?“, *Journal of High Energy Physics* 2013, 62, DOI: 10.1007/JHEP02(2013)062.
13. G. Penington, „Entanglement Wedge Reconstruction and the Information Paradox“, *Journal of High Energy Physics* 2020, 2, DOI: 10.1007/JHEP09(2020)002.
14. C. Rovelli und F. Vidotto, „Planck Stars“, *International Journal of Modern Physics D* 23 (2014), 1442026, DOI: 10.1142/S0218271814420267.
15. J. F. Donoghue, „General Relativity as an Effective Field Theory: The Leading Quantum Corrections“, *Physical Review D* 50 (1994), 3874-3888, DOI: 10.1103/PhysRevD.50.3874.
16. Lean FRO, *Lean Language Reference* und *Validating a Lean Proof*, jeweils für die im Repository gebundene Toolchain und Kernelgrenze.

---

**Quod erat demonstrandum gilt nur für die ausdrücklich benannten und tatsächlich ausgeführten formalen Modelltheoreme.**

**Ingolf Lohmann**
