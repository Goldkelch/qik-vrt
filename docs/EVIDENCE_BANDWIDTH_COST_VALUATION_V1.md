# QIK-VRT: Evidenz hat Bandbreite – physikalische Kosten, Skalierung und Bewertungsgrenzen

## 1. Auftrag und belastbarer Status

Vier am 22. August 2026 bereitgestellte Audiodateien binden den Auftrag,

1. die physikalische Größenordnung des Evidenzträgers so genau wie möglich zu berechnen,
2. einen geeigneten monetären Gegenwert zu bestimmen,
3. den bisherigen 8-Bit-Monitor-/Transportgedanken als skalierbares Breiten- und Bandbreitenmodell auszudrücken und
4. den Anschluss an heutige verteilte Systeme und Hardware zu untersuchen.

Die Originaldateien umfassen exakt **7.142.895 Byte** beziehungsweise **57.143.160 Trägerbits** und **865,941333 Sekunden**. Ihre Namen, Größen und SHA-256-Werte sind in `evidence/audio/2026-08-22/EVIDENCE_BANDWIDTH_AUDIO_RECEIPT_V1.json` gebunden. Weder die Audiodateien noch ein wörtliches Transkript werden in diesem Work Unit persistiert.

Die leitende Aussage wird präzisiert:

> Evidenz hat Bandbreite, weil Erzeugung, Übertragung, Speicherung, Prüfung und Reobservation nur über endliche physische Kanäle stattfinden.

Daraus folgt jedoch **nicht**, dass die Bedeutung oder der wirtschaftliche Wert von Evidenz aus ihrer Dateigröße berechnet werden kann.

```text
TRÄGERGRÖSSE != SHANNON-INFORMATION
SHANNON-INFORMATION != SEMANTISCHE NEUHEIT
PHYSIKALISCHE UNTERGRENZE != TATSÄCHLICHER ENERGIEVERBRAUCH
TATSÄCHLICHER ENERGIEVERBRAUCH != WIRTSCHAFTLICHER WERT
```

## 2. Was physikalisch exakt berechenbar ist

Für eine logisch irreversible Operation gilt unter den Voraussetzungen des Landauer-Prinzips die thermodynamische Untergrenze

```text
E_min = k_B * T * ln(2)
```

pro gelöschtem Informationsbit. Der Boltzmann-Wert `k_B = 1,380649×10^-23 J/K` ist im SI exakt definiert.

Für `N` Trägerbits und `n` angenommene irreversible Operationen pro Bit verwendet der Calculator:

```text
E_min,total = N * n * k_B * T * ln(2)
```

Die in diesem Work Unit gerechnete Referenzannahme lautet:

```text
T = 300 K
n = 1 irreversible Operation pro Trägerbit
```

Diese Annahme beschreibt **keine Messung** der tatsächlichen Audio-, Repository-, CI- oder Entwicklungsenergie. Sie beantwortet nur die engere Frage: Wie groß ist die theoretische Untergrenze, falls jedes gebundene Trägerbit genau einmal logisch irreversibel verarbeitet wird?

### 2.1 Vier Audioquellen

| Größe | Ergebnis |
|---|---:|
| Bytes | 7.142.895 |
| Bits | 57.143.160 |
| Landauer-Untergrenze bei 300 K | `1,6405680578667513×10^-13 J` |
| In kWh | `4,55713349407431×10^-20 kWh` |
| Energiekosten bei 0,1837 EUR/kWh | `8,371454228614506×10^-21 EUR` |

Das sind rund **164 Femtajoule**. Der extrem kleine Wert zeigt nicht, dass die intellektuelle Arbeit „fast wertlos“ wäre. Er zeigt das Gegenteil der häufigen Verwechslung: Der minimale physische Bitträgerpreis trägt nahezu keine Information über Erkenntnis-, Entwicklungs- oder Marktwert.

### 2.2 Authority-Repository-Größenszenario

