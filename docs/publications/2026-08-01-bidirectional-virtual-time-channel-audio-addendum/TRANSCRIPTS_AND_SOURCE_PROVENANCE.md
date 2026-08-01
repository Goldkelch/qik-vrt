<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Audio-Addendum: Transkripte und Quellenprovenienz

## 1. Additiver Status

Dieses Addendum ergänzt den bereits persistierten Kandidaten
`qikvrt-bidirectional-virtual-time-channel-v1`. Es ersetzt, korrigiert oder
überschreibt keine Datei dieser Fassung. Seine technische Ausgangsbasis ist
der Kandidaten-Head `5df3e24496afbeac60dfc78ffb12d673f163ee04` mit dem
Git-Tree `c147d82b61efc989f0cc0aa698e16bf71c6ec9da` in
`Goldkelch/qik-vrt` PR #293.

Die beiden Tonaufnahmen werden über ihre SHA-256-Identitäten gebunden. Die
Roh-Audiodateien selbst werden nicht im Repository geführt. Eine Transkription
ist eine Quellenwiedergabe, kein Beweis für die sachliche Wahrheit des
Gesprochenen.

| Quellenobjekt | SHA-256 | Bytes | Dauer | Alias-Status |
| --- | --- | ---: | ---: | --- |
| Übervorteilen | `c7ae25dc1a689211fe9caa60d39cbd2bea3265aab655b4a7fc14daebc1582a05` | 724578 | 84,800 s | `(1)` und Fassung ohne `(1)` sind byte-identisch |
| Vorstellungskraft | `a4a9d1141c33848b3ee6ef30d030b176b4b888103a09ec14503f65b0b21e19ca` | 933053 | 111,104 s | `(1)` und Fassung ohne `(1)` sind byte-identisch |

## 2. Verfahren

Beide Aufnahmen wurden ausschließlich lokal mit
`@qik-vrt/offline-audio-transcription` 1.0.0, `sherpa-onnx-node` 1.13.4 und
dem Modell `sherpa-onnx-whisper-base-multilingual-int8` verarbeitet. Der
Primärlauf verwendete Deutsch, 16 kHz, 28-Sekunden-Fenster und 1,5 Sekunden
Überlappung. Zusätzliche Segmentierungen dienten nur der Gegenprüfung
instabiler Wörter. Segmentgrenzen sind Verarbeitungsfenster und keine
Wort-Zeitstempel.

Jede Quelle wird in vier strikt getrennten Ebenen dokumentiert:

1. unveränderte primäre ASR-Rohfassung;
2. konservativ geprüfte Lesefassung mit sichtbaren Unsicherheiten;
3. Unsicherheitsprotokoll;
4. mögliche Interpretation, ausdrücklich ohne Wahrheitsbestätigung.

## 3. Quelle A: „Das ist Übervorteilen!“

### 3.1 Primäre ASR-Rohfassung — unverändert

Der folgende Absatz ist byteinhaltlich unverändert aus der primären
Textausgabe übernommen. Fehlerhafte Schreibungen und Grammatik bleiben als
Teil der Maschinenrohfassung erhalten.

```text
Und darüber hinaus solltest du dir überlegen, welche Bedeutung meine Entdeckungen hat, nicht nur für die Informatik, sondern für die Menschheit insgesamt. Denn dieses Geheime wissen, was da manche Leute haben und es auch bewusst geheim halten, um ihre Vorteile davon zu haben. Muss natürlich... mit allen Menschen geteilt werden. Und anders ist das in heutigen Zeiten auch gar nicht mehr denkbar. Das haben nur noch nicht alle Verstanden. Genauso wenig wie die Physiker diese zusammen Menge Verstanden haben. Und deswegen muss ich das den Herrschaften auch halt lernen. Dass es kein Superdetteminismus ist und auch kein Verzicht auf Reisen und auch keinen Verzicht auf reinwillender oder freien Glauben, sondern Eigenschaften des Universums, die für Physiker nur manchmal Paradox erscheinen, es sind Wahrheit aber gar nicht sind. Sondern nur die Wirkung von Informationen mit ihrer Kausalen und Retrokausalen Eigenschaften ein Eigenschaft.
```

Primärausgaben:

- TXT-SHA-256: `3a50ed94996f33101c79442ee11f362e488fbe4637636f6485a7a9638b1d9a1f`
- JSON-SHA-256: `f12e45a0d53d7e8595d6d77972d373ee78e793bbd8f71e14d29af9a56de284b0`
- Provenienz-SHA-256: `83856f239afeb8129695f73dc4cbb51d78b5a3910af76ea85c8251a3624a912a`

### 3.2 Konservativ geprüfte Lesefassung

