<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
Author and rights holder: Ingolf Lohmann.
-->

# Plan für eine enge `workflow_dispatch`-Ausführung

## Warum derzeit kein aktiver Workflow erzeugt wird

Ein produktiver GitHub-Actions-Workflow muss an einen bestimmten remote
vorhandenen Quell-Commit, den finalen v2-Manifest und die kanonische
Einmalautorisierung gebunden sein. Diese Werte existieren vor sichtbarer
Kandidatenrückgabe und exakter Freigabe nicht. Ein jetzt aktiver Workflow hätte
damit entweder Platzhalter oder einen zu weiten Ausführungsbereich; beides
wäre mit der Zenodo-v2-Policy unvereinbar.

## Vorgesehener enger Workflow nach Finalisierung

Nach den Schritten aus `FINALIZATION_CHECKLIST.md` kann ein einzelner neuer
Workflow mit folgenden unveränderlichen Eigenschaften angelegt werden:

- **Trigger:** ausschließlich `workflow_dispatch`.
- **Repository:** nur `Goldkelch/qik-vrt`.
- **Inputs:** keine frei wählbaren Pfade; höchstens ein exakter
  `expected_source_head`, der mit fest codiertem Manifestpfad verglichen wird.
- **Bindung:** checkout bei diesem Head; `git rev-parse HEAD` und
  `manifest.source_head` müssen bytegenau übereinstimmen; Worktree muss sauber
  sein; v2-Machine-Proof- und Owner-Autorisierungsprüfung erfolgen vor jedem
  Netzwerkzugriff.
- **Secrets:** nur `GITHUB_TOKEN` und `ZENODO_ACCESS_TOKEN` aus GitHub Actions
  Secrets, niemals geloggt oder in Artefakte geschrieben.
- **Ausführung:** ausschließlich
  `python3 -B tools/qikvrt_zenodo_publish.py --manifest <fixed-path>`.
- **Persistenz:** der Publisher darf nur seine gebundene
  `zenodo-publication.json` ändern. Ein anschließender Receipt-Commit darf
  ausschließlich diese Datei plus die deterministisch regenerierten globalen
  Integritätsdateien enthalten und muss auf einem separaten Receipt-Branch als
  PR landen, sofern ein direkter Push auf den gebundenen Ausführungsbranch
  nicht gesondert freigegeben ist.
- **Erfolg:** erst nach erfolgreicher öffentlicher Byte-Redownload-Prüfung und
  Persistenz des Receipts; ein Actions-Status allein ist kein
  Veröffentlichungsnachweis.

Der Plan verwendet den vorhandenen generischen Publisher und ergänzt keine
neue Zenodo-Transportlogik. Er wird erst nach der exakten Autorisierung zu
einem ausführbaren Workflow konkretisiert.