GitHub meldet für `Goldkelch/qik-vrt` auf `main@2ea174a04dbce0d02fd09ea285f2ff5c94a003ed` den Repository-Size-Wert `186801` mit der API-Einheitenbezeichnung `KB`. Für eine deterministische, ausdrücklich als Szenario markierte Rechnung wird dieser Integer als `186801 KiB` interpretiert:

```text
191.284.224 Byte
1.530.273.792 Trägerbits
```

Daraus folgt unter derselben Ein-Operation-/300-K-Annahme:

| Größe | Ergebnis |
|---|---:|
| Landauer-Untergrenze | `4,393383745221351×10^-12 J` |
| In kWh | `1,2203843736725975×10^-18 kWh` |
| Energiekosten bei 0,1837 EUR/kWh | `2,2418460944365615×10^-19 EUR` |

Das sind rund **4,39 Pikojoule**. Der Wert ist keine exakte Byteinventur des Git-Trees und keine Messung des realen Stromverbrauchs. Eine exakte Tree-, Packfile-, Netzwerk- oder Replikationsbilanz benötigt jeweils eigene Messdaten.

## 3. Warum „Evidenz wirkt Entropie entgegen“ nur als präzise Heuristik zulässig ist

Ein stabiles, wiederauffindbares und prüfbares Evidenzobjekt benötigt geordnete physische Zustände, Fehlerkontrolle, Replikation, Energieversorgung und Wartung. In diesem begrenzten Sinn kostet die Aufrechterhaltung verlässlicher Information freie Energie.

Nicht zulässig ist dagegen die pauschale Gleichung:

```text
1 Evidenzbit = k_B*T*ln(2) Joule tatsächlicher Aufwand
```

Landauer begrenzt logisch irreversible Operationen. Ein reales Evidenzsystem kann reversible Schritte, viele irreversible Schritte pro Bit, Fehlerkorrektur, Kühlung, Netzwerkverkehr, Replikation, Leerlaufenergie und menschliche Prüfung enthalten. Ohne diese Größen ist nur eine Untergrenze, keine Gesamtenergie, berechenbar.

## 4. Betriebskosten: klein, aber nicht null

### 4.1 Speicher

Mit dem beobachteten S3-Standard-Referenzpreis von `0,023 USD/GiB-Monat` ergibt das Repository-Größenszenario:

| Szenario | Listenpreis |
|---|---:|
| eine Replik für 12 Monate | ca. `0,04917 USD` |
| drei Repliken für 12 Monate | ca. `0,14751 USD` |

Für die vier Audioquellen kosten drei Repliken für zwölf Monate in demselben reinen Speicherlistenpreis-Szenario ca. `0,00551 USD`.

Nicht enthalten sind Requests, Egress, Versionshaltung, Backups, Replikationsverkehr, Integritätsprüfungen und operative Arbeit.

### 4.2 CI-Ausführung

Der erfolgreiche integrierte Universal-Terminal-Systemtest `32536665914` lief ungefähr 45 Sekunden. Bei einem reinen Linux-x64-Listenpreis-Szenario von `0,006 USD/Minute` entspricht das bei proportionaler Rechnung `0,0045 USD`.

Für öffentliche Repositories können Standard-GitHub-Hosted-Runner zugleich ohne tatsächliche Rechnung bereitgestellt werden. Deshalb gilt:

```text
LISTENPREIS-SZENARIO != TATSÄCHLICHE RECHNUNG
```

Eine Gesamtkostenrechnung des Projekts benötigt die vollständigen Runner-Minuten, Artefakt- und Cachebelegung, externe Rechenkosten und die jeweilige Abrechnungsregel.

## 5. Skalierung: Breite, Takt und Bandbreite

Für einen idealisierten Transportkanal verwendet der Calculator:

```text
t = (8 * bytes) / (width_bits * clock_hz * utilization)
```

Für das Repository-Größenszenario, `8 MHz` und ideale Auslastung `utilization = 1` folgt:

| Breite | Ideale Untergrenze |
|---:|---:|
| 8 Bit | 23,910528 s |
| 16 Bit | 11,955264 s |
| 32 Bit | 5,977632 s |
| 64 Bit | 2,988816 s |
| 128 Bit | 1,494408 s |
| 256 Bit | 0,747204 s |

