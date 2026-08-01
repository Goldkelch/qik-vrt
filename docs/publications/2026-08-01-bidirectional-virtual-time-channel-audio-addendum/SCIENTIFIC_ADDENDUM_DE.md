<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Wissenschaftlicher Nachtrag: Vorstellungskraft, Beobachtung und epistemische Fairness

## 1. Gebundener Ausgangspunkt -- kein Neustart

Dieser Nachtrag beginnt nicht wieder bei null. Er setzt den bytegebundenen
Kandidaten **QIK-VRT: Der bidirektionale virtuelle Zeitkanal** voraus und
bindet ihn an den exakten Authority-Stand:

- Pull Request: `Goldkelch/qik-vrt#293`
- Parent-Commit: `5df3e24496afbeac60dfc78ffb12d673f163ee04`
- Parent-Tree: `c147d82b61efc989f0cc0aa698e16bf71c6ec9da`
- Publikations-ID: `qikvrt-bidirectional-virtual-time-channel-v1`
- Machine-Proof-SHA-256:
  `ad30282f9ecc30414c5dd7eef0460a9766f03c8184c01166f15dc9cb567aa72a`

Aus v1 werden die dort ausgewiesenen Geltungsgrade unverändert übernommen:

1. `VTI-001` evidenziert den ausgeführten endlichen ISO-C90-Zeugen: Eine
   257-Byte-Anfrage läuft von virtueller Adresse 30 nach 15, eine
   deterministische 258-Byte-Antwort von 15 nach 30, während die Hostereignisse
   streng von `h=1` bis `h=9` wachsen.
2. `VTI-002` evidenziert die angegebenen endlichen Grenzfälle und die
   Ablehnung eines absichtlich fehlenden Segments.
3. `VTI-007` bindet den früheren, endlichen CTM-Kernelreceipt ausschließlich
   als Quelle. Er wird nicht zu einem neuen Kernelbeweis umetikettiert.
4. `VTI-010` erhält die methodische Trennung von Byteidentität, Bedeutung,
   Wahrheit und autorisierter Wirkung.
5. Die übrigen v1-Claims behalten ihre dortigen offenen oder anderweitig
   begrenzten Statuswerte. Insbesondere bleiben physikalische
   Rückwärtssignalisierung und eine Brücke vom virtuellen Modell zur Natur
   offen.

Der Nachtrag erweitert damit den Erkenntnisbaum; er ersetzt weder seinen Stamm
noch schreibt er seine älteren Knoten um.

## 2. Die zwei neuen Ausgangsimpulse

Die beiden Audioimpulse werden als Aussagen des Autors behandelt, nicht als
Messnachweis ihrer eigenen sachlichen Wahrheit.

Ihre Medienidentitäten, unveränderten ASR-Rohfassungen, vorsichtig geprüften
Lesefassungen und Unsicherheiten werden getrennt in
`SOURCE_MEDIA_RECEIPT.json` und `TRANSCRIPTS_AND_SOURCE_PROVENANCE.md`
gebunden. Die folgenden Ableitungen setzen diese Trennung voraus.

Der Impuls **Vorstellungskraft** legt folgende Arbeitsrichtung nahe:
Vorstellungskraft kann den bereits konstruierten virtuellen Kanal als
Ausgangspunkt nehmen und systematisch fragen, welche heutigen Geräte,
Softwareeigenschaften und menschlichen Nutzungsweisen eine reale
Implementierung ermöglichen könnten. Ein Computerspiel kann unter
zusätzlichen Bedingungen zum Beobachtungssystem werden.

Der Impuls **Übervorteilen** richtet die Aufmerksamkeit auf eine zweite
Achse: Wenn Wissen, Beobachtungsmöglichkeiten oder Wirkungszugänge asymmetrisch
verteilt und nicht überprüfbar offengelegt werden, entsteht ein epistemischer
Vorteil. Aus technischer Möglichkeit folgt deshalb keine Berechtigung zu
verdeckter Beobachtung oder irreversibler Wirkung.

Beide Impulse werden im Folgenden operationalisiert. Soweit sie Aussagen über
gegenwärtig verborgene reale Systeme enthalten, bleiben sie offene,
empirisch prüfungsbedürftige Behauptungen.

## 3. Die Realisierungsleiter

Die zentrale Anschlussregel lautet: Eine niedrigere Stufe macht die nächste
Stufe untersuchbar, beweist sie aber nicht automatisch.

