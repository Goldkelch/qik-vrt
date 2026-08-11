<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Reproduzierbarkeit

## Statische Kandidatenprüfung

```text
python3 -B verify_qce_package.py --static-only
```

Diese Prüfung validiert Quellform, Referenzsyntax, zehn Positiv-/Negativtests,
JSON-Dateien, PDF-Eigenschaften und SHA-256-Bindungen. Sie erzeugt bewusst kein
Lean-Receipt.

## Vollständige formale Prüfung

```text
lake build
python3 -B verify_qce_package.py \
  --lean "$(command -v lean)" \
  --axiom-output qce-axiom-output.txt \
  > qce-verification.json
```

Anschließend:

```text
python3 -B make_qce_kernel_receipt.py \
  --lean "$(command -v lean)" \
  --axiom-output qce-axiom-output.txt \
  --verification-output qce-verification.json \
  --output QCE_KERNEL_RECEIPT.json \
  --repository "$GITHUB_REPOSITORY" \
  --commit "$GITHUB_SHA" \
  --tree "$(git rev-parse "${GITHUB_SHA}^{tree}")" \
  --run-id "$GITHUB_RUN_ID" \
  --run-attempt "$GITHUB_RUN_ATTEMPT"
```

Das erzeugte Receipt ist nur für die exakten Sourcebytes, den gebundenen
Commit/Tree und die ausgewiesene Lean-Version gültig.

## Persistierte Ausführungsevidenz

Der in diesem Paket enthaltene Receipt stammt aus dem erfolgreichen Lauf
`QIK-VRT QCE candidate verification` mit Run-ID `31467654213`. Seine
Provenienz, die drei Artefaktdateien und ihre Hashes sind in
`QCE_KERNEL_ARTIFACT_PROVENANCE.json` gebunden. Die lokale Paketbindung wird
ohne erneuten Lean-Lauf geprüft durch:

```text
python3 -B verify_qce_package.py \
  --static-only \
  --executed-receipt QCE_KERNEL_RECEIPT.json
```

## PDF

```text
./build_qce_pdf.sh
pdfinfo QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf
pdftotext QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf -
```

## Zenodo-Neubindung

Vor einer Zenodo-Veröffentlichung müssen `MANIFEST.json`, `SHA256SUMS` und
`MACHINE_PROOF_BUNDLE.json` unter Einschluss des tatsächlich ausgeführten
`QCE_KERNEL_RECEIPT.json`, des Axiom-Audit-Outputs, des Verifikationsoutputs
und der Artefaktprovenienz neu erzeugt werden. Ein unverbindliches
Receipt-Template gehört nicht in ein ausgeführtes Zenodo-Fileset.