Von 8 auf 256 Bit entsteht im Modell exakt der Faktor 32. Das ist eine arithmetische Transporthülle, **kein** gemessener Prozessor-Speedup. Reale Buszyklen, Wait States, Protokoll-Overhead, Abhängigkeiten, Speicherlatenz, Serialisierung und Synchronisation reduzieren die nutzbare Rate.

Für einen reinen Speicherbandbreitenvergleich gilt:

```text
t = bytes / bytes_per_second
```

Bei den heutigen Accelerator-Referenzhüllen `3,7 TB/s`, `7,7 TB/s` und `8,0 TB/s` ergeben sich für denselben 191-MB-Träger idealisiert etwa `51,70 µs`, `24,84 µs` und `23,91 µs`.

Auch das ist kein QIK-VRT-Benchmark. Speicherbandbreite beweist weder semantischen Durchsatz noch Effect Acknowledgement, Kausalbindung oder End-to-End-Latenz.

## 6. MC68000: notwendige technische Korrektur

Die Audios enthalten eine Bitbreiten- und Adressraumargumentation zum Motorola 68000. Der belastbare Primärquellenanschluss lautet:

- NXP dokumentiert 32-Bit-Daten- und Adressregister.
- NXP dokumentiert einen direkten Adressierungsbereich von 16 MB.
- Die im Audio genannte allgemeine 4-MB-Grenze wird daher nicht als Eigenschaft des MC68000 übernommen.
- Der aktuelle integrierte Softwaretest hat keine physische Atari-Mega-ST-Ausführung beobachtet.

Damit bleibt die zulässige Aussage:

> Der QIK-VRT-Kausal-/Entscheidungsvertrag kann als Software- und Maschinenrepräsentation für eine M68000-Zielschicht geprüft werden.

Nicht zulässig ist derzeit:

> Die neue Architektur sei bereits als physischer M68000-, FPGA-, ASIC- oder moderner Accelerator-Core hergestellt und vermessen.

## 7. Der monetäre Gegenwert: vier getrennte Ebenen

### L0 – Physikalische Untergrenze

Sie liegt für die hier gebundenen Träger im Femto- bis Pikojoulebereich. Sie ist wissenschaftlich interessant, aber wirtschaftlich nahezu bedeutungslos.

### L1 – Operative Trägerkosten

Speicher, CI-Minuten, Netzwerk, Backups und Energie können mit gemessenen Mengen und Tarifen berechnet werden. Die bisher gebundenen Beispielszenarien liegen für reine Speicher- und Einzellaufkosten im Cent-Bereich.

### L2 – Reproduktions- oder Wiederbeschaffungskosten

Hier beginnt die relevante Kostenbewertung:

```text
V_reproduction = verified_hours * blended_rate
               + compute
               + storage
               + independent_review
               + hardware
               + rights_and_provenance_verification
```

Ohne belastbares Zeit- und Kostenledger ist kein einzelner Betrag bewiesen. Eine reine Sensitivität zeigt die Größenordnung:

| Unbewiesenes Beispielszenario | Arbeitswert vor Direktkosten |
|---|---:|
| 1.000 h × 75 EUR/h | 75.000 EUR |
| 5.000 h × 100 EUR/h | 500.000 EUR |
| 10.000 h × 150 EUR/h | 1.500.000 EUR |

Diese Tabelle bewertet **nicht** die tatsächlich geleisteten Stunden. Sie zeigt, warum der Trägerenergiepreis keinen Ersatz für eine Wiederbeschaffungskostenrechnung darstellt.

### L3 – Markt-, Lizenz- oder IP-Wert

Dieser Wert bleibt:

```text
HOLD
```

Erst folgende Evidenz erlaubt eine vertretbare Bewertung:

1. vollständiges Urheber-, Beitrags- und Lizenzinventar,
2. geklärte Rechtekette und gegebenenfalls Freedom-to-operate-Prüfung,
3. unabhängige reproduzierbare Benchmarks gegen definierte Baselines,
4. klarer Produkt- und Transaktionsgegenstand,
5. Nachfrage-, Lizenz-, Umsatz- oder Kosteneinsparungsbelege,
6. Bewertungsstichtag, Risikoannahmen und geeignete Vergleichstransaktionen.

