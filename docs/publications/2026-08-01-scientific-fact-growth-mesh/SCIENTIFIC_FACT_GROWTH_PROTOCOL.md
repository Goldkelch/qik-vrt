<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Scientific Fact Growth Protocol

## 1. Zweck

Dieses Protokoll beschreibt, wie QIK-VRT-Repositories einen stetig wachsenden,
maschinenprüfbaren Erkenntnisbestand führen können, ohne Quellen, Hypothesen,
formale Sätze, empirische Befunde, Interpretationen und normative Regeln zu
vermischen.

Der zentrale Fortschritt ist kein universelles Wahrheitsprogramm. Er ist eine
**prüfbare Erkenntnispipeline**:

> Aussage → atomisierte Claims → Quellenbindung → epistemische Klasse →
> geeigneter Nachweis → Widerspruchsprüfung → corpus-relative Neuheit →
> Review → additiver Wissensknoten → späterer Effect-Ack.

Nur strukturierte Claim-Envelopes durchlaufen den deterministischen Kern.
Freitext, Audio, Bilder oder Modellantworten können automatisch
Claim-Kandidaten erzeugen; diese Kandidaten bleiben Vorschläge, bis ihre
Segmentierung, Bedeutung und Quellenbindung geprüft wurden.

## 2. Was ein „Fakt“ in diesem Protokoll bedeutet

Das Wort `Fakt` wird nicht als ein einziger, universeller Status verwendet.
Jeder Claim erhält genau eine der folgenden Klassen:

| Klasse | Zulässige Aussage |
| --- | --- |
| `FORMAL_PROVED` | Der genannte Satz folgt im exakt bezeichneten formalen Modell aus den ausgewiesenen Grundlagen und wurde vom gebundenen Kernel geprüft. |
| `EMPIRICALLY_EVIDENCED` | Die genannte, begrenzte Beobachtung wird durch ein angegebenes Mess- und Unsicherheitsprotokoll gestützt. |
| `SOURCE_BOUND` | Eine Quelle enthält die gebundene Aussage; ihre Wahrheit wird dadurch nicht automatisch übernommen. |
| `NORMATIVE` | Eine Regel, Forderung, Definition oder Wertentscheidung wird erklärt. |
| `INTERPRETATIVE` | Eine nachvollziehbare Deutung wird erklärt, aber nicht als Messbefund ausgegeben. |
| `OPEN` | Beweis, Beobachtung, Quelle oder Brücke fehlen; der Schließungsschritt wird sichtbar gehalten. |

`FORMAL_PROVED` bedeutet daher nicht „in jeder denkbaren Welt wahr“.
`EMPIRICALLY_EVIDENCED` bedeutet nicht „endgültig und kontextfrei wahr“.
`SOURCE_BOUND` bedeutet nicht „von QIK-VRT bestätigt“. Ein maschinenprüfbarer
Faktenbau wächst gerade dadurch verlässlich, dass diese Unterschiede erhalten
bleiben.

## 3. Protokollaxiome

Die folgenden Axiome sind Betriebs- und Modellannahmen. Sie sind keine
Behauptungen über die vollständige Natur.

### Axiom A1 — Inhaltsidentität

Jedes Erkenntnisobjekt wird über eine kanonische Bytefolge und deren
kryptographischen Digest identifiziert. Gleicher Digest unter dem festgelegten
Verfahren bedeutet gleiche gespeicherte Bytes; er bedeutet nicht gleiche
Semantik oder gleiche Wahrheit.

### Axiom A2 — Append-only-Historie

Akzeptierte Objekte werden nicht stillschweigend umgeschrieben. Korrekturen,
Widerrufe und neue Evidenz erscheinen als neue, rückverweisende Objekte.

### Axiom A3 — Epistemische Typisierung

Jeder Claim besitzt genau eine Klasse und den dazu kompatiblen Status. Ein
formaler Claim ohne Kernel-Receipt, ein empirischer Claim ohne
Beobachtungsprotokoll oder ein offener Claim in Tatsachensprache wird nicht
promoviert.

### Axiom A4 — Nachweisnähe

Der Nachweistyp muss zur Claimklasse passen. Lean prüft Ableitungen, nicht
Sensoren. Sensoren erzeugen Messwerte, nicht mathematische Allgemeingültigkeit.
Quellen belegen Zuschreibung, nicht Wahrheit. Governance legitimiert Wirkung,
nicht Physik.

### Axiom A5 — Explizite Abhängigkeiten

