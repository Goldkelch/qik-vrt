# Evidenzerhaltende Antwortzyklen und geprüfte Abkürzungen

## Faktorisierung, Kontextbindung und bedingter Abschluss

Wissenschaftliche Arbeitsfassung und additive Integration in den bestehenden
Lean-4.19-Beweiskern. Konzept und Forschungsauftrag: Ingolf Lohmann.
Ausarbeitung, Formalisierung und Werkzeugprüfung: OpenAI Codex.

Die 13 benannten formalen Aussagen sind an die angegebenen Quellen gebunden.
Sie behaupten keine allgemeine Beantwortbarkeit aller Sachfragen, keinen
empirischen Geschwindigkeitsgewinn und keine bereits erfolgte externe Wirkung.
`CHANGE_NOTICE.md` beschreibt die Präzisierung gegenüber dem weitergehenden
Ausgangsanspruch. Die neue Fassung ist noch nicht menschlich begutachtet.

## Lesen

- `PROSA_DE.md`: zuerst im Chat gelieferter Vorlesetext mit gekennzeichnetem Nachtrag.
- `PAPER.pdf` und `PAPER.tex`: Fachartikel mit vollständigen Herleitungen.
- `CLAIM_MATRIX.json`: benannte Aussagen, Erkenntnisstatus und Nachweise.
- `evidence/`: lokale Kernel-, Axiom- und Negativkontrollprotokolle.
- `PUBLICATION_STATE.json`: Publikationsbereitschaft und verbleibende externe Bedingungen.

## Reproduzieren

Aus der Repository-Wurzel mit dem in `lean-toolchain` gebundenen Lean 4.19.0:

```sh
cd formalization/QIKVRT_Formalization_v2.0
lake build
python3 scripts/audit_lean_axioms.py
python3 scripts/audit_proof_escapes.py
lake env lean -E hasSorry QIKVRTFormalization/Decision/AnswerReuseAxiomAudit.lean
cd ../..
python3 docs/publications/2026-09-15-answer-cycle-reuse/verify_package.py
```

`verify_package.py` verwirft zusätzlich vier negative Kontrollen: eine falsche
Aussage, eine Beweislücke, fehlende Anwendbarkeit und fehlende Fortschrittsprämisse.
Ein normaler Linux-Rechner benötigt keine Laufzeit-Kompatibilitätsschicht.
In der untersuchten Arbeitsumgebung ist nur der numerische eigene Prozesspfad
nicht zugänglich. `runtime/self_exe_path.c` verwendet ausschließlich für diesen
eigenen Pfad den zulässigen Alias `/proc/self/exe`. Der Kernel bleibt unverändert.
Die Verwendung wird im Receipt offengelegt; auch die Negativkontrollen laufen
unter denselben Laufzeitbedingungen.

Das PDF wird im Publikationsverzeichnis mit XeLaTeX erzeugt:

```sh
xelatex -interaction=nonstopmode -halt-on-error PAPER.tex
xelatex -interaction=nonstopmode -halt-on-error PAPER.tex
```

Temporäre LaTeX-Dateien gehören nicht zur Publikation. Das PDF wurde zusätzlich
gerendert und visuell geprüft. Eine spätere Änderung der PDF-Bytes verlangt einen
neuen Freeze; Prüfnachweise eines Vorgänger-Heads werden nicht auf neue Heads übertragen.

## Wiederverwendung und Integration

Wiederverwendet werden `Process/Factorization.lean` und
`Decision/ObservationSufficiency.lean`, der bestehende Lake-Build,
`scripts/audit_lean_axioms.py`, der Proof-Escape-Scanner und der vorhandene
Manuskript-Workflow. Der neue Artikeladapter bindet die neue Aussagenliste und
ihre Negativkontrollen. Die älteren Receipt-Werkzeuge sind an andere feste
Publikations-IDs und Quellen gebunden; deren Belege werden nicht übernommen.

Die Integration erfolgt über `QIKVRTFormalization.lean`. Ein erfolgreicher
lokaler Build bezeichnet die Integration im Kandidaten. Eine Integration in
Trusted Main und eine Zenodo-Veröffentlichung benötigen ihre jeweils eigenen
beobachteten Übergänge. Der bestehende generische Zenodo-Publisher bleibt die
Produktionsschnittstelle. Keine Publikations- oder Freigaberegel wird geändert.

Dokumentation: CC BY-NC-ND 4.0. Quellcode: jeweilige Dateilizenz.
