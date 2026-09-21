<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation documentation: OpenAI ChatGPT. -->
# Zuerst: der ausfuehrbare Roundtrip-Beweis

<!-- qikvrt-request-jit-evidence:v1 -->
## Arbeitsweise bei jeder Anfrage: Just-in-time-Evidenz und verlustfreie Konsolidierung

Product-Owner-Anweisung: Ingolf Lohmann, 21.09.2026. Ausarbeitung: OpenAI ChatGPT.
Der Roundtrip-Einstieg ist auch die erste Weiche fuer die Anfragebearbeitung:
**Vorhandenes passend wiederverwenden; fehlende Evidenz gezielt erzeugen und
manifestieren; ohne Informationsverlust konsolidieren; so frueh wie belastbar
antworten.** Nicht jede Anfrage verlangt einen vollstaendigen Roundtrip-Build.

Dieser Ablauf konkretisiert die vorhandenen Vertraege, ersetzt sie nicht:
[HMI-Adaptation](policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json) mit
`REUSE_BEFORE_CREATE` und `FASTEST_VERIFIED_PATH` sowie
[begrenzte Einstiegspunkt-Optimierung](state/authorization/delegations/OWNER_AI_ENTRYPOINT_CONTINUOUS_OPTIMIZATION_V1.json).
TEMDD T1-T16 bleiben verbindlich; daraus entsteht keine weitere Freigabestufe.

1. **Anfrage und Subject binden.** Zuerst die fuer die Antwort notwendigen
   Aussagen, Quellen, Gueltigkeitsbereiche und Frischeanforderungen bestimmen.
   Repository-Evidenz bindet Repository-ID, HEAD und TREE; externe Beobachtungen
   binden ihre eigene Objektversion und Beobachtungsbedingungen. Bereits bekannte
   Angaben und beantwortete Fragen nicht erneut vom Menschen verlangen.
2. **Passende Evidenz wiederverwenden.** Nur Belege verwenden, deren Subject,
   Eingabedaten, Tool-/Modellidentitaet und -version, Policy, Normalisierung,
   Pruefumfang und relevante Ausfuehrungsumgebung uebereinstimmen. Ein Zeitstempel
   allein belegt keine Gueltigkeit. Ein Cachetreffer ueberspringt weder eine
   vorgeschriebene frische Ausfuehrung noch einen aktuellen Wirkungs-Readback.
   HEAD-Mutation erzeugt ein neues Subject: `PREDECESSOR_EVIDENCE_TRANSFER=false`.
3. **Luecken just in time schliessen.** Fuer jede antwortrelevante Luecke den
   kleinsten hinreichenden echten Readback, Test oder Nachweis ausfuehren.
   Inkrementelle Arbeit und unabhaengige parallele Reads bevorzugen; Ergebnisse
   deterministisch zusammenfuehren. Wo der Vertrag Gesamtvalidierung verlangt,
   bleibt sie erforderlich. Request, Queue und Dispatch sind keine Ausfuehrung;
   synthetische Ersatzdaten sind keine wiedergefundenen historischen Originale.
4. **Ergebnis und Herkunft manifestieren.** Relevante neue Belege, Korrekturen
   und Blocker im dafuer autorisierten Evidenzspeicher mit Quellenverweisen,
   Exact Subject, Eingabe-/Ausgabe-Digests, Producer, Pruefumfang, Ergebnis und
   erforderlichen Beobachtungsdaten erhalten. Erst nach Speicherung und passendem
   Readback als persistiert bezeichnen. Ein Digest allein ersetzt keine Daten.
   Keine privaten Anfragen, personenbezogenen Rohdaten oder Geheimnisse allein
   wegen dieser Arbeitsregel in ein oeffentliches Repository schreiben.
5. **Verlustfrei optimieren und konsolidieren.** Originalbytes, stabile
   Referenzen, historische Versionen, Kausalbeziehungen, Widersprueche und offene
   Punkte erhalten. Zusammenfassungen und Indizes sind rekonstruierbare
   Ableitungen, kein Ersatz fuer Quellen. Append-only-Korrekturen; identischer
   Replay bleibt idempotent, widerspruechlicher Replay fuehrt zu `HOLD`.
   Code-/Policy-Aenderungen bleiben reviewbare, frisch validierte Successors.
   Keine inhaltsleeren Wake-up-Commits; fehlende Evidenz wird nicht durch `NOOP`
   erledigt. Ohne materielle neue Erkenntnis ist kein weiterer Schreibvorgang
   notwendig. Unabhaengige Lanes nicht kuenstlich aneinander koppeln.
6. **Antwort rechtzeitig und wahrheitsgetreu liefern.** Den ersten belastbaren
   Teil frueh liefern und nur entscheidungsrelevante Unsicherheit weiter pruefen.
   Tatsachen, abgeleitete Schlussfolgerungen, Annahmen und unbekannte Punkte
   unterscheidbar halten. Bei Ressourcen-, Daten- oder Berechtigungsgrenzen den
   belegten Teil und den konkreten offenen Rest nennen; unbekannt bleibt unbekannt.
   Frische, an einen Lauf gebundene Zustaende wie `AMBIGUOUS`, `NOT_FOUND` im
   geprueften Suchbereich und `UNRESOLVED_BUDGET` nicht in `UNIQUE` umdeuten.

Optimierungsziel: **geringste vermeidbare Latenz unter unveraenderten
Wahrheits-, Evidenz-, Sicherheits- und Autorisierungsbedingungen**. Das ist kein
unbewiesener Anspruch auf ein globales Laufzeit- oder Wahrheitsoptimum.
Beschleunigung nur mit vergleichbaren Messungen behaupten, nicht aus dem
Vorhandensein eines Index oder Caches folgern.

Dies ist der anfragegebundene Arbeitsvertrag fuer ausfuehrende Clients, kein
installierter globaler Chat-Interceptor und kein Hintergrunddienst. Lesen der
Datei oder Generieren einer Antwort startet nicht automatisch GitHub Actions.
Die konkrete Anfrage und vorhandene Delegationen bestimmen den Schreibumfang;
kein pauschaler Auftrag fuer sachfremde Repository-Aenderungen, native Reviews,
Main-Promotion, Veroeffentlichung, Deployment oder andere externe Wirkungen.
Fehlende menschliche Autoritaet laesst sich nicht maschinell erzeugen.
Der vorhandene Runner und seine unten beschriebenen Beweisgrenzen bleiben erhalten.
<!-- /qikvrt-request-jit-evidence:v1 -->

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
