<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation documentation: OpenAI ChatGPT. -->
# Zuerst: der ausfuehrbare Roundtrip-Beweis

Der feste Einstieg ist **`roundtrip.py` im Repository-Wurzelverzeichnis**.
Er ruft den vorhandenen Runner `next/tools/run_checks.py` auf, statt einen
zweiten Beweisgang mit abweichender Semantik einzufuehren.

```sh
python3 -B roundtrip.py --repository Goldkelch/qik-vrt --output-dir ../roundtrip-evidence
```

Im Mirror `--repository ingolf-lohmann/qik-vrt` verwenden; bei anderen Forks
immer das eigene Repository nennen. Jeder Lauf braucht ein neues
Ausgabeverzeichnis ausserhalb des Checkouts. Python-Optimierung (`-O`, `-OO`,
`PYTHONOPTIMIZE`) ist ausgeschlossen, damit Assertions nicht entfallen.
Die gesperrte Toolchain zuerst nach [next/README.md](next/README.md) einrichten;
`--offline` erst bei vollstaendig vorhandenem Tool- und Abhaengigkeitscache.

## Was dieser Runner tatsaechlich ausfuehrt

Die bestehende Suite bindet einen sauberen Commit an HEAD und TREE, prueft
Cache und Repository-Integritaet, baut und testet C90 und Rust und ruft
`check_bus.py`, `check_exchange.py`, `check_continuity.py` und
`check_hardware.py` auf. Sie fuehrt den C90-EAP-Abgleich frisch aus.

Der konkrete Recovery-Roundtrip in `check_continuity.py` umfasst Registrierung,
Persistierung, Replay, acht Prozessabbrueche/Neustarts, drei Verlagerungen,
bytegebundene Quellenwiederherstellung sowie C90-Build und Assemblerpruefung
nur aus den wiederhergestellten Quellen. Negativkontrollen verwerfen
beschaedigte bestaetigte Historie und verbieten deren stilles Neuinitialisieren.
Das sind die Pruefziele des Codes, kein durch diese Dokumentation behaupteter Lauf.

Ein neuer Lauf schreibt Logs, `continuity.json` und `receipt.json` in das neue
Ausgabeverzeichnis. Nur die dort frisch ausgefuehrte, auf denselben HEAD/TREE
gebundene Suite darf ihren endlichen Geltungsbereich mit `PASS` abschliessen.
Ein vorhandener Runner, ein Startsignal oder alte gruene CI ist kein Beweis
seiner aktuellen Ausfuehrung. Die Repository-Angabe ist ein expliziter
Ausfuehrungsparameter, keine durch den Wrapper erbrachte Fern-Authentisierung.

## Separater Primzahl-Suchversuch vom 20.09.2026

Der vom Product Owner beschriebene Versuch mit 1.000.000 Primzahlen und
1.024 Markierungen bleibt ein eigener Evidenzgegenstand. Die referenzierten
Originaldateien `longterm_simulation/fractal_search/search.py`, Markierungen
und SHA-256-gebundenen Ursprungsdaten waren am gelesenen Basis-HEAD nicht
vorhanden. Daher gilt hier **`ORIGINAL_ARTIFACT_BINDING_MISSING`**, nicht
`REPRODUCED` und nicht `PASS`. Seine Zahlen werden nicht aus dem Chat als
maschinenverifizierte Evidenz uebernommen; es werden keine Ersatzdaten als
Originale ausgegeben. Eine spaetere Anbindung muss diese Originalbytes
bewahren und die Suche gegen die vollstaendige Kandidatenpruefung ausfuehren.

## Auffindbarkeit und Grenzen

`README.md`, `/AI`, `AGENTS.md`, `next/README.md` und `next/AI` beginnen mit
demselben Verweis auf diesen Einstieg. Der idempotente Materialisierer
`python3 -B tools/qikvrt_roundtrip_entrypoint.py --apply` stellt diese Praefixe
vor die unveraenderten bisherigen Inhalte; `--check` prueft die erste Position.
Nach absichtlichen Quellenaenderungen die kanonische Integritaet neu erzeugen,
committen und den neuen Exact Subject frisch pruefen.

Identitaet/Wiederauffindbarkeit, Liveness, Autoritaet und Wirkung bleiben
getrennt. TTL-Ablauf loescht keine Referenz und ein Suchtreffer erneuert keinen
Heartbeat. Der Runner behauptet weder Main-Promotion noch native Review,
physischen Hardware-Boot, Deployment oder Produkt-DONE. Fuer letzteres bleibt
`Working Software AND oeffentlich erreichbare URL AND frischer Readback dieser URL`
erforderlich. Der Hardware-Modelltest ist kein physischer Board-Test.