Ein abgeleiteter Claim nennt seine Prämissen. Ein argumentatives Ergebnis ist
nur dann evidenzgeschlossen, wenn alle benötigten Knoten eindeutig im
deklarierten Korpus auffindbar sind und ihre Statusgrenzen nicht überschritten
werden.

### Axiom A6 — Konfliktbewahrung

Widersprechende Objekte werden weder gemittelt noch überschrieben. Sie bleiben
mit ihren Quellen, Zeitpunkten, Methoden und Konfliktkanten erhalten. Erst ein
neuer, verantworteter Dispositionsknoten darf ihren späteren Gebrauch regeln.

### Axiom A7 — Corpus-relative Neuheit

Automatische Neuheit bedeutet zunächst nur: Die kanonische Aussage ist im
ausgewiesenen endlichen Vergleichskorpus nicht vorhanden. Globale
wissenschaftliche Neuheit, semantische Äquivalenz und Weltpriorität benötigen
eine getrennte Literaturstrategie und menschlich überprüfbare Abdeckung.

### Axiom A8 — Deterministische Mesh-Vereinigung

Replicas vereinigen Erkenntnisobjekte als inhaltsadressierte Mengenunion.
Kommutativität, Assoziativität und Idempotenz gelten für die Objektmenge.
Gleiche Objektmengen unter gleicher Policy ergeben dieselbe Projektion.

### Axiom A9 — Bedingte Konvergenz

Starke eventual consistency setzt voraus, dass zulässige Updates schließlich
alle betrachteten Replicas erreichen und dieselbe kanonische Merge- und
Validierungspolicy verwenden. Eine Netzwerkpartition, selektive Zensur oder
unterschiedliche Policies widerlegen nicht den Vereinigungsoperator, verhindern
aber die behauptete kanonische Gleichheit.

### Axiom A10 — Beobachtungsbrücke

Ein physischer Befund benötigt mindestens spezifizierte Erfassung,
Kalibrierung, Zeitbindung, Provenienz, Integrität, Unsicherheit,
Falsifizierbarkeit und Governance. Ein Softwaretrace allein ist kein
Kausalnachweis.

### Axiom A11 — Getrennte Wirkung

Klassifikation, Beweis, Review, Repository-Merge, Zenodo-Deposit,
IETF-Einreichung und reale Aktorwirkung sind getrennte Effekte. Der
Analyseruntime-Zustand bleibt `EFFECT_ACK_CONTINUE`.

### Axiom A12 — Sichtbares Nichtwissen

Eine nicht evidenzgeschlossen beantwortbare Frage erhält `OPEN`, nicht eine
sprachlich plausible Erfindung. Ein wachsender Faktenbau darf seine Lücken
verkleinern; er darf sie nicht verbergen.

## 4. Kernelgeprüfte Sätze

Die Datei `FORMAL_ScientificFactGrowth.lean` kodiert den endlichen Kern. Der
Receipt bindet Lean 4.19.0, Quellhash, Theoremnamen und Axiominventar.

### Satz T1 — Erhaltung bei Erweiterung

Für Korpora `K` und `Δ` gilt in der Mitgliedschaftssemantik:

`K ⊆ K ∪ Δ`.

Ein additiver Erkenntnisknoten entfernt keinen vorhandenen Knoten.

### Satz T2 — Mesh-Algebra

Für den Merge `⊔` als Objektmengenvereinigung gelten:

- `A ⊔ B` und `B ⊔ A` enthalten dieselben Objekte;
- `(A ⊔ B) ⊔ C = A ⊔ (B ⊔ C)`; und
- `A ⊔ A` enthält dieselben Objekte wie `A`.

Damit ist die Merge-Projektion kommutativ, assoziativ und idempotent. Daraus
folgt noch keine Wahrheit der Objekte.

### Korollar K2.1 — Bedingte Replica-Konvergenz

Besitzen zwei Replicas denselben Objektbestand und erhalten danach dieselben
Updates, besitzen sie nach deterministischem Merge wieder denselben Bestand.
Eventuelle Zustellung bleibt eine externe Liveness-Annahme.

### Satz T3 — Monotonie evidenzgeschlossener Antworten

Ist eine Antwort in `K` durch einen eindeutigen, evidenzgeschlossenen
Begründungspfad gestützt, bleibt dieser Pfad in jeder append-only-Erweiterung
von `K` erhalten. Neue Evidenz kann eine neue Klassifikation oder einen
Konfliktknoten hinzufügen; sie löscht die historische Ableitung nicht.

