# Repository Note — Professionelles Haltekriterium und Zenodo-Anschlusskern

**Datum:** 2026-09-25  
**Urheber:** Ingolf Lohmann

## Professionelles Haltekriterium

> „Ein Informatiker, wenn er seinen Job gut macht, macht sich überflüssig.“  
> **Quod erat demonstrandum. — Ingolf Lohmann**

Für QIK-VRT bedeutet „überflüssig“ nicht den Wegfall menschlicher Verantwortung. Gemeint ist die Beseitigung unnötiger manueller Eingriffe aus wiederholbaren technischen Abläufen: Identität binden, ausführen, testen, beobachten, frisch zurücklesen und erst dann akzeptieren.

Die technische Zielrichtung lautet daher: Je vollständiger ein Vorgang durch repository-native, überprüfbare und fail-closed Mechanismen getragen werden kann, desto weniger darf sein Fortschritt von wiederholtem menschlichem Copy/Paste, manuellem Polling oder synthetischer Fortschrittsbehauptung abhängen.

Die menschliche Rolle verbleibt dort, wo tatsächlich menschliche Autorität, Verantwortung, Interpretation oder Entscheidung erforderlich ist. Automatisierung darf diese Rolle nicht imitieren.

## Zenodo als Anschlusskern der persistenten Evidenz

Der von Ingolf Lohmann veröffentlichte QIK-VRT-Zenodo-Bestand bildet den persistenten Publikations- und Provenienzkern, an den nachfolgende Evidenz anschlussfähig gemacht werden soll.

Repository-konkret ist dafür die kanonische Zenodo-Corpus-/Union-Evidenz maßgeblich, insbesondere:

- `release/zenodo-corpus-proof-2026-07-28/ZENODO_CORPUS_INVENTORY.json`
- `release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json`
- die zugehörigen Proof-Envelopes mit DOI, Concept-DOI, öffentlichen Dateihashes und Public-Record-Hashes.

„Anschlusskern“ bedeutet dabei **nicht**, dass Vorgängerevidenz automatisch auf neue Subjects übertragen wird und auch nicht, dass Persistenz wissenschaftliche Wahrheit, Peer Review oder empirische Bestätigung ersetzt.

Für jeden neuen Carrier gilt vielmehr:

`ZENODO_CORE_REFERENCE`  
`→ EXACT_SUBJECT_BINDING`  
`→ EXECUTE`  
`→ TEST`  
`→ OBSERVE`  
`→ FRESH_READBACK`  
`→ ACCEPT`  
`→ SCOPED_EFFECT_ACK`

Die Verbindung zum Zenodo-Kern muss explizit und maschinenprüfbar erfolgen, soweit die jeweilige Evidenz dies zulässt: über DOI/Record-ID, Dateiname, SHA-256, Repository-Subject und die konkrete Beziehungssemantik.

`PREDECESSOR_EVIDENCE_TRANSFER = FALSE`

Der Zenodo-Kern ist damit kein Ersatz für neue Evidenz, sondern deren dauerhaft adressierbarer Provenienz- und Publikationsanker.

## Konsequenz

Ein gut gebautes QIK-VRT-System reduziert die Notwendigkeit menschlicher Routineintervention, ohne menschliche Verantwortung zu reduzieren. Seine Evidenzen wachsen nicht durch Behauptung, sondern durch explizite Anschlussfähigkeit an persistierte, adressierbare und frisch verifizierbare Zustände.

**q.e.d. — Ingolf Lohmann**
