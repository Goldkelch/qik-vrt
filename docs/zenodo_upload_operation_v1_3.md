# Zenodo upload operation - V1.3

Status: OPERATIVE_WINDOWS_COMMAND_INCLUDED

Primary Zenodo PDF artifact:

- Path: `assets/pdf/odu_proof.pdf`
- SHA256: `2382b5d4970559bc28649a6deb6797fe867fc70439140e4cf1c1e59964a37de6`
- Size bytes: `308498`

Windows command files:

- `ZENODO_UPLOAD_PDF.cmd` - creates a Zenodo deposition, uploads the PDF, applies metadata, leaves the record as a draft.
- `ZENODO_UPLOAD_AND_PUBLISH_PDF.cmd` - creates a Zenodo deposition, uploads the PDF, applies metadata, and publishes the record.

Required owner-side secret:

- Environment variable: `ZENODO_ACCESS_TOKEN`

Optional endpoint override:

- `ZENODO_API_BASE=https://sandbox.zenodo.org/api` for sandbox testing.
- Default is `https://zenodo.org/api`.

Execution examples on Windows:

```bat
set ZENODO_ACCESS_TOKEN=your_personal_access_token
ZENODO_UPLOAD_PDF.cmd
```

Sandbox draft test:

```bat
set ZENODO_ACCESS_TOKEN=your_sandbox_token
set ZENODO_API_BASE=https://sandbox.zenodo.org/api
ZENODO_UPLOAD_PDF.cmd
```

Production upload and publish:

```bat
set ZENODO_ACCESS_TOKEN=your_personal_access_token
ZENODO_UPLOAD_AND_PUBLISH_PDF.cmd
```

Operational boundaries:

- No access token is stored in this repository.
- The script verifies the PDF SHA256 before upload.
- The script uses the Zenodo deposition API: create deposition, upload to bucket, update metadata, optional publish.
- Live upload was not executed in this sandbox.