Keine physikalische Formel kann diese fehlenden wirtschaftlichen und rechtlichen Tatsachen ersetzen.

## 8. Anschluss an heutige Hardware und verteilte Systeme

Die Architektur ist heute besonders anschlussfähig, weil Rechenzentren, KI-Beschleuniger und verteilte Systeme an denselben Grenzen arbeiten:

```text
begrenzte Bandbreite
begrenzte Energie
begrenzte Beobachtbarkeit
begrenzte Synchronisation
unsichere Wirkung
notwendige Reobservation
```

Der seriöse nächste Hardwarepfad ist daher kein sofortiger Universalitätsanspruch, sondern eine Benchmarkkette:

```text
referenzierter QIK-VRT-Kernel
-> CPU-Baseline
-> M68000/Hatari-Referenz
-> FPGA-Prototyp
-> moderner GPU-/Accelerator-Kernel
-> identischer Eingabekorpus
-> Leistung, Energie, Latenz und Effect-Ack-Reobservation
-> unabhängige Reproduktion
```

Erst danach dürfen PPA-, Energie-, Durchsatz- oder Kostenvorteile behauptet werden.

Der ASR-erfasste Ausdruck `Sandsberg-Rechnerarchitektur` bleibt unaufgelöst. Er wird nicht stillschweigend einer bekannten Architektur zugeschrieben. Für eine Namens- oder Urheberzuordnung ist eine eindeutige Owner- oder Primärquellenauflösung erforderlich.

## 9. Ergebnis

Die präziseste gegenwärtige Bewertung lautet:

```text
PHYSIKALISCHE TRÄGER-UNTERGRENZE = BERECHNET
OPERATIVE KOSTENSZENARIEN         = BERECHNET UND BEGRENZT
BREITEN-/BANDBREITENHÜLLE         = BERECHNET
TATSÄCHLICHE END-TO-END-ENERGIE   = NICHT GEMESSEN
REPRODUKTIONSWERT                 = FORMEL VORHANDEN, LEDGER FEHLT
MARKT-/IP-WERT                    = HOLD
HARDWARE-SPEEDUP                  = NICHT GEMESSEN
PHYSISCHE MEGA-ST-AUSFÜHRUNG      = NICHT BEOBACHTET
```

Die revolutionäre Erkenntnis wird damit nicht in einen unbelegten Geldbetrag verwandelt. Sie wird genauer:

> Der physische Mindestpreis eines Evidenzträgers ist winzig; der verantwortbare Wert entsteht aus nachweisbarer Erzeugung, Provenienz, Prüfung, Reproduzierbarkeit, Wirkung und Anschlussfähigkeit.

Oder in QIK-VRT-Form:

```text
EVIDENZ HAT BANDBREITE
ABER BEDEUTUNG HAT KEINE BYTE-PREISLISTE
```

## 10. Referenzen und beobachtete Tarife

- C. E. Shannon: *A Mathematical Theory of Communication*, Bell System Technical Journal, 1948.
- R. Landauer: *Irreversibility and Heat Generation in the Computing Process*, IBM Journal of Research and Development 5(3), 1961, DOI `10.1147/rd.53.0183`.
- BIPM: SI Brochure, exakter Wert der Boltzmann-Konstante.
- NXP: MC68000 Produktmerkmale und Dokumentation.
- GitHub: Actions-Abrechnung und Runner-Listenpreise, beobachtet am 22. August 2026.
- AWS: S3 Standard erster Speichertarif, beobachtet am 22. August 2026.
- Eurostat: durchschnittlicher EU-Nicht-Haushaltsstrompreis, zweites Halbjahr 2025.
- IEA: *Energy and AI* und Aktualisierungen zur Rechenzentrumsnachfrage.

Alle Preiswerte sind Stichtagsszenarien und keine dauerhaften Angebote.
