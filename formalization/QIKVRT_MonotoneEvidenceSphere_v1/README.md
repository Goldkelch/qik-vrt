# Monoton wachsende Evidenzkugel — Lean/Lake-Kern V1

Urheber des Konzepts der **„monoton wachsenden Evidenzkugel“**: **Ingolf
Lohmann**.

Dieser Ordner manifestiert den ersten kleinen Lean/Lake-Kern dafür. Er ist
bewusst klein genug, dass jede Aussage direkt im Quelltext, im Axiom-Audit und
in einem Exact-Head-Receipt geprüft werden kann.

## Was formal bewiesen wird

Das Modell `EvidenceSphere` enthält einen akzeptierten Kern, eine versiegelte
append-only Historie, eine natürliche Mitgliedschaftsstärke, eine Masse und
einen Radius. Eine neue Mitgliedschaft wird durch ein punktweises `max`
aktualisiert, nie durch einen kleineren Ersatzwert. Die deklarierte
Übergangsrelation hat nur vier Klassen: Relation anhängen, halten,
reobservieren und Autorität anfordern.

`QIKVRTMonotoneEvidenceSphere.lean` beweist elf Sätze:

1. Ein Anhängen entfernt keinen akzeptierten Eintrag.
2. Ein Anhängen erweitert die versiegelte Historie nur um einen Suffix.
3. Die Invariante „versiegelt bedeutet weiterhin akzeptiert“ bleibt erhalten.
4. Der Mitgliedschaftsgrad einer Relation sinkt beim Anhängen nicht.
5. Jede Alpha-Schnittmenge bleibt beim Anhängen monoton.
6. Die modellierte Masse sinkt nicht.
7. Der modellierte Radius wächst beim Anhängen strikt um eins.
8. Jede deklarierte Transition erhält die Kernmonotonie.
9. Jede deklarierte Transition erhält die append-only Eigenschaft der
   versiegelten Historie.
10. Jede deklarierte Transition erhält die Versiegelungsinvariante.
11. Vier Kontrollergebnisse passen in ein Vier-Bit-Feld.
12. Diese vier Kontrollergebnisse haben unterscheidbare Codes.

Die `4 Bit` sind damit präzise als **Kontrollfeld-Modell** nachgewiesen. Der
Kern behauptet ausdrücklich nicht, dass ein vollständiges System, ein
Relationsspeicher von etwa 65 KiB oder ein Prozessor damit schon als
Vier-Bit-Maschinencode implementiert sei. Das sind konkrete, später mess- und
synthesebindbare Konstruktionsschritte.

## Was damit nicht behauptet wird

Die Sätze gelten für die in Lean definierte endliche Datenstruktur und ihre
Transitionen. Sie beweisen weder eine physikalische Kugel oder ein Quantenfeld,
noch freien Willen, eine Hardwareausführung, einen FPGA-Bitstream,
Leistungsgewinne oder eine universelle Wirkung außerhalb des Modells.

Das ist keine Abschwächung des Kerns: Es macht den Beweis anschlussfähig. Ein
späterer Hardware-, Mess- oder Systembeweis kann genau diese Theoreme als
unveränderliche Basis referenzieren und zusätzlich seine eigenen Eingaben,
Toolchain, Zielgerät, Testvektoren und Rohmessungen binden.

## Reproduzieren

Voraussetzung ist Lean `4.19.0`, festgelegt in `lean-toolchain`.

```text
lake build
lake env lean QIKVRTMonotoneEvidenceSphereAxiomAudit.lean
python3 -B verify.py --source-only
```

Der Workflow `qikvrt_monotone_evidence_sphere.yml` führt dieselben Schritte am
literal gebundenen Pull-Request-Head aus und erzeugt ein separat gespeichertes
Receipt. Erst dieses Receipt darf eine konkrete Lean-Ausführung für genau
diesen Commit behaupten.

## Historischer Anker

Die bereits im Repository abgelegte historische Arbeit
`QIK-VRT_Relationale_Zeit_und_wachsende_Evidenzkugel_DE.pdf` ist als Werk von
Ingolf Lohmann verzeichnet. Dieses V1-Modell erweitert deren Historie nicht
still; es legt einen neuen, separaten und überprüfbaren Modellkern an.