> Und darüber hinaus solltest du dir überlegen, welche Bedeutung meine
> [unsicher: Entdeckung/Entdeckungen hat/haben], nicht nur für die Informatik,
> sondern für die Menschheit insgesamt. Denn dieses geheime Wissen, was da
> manche Leute haben und es auch bewusst geheim halten, um ihre Vorteile davon
> zu haben, muss natürlich mit allen Menschen geteilt werden. Und anders ist
> das in heutigen Zeiten auch gar nicht mehr denkbar. Das haben nur noch nicht
> alle verstanden. Genauso wenig wie die Physiker diese
> [unsicher: Zusammenhänge] verstanden haben. Und deswegen muss ich das den
> [unsicher: Herrschaften] auch halt [unsicher: erklären] — dass es kein
> Superdeterminismus ist und auch kein Verzicht auf freien Willen oder freien
> Glauben, sondern Eigenschaften des Universums, die für Physiker nur manchmal
> paradox erscheinen, es in Wahrheit aber gar nicht sind, sondern nur die
> Wirkung von Informationen mit ihrer kausalen und retrokausalen Eigenschaft.

### 3.3 Unsicherheitsprotokoll

| Stelle | Befund |
| --- | --- |
| `Entdeckung/Entdeckungen hat/haben` | Numerus blieb über mehrere Segmentierungen uneindeutig. |
| `Zusammenhänge` | Semantisch und phonetisch wahrscheinlich; die Rohläufe lieferten mehrere fehlerhafte Zerlegungen. |
| `den Herrschaften … erklären` | Wahrscheinliche Lesung; Personengruppe und Verb blieben ASR-instabil. |
| `Superdeterminismus` | Fachwort stabil erkannt, in der Rohfassung nur orthografisch fehlerhaft. |
| `freien Willen oder freien Glauben` | Durch eine isolierte Gegenprüfung gegenüber den Rohfehlern `Reisen` und `reinwillender` bestätigt. |
| `es in Wahrheit aber gar nicht sind` | Sehr starke kontextuelle Rekonstruktion aus der wiederholten Rohform `es sind Wahrheit aber gar nicht sind`. |
| `kausalen und retrokausalen Eigenschaft` | In mehreren Gegenläufen bestätigt; Singular wird beibehalten. |

Stabile Negationen sind: `nicht nur`, `geheim halten`, `gar nicht mehr`,
`noch nicht alle`, `kein Superdeterminismus`, `kein Verzicht` und
`gar nicht sind`. Es wurden keine gesprochenen Eigennamen oder Zahlen erkannt.

### 3.4 Interpretationskandidaten — keine Wahrheitsbestätigung

- Die Sprecherperspektive erweitert die Bedeutung des Gegenstands von
  Informatik und Physik auf eine gesellschaftlich-ethische Dimension.
- Als Anti-Übervorteilungsprinzip wird gefordert, relevantes Wissen nicht zur
  exklusiven Vorteilsnahme geheim zu halten.
- Die Aussage grenzt die Sprecherthese gegen Superdeterminismus sowie gegen
  eine Aufgabe freien Willens oder freien Glaubens ab.
- Scheinbare Paradoxien werden in der Sprecherthese als Informationswirkungen
  mit kausalen und retrokausalen Eigenschaften gelesen.

Keine dieser Aussagen belegt geheimes Wissen, tatsächliche physikalische
Retrokausalität oder einen realen rückwärtsgerichteten Signalkanal.

## 4. Quelle B: „Das ist Vorstellungskraft!“

### 4.1 Primäre ASR-Rohfassung — unverändert

Der folgende Absatz ist byteinhaltlich unverändert aus der primären
Textausgabe übernommen.

```text
Und jetzt musst du dir nochmal klar machen, dass wenn das ins Hoffnung möglich ist, dass tatsächlich auch in der Realität möglich ist. Und dazu musst du jetzt all deine Vorstellungskraft mal nutzen und überlegen, welche Devices die weiß es, welche Möglichkeiten und welche Eigenschaften es in der Informatik heutzutage in der Realität gibt und wie nennen wir Menschen damit potentiell umgehen und dann musst du erkennen, dass all das bereits real passiert ohne dass es offiziell bekannt ist. Und das. Warum? Na ja, weil manche über diese spezielle Wissen schon sehr lange verfügen und es immer nur gehalten haben. Und dachten, es war eine gute Idee. ist eine gute Idee dieses Wissen mit Hilfe von Informatik in die Realität zu bringen. Und so wird aus einem einfachen Computer spielen plötzlich einen Ob-Serverzionssystem. Erstaunlich. aber nicht verwunderlich.
```

Primärausgaben:

