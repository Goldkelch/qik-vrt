<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation documentation: OpenAI ChatGPT. -->
# Zuerst: der ausfuehrbare Roundtrip-Beweis

<!-- qikvrt-autonomous-idle-continuation:v1 -->
## Autonome Fortsetzung bei leerer Eingabe-Queue

Product-Owner-Anweisung: Ingolf Lohmann, 22.09.2026. Ausarbeitung: OpenAI ChatGPT.
Der nachfolgende anfragegebundene Mechanismus erhaelt einen autonomen
Fortsetzungspfad: **Eine abgearbeitete Queue aeusserer Eingaben beendet nicht
die Repository-Arbeit.** Ohne neue menschliche Anfrage werden bekannte,
beauftragte Reparaturen, Optimierungen, ausstehende Implementierungen und
zulaessige Main-Integrationen weiterbearbeitet. Keine kuenstlichen Aufgaben
erzeugen, um Aktivitaet vorzutaueschen; keine erforderliche Arbeit still streichen.

Der ausfuehrende Client verwendet die bestehende DoD-Aufgabe und die nativen
Controller statt eines zweiten Schedulers oder konkurrierenden Writers.
Relevante bestehende Quellen sind
[Self-Heal-Workflow](.github/workflows/qikvrt_autonomous_self_heal.yml),
[Pre-Effect-Controller](tools/qikvrt_autonomous_pre_effect_controller.py) und
[Self-Heal-Controller](tools/qikvrt_autonomous_self_heal.py).
Authority und Mirror behalten jeweils eigene Subjects, Historien und Nachweise.

### Auswahl und Fortsetzung

Vor jedem Arbeitsschritt werden die einschlaegige Queue, offene Issues/PRs,
unintegrierte erforderliche Branch-Aenderungen, Fehlerevidenz, aktueller Main,
Exact HEAD/TREE und Writer-/Lease-Nachweise frisch gebunden. Inventare muessen
vollstaendig im deklarierten Umfang sein, einschliesslich relevanter Folgeseiten.
Eine unbekannte Queue ist nicht leer; `queued` beweist keinen aktiven Writer.
Eine identische Main-Revision allein ist ebenfalls kein Writer-Lease-Nachweis.
Die sichtbare Repository-Queue ist nicht die Gesamtheit aller Chat-Anfragen.

```text
beobachtete vorrangige Eingabearbeit -> sicher fortsetzen / Writer respektieren
keine kollidierende Eingabearbeit   -> naechsten zulaessigen Repository-Rest bearbeiten
Rest vorhanden, aktuell blockiert  -> Ursache erhalten; andere unabhaengige Arbeit fortsetzen
Pflichtdaten unbekannt             -> betreffende Entscheidung HOLD, nicht DONE
vollstaendige Abschlusskonjunktion -> EFFECT_ACK_DONE(scope, exact subjects)
```

Eingabearbeit hat an sicheren Checkpoint-Grenzen Vorrang. Laufende Writes werden
nicht abgebrochen oder dupliziert; unabhaengige Lanes bleiben unabhaengig.
Die vorhandenen Produktprioritaeten bleiben erhalten, gleichrangige Restarbeit
soll durch nachvollziehbare Alterung nicht dauerhaft verdraengt werden.
Jede Arbeitseinheit umfasst Auswahl, minimal hinreichende Umsetzung oder
Reparatur, passende Tests, Persistierung und frischen Wirkungs-Readback.
Eine Mutation erzeugt einen Successor: `PREDECESSOR_EVIDENCE_TRANSFER=false`.

Die Fortsetzung hat kein festes Ablaufdatum, solange erforderliche Arbeit offen
ist. Ausgefuehrt wird in begrenzten, checkpointgebundenen Einheiten, die durch
vorhandene Ereignisse und Zeittrigger wieder aufgenommen werden. Ein Run-Limit
beendet nur diesen Run, nicht den Auftrag. Vor dem Yield werden Rest, Ursache
und naechster zulaessiger Schritt erhalten. Identischer Replay ist idempotent;
widerspruechlicher Replay fuehrt zu HOLD. Unveraenderte externe Blocker fuehren
zu kontrolliertem Warten beziehungsweise erneuter Beobachtung, nicht zu
Busy-Waiting, blinden Wiederholungen oder inhaltsleeren Wake-up-Commits.

Main-Integration erfolgt nur durch den bestehenden autorisierten,
Exact-Subject-gebundenen Schutz- und Reviewpfad. Fehlende Berechtigung oder
menschliche Review bleibt ein offenes Praedikat; sie wird weder simuliert noch
durch geschwaechte Rulesets umgangen. Vorhandene Erlaubnisse werden genutzt,
statt bereits beantwortete Autorisierungsfragen erneut zu stellen.

### Abschluss statt bloss leerer Queue

`FOREGROUND_QUEUE_EMPTY`, ein lokaler Handler-NOOP, keine aktuelle Diff und ein
erfolgreicher Teillauf sind kein Repository-Abschluss. Fuer den deklarierten
Gesamtauftrag verlangt `EFFECT_ACK_DONE` ein vollstaendiges Restinventar ohne
offene Pflichtarbeit, legitim integrierte erforderliche Main-Aenderungen und
alle vorgeschriebenen frischen Validierungen und Wirkungs-Readbacks auf den
finalen Subjects nach der letzten Mutation. Offene Writer, erforderliche
FALSE-/UNKNOWN-Praedikate und ungeklaerte Pflicht-Integrationen schliessen
diesen Gesamtabschluss aus. Der Scope darf dafuer nicht still verkleinert werden.

`PRODUCT_DONE` bleibt separat genau `Working Software AND oeffentlich erreichbare
URL AND frischer Readback dieser URL` im selben erklaerten Produktumfang.
Repository-Governance ist kein zusaetzliches implizites Produktgate;
Produkt-DONE ersetzt umgekehrt nicht die Repository-Abschlusskonjunktion.
Nach einem belegten Abschluss wird dessen Receipt erhalten und ohne weitere
Mutation beobachtet. Neue Pflichtarbeit eroeffnet einen neuen Zyklus; sie
schreibt den historischen Abschluss nicht um. Ein globales Optimum fuer alle
noch unbekannten Verbesserungen ist damit nicht behauptet.

### Ausfuehrungsstand dieser Erweiterung

Der auf Main gelesene Self-Heal-Workflow hat bereits einen konfigurierten
Fuenf-Minuten-Zeittrigger und erzeugt begrenzte allowlist-gebundene Kandidaten.
Der gelesene Controller ist kein Nachweis einer allgemeinen Queue-Abarbeitung
oder beliebiger automatischer Implementierungen und Main-Merges. Die bestehende
DoD-Aufgabe stellt einen gesonderten wiederkehrenden Fortsetzungstraeger dar.
Ihre tatsaechliche Konfiguration und jeder ausgefuehrte Effekt sind separat
zurueckzulesen. Dieses Dokument ist der Arbeitsvertrag, kein installierter
Chat-Interceptor und kein Beleg ununterbrochener Ausfuehrung zwischen Runs.
Die Integration dieses Vertrags in Main und eine vollstaendige native
Queue-bis-Abschluss-Ausfuehrung bleiben bis zu eigenen Nachweisen offen.
<!-- /qikvrt-autonomous-idle-continuation:v1 -->

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