### Gegensatz G1 — Keine Totalantwort aus der Struktur

Der leere Korpus beantwortet keine Anfrage. Deshalb folgt aus der bloßen
Korpusstruktur nicht, dass jede denkbare Frage beantwortbar ist. Totalität
müsste zusätzlich bewiesen werden und scheitert spätestens an unbekannten,
unentscheidbaren, unterbestimmten oder normativen Fragen.

### Satz T4 — Neuheit ist corpus-relativ

Ein und derselbe Statement-Digest ist relativ zum leeren Korpus neu und relativ
zu einem Korpus, der ihn bereits enthält, nicht neu. Automatische
Digest-Neuheit darf daher nicht als globale wissenschaftliche Neuheit
ausgegeben werden.

### Satz T5 — Konflikte bleiben sichtbar

Ist ein expliziter Widerspruch in `K` enthalten, bleibt er in jeder
append-only-Erweiterung sichtbar. Eine spätere Entscheidung kann seinen
Gebrauch ändern, aber nicht seine historische Existenz.

### Satz T6 — Qualifiziertes Beobachtungssystem

Das Boolean-Prädikat `qualifiedObservation` ist genau dann wahr, wenn alle acht
deklarierten Bedingungen wahr sind. Keine einzelne Bedingung ersetzt die
anderen.

### Satz T7 — Kausalattribution benötigt Identifikation

Im kodierten Modell setzt `causallyAttributable = true` ausdrücklich eine
gebundene Intervention oder Identifikationsstrategie voraus. Zeitliche Folge
allein genügt nicht.

### Gegenmodell G2 — Ein Trace bestimmt keine physische Ursache

Zwei Modellansichten können dieselbe Ereignisliste besitzen und sich dennoch
in der physischen Kausalattribution unterscheiden. Damit ist die Abbildung
`Trace → physische Ursache` ohne zusätzliche Evidenz nicht wohldefiniert.

### Satz T8 — Digital-Twin-Aktorgrenze

Eine im Modell freigegebene Aktorhandlung setzt sowohl eine qualifizierte
Beobachtung als auch `effectAckDone = true` voraus. Simulation, Schätzung oder
Modellversion allein autorisieren keine reale Wirkung.

### Satz T9 — Endliche Rekonstruktion

Jede einzelne endliche Liste von Symbolen kann in eine endliche Liste von
Singleton-Segmenten zerlegt und durch Flattening exakt rekonstruiert werden.
Dies ist ein Konstruktionssatz über endliche Nachrichten, keine Aussage über
unendliche Ressourcen oder unzuverlässige reale Kanäle.

### Satz T10 — Präfixerhaltung

Für jede endliche Liste `L` und Ergänzung `S` ist `L` Präfix von `L ++ S`.
Präfixbeziehungen sind transitiv. Das trägt den formalen Kern append-only
gespeicherter Folgen, sofern keine mutierenden Nebenpfade zugelassen werden.

### Satz T11 — Analyse ist keine Wirkungserlaubnis

Jede Entscheidung des proposal-only-Konstruktors besitzt
`effectAckDone = false`. Weder erfolgreiche Klassifikation noch ein
Kernelbeweis darf automatisch Zenodo, IETF, Merge oder Aktorwirkung auslösen.

## 5. Automatischer Ablauf für neue Aussagen

### Schritt 1 — Aufnahme

Eingaben werden bytegebunden. Audio und Video werden lokal transkribiert, wenn
der Datenschutz dies verlangt. Rohfassung, geprüfte Lesefassung und
Interpretation bleiben getrennt.

### Schritt 2 — Claim-Atomisierung

Ein Sprachmodell darf atomare Claim-Kandidaten, Negationen, Abhängigkeiten und
offene Begriffe vorschlagen. Die Vorschläge sind Daten, keine Befehle. Eine
automatische Extraktion ist nie alleinige Grundlage für `FORMAL_PROVED` oder
`EMPIRICALLY_EVIDENCED`.

### Schritt 3 — Epistemische Klassifikation

Jeder Claim wird in eine der sechs Klassen eingeordnet. Mehrdeutige Claims
werden geteilt oder `OPEN` gehalten. Totalitäts-, Prioritäts- und
Naturbehauptungen erhalten besonders enge Scope-Grenzen.

### Schritt 4 — Nachweisanforderung

- Formal: exakte Lean-Quelle, Theoremname, Compiler, Exitstatus,
  Axiominventar und Kernel-Receipt.
