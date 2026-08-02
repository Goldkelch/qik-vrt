<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT VRTCore Virtual Sphere H6

H6 schließt die zuvor benannten Hohlräume im **deklarierten virtuellen
Modell**: konkrete nichtleere Initialisierung, deterministische und
lückenfreie Nachfolge, Invariantenerhaltung, exakt um eins wachsende endliche
Population, mathematische Unbeschränktheit, formaler Bitstream-Codec,
AST-Semantik-Verfeinerung sowie eine erhaltene Wirkungsgrenze.

Der oberste Lean-Satz ist:

```text
QIKVRT.VRTCore.VirtualSphereH6.h6_virtualSphere_noHole_complete
```

Der lokale Befund lautet **55/55 kernelakzeptiert**. Zwei frische
Lean-4.19.0-Läufe erzeugten dasselbe persistierte `.olean` mit SHA-256
`c50a1810715547bf760fe087364d36d2a85bd800b21495ec6a33c6f8decabcf8`;
beide vollständigen Axiom-Audits waren identisch.

## Einstieg

- `QIK-VRT_VirtualSphere_NoHole_DE.md`: allgemein verständlicher,
  WhatsApp- und Vorlese-optimierter Artikel.
- `VRTCore_VirtualSphere.lean`: Definitionen, konkrete Konstruktion und
  55 benannte Theoreme.
- `VRTCore_VirtualSphere_AxiomAudit.lean`: vollständiger Axiom-Audit.
- `VRTCore_VirtualSphere_Syntax.ebnf`: menschlich lesbare H6-
  Oberflächengrammatik mit H6-S01 bis H6-S39.
- `VRTCore_VirtualSphere_EBNF_Map_DE.svg`: Vektorkarte der Grammatik- und
  Beweisschichten.
- `H6_REFERENCE_OBJECT.vsphere`: kanonisches Oberflächenobjekt.
- `CLAIM_MATRIX.json`: sechs Erkenntnisarten und ihre Grenzen.
- `SOURCE_EVIDENCE_BINDINGS.json`: Quelle-Evidenz-Zuordnung.
- `TRUST_BASE.json`: explizite logische und technische Vertrauensbasis.
- `COMMANDS.json`: normalisierte Befehle der lokalen Doppelausführung.
- `H6_LOCAL_KERNEL_RECEIPT.json`: lokale Ausführungs- und Bytebindung.
- `MANIFEST.json`, `SHA256SUMS`, `PACKAGE_ROOT.sha256`: exaktes Inventar und
  gestufte Fixitätskette.
- `verify_h6_package.py`: fail-closed Reproduktionsprüfung.

## Reproduktion

```bash
python3 verify_h6_package.py \
  --lean /pfad/zu/lean-4.19.0/bin/lean \
  --preload /pfad/zu/qikvrt-lean-selfexe-compat.so
```

Der Verifier prüft unter anderem:

1. exakte Gleichheit von Manifest-, Verzeichnis- und Prüfsummen-Inventar;
2. jede gebundene Dateigröße und jeden SHA-256-Wert;
3. 55 Theoreme, 55 Auditdirektiven und das Fehlen projektlokaler Axiome,
   `sorry`, `admit` und `unsafe`;
4. zwei neue Compiles, byteidentische `.olean`-Ausgaben und Gleichheit mit
   dem persistierten `.olean`;
5. zwei vollständige, identische Axiom-Audits und die deklarierte
   Abhängigkeitsverteilung;
6. die H6-S01-bis-H6-S39-Oberflächenpflichten, Claim-Grenzen,
   `PhysicalClosure = OPEN` und `EFFECT_ACK_CONTINUE`.

## Exakte Geltungsgrenze

```text
VIRTUAL_CLOSURE_SCOPE = PASS
PHYSICAL_CLOSURE = OPEN
PHYSICAL_BIG_BANG_IDENTITY = NOT_CLAIMED
INDEPENDENT_EXTERNAL_REPRODUCTION = OPEN
GLOBAL_PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
EFFECT_STATE = EFFECT_ACK_CONTINUE
```

`VIRTUAL_CLOSURE_SCOPE = PASS` bedeutet: Der konkrete H6-Zertifikatskern und
die exakte lokale Paketbyte-Kette bestehen relativ zur ausgewiesenen
Lean-/SHA-256-Vertrauensbasis. Es bedeutet weder eine grundlagenfreie absolute
Wahrheit noch physikalische Quantengravitation, einen Gravitonnachweis oder die
Identität virtueller Kosmogenese mit dem physikalischen Urknall.
