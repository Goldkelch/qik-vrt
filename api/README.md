# QIK-VRT public API quickstart

This directory contains the canonical machine-readable and human-readable contract for the QIK-VRT GitHub Dispatch API.

- OpenAPI: [qikvrt_github_api.openapi.yaml](qikvrt_github_api.openapi.yaml)
- GitHub Actions implementation: [../.github/workflows/qikvrt_mesh_api.yml](../.github/workflows/qikvrt_mesh_api.yml)
- Local synchronous adapter: [../src/qikvrt_github_api_shim.py](../src/qikvrt_github_api_shim.py)
- Reference client: [../scripts/qikvrt_api_client.py](../scripts/qikvrt_api_client.py)

## Canonical Authority endpoint

The directly addressable GitHub workflow endpoint is:

```text
POST https://api.github.com/repos/Goldkelch/qik-vrt/actions/workflows/qikvrt_mesh_api.yml/dispatches
```

The public Mirror exposes the same workflow file at:

```text
POST https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/workflows/qikvrt_mesh_api.yml/dispatches
```

For GitHub `workflow_dispatch`, a fine-grained token requires **Actions: write** for the target repository. A classic PAT requires `repo`. Use the GitHub API headers recommended for the current API version.

## Safe dry-run example

The following example sends the bytes `hello` as an **ingest dry-run**. It does not authorize a non-dry-run effect.

```bash
curl -L \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  https://api.github.com/repos/Goldkelch/qik-vrt/actions/workflows/qikvrt_mesh_api.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "operation": "ingest",
      "artifact_id": "public-api-example",
      "payload_b64": "aGVsbG8=",
      "expected_sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
      "dry_run": "true",
      "request_id": "public-api-example-001",
      "effect_accepted": "false"
    }
  }'
```

GitHub currently returns HTTP `200` for an accepted workflow dispatch and includes the workflow run ID/URLs. This is **transport admission only**. Inspect that run and its `qikvrt-api-state` artifact for the QIK-VRT result.

## repository_dispatch alternative

The same workflow also accepts:

```text
POST https://api.github.com/repos/Goldkelch/qik-vrt/dispatches
```

with the exact event type:

```json
{
  "event_type": "qikvrt_mesh_api",
  "client_payload": {
    "operation": "ingest",
    "artifact_id": "public-api-example",
    "payload_b64": "aGVsbG8=",
    "expected_sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    "dry_run": "true",
    "request_id": "public-api-example-001",
    "effect_accepted": "false"
  }
}
```

For GitHub `repository_dispatch`, a fine-grained token requires **Contents: write**. GitHub returns HTTP `204` on accepted dispatch.

## Input contract

Required for every request:

- `operation`: one of `ingest`, `verify`, `stage`, `release_status`
- `artifact_id`: safe identifier, 1–128 characters
- `dry_run`: `true` or `false`
- `request_id`: stable idempotency key
- `effect_accepted`: explicit scoped effect authorization flag

Conditionally used:

- `payload_b64`
- `expected_sha256`
- `state_run_id` — required by the workflow for `verify` and `stage`
- `remote_evidence_b64` — signed remote release evidence for `release_status`

The local loopback adapter additionally permits an optional `responsibility_owner` field and requires it, when supplied, to match the authenticated principal. In the GitHub Actions path, responsibility is bound to `github.actor`; caller-supplied `responsibility_owner` is not used by the workflow.

## Effect boundary

```text
HTTP dispatch accepted
!= workflow job executed
!= QIK-VRT EFFECT_ACK_DONE
```

For a non-dry-run effect, `effect_accepted=true` is required in addition to the authenticated GitHub origin. A successful GitHub dispatch response does not itself authorize or prove the requested downstream effect.

`TRANSPORT_ACK != EFFECT_ACK`.