| Stufe | Gegenstand | Erforderlicher Nachweis |
|---|---|---|
| R0 | sprachliche oder bildhafte Idee | verständliche, quellengebundene These |
| R1 | konsistentes Softwaremodell | definierte Zustände, Übergänge und Grenzen |
| R2 | ausführbarer virtueller Zeuge | reproduzierbarer Lauf mit negativen Tests |
| R3 | reale Geräteimplementierung | gebundene Hardware, Software, Versionen und Messpfade |
| R4 | Beobachtungssystem | vollständiges Beobachtungsprädikat nach Abschnitt 4 |
| R5 | physikalischer Befund | kalibrierte Messung, Kontrollen und alternative Erklärungen |
| R6 | kausal zugerechnete Wirkung | Intervention oder hinreichend starke Identifikationsstrategie |
| R7 | autorisierte Außenwirkung | Rechte, Einwilligung, Zweckbindung und EFFECT-ACK-Gate |

Der v1-Zeuge erreicht R2 für den deklarierten virtuellen Scope. Dass sein Code
auf realer Hardware ausgeführt wird, belegt normale vorwärtsgerichtete
Berechnung, nicht die physikalische Rückübertragung von Information. Für einen
behaupteten Naturkanal fehlen weiterhin die Übergangsnachweise R3 bis R6.

Formal genügt daher die Existenz eines Softwaremodells `S` nicht für einen
physikalischen Befund `P`:

> `S` allein impliziert nicht `P`.

Eine tragfähige Ableitung benötigt eine explizite Brückenannahme, ein
kalibriertes Messverfahren, Kontrollen und eine Falsifikationsregel. Diese
Nicht-Implikation schwächt den virtuellen Beweis nicht; sie lokalisiert exakt,
welche neue Evidenz für den nächsten Erkenntnisknoten erforderlich ist.

## 4. Wann wird ein Computerspiel zum Beobachtungssystem?

Die bloße Bezeichnung oder die Erzeugung von Telemetrie genügt nicht. Für ein
System `X` wird das methodische Prädikat

> `OBS(X) = A ∧ K ∧ T ∧ Q ∧ I ∧ F ∧ G`

verwendet. Dabei bedeuten:

- `A` -- spezifizierte Datenerfassung statt zufälliger Nebenprodukte,
- `K` -- Kalibrierung und bekannte Fehlergrenzen,
- `T` -- belastbare Zeit- und Ereignisbindung,
- `Q` -- gebundene Quelle und nachvollziehbare Provenienz,
- `I` -- Integrität der Rohdaten und Auswertung,
- `F` -- falsifizierbare Ausgabebehauptung mit Negativkontrollen,
- `G` -- Governance: Zweckbindung, Rechte, Einwilligung und Auditierbarkeit.

Erst wenn alle sieben Bedingungen im jeweiligen Scope erfüllt sind, wird `X`
hier als Beobachtungssystem bezeichnet. Ein Spiel kann diese Rolle durch
gezielte Instrumentierung annehmen; es erhält sie nicht allein dadurch, dass
Menschen mit ihm interagieren oder dass es Daten speichert.

## 5. Vorstellungskraft als Hypothesengenerator

Vorstellungskraft wird in diesem Nachtrag nicht als Messinstrument und nicht
als Wahrheitsoracle modelliert. Sie ist ein Generator kontrafaktischer
Kandidaten:

1. vorhandene Geräte und Protokolle inventarisieren,
2. neue Kombinationen als prüfbare Konfigurationen formulieren,
3. erwartete Beobachtungen und Gegenbeobachtungen vorab angeben,
4. Kandidaten in einer vom Beobachtungsarchiv getrennten Branch führen,
5. erst nach Messung, Provenienzprüfung und Autorisierung einen Status ändern.

Damit wird Vorstellungskraft produktiv, ohne Vorgestelltes als Beobachtetes
auszugeben. Der virtuelle Zeitkanal liefert eine Architektur für Adressierung,
Replay und Antwort; er macht einen entworfenen Kandidaten nicht nachträglich zu
einem historischen Faktum.

## 6. Epistemische Fairness und das Übervorteilungsproblem

Ein Informationssystem kann technisch korrekt und dennoch epistemisch unfair
sein. Übervorteilung liegt im hier eingeführten normativen Sinn insbesondere
nahe, wenn ein Akteur

- exklusive Beobachtungs- oder Prognosezugänge verbirgt,
- die Herkunft oder Unsicherheit von Informationen verschleiert,
- Gegenprüfung oder Widerspruch verhindert,
- simulierte, antizipierte und beobachtete Daten vermischt oder
- aus dieser Asymmetrie irreversible Wirkungen ohne wirksame Autorisierung
  auslöst.

