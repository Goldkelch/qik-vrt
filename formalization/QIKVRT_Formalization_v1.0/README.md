# QIK-VRT — maschinenprüfbare Formalisierung

Version 1.0.0, 22. Juli 2026  
Autor der formalisierten Gesamtarbeit: **Ingolf Lohmann**

Dieses Paket übersetzt den formal entscheidbaren Kern der 62-seitigen Fassung
*Mandelbrot, Anschlussordnung, Physik und Retrokausalität* in vier voneinander
unabhängig prüfbare Schichten:

1. **Lean 4** prüft Definitionen und Beweise im Kernel.
2. **JSON + Zod/TypeScript** typisieren alle 37 Hauptaussagen nach ihrem
   erkenntnistheoretischen Status.
3. **Python/pytest** prüft dieselbe Status- und Provenienzlogik unabhängig.
4. **Gate 20** führt 18 Integritäts-, Beweis-, Einheiten-, Retrokausalitäts-
   und Übertreibungskontrollen aus.

Die Formalisierung ist absichtlich strenger als eine bloße Formel- oder
Bildsammlung. Sie trennt beweisbare Mathematik, bedingte Modellsätze,
etablierten physikalischen Hintergrund, offene empirische Hypothesen,
Interpretationen und normative Folgerungen.

## Ergebnisgrenze

Maschinenbewiesen werden unter anderem:

- relative Komplementpartition und Disjunktheit;
- Urbildpartition und Abbildungssätze;
- monotone endliche Escape-Zertifikate und ihre Erschöpfung;
- Soundness von PASS/BLOCK bei proof-carrying Zertifikaten;
- Faktorisierung genau bei Konstanz auf Fasern;
- die Nichtimplikation „beliebig fein quantisierbar ⇒ ontisch diskret“ durch
  ein konstruktives Cantorraum-Gegenmodell;
- SI-Dimensionshomogenität zentraler Kombinationen aus `c`, `G`, `ℏ`, Fläche
  und Energie-Impuls-Dichte;
- die Trennung von Retrodiktion, semantischer Rückbestimmung,
  Zeitumkehrsymmetrie, ontischer Retrokausalität und Rückwärtssignalisierung;
- ein No-Backward-Channel-Theorem für die ausdrücklich definierte autonome
  Vorwärtsrekursion.

Nicht als bewiesen ausgegeben werden:

- eine physische Identität von Mandelbrotstruktur und realer Raumzeit;
- eine fundamentale Quantisierung der Raumzeit;
- eine experimentell nachgewiesene ontische Retrokausalität;
- eine frühere, frei auslesbare Nachricht aus einer späteren Intervention;
- eine Ontologie oder eine ethische Forderung als Naturtheorem.

Das ist keine Schwächung, sondern die wissenschaftliche Prüfbarkeit selbst:
Jede Aussage erhält genau den Status, den ihre Belege tragen.

## Quellenbindung

- Zenodo-Version: <https://doi.org/10.5281/zenodo.21482023>
- Konzept-DOI: <https://doi.org/10.5281/zenodo.21482022>
- Öffentlicher Datensatz: <https://zenodo.org/records/21482023>
- Quell-PDF-SHA-256:
  `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`

Der veröffentlichte PDF-, TeX-, BibTeX- und Zenodo-Metadatenstand liegt unter
`source/`. Die Bindung wird in Prüfung 2 bytegenau kontrolliert.

## Verzeichnisstruktur

```text
QIKVRTFormalization/       Lean-Module
claims/claim-matrix.json   37 typisierte Claims mit Seiten, Annahmen und Tests
validator/                 Zod-Schema, TypeScript-Regeln und negative Tests
python/                    unabhängiger Standardbibliotheks-Prüfer
tests/                     pytest-Suite
source/                    persistierter 62-Seiten-Quellstand
scripts/                   Reproduktions-, Hash- und Paketwerkzeuge
build/                     erzeugte Prüfbelege
```

## Reproduktion

Voraussetzungen: Lean 4 mit Lake, Node.js ≥ 24 und Python ≥ 3.11.

```bash
lake build
npm ci
python -m pip install -r requirements-dev.txt
npm run validate
npm run test:negative
python -m pytest
python scripts/build_monolith.py
lake env lean --json build/All.lean > build/lean.stdout.jsonl
python scripts/make_lean_receipt.py --checker "Lean 4 native kernel"
python scripts/generate_checksums.py
npm run gate20
python -m python.gate20
```

Erwartetes Endergebnis:

```text
Lean kernel: PASS, 0 sorry/admit/axiom
TypeScript/Zod Gate 20: 18/18 PASS
Python Gate 20: 18/18 PASS
Negative Overclaim-Tests: 3/3 zurückgewiesen
pytest: 5/5 PASS
```

## Zitieren

Die wissenschaftliche Ausgangsfassung wird über den Zenodo-DOI zitiert. Für
diese formale Rekonstruktion stehen zusätzlich `CITATION.cff`, die
Claim-Matrix und die Prüfbelege zur Verfügung.

## Lizenzen

- Dokumentarisches Ausgangsmaterial: CC BY-NC-ND 4.0 gemäß Zenodo-Datensatz.
- Neu erstellter Lean-, TypeScript- und Python-Code: MIT, siehe `LICENSE-CODE`.