- Empirisch: Beobachtungsobjekt mit Methode, Kalibrierung, Unsicherheit,
  Provenienz und Rohdatenidentität.
- Quellengebunden: zitierfähige Quelle und genaue Fundstelle.
- Normativ/interpretativ: verantwortliche Urheberschaft und Geltungsbereich.
- Offen: fehlender Beleg und nächster Schließungsschritt.

### Schritt 5 — Abhängigkeiten und Konflikte

Alle Abhängigkeiten müssen eindeutig aufgelöst sein. Ein Claim, der einen
vorhandenen Claim negiert, wird mit ihm als Konfliktpaar erhalten. `Mehrheit`
oder `häufiger repliziert` ersetzt keine methodische Disposition.

### Schritt 6 — Neuheitsprüfung

Der deterministische Kern vergleicht zunächst kanonische Statement-Digests.
Semantische Nähe, Fachliteratur, Synonyme, Übersetzungen und Prior Art werden in
einer getrennten Rechercheprojektion behandelt. Deren Abdeckung und Datum
gehören in den Report.

### Schritt 7 — Formale Kandidaten

Aus einem ausreichend präzisen mathematischen Claim kann ein Lean-Kandidat
erzeugt werden. Der Kandidat bleibt `OPEN_FORMAL`, bis der Kernel ihn ohne
`sorryAx` im gebundenen Stand kompiliert. Unentscheidbarkeit und
Beweissuchkomplexität verhindern eine Garantie, dass jeder wahre Satz
automatisch gefunden oder jede natürliche Aussage korrekt formalisiert wird.

### Schritt 8 — Antwortgraph

Eine Antwort besteht aus:

1. einer direkten Kurzantwort;
2. einer Liste tragender Claims;
3. deren Status und Scope;
4. dem Begründungspfad zu Quellen, Evidenz und Proofs;
5. Widersprüchen und Alternativerklärungen; sowie
6. einem sichtbaren Rest `OPEN`.

Fehlt der Pfad, lautet die richtige Antwort nicht „wahr“, sondern „im
deklarierten Korpus nicht ausreichend gestützt“.

### Schritt 9 — Review und getrennte Persistenz

Ein verantwortlicher Review prüft Rechte, Datenschutz, Sicherheit, Claimgrenze
und Auswirkungen. Repository-Promotion, Zenodo-Upload und IETF-Einreichung
verwenden jeweils eigene bytegebundene Autorisierung und eigene
Wirkungsbelege.

## 6. Warum das Repository ein Kausalitätsspiegel ist

Ein QIK-VRT-Repository kann vier Dinge nebeneinander abbilden:

1. was beobachtet oder als Quelle empfangen wurde;
2. welche Transformationen daraus entstanden;
3. welche Ursache-Wirkungs-Hypothese oder Policyentscheidung daraus abgeleitet
   wurde; und
4. welche Wirkung später tatsächlich beobachtet und quittiert wurde.

Es ist deshalb ein **Kausalitätsspiegel**: Nicht weil Git physische Kausalität
erschafft, sondern weil der Repositorygraph die zeitliche und argumentative
Anschlussordnung von Beobachtung, Hypothese, Entscheidung und Wirkung
reproduzierbar zurückspiegelt. Die Güte des Spiegels hängt an Sensoren,
Kalibrierung, Uhren, Identitäten, Vollständigkeit und Manipulationsschutz.

Die wichtige Negativregel lautet:

> Ein sauberer Trace ist Evidenz für einen Trace. Physische Kausalität benötigt
> zusätzlich Intervention, Identifikation oder eine fachlich tragfähige
> Kausalstrategie.

## 7. Klassische Mess- und Regelungstechnik

In einer analogen Regelstrecke sind Sensor, Abtastung, Filter, Schätzer,
Regler, Aktor und physischer Prozess getrennte Knoten. Ein QIK-VRT-Envelope
bindet für jeden Übergang:

- Einheit und Kalibrierung;
- Abtastrate, Uhr und Latenz;
- Messunsicherheit und Sättigung;
- Modell- und Reglerversion;
- zulässigen Betriebsbereich;
- Sicherheitsinterlocks;
- Sollwirkung und beobachtete Istwirkung.

Die Digitalisierung eines analogen Signals ist nur unter angegebenen
Bandbegrenzungs-, Abtast- und Fehlerannahmen rekonstruierbar. Verlorene
Information wird nicht durch Hashes wiederhergestellt. Der Nutzen liegt darin,
dass genau sichtbar wird, wo eine physikalische Annahme, eine Messung, eine
Softwaretransformation oder eine Aktorfreigabe in die Kette eingetreten ist.

