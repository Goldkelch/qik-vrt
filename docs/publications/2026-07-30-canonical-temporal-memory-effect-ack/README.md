<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: kanonischer Speicher zwischen Vergangenheit und Zukunft

Dieses Verzeichnis enthält den noch unveröffentlichten Working-Paper-Kandidaten
`qikvrt-canonical-temporal-memory-effect-ack-v1`.

Die wissenschaftlich engste Kernaussage lautet:

> In der definierten QIK-VRT-Freigabefunktion ist eine gegenwärtig vorhandene,
> kanonisch repräsentierte und zukunftsindexierte Wirkungsbedingung ein
> funktional relevanter Eingang. Das Paper bezeichnet diese
> Protokollabhängigkeit autorenseitig als operationale Retrokausalität; es
> behauptet damit weder ein Signal aus einer aktualen Zukunft noch eine
> nachträgliche Änderung eines Vergangenheitsrecords.

## Artefakte

| Datei | Rolle |
|---|---|
| `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf` | gespeicherter PDF-Kandidatenstand; seine genaue Gültigkeit ist ausschließlich durch den zugehörigen Render-Receipt bestimmt |
| `QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex` | reproduzierbare XeLaTeX-Quelle |
| `CLAIM_MATRIX.json` | typisierte Inventur der 22 Hauptclaims dieses Paper-Scopes |
| `CLAIM_MATRIX_H0_PENDING.json` | bytegenaue historische Pending-Ausgangsmatrix zur Offline-Rekonstruktion des H0→H1-Übergangs |
| `SOURCE_EVIDENCE_BINDINGS.json` | vollständige Claim-, TeX-Zitations-, DOI-, Standard-, Draft- und Repository-Bindungen |
| `BOUNDARY_TEST_REPORT.json` | positive und negative Python-/Repository-Gates; kein Lean-Kernel-Receipt |
| `EVIDENCE_BOUNDARY.md` | explizite Nachweis- und Nichtnachweisgrenzen |
| `PDF_RENDER_VALIDATION.json` | Build-, Font-, Seiten- und visuelle QA-Evidenz |
| `KERNEL_PROOF_PLAN.json` | erwartete Lean-Sätze, Toolchain und Receipt-Vertrag |
| `KERNEL_RECEIPT.json` | finaler zweistufiger Exact-Head-, Artefakt-, Axiom- und Claim-Übergangsbeleg mit expliziter Selbstinklusionsgrenze |
| `KERNEL_EVIDENCE_H0_PENDING.json` | unveränderte Rohbytes des erfolgreichen H0-CI-Kernel-Artefakts für die Pending-Ausgangsmatrix |
| `KERNEL_EVIDENCE_H1_TARGET.json` | unveränderte Rohbytes des erfolgreichen H1-CI-Kernel-Artefakts für die materialisierte Zielmatrix |
| `CHANGE_NOTICE.md` | sichtbare wissenschaftliche Präzisierungen gegenüber der wortwörtlichen Ausgangsthese |
| `ORIGINAL_THESIS_TRANSCRIPT.md` | wortwörtliche, vom Autor gelieferte Ausgangsthese und unmittelbare Korrektur |
| `CITATION.cff` | Kandidatenmetadaten ohne vorweggenommenen DOI oder Veröffentlichungsdatum |
| `LICENSE_NOTICE.md` | dateibezogene Lizenzgrenzen |
| `ZENODO_FILESET.md` | vorgesehener, noch nicht autorisierter Upload-Scope |

Der formale Quellkern liegt in:

- `formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/CanonicalTemporalMemory.lean`

Die Claims `CTM-001` bis `CTM-004` sind gemeinsam `FORMAL_PROVED` /
`KERNEL_VERIFIED`. Grundlage ist der persistierte `KERNEL_RECEIPT.json`, der
den erfolgreichen Exact-Head-Lauf, die exakte Lean-Quelle, neun Theoreme,
Axiomberichte und das kompilierte Objekt bindet. Der aktuelle
Receipt-Zustand `KERNEL_VERIFIED` schließt die zweistufige Prüfung: H0 bindet
die Pending-Ausgangsmatrix, H1 bindet die unveränderten Aussagen und
Beweisreferenzen in der materialisierten Zielmatrix. Der Receipt selbst wird
erst im direkten H2-Nachfolger materialisiert und beansprucht daher
ausdrücklich keine kryptographisch unmögliche Selbstinklusion. Erst ein
späteres, kandidatengebundenes Machine-Proof-Bundle kann ihn als Upload-Gate
verwenden.

Die zusätzlich persistierte `CLAIM_MATRIX_H0_PENDING.json` ist bytegleich mit
dem Matrix-Blob aus H0. Ein Offline-Gate kann deshalb nachrechnen, dass H1 nur
die vier erlaubten Formalstatusfelder und den aggregierten `proof_state`
ändert; Aussagen, Grenzen, Quellen und Beweisreferenzen bleiben gleich.

Ein `PREPUBLICATION_RETURN_RECEIPT.json`, das
`MACHINE_PROOF_BUNDLE.json`, die einmalige Owner-Autorisierung und ein
v2-`publish-request.json` werden in dieser azyklischen Reihenfolge erst nach
Rückgabe der exakten Kandidatenbytes materialisiert: Return-Receipt, Bundle,
Owner-Entscheidung, Publish-Request. Ihr Fehlen ist fail-closed.

## PDF reproduzieren

Vom Publikationsverzeichnis:

```sh
SOURCE_DATE_EPOCH=1785369600 FORCE_SOURCE_DATE=1 \
  xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
SOURCE_DATE_EPOCH=1785369600 FORCE_SOURCE_DATE=1 \
  xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
SOURCE_DATE_EPOCH=1785369600 FORCE_SOURCE_DATE=1 \
  xelatex -interaction=nonstopmode -halt-on-error \
  QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex
```

Nach jeder Änderung der TeX-Quelle muss der PDF-Kandidat neu gebaut und der
`PDF_RENDER_VALIDATION.json` neu erzeugt werden. Ein älterer Receipt belegt nur
die darin ausdrücklich genannten Quell- und PDF-Hashes. Die visuelle Prüfung
rendert alle gespeicherten PDF-Seiten mit Poppler und kontrolliert Schnitt,
Überlagerung, Schriftlesbarkeit, Tabellenumbruch und Leerseiten.

## Veröffentlichungsstatus

Der in diesen Artefakten festgehaltene Freeze-Zustand ist
`CANDIDATE_PREPUBLICATION`.

- kein Zenodo-DOI wird vorweggenommen;
- kein Veröffentlichungsdatum wird in `CITATION.cff` vorweggenommen;
- kein IETF-Portalupdate wird vorweggenommen;
- ein vorhandener Internet-Draft wird ausdrücklich nicht als IETF-Billigung
  oder Konsens behandelt;
- kein Repository-weites `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird
  behauptet;
- die ontische physikalische und die panpsychistische Erweiterung bleiben
  ausdrücklich offen beziehungsweise interpretativ.

Dieser Freeze ist eine historische, scope-gebundene Beobachtung. Spätere
Merge-, Mirror-, Kernel- oder Publikationsreceipts dürfen den operativen Status
fortschreiben, müssen aber ihre eigenen Heads, Trees, Manifeste, Hashes und
Zeitstempel nennen. Vor einem Upload ist eine separate, kandidatengebundene
Freigabe erforderlich. Nach Veröffentlichung müssen öffentlicher Record,
öffentliche Dateien und Re-Downloads bytegenau geprüft und die daraus
abgeleiteten Receipts erneut in Authority und Mirror gebunden werden.