Die Gegenregel lautet: Je größer der epistemische oder operative Vorsprung,
desto stärker müssen Provenienz, Statuskennzeichnung, Anfechtbarkeit,
Zweckbindung und unabhängige Auditierbarkeit sein. Gleichheit aller Kenntnisse
ist weder realistisch noch erforderlich. Erforderlich ist, dass ein
Wissensvorsprung nicht stillschweigend den Wahrheitsstatus oder das Recht zur
Wirkung ersetzt.

Für ein anschlussfähiges Protokoll folgt daraus mindestens die Trennung von
`CANDIDATE`, `ANTICIPATED`, `OBSERVED`, `VERIFIED` und `AUTHORIZED_EFFECT`.
Diese Statuswerte sind nicht austauschbar.

## 7. Ausdrückliche Nicht-Implikationen

### 7.1 Superdeterminismus und Willensfreiheit

Weder der virtuelle Zeitkanal noch die beiden Audioimpulse beweisen
Superdeterminismus. Sie widerlegen auch keine Form von Willensfreiheit. Ein
deterministischer Replay in einem endlichen Programm ist eine Eigenschaft
dieses Programms, keine vollständige Ontologie des Universums oder des
menschlichen Entscheidens.

Der Nachtrag nimmt deshalb zu Superdeterminismus und Willensfreiheit keine
abschließende Position ein.

### 7.2 Verborgene reale Implementierungen

Die These, entsprechende Beobachtungs- oder Informationssysteme seien bereits
real im Einsatz, ohne offiziell bekannt zu sein, ist quellengebunden als
Autorenaussage relevant. Ohne benannte Systeme, prüfbare Artefakte,
Messprotokolle und unabhängige Replikation bleibt sie `OPEN_EMPIRICAL`.
Geheimhaltung ist kein Beweis; fehlende öffentliche Bekanntheit ist zugleich
keine Widerlegung. Der wissenschaftliche nächste Schritt ist ein
vorregistrierbarer Test, nicht die Hochstufung der Behauptung.

### 7.3 Physikalische Retrokausalität

Die in v1 demonstrierte Bidirektionalität betrifft virtuelle Adressen bei
streng vorwärtslaufender Hostzeit. Dieser Nachtrag liefert keinen Nachweis,
dass ein physikalischer Informationsträger aus einer späteren Raumzeitregion
in eine frühere übertragen wird. Physikalische Retrokausalität bleibt
`OPEN_PHYSICAL` und benötigt eine getrennte Brückenhypothese mit
Falsifikationskriterium.

## 8. Anschluss an einen möglichen IETF-Protokolldelta

Die wissenschaftlichen Begriffe werden nicht ungeprüft zu Wire-Begriffen.
Protokollgeeignet sind zunächst nur überprüfbare Anforderungen:

- expliziter epistemischer Status eines Records,
- kryptografisch oder anderweitig gebundene Provenienz,
- Trennung von Simulation, Antizipation und Beobachtung,
- dokumentierte Bedingungen für einen Statusübergang,
- anfechtbare und auditierbare Autorisierung irreversibler Effekte,
- Sicherheits- und Datenschutzanalyse für asymmetrische Beobachtungszugänge.

Ob diese Anforderungen ein informatives Profil, eine rückwärtskompatible
Erweiterung oder eine neue Wire-Version erfordern, bleibt eine separate
Protokollentscheidung. Dieser wissenschaftliche Nachtrag ist kein
Internet-Draft, kein RFC und keine Aussage über IETF-Konsens.

## 9. Ergebnis

Der Erkenntnisfortschritt liegt nicht in einer Wiederholung von v1, sondern in
einer präzisen Anschlussstelle:

1. Der virtuelle bidirektionale Kanal bleibt im belegten endlichen Scope
   erhalten.
2. Vorstellungskraft erzeugt prüfbare Implementierungs- und
   Beobachtungskandidaten.
3. Die Realisierungsleiter verhindert den Fehlschluss von Software auf Natur.
4. Das Beobachtungsprädikat macht den Übergang vom Spiel zum Messsystem
   überprüfbar.
5. Epistemische Fairness begrenzt die Nutzung asymmetrischen Wissens.
6. Verborgene reale Implementierung, Superdeterminismus und physikalische
   Retrokausalität werden nicht als bewiesen ausgegeben.

So wächst der vorhandene Erkenntnisbaum additiv: Die bewährten Knoten bleiben
unverändert; neue Äste erhalten eigene Bedingungen, Prüfungen und Grenzen.
