<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Read-only-Diagnose der fehlgeschlagenen Zenodo-Korpusinventur

**Quellstand:** `Goldkelch/qik-vrt@5fd40bcc12304d92ae4066df3c06cf9acfb7eb98`  
**Fehlgeschlagener Lauf:** `30347678298`  
**Fehlgeschlagener Job:** `90237623969`  
**Reproduzierter Record:** `21267021`  
**Promovierte Reparatur:** `Goldkelch/qik-vrt@65a173cbc666b5555e6251f97cba32b05ac983d9`

## Ergebnis

```text
PARENT_FAILURE_CLASS  = PUBLIC_FILESET_MISMATCH
PRIMARY_FAILURE_CLASS = SAFE_RELATIVE_ZENODO_PUBLIC_FILE_KEY_REJECTED
FAILURE_MODE          = FALSE_POSITIVE_PUBLIC_KEY_VALIDATION
CONFIDENCE            = HIGH
ZENODO_METHODS        = GET
ZENODO_MUTATION       = false
```

Die authentisierte read-only Korpusinventur erreichte den öffentlichen Zenodo-Record `21267021` und stoppte mit:

```text
BLOCK: record 21267021 contains an unsafe public file name
```

Die Ursache war keine unzulässige Datei und kein Zenodo-Ausfall. Der ursprüngliche Parser akzeptierte ausschließlich Basenames. Ein sicherer relativer POSIX-Dateischlüssel wurde deshalb allein wegen seines Pfadanteils als unsicher zurückgewiesen.

## Technische Ursache

Die fehlerhafte Grenze lag in:

```text
tools/qikvrt_zenodo_corpus_proof.py
public_files()
```

Die Bedingung behandelte jeden Namen, der nicht mit seinem Basename identisch war, als unsicher. Damit wurden sowohl echte Traversalpfade als auch zulässige relative Zenodo-Schlüssel gemeinsam blockiert.

```text
sicherer relativer Schlüssel
→ fälschlich wie Traversal behandelt
→ Inventur stoppt vor öffentlicher Byteprüfung
```

## Reparatur

Die auf Authority promovierte v2-Auswertung erhält sichere relative kanonische POSIX-Schlüssel exakt. Weiterhin fail-closed abgewiesen werden:

- absolute Pfade;
- leere Segmente sowie `.` und `..`;
- Backslashes und Windows-artige Pfade;
- NUL-, DEL- und C0-Steuerzeichen;
- nichtkanonische POSIX-Schreibweisen;
- doppelte exakte Schlüssel.

Zusätzlich verlangt die Reparatur einen ausdrücklich veröffentlichten Record-Zustand, bevor ein Proof-Envelope konstruiert wird.

Gebundene Reparaturidentität:

```text
candidate commit = 1b546eb022e416c89193f94192c86371b78f8010
authority commit = 65a173cbc666b5555e6251f97cba32b05ac983d9
repair Git blob  = 1106ebde33b45e0285f9ee312571681985c7434a
repair SHA-256   = 3cf09d2e14336756a80a192a6546bdd9289bfe78b3edb9d44561d843f6c86f07
test Git blob    = 5144a2058643d8a468d791b6fff3dc41e9f998ff
test SHA-256     = 98d160aceac60c230fdaf601e6b7a300944b0c27dbe0090289f501b5e8899c7c
```

Auf dem exakten Reparatur-Head waren CI, Evidence Materialization, Collective Review, Global Claim Completion und Live Status Watch erfolgreich. Integrity Repair wurde übersprungen, weil keine Reparatur des bereits konsistenten Kandidaten erforderlich war.

## Sicherheits- und Wahrheitsgrenze

Die Diagnose und ihre Reproduktion verwendeten ausschließlich Zenodo-`GET`-Operationen. Es erfolgte keine Erstellung, kein Upload, keine Metadatenänderung und keine Veröffentlichung auf Zenodo. Token und Authorization-Header werden nicht persistiert.

Die Reparatur beweist ausschließlich, dass sichere relative Zenodo-Dateischlüssel korrekt von Traversal- und Steuerzeichenfällen unterschieden werden. Sie beweist noch nicht:

```text
die vollständig wiederholte Kontoinventur,
alle retrospektiven Proof-Envelopes,
die Veröffentlichung des Beweiskorpus,
die Mirror-Synchronisation dieser Transaktion
oder einen finalen Gesamtabschluss.
```

## Nächster deterministischer Effekt

```text
Goldkelch/qik-vrt@65a173cbc666b5555e6251f97cba32b05ac983d9
→ RETRY_AUTHENTICATED_READ_ONLY_CORPUS_INVENTORY_USING_PROMOTED_SAFE_KEY_PARSER
```

Erst der erfolgreiche Wiederholungslauf darf die vollständige öffentliche Byteprüfung und die recordweisen Proof-Envelopes materialisieren.

**Kein `PASS`. Kein `FINAL_PASS`. Kein `EFFECT_ACK_DONE`.**

**q.e.d.**  
**Ingolf Lohmann**