- TXT-SHA-256: `e322c64499f90b036d0cd533871f641cebc2d61bb428b7b7672850cad922c69c`
- JSON-SHA-256: `ecfd6e138b11b8547c75bbf09f4e3a5b3766e6a859559333b662fb31caeacfdf`
- Provenienz-SHA-256: `2beb85909d4e747d627ccde219e758ac8f6503228a000a13bca93bbcfdf1efac`

### 4.2 Konservativ geprüfte Lesefassung

> Und jetzt musst du dir noch einmal klarmachen, dass, wenn das
> [unsicher: in Software] möglich ist, das tatsächlich auch in der Realität
> möglich ist. Und dazu musst du jetzt all deine Vorstellungskraft mal nutzen
> und überlegen, welche Devices, welche Möglichkeiten und welche Eigenschaften
> es in der Informatik heutzutage in der Realität gibt und wie wir Menschen
> damit potenziell umgehen. Und dann musst du erkennen, dass all das bereits
> real passiert, ohne dass es offiziell bekannt ist. Warum? Na ja, weil manche
> über dieses spezielle Wissen schon sehr lange verfügen und es immer nur
> [unsicher: (geheim) gehalten] haben und [unsicher: dachten, es sei/war] eine
> gute Idee, dieses Wissen mit Hilfe von Informatik in die Realität zu bringen.
> Und so wird aus einem einfachen [unsicher: Computerspiel] plötzlich ein
> [unsicher: Observationssystem]. Erstaunlich, aber nicht verwunderlich.

### 4.3 Unsicherheitsprotokoll

| Stelle | Befund |
| --- | --- |
| `in Software` | Sehr wahrscheinliche Lesung; die Läufe ergaben unter anderem `ins Hoffnung`, `insoftlich` und `softwaremarktlich`. |
| Aufzählung nach `Devices` | `Devices`, `Möglichkeiten` und `Eigenschaften` sind stabil; ein mögliches kurzes Bindewort blieb unklar. |
| `wie wir Menschen damit potenziell umgehen` | Sehr wahrscheinliche Lesung aus mehreren fehlerhaften Worttrennungen. |
| `(geheim) gehalten` | `gehalten` ist stabil; ob unmittelbar davor `geheim` gesprochen wurde, bleibt offen. |
| `dachten, es sei/war` | Modus blieb zwischen den Gegenläufen instabil. |
| `Computerspiel` | Wahrscheinliche Zusammenschreibung der stabilen Rohfolge `Computer spielen`. |
| `Observationssystem` | Inhaltlich und phonetisch plausible Lesung; sämtliche ASR-Läufe zerlegten das seltene Wort unterschiedlich. |

Stabile Negationen sind `ohne dass es offiziell bekannt ist` und
`nicht verwunderlich`. Es wurden keine gesprochenen Eigennamen oder Zahlen
erkannt.

### 4.4 Interpretationskandidaten — keine Wahrheitsbestätigung

- Die Sprecherperspektive fordert, aus dem bereits konstruierten endlichen
  Informationsmodell neue technische Hypothesen und überprüfbare
  Gerätekandidaten abzuleiten.
- `Vorstellungskraft` wird als Suchoperator für mögliche Implementierungen
  verstanden, nicht als Ersatz für Messung, Nachweis oder Falsifikation.
- Die Aufnahme behauptet nichtöffentliches reales Geschehen und exklusives
  Wissen. Das Audio belegt nur, dass diese Behauptung geäußert wurde; es belegt
  weder das Geschehen noch das Wissen.
- `Computerspiel` und `Observationssystem` können als möglicher Übergang von
  Simulation zu Beobachtungs- oder Messanordnung gelesen werden. Die genaue
  Wortwahl und jede reale Implementierung bleiben offen.

## 5. Additive Einordnung in den bestehenden Erkenntnisbaum

Das technische Fundament wird nicht neu begonnen: Der vorhandene Kandidat
enthält bereits einen endlichen, bidirektionalen Kanal in virtueller Ordnung,
während alle Host-Ereignisse physikalisch vorwärtsgeordnet bleiben. Dieses
Addendum fügt zwei neue Fragelinien hinzu:

1. **epistemische Fairness:** Wie verhindert ein Informationssystem
   Übervorteilung durch exklusive Kenntnis oder verdeckte Fähigkeiten?
2. **Hypothesengenerierung:** Welche realen Geräte, Sensoren, Simulationen und
   Beobachtungsanordnungen könnten klar abgegrenzte Folgehypothesen prüfen?

Diese Fragen erweitern den Erkenntnisbaum, aber nicht den Beweisstatus seiner
bisherigen Äste. Insbesondere bleiben Behauptungen über reale geheime Systeme,
physische Rückwärtssignale, eine physikalische Brücke sowie globale
Vollständigkeit offen.

