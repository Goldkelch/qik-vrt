# V2.0 Parser-Fix und ownerseitiger Upload-Publish-Pfad

Status: `V2_0_REPLACES_V1_9`.

## Blockierter Vorgänger

V1.9 ist blockiert durch:

`POWERSHELL_FUNCTION_DECLARATION_CONCATENATION_PARSE_ERROR`

Fehlerklasse:

`Invoke-GitHubUploadfunction Invoke-GitHubUpload(...)` wurde als zusammengeklebte PowerShell-Funktionsdeklaration ausgeliefert und bricht bereits vor Laufzeit beim Parsen.

## Korrektur

V2.0 ersetzt die fehlerhafte Zeile durch genau eine Funktionsdeklaration:

`function Invoke-GitHubUpload([string]$UploadUrl, [string]$FilePath, [string]$AssetName) { ... }`

Zusätzlich enthält V2.0 ein Windows-seitiges Parser-Gate:

`POWERSHELL_PARSE_CHECK_ONLY.cmd`

Dieses Gate verwendet den PowerShell-AST-Parser und blockiert:

- Parserfehler in `tools/github_zenodo_release_publish.ps1`,
- doppelte `function...function`-Tokens,
- das exakte V1.9-Fehlmuster `Invoke-GitHubUploadfunction`.

## Workflow bleibt GitHub-token-only

V2.0 verwendet weiterhin keinen Zenodo-Token. Der Ablauf bleibt:

1. GitHub-Repository ownerseitig in Zenodo aktivieren.
2. Unter Windows `DRY_RUN_VERIFY_ONLY.cmd` ausführen.
3. Optional `POWERSHELL_PARSE_CHECK_ONLY.cmd` ausführen.
4. `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd` ausführen.
5. GitHub Release prüfen.
6. Zenodo-Ingestion/DOI in Zenodo-Weboberfläche prüfen.

Live-Publish ist ownerseitig, nicht sandboxseitig ausgeführt.