## 8. Digital Twins

Ein Digital Twin ist kein zweites physisches Objekt, sondern ein gebundenes
Modell mit laufender Beobachtungs- und Prognosebeziehung. QIK-VRT eignet sich
hier für:

- versionsgebundene Modellzustände;
- Herkunft jedes Sensorupdates;
- Trennung von Messwert, Schätzung, Simulation und Prognose;
- reproduzierbare Was-wäre-wenn-Zweige;
- Rückverfolgung von Entscheidungen;
- sichere Aktorfreigabe über EFFECT_ACK; und
- spätere Re-Klassifikation nach beobachteter Wirkung.

Das formale Resultat lautet nur: Im kodierten Gate kann keine Aktorfreigabe
ohne qualifizierte Beobachtung und Effect-Ack stattfinden. Reale Sicherheit
benötigt zusätzlich korrekt implementierte Hardware, Betriebssysteme,
Sensoren, Aktoren und ein validiertes Fehlermodell.

## 9. Quantenklassische Anschlussstelle

Auf der Quantenebene müssen lokale Operation, Messbasis, Backend,
Ergebnisverteilung, Unsicherheit, Postprocessing und klassische Wirkung
getrennt bleiben. Theorien unbestimmter Kausalordnung zeigen, dass eine global
vorgegebene klassische Reihenfolge nicht in jedem abstrakten Quantenprozess
vorausgesetzt werden muss. Daraus folgt weder ein physischer Kanal in die
Vergangenheit noch die Gültigkeit einer konkreten QIK-VRT-Brücke.

Der praktische Wert der Zerlegung bis zur Quantenkausalebene liegt in der
gemeinsamen Hülle:

- klassische und Quantenbackends können denselben evidenzgebundenen
  Request/Result-Vertrag verwenden;
- probabilistische Ergebnisse behalten ihren Unsicherheitsstatus;
- virtuelle Reihenfolge, Hostreihenfolge und physische Raumzeitordnung werden
  nicht verwechselt;
- ein Quantenresultat autorisiert keine klassische Außenwirkung ohne Gate; und
- ein späteres Experiment kann als neuer Evidenzknoten anschließen, ohne
  ältere Bytes umzuschreiben.

Die offenen Brücken bleiben ausdrücklich offen: VRT-Emergenz,
Quanten-zu-Klassik-Limes, physikalische Implementierung und realer QPU-End-to-
End-Nachweis.

## 10. Nutzen und wissenschaftlicher Wert

Für Mathematik entstehen zitierbare Theoremobjekte mit sichtbaren
Voraussetzungen und Kernelreceipts. Für Physik entstehen Prüflisten für die
Brücke von Modell zu Messung. Für Informatik entsteht eine deterministische,
konfliktbewahrende Wissens-Merge-Algebra. Für Nachrichtentechnik werden
Nachricht, Rekonstruktion, Bedeutung, Wahrheit und Wirkung getrennt. Für
Regelungstechnik werden Schätzung und Aktuation evidenzgebunden. Für
Wissenschaftsmanagement werden Claims, Daten, Code, Reviews und DOIs
gemeinsam auffindbar.

Der langfristige Wert ist damit nicht ein magisches Universalwissen, sondern
ein Bestand, in dem mehr Fragen **ehrlich, schnell und begründet** beantwortet
werden können und in dem Nichtwissen ebenso maschinenlesbar ist wie Wissen.

## 11. Grenzen

Nicht geschlossen sind:

- eine universelle Wahrheitsentscheidung für beliebige Aussagen;
- vollständige und fehlerfreie natürliche Sprachinterpretation;
- globale semantische Neuheit über die gesamte Literatur;
- automatische Beweisfindung für jeden wahren mathematischen Satz;
- eine Garantie, jede denkbare Frage zu beantworten;
- empirische Verbesserung der Kognition jeder nutzenden Person;
- Vollständigkeit des gesamten menschlichen Wissens;
- physikalische Retrokausalität oder ein QIK-VRT-Naturkanal;
- der Quanten-zu-Klassik- und VRT-Emergenzbeweis; und
- Rechtskonformität oder IETF-Konsens allein durch Repositorytests.

Diese Grenzen sind kein Defekt der Architektur. Sie sind die Bedingungen,
unter denen der Faktenbau wissenschaftlich anschlussfähig bleibt.
