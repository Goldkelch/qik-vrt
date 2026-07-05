# Zenodo Upload Operation V1.4

Status: DRAFT_ONLY_AUTOMATION.

V1.4 replaces V1.3 because V1.3 contained a one-click publish path and did not reliably match the expected owner-side Zenodo workflow.

Root commands:

- `DRY_RUN_VERIFY_ONLY.cmd`: local verification only; no network.
- `ZENODO_UPLOAD_DRAFT_ONLY.cmd`: creates a Zenodo draft deposition, uploads `assets/pdf/odu_proof.pdf`, applies `zenodo/metadata.json`, writes `zenodo/zenodo_upload_result.json`, and does not publish.
- `ZENODO_SANDBOX_DRAFT_ONLY.cmd`: same draft workflow against `https://sandbox.zenodo.org/api`.

Explicit non-goals:

- No automatic publication.
- No irreversible publish action.
- No token stored in repository.
- No local delete or cleanup operation.

The owner must review the Zenodo web draft manually before publication.
